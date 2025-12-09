#!/bin/bash
# arch-whisper installation script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HYPRLAND_BINDINGS="$HOME/.config/hypr/bindings.conf"

echo "=== arch-whisper installer ==="
echo ""

# Check if running on Arch
if ! command -v pacman &> /dev/null; then
    echo "Warning: pacman not found. This script is designed for Arch Linux."
    echo "You may need to install dependencies manually."
fi

# Configure keyboard shortcut
echo "Configure keyboard shortcut for voice dictation"
echo "Default: Super+Z (hold to record, release to transcribe)"
echo ""
read -p "Modifier key (SUPER/ALT/CTRL/CTRL SHIFT) [SUPER]: " KEYBIND_MOD
KEYBIND_MOD=${KEYBIND_MOD:-SUPER}
read -p "Key [Z]: " KEYBIND_KEY
KEYBIND_KEY=${KEYBIND_KEY:-Z}

echo ""
echo "Using keyboard shortcut: $KEYBIND_MOD + $KEYBIND_KEY"
echo ""

# Update config.py with user's keybinding choice
sed -i "s/^KEYBIND_MOD = .*/KEYBIND_MOD = \"$KEYBIND_MOD\"/" "$SCRIPT_DIR/config.py"
sed -i "s/^KEYBIND_KEY = .*/KEYBIND_KEY = \"$KEYBIND_KEY\"/" "$SCRIPT_DIR/config.py"

# Install system dependencies
echo "Installing system dependencies..."
sudo pacman -S --needed --noconfirm libnotify python ydotool

# Create virtual environment with Python 3.13 (faster-whisper not compatible with 3.14 yet)
echo ""
echo "Creating Python virtual environment..."
cd "$SCRIPT_DIR"
/usr/bin/python3.13 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Make scripts executable
echo ""
echo "Making scripts executable..."
chmod +x arch_whisper.py
chmod +x arch_whisper_client.py

# Install systemd service
echo ""
echo "Installing systemd user service..."
mkdir -p "$HOME/.config/systemd/user"

cat > "$HOME/.config/systemd/user/arch-whisper.service" << EOF
[Unit]
Description=arch-whisper voice dictation daemon
After=graphical-session.target

[Service]
Type=simple
ExecStart=$SCRIPT_DIR/.venv/bin/python $SCRIPT_DIR/arch_whisper.py
Restart=on-failure
RestartSec=5
Environment=XDG_RUNTIME_DIR=/run/user/%U

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable arch-whisper.service

# Enable ydotool daemon (required for ydotool to work)
echo ""
echo "Enabling ydotool daemon..."
systemctl --user enable --now ydotool

# Add Hyprland bindings
echo ""
echo "Configuring Hyprland bindings..."
if [ -f "$HYPRLAND_BINDINGS" ]; then
    if ! grep -q "arch-whisper" "$HYPRLAND_BINDINGS"; then
        cat >> "$HYPRLAND_BINDINGS" << EOF

# arch-whisper voice dictation ($KEYBIND_MOD+$KEYBIND_KEY: hold to record, release to transcribe)
bindd = $KEYBIND_MOD, $KEYBIND_KEY, Start voice dictation, exec, $SCRIPT_DIR/arch_whisper_client.py start
bindr = $KEYBIND_MOD, $KEYBIND_KEY, exec, $SCRIPT_DIR/arch_whisper_client.py stop
EOF
        echo "Added bindings to $HYPRLAND_BINDINGS"
    else
        echo "Bindings already exist in $HYPRLAND_BINDINGS"
        echo "To update the keybinding, edit $HYPRLAND_BINDINGS manually"
    fi
else
    echo "Warning: $HYPRLAND_BINDINGS not found."
    echo "Add these bindings manually to your Hyprland config:"
    echo ""
    echo "bindd = $KEYBIND_MOD, $KEYBIND_KEY, Start voice dictation, exec, $SCRIPT_DIR/arch_whisper_client.py start"
    echo "bindr = $KEYBIND_MOD, $KEYBIND_KEY, exec, $SCRIPT_DIR/arch_whisper_client.py stop"
fi

echo ""
echo "=== Installation complete! ==="
echo ""
echo "To start arch-whisper:"
echo "  systemctl --user start arch-whisper"
echo ""
echo "To reload Hyprland config:"
echo "  hyprctl reload"
echo ""
echo "Usage:"
echo "  Press and hold $KEYBIND_MOD+$KEYBIND_KEY to record"
echo "  Release $KEYBIND_MOD+$KEYBIND_KEY to transcribe and type"
echo ""
echo "Configuration:"
echo "  Edit config.py to change model, language, backend, or filler words"
echo "  Edit ~/.config/hypr/bindings.conf to change the keybinding"
echo ""
echo "Check status:"
echo "  systemctl --user status arch-whisper"
echo "  journalctl --user -u arch-whisper -f"
echo ""
echo "=== Optional: Groq Cloud API ==="
echo "For faster transcription using Groq cloud:"
echo "  1. Get API key from https://console.groq.com/keys"
echo "  2. Add to ~/.bashrc: export GROQ_API_KEY='your_key_here'"
echo "  3. Edit config.py: TRANSCRIPTION_BACKEND = \"groq\""
echo ""
echo "=== Optional: Local LLM Grammar Correction (Ollama) ==="
echo "For local grammar correction without cloud:"
echo "  1. Install Ollama: curl -fsSL https://ollama.com/install.sh | sh"
echo "  2. Pull a small model: ollama pull qwen2.5:3b"
echo "  3. Edit config.py:"
echo "     TRANSFORM_ENABLED = True"
echo "     TRANSFORM_BACKEND = \"ollama\""
echo "     TRANSFORM_MODEL = \"qwen2.5:3b\""
