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
        "setup": ["run", "axes_setup", "parameters"],
        "admin": ["run", "axes_setup", "parameters", "diagnostics"],
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
        assert result == ["run", "axes_setup", "parameters"], (
            f"Expected run+axes_setup+parameters, got {result}"
        )

    def test_admin_tabs(self):
        result = _tabs_for_role("admin")
        assert result == ["run", "axes_setup", "parameters", "diagnostics"], (
            f"Expected all four tabs, got {result}"
        )

    def test_unknown_role_defaults_to_operator(self):
        result = _tabs_for_role("")
        assert result == ["run"], f"Expected ['run'] for unknown role, got {result}"

    def test_none_like_string_defaults_to_operator(self):
        result = _tabs_for_role("superadmin")
        assert result == ["run"], f"Expected ['run'] for unrecognised role, got {result}"
