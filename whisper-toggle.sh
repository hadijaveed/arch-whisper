#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Whisper Toggle
# @raycast.mode silent

# Optional parameters:
# @raycast.icon 🎤
# @raycast.packageName Whisper

LOCK_FILE="/tmp/whisper-recording.lock"
DEBOUNCE_FILE="/tmp/whisper-debounce.lock"
SCRIPT_DIR="/Users/hadijaveed/code-place/arch-whisper"

# Debounce: ignore if called within last 1 second
if [ -f "$DEBOUNCE_FILE" ]; then
  LAST_TIME=$(cat "$DEBOUNCE_FILE")
  CURRENT_TIME=$(date +%s)
  DIFF=$((CURRENT_TIME - LAST_TIME))
  if [ "$DIFF" -lt 1 ]; then
    exit 0
  fi
fi
date +%s >"$DEBOUNCE_FILE"

if [ -f "$LOCK_FILE" ]; then
  rm -f "$LOCK_FILE"
  "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/mac_whisper.py" stop
else
  touch "$LOCK_FILE"
  "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/mac_whisper.py" start
fi
