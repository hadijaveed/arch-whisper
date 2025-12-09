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

# Install system dependencies
echo "Installing system dependencies..."
sudo pacman -S --needed --noconfirm wtype libnotify python

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

# Add Hyprland bindings
echo ""
echo "Configuring Hyprland bindings..."
if [ -f "$HYPRLAND_BINDINGS" ]; then
    if ! grep -q "arch-whisper" "$HYPRLAND_BINDINGS"; then
        cat >> "$HYPRLAND_BINDINGS" << EOF

# arch-whisper voice dictation (Super+Z: hold to record, release to transcribe)
bindd = SUPER, Z, Start voice dictation, exec, $SCRIPT_DIR/arch_whisper_client.py start
bindr = SUPER, Z, exec, $SCRIPT_DIR/arch_whisper_client.py stop
EOF
        echo "Added bindings to $HYPRLAND_BINDINGS"
    else
        echo "Bindings already exist in $HYPRLAND_BINDINGS"
    fi
else
    echo "Warning: $HYPRLAND_BINDINGS not found."
    echo "Add these bindings manually:"
    echo ""
    echo "bindd = SUPER, Z, Start voice dictation, exec, $SCRIPT_DIR/arch_whisper_client.py start"
    echo "bindr = SUPER, Z, exec, $SCRIPT_DIR/arch_whisper_client.py stop"
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
echo "  Press and hold Super+Z to record"
echo "  Release Super+Z to transcribe and type"
echo ""
echo "Check status:"
echo "  systemctl --user status arch-whisper"
echo "  journalctl --user -u arch-whisper -f"
