"""Unit tests for MachineState auth fields."""
from unittest.mock import MagicMock

import pytest

from dmccodegui.app_state import MachineState


def test_initial_auth_fields():
    """Fresh MachineState has empty auth fields."""
    state = MachineState()
    assert state.current_user == ""
    assert state.current_role == ""
    assert state.setup_unlocked is False


def test_set_auth_admin():
    """set_auth('Admin', 'admin') sets user, role, and setup_unlocked=True."""
    state = MachineState()
    state.set_auth("Admin", "admin")
    assert state.current_user == "Admin"
    assert state.current_role == "admin"
    assert state.setup_unlocked is True


def test_set_auth_operator():
    """set_auth with 'operator' role sets setup_unlocked=False."""
    state = MachineState()
    state.set_auth("Op", "operator")
    assert state.current_user == "Op"
    assert state.current_role == "operator"
    assert state.setup_unlocked is False


def test_set_auth_setup():
    """set_auth with 'setup' role sets setup_unlocked=True."""
    state = MachineState()
    state.set_auth("Setup", "setup")
    assert state.current_user == "Setup"
    assert state.current_role == "setup"
    assert state.setup_unlocked is True


def test_set_auth_triggers_notify():
    """set_auth calls notify(), which triggers all listeners."""
    state = MachineState()
    listener = MagicMock()
    state.subscribe(listener)
    state.set_auth("Admin", "admin")
    listener.assert_called_once_with(state)


def test_lock_setup():
    """After set_auth with setup role, lock_setup() clears setup_unlocked."""
    state = MachineState()
    state.set_auth("Setup", "setup")
    assert state.setup_unlocked is True
    state.lock_setup()
    assert state.setup_unlocked is False


def test_lock_setup_triggers_notify():
    """lock_setup() calls notify(), which triggers all listeners."""
    state = MachineState()
    state.set_auth("Setup", "setup")
    listener = MagicMock()
    state.subscribe(listener)
    state.lock_setup()
    listener.assert_called_once_with(state)


def test_lock_setup_operator_noop():
    """lock_setup() on operator state still sets setup_unlocked=False without crash."""
    state = MachineState()
    state.set_auth("Op", "operator")
    assert state.setup_unlocked is False
    # Should not raise even though already False
    state.lock_setup()
    assert state.setup_unlocked is False
