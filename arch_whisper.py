#!/usr/bin/env python3
"""
arch-whisper: Local voice dictation daemon for Arch Linux + Hyprland
Press Super+Z to record, release to transcribe and type.
"""

import concurrent.futures
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

# Import configuration from config.py
from config import MODEL_SIZE, COMPUTE_TYPE, LANGUAGE, SAMPLE_RATE, FILLERS

SOCKET_PATH = "/tmp/arch-whisper.sock"
CHANNELS = 1
MAX_RECORDING_SECONDS = 60  # Auto-stop recording after this duration
TRANSCRIPTION_TIMEOUT = 10  # Timeout for transcription in seconds


class ArchWhisper:
    def __init__(self):
        self.model = None
        self.recording = False
        self.transcribing = False
        self.audio_data = []
        self.stream = None
        self.lock = threading.Lock()
        self.watchdog_timer = None

    def load_model(self):
        """Load the Whisper model into memory."""
        print(f"Loading faster-whisper model '{MODEL_SIZE}' with {COMPUTE_TYPE}...")
        self.model = WhisperModel(MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE)
        print("Model loaded successfully!")

    def notify(self, message: str, urgency: str = "normal", timeout: int = 1500):
        """Send a desktop notification."""
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
        except Exception as e:
            print(f"Notification error: {e}")

    def audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream - collect audio chunks."""
        if status:
            print(f"Audio status: {status}")
        if self.recording:
            self.audio_data.append(indata.copy())

    def start_recording(self):
        """Start recording audio from the microphone."""
        with self.lock:
            if self.recording:
                return

            # Cancel any pending watchdog timer
            if self.watchdog_timer:
                self.watchdog_timer.cancel()
                self.watchdog_timer = None

            self.recording = True
            self.audio_data = []

            # Start audio stream
            self.stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=np.float32,
                callback=self.audio_callback,
                blocksize=1024,
            )
            self.stream.start()

            # Start watchdog timer to auto-stop after max duration
            self.watchdog_timer = threading.Timer(
                MAX_RECORDING_SECONDS, self._watchdog_timeout
            )
            self.watchdog_timer.start()

        self.notify("Recording...", urgency="low", timeout=10000)
        print("Recording started...")

    def stop_recording(self) -> str:
        """Stop recording and return transcribed text."""
        with self.lock:
            if not self.recording:
                return ""

            self.recording = False

            # Cancel watchdog timer
            if self.watchdog_timer:
                self.watchdog_timer.cancel()
                self.watchdog_timer = None

            # Stop and close audio stream
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None

            # Get recorded audio
            if not self.audio_data:
                print("No audio recorded")
                return ""

            audio = np.concatenate(self.audio_data, axis=0).flatten()
            self.audio_data = []

        print(f"Recording stopped. Audio length: {len(audio) / SAMPLE_RATE:.2f}s")

        # Check minimum audio length
        if len(audio) < SAMPLE_RATE * 0.3:  # Less than 0.3 seconds
            print("Audio too short, skipping transcription")
            return ""

        # Transcribe with timeout
        print("Transcribing...")
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._transcribe_audio, audio)
                text = future.result(timeout=TRANSCRIPTION_TIMEOUT)
                return text
        except concurrent.futures.TimeoutError:
            print(f"Transcription timeout after {TRANSCRIPTION_TIMEOUT}s!")
            self.notify("Transcription timed out", urgency="critical")
            return ""
        except Exception as e:
            print(f"Transcription error: {e}")
            self.notify(f"Transcription error: {e}", urgency="critical")
            return ""

    def _transcribe_audio(self, audio) -> str:
        """Transcribe audio using Whisper model."""
        segments, info = self.model.transcribe(
            audio,
            language=LANGUAGE,
            vad_filter=True,  # Filter out silence
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        text = " ".join([segment.text for segment in segments])
        text = self.clean_text(text)

        print(f"Transcribed: {text}")
        return text

    def _watchdog_timeout(self):
        """Auto-stop recording if max duration exceeded."""
        if self.recording:
            print(f"Recording exceeded {MAX_RECORDING_SECONDS}s, auto-stopping")
            self.notify("Recording auto-stopped (max duration)", urgency="normal")
            threading.Thread(target=self._process_recording, daemon=True).start()

    def _process_recording(self):
        """Process recording in background thread."""
        self.transcribing = True
        try:
            text = self.stop_recording()
            if text:
                self.type_text(text)
        finally:
            self.transcribing = False

    def _force_reset(self):
        """Force reset all state."""
        print("Force resetting state...")
        with self.lock:
            self.recording = False
            self.transcribing = False
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
        """Remove filler words and clean up text."""
        if not text:
            return ""

        # Remove filler words
        for filler in FILLERS:
            # Word boundary matching for fillers
            pattern = rf"\b{re.escape(filler)}\b"
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        # Remove leading/trailing punctuation artifacts
        text = re.sub(r"^[,.\s]+", "", text)
        text = re.sub(r"[,\s]+$", "", text)

        return text

    def type_text(self, text: str):
        """Type text into the active window using wtype."""
        if not text:
            return

        try:
            # Use wtype for Wayland
            subprocess.run(["wtype", "--", text], check=True, capture_output=True)
            self.notify("Typed!", urgency="low", timeout=1000)
            print(f"Typed: {text}")
        except subprocess.CalledProcessError as e:
            print(f"wtype error: {e}")
            self.notify("Failed to type text", urgency="critical")
        except FileNotFoundError:
            print("wtype not found. Please install: sudo pacman -S wtype")
            self.notify("wtype not found!", urgency="critical")

    def handle_command(self, command: str) -> str:
        """Handle a command from the client."""
        command = command.strip().lower()

        if command == "start":
            self.start_recording()
            return "ok"
        elif command == "stop":
            # Process recording in background thread so socket stays responsive
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
            else:
                return "idle"
        elif command == "ping":
            return "pong"
        else:
            return f"unknown command: {command}"

    def run_server(self):
        """Run the Unix socket server."""
        # Remove existing socket
        socket_path = Path(SOCKET_PATH)
        if socket_path.exists():
            socket_path.unlink()

        # Create socket
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(SOCKET_PATH)
        server.listen(5)  # Allow multiple pending connections

        # Make socket accessible
        os.chmod(SOCKET_PATH, 0o666)

        print(f"Listening on {SOCKET_PATH}")

        try:
            while True:
                conn, _ = server.accept()
                try:
                    data = conn.recv(1024).decode("utf-8")
                    if data:
                        response = self.handle_command(data)
                        conn.send(response.encode("utf-8"))
                except Exception as e:
                    print(f"Connection error: {e}")
                finally:
                    conn.close()
        finally:
            server.close()
            socket_path.unlink(missing_ok=True)


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print("\nShutting down...")
    socket_path = Path(SOCKET_PATH)
    socket_path.unlink(missing_ok=True)
    sys.exit(0)


def main():
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and run daemon
    daemon = ArchWhisper()
    daemon.load_model()
    daemon.run_server()


if __name__ == "__main__":
    main()
