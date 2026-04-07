"""Tests for CSV Profile Engine — CSV-01, CSV-02, CSV-03 business logic.

All tests are pure Python (no Kivy). Uses tmp_path fixture for file I/O.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

import dmccodegui.machine_config as mc
from dmccodegui.screens.profiles import (
    KNOWN_ARRAYS,
    compute_diff,
    export_profile,
    parse_profile_csv,
    validate_import,
)


@pytest.fixture(autouse=True)
def _init_machine_config(tmp_path):
    """Initialize machine_config with a temp settings file before each test."""
    mc.init(str(tmp_path / "settings.json"))
    mc.set_active_type("4-Axes Flat Grind")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scalars() -> dict:
    """Minimal valid scalar dict for export/round-trip tests."""
    return {"knfThk": 25.5, "edgeThk": 0.8, "fdA": 100.0}


def _make_arrays() -> dict:
    """Minimal valid arrays dict for export/round-trip tests."""
    return {"deltaA": [0.0, 0.5, 1.0, 1.5]}


# ---------------------------------------------------------------------------
# CSV-01: Export
# ---------------------------------------------------------------------------

class TestExportMetadataRows:
    """export_profile() writes correct metadata rows."""

    def test_export_writes_machine_type(self, tmp_path):
        path = tmp_path / "profile.csv"
        export_profile(path, "TestProfile", {}, {})
        rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
        machine_rows = [r for r in rows if r and r[0] == "_machine_type"]
        assert len(machine_rows) == 1
        assert machine_rows[0][1] == mc.get_active_type()

    def test_export_writes_profile_name(self, tmp_path):
        path = tmp_path / "profile.csv"
        export_profile(path, "MyProfile", {}, {})
        rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
        name_rows = [r for r in rows if r and r[0] == "_profile_name"]
        assert len(name_rows) == 1
        assert name_rows[0][1] == "MyProfile"

    def test_export_writes_export_date(self, tmp_path):
        path = tmp_path / "profile.csv"
        export_profile(path, "P", {}, {})
        rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
        date_rows = [r for r in rows if r and r[0] == "_export_date"]
        assert len(date_rows) == 1
        # Should be an ISO date string (non-empty)
        assert len(date_rows[0][1]) > 0
        # Basic ISO format check: contains 'T'
        assert "T" in date_rows[0][1]


class TestExportScalarsAndArrays:
    """export_profile() writes scalar and array data rows."""

    def test_export_writes_all_scalars(self, tmp_path):
        path = tmp_path / "profile.csv"
        scalars = {"knfThk": 25.5, "edgeThk": 0.8}
        export_profile(path, "P", scalars, {})
        rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
        row_map = {r[0]: r for r in rows if r}
        assert "knfThk" in row_map
        assert float(row_map["knfThk"][1]) == pytest.approx(25.5)
        assert "edgeThk" in row_map
        assert float(row_map["edgeThk"][1]) == pytest.approx(0.8)

    def test_export_writes_array_row(self, tmp_path):
        path = tmp_path / "profile.csv"
        arrays = {"deltaA": [0.0, 0.5, 1.0]}
        export_profile(path, "P", {}, arrays)
        rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
        array_rows = [r for r in rows if r and r[0] == "deltaA"]
        assert len(array_rows) == 1
        values = [float(v) for v in array_rows[0][1:]]
        assert values == pytest.approx([0.0, 0.5, 1.0])

    def test_export_csv_parseable(self, tmp_path):
        """Round-trip: exported CSV parses back without error."""
        path = tmp_path / "profile.csv"
        export_profile(path, "TestProfile", _make_scalars(), _make_arrays())
        # Should not raise
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert len(rows) > 0

    def test_export_newline_handling(self, tmp_path):
        """File must NOT contain bare \\r\\n double line endings (Windows artifact).

        On Windows, opening with newline='' prevents csv.writer from doubling \\r.
        We verify this by reading raw bytes and checking no \\r\\r is present.
        """
        path = tmp_path / "profile.csv"
        export_profile(path, "P", {"knfThk": 1.0}, {})
        raw = path.read_bytes()
        # No double carriage-return
        assert b"\r\r" not in raw


# ---------------------------------------------------------------------------
# CSV-02: Parse
# ---------------------------------------------------------------------------

class TestParseReturnsMetadata:
    """parse_profile_csv() extracts metadata correctly."""

    def test_parse_returns_metadata(self, tmp_path):
        path = tmp_path / "p.csv"
        export_profile(path, "RoundTrip", _make_scalars(), _make_arrays())
        result = parse_profile_csv(path)
        assert result["machine_type"] == mc.get_active_type()
        assert result["profile_name"] == "RoundTrip"
        assert "T" in result["export_date"]  # ISO date

    def test_parse_returns_scalars(self, tmp_path):
        path = tmp_path / "p.csv"
        scalars = {"knfThk": 25.5, "edgeThk": 0.8}
        export_profile(path, "P", scalars, {})
        result = parse_profile_csv(path)
        assert result["scalars"]["knfThk"] == pytest.approx(25.5)
        assert result["scalars"]["edgeThk"] == pytest.approx(0.8)

    def test_parse_returns_arrays(self, tmp_path):
        path = tmp_path / "p.csv"
        arrays = {"deltaA": [0.0, 0.5, 1.0]}
        export_profile(path, "P", {}, arrays)
        result = parse_profile_csv(path)
        assert result["arrays"]["deltaA"] == pytest.approx([0.0, 0.5, 1.0])

    def test_parse_skips_empty_rows(self, tmp_path):
        """CSV files with blank lines are parsed without error."""
        path = tmp_path / "p.csv"
        # Write CSV with intentional blank lines
        path.write_text(
            "_machine_type,TestMachine\n"
            "\n"
            "_profile_name,Blank\n"
            "\n"
            "_export_date,2026-01-01T00:00:00\n",
            encoding="utf-8",
        )
        result = parse_profile_csv(path)
        assert result["machine_type"] == "TestMachine"
        assert result["profile_name"] == "Blank"


class TestUnknownArrayNames:
    """parse_profile_csv() ignores unrecognized array names."""

    def test_unknown_array_names_skipped(self, tmp_path):
        """Rows with names not in KNOWN_ARRAYS are silently ignored."""
        path = tmp_path / "p.csv"
        path.write_text(
            "_machine_type,TestMachine\n"
            "_profile_name,P\n"
            "_export_date,2026-01-01T00:00:00\n"
            "unknownArray,1.0,2.0,3.0\n",
            encoding="utf-8",
        )
        result = parse_profile_csv(path)
        # 'unknownArray' must NOT appear in result arrays
        assert "unknownArray" not in result["arrays"]


# ---------------------------------------------------------------------------
# CSV-02: Diff
# ---------------------------------------------------------------------------

class TestComputeDiff:
    """compute_diff() returns correct diff rows."""

    def test_diff_only_changed(self):
        csv_scalars = {"knfThk": 25.5, "edgeThk": 0.8}
        current_scalars = {"knfThk": 30.0, "edgeThk": 0.8}  # only knfThk changed
        diff = compute_diff(csv_scalars, current_scalars, {}, {})
        names = [d["name"] for d in diff]
        assert "knfThk" in names
        assert "edgeThk" not in names

    def test_diff_numeric_comparison(self):
        """Float equality via tolerance — same float values must not appear in diff."""
        csv_scalars = {"knfThk": 25.5}
        current_scalars = {"knfThk": 25.5}
        diff = compute_diff(csv_scalars, current_scalars, {}, {})
        assert diff == []

    def test_diff_includes_arrays(self):
        """Arrays with changed elements appear in diff."""
        csv_arrays = {"deltaA": [0.0, 0.5, 1.0]}
        current_arrays = {"deltaA": [0.0, 0.5, 2.0]}  # last element changed
        diff = compute_diff({}, {}, csv_arrays, current_arrays)
        names = [d["name"] for d in diff]
        assert "deltaA" in names

    def test_diff_array_length_mismatch(self):
        """Arrays with different lengths appear in diff."""
        csv_arrays = {"deltaA": [0.0, 0.5]}
        current_arrays = {"deltaA": [0.0, 0.5, 1.0]}
        diff = compute_diff({}, {}, csv_arrays, current_arrays)
        names = [d["name"] for d in diff]
        assert "deltaA" in names

    def test_diff_identical_arrays_not_in_diff(self):
        """Identical arrays must NOT appear in diff."""
        csv_arrays = {"deltaA": [0.0, 0.5, 1.0]}
        current_arrays = {"deltaA": [0.0, 0.5, 1.0]}
        diff = compute_diff({}, {}, csv_arrays, current_arrays)
        assert diff == []

    def test_diff_returns_name_current_new(self):
        """Each diff row has 'name', 'current', and 'new' keys."""
        csv_scalars = {"knfThk": 30.0}
        current_scalars = {"knfThk": 25.5}
        diff = compute_diff(csv_scalars, current_scalars, {}, {})
        assert len(diff) == 1
        row = diff[0]
        assert "name" in row
        assert "current" in row
        assert "new" in row
        # current = value in live controller, new = value from CSV
        assert row["name"] == "knfThk"
        assert float(row["current"]) == pytest.approx(25.5)
        assert float(row["new"]) == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# CSV-03: Validation
# ---------------------------------------------------------------------------

class TestValidateImport:
    """validate_import() rejects invalid data and passes valid data."""

    def _valid_parsed(self) -> dict:
        return {
            "machine_type": mc.get_active_type(),
            "profile_name": "TestProfile",
            "export_date": "2026-01-01T00:00:00",
            "scalars": {"knfThk": 25.5, "edgeThk": 0.8},
            "arrays": {},
        }

    def test_machine_type_mismatch_blocked(self):
        parsed = self._valid_parsed()
        parsed["machine_type"] = "Wrong Machine"
        errors = validate_import(parsed)
        assert len(errors) == 1
        assert "machine" in errors[0].lower() or "type" in errors[0].lower()

    def test_machine_type_mismatch_skips_further_validation(self):
        """On machine_type mismatch, return immediately (single error only)."""
        parsed = self._valid_parsed()
        parsed["machine_type"] = "Wrong Machine"
        parsed["scalars"]["knfThk"] = 9999.0  # also invalid range
        errors = validate_import(parsed)
        # Should only have 1 error (the machine type error); range check is skipped
        assert len(errors) == 1

    def test_import_validates_scalar_range(self):
        """Out-of-range scalar value returns an error."""
        parsed = self._valid_parsed()
        parsed["scalars"]["knfThk"] = 9999.0  # max is 50.0
        errors = validate_import(parsed)
        assert len(errors) >= 1
        # Error message should mention the field name or 'range'
        assert any("knfThk" in e or "range" in e.lower() for e in errors)

    def test_import_validates_scalar_range_below_min(self):
        """Below-min scalar value returns an error."""
        parsed = self._valid_parsed()
        parsed["scalars"]["knfThk"] = 0.0  # min is 0.1
        errors = validate_import(parsed)
        assert len(errors) >= 1

    def test_import_validates_scalar_numeric(self):
        """Non-numeric scalar string returns an error."""
        parsed = self._valid_parsed()
        # Force a non-float value into scalars (as if parse had a bad row)
        parsed["scalars"]["knfThk"] = "not-a-number"
        errors = validate_import(parsed)
        assert len(errors) >= 1
        assert any("knfThk" in e or "numeric" in e.lower() for e in errors)

    def test_import_valid_returns_no_errors(self):
        """Fully valid parsed dict returns empty error list."""
        parsed = self._valid_parsed()
        errors = validate_import(parsed)
        assert errors == []

    def test_import_unknown_scalar_names_ignored(self):
        """Extra scalar vars not in PARAM_DEFS are silently ignored."""
        parsed = self._valid_parsed()
        parsed["scalars"]["unknownVar"] = 999.0
        errors = validate_import(parsed)
        assert errors == []

    def test_validate_import_uses_active_type(self):
        """validate_import checks against mc.get_active_type(), not a stale constant."""
        mc.set_active_type("3-Axes Serration Grind")
        parsed = self._valid_parsed()  # uses mc.get_active_type() which is now Serration
        errors = validate_import(parsed)
        assert errors == []
        # Reset
        mc.set_active_type("4-Axes Flat Grind")


# ---------------------------------------------------------------------------
# UI-01: motion_active gating on import button (ProfilesScreen._update_import_button)
# ---------------------------------------------------------------------------

class TestProfilesImportButtonGating:
    """_update_import_button() gates on dmc_state (motion_active) not cycle_running."""

    def _make_state(self, connected: bool, dmc_state: int):
        """Create a minimal mock state object."""
        from unittest.mock import MagicMock
        state = MagicMock()
        state.connected = connected
        state.dmc_state = dmc_state
        return state

    def _make_btn(self):
        """Create a mock button object."""
        from unittest.mock import MagicMock
        btn = MagicMock()
        btn.disabled = False
        btn.opacity = 1.0
        return btn

    def _make_screen(self, state, btn):
        """Create a minimal ProfilesScreen with a mock button in ids.

        Kivy's ids is an ObservableDict that can be updated with dict entries.
        We use ids.update() to inject the mock button without replacing ids itself.
        """
        import os
        os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
        os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
        from dmccodegui.screens.profiles import ProfilesScreen
        screen = ProfilesScreen.__new__(ProfilesScreen)
        screen._unsubscribe = None
        screen._pending_parsed = None
        screen.state = state
        screen.controller = None
        # Inject mock button into Kivy's ObservableDict via update()
        screen.ids.update({'import_btn': btn})
        return screen

    def test_import_disabled_when_grinding(self):
        """Import button is disabled when dmc_state=STATE_GRINDING and connected=True."""
        from dmccodegui.hmi.dmc_vars import STATE_GRINDING
        state = self._make_state(connected=True, dmc_state=STATE_GRINDING)
        btn = self._make_btn()
        screen = self._make_screen(state, btn)

        screen._update_import_button()

        assert btn.disabled is True, "Button should be disabled during GRINDING"
        assert btn.opacity == pytest.approx(0.4), "Opacity should be 0.4 during GRINDING"

    def test_import_disabled_when_homing(self):
        """Import button is disabled when dmc_state=STATE_HOMING and connected=True."""
        from dmccodegui.hmi.dmc_vars import STATE_HOMING
        state = self._make_state(connected=True, dmc_state=STATE_HOMING)
        btn = self._make_btn()
        screen = self._make_screen(state, btn)

        screen._update_import_button()

        assert btn.disabled is True, "Button should be disabled during HOMING"
        assert btn.opacity == pytest.approx(0.4), "Opacity should be 0.4 during HOMING"

    def test_import_disabled_when_disconnected(self):
        """Import button is disabled when connected=False."""
        from dmccodegui.hmi.dmc_vars import STATE_IDLE
        state = self._make_state(connected=False, dmc_state=STATE_IDLE)
        btn = self._make_btn()
        screen = self._make_screen(state, btn)

        screen._update_import_button()

        assert btn.disabled is True, "Button should be disabled when disconnected"
        assert btn.opacity == pytest.approx(0.4), "Opacity should be 0.4 when disconnected"

    def test_import_enabled_when_idle(self):
        """Import button is enabled when dmc_state=STATE_IDLE and connected=True."""
        from dmccodegui.hmi.dmc_vars import STATE_IDLE
        state = self._make_state(connected=True, dmc_state=STATE_IDLE)
        btn = self._make_btn()
        screen = self._make_screen(state, btn)

        screen._update_import_button()

        assert btn.disabled is False, "Button should be enabled when IDLE and connected"
        assert btn.opacity == pytest.approx(1.0), "Opacity should be 1.0 when IDLE"

    def test_import_enabled_when_setup(self):
        """Import button is enabled when dmc_state=STATE_SETUP and connected=True."""
        from dmccodegui.hmi.dmc_vars import STATE_SETUP
        state = self._make_state(connected=True, dmc_state=STATE_SETUP)
        btn = self._make_btn()
        screen = self._make_screen(state, btn)

        screen._update_import_button()

        assert btn.disabled is False, "Button should be enabled when SETUP and connected"
        assert btn.opacity == pytest.approx(1.0), "Opacity should be 1.0 when SETUP"


# ---------------------------------------------------------------------------
# Smart enter/exit tests (Plan 16-01)
# ---------------------------------------------------------------------------

def _make_profiles_screen(connected: bool, dmc_state: int):
    """Create a headless ProfilesScreen with mock controller and state.

    Uses __new__ to skip Kivy widget initialisation.
    """
    import os
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from unittest.mock import MagicMock
    from dmccodegui.screens.profiles import ProfilesScreen
    screen = ProfilesScreen.__new__(ProfilesScreen)
    screen._unsubscribe = None
    screen._pending_parsed = None
    ctrl = MagicMock()
    ctrl.is_connected.return_value = connected
    ctrl.cmd.return_value = ""
    screen.controller = ctrl
    state = MagicMock()
    state.dmc_state = dmc_state
    screen.state = state
    return screen, ctrl


def test_enter_skips_fire_when_already_setup():
    """SETP-01: on_pre_enter with dmc_state=STATE_SETUP does NOT send hmiSetp=0."""
    from unittest.mock import patch
    from dmccodegui.hmi.dmc_vars import STATE_SETUP

    screen, ctrl = _make_profiles_screen(connected=True, dmc_state=STATE_SETUP)

    with patch('dmccodegui.screens.profiles.Clock'):
        screen.on_pre_enter()

    calls = [c[0][0] for c in ctrl.cmd.call_args_list]
    assert not any('hmiSetp=0' in s for s in calls), \
        f"Should NOT send hmiSetp=0 when already in STATE_SETUP, got: {calls}"


def test_enter_does_not_fire_hmiSetp():
    """Profiles screen does not manage setup mode — no hmiSetp on enter."""
    from unittest.mock import patch
    from dmccodegui.hmi.dmc_vars import STATE_IDLE

    screen, ctrl = _make_profiles_screen(connected=True, dmc_state=STATE_IDLE)

    with patch('dmccodegui.screens.profiles.Clock'):
        screen.on_pre_enter()

    calls = [c[0][0] for c in ctrl.cmd.call_args_list] if ctrl.cmd.call_args_list else []
    assert not any('hmiSetp=0' in s for s in calls), \
        f"Profiles should NOT send hmiSetp=0, got: {calls}"


def test_exit_does_not_fire_hmiExSt():
    """Profiles screen does not manage setup mode — no hmiExSt on leave."""
    from unittest.mock import patch
    from dmccodegui.hmi.dmc_vars import STATE_IDLE

    screen, ctrl = _make_profiles_screen(connected=True, dmc_state=STATE_IDLE)

    with patch('dmccodegui.screens.profiles.Clock'):
        screen.on_leave()

    calls = [c[0][0] for c in ctrl.cmd.call_args_list] if ctrl.cmd.call_args_list else []
    assert not any('hmiExSt=0' in s for s in calls), \
        f"Profiles should NOT send hmiExSt=0, got: {calls}"


def test_exit_does_not_send_hmiSetp():
    """SETP-08: on_leave does NOT send hmiSetp=1 (old bug eliminated)."""
    from unittest.mock import patch
    from dmccodegui.hmi.dmc_vars import STATE_IDLE

    screen, ctrl = _make_profiles_screen(connected=True, dmc_state=STATE_IDLE)

    with patch('dmccodegui.screens.profiles.Clock'):
        screen.on_leave()

    calls = [c[0][0] for c in ctrl.cmd.call_args_list]
    assert not any('hmiSetp=1' in s for s in calls), \
        f"Should NOT send hmiSetp=1 on leave (old bug), got: {calls}"
