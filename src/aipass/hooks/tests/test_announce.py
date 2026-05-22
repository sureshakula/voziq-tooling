# =================== AIPass ====================
# Name: test_announce.py
# Version: 1.1.0
# Description: Tests for announce notification handler
# Branch: hooks
# Created: 2026-05-20
# Modified: 2026-05-20
# =============================================

"""Tests for handlers/notification/announce.py."""

from unittest.mock import patch, MagicMock


class TestAnnounceHandler:
    """Core handler behavior tests."""

    def test_handle_returns_result_dict(self):
        from aipass.hooks.apps.handlers.notification.announce import handle

        with (
            patch("aipass.hooks.apps.handlers.notification.announce._play"),
            patch("aipass.hooks.apps.handlers.notification.announce._speak"),
        ):
            result = handle({})

        assert isinstance(result, dict)
        assert result["stdout"] == ""
        assert result["exit_code"] == 0

    def test_handle_speaks_notification_sound(self):
        from aipass.hooks.apps.handlers.notification.announce import handle

        with (
            patch("aipass.hooks.apps.handlers.notification.announce._play"),
            patch("aipass.hooks.apps.handlers.notification.announce._speak") as mock_speak,
        ):
            handle({})

        mock_speak.assert_called_once_with("notification sound")

    def test_handle_does_not_play_wav(self):
        from aipass.hooks.apps.handlers.notification.announce import handle

        with (
            patch("aipass.hooks.apps.handlers.notification.announce._play") as mock_play,
            patch("aipass.hooks.apps.handlers.notification.announce._speak"),
        ):
            handle({})

        mock_play.assert_not_called()


class TestPlayFunction:
    """WAV playback tests."""

    def test_play_calls_aplay(self):
        from aipass.hooks.apps.handlers.notification.announce import _play

        mock_path = MagicMock()
        mock_path.exists.return_value = True

        with patch("aipass.hooks.apps.handlers.notification.announce.subprocess.Popen") as mock_popen:
            _play(mock_path)

        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args[0] == "aplay"
        assert args[1] == "-q"

    def test_play_skips_when_file_missing(self):
        from aipass.hooks.apps.handlers.notification.announce import _play

        mock_path = MagicMock()
        mock_path.exists.return_value = False

        with patch("aipass.hooks.apps.handlers.notification.announce.subprocess.Popen") as mock_popen:
            _play(mock_path)

        mock_popen.assert_not_called()

    def test_play_graceful_on_os_error(self):
        from aipass.hooks.apps.handlers.notification.announce import _play

        mock_path = MagicMock()
        mock_path.exists.return_value = True

        with patch(
            "aipass.hooks.apps.handlers.notification.announce.subprocess.Popen",
            side_effect=OSError("broken"),
        ):
            _play(mock_path)


class TestSpeakFunction:
    """Piper TTS tests."""

    def test_speak_calls_piper_then_aplay(self):
        from aipass.hooks.apps.handlers.notification.announce import _speak

        with (
            patch("aipass.hooks.apps.handlers.notification.announce.PIPER_BIN") as mock_piper_bin,
            patch("aipass.hooks.apps.handlers.notification.announce.PIPER_VOICE") as mock_voice,
            patch("aipass.hooks.apps.handlers.notification.announce.subprocess") as mock_sub,
            patch("aipass.hooks.apps.handlers.notification.announce.tempfile") as mock_tmp,
            patch("aipass.hooks.apps.handlers.notification.announce.Path") as mock_path,
        ):
            mock_piper_bin.exists.return_value = True
            mock_voice.exists.return_value = True
            mock_file = MagicMock()
            mock_file.name = "/tmp/test.wav"
            mock_tmp.NamedTemporaryFile.return_value = mock_file
            mock_sub.run.return_value = MagicMock(returncode=0)
            mock_path.return_value.exists.return_value = True

            _speak("test text")

        mock_sub.run.assert_called_once()
        mock_sub.Popen.assert_called_once()

    def test_speak_skips_when_piper_missing(self):
        from aipass.hooks.apps.handlers.notification.announce import _speak

        with (
            patch("aipass.hooks.apps.handlers.notification.announce.PIPER_BIN") as mock_piper_bin,
            patch("aipass.hooks.apps.handlers.notification.announce.subprocess") as mock_sub,
        ):
            mock_piper_bin.exists.return_value = False
            _speak("test")

        mock_sub.run.assert_not_called()

    def test_speak_graceful_on_timeout(self):
        import subprocess as real_sub
        from aipass.hooks.apps.handlers.notification.announce import _speak

        with (
            patch("aipass.hooks.apps.handlers.notification.announce.PIPER_BIN") as mock_piper_bin,
            patch("aipass.hooks.apps.handlers.notification.announce.PIPER_VOICE") as mock_voice,
            patch("aipass.hooks.apps.handlers.notification.announce.subprocess") as mock_sub,
            patch("aipass.hooks.apps.handlers.notification.announce.tempfile") as mock_tmp,
        ):
            mock_piper_bin.exists.return_value = True
            mock_voice.exists.return_value = True
            mock_file = MagicMock()
            mock_file.name = "/tmp/test.wav"
            mock_tmp.NamedTemporaryFile.return_value = mock_file
            mock_sub.run.side_effect = real_sub.TimeoutExpired("piper", 5)
            mock_sub.TimeoutExpired = real_sub.TimeoutExpired

            _speak("test")

    def test_speak_graceful_on_os_error(self):
        from aipass.hooks.apps.handlers.notification.announce import _speak

        with (
            patch("aipass.hooks.apps.handlers.notification.announce.PIPER_BIN") as mock_piper_bin,
            patch("aipass.hooks.apps.handlers.notification.announce.PIPER_VOICE") as mock_voice,
            patch("aipass.hooks.apps.handlers.notification.announce.subprocess.run", side_effect=OSError("broken")),
            patch("aipass.hooks.apps.handlers.notification.announce.tempfile") as mock_tmp,
        ):
            mock_piper_bin.exists.return_value = True
            mock_voice.exists.return_value = True
            mock_file = MagicMock()
            mock_file.name = "/tmp/test.wav"
            mock_tmp.NamedTemporaryFile.return_value = mock_file

            _speak("test")
