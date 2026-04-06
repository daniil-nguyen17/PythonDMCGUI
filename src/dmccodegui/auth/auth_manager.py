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

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    def create_user(self, name: str, pin: str, role: str) -> Optional[str]:
        """Add a new user to users.json.

        Validates:
        - name is non-empty and not already in use
        - PIN is 4-6 digits only
        - PIN is not already used by another user

        Returns None on success, an error string on failure.
        """
        if not name:
            return "Name must not be empty."

        users = self._data.get("users", {})

        if name in users:
            return f"User '{name}' already exists."

        if not pin.isdigit() or not (4 <= len(pin) <= 6):
            return "PIN must be 4-6 digits."

        for existing_name, info in users.items():
            if info.get("pin") == pin:
                return f"PIN is already used by '{existing_name}'."

        users[name] = {"pin": pin, "role": role}
        self._save()
        return None

    def delete_user(self, name: str) -> Optional[str]:
        """Remove a user from users.json.

        Validates:
        - name exists
        - if the user is an admin, at least one other admin must remain

        Returns None on success, an error string on failure.
        """
        users = self._data.get("users", {})

        if name not in users:
            return f"User '{name}' not found."

        user_role = users[name].get("role")
        if user_role == "admin":
            admin_count = sum(
                1 for info in users.values() if info.get("role") == "admin"
            )
            if admin_count <= 1:
                return "Cannot delete the last Admin account."

        del users[name]
        self._save()
        return None

    def update_user(
        self,
        name: str,
        new_name: Optional[str] = None,
        new_pin: Optional[str] = None,
        new_role: Optional[str] = None,
        current_user: Optional[str] = None,
    ) -> Optional[str]:
        """Modify name, PIN, or role for an existing user.

        Validation rules (all run before any mutation):
        - User must exist
        - Role change blocks self-demotion (name == current_user)
        - Role change blocks demoting the last Admin
        - PIN must be 4-6 digits and not already used by a DIFFERENT user
        - New name must be non-empty and not a duplicate

        Returns None on success, an error string on failure.
        """
        users = self._data.get("users", {})

        if name not in users:
            return f"User '{name}' not found."

        # --- Validate role change ---
        if new_role is not None:
            if current_user is not None and name == current_user:
                return "You cannot change your own role."
            current_role = users[name].get("role")
            if current_role == "admin" and new_role != "admin":
                admin_count = sum(
                    1 for info in users.values() if info.get("role") == "admin"
                )
                if admin_count <= 1:
                    return "Cannot demote the last Admin account."

        # --- Validate PIN ---
        if new_pin is not None:
            if not new_pin.isdigit() or not (4 <= len(new_pin) <= 6):
                return "PIN must be 4-6 digits."
            for existing_name, info in users.items():
                if existing_name != name and info.get("pin") == new_pin:
                    return f"PIN is already used by '{existing_name}'."

        # --- Validate name change ---
        if new_name is not None:
            if not new_name:
                return "Name must not be empty."
            if new_name != name and new_name in users:
                return f"User '{new_name}' already exists."

        # --- Apply mutations ---
        entry = users[name]

        if new_pin is not None:
            entry["pin"] = new_pin

        if new_role is not None:
            entry["role"] = new_role

        if new_name is not None and new_name != name:
            users[new_name] = entry
            del users[name]
            # Keep last_user in sync with the renamed user
            if self._data.get("last_user") == name:
                self._data["last_user"] = new_name

        self._save()
        return None

    def get_all_users(self) -> list:
        """Return display-safe records for all users.

        Each entry is a dict with keys:
        - ``name`` (str): username
        - ``role`` (str): role string
        - ``pin_masked`` (str): bullet character (U+2022) repeated once per PIN digit
        """
        users = self._data.get("users", {})
        return [
            {
                "name": name,
                "role": info.get("role", ""),
                "pin_masked": "\u2022" * len(info.get("pin", "")),
            }
            for name, info in users.items()
        ]
