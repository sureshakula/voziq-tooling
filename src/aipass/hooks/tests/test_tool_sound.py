# =================== AIPass ====================
# Name: test_tool_sound.py
# Version: 1.1.0
# Description: Tests for tool_sound notification handler
# Branch: hooks
# Created: 2026-05-19
# Modified: 2026-05-19
# =============================================

"""Tests for handlers/notification/tool_sound.py."""

from unittest.mock import patch, MagicMock


class TestToolSoundHandler:
    """Core handler behavior tests."""

    def test_handle_returns_result_dict(self):
        from aipass.hooks.apps.handlers.notification.tool_sound import handle

        with patch("aipass.hooks.apps.handlers.notification.tool_sound._speak"):
            result = handle({"tool_name": "Bash"})

        assert isinstance(result, dict)
        assert "stdout" in result
        assert "exit_code" in result
        assert result["stdout"] == ""
        assert result["exit_code"] == 0

    def test_speaks_tool_name(self):
        from aipass.hooks.apps.handlers.notification.tool_sound import handle

        with patch("aipass.hooks.apps.handlers.notification.tool_sound._speak") as mock_speak:
            handle({"tool_name": "Edit"})

        mock_speak.assert_called_once_with("tool sound: Edit")

    def test_no_speak_when_no_tool_name(self):
        from aipass.hooks.apps.handlers.notification.tool_sound import handle

        with patch("aipass.hooks.apps.handlers.notification.tool_sound._speak") as mock_speak:
            handle({})

        mock_speak.assert_not_called()

    def test_no_speak_when_empty_tool_name(self):
        from aipass.hooks.apps.handlers.notification.tool_sound import handle

        with patch("aipass.hooks.apps.handlers.notification.tool_sound._speak") as mock_speak:
            handle({"tool_name": ""})

        mock_speak.assert_not_called()


class TestSpeakFunction:
    """Piper TTS integration tests."""

    def test_speak_calls_piper_then_aplay(self):
        from aipass.hooks.apps.handlers.notification.tool_sound import _speak

        with (
            patch("aipass.hooks.apps.handlers.notification.tool_sound.PIPER_BIN") as mock_piper_bin,
            patch("aipass.hooks.apps.handlers.notification.tool_sound.PIPER_VOICE") as mock_voice,
            patch("aipass.hooks.apps.handlers.notification.tool_sound.subprocess") as mock_sub,
            patch("aipass.hooks.apps.handlers.notification.tool_sound.tempfile") as mock_tmp,
            patch("aipass.hooks.apps.handlers.notification.tool_sound.Path") as mock_path,
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
        from aipass.hooks.apps.handlers.notification.tool_sound import _speak

        with (
            patch("aipass.hooks.apps.handlers.notification.tool_sound.PIPER_BIN") as mock_piper_bin,
            patch("aipass.hooks.apps.handlers.notification.tool_sound.subprocess") as mock_sub,
        ):
            mock_piper_bin.exists.return_value = False
            _speak("test")

        mock_sub.run.assert_not_called()

    def test_speak_graceful_on_timeout(self):
        import subprocess as real_sub
        from aipass.hooks.apps.handlers.notification.tool_sound import _speak

        with (
            patch("aipass.hooks.apps.handlers.notification.tool_sound.PIPER_BIN") as mock_piper_bin,
            patch("aipass.hooks.apps.handlers.notification.tool_sound.PIPER_VOICE") as mock_voice,
            patch("aipass.hooks.apps.handlers.notification.tool_sound.subprocess") as mock_sub,
            patch("aipass.hooks.apps.handlers.notification.tool_sound.tempfile") as mock_tmp,
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
        from aipass.hooks.apps.handlers.notification.tool_sound import _speak

        with (
            patch("aipass.hooks.apps.handlers.notification.tool_sound.PIPER_BIN") as mock_piper_bin,
            patch("aipass.hooks.apps.handlers.notification.tool_sound.PIPER_VOICE") as mock_voice,
            patch("aipass.hooks.apps.handlers.notification.tool_sound.subprocess.run", side_effect=OSError("broken")),
            patch("aipass.hooks.apps.handlers.notification.tool_sound.tempfile") as mock_tmp,
        ):
            mock_piper_bin.exists.return_value = True
            mock_voice.exists.return_value = True
            mock_file = MagicMock()
            mock_file.name = "/tmp/test.wav"
            mock_tmp.NamedTemporaryFile.return_value = mock_file

            _speak("test")
