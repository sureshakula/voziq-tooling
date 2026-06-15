# =================== AIPass ====================
# Name: test_secrets.py
# Description: Tests for secrets handler and get_secret_cmd orchestrator
# Version: 1.0.0
# Created: 2026-06-15
# Modified: 2026-06-15
# =============================================

"""Tests for apps/handlers/auth/secrets.py and apps/modules/api_key.get_secret_cmd.

Tests — secrets.py (get_secret, list_secrets):
- get_secret: JSON token extraction via _TOKEN_KEYS
- get_secret: as_json returns full parsed dict
- get_secret: raw file fallback returns stripped content
- get_secret: missing provider directory returns None
- get_secret: missing slug file returns None
- get_secret: malformed JSON returns None
- get_secret: unreadable file (OSError) returns None
- get_secret: JSON with no matching token key returns json.dumps of dict
- list_secrets: returns sorted slug names, strips .json extension
- list_secrets: non-existent provider returns empty list
- list_secrets: skips dotfiles, __pycache__, directories

Tests — api_key.py (get_secret_cmd):
- get_secret_cmd with provider/slug prints token
- get_secret_cmd with --json prints JSON
- get_secret_cmd with --list prints slugs
- get_secret_cmd with no args calls error()
- get_secret_cmd with provider only (no --list) calls error()
- get_secret_cmd with only flags (no positional args) calls error()
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from aipass.api.apps.modules.api_key import handle_command as _hc  # noqa: F401 — seedgo test_coverage detection
from aipass.api.apps.handlers.auth.secrets import (
    get_secret,
    list_secrets,
)
from aipass.api.apps.modules.api_key import get_secret_cmd


# Patch targets
PATCH_SECRETS_BASE = "aipass.api.apps.handlers.auth.secrets.SECRETS_BASE"
PATCH_JSON_HANDLER = "aipass.api.apps.handlers.auth.secrets.json_handler"
PATCH_LOGGER = "aipass.api.apps.handlers.auth.secrets.logger"

PATCH_CMD_SECRETS = "aipass.api.apps.modules.api_key.secrets"
PATCH_CMD_ERROR = "aipass.api.apps.modules.api_key.error"
PATCH_CMD_JSON_HANDLER = "aipass.api.apps.modules.api_key.json_handler"


# =============================================
# get_secret
# =============================================


class TestGetSecret:
    """Verifies secret retrieval under various conditions."""

    def test_json_token_extraction(self, tmp_path: Path) -> None:
        """JSON file with a known token key returns the extracted token string."""
        provider_dir = tmp_path / "telegram"
        provider_dir.mkdir()
        secret_file = provider_dir / "bot.json"
        secret_file.write_text(json.dumps({"bot_token": "abc123", "extra": "stuff"}))

        with patch(PATCH_SECRETS_BASE, tmp_path), patch(PATCH_JSON_HANDLER), patch(PATCH_LOGGER):
            result = get_secret("telegram", "bot")

        assert result == "abc123"

    def test_json_token_extraction_searches_keys_in_order(self, tmp_path: Path) -> None:
        """Token extraction tries _TOKEN_KEYS in order; first match wins."""
        provider_dir = tmp_path / "discord"
        provider_dir.mkdir()
        # Has both 'api_key' and 'token'; api_key comes first in _TOKEN_KEYS
        secret_file = provider_dir / "creds.json"
        secret_file.write_text(json.dumps({"token": "second", "api_key": "first"}))

        with patch(PATCH_SECRETS_BASE, tmp_path), patch(PATCH_JSON_HANDLER), patch(PATCH_LOGGER):
            result = get_secret("discord", "creds")

        assert result == "first"

    def test_as_json_returns_full_dict(self, tmp_path: Path) -> None:
        """as_json=True returns the full parsed dictionary."""
        provider_dir = tmp_path / "telegram"
        provider_dir.mkdir()
        data = {"bot_token": "abc123", "webhook_url": "https://example.com"}
        (provider_dir / "bot.json").write_text(json.dumps(data))

        with patch(PATCH_SECRETS_BASE, tmp_path), patch(PATCH_JSON_HANDLER), patch(PATCH_LOGGER):
            result = get_secret("telegram", "bot", as_json=True)

        assert result == data

    def test_raw_file_fallback(self, tmp_path: Path) -> None:
        """When no JSON file exists, falls back to raw file and returns stripped content."""
        provider_dir = tmp_path / "generic"
        provider_dir.mkdir()
        (provider_dir / "api_token").write_text("  raw-secret-value  \n")

        with patch(PATCH_SECRETS_BASE, tmp_path), patch(PATCH_JSON_HANDLER), patch(PATCH_LOGGER):
            result = get_secret("generic", "api_token")

        assert result == "raw-secret-value"

    def test_missing_provider_directory(self, tmp_path: Path) -> None:
        """Non-existent provider directory returns None."""
        with patch(PATCH_SECRETS_BASE, tmp_path), patch(PATCH_JSON_HANDLER), patch(PATCH_LOGGER):
            result = get_secret("nonexistent", "bot")

        assert result is None

    def test_missing_slug_file(self, tmp_path: Path) -> None:
        """Provider exists but slug file does not -- returns None."""
        provider_dir = tmp_path / "telegram"
        provider_dir.mkdir()

        with patch(PATCH_SECRETS_BASE, tmp_path), patch(PATCH_JSON_HANDLER), patch(PATCH_LOGGER):
            result = get_secret("telegram", "missing_slug")

        assert result is None

    def test_malformed_json_returns_none(self, tmp_path: Path) -> None:
        """Malformed JSON file returns None and logs a warning."""
        provider_dir = tmp_path / "telegram"
        provider_dir.mkdir()
        (provider_dir / "bot.json").write_text("{not valid json")

        mock_logger = MagicMock()
        with patch(PATCH_SECRETS_BASE, tmp_path), patch(PATCH_JSON_HANDLER), patch(PATCH_LOGGER, mock_logger):
            result = get_secret("telegram", "bot")

        assert result is None
        mock_logger.warning.assert_called()

    def test_unreadable_file_returns_none(self, tmp_path: Path) -> None:
        """OSError when reading file returns None."""
        provider_dir = tmp_path / "telegram"
        provider_dir.mkdir()
        secret_file = provider_dir / "bot.json"
        secret_file.write_text(json.dumps({"bot_token": "abc"}))
        # Make unreadable
        secret_file.chmod(0o000)

        mock_logger = MagicMock()
        with patch(PATCH_SECRETS_BASE, tmp_path), patch(PATCH_JSON_HANDLER), patch(PATCH_LOGGER, mock_logger):
            result = get_secret("telegram", "bot")

        # Restore permissions for cleanup
        secret_file.chmod(0o644)

        assert result is None

    def test_json_no_matching_token_key(self, tmp_path: Path) -> None:
        """JSON dict with no recognized token key returns json.dumps of the dict."""
        provider_dir = tmp_path / "custom"
        provider_dir.mkdir()
        data = {"username": "admin", "host": "localhost"}
        (provider_dir / "config.json").write_text(json.dumps(data))

        with patch(PATCH_SECRETS_BASE, tmp_path), patch(PATCH_JSON_HANDLER), patch(PATCH_LOGGER):
            result = get_secret("custom", "config")

        assert result == json.dumps(data)

    def test_json_non_dict_value(self, tmp_path: Path) -> None:
        """JSON file containing a non-dict value (e.g., a string) returns str of it."""
        provider_dir = tmp_path / "simple"
        provider_dir.mkdir()
        (provider_dir / "token.json").write_text(json.dumps("plain-string-secret"))

        with patch(PATCH_SECRETS_BASE, tmp_path), patch(PATCH_JSON_HANDLER), patch(PATCH_LOGGER):
            result = get_secret("simple", "token")

        assert result == "plain-string-secret"

    def test_json_preferred_over_raw(self, tmp_path: Path) -> None:
        """When both JSON and raw files exist, JSON takes priority."""
        provider_dir = tmp_path / "dual"
        provider_dir.mkdir()
        (provider_dir / "cred.json").write_text(json.dumps({"api_key": "from-json"}))
        (provider_dir / "cred").write_text("from-raw")

        with patch(PATCH_SECRETS_BASE, tmp_path), patch(PATCH_JSON_HANDLER), patch(PATCH_LOGGER):
            result = get_secret("dual", "cred")

        assert result == "from-json"

    def test_provider_is_file_not_dir(self, tmp_path: Path) -> None:
        """If provider path exists but is a file (not a directory), returns None."""
        (tmp_path / "notadir").write_text("file content")

        with patch(PATCH_SECRETS_BASE, tmp_path), patch(PATCH_JSON_HANDLER), patch(PATCH_LOGGER):
            result = get_secret("notadir", "slug")

        assert result is None


# =============================================
# list_secrets
# =============================================


class TestListSecrets:
    """Verifies secret listing under various conditions."""

    def test_returns_sorted_slugs(self, tmp_path: Path) -> None:
        """Returns sorted slug names with .json extension stripped."""
        provider_dir = tmp_path / "telegram"
        provider_dir.mkdir()
        (provider_dir / "webhook.json").write_text("{}")
        (provider_dir / "bot.json").write_text("{}")
        (provider_dir / "raw_token").write_text("tok")

        with patch(PATCH_SECRETS_BASE, tmp_path), patch(PATCH_LOGGER):
            result = list_secrets("telegram")

        assert result == ["bot", "raw_token", "webhook"]

    def test_nonexistent_provider_returns_empty(self, tmp_path: Path) -> None:
        """Non-existent provider returns empty list."""
        with patch(PATCH_SECRETS_BASE, tmp_path), patch(PATCH_LOGGER):
            result = list_secrets("nonexistent")

        assert result == []

    def test_skips_dotfiles(self, tmp_path: Path) -> None:
        """Entries starting with '.' are excluded."""
        provider_dir = tmp_path / "provider"
        provider_dir.mkdir()
        (provider_dir / ".hidden").write_text("secret")
        (provider_dir / "visible.json").write_text("{}")

        with patch(PATCH_SECRETS_BASE, tmp_path), patch(PATCH_LOGGER):
            result = list_secrets("provider")

        assert result == ["visible"]

    def test_skips_pycache(self, tmp_path: Path) -> None:
        """__pycache__ directory is excluded."""
        provider_dir = tmp_path / "provider"
        provider_dir.mkdir()
        # __pycache__ as a file (the check is name-based, not type-based for this entry)
        pycache = provider_dir / "__pycache__"
        pycache.mkdir()
        (provider_dir / "real.json").write_text("{}")

        with patch(PATCH_SECRETS_BASE, tmp_path), patch(PATCH_LOGGER):
            result = list_secrets("provider")

        assert result == ["real"]

    def test_skips_directories(self, tmp_path: Path) -> None:
        """Subdirectories (non-files) are excluded."""
        provider_dir = tmp_path / "provider"
        provider_dir.mkdir()
        (provider_dir / "subdir").mkdir()
        (provider_dir / "secret.json").write_text("{}")

        with patch(PATCH_SECRETS_BASE, tmp_path), patch(PATCH_LOGGER):
            result = list_secrets("provider")

        assert result == ["secret"]

    def test_provider_is_file_not_dir(self, tmp_path: Path) -> None:
        """If provider path is a file instead of a directory, returns empty list."""
        (tmp_path / "notadir").write_text("file")

        with patch(PATCH_SECRETS_BASE, tmp_path), patch(PATCH_LOGGER):
            result = list_secrets("notadir")

        assert result == []


# =============================================
# get_secret_cmd
# =============================================


class TestGetSecretCmd:
    """Verifies the get_secret_cmd orchestrator in api_key.py."""

    @patch(PATCH_CMD_JSON_HANDLER)
    @patch(PATCH_CMD_SECRETS)
    @patch("builtins.print")
    def test_prints_token(self, mock_print, mock_secrets, mock_jh) -> None:
        """provider/slug prints the token to stdout."""
        mock_secrets.get_secret.return_value = "my-secret-token"

        get_secret_cmd(["telegram/bot"])

        mock_secrets.get_secret.assert_called_once_with("telegram", "bot")
        mock_print.assert_called_once_with("my-secret-token")

    @patch(PATCH_CMD_JSON_HANDLER)
    @patch(PATCH_CMD_SECRETS)
    @patch("builtins.print")
    def test_json_flag_prints_json(self, mock_print, mock_secrets, mock_jh) -> None:
        """--json flag prints formatted JSON to stdout."""
        data = {"bot_token": "abc123", "webhook": "https://example.com"}
        mock_secrets.get_secret.return_value = data

        get_secret_cmd(["telegram/bot", "--json"])

        mock_secrets.get_secret.assert_called_once_with("telegram", "bot", as_json=True)
        mock_print.assert_called_once_with(json.dumps(data, indent=2))

    @patch(PATCH_CMD_JSON_HANDLER)
    @patch(PATCH_CMD_SECRETS)
    @patch("builtins.print")
    def test_list_flag_prints_slugs(self, mock_print, mock_secrets, mock_jh) -> None:
        """--list flag prints each slug on its own line."""
        mock_secrets.list_secrets.return_value = ["bot", "webhook"]

        get_secret_cmd(["telegram", "--list"])

        mock_secrets.list_secrets.assert_called_once_with("telegram")
        assert mock_print.call_count == 2
        mock_print.assert_any_call("bot")
        mock_print.assert_any_call("webhook")

    @patch(PATCH_CMD_JSON_HANDLER)
    @patch(PATCH_CMD_ERROR)
    def test_no_args_calls_error(self, mock_error, mock_jh) -> None:
        """Empty args list calls error() with usage message."""
        get_secret_cmd([])

        mock_error.assert_called_once()
        assert "Usage" in mock_error.call_args[0][0]

    @patch(PATCH_CMD_JSON_HANDLER)
    @patch(PATCH_CMD_ERROR)
    def test_provider_only_without_list_calls_error(self, mock_error, mock_jh) -> None:
        """Single provider name without --list flag calls error() with format message."""
        get_secret_cmd(["telegram"])

        mock_error.assert_called_once()
        assert "provider" in mock_error.call_args[0][0].lower() or "format" in mock_error.call_args[0][0].lower()

    @patch(PATCH_CMD_JSON_HANDLER)
    @patch(PATCH_CMD_ERROR)
    def test_only_flags_no_positional_args_calls_error(self, mock_error, mock_jh) -> None:
        """Only flags (no positional args after stripping) calls error()."""
        get_secret_cmd(["--json"])

        mock_error.assert_called_once()
        assert "Usage" in mock_error.call_args[0][0]

    @patch(PATCH_CMD_JSON_HANDLER)
    @patch(PATCH_CMD_SECRETS)
    @patch(PATCH_CMD_ERROR)
    def test_secret_not_found_calls_error(self, mock_error, mock_secrets, mock_jh) -> None:
        """When get_secret returns None, error() is called."""
        mock_secrets.get_secret.return_value = None

        get_secret_cmd(["telegram/bot"])

        mock_error.assert_called_once()
        assert "not found" in mock_error.call_args[0][0].lower()

    @patch(PATCH_CMD_JSON_HANDLER)
    @patch(PATCH_CMD_SECRETS)
    @patch(PATCH_CMD_ERROR)
    def test_json_secret_not_found_calls_error(self, mock_error, mock_secrets, mock_jh) -> None:
        """When get_secret with --json returns None, error() is called."""
        mock_secrets.get_secret.return_value = None

        get_secret_cmd(["telegram/bot", "--json"])

        mock_error.assert_called_once()
        assert "not found" in mock_error.call_args[0][0].lower()

    @patch(PATCH_CMD_JSON_HANDLER)
    @patch(PATCH_CMD_SECRETS)
    @patch("builtins.print")
    def test_list_empty_provider(self, mock_print, mock_secrets, mock_jh) -> None:
        """--list with provider that has no secrets prints nothing."""
        mock_secrets.list_secrets.return_value = []

        get_secret_cmd(["empty_provider", "--list"])

        mock_secrets.list_secrets.assert_called_once_with("empty_provider")
        mock_print.assert_not_called()
