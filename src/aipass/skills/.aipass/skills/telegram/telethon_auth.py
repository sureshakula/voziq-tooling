"""
One-time Telethon phone authentication.

Run this once to create the .telethon.session file needed for BotFather automation.
After that, Telethon can automate BotFather without re-authenticating.

Prerequisites:
    pip install telethon
    drone @api get-secret telethon_config  # must have api_id + api_hash

Usage:
    python3 telethon_auth.py

Session is saved to ~/.secrets/aipass/telegram/.telethon.session
"""

import asyncio
import json
import subprocess
from pathlib import Path

SESSION_DIR = Path.home() / ".secrets" / "aipass" / "telegram"
SESSION_PATH = SESSION_DIR / ".telethon"


def _get_secret(key: str) -> dict | None:
    """Fetch a secret from drone @api get-secret."""
    try:
        result = subprocess.run(
            ["drone", "@api", "get-secret", key, "--json"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except (subprocess.SubprocessError, json.JSONDecodeError):
        pass
    return None


async def main() -> None:
    from telethon import TelegramClient

    config = _get_secret("telethon_config")
    if not config or "api_id" not in config or "api_hash" not in config:
        print("ERROR: telethon_config secret not found or missing api_id/api_hash.")
        print('Set it with: drone @api set-secret telethon_config \'{"api_id": ..., "api_hash": "..."}\'')
        return

    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    client = TelegramClient(
        str(SESSION_PATH),
        config["api_id"],
        config["api_hash"],
    )
    await client.start()
    me = await client.get_me()
    print(f"\nAuthenticated as: {me.first_name} (ID: {me.id})")
    print(f"Session saved to: {SESSION_PATH}.session")
    print("Telethon setup complete! You can now use automated BotFather creation.")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
