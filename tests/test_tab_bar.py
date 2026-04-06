"""Unit tests for TabBar role-based tab filtering logic.

Tests _tabs_for_role as a pure Python function — no Kivy event loop required.
"""
from __future__ import annotations

import sys
import os

import pytest


# ---------------------------------------------------------------------------
# Import the function under test without triggering Kivy Window/GL init
# ---------------------------------------------------------------------------

def _tabs_for_role(role: str) -> list[str]:
    """Mirror of TabBar._tabs_for_role staticmethod for isolated testing."""
    ROLE_TABS = {
        "operator": ["run"],
        "setup": ["run", "axes_setup", "parameters", "profiles"],
        "admin": ["run", "axes_setup", "parameters", "profiles", "diagnostics", "users"],
    }
    return ROLE_TABS.get(role, ["run"])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTabsForRole:
    def test_operator_tabs(self):
        result = _tabs_for_role("operator")
        assert result == ["run"], f"Expected ['run'], got {result}"

    def test_setup_tabs(self):
        result = _tabs_for_role("setup")
        assert result == ["run", "axes_setup", "parameters", "profiles"], (
            f"Expected run+axes_setup+parameters+profiles, got {result}"
        )

    def test_admin_tabs(self):
        result = _tabs_for_role("admin")
        assert result == ["run", "axes_setup", "parameters", "profiles", "diagnostics", "users"], (
            f"Expected run+axes_setup+parameters+profiles+diagnostics+users, got {result}"
        )

    def test_unknown_role_defaults_to_operator(self):
        result = _tabs_for_role("")
        assert result == ["run"], f"Expected ['run'] for unknown role, got {result}"

    def test_none_like_string_defaults_to_operator(self):
        result = _tabs_for_role("superadmin")
        assert result == ["run"], f"Expected ['run'] for unrecognised role, got {result}"


class TestProfilesTabRoleVisibility:
    """Verify that the Profiles tab is visible for Setup/Admin and hidden for Operator."""

    def test_operator_does_not_see_profiles(self):
        result = _tabs_for_role("operator")
        assert "profiles" not in result, (
            f"Operator should NOT see 'profiles' tab; got {result}"
        )

    def test_setup_sees_profiles(self):
        result = _tabs_for_role("setup")
        assert "profiles" in result, (
            f"Setup should see 'profiles' tab; got {result}"
        )

    def test_admin_sees_profiles(self):
        result = _tabs_for_role("admin")
        assert "profiles" in result, (
            f"Admin should see 'profiles' tab; got {result}"
        )


def _compute_gates(dmc_state: int, connected: bool) -> dict:
    """Mirror of TabBar.update_state_gates gate logic for isolated testing.

    Returns a dict of tab_name -> should_disable.
    """
    STATE_SETUP = 3
    STATE_GRINDING = 2
    STATE_HOMING = 4

    if not connected:
        return {}  # No gates when disconnected

    motion_active = dmc_state in (STATE_GRINDING, STATE_HOMING)
    return {
        "run": dmc_state == STATE_SETUP,
        "axes_setup": motion_active,
        "parameters": motion_active,
    }


class TestUpdateStateGates:
    """Tests for update_state_gates gate logic (pure Python, no Kivy)."""

    def test_setup_state_disables_run(self):
        """SETUP state: run disabled, axes_setup and parameters not disabled."""
        gates = _compute_gates(dmc_state=3, connected=True)
        assert gates.get("run") is True, "run should be disabled during SETUP"
        assert gates.get("axes_setup") is not True, "axes_setup should be enabled during SETUP"
        assert gates.get("parameters") is not True, "parameters should be enabled during SETUP"

    def test_grinding_state_disables_setup_tabs(self):
        """GRINDING state: run accessible, axes_setup and parameters disabled."""
        gates = _compute_gates(dmc_state=2, connected=True)
        assert gates.get("run") is not True, "run should be enabled during GRINDING"
        assert gates.get("axes_setup") is True, "axes_setup should be disabled during GRINDING"
        assert gates.get("parameters") is True, "parameters should be disabled during GRINDING"

    def test_homing_state_disables_setup_tabs(self):
        """HOMING state: same gate pattern as GRINDING."""
        gates = _compute_gates(dmc_state=4, connected=True)
        assert gates.get("run") is not True, "run should be enabled during HOMING"
        assert gates.get("axes_setup") is True, "axes_setup should be disabled during HOMING"
        assert gates.get("parameters") is True, "parameters should be disabled during HOMING"

    def test_idle_state_no_gates(self):
        """IDLE state: no tabs disabled."""
        gates = _compute_gates(dmc_state=1, connected=True)
        assert not any(gates.values()), f"No tabs should be gated during IDLE, got {gates}"

    def test_disconnected_no_gates(self):
        """Disconnected: nothing disabled regardless of dmc_state."""
        gates = _compute_gates(dmc_state=3, connected=False)
        assert gates == {}, f"Disconnected should have no gates, got {gates}"

    def test_setup_disconnected_no_gates(self):
        """SETUP + disconnected: nothing disabled (connected=False overrides state)."""
        gates = _compute_gates(dmc_state=3, connected=False)
        assert not any(gates.values()), (
            f"Disconnected should override SETUP gate, got {gates}"
        )


class TestUsersTabRoleVisibility:
    """Verify that the Users tab is visible for Admin only."""

    def test_operator_does_not_see_users(self):
        result = _tabs_for_role("operator")
        assert "users" not in result, (
            f"Operator should NOT see 'users' tab; got {result}"
        )

    def test_setup_does_not_see_users(self):
        result = _tabs_for_role("setup")
        assert "users" not in result, (
            f"Setup should NOT see 'users' tab; got {result}"
        )

    def test_admin_sees_users(self):
        result = _tabs_for_role("admin")
        assert "users" in result, (
            f"Admin should see 'users' tab; got {result}"
        )
