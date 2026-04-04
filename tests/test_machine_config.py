"""Tests for machine_config module — machine type registry, persistence, and API.

Run with: pytest tests/test_machine_config.py -x
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

# Ensure src is on path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import dmccodegui.machine_config as mc
from dmccodegui.app_state import MachineState


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


def test_registry_has_all_types():
    """MACHINE_TYPES contains exactly the 3 expected type strings."""
    assert mc.MACHINE_TYPES == [
        "4-Axes Flat Grind",
        "4-Axes Convex Grind",
        "3-Axes Serration Grind",
    ]


def test_flat_axis_list():
    """Flat Grind has 4 axes: A, B, C, D."""
    assert mc.get_axis_list("4-Axes Flat Grind") == ["A", "B", "C", "D"]


def test_convex_axis_list():
    """Convex Grind has 4 axes: A, B, C, D."""
    assert mc.get_axis_list("4-Axes Convex Grind") == ["A", "B", "C", "D"]


def test_serration_axis_list():
    """Serration Grind has 3 axes: A, B, C (no D)."""
    assert mc.get_axis_list("3-Axes Serration Grind") == ["A", "B", "C"]


def test_is_serration_true():
    """is_serration returns True for the Serration type."""
    assert mc.is_serration("3-Axes Serration Grind") is True


def test_is_serration_false_flat():
    """is_serration returns False for Flat Grind."""
    assert mc.is_serration("4-Axes Flat Grind") is False


def test_is_serration_false_convex():
    """is_serration returns False for Convex Grind."""
    assert mc.is_serration("4-Axes Convex Grind") is False


def test_has_bcomp_serration():
    """Serration registry entry has has_bcomp: True."""
    # Access via get_param_defs to avoid importing internal _REGISTRY
    # Use a dedicated helper check via is_serration + internal registry inspection
    import dmccodegui.machine_config as _mc
    entry = _mc._REGISTRY["3-Axes Serration Grind"]
    assert entry["has_bcomp"] is True


def test_has_bcomp_flat_convex():
    """Flat and Convex registry entries have has_bcomp: False."""
    import dmccodegui.machine_config as _mc
    assert _mc._REGISTRY["4-Axes Flat Grind"]["has_bcomp"] is False
    assert _mc._REGISTRY["4-Axes Convex Grind"]["has_bcomp"] is False


# ---------------------------------------------------------------------------
# Param defs tests
# ---------------------------------------------------------------------------


def test_param_defs_per_type():
    """get_param_defs returns a list of dicts, each with required keys."""
    required_keys = {"label", "var", "unit", "group", "min", "max"}
    for mtype in mc.MACHINE_TYPES:
        defs = mc.get_param_defs(mtype)
        assert isinstance(defs, list), f"{mtype}: expected list"
        assert len(defs) > 0, f"{mtype}: empty param_defs"
        for entry in defs:
            missing = required_keys - entry.keys()
            assert not missing, f"{mtype}: entry missing keys {missing}: {entry}"


def test_flat_param_defs_match_existing():
    """Flat Grind param_defs entries match PARAM_DEFS from parameters.py."""
    from dmccodegui.screens.parameters import PARAM_DEFS as EXPECTED

    flat_defs = mc.get_param_defs("4-Axes Flat Grind")
    # Every entry in EXPECTED must appear in flat_defs (by var name match)
    flat_vars = {d["var"] for d in flat_defs}
    for expected_entry in EXPECTED:
        assert expected_entry["var"] in flat_vars, (
            f"var '{expected_entry['var']}' from parameters.py missing from Flat Grind param_defs"
        )
    # Also verify label/unit/group/min/max match for each
    flat_by_var = {d["var"]: d for d in flat_defs}
    for expected_entry in EXPECTED:
        actual = flat_by_var[expected_entry["var"]]
        for key in ("label", "unit", "group", "min", "max"):
            assert actual[key] == expected_entry[key], (
                f"var '{expected_entry['var']}' key '{key}': "
                f"expected {expected_entry[key]!r}, got {actual[key]!r}"
            )


# ---------------------------------------------------------------------------
# Persistence tests
# ---------------------------------------------------------------------------


def test_not_configured_on_fresh_init():
    """Fresh init with nonexistent settings path -> is_configured() is False."""
    with tempfile.TemporaryDirectory() as tmpdir:
        nonexistent = os.path.join(tmpdir, "settings.json")
        mc.init(nonexistent)
        assert mc.is_configured() is False


def test_unknown_type_raises():
    """set_active_type with an unknown string raises ValueError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = os.path.join(tmpdir, "settings.json")
        mc.init(settings)
        with pytest.raises(ValueError):
            mc.set_active_type("bogus machine type")


def test_persistence_roundtrip():
    """set_active_type writes to settings.json; new init() reads it back correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = os.path.join(tmpdir, "settings.json")
        mc.init(settings)
        mc.set_active_type("3-Axes Serration Grind")
        assert mc.get_active_type() == "3-Axes Serration Grind"

        # Re-init from same path — should restore the saved type
        mc.init(settings)
        assert mc.get_active_type() == "3-Axes Serration Grind"
        assert mc.is_configured() is True


# ---------------------------------------------------------------------------
# MachineState extension tests
# ---------------------------------------------------------------------------


def test_machine_state_machine_type_field():
    """MachineState has a machine_type field defaulting to empty string."""
    state = MachineState()
    assert hasattr(state, "machine_type")
    assert state.machine_type == ""


def test_machine_state_notify_on_type_change():
    """Setting machine_type and calling notify() triggers subscriber."""
    state = MachineState()
    received: list[MachineState] = []

    state.subscribe(lambda s: received.append(s))

    state.machine_type = "4-Axes Flat Grind"
    state.notify()

    assert len(received) == 1
    assert received[0].machine_type == "4-Axes Flat Grind"
