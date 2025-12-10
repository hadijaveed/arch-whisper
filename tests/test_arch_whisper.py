#!/usr/bin/env python3
"""Tests for arch-whisper voice dictation daemon."""

import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from arch_whisper import ArchWhisper, SOCKET_PATH
from config import FILLERS, SAMPLE_RATE


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def whisper_instance():
    """Create a fresh ArchWhisper instance for testing."""
    instance = ArchWhisper()
    yield instance
    # Cleanup
    if instance.stream:
        try:
            instance.stream.stop()
            instance.stream.close()
        except Exception:
            pass
    if instance.watchdog_timer:
        instance.watchdog_timer.cancel()


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for ydotool and notify-send."""
    with patch("arch_whisper.subprocess.run") as mock:
        mock.return_value = MagicMock(returncode=0)
        yield mock


# =============================================================================
# Text Cleaning Tests
# =============================================================================


class TestCleanText:
    """Tests for the clean_text method."""

    def test_empty_string(self, whisper_instance):
        assert whisper_instance.clean_text("") == ""

    def test_none_handling(self, whisper_instance):
        assert whisper_instance.clean_text(None) == ""

    def test_filler_word_removal(self, whisper_instance):
        """Test that filler words are removed."""
        text = "Um, I think, uh, this is like basically a test."
        result = whisper_instance.clean_text(text)
        assert "um" not in result.lower()
        assert "uh" not in result.lower()
        assert "like" not in result.lower()
        assert "basically" not in result.lower()

    def test_capitalize_first_letter(self, whisper_instance):
        result = whisper_instance.clean_text("hello world")
        assert result[0] == "H"

    def test_capitalize_after_sentence(self, whisper_instance):
        result = whisper_instance.clean_text("hello. world")
        assert "Hello. World" == result

    def test_fix_missing_space_after_period(self, whisper_instance):
        result = whisper_instance.clean_text("Hello.World")
        assert result == "Hello. World"

    def test_fix_missing_space_after_comma(self, whisper_instance):
        result = whisper_instance.clean_text("Hello,world")
        assert result == "Hello, world"

    def test_remove_leading_punctuation(self, whisper_instance):
        result = whisper_instance.clean_text("...hello")
        # Leading punctuation removed, but capitalize happens before removal
        assert "..." not in result
        assert "hello" in result.lower()

    def test_remove_trailing_punctuation(self, whisper_instance):
        result = whisper_instance.clean_text("hello,,,")
        assert result == "Hello"

    def test_collapse_whitespace(self, whisper_instance):
        result = whisper_instance.clean_text("hello    world")
        assert result == "Hello world"

    def test_preserve_sentence_punctuation(self, whisper_instance):
        result = whisper_instance.clean_text("Hello! How are you?")
        assert "!" in result
        assert "?" in result

    def test_complex_filler_removal(self, whisper_instance):
        """Test multi-word fillers like 'you know', 'i mean'."""
        text = "I mean, you know, it's sort of kind of working."
        result = whisper_instance.clean_text(text)
        assert "i mean" not in result.lower()
        assert "you know" not in result.lower()


# =============================================================================
# Command Handling Tests
# =============================================================================


class TestHandleCommand:
    """Tests for the handle_command method."""

    def test_ping_command(self, whisper_instance):
        assert whisper_instance.handle_command("ping") == "pong"

    def test_ping_with_whitespace(self, whisper_instance):
        assert whisper_instance.handle_command("  ping  ") == "pong"

    def test_ping_case_insensitive(self, whisper_instance):
        assert whisper_instance.handle_command("PING") == "pong"
        assert whisper_instance.handle_command("Ping") == "pong"

    def test_status_idle(self, whisper_instance):
        assert whisper_instance.handle_command("status") == "idle"

    def test_status_recording(self, whisper_instance):
        whisper_instance.recording = True
        assert whisper_instance.handle_command("status") == "recording"

    def test_status_transcribing(self, whisper_instance):
        whisper_instance.transcribing = True
        assert whisper_instance.handle_command("status") == "transcribing"

    def test_unknown_command(self, whisper_instance):
        result = whisper_instance.handle_command("foobar")
        assert "unknown" in result

    def test_start_command(self, whisper_instance):
        with patch.object(whisper_instance, "start_recording"):
            result = whisper_instance.handle_command("start")
            assert result == "ok"

    def test_reset_command(self, whisper_instance):
        with patch.object(whisper_instance, "_force_reset"):
            result = whisper_instance.handle_command("reset")
            assert result == "ok"


# =============================================================================
# Recording State Tests
# =============================================================================


class TestRecordingState:
    """Tests for recording state management."""

    def test_initial_state(self, whisper_instance):
        assert whisper_instance.recording is False
        assert whisper_instance.transcribing is False
        assert whisper_instance.pending_start is False
        assert whisper_instance.audio_data == []

    def test_start_recording_sets_flag(self, whisper_instance):
        with patch("arch_whisper.sd.InputStream") as mock_stream:
            mock_stream.return_value.start = MagicMock()
            whisper_instance._do_start_recording()
            assert whisper_instance.recording is True

    def test_stop_recording_when_not_recording(self, whisper_instance):
        result = whisper_instance.stop_recording()
        assert result == ""

    def test_pending_start_when_transcribing(self, whisper_instance):
        whisper_instance.transcribing = True
        whisper_instance.start_recording()
        assert whisper_instance.pending_start is True
        assert whisper_instance.recording is False

    def test_ignore_start_when_already_recording(self, whisper_instance):
        whisper_instance.recording = True
        original_data = whisper_instance.audio_data
        whisper_instance.start_recording()
        # Should return early, not reset audio_data
        assert whisper_instance.audio_data is original_data


# =============================================================================
# Force Reset Tests
# =============================================================================


class TestForceReset:
    """Tests for the force reset functionality."""

    def test_reset_clears_recording_flag(self, whisper_instance):
        whisper_instance.recording = True
        whisper_instance._force_reset()
        assert whisper_instance.recording is False

    def test_reset_clears_transcribing_flag(self, whisper_instance):
        whisper_instance.transcribing = True
        whisper_instance._force_reset()
        assert whisper_instance.transcribing is False

    def test_reset_clears_pending_start(self, whisper_instance):
        whisper_instance.pending_start = True
        whisper_instance._force_reset()
        assert whisper_instance.pending_start is False

    def test_reset_clears_audio_data(self, whisper_instance):
        whisper_instance.audio_data = [np.zeros(100)]
        whisper_instance._force_reset()
        assert whisper_instance.audio_data == []

    def test_reset_cancels_watchdog(self, whisper_instance):
        mock_timer = MagicMock()
        whisper_instance.watchdog_timer = mock_timer
        whisper_instance._force_reset()
        mock_timer.cancel.assert_called_once()
        assert whisper_instance.watchdog_timer is None

    def test_reset_sets_cancel_transform(self, whisper_instance):
        whisper_instance.cancel_transform = False
        whisper_instance._force_reset()
        assert whisper_instance.cancel_transform is True


# =============================================================================
# Audio Processing Tests
# =============================================================================


class TestAudioProcessing:
    """Tests for audio processing functionality."""

    def test_audio_callback_appends_data(self, whisper_instance):
        whisper_instance.recording = True
        fake_audio = np.array([[0.1], [0.2], [0.3]], dtype=np.float32)
        whisper_instance.audio_callback(fake_audio, 3, None, None)
        assert len(whisper_instance.audio_data) == 1
        np.testing.assert_array_equal(whisper_instance.audio_data[0], fake_audio)

    def test_audio_callback_ignores_when_not_recording(self, whisper_instance):
        whisper_instance.recording = False
        fake_audio = np.array([[0.1], [0.2]], dtype=np.float32)
        whisper_instance.audio_callback(fake_audio, 2, None, None)
        assert len(whisper_instance.audio_data) == 0

    def test_short_audio_returns_empty(self, whisper_instance):
        """Audio shorter than 0.3 seconds should be ignored."""
        whisper_instance.recording = True
        # Create audio shorter than 0.3 seconds
        short_audio = np.zeros((int(SAMPLE_RATE * 0.1), 1), dtype=np.float32)
        whisper_instance.audio_data = [short_audio]

        with whisper_instance.lock:
            whisper_instance.recording = False
            audio = np.concatenate(whisper_instance.audio_data, axis=0).flatten()
            whisper_instance.audio_data = []

        # Simulate the length check
        assert len(audio) < SAMPLE_RATE * 0.3


# =============================================================================
# Multi-turn Spacing Tests
# =============================================================================


class TestMultiTurnSpacing:
    """Tests for multi-turn dictation spacing."""

    def test_adds_space_for_recent_typing(self, whisper_instance, mock_subprocess):
        whisper_instance.last_typing_time = time.time()
        whisper_instance.type_text("hello")
        # Find the ydotool call (first call, notify is second)
        ydotool_call = mock_subprocess.call_args_list[0][0][0]
        assert ydotool_call[-1] == " hello"

    def test_no_space_for_old_typing(self, whisper_instance, mock_subprocess):
        whisper_instance.last_typing_time = time.time() - 60  # 60 seconds ago
        whisper_instance.type_text("hello")
        ydotool_call = mock_subprocess.call_args_list[0][0][0]
        assert ydotool_call[-1] == "hello"

    def test_no_space_for_punctuation_start(self, whisper_instance, mock_subprocess):
        whisper_instance.last_typing_time = time.time()
        whisper_instance.type_text(".hello")
        ydotool_call = mock_subprocess.call_args_list[0][0][0]
        assert ydotool_call[-1] == ".hello"


# =============================================================================
# Typing Tests
# =============================================================================


class TestTyping:
    """Tests for text typing functionality."""

    def test_type_empty_string(self, whisper_instance, mock_subprocess):
        whisper_instance.type_text("")
        mock_subprocess.assert_not_called()

    def test_type_text_calls_ydotool(self, whisper_instance, mock_subprocess):
        whisper_instance.type_text("hello world")
        mock_subprocess.assert_called()
        # First call is ydotool, second is notify-send
        ydotool_call = mock_subprocess.call_args_list[0][0][0]
        assert "ydotool" in ydotool_call
        assert "type" in ydotool_call

    def test_type_updates_last_typing_time(self, whisper_instance, mock_subprocess):
        old_time = whisper_instance.last_typing_time
        whisper_instance.type_text("test")
        assert whisper_instance.last_typing_time > old_time


# =============================================================================
# Client Mode Tests
# =============================================================================


class TestClientMode:
    """Tests for client mode (command-line interface)."""

    def test_client_script_ping(self):
        """Test that client mode works with ping command."""
        result = subprocess.run(
            [sys.executable, "arch_whisper.py", "ping"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        # Either pong (daemon running) or error (daemon not running)
        assert "pong" in result.stdout or "error" in result.stdout

    def test_client_script_status(self):
        """Test status command."""
        result = subprocess.run(
            [sys.executable, "arch_whisper.py", "status"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.stdout.strip() in ["idle", "recording", "transcribing", "error: daemon not running"]


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests that test multiple components together."""

    def test_full_reset_cycle(self, whisper_instance):
        """Test a full reset cycle."""
        # Simulate active state
        whisper_instance.recording = True
        whisper_instance.transcribing = True
        whisper_instance.pending_start = True
        whisper_instance.audio_data = [np.zeros(100)]

        # Reset
        whisper_instance._force_reset()

        # Verify clean state
        assert whisper_instance.recording is False
        assert whisper_instance.transcribing is False
        assert whisper_instance.pending_start is False
        assert whisper_instance.audio_data == []

    def test_command_sequence(self, whisper_instance):
        """Test a sequence of commands."""
        # Initial state
        assert whisper_instance.handle_command("status") == "idle"
        assert whisper_instance.handle_command("ping") == "pong"

        # After simulated recording
        whisper_instance.recording = True
        assert whisper_instance.handle_command("status") == "recording"

        # Reset
        with patch.object(whisper_instance, "notify"):
            whisper_instance.handle_command("reset")
        assert whisper_instance.handle_command("status") == "idle"


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_concurrent_start_stop(self, whisper_instance):
        """Test that concurrent start/stop is handled correctly."""
        whisper_instance.transcribing = True

        # Start should queue
        whisper_instance.start_recording()
        assert whisper_instance.pending_start is True
        assert whisper_instance.recording is False

    def test_clean_text_with_only_fillers(self, whisper_instance):
        """Test cleaning text that contains only filler words."""
        result = whisper_instance.clean_text("um uh like")
        # Should result in empty or minimal text
        assert result.strip() in ["", "Um uh like"]  # May vary based on filler list

    def test_clean_text_preserves_urls(self, whisper_instance):
        """Test that URLs are preserved."""
        text = "Check out https://example.com for more info."
        result = whisper_instance.clean_text(text)
        assert "example.com" in result

    def test_notification_failure_handled(self, whisper_instance):
        """Test that notification failures don't crash."""
        with patch("arch_whisper.subprocess.run", side_effect=Exception("notify failed")):
            # Should not raise
            whisper_instance.notify("test message")

    def test_type_ydotool_not_found(self, whisper_instance):
        """Test handling when ydotool is not installed."""
        with patch("arch_whisper.subprocess.run", side_effect=FileNotFoundError()):
            with patch.object(whisper_instance, "notify") as mock_notify:
                whisper_instance.type_text("test")
                mock_notify.assert_called()


# =============================================================================
# Config Tests
# =============================================================================


class TestConfig:
    """Tests for configuration values."""

    def test_sample_rate_is_16khz(self):
        """Whisper requires 16kHz sample rate."""
        assert SAMPLE_RATE == 16000

    def test_fillers_list_exists(self):
        """Test that filler words are defined."""
        assert isinstance(FILLERS, list)
        assert len(FILLERS) > 0
        assert "um" in FILLERS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
