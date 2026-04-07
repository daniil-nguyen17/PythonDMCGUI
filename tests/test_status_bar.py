"""Unit tests for StatusBar state label and color.

Tests update_from_state() state_text and state_color properties using a
simple namespace mock — no Kivy event loop required, since StatusBar is a
BoxLayout that can be instantiated headlessly.
"""
from __future__ import annotations

import types
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(**kwargs) -> object:
    """Return a namespace object with MachineState-like fields."""
    defaults = {
        "connected": False,
        "connected_address": "",
        "current_user": "",
        "current_role": "",
        "machine_type": "",
        "program_running": True,
        "dmc_state": 0,
    }
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def _make_status_bar():
    """Instantiate StatusBar without a running Kivy app."""
    from dmccodegui.screens.status_bar import StatusBar
    return StatusBar()


# ---------------------------------------------------------------------------
# TestStatusBarStateLabel
# ---------------------------------------------------------------------------

class TestStatusBarStateLabel:
    """Tests for state_text and state_color on StatusBar."""

    def test_state_text_idle(self):
        """state_text is 'IDLE' when connected=True, dmc_state=1."""
        sb = _make_status_bar()
        state = _make_state(connected=True, dmc_state=1)
        sb.update_from_state(state)
        assert sb.state_text == "IDLE", f"Expected 'IDLE', got '{sb.state_text}'"

    def test_state_color_idle_is_orange(self):
        """state_color is orange when dmc_state=1 (IDLE)."""
        sb = _make_status_bar()
        state = _make_state(connected=True, dmc_state=1)
        sb.update_from_state(state)
        r, g, b, a = sb.state_color
        # Orange: high red, moderate green, low blue
        assert r > 0.9, f"Red channel should be high for orange, got {r}"
        assert g > 0.4, f"Green channel should be moderate for orange, got {g}"
        assert b < 0.1, f"Blue channel should be low for orange, got {b}"

    def test_state_text_grinding(self):
        """state_text is 'GRINDING' when connected=True, dmc_state=2."""
        sb = _make_status_bar()
        state = _make_state(connected=True, dmc_state=2)
        sb.update_from_state(state)
        assert sb.state_text == "GRINDING", f"Expected 'GRINDING', got '{sb.state_text}'"

    def test_state_color_grinding_is_green(self):
        """state_color is green when dmc_state=2 (GRINDING)."""
        sb = _make_status_bar()
        state = _make_state(connected=True, dmc_state=2)
        sb.update_from_state(state)
        r, g, b, a = sb.state_color
        assert g > 0.6, f"Green channel should be high for grinding green, got {g}"
        assert r < 0.3, f"Red channel should be low for grinding green, got {r}"

    def test_state_text_setup(self):
        """state_text is 'SETUP' when connected=True, dmc_state=3."""
        sb = _make_status_bar()
        state = _make_state(connected=True, dmc_state=3)
        sb.update_from_state(state)
        assert sb.state_text == "SETUP", f"Expected 'SETUP', got '{sb.state_text}'"

    def test_state_color_setup_is_red(self):
        """state_color is red when dmc_state=3 (SETUP)."""
        sb = _make_status_bar()
        state = _make_state(connected=True, dmc_state=3)
        sb.update_from_state(state)
        r, g, b, a = sb.state_color
        assert r > 0.7, f"Red channel should be high for setup red, got {r}"
        assert g < 0.4, f"Green channel should be low for setup red, got {g}"

    def test_state_text_homing(self):
        """state_text is 'HOMING' when connected=True, dmc_state=4."""
        sb = _make_status_bar()
        state = _make_state(connected=True, dmc_state=4)
        sb.update_from_state(state)
        assert sb.state_text == "HOMING", f"Expected 'HOMING', got '{sb.state_text}'"

    def test_state_color_homing_is_orange(self):
        """state_color is orange when dmc_state=4 (HOMING)."""
        sb = _make_status_bar()
        state = _make_state(connected=True, dmc_state=4)
        sb.update_from_state(state)
        r, g, b, a = sb.state_color
        assert r > 0.9, f"Red channel should be high for homing orange, got {r}"
        assert b < 0.1, f"Blue channel should be low for homing orange, got {b}"

    def test_state_text_offline_when_connected_false_program_running(self):
        """state_text is 'OFFLINE' when connected=False and program_running=True."""
        sb = _make_status_bar()
        state = _make_state(connected=False, program_running=True, dmc_state=2)
        sb.update_from_state(state)
        assert sb.state_text == "OFFLINE", f"Expected 'OFFLINE', got '{sb.state_text}'"

    def test_state_color_offline_is_gray(self):
        """state_color is gray when disconnected and program_running=True."""
        sb = _make_status_bar()
        state = _make_state(connected=False, program_running=True)
        sb.update_from_state(state)
        r, g, b, a = sb.state_color
        # Gray: all channels close to each other and mid-range
        assert abs(r - g) < 0.15, f"Gray should have balanced channels, got r={r} g={g}"
        assert abs(r - b) < 0.15, f"Gray should have balanced channels, got r={r} b={b}"

    def test_state_text_estop_when_connected_false_program_not_running(self):
        """state_text is 'E-STOP' when connected=False and program_running=False."""
        sb = _make_status_bar()
        state = _make_state(connected=False, program_running=False)
        sb.update_from_state(state)
        assert sb.state_text == "E-STOP", f"Expected 'E-STOP', got '{sb.state_text}'"

    def test_state_color_estop_is_red(self):
        """state_color is red when E-STOP state (connected=False, program_running=False)."""
        sb = _make_status_bar()
        state = _make_state(connected=False, program_running=False)
        sb.update_from_state(state)
        r, g, b, a = sb.state_color
        assert r > 0.7, f"Red channel should be high for E-STOP, got {r}"
        assert g < 0.4, f"Green channel should be low for E-STOP, got {g}"

    def test_state_text_offline_when_connected_uninitialized(self):
        """state_text is 'OFFLINE' when connected=True but dmc_state=0 (uninitialized)."""
        sb = _make_status_bar()
        state = _make_state(connected=True, dmc_state=0)
        sb.update_from_state(state)
        assert sb.state_text == "OFFLINE", f"Expected 'OFFLINE' for uninitialized dmc_state=0, got '{sb.state_text}'"

    def test_recover_enabled_chain(self):
        """RECOVER button state follows the full connect/disconnect/E-STOP lifecycle."""
        sb = _make_status_bar()

        # Cold-start: disconnected, program_running=True -> RECOVER disabled
        state = _make_state(connected=False, program_running=True)
        sb.update_from_state(state)
        assert sb.recover_enabled is False, (
            f"Cold-start: recover_enabled should be False, got {sb.recover_enabled}"
        )

        # Post E-STOP disconnect: disconnected, program_running=False -> RECOVER disabled
        state = _make_state(connected=False, program_running=False)
        sb.update_from_state(state)
        assert sb.recover_enabled is False, (
            f"E-STOP disconnect: recover_enabled should be False, got {sb.recover_enabled}"
        )

        # Reconnect with stopped program: connected=True, program_running=False -> RECOVER enabled
        state = _make_state(connected=True, program_running=False)
        sb.update_from_state(state)
        assert sb.recover_enabled is True, (
            f"Reconnect with stopped program: recover_enabled should be True, got {sb.recover_enabled}"
        )

    def test_prev_dmc_state_change_detection(self):
        """Calling update_from_state twice with same dmc_state does not change state_text."""
        sb = _make_status_bar()
        # First call — sets state
        state1 = _make_state(connected=True, dmc_state=1)
        sb.update_from_state(state1)
        assert sb.state_text == "IDLE"

        # Override state_text to something else to detect if it's re-set
        sb.state_text = "TAMPERED"

        # Second call with same dmc_state and same connected — change detection should skip
        state2 = _make_state(connected=True, dmc_state=1)
        sb.update_from_state(state2)
        assert sb.state_text == "TAMPERED", (
            "_prev_dmc_state change detection should skip redundant update"
        )
