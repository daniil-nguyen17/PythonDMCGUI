"""Unit tests for AuthManager."""
import json
import pytest

from dmccodegui.auth import AuthManager


def test_default_users_created(tmp_users_path):
    """When users.json does not exist, AuthManager creates it with Admin/Operator/Setup."""
    am = AuthManager(str(tmp_users_path))
    assert tmp_users_path.exists()
    data = json.loads(tmp_users_path.read_text())
    assert "Admin" in data["users"]
    assert "Operator" in data["users"]
    assert "Setup" in data["users"]
    assert data["users"]["Admin"]["pin"] == "0000"
    assert data["users"]["Operator"]["pin"] == "1234"
    assert data["users"]["Setup"]["pin"] == "5678"


def test_validate_pin_correct(tmp_users_path):
    """validate_pin returns role string on correct PIN."""
    am = AuthManager(str(tmp_users_path))
    result = am.validate_pin("Admin", "0000")
    assert result == "admin"


def test_validate_pin_wrong(tmp_users_path):
    """validate_pin returns None on wrong PIN."""
    am = AuthManager(str(tmp_users_path))
    result = am.validate_pin("Admin", "9999")
    assert result is None


def test_validate_pin_unknown_user(tmp_users_path):
    """validate_pin returns None for unknown user."""
    am = AuthManager(str(tmp_users_path))
    result = am.validate_pin("Nobody", "0000")
    assert result is None


def test_last_user_default(tmp_users_path):
    """On first boot, last_user is 'Operator'."""
    am = AuthManager(str(tmp_users_path))
    assert am.last_user == "Operator"


def test_last_user_persistence(tmp_users_path):
    """After successful validate_pin, last_user is updated and persists across reload."""
    am = AuthManager(str(tmp_users_path))
    am.validate_pin("Admin", "0000")
    assert am.last_user == "Admin"

    # Reload from disk
    am2 = AuthManager(str(tmp_users_path))
    assert am2.last_user == "Admin"


def test_user_names(tmp_users_path):
    """user_names returns list of all user names."""
    am = AuthManager(str(tmp_users_path))
    names = am.user_names
    assert isinstance(names, list)
    assert "Admin" in names
    assert "Operator" in names
    assert "Setup" in names


def test_existing_file_loads(tmp_users_path):
    """If users.json already exists with custom data, AuthManager loads it without overwriting."""
    custom_data = {
        "last_user": "Admin",
        "users": {
            "Custom": {"pin": "9999", "role": "admin"}
        }
    }
    tmp_users_path.write_text(json.dumps(custom_data))

    am = AuthManager(str(tmp_users_path))
    assert am.last_user == "Admin"
    assert "Custom" in am.user_names
    assert "Admin" not in am.user_names  # Defaults not added when file exists
