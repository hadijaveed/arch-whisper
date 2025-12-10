#!/usr/bin/env python3
"""arch-whisper: Voice dictation daemon for Linux + Hyprland"""

# Client mode check - must be before heavy imports (numpy, scipy, sounddevice)
# ruff: noqa: E402
import socket
import sys

SOCKET_PATH = "/tmp/arch-whisper.sock"

CLIENT_COMMANDS = {"start", "stop", "status", "ping", "reset"}

if len(sys.argv) > 1 and sys.argv[1] in CLIENT_COMMANDS:
    def send_command(cmd):
        try:
            c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            c.settimeout(2.0)
            c.connect(SOCKET_PATH)
            c.send(cmd.encode("utf-8"))
            r = c.recv(1024).decode("utf-8")
            c.close()
            return r
        except FileNotFoundError:
            return "error: daemon not running"
        except socket.timeout:
            return "error: timeout"
        except Exception as e:
            return f"error: {e}"
    print(send_command(sys.argv[1]))
    sys.exit(0)

# Daemon mode - import heavy dependencies
import json
import os
import re
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.io import wavfile

from config import (
    MODEL_SIZE,
    COMPUTE_TYPE,
    LANGUAGE,
    SAMPLE_RATE,
    FILLERS,
    TRANSCRIPTION_BACKEND,
    GROQ_WHISPER_MODEL,
    TRANSFORM_ENABLED,
    TRANSFORM_BACKEND,
    TRANSFORM_MODEL,
    TRANSFORM_PROMPT,
)

CHANNELS = 1
MAX_RECORDING_SECONDS = 60
TRANSCRIPTION_TIMEOUT = 30
MULTI_TURN_SPACING_WINDOW = 30


