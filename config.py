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
KEYBIND_KEY = "z"

# =============================================================================
# TRANSCRIPTION BACKEND
# =============================================================================
# "local" - Use faster-whisper locally (default, no API key needed)
# "groq"  - Use Groq Whisper API (requires GROQ_API_KEY env var)
# TRANSCRIPTION_BACKEND = "local"

# TRANSCRIPTION_BACKEND = "groq"
TRANSCRIPTION_BACKEND = "groq"

# =============================================================================
# LOCAL WHISPER SETTINGS (only used if TRANSCRIPTION_BACKEND = "local")
# =============================================================================
# Model sizes (download size → RAM usage):
#   tiny   (~75 MB)  - Fastest, good accuracy, best for most users
#   base   (~142 MB) - Fast, better accuracy
#   small  (~466 MB) - Medium speed, great accuracy
#   medium (~1.5 GB) - Slow, excellent accuracy
#   large  (~3 GB)   - Slowest, best accuracy (requires lots of RAM)

MODEL_SIZE = "medium"

# Compute type:
#   "int8"    - Best for CPU (faster, less memory)
#   "float16" - Best for GPU with CUDA
#   "float32" - Fallback (slower)

COMPUTE_TYPE = "float32"

# =============================================================================
# GROQ API SETTINGS (only used if TRANSCRIPTION_BACKEND = "groq" or TRANSFORM_BACKEND = "groq")
# =============================================================================
# API key is read from GROQ_API_KEY environment variable
# Get your key at: https://console.groq.com/keys
#
# Groq Whisper models:
#   "whisper-large-v3-turbo" - Fast (216x realtime), $0.04/hour, 12% WER
#   "whisper-large-v3"       - Accurate (164x realtime), $0.111/hour, 10.3% WER

GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"

# =============================================================================
# LANGUAGE SETTINGS
# =============================================================================
# Language code (ISO 639-1): "en" - English
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
]

# =============================================================================
# TEXT TRANSFORMATION (Grammar/Punctuation Correction)
# =============================================================================
# Enable/disable post-transcription text transformation using an LLM
TRANSFORM_ENABLED = False

# Transform backend:
#   "groq"   - Use Groq LLM API (fast, requires GROQ_API_KEY env var)
#   "ollama" - Use local Ollama (free, requires ollama installed)
TRANSFORM_BACKEND = "groq"

# Model for transformation:
# Groq models:
#   "openai/gpt-oss-20b"      - Fastest (1000 tok/s), great for grammar
#   "llama-3.1-8b-instant"    - Fast (560 tok/s), $0.05/$0.08 per 1M tokens
#   "llama-3.3-70b-versatile" - Better quality (280 tok/s), $0.59/$0.79 per 1M tokens
# Ollama models (local):
#   "qwen2.5:3b"  - Small (~3GB RAM), fast
#   "phi3:mini"   - Small (~4GB RAM), good quality
#   "qwen2.5:7b"  - Medium (~5GB RAM), better quality
TRANSFORM_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"

# Prompt for text transformation
# Use {text} as placeholder for the transcribed text
TRANSFORM_PROMPT = """Fix grammar, spelling, and punctuation in the following transcribed speech.
Add proper capitalization and commas where needed.
Keep the original meaning and tone.
Only output the corrected text, nothing else.
Do not add any explanations or notes, your job is to simply correct the text or format the text only

Again remember there is no modification to the output. Output remains as is and consistent

Text: {text}"""
