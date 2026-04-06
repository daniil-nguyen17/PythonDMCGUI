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


# ---------------------------------------------------------------------------
# CRUD: create_user
# ---------------------------------------------------------------------------

def test_create_user(tmp_users_path):
    """create_user returns None on success, user appears in user_names with correct role."""
    am = AuthManager(str(tmp_users_path))
    result = am.create_user("Alice", "1111", "operator")
    assert result is None
    assert "Alice" in am.user_names
    assert am.get_role("Alice") == "operator"


def test_create_user_duplicate_name(tmp_users_path):
    """create_user rejects a name that already exists (Admin is a default user)."""
    am = AuthManager(str(tmp_users_path))
    result = am.create_user("Admin", "9999", "operator")
    assert isinstance(result, str) and len(result) > 0


def test_create_user_duplicate_pin(tmp_users_path):
    """create_user rejects a PIN already used by another user (Admin uses 0000)."""
    am = AuthManager(str(tmp_users_path))
    result = am.create_user("Alice", "0000", "operator")
    assert isinstance(result, str) and len(result) > 0


def test_create_user_invalid_pin_short(tmp_users_path):
    """create_user rejects a PIN shorter than 4 digits."""
    am = AuthManager(str(tmp_users_path))
    result = am.create_user("Alice", "123", "operator")
    assert isinstance(result, str) and len(result) > 0


def test_create_user_invalid_pin_long(tmp_users_path):
    """create_user rejects a PIN longer than 6 digits."""
    am = AuthManager(str(tmp_users_path))
    result = am.create_user("Alice", "1234567", "operator")
    assert isinstance(result, str) and len(result) > 0


def test_create_user_invalid_pin_letters(tmp_users_path):
    """create_user rejects a non-digit PIN."""
    am = AuthManager(str(tmp_users_path))
    result = am.create_user("Alice", "abcd", "operator")
    assert isinstance(result, str) and len(result) > 0


def test_create_user_empty_name(tmp_users_path):
    """create_user rejects an empty name."""
    am = AuthManager(str(tmp_users_path))
    result = am.create_user("", "1111", "operator")
    assert isinstance(result, str) and len(result) > 0


# ---------------------------------------------------------------------------
# CRUD: delete_user
# ---------------------------------------------------------------------------

def test_delete_user(tmp_users_path):
    """delete_user returns None on success, user removed from user_names."""
    am = AuthManager(str(tmp_users_path))
    result = am.delete_user("Operator")
    assert result is None
    assert "Operator" not in am.user_names


def test_delete_user_not_found(tmp_users_path):
    """delete_user returns error string for a nonexistent user."""
    am = AuthManager(str(tmp_users_path))
    result = am.delete_user("Ghost")
    assert isinstance(result, str) and len(result) > 0


def test_delete_last_admin_blocked(tmp_users_path):
    """delete_user blocks deletion of the last Admin; Admin remains in user_names."""
    am = AuthManager(str(tmp_users_path))
    # Remove all non-admin users first
    am.delete_user("Operator")
    am.delete_user("Setup")
    # Now only Admin remains — delete must be blocked
    result = am.delete_user("Admin")
    assert isinstance(result, str) and len(result) > 0
    assert "Admin" in am.user_names


# ---------------------------------------------------------------------------
# CRUD: update_user
# ---------------------------------------------------------------------------

def test_update_user_pin(tmp_users_path):
    """update_user changes PIN; validate_pin succeeds with new PIN."""
    am = AuthManager(str(tmp_users_path))
    result = am.update_user("Operator", new_pin="4321")
    assert result is None
    assert am.validate_pin("Operator", "4321") == "operator"


def test_update_user_pin_duplicate(tmp_users_path):
    """update_user rejects a PIN already used by another user."""
    am = AuthManager(str(tmp_users_path))
    # Admin uses 0000 — Operator cannot steal it
    result = am.update_user("Operator", new_pin="0000")
    assert isinstance(result, str) and len(result) > 0


def test_update_user_pin_same_user_ok(tmp_users_path):
    """update_user allows setting the same PIN (self-assignment is not a duplicate)."""
    am = AuthManager(str(tmp_users_path))
    # Operator's current PIN is 1234 — resetting to 1234 is valid
    result = am.update_user("Operator", new_pin="1234")
    assert result is None


def test_update_user_role(tmp_users_path):
    """update_user changes role; get_role reflects the new value."""
    am = AuthManager(str(tmp_users_path))
    result = am.update_user("Operator", new_role="setup")
    assert result is None
    assert am.get_role("Operator") == "setup"


def test_update_self_role_blocked(tmp_users_path):
    """update_user blocks self-demotion: Admin cannot change own role."""
    am = AuthManager(str(tmp_users_path))
    result = am.update_user("Admin", new_role="operator", current_user="Admin")
    assert isinstance(result, str) and len(result) > 0


def test_update_last_admin_demotion_blocked(tmp_users_path):
    """update_user blocks demotion of the sole remaining Admin by another user."""
    am = AuthManager(str(tmp_users_path))
    # Setup tries to demote Admin (only admin) — must be blocked
    result = am.update_user("Admin", new_role="operator", current_user="Setup")
    assert isinstance(result, str) and len(result) > 0


def test_update_user_name(tmp_users_path):
    """update_user renames a user; old name gone, new name present."""
    am = AuthManager(str(tmp_users_path))
    result = am.update_user("Operator", new_name="Joe")
    assert result is None
    assert "Joe" in am.user_names
    assert "Operator" not in am.user_names


def test_update_user_name_duplicate(tmp_users_path):
    """update_user rejects a new name that already belongs to another user."""
    am = AuthManager(str(tmp_users_path))
    result = am.update_user("Operator", new_name="Admin")
    assert isinstance(result, str) and len(result) > 0


def test_update_user_name_updates_last_user(tmp_users_path):
    """When the renamed user is last_user, last_user is updated to the new name."""
    am = AuthManager(str(tmp_users_path))
    # Log in as Operator so last_user = "Operator"
    am.validate_pin("Operator", "1234")
    assert am.last_user == "Operator"
    # Rename Operator -> Joe
    result = am.update_user("Operator", new_name="Joe")
    assert result is None
    assert am.last_user == "Joe"


# ---------------------------------------------------------------------------
# CRUD: get_all_users
# ---------------------------------------------------------------------------

def test_get_all_users(tmp_users_path):
    """get_all_users returns list of dicts with name, role, and pin_masked."""
    am = AuthManager(str(tmp_users_path))
    users = am.get_all_users()
    assert isinstance(users, list)
    assert len(users) == 3  # Admin, Operator, Setup by default
    for entry in users:
        assert "name" in entry
        assert "role" in entry
        assert "pin_masked" in entry
        # pin_masked should be bullet dots matching actual PIN length
        # Admin PIN is 0000 (4 digits) -> 4 bullet chars
        if entry["name"] == "Admin":
            assert len(entry["pin_masked"]) == 4
            assert all(c == "\u2022" for c in entry["pin_masked"])


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def test_crud_persists_to_disk(tmp_users_path):
    """After create_user, a fresh AuthManager loaded from the same path sees the new user."""
    am = AuthManager(str(tmp_users_path))
    am.create_user("Alice", "2222", "operator")

    am2 = AuthManager(str(tmp_users_path))
    assert "Alice" in am2.user_names
    assert am2.get_role("Alice") == "operator"
