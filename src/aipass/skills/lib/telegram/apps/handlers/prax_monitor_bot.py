# =================== AIPass ====================
# Name: prax_monitor_bot.py
# Description: Telegram bot for the Prax Monitor chat — command receiver for relay control
# Version: 1.0.0
# Created: 2026-07-12
# Modified: 2026-07-12
# =============================================

"""
PraxMonitorBot — a BaseBot subclass for the Prax Monitor TG chat.

Receives commands from the Prax Monitor Telegram chat and writes a control file
that the prax relay reads each flush cycle (~5s). No tmux/Claude sessions.

Control file: ~/.aipass/telegram_bots/prax_monitor_control.json
Schema: {"paused": bool, "level": "all"|"errors", "updated_at": iso8601}
"""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from aipass.prax import logger

from .base_bot import BaseBot


CONTROL_FILE = Path.home() / ".aipass" / "telegram_bots" / "prax_monitor_control.json"


class PraxMonitorBot(BaseBot):
    """Prax Monitor command bot — controls the relay via a shared control file."""

    def handle_message(self, chat_id: int, text: str, message: dict) -> None:
        """Reject free-text — this bot only serves commands."""
        self.send_message(
            chat_id,
            "I only handle commands.\nTry /pause, /resume, /errors, /all, or /status",
        )

    def handle_file(self, chat_id: int, message: dict) -> None:
        """Reject files."""
        self.send_message(chat_id, "I don't process files. Try /status or /help")

    def _dispatch_command(self, chat_id: int, parsed: tuple) -> bool:
        cmd_name, cmd_args = parsed
        if cmd_name == "pause":
            self._handle_pause(chat_id)
            return True
        if cmd_name == "resume":
            self._handle_resume(chat_id)
            return True
        if cmd_name == "errors":
            self._handle_errors(chat_id)
            return True
        if cmd_name == "all":
            self._handle_all(chat_id)
            return True
        if cmd_name == "status":
            self._handle_prax_status(chat_id)
            return True
        return super()._dispatch_command(chat_id, parsed)

    def get_custom_commands(self) -> dict:
        cmds = super().get_custom_commands()
        cmds["pause"] = {
            "description": "Pause the prax log relay",
            "menu_text": "Pause relay",
        }
        cmds["resume"] = {
            "description": "Resume the prax log relay",
            "menu_text": "Resume relay",
        }
        cmds["errors"] = {
            "description": "Show errors & warnings only",
            "menu_text": "Errors only",
        }
        cmds["all"] = {
            "description": "Show all log levels",
            "menu_text": "All levels",
        }
        return cmds

    # =============================================
    # COMMAND HANDLERS
    # =============================================

    def _handle_pause(self, chat_id: int) -> None:
        ctrl = self._read_control()
        ctrl["paused"] = True
        if self._write_control(ctrl):
            self.send_message(chat_id, "Relay paused.\n\n/resume to restart.")
        else:
            self.send_message(chat_id, "Failed to write control file.")
        logger.info("Prax monitor paused (chat_id=%s)", chat_id)

    def _handle_resume(self, chat_id: int) -> None:
        ctrl = self._read_control()
        ctrl["paused"] = False
        if self._write_control(ctrl):
            level = ctrl.get("level", "all")
            self.send_message(chat_id, f"Relay resumed (level: {level}).\n\n/pause to stop.")
        else:
            self.send_message(chat_id, "Failed to write control file.")
        logger.info("Prax monitor resumed (chat_id=%s)", chat_id)

    def _handle_errors(self, chat_id: int) -> None:
        ctrl = self._read_control()
        ctrl["level"] = "errors"
        if self._write_control(ctrl):
            self.send_message(chat_id, "Level set to errors & warnings only.\n\n/all for full firehose.")
        else:
            self.send_message(chat_id, "Failed to write control file.")
        logger.info("Prax monitor level=errors (chat_id=%s)", chat_id)

    def _handle_all(self, chat_id: int) -> None:
        ctrl = self._read_control()
        ctrl["level"] = "all"
        if self._write_control(ctrl):
            self.send_message(chat_id, "Level set to all.\n\n/errors for filtered mode.")
        else:
            self.send_message(chat_id, "Failed to write control file.")
        logger.info("Prax monitor level=all (chat_id=%s)", chat_id)

    def _handle_prax_status(self, chat_id: int) -> None:
        ctrl = self._read_control()
        paused = ctrl.get("paused", False)
        level = ctrl.get("level", "all")
        updated = ctrl.get("updated_at", "never")

        relay_alive = self._check_relay_alive()
        relay_status = "running" if relay_alive else "not detected"

        state = "paused" if paused else "active"
        level_label = "errors & warnings" if level == "errors" else "all levels"

        self.send_message(
            chat_id,
            f"Prax Monitor\nState: {state}\nLevel: {level_label}\nRelay: {relay_status}\nLast update: {updated}",
        )

    # =============================================
    # CONTROL FILE I/O
    # =============================================

    def _read_control(self) -> dict:
        """Read the control file; return defaults if missing or corrupt."""
        if not CONTROL_FILE.exists():
            return {"paused": False, "level": "all"}
        try:
            data = json.loads(CONTROL_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
            return {"paused": False, "level": "all"}
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read control file: %s", e)
            return {"paused": False, "level": "all"}

    def _write_control(self, ctrl: dict) -> bool:
        """Write the control file with updated_at timestamp."""
        ctrl["updated_at"] = datetime.now(timezone.utc).isoformat()
        try:
            CONTROL_FILE.parent.mkdir(parents=True, exist_ok=True)
            CONTROL_FILE.write_text(
                json.dumps(ctrl, indent=2),
                encoding="utf-8",
            )
            return True
        except OSError as e:
            logger.error("Failed to write control file: %s", e)
            return False

    @staticmethod
    def _check_relay_alive() -> bool:
        """Check if the prax-monitor systemd service is active."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "prax-monitor"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() == "active"
        except (subprocess.TimeoutExpired, OSError):
            return False
