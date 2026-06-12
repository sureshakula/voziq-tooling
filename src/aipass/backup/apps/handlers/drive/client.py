# =================== AIPass ====================
# Name: client.py
# Description: Google Drive client — auth, folders, file lookup via @api gateway
# Version: 1.0.0
# Created: 2026-04-16
# Modified: 2026-06-12
# =============================================

"""Google Drive client.

Core Drive v3 client routed through the @api gateway.  Handles
authentication, folder creation/lookup, and file discovery.
Never uses console-OAuth -- all auth flows through
``aipass.api.apps.modules.google_client``.
"""

from __future__ import annotations

import threading
from typing import Any

from aipass.prax import logger

from ..json import json_handler

try:
    from aipass.api.apps.modules.google_client import (
        api_call_with_retry,
        get_drive_service,
    )

    GOOGLE_API_AVAILABLE = True
except ImportError:
    logger.info("Google API client libraries not available")
    GOOGLE_API_AVAILABLE = False
    get_drive_service = None  # type: ignore[assignment]
    api_call_with_retry = None  # type: ignore[assignment]


BACKUP_FOLDER_NAME = "AIPass Backups"
FOLDER_MIME = "application/vnd.google-apps.folder"


class DriveClient:
    """Google Drive v3 client backed by the @api gateway."""

    def __init__(self) -> None:
        self._drive_service: Any = None
        self._thread_local = threading.local()
        self._folder_cache_lock = threading.Lock()
        self.backup_folder_id: str | None = None
        self.project_folder_cache: dict[str, str] = {}
        self.file_tracker: dict[str, dict] = {}
        self.last_error: str | None = None

    # -- properties ----------------------------------------------------------

    @property
    def drive_service(self) -> Any:
        """Return thread-local service if set, otherwise main service."""
        return getattr(self._thread_local, "service", None) or self._drive_service

    # -- auth ----------------------------------------------------------------

    def authenticate(self) -> bool:
        """Authenticate through the @api gateway.

        Returns:
            True if a Drive service was obtained, False otherwise.
        """
        if not GOOGLE_API_AVAILABLE:
            self.last_error = "Google API libraries not installed"
            json_handler.log_operation(
                "drive_authenticate",
                {"success": False, "reason": self.last_error},
            )
            return False

        try:
            self._drive_service = get_drive_service(thread_safe=False)  # type: ignore[misc]
            if self._drive_service is None:
                self.last_error = "get_drive_service returned None"
                json_handler.log_operation(
                    "drive_authenticate",
                    {"success": False, "reason": self.last_error},
                )
                return False
            json_handler.log_operation("drive_authenticate", {"success": True})
            return True
        except Exception as exc:
            self.last_error = str(exc)
            logger.warning(f"Drive authentication failed: {exc}")
            json_handler.log_operation(
                "drive_authenticate",
                {"success": False, "error": self.last_error},
            )
            return False

    # -- low-level API -------------------------------------------------------

    def _api_call(self, request: Any, max_retries: int = 3) -> Any:
        """Execute a Google API request with retry.

        On failure, rebuilds the thread-local service and retries once.
        """
        try:
            return api_call_with_retry(request, max_retries=max_retries)  # type: ignore[misc]
        except Exception as first_exc:
            # Rebuild thread service and retry once
            logger.info(f"API call failed, rebuilding thread service: {first_exc}")
            try:
                self._thread_local.service = self._build_thread_service()
                return api_call_with_retry(request, max_retries=1)  # type: ignore[misc]
            except Exception as exc:
                self.last_error = str(exc)
                logger.info(f"API call retry also failed: {exc}")
                return None

    def _build_thread_service(self) -> Any:
        """Build an isolated Drive service for the current thread."""
        return get_drive_service(thread_safe=True)  # type: ignore[misc]

    # -- folder ops ----------------------------------------------------------

    def _verify_folder_id(self, folder_id: str) -> bool:
        """Check that a folder exists and is not trashed."""
        if not self.drive_service:
            return False
        try:
            request = self.drive_service.files().get(fileId=folder_id, fields="id,trashed")
            result = self._api_call(request)
            if result is None:
                return False
            return not result.get("trashed", True)
        except Exception as exc:
            logger.info(f"Failed to verify folder {folder_id}: {exc}")
            return False

    def get_or_create_backup_folder(self) -> str | None:
        """Get or create the root 'AIPass Backups' folder.

        Returns:
            Folder ID or None on failure.
        """
        if not self.drive_service:
            return None

        # Search for existing
        query = f"name='{BACKUP_FOLDER_NAME}' and mimeType='{FOLDER_MIME}' and trashed=false"
        try:
            request = self.drive_service.files().list(q=query, spaces="drive", fields="files(id,name)")
            result = self._api_call(request)
            if result and result.get("files"):
                self.backup_folder_id = result["files"][0]["id"]
                json_handler.log_operation(
                    "get_backup_folder",
                    {"action": "found_existing", "folder_id": self.backup_folder_id},
                )
                return self.backup_folder_id
        except Exception as exc:
            self.last_error = str(exc)
            logger.warning(f"Failed to search for backup folder: {exc}")
            return None

        # Create new
        try:
            metadata = {"name": BACKUP_FOLDER_NAME, "mimeType": FOLDER_MIME}
            request = self.drive_service.files().create(body=metadata, fields="id")
            result = self._api_call(request)
            if result:
                self.backup_folder_id = result["id"]
                self.file_tracker = {}
                json_handler.log_operation(
                    "get_backup_folder",
                    {"action": "created_new", "folder_id": self.backup_folder_id},
                )
                return self.backup_folder_id
        except Exception as exc:
            self.last_error = str(exc)
            logger.warning(f"Failed to create backup folder: {exc}")

        return None

    def get_or_create_project_folder(self, project_name: str) -> str | None:
        """Get or create a project subfolder under AIPass Backups.

        Thread-safe via lock.

        Returns:
            Folder ID or None on failure.
        """
        with self._folder_cache_lock:
            if project_name in self.project_folder_cache:
                return self.project_folder_cache[project_name]

        if not self.backup_folder_id:
            self.backup_folder_id = self.get_or_create_backup_folder()
            if not self.backup_folder_id:
                return None

        query = (
            f"name='{project_name}' "
            f"and mimeType='{FOLDER_MIME}' "
            f"and '{self.backup_folder_id}' in parents "
            f"and trashed=false"
        )
        try:
            request = self.drive_service.files().list(q=query, spaces="drive", fields="files(id,name)")
            result = self._api_call(request)
            if result and result.get("files"):
                folder_id = result["files"][0]["id"]
                with self._folder_cache_lock:
                    self.project_folder_cache[project_name] = folder_id
                return folder_id
        except Exception as exc:
            self.last_error = str(exc)
            logger.warning(f"Failed to search for project folder '{project_name}': {exc}")
            return None

        # Create
        try:
            metadata = {
                "name": project_name,
                "mimeType": FOLDER_MIME,
                "parents": [self.backup_folder_id],
            }
            request = self.drive_service.files().create(body=metadata, fields="id")
            result = self._api_call(request)
            if result:
                folder_id = result["id"]
                with self._folder_cache_lock:
                    self.project_folder_cache[project_name] = folder_id
                return folder_id
        except Exception as exc:
            self.last_error = str(exc)
            logger.warning(f"Failed to create project folder '{project_name}': {exc}")

        return None

    def get_or_create_nested_folder(
        self,
        parent_id: str,
        folder_path: str,
    ) -> str | None:
        """Create a nested folder hierarchy segment by segment.

        Thread-safe via lock.

        Args:
            parent_id: ID of the parent folder.
            folder_path: Slash-separated path of nested folders.

        Returns:
            ID of the deepest folder, or None on failure.
        """
        current_parent = parent_id
        segments = [s for s in folder_path.split("/") if s]

        for segment in segments:
            cache_key = f"{current_parent}/{segment}"
            with self._folder_cache_lock:
                if cache_key in self.project_folder_cache:
                    current_parent = self.project_folder_cache[cache_key]
                    continue

            # Search for existing
            query = f"name='{segment}' and mimeType='{FOLDER_MIME}' and '{current_parent}' in parents and trashed=false"
            try:
                request = self.drive_service.files().list(q=query, spaces="drive", fields="files(id,name)")
                result = self._api_call(request)
                if result and result.get("files"):
                    folder_id = result["files"][0]["id"]
                    with self._folder_cache_lock:
                        self.project_folder_cache[cache_key] = folder_id
                    current_parent = folder_id
                    continue
            except Exception as exc:
                self.last_error = str(exc)
                logger.info(f"Failed to search for nested folder '{segment}': {exc}")
                return None

            # Create
            try:
                metadata = {
                    "name": segment,
                    "mimeType": FOLDER_MIME,
                    "parents": [current_parent],
                }
                request = self.drive_service.files().create(body=metadata, fields="id")
                result = self._api_call(request)
                if result:
                    folder_id = result["id"]
                    with self._folder_cache_lock:
                        self.project_folder_cache[cache_key] = folder_id
                    current_parent = folder_id
                else:
                    return None
            except Exception as exc:
                self.last_error = str(exc)
                logger.info(f"Failed to create nested folder '{segment}': {exc}")
                return None

        return current_parent

    # -- file ops ------------------------------------------------------------

    def _find_existing_file(
        self,
        filename: str,
        parent_folder_id: str,
    ) -> dict | None:
        """Find a file by name in a folder (excludes trashed).

        Returns:
            File metadata dict with id/name, or None if not found.
        """
        query = f"name='{filename}' and '{parent_folder_id}' in parents and trashed=false"
        try:
            request = self.drive_service.files().list(q=query, spaces="drive", fields="files(id,name)")
            result = self._api_call(request)
            if result and result.get("files"):
                return result["files"][0]
        except Exception as exc:
            logger.info(f"Failed to find file {filename}: {exc}")
        return None


# =============================================
