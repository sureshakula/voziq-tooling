# Standard library
import argparse
import sys
import time
from pathlib import Path

# Sibling import
from .base_bot import BaseBot

# Logging
from aipass.prax import logger


# =============================================
# BranchPlugin CLASS
# =============================================


class BranchPlugin(BaseBot):
    """
    Per-branch Telegram bot that extends BaseBot with branch-specific behavior.

    Overrides BaseBot hooks to prefix messages, tag responses, and trigger
    the AIPass startup protocol when a new tmux session is created.
    """

    def __init__(self, branch_name: str, **kwargs) -> None:
        """
        Initialize BranchPlugin.

        Args:
            branch_name: AIPass branch name (e.g., "dev_central", "seed")
            **kwargs: All BaseBot constructor arguments (bot_id, bot_token, etc.)
        """
        self.branch_name = branch_name
        super().__init__(**kwargs)

    # =============================================
    # HOOK OVERRIDES
    # =============================================

    def on_message(self, text: str) -> str:
        """
        Prefix incoming messages with sender attribution.

        Args:
            text: Raw message text from Telegram

        Returns:
            Prefixed text for Claude: "{sender_name} via Telegram: {text}"
        """
        sender = getattr(self, "_current_sender_name", "User")
        return f"{sender} via Telegram: {text}"

    def on_response(self, text: str) -> str:
        """
        Prefix outgoing responses with branch tag.

        Args:
            text: Raw response text from Claude

        Returns:
            Tagged text: "@{branch_name}\n{text}"
        """
        return f"@{self.branch_name}\n{text}"

    def on_session_create(self, session_name: str, work_dir: Path) -> None:
        """
        Inject "hi" after tmux session creation to trigger startup protocol.

        Waits 2 seconds for Claude to fully initialize, then injects "hi"
        which triggers the AIPass startup sequence (reading memories, etc.).

        Args:
            session_name: The tmux session name that was created
            work_dir: The working directory of the session
        """
        logger.info(
            "Branch session created for @%s, injecting startup greeting",
            self.branch_name,
        )
        time.sleep(2)
        self.inject_message("hi")


# =============================================
# CLI ENTRY POINT
# =============================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIPass Telegram Branch Bot")
    parser.add_argument("--bot-id", required=True, help="Bot identifier")
    parser.add_argument("--config", help="Path to bot config JSON")
    args = parser.parse_args()

    from .config import load_bot_config

    config = load_bot_config(args.bot_id)
    if not config:
        print(f"No config found for bot_id={args.bot_id}")
        sys.exit(1)

    shared_session = config.get("shared_session")

    if config.get("branch_name"):
        bot = BranchPlugin(
            branch_name=config["branch_name"],
            bot_id=args.bot_id,
            bot_token=config["bot_token"],
            work_dir=Path(config["work_dir"]),
            bot_name=config.get("bot_name", f"AIPass {config['branch_name']} Bot"),
            allowed_user_ids=config.get("allowed_user_ids", []),
            shared_session=shared_session,
        )
    else:
        bot = BaseBot(
            bot_id=args.bot_id,
            bot_token=config["bot_token"],
            work_dir=Path(config.get("work_dir", str(Path.home()))),
            bot_name=config.get("bot_name", "AIPass Bot"),
            allowed_user_ids=config.get("allowed_user_ids", []),
            shared_session=shared_session,
        )

    sys.exit(bot.run())
