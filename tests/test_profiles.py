"""Tests for CSV Profile Engine — CSV-01, CSV-02, CSV-03 business logic.

All tests are pure Python (no Kivy). Uses tmp_path fixture for file I/O.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

from dmccodegui.screens.profiles import (
    KNOWN_ARRAYS,
    MACHINE_TYPE,
    compute_diff,
    export_profile,
    parse_profile_csv,
    validate_import,
)


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
        assert machine_rows[0][1] == MACHINE_TYPE

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
        assert result["machine_type"] == MACHINE_TYPE
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
            "machine_type": MACHINE_TYPE,
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
