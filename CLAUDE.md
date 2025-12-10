# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

arch-whisper is a voice dictation daemon for Linux + Hyprland. Push-to-talk transcription using faster-whisper (local) or Groq API (cloud), typing results via ydotool.

## Architecture

```
Hyprland keybinding (bindd/bindr)
        │
        ▼
arch_whisper.py start/stop ──── Unix socket ────► arch_whisper.py (daemon)
        │                                                │
        │                                                ├── faster-whisper / Groq (transcription)
        │                                                ├── sounddevice (audio recording)
        │                                                ├── LLM transform (optional)
        │                                                └── ydotool (text injection)
        ▼
/tmp/arch-whisper.sock
```

**Single-file design**: `arch_whisper.py` handles both daemon mode (no args) and client mode (with args like `start`, `stop`, `ping`). Client mode check happens BEFORE heavy imports to avoid loading numpy/scipy for simple commands.

```python
# Client mode - early exit before heavy imports
CLIENT_COMMANDS = {"start", "stop", "status", "ping", "reset"}
if len(sys.argv) > 1 and sys.argv[1] in CLIENT_COMMANDS:
    # ... send command via socket ...
    sys.exit(0)

# Daemon mode - import heavy dependencies
import numpy as np
import sounddevice as sd
```

## Files

| File | Purpose |
|------|---------|
| `arch_whisper.py` | Daemon + CLI (single file) |
| `config.py` | All user settings |
| `install.sh` | Automated installer |
| `tests/test_arch_whisper.py` | pytest test suite (52 tests) |

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
./arch_whisper.py ping
./arch_whisper.py status
./arch_whisper.py reset

# Reload Hyprland after binding changes
hyprctl reload
```

## Testing

```bash
# Activate venv first
source .venv/bin/activate

# Run all tests
pytest tests/ -v

# Run a single test
pytest tests/test_arch_whisper.py::TestCleanText::test_empty_string -v

# Run a test class
pytest tests/test_arch_whisper.py::TestHandleCommand -v
```

## Development

```bash
# Activate venv
source .venv/bin/activate

# Run daemon directly (for debugging)
python arch_whisper.py

# Test client commands
python arch_whisper.py start
python arch_whisper.py stop
python arch_whisper.py ping
```

## Key Implementation Details

- Python 3.13 required (faster-whisper incompatible with 3.14)
- Unix socket at `/tmp/arch-whisper.sock` for IPC
- Audio: 16kHz sample rate (Whisper requirement), mono channel
- VAD filter with 500ms silence threshold
- Minimum 0.3s audio required for transcription
- Thread-safe with `threading.Lock` for recording state
- `pending_start` flag handles rapid key presses during transcription
- Transform streaming types text as LLM generates it (chunk by punctuation)

## Important Patterns

**Linter compatibility**: The `# ruff: noqa: E402` comment is required to prevent formatters from moving imports to the top, which would break client mode.

**Multi-turn spacing**: If text is typed within 30 seconds of previous typing and doesn't start with punctuation, a space is prepended automatically.
