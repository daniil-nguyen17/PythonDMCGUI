"""Tests for main app structure (UI-04: NoTransition)."""
import os
import pytest


def test_no_transition():
    """Verify base.kv declares NoTransition on the ScreenManager."""
    base_kv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "src", "dmccodegui", "ui", "base.kv"
    )
    with open(base_kv_path, "r") as f:
        content = f.read()
    assert "NoTransition" in content, (
        "base.kv must use NoTransition on ScreenManager (UI-04)"
    )
    # Also verify the import line exists
    assert "#:import NoTransition" in content, (
        "base.kv must import NoTransition from kivy.uix.screenmanager"
    )