class ArchWhisper:
    def __init__(self):
        self.model = None
        self.recording = False
        self.transcribing = False
        self.audio_data = []
        self.stream = None
        self.lock = threading.Lock()
        self.processing_lock = threading.Lock()
        self.watchdog_timer = None
        self.cancel_transform = False
        self.shutdown_requested = False
        self.last_typing_time = 0
        self.transform_first_chunk = False
        self.pending_start = False

    def load_model(self):
        if TRANSCRIPTION_BACKEND == "local":
            from faster_whisper import WhisperModel

            print(f"Loading faster-whisper model '{MODEL_SIZE}'...")
            self.model = WhisperModel(
                MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE
            )
            print("Model loaded!")
        else:
            print(f"Using Groq API ({GROQ_WHISPER_MODEL})")
            if not os.environ.get("GROQ_API_KEY"):
                print("WARNING: GROQ_API_KEY not set")

    def notify(self, message: str, urgency: str = "normal", timeout: int = 1500):
        try:
            subprocess.run(
                [
                    "notify-send",
                    "-t",
                    str(timeout),
                    "-u",
                    urgency,
                    "-a",
                    "arch-whisper",
                    message,
                ],
                check=False,
                capture_output=True,
            )
        except Exception:
            pass

    def audio_callback(self, indata, frames, time_info, status):
        if self.recording:
            self.audio_data.append(indata.copy())

    def start_recording(self):
        with self.lock:
            if self.recording:
                return
            if self.transcribing:
                self.pending_start = True
                return
            self._do_start_recording()

    def _do_start_recording(self):
        self.pending_start = False
        self.cancel_transform = True
        if self.watchdog_timer:
            self.watchdog_timer.cancel()
        self.recording = True
        self.audio_data = []
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=np.float32,
            callback=self.audio_callback,
            blocksize=1024,
        )
        self.stream.start()
        self.watchdog_timer = threading.Timer(
            MAX_RECORDING_SECONDS, self._watchdog_timeout
        )
        self.watchdog_timer.start()
        self.notify("Recording...", urgency="low", timeout=10000)
        print("Recording started...")

    def stop_recording(self) -> str:
        with self.lock:
            if not self.recording:
                return ""
            self.recording = False
            if self.watchdog_timer:
                self.watchdog_timer.cancel()
                self.watchdog_timer = None
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            if not self.audio_data:
                return ""
            audio = np.concatenate(self.audio_data, axis=0).flatten()
            self.audio_data = []

        print(f"Recording stopped. {len(audio) / SAMPLE_RATE:.2f}s")
        if len(audio) < SAMPLE_RATE * 0.3:
            return ""

        return self._transcribe(audio)

    def _transcribe(self, audio) -> str:
        print("Transcribing...")
        result = [None]
        error = [None]

        def do_transcribe():
            try:
                if TRANSCRIPTION_BACKEND == "local":
                    result[0] = self._transcribe_local(audio)
                else:
                    result[0] = self._transcribe_groq(audio)
            except Exception as e:
                error[0] = e

        thread = threading.Thread(target=do_transcribe)
        thread.start()
        thread.join(timeout=TRANSCRIPTION_TIMEOUT)

        if thread.is_alive():
            print(f"Transcription timeout!")
            self.notify("Transcription timed out", urgency="critical")
            return ""
        if error[0]:
            print(f"Transcription error: {error[0]}")
            self.notify(f"Error: {error[0]}", urgency="critical")
            return ""
        return result[0] or ""

    def _transcribe_local(self, audio) -> str:
        segments, _ = self.model.transcribe(
            audio,
            language=LANGUAGE,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            initial_prompt="Use proper punctuation, capitalization, and complete sentences.",
        )
        text = self.clean_text(" ".join([s.text for s in segments]))
        print(f"Transcribed: {text}")
        return text

    def _transcribe_groq(self, audio) -> str:
        from groq import Groq

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            wavfile.write(temp_path, SAMPLE_RATE, (audio * 32767).astype(np.int16))

        try:
            client = Groq(api_key=api_key)
            with open(temp_path, "rb") as f:
                result = client.audio.transcriptions.create(
                    file=f,
                    model=GROQ_WHISPER_MODEL,
                    language=LANGUAGE if LANGUAGE else None,
                    response_format="text",
                    temperature=0.0,
                    prompt="Use proper punctuation, capitalization, and complete sentences.",
                )
            text = self.clean_text(result if isinstance(result, str) else result.text)
            print(f"Transcribed: {text}")
            return text
        finally:
            os.unlink(temp_path)

    def _watchdog_timeout(self):
        if self.recording:
            print(f"Auto-stopping (max {MAX_RECORDING_SECONDS}s)")
            self.notify("Recording auto-stopped", urgency="normal")
            threading.Thread(target=self._process_recording, daemon=True).start()

    def _process_recording(self):
        if not self.processing_lock.acquire(blocking=False):
            return
        try:
            with self.lock:
                self.transcribing = True
            text = self.stop_recording()
            if text:
                if TRANSFORM_ENABLED:
                    self._transform_text(text)
                    self.notify("Typed!", urgency="low", timeout=1000)
                else:
                    self.type_text(text)
        except Exception as e:
            print(f"Error: {e}")
            self.notify(f"Error: {e}", urgency="critical")
        finally:
            with self.lock:
                self.transcribing = False
                if self.pending_start:
                    self._do_start_recording()
            self.processing_lock.release()

    def _force_reset(self):
        print("Resetting...")
        self.cancel_transform = True
        with self.lock:
            self.recording = False
            self.transcribing = False
            self.pending_start = False
            self.audio_data = []
            if self.watchdog_timer:
                self.watchdog_timer.cancel()
                self.watchdog_timer = None
            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None
        self.notify("Reset!", urgency="low", timeout=1000)

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        for filler in FILLERS:
            text = re.sub(rf"\b{re.escape(filler)}\b", "", text, flags=re.IGNORECASE)
        text = re.sub(r"([.!?])([A-Z])", r"\1 \2", text)
        text = re.sub(r",([A-Za-z])", r", \1", text)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            text = text[0].upper() + text[1:]
        text = re.sub(
            r"([.!?])\s+([a-z])", lambda m: m.group(1) + " " + m.group(2).upper(), text
        )
        text = re.sub(r"^[,.\s]+", "", text)
        text = re.sub(r"[,\s]+$", "", text)
        return text

    def type_text(self, text: str):
        if not text:
            return
        if (
            time.time() - self.last_typing_time < MULTI_TURN_SPACING_WINDOW
            and text[0] not in ".,!?:;)'\""
        ):
            text = " " + text
        try:
            subprocess.run(
                ["ydotool", "type", "-d", "0", "-H", "0", "--", text],
                check=True,
                capture_output=True,
            )
            self.last_typing_time = time.time()
            self.notify("Typed!", urgency="low", timeout=1000)
            print(f"Typed: {text}")
        except FileNotFoundError:
            self.notify("ydotool not found!", urgency="critical")
        except subprocess.CalledProcessError:
            self.notify("Failed to type", urgency="critical")

    def _type_chunk(self, text: str):
        if not text:
            return
        if self.transform_first_chunk:
            self.transform_first_chunk = False
            if (
                time.time() - self.last_typing_time < MULTI_TURN_SPACING_WINDOW
                and text[0] not in ".,!?:;)'\""
            ):
                text = " " + text
        try:
            subprocess.run(
                ["ydotool", "type", "-d", "0", "-H", "0", "--", text],
                check=True,
                capture_output=True,
            )
            self.last_typing_time = time.time()
        except Exception:
            pass

    def _stream_transform(self, stream_iter, get_content):
        """Common streaming logic for transform backends."""
        self.cancel_transform = False
        self.transform_first_chunk = True
        result = ""
        buffer = ""

        for item in stream_iter:
            if self.cancel_transform or self.shutdown_requested:
                print("Transform cancelled")
                break
            content = get_content(item)
            if content:
                result += content
                buffer += content
                if buffer and buffer[-1] in " .,!?\n:;":
                    self._type_chunk(buffer)
                    buffer = ""

        if buffer and not self.cancel_transform:
            self._type_chunk(buffer)
        return result

    def _transform_text(self, text: str) -> str:
        if not TRANSFORM_ENABLED or not text:
            return text
        print("Transforming...")
        prompt = TRANSFORM_PROMPT.format(text=text)
        try:
            if TRANSFORM_BACKEND == "groq":
                return self._transform_with_groq(prompt)
            elif TRANSFORM_BACKEND == "ollama":
                return self._transform_with_ollama(prompt)
            return text
        except Exception as e:
            print(f"Transform error: {e}")
            self.notify(f"Transform error: {e}", urgency="critical")
            return text

    def _transform_with_groq(self, prompt: str) -> str:
        from groq import Groq

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set")

        client = Groq(api_key=api_key)
        stream = client.chat.completions.create(
            model=TRANSFORM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            max_tokens=500,
            temperature=0.3,
        )
        result = self._stream_transform(stream, lambda c: c.choices[0].delta.content)
        print(f"Transformed: {result}")
        return result

    def _transform_with_ollama(self, prompt: str) -> str:
        import requests

        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": TRANSFORM_MODEL, "prompt": prompt, "stream": True},
                stream=True,
                timeout=30,
            )
            response.raise_for_status()

            def get_content(line):
                if line:
                    data = json.loads(line)
                    return data.get("response", "")
                return ""

            result = self._stream_transform(response.iter_lines(), get_content)
            print(f"Transformed: {result}")
            return result
        except Exception as e:
            raise Exception(f"Ollama error: {e}")

    def handle_command(self, command: str) -> str:
        command = command.strip().lower()
        if command == "start":
            self.start_recording()
            return "ok"
        elif command == "stop":
            threading.Thread(target=self._process_recording, daemon=True).start()
            return "ok"
        elif command == "reset":
            self._force_reset()
            return "ok"
        elif command == "status":
            if self.recording:
                return "recording"
            elif self.transcribing:
                return "transcribing"
            return "idle"
        elif command == "ping":
            return "pong"
        return f"unknown: {command}"

    def run_server(self):
        socket_path = Path(SOCKET_PATH)
        if socket_path.exists():
            socket_path.unlink()

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(SOCKET_PATH)
        server.listen(5)
        os.chmod(SOCKET_PATH, 0o666)
        print(f"Listening on {SOCKET_PATH}")

        try:
            while True:
                conn, _ = server.accept()
                try:
                    data = conn.recv(1024).decode("utf-8")
                    if data:
                        conn.send(self.handle_command(data).encode("utf-8"))
                except Exception as e:
                    print(f"Connection error: {e}")
                finally:
                    conn.close()
        finally:
            server.close()
            socket_path.unlink(missing_ok=True)


daemon = None


def signal_handler(signum, frame):
    global daemon
    print("\nShutting down...")
    if daemon:
        daemon.shutdown_requested = True
        daemon.cancel_transform = True
    Path(SOCKET_PATH).unlink(missing_ok=True)
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    daemon = ArchWhisper()
    daemon.load_model()
    daemon.run_server()
