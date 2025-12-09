"""
arch-whisper configuration
Edit these values to customize your setup, then restart the service:
    systemctl --user restart arch-whisper
"""

# =============================================================================
# KEYBOARD SHORTCUT (Hyprland format)
# =============================================================================
# These values are used by install.sh to set up Hyprland bindings.
# To change after installation, edit ~/.config/hypr/bindings.conf directly.
#
# Examples:
#   KEYBIND_MOD = "SUPER"       KEYBIND_KEY = "Z"     → Super+Z
#   KEYBIND_MOD = "ALT"         KEYBIND_KEY = "D"     → Alt+D
#   KEYBIND_MOD = "CTRL SHIFT"  KEYBIND_KEY = "V"     → Ctrl+Shift+V

KEYBIND_MOD = "SUPER"
KEYBIND_KEY = "Z"

# =============================================================================
# WHISPER MODEL SETTINGS
# =============================================================================
# Model sizes (download size → RAM usage):
#   tiny   (~75 MB)  - Fastest, good accuracy, best for most users
#   base   (~142 MB) - Fast, better accuracy
#   small  (~466 MB) - Medium speed, great accuracy
#   medium (~1.5 GB) - Slow, excellent accuracy
#   large  (~3 GB)   - Slowest, best accuracy (requires lots of RAM)

MODEL_SIZE = "base"

# Compute type:
#   "int8"    - Best for CPU (faster, less memory)
#   "float16" - Best for GPU with CUDA
#   "float32" - Fallback (slower)

COMPUTE_TYPE = "int8"

# Language code (ISO 639-1):
#   "en" - English
#   "es" - Spanish
#   "fr" - French
#   "de" - German
#   "zh" - Chinese
#   "ja" - Japanese
#   None - Auto-detect (slower, but works with any language)

LANGUAGE = "en"

# =============================================================================
# AUDIO SETTINGS
# =============================================================================
# Sample rate - DO NOT CHANGE (Whisper requires 16kHz)
SAMPLE_RATE = 16000

# =============================================================================
# TEXT PROCESSING
# =============================================================================
# Filler words to automatically remove from transcriptions.
# Add or remove words as needed for your speaking style.

FILLERS = [
    "um",
    "uh",
    "uhh",
    "umm",
    "hmm",
    "hm",
    "like",
    "you know",
    "basically",
    "actually",
    "i mean",
    "sort of",
    "kind of",
    "right",
]
