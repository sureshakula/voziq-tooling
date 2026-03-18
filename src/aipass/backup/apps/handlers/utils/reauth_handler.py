# =================== AIPass ====================
# Name: reauth_handler.py
# Description: Google Drive Re-Authentication Handler
# Version: 1.0.0
# Created: 2026-02-20
# Modified: 2026-03-09
# =============================================

"""
Google Drive Re-Authentication Handler

Implementation logic for re-authenticating with Google Drive via console OAuth flow.
Called by the reauth_drive module orchestrator.
"""

from pathlib import Path

from aipass.backup.apps.handlers.json import json_handler

SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDS_PATH = Path.home() / '.aipass' / 'drive_creds.json'


def reauth(client_secrets_path: Path) -> bool:
    """Perform Google Drive re-authentication via console OAuth flow.

    Args:
        client_secrets_path: Path to the OAuth client secrets JSON file

    Returns:
        bool: True if authentication succeeded, False otherwise
    """
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[import-unresolved]
        from google.oauth2.credentials import Credentials  # type: ignore[import-unresolved]
        from google.auth.transport.requests import Request  # type: ignore[import-unresolved]
        from googleapiclient.discovery import build  # type: ignore[import-unresolved]
    except ImportError as e:
        return False

    json_handler.log_operation("reauth_initiated")

    # Step 1: Try refreshing existing token first
    if CREDS_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(CREDS_PATH), SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(CREDS_PATH, 'w', encoding='utf-8') as f:
                    f.write(creds.to_json())
                # Test connection
                service = build('drive', 'v3', credentials=creds)
                about = service.about().get(fields="user").execute()
                return True
        except Exception:
            pass  # Proceed with full re-authentication

    # Step 2: Full OAuth flow via console
    if not client_secrets_path.exists():
        return False

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)

    try:
        creds = flow.run_local_server(port=8085, open_browser=False)
    except Exception:
        return False

    # Save new credentials
    CREDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CREDS_PATH, 'w', encoding='utf-8') as f:
        f.write(creds.to_json())

    # Test connection
    try:
        service = build('drive', 'v3', credentials=creds)
        about = service.about().get(fields="user,storageQuota").execute()
        return True
    except Exception:
        return False
