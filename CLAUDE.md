# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

arch-whisper is a local voice dictation daemon for Arch Linux + Hyprland. It provides push-to-talk voice transcription using faster-whisper, typing the result into any Wayland application via wtype.

## Architecture

```
Hyprland keybinding (bindd/bindr)
        │
        ▼
arch_whisper_client.py ──── Unix socket ────► arch_whisper.py (daemon)
        │                                            │
        │                                            ├── faster-whisper (transcription)
        │                                            ├── sounddevice (audio recording)
        │                                            └── wtype (text injection)
        │
        ▼
/tmp/arch-whisper.sock
```

- **arch_whisper.py**: Main daemon that runs as a systemd user service. Loads Whisper model into memory, listens on Unix socket, records audio on "start", transcribes on "stop", types via wtype.
- **arch_whisper_client.py**: Lightweight client called by Hyprland keybindings. Sends commands (start/stop/status/ping) to daemon via Unix socket.
- **config.py**: All user-configurable settings (model size, language, keybinding, filler words).
- **install.sh**: Interactive installer that sets up venv, systemd service, and Hyprland bindings.

## Commands

```bash
# Service management
systemctl --user start arch-whisper
systemctl --user stop arch-whisper
systemctl --user restart arch-whisper   # Required after config.py changes
systemctl --user status arch-whisper

# View logs
journalctl --user -u arch-whisper -f

# Test daemon
./arch_whisper_client.py ping
./arch_whisper_client.py status

# Reload Hyprland after binding changes
hyprctl reload
```

## Development

```bash
# Activate venv
source .venv/bin/activate

# Run daemon directly (for debugging)
python arch_whisper.py

# Test client
python arch_whisper_client.py start
python arch_whisper_client.py stop
```

## Key Implementation Details

- Uses Python 3.13 (faster-whisper incompatible with 3.14)
- Unix socket at `/tmp/arch-whisper.sock` for IPC
- Audio: 16kHz sample rate (Whisper requirement), mono channel
- VAD filter enabled with 500ms silence threshold
- Minimum 0.3s audio required for transcription
- Thread-safe recording with `threading.Lock`
