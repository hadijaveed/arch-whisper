# arch-whisper

**Voice dictation for Linux that actually works.**

Hold a key, speak, release — your words appear instantly. No cloud required, no subscription, no data leaves your machine.

---

## Why arch-whisper?

I built this because existing voice dictation options on Linux were either:
- **Too heavy** — bloated apps with unnecessary features
- **Didn't work** — broken on Wayland, incompatible with modern compositors
- **Cloud-only** — privacy concerns, subscription fees, latency

Inspired by [Whispr Flow](https://wisprflow.ai/) (excellent Mac app), but free and runs locally.

**Tested on Arch Linux with [Omarchy](https://github.com/basecamp/omarchy)** — works on any Linux distro with Hyprland.

---

## Quick Start

> **Keybinding:** Default is `Super+Z`. The installer will prompt you to choose your preferred shortcut.

```bash
git clone https://github.com/YOUR_USERNAME/arch-whisper.git
cd arch-whisper
./install.sh
```

When prompted, choose your keybinding (or press Enter for default):
```
Configure keyboard shortcut for voice dictation
Default: Super+Z (hold to record, release to transcribe)

Modifier key (SUPER/ALT/CTRL/CTRL SHIFT) [SUPER]:
Key [Z]:
```

Then start the service:
```bash
systemctl --user start arch-whisper && hyprctl reload
```

**That's it!** Hold your shortcut, speak, release — text appears.

---

## Features

| Feature | Description |
|---------|-------------|
| **Push-to-talk** | Hold to record, release to transcribe and type |
| **Works everywhere** | Types into any application (uses kernel-level input) |
| **Instant response** | Whisper model stays loaded in memory |
| **100% local** | Runs entirely offline after model download |
| **Cloud option** | Optional Groq API for faster transcription |
| **Grammar correction** | Optional LLM post-processing (local or cloud) |
| **Smart cleanup** | Automatically removes filler words (um, uh, like) |
| **Visual feedback** | Desktop notifications show recording state |

---

## Requirements

- **Linux** — Any distro (tested on Arch Linux / Omarchy)
- **Hyprland** — Wayland compositor (bindings can be adapted for others)
- **Python 3.13** — Required (faster-whisper not compatible with 3.14 yet)
- **Microphone** — Working audio input

---

## Installation

### Automatic (Recommended)

```bash
./install.sh
```

The installer will:
1. Ask for your keyboard shortcut preference
2. Install system dependencies (`ydotool`, `libnotify`)
3. Create Python virtual environment
4. Install Python packages (faster-whisper, sounddevice, numpy)
5. Set up systemd user service
6. Configure Hyprland keybindings
7. Enable the ydotool daemon

### Manual Installation

<details>
<summary>Click to expand manual steps</summary>

1. **Install system packages:**

   Arch Linux:
   ```bash
   sudo pacman -S ydotool libnotify python
   ```

   Ubuntu/Debian:
   ```bash
   sudo apt install ydotool libnotify-bin python3
   ```

   Fedora:
   ```bash
   sudo dnf install ydotool libnotify python3
   ```

2. **Create virtual environment:**
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Make scripts executable:**
   ```bash
   chmod +x arch_whisper.py arch_whisper_client.py
   ```

4. **Create systemd service** at `~/.config/systemd/user/arch-whisper.service`:
   ```ini
   [Unit]
   Description=arch-whisper voice dictation daemon
   After=graphical-session.target

   [Service]
   Type=simple
   ExecStart=/path/to/arch-whisper/.venv/bin/python /path/to/arch-whisper/arch_whisper.py
   Restart=on-failure
   RestartSec=5
   Environment=XDG_RUNTIME_DIR=/run/user/%U

   [Install]
   WantedBy=default.target
   ```

5. **Enable services:**
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now arch-whisper
   systemctl --user enable --now ydotool
   ```

6. **Add Hyprland bindings** to `~/.config/hypr/bindings.conf`:
   ```
   bindd = SUPER, Z, Start voice dictation, exec, /path/to/arch_whisper_client.py start
   bindr = SUPER, Z, exec, /path/to/arch_whisper_client.py stop
   ```

7. **Reload Hyprland:**
   ```bash
   hyprctl reload
   ```

</details>

---

## Configuration

All settings are in `config.py`.

> **Important:** After any configuration change, restart the service:
> ```bash
> systemctl --user restart arch-whisper
> ```

### Keyboard Shortcut

To change after installation, edit `~/.config/hypr/bindings.conf`:
```
bindd = ALT, D, Start voice dictation, exec, /path/to/arch_whisper_client.py start
bindr = ALT, D, exec, /path/to/arch_whisper_client.py stop
```

Then reload: `hyprctl reload`

### Whisper Model

Edit `config.py`:
```python
MODEL_SIZE = "base"  # Options: tiny, base, small, medium, large
```

| Model | Download | Speed | Accuracy | RAM |
|-------|----------|-------|----------|-----|
| tiny | ~75 MB | Fastest | Good | ~1 GB |
| base | ~142 MB | Fast | Better | ~1 GB |
| small | ~466 MB | Medium | Great | ~2 GB |
| medium | ~1.5 GB | Slow | Excellent | ~5 GB |
| large | ~3 GB | Slowest | Best | ~10 GB |

### Language

```python
LANGUAGE = "en"   # English (default)
LANGUAGE = "es"   # Spanish
LANGUAGE = "fr"   # French
LANGUAGE = "de"   # German
LANGUAGE = None   # Auto-detect (slower)
```

### Groq Cloud API (Optional)

For faster transcription using Groq's cloud API:

1. Get API key from [console.groq.com/keys](https://console.groq.com/keys)

2. Add to `~/.bashrc`:
   ```bash
   export GROQ_API_KEY='gsk_your_key_here'
   ```

3. Edit `config.py`:
   ```python
   TRANSCRIPTION_BACKEND = "groq"
   GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"  # Fast and cheap
   ```

4. Restart service

| Model | Speed | Cost |
|-------|-------|------|
| whisper-large-v3-turbo | 216x realtime | $0.04/hour |
| whisper-large-v3 | 164x realtime | $0.111/hour |

### Grammar Correction (Optional)

Fix grammar, punctuation, and capitalization with LLM post-processing.

**Using Groq (cloud):**
```python
TRANSFORM_ENABLED = True
TRANSFORM_BACKEND = "groq"
TRANSFORM_MODEL = "llama-3.1-8b-instant"
```

**Using Ollama (local, free):**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull qwen2.5:3b
```

```python
TRANSFORM_ENABLED = True
TRANSFORM_BACKEND = "ollama"
TRANSFORM_MODEL = "qwen2.5:3b"
```

### Filler Words

Customize which words are automatically removed:
```python
FILLERS = [
    "um", "uh", "like", "you know",
    "basically", "actually", "i mean",
    # Add your own...
]
```

---

## Usage

### Basic Usage

1. **Press and hold** your shortcut key (default: `Super+Z`)
2. **Speak** — you'll see a "Recording..." notification
3. **Release** the key — text is transcribed and typed into the active window

### Commands

```bash
# Check if daemon is running
./arch_whisper_client.py ping

# View current state (idle/recording/transcribing)
./arch_whisper_client.py status

# Force reset if stuck
./arch_whisper_client.py reset
```

### Service Management

```bash
# Start the service
systemctl --user start arch-whisper

# Stop the service
systemctl --user stop arch-whisper

# Restart (required after config changes)
systemctl --user restart arch-whisper

# View logs
journalctl --user -u arch-whisper -f

# Check status
systemctl --user status arch-whisper
```

---

## Known Issues

### Recording occasionally gets stuck on release

Sometimes when you release the key, text doesn't type immediately. The recording completed successfully, but the stop event wasn't processed.

**Workaround:** Press your keybind again (e.g., `Super+Z`) — the text will type on the second release.

This is a known issue we're actively debugging. It appears to be related to Hyprland's key release event timing.

---

## Troubleshooting

### Daemon not running

```bash
# Check status
systemctl --user status arch-whisper

# View logs for errors
journalctl --user -u arch-whisper -f

# Restart
systemctl --user restart arch-whisper
```

### No audio / wrong microphone

```bash
# List audio devices
python -c "import sounddevice; print(sounddevice.query_devices())"

# Test recording
arecord -d 3 test.wav && aplay test.wav
```

### Text not typing

```bash
# Check ydotool daemon is running
systemctl --user status ydotool

# Start if not running
systemctl --user start ydotool

# Test ydotool manually
ydotool type "hello world"
```

### Recording gets stuck

```bash
# Force reset
./arch_whisper_client.py reset

# Or restart service
systemctl --user restart arch-whisper
```

### Groq API errors

```bash
# Check API key is set
echo $GROQ_API_KEY

# Verify it's exported in your shell config
grep GROQ_API_KEY ~/.bashrc
```

### Ollama not working

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Verify model is installed
ollama list
```

### Python version issues

faster-whisper requires Python 3.13 or earlier:
```bash
python --version
/usr/bin/python3.13 --version
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Hyprland                            │
│  Super+Z pressed  → exec arch_whisper_client.py start       │
│  Super+Z released → exec arch_whisper_client.py stop        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  arch_whisper_client.py                     │
│            Lightweight client, sends commands               │
│                   via Unix socket                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    /tmp/arch-whisper.sock
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              arch_whisper.py (daemon)                       │
│                                                             │
│  ┌─────────────┐    ┌──────────────────┐    ┌───────────┐  │
│  │   Record    │ →  │   Transcribe     │ →  │  Transform │  │
│  │ (sounddevice)│    │ (whisper/groq)   │    │ (optional) │  │
│  └─────────────┘    └──────────────────┘    └───────────┘  │
│                                                     │       │
│                                                     ▼       │
│                                              ┌───────────┐  │
│                                              │   Type    │  │
│                                              │ (ydotool) │  │
│                                              └───────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Files

| File | Purpose |
|------|---------|
| `arch_whisper.py` | Main daemon — loads model, records, transcribes, types |
| `arch_whisper_client.py` | CLI client — sends commands to daemon |
| `config.py` | All user settings |
| `install.sh` | Automated installer |

### How It Works

1. **Daemon starts** — loads Whisper model into memory, listens on Unix socket
2. **Key pressed** — Hyprland runs client with "start", daemon begins recording
3. **Key released** — Hyprland runs client with "stop", daemon stops recording
4. **Transcription** — audio sent to Whisper (local) or Groq API (cloud)
5. **Transform** — optional LLM grammar correction with streaming output
6. **Type** — ydotool injects keystrokes at kernel level (works everywhere)

---

## Uninstall

```bash
# Stop and disable service
systemctl --user stop arch-whisper
systemctl --user disable arch-whisper

# Remove service file
rm ~/.config/systemd/user/arch-whisper.service
systemctl --user daemon-reload

# Remove Hyprland bindings
# Edit ~/.config/hypr/bindings.conf and remove arch-whisper lines

# Remove project folder
rm -rf /path/to/arch-whisper
```

---

## Credits

- Inspired by [Whispr Flow](https://wisprflow.ai/)
- Hyprland setup: [Omarchy](https://github.com/basecamp/omarchy) by DHH
- Speech-to-text: [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- Built with [Claude Code](https://claude.ai/code) (Opus 4.5)

## License

MIT
