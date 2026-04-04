"""AuthManager: PIN validation and user storage for DMC GUI."""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional


DEFAULT_USERS: Dict[str, Dict[str, str]] = {
    "Admin": {"pin": "0000", "role": "admin"},
    "Operator": {"pin": "1234", "role": "operator"},
    "Setup": {"pin": "5678", "role": "setup"},
}


class AuthManager:
    """Manages user authentication via PIN against a JSON file.

    Args:
        users_path: Absolute path to users.json. File is created with
                    defaults if it does not exist.
    """

    def __init__(self, users_path: str) -> None:
        self._path = users_path
        self._data: Dict = {}
        self._load()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load users.json from disk, creating defaults if absent."""
        if os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as fh:
                self._data = json.load(fh)
        else:
            self._data = {
                "last_user": "Operator",
                "users": {
                    name: dict(info) for name, info in DEFAULT_USERS.items()
                },
            }
            self._save()

    def _save(self) -> None:
        """Persist current state to users.json."""
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def user_names(self) -> List[str]:
        """Return list of all user names stored in users.json."""
        return list(self._data.get("users", {}).keys())

    @property
    def last_user(self) -> str:
        """Return the name of the last successfully logged-in user."""
        return self._data.get("last_user", "Operator")

    def validate_pin(self, username: str, pin: str) -> Optional[str]:
        """Validate a PIN for the given username.

        Returns the role string (e.g. ``"admin"``) on success, or ``None``
        on failure. On success, updates and persists ``last_user``.
        """
        users = self._data.get("users", {})
        user = users.get(username)
        if user is None:
            return None
        if user.get("pin") != pin:
            return None
        # Correct PIN — update last_user and persist
        self._data["last_user"] = username
        self._save()
        return user.get("role")

    def get_role(self, username: str) -> Optional[str]:
        """Return the role for the given username, or None if not found."""
        users = self._data.get("users", {})
        user = users.get(username)
        if user is None:
            return None
        return user.get("role")
