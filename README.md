# arch-whisper

Local voice dictation for Arch Linux + Hyprland. Hold a key to record, release to transcribe and type.

Inspired by [Whispr Flow](https://wisprflow.ai/) — but free, local, and private. No cloud, no subscription, no data leaves your machine.

Built in 15 minutes with [Claude Code](https://claude.ai/code) (Opus 4.5).

## Features

- **Push-to-talk**: Hold your shortcut key to record, release to transcribe
- **Instant response**: Whisper model stays loaded in memory
- **Works anywhere**: Types into any Wayland application
- **100% local**: Runs entirely offline after initial model download
- **Cloud option**: Use Groq API for faster transcription (optional)
- **Grammar correction**: Optional LLM post-processing with streaming output
- **Smart cleanup**: Automatically removes filler words (um, uh, like, etc.)
- **Visual feedback**: Desktop notifications show recording state
- **Configurable**: Change keybinding, model size, language, and more

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/arch-whisper.git
cd arch-whisper
./install.sh
systemctl --user start arch-whisper && hyprctl reload
```

That's it! Press **Super+Z** (or your chosen shortcut) to dictate.

## Requirements

- **Arch Linux** (or Arch-based distro)
- **Hyprland** compositor (tested with [Omarchy](https://omakub.org/omarchy))
- **Python 3.13** (not 3.14 — faster-whisper compatibility)
- **Working microphone**

## Installation

### Automatic (recommended)

```bash
./install.sh
```

The installer will:
1. Ask for your preferred keyboard shortcut (default: Super+Z)
2. Install system dependencies (wtype, libnotify)
3. Create Python virtual environment
4. Install Python packages (faster-whisper, sounddevice, numpy)
5. Set up systemd user service
6. Add Hyprland keybindings

### Manual

1. Install system packages:
   ```bash
   sudo pacman -S wtype libnotify python
   ```

2. Create virtual environment:
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Make scripts executable:
   ```bash
   chmod +x arch_whisper.py arch_whisper_client.py
   ```

4. Create systemd service at `~/.config/systemd/user/arch-whisper.service`:
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

5. Enable and start service:
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now arch-whisper
   ```

6. Add to `~/.config/hypr/bindings.conf` or add your preferred key-bindings:
   ```
   bindd = SUPER, Z, Start voice dictation, exec, /path/to/arch_whisper_client.py start
   bindr = SUPER, Z, exec, /path/to/arch_whisper_client.py stop
   ```

7. Reload Hyprland:
   ```bash
   hyprctl reload
   ```

## Usage

1. **Press and hold** your shortcut key (default: Super+Z)
2. **Speak** — you'll see a "Recording..." notification
3. **Release** the key — text is transcribed and typed into the active window

### Commands

```bash
# Check daemon status
./arch_whisper_client.py status

# Test connection
./arch_whisper_client.py ping

# View logs
journalctl --user -u arch-whisper -f

# Restart after config changes
systemctl --user restart arch-whisper
```

## Configuration

All settings are in `config.py`. Edit and restart the service to apply changes.

### Change Keyboard Shortcut

1. Edit `config.py`:
   ```python
   KEYBIND_MOD = "ALT"      # Options: SUPER, ALT, CTRL, CTRL SHIFT
   KEYBIND_KEY = "D"        # Any single key
   ```

2. Update `~/.config/hypr/bindings.conf`:
   ```
   # Find and replace the arch-whisper lines:
   bindd = ALT, D, Start voice dictation, exec, /path/to/arch_whisper_client.py start
   bindr = ALT, D, exec, /path/to/arch_whisper_client.py stop
   ```

3. Reload Hyprland:
   ```bash
   hyprctl reload
   ```

### Change Whisper Model

Edit `config.py`:
```python
MODEL_SIZE = "base"  # Options: tiny, base, small, medium, large
# get decent latency and performance on small
```

| Model  | Size    | Speed    | Accuracy  | RAM Usage |
|--------|---------|----------|-----------|-----------|
| tiny   | ~75 MB  | Fastest  | Good      | ~1 GB     |
| base   | ~142 MB | Fast     | Better    | ~1 GB     |
| small  | ~466 MB | Medium   | Great     | ~2 GB     |
| medium | ~1.5 GB | Slow     | Excellent | ~5 GB     |
| large  | ~3 GB   | Slowest  | Best      | ~10 GB    |

Then restart:
```bash
systemctl --user restart arch-whisper
```

### Change Language

Edit `config.py`:
```python
LANGUAGE = "es"   # Spanish
LANGUAGE = "fr"   # French
LANGUAGE = "de"   # German
LANGUAGE = "zh"   # Chinese
LANGUAGE = "ja"   # Japanese
LANGUAGE = None   # Auto-detect (slower)
```

### Customize Filler Words

Edit the `FILLERS` list in `config.py`:
```python
FILLERS = [
    "um", "uh", "like", "you know",
    # Add your own...
]
```

## Groq Cloud API (Optional)

For faster transcription using Groq's cloud Whisper API instead of local processing:

### Setup

1. Get an API key from [console.groq.com/keys](https://console.groq.com/keys)

2. Add to your shell profile (`~/.bashrc` or `~/.zshrc`):
   ```bash
   export GROQ_API_KEY='gsk_your_key_here'
   ```

3. Edit `config.py`:
   ```python
   TRANSCRIPTION_BACKEND = "groq"  # Instead of "local"
   GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"  # Fast and cheap
   ```

4. Restart the service:
   ```bash
   systemctl --user restart arch-whisper
   ```

### Groq Whisper Models

| Model | Speed | Cost | Word Error Rate |
|-------|-------|------|-----------------|
| whisper-large-v3-turbo | 216x realtime | $0.04/hour | 12% |
| whisper-large-v3 | 164x realtime | $0.111/hour | 10.3% |

## Grammar Correction (Optional)

Enable LLM post-processing to fix grammar, punctuation, and capitalization. Text streams directly into your application as the LLM generates it.

### Using Groq LLM (Cloud)

1. Ensure `GROQ_API_KEY` is set (same key as transcription)

2. Edit `config.py`:
   ```python
   TRANSFORM_ENABLED = True
   TRANSFORM_BACKEND = "groq"
   TRANSFORM_MODEL = "llama-3.1-8b-instant"  # Fast and cheap
   ```

3. Restart the service

### Using Ollama (Local, Free)

For fully offline grammar correction:

1. Install Ollama:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. Pull a small model:
   ```bash
   ollama pull qwen2.5:3b   # ~3GB RAM, fast
   # or
   ollama pull phi3:mini    # ~4GB RAM, good quality
   ```

3. Edit `config.py`:
   ```python
   TRANSFORM_ENABLED = True
   TRANSFORM_BACKEND = "ollama"
   TRANSFORM_MODEL = "qwen2.5:3b"
   ```

4. Restart the service

### Transform Models

**Groq (cloud):**
| Model | Speed | Cost (per 1M tokens) |
|-------|-------|---------------------|
| llama-3.1-8b-instant | 560 tok/s | $0.05 in / $0.08 out |
| llama-3.3-70b-versatile | 280 tok/s | $0.59 in / $0.79 out |

**Ollama (local):**
| Model | RAM | Speed | Notes |
|-------|-----|-------|-------|
| qwen2.5:3b | ~3GB | Fast | Good for grammar |
| phi3:mini | ~4GB | Fast | Excellent quality |
| qwen2.5:7b | ~5GB | Medium | Better quality |

### Custom Transform Prompt

Edit `TRANSFORM_PROMPT` in `config.py` to customize how the LLM processes your text:
```python
TRANSFORM_PROMPT = """Fix grammar, spelling, and punctuation in the following transcribed speech.
Add proper capitalization and commas where needed.
Keep the original meaning and tone.
Only output the corrected text, nothing else.
Do not add any explanations or notes.

Text: {text}"""
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Hyprland                             │
│  Super+Z pressed  → exec arch_whisper_client.py start       │
│  Super+Z released → exec arch_whisper_client.py stop        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  arch_whisper_client.py                      │
│            Sends command via Unix socket                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   arch_whisper.py (daemon)                   │
│                                                              │
│  Audio Recording                                             │
│       │                                                      │
│       ▼                                                      │
│  Transcription (local faster-whisper OR Groq API)           │
│       │                                                      │
│       ▼                                                      │
│  Transform (optional: Groq LLM or Ollama, streaming)        │
│       │                                                      │
│       ▼                                                      │
│  wtype → types into active window                           │
└─────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Daemon not running

```bash
# Check status
systemctl --user status arch-whisper

# View logs
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

### wtype not working

```bash
# Check if installed
which wtype

# Test manually
wtype "hello world"
```

If wtype doesn't work, ensure you're running on Wayland:
```bash
echo $XDG_SESSION_TYPE  # Should print "wayland"
```

### Python version issues

faster-whisper requires Python ≤3.13. Check your version:
```bash
python --version
/usr/bin/python3.13 --version
```

### Model download fails

The model downloads on first use. If it fails:
```bash
# Check internet connection
# Try downloading manually
python -c "from faster_whisper import WhisperModel; WhisperModel('tiny')"
```

### Groq API errors

```bash
# Check API key is set
echo $GROQ_API_KEY

# Test API key
curl -X POST "https://api.groq.com/openai/v1/models" \
  -H "Authorization: Bearer $GROQ_API_KEY"
```

### Ollama not working

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Check model is pulled
ollama list
```

### Recording gets stuck

If the daemon gets stuck in recording mode:
```bash
# Force reset
./arch_whisper_client.py reset

# Or restart the service
systemctl --user restart arch-whisper
```

## Uninstall

```bash
# Stop and disable service
systemctl --user stop arch-whisper
systemctl --user disable arch-whisper

# Remove service file
rm ~/.config/systemd/user/arch-whisper.service
systemctl --user daemon-reload

# Remove Hyprland bindings (edit manually)
# Remove these lines from ~/.config/hypr/bindings.conf:
#   bindd = SUPER, Z, Start voice dictation, exec, ...
#   bindr = SUPER, Z, exec, ...

# Remove project folder
rm -rf /path/to/arch-whisper
```

## Credits

- Inspired by [Whispr Flow](https://wisprflow.ai/) — excellent Mac app, but why pay when you can run it locally?
- Hyprland setup: [Omarchy](https://omakub.org/omarchy) by DHH
- Speech-to-text: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) by SYSTRAN
- Built with [Claude Code](https://claude.ai/code) (Opus 4.5) in 15 minutes

## License

MIT
