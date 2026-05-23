# =================== AIPass ====================
# Name: test_sound.py
# Version: 1.0.0
# Description: Tests for shared sound module
# Branch: hooks
# Created: 2026-05-22
# Modified: 2026-05-22
# =============================================

"""Tests for apps/sound.py — shared speak/play with mute support."""

from pathlib import Path
from unittest.mock import patch, MagicMock


class TestIsMuted:
    """Mute flag detection."""

    def test_not_muted_when_flag_missing(self):
        from aipass.hooks.apps.sound import is_muted

        with patch("aipass.hooks.apps.sound.MUTE_FLAG") as mock_flag:
            mock_flag.exists.return_value = False
            assert is_muted() is False

    def test_muted_when_flag_exists(self):
        from aipass.hooks.apps.sound import is_muted

        with patch("aipass.hooks.apps.sound.MUTE_FLAG") as mock_flag:
            mock_flag.exists.return_value = True
            assert is_muted() is True


class TestSpeak:
    """Piper TTS with mute support."""

    def test_speak_calls_piper_when_not_muted(self):
        from aipass.hooks.apps.sound import speak

        with (
            patch("aipass.hooks.apps.sound.is_muted", return_value=False),
            patch("aipass.hooks.apps.sound.PIPER_BIN") as mock_bin,
            patch("aipass.hooks.apps.sound.PIPER_VOICE") as mock_voice,
            patch("aipass.hooks.apps.sound.subprocess") as mock_sub,
            patch("aipass.hooks.apps.sound.tempfile") as mock_tmp,
            patch("aipass.hooks.apps.sound.Path") as mock_path,
        ):
            mock_bin.exists.return_value = True
            mock_voice.exists.return_value = True
            mock_file = MagicMock()
            mock_file.name = "/tmp/test.wav"
            mock_tmp.NamedTemporaryFile.return_value = mock_file
            mock_sub.run.return_value = MagicMock(returncode=0)
            mock_path.return_value.exists.return_value = True

            speak("test text")

        mock_sub.run.assert_called_once()
        mock_sub.Popen.assert_called_once()

    def test_speak_skips_when_muted(self):
        from aipass.hooks.apps.sound import speak

        with (
            patch("aipass.hooks.apps.sound.is_muted", return_value=True),
            patch("aipass.hooks.apps.sound.subprocess") as mock_sub,
        ):
            speak("test")

        mock_sub.run.assert_not_called()

    def test_speak_skips_when_piper_missing(self):
        from aipass.hooks.apps.sound import speak

        with (
            patch("aipass.hooks.apps.sound.is_muted", return_value=False),
            patch("aipass.hooks.apps.sound.PIPER_BIN") as mock_bin,
            patch("aipass.hooks.apps.sound.subprocess") as mock_sub,
        ):
            mock_bin.exists.return_value = False
            speak("test")

        mock_sub.run.assert_not_called()

    def test_speak_graceful_on_timeout(self):
        import subprocess as real_sub
        from aipass.hooks.apps.sound import speak

        with (
            patch("aipass.hooks.apps.sound.is_muted", return_value=False),
            patch("aipass.hooks.apps.sound.PIPER_BIN") as mock_bin,
            patch("aipass.hooks.apps.sound.PIPER_VOICE") as mock_voice,
            patch("aipass.hooks.apps.sound.subprocess") as mock_sub,
            patch("aipass.hooks.apps.sound.tempfile") as mock_tmp,
        ):
            mock_bin.exists.return_value = True
            mock_voice.exists.return_value = True
            mock_file = MagicMock()
            mock_file.name = "/tmp/test.wav"
            mock_tmp.NamedTemporaryFile.return_value = mock_file
            mock_sub.run.side_effect = real_sub.TimeoutExpired("piper", 5)
            mock_sub.TimeoutExpired = real_sub.TimeoutExpired

            speak("test")

    def test_speak_graceful_on_os_error(self):
        from aipass.hooks.apps.sound import speak

        with (
            patch("aipass.hooks.apps.sound.is_muted", return_value=False),
            patch("aipass.hooks.apps.sound.PIPER_BIN") as mock_bin,
            patch("aipass.hooks.apps.sound.PIPER_VOICE") as mock_voice,
            patch("aipass.hooks.apps.sound.subprocess.run", side_effect=OSError("broken")),
            patch("aipass.hooks.apps.sound.tempfile") as mock_tmp,
        ):
            mock_bin.exists.return_value = True
            mock_voice.exists.return_value = True
            mock_file = MagicMock()
            mock_file.name = "/tmp/test.wav"
            mock_tmp.NamedTemporaryFile.return_value = mock_file

            speak("test")


class TestPlay:
    """WAV playback with mute support."""

    def test_play_calls_aplay_when_not_muted(self):
        from aipass.hooks.apps.sound import play

        with (
            patch("aipass.hooks.apps.sound.is_muted", return_value=False),
            patch("aipass.hooks.apps.sound.subprocess") as mock_sub,
        ):
            mock_path = MagicMock()
            mock_path.exists.return_value = True

            play(mock_path)

        mock_sub.Popen.assert_called_once()

    def test_play_skips_when_muted(self):
        from aipass.hooks.apps.sound import play

        with (
            patch("aipass.hooks.apps.sound.is_muted", return_value=True),
            patch("aipass.hooks.apps.sound.subprocess") as mock_sub,
        ):
            play(Path("/tmp/sound.wav"))

        mock_sub.Popen.assert_not_called()

    def test_play_skips_when_file_missing(self):
        from aipass.hooks.apps.sound import play

        with (
            patch("aipass.hooks.apps.sound.is_muted", return_value=False),
            patch("aipass.hooks.apps.sound.subprocess") as mock_sub,
        ):
            mock_path = MagicMock()
            mock_path.exists.return_value = False

            play(mock_path)

        mock_sub.Popen.assert_not_called()

    def test_play_graceful_on_os_error(self):
        from aipass.hooks.apps.sound import play

        with (
            patch("aipass.hooks.apps.sound.is_muted", return_value=False),
            patch("aipass.hooks.apps.sound.subprocess.Popen", side_effect=OSError("no aplay")),
        ):
            mock_path = MagicMock()
            mock_path.exists.return_value = True

            play(mock_path)
