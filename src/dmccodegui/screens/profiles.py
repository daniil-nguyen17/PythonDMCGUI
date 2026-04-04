"""CSV Profile Engine — pure Python, no Kivy dependency.

Provides export, import parsing, diff computation, and validation for
knife-profile CSV files. All functions are testable headless.

This module is the foundation for Plan 02 (ProfilesScreen UI).
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from dmccodegui.screens.parameters import PARAM_DEFS

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

MACHINE_TYPE: str = "4-Axes Flat Grind"
"""Hard-coded machine type. Phase 6 will add a proper machine-type module."""

KNOWN_ARRAYS: list[str] = ["deltaA", "deltaB", "deltaC", "deltaD"]
"""Array variable names that can be exported/imported in profiles."""

# Internal lookup: var name -> param def dict
_PARAM_BY_VAR: dict[str, dict] = {p["var"]: p for p in PARAM_DEFS}


# ---------------------------------------------------------------------------
# 1. Export
# ---------------------------------------------------------------------------

def export_profile(
    path: Path,
    profile_name: str,
    scalars: dict[str, Any],
    arrays: dict[str, list[float]],
    machine_type: str = MACHINE_TYPE,
) -> None:
    """Write a knife profile to a CSV file.

    File layout:
      - 3 metadata rows: _machine_type, _export_date, _profile_name
      - One scalar row per entry in `scalars`: [var_name, value]
      - One array row per entry in `arrays`:  [array_name, val1, val2, ...]

    Args:
        path: Destination path (will be created/overwritten).
        profile_name: Human-readable name stored in _profile_name row.
        scalars: Dict mapping var names to numeric values.
        arrays: Dict mapping array names to lists of floats.
        machine_type: Machine type string (defaults to MACHINE_TYPE constant).
    """
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)

        # Metadata rows
        writer.writerow(["_machine_type", machine_type])
        writer.writerow(["_export_date", datetime.now().isoformat(timespec="seconds")])
        writer.writerow(["_profile_name", profile_name])

        # Scalar rows
        for var_name, value in scalars.items():
            writer.writerow([var_name, value])

        # Array rows — format each float with :.6g to keep precision without trailing zeros
        for array_name, values in arrays.items():
            row = [array_name] + [f"{v:.6g}" for v in values]
            writer.writerow(row)


# ---------------------------------------------------------------------------
# 2. Parse
# ---------------------------------------------------------------------------

def parse_profile_csv(path: Path) -> dict:
    """Parse a profile CSV file into structured data.

    Returns:
        {
            'machine_type': str,
            'profile_name': str,
            'export_date': str,
            'scalars': {var_name: float},
            'arrays': {array_name: [float, ...]},
        }

    Rules:
        - Rows starting with '_' are metadata.
        - Rows whose key is a known scalar var (in PARAM_DEFS) are scalars.
        - Rows with key in KNOWN_ARRAYS and >1 value column are arrays.
        - Empty rows are silently skipped.
        - Unrecognized rows are silently ignored.
    """
    result: dict = {
        "machine_type": "",
        "profile_name": "",
        "export_date": "",
        "scalars": {},
        "arrays": {},
    }

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        for row in reader:
            # Skip empty rows
            if not row or all(cell.strip() == "" for cell in row):
                continue

            key = row[0]

            # Metadata rows
            if key.startswith("_"):
                if key == "_machine_type" and len(row) >= 2:
                    result["machine_type"] = row[1]
                elif key == "_profile_name" and len(row) >= 2:
                    result["profile_name"] = row[1]
                elif key == "_export_date" and len(row) >= 2:
                    result["export_date"] = row[1]
                # other _keys silently ignored
                continue

            # Array rows (multi-value, known name)
            if key in KNOWN_ARRAYS and len(row) > 1:
                try:
                    result["arrays"][key] = [float(v) for v in row[1:]]
                except ValueError:
                    pass  # malformed array — skip
                continue

            # Scalar rows (known var name, single value)
            if key in _PARAM_BY_VAR and len(row) >= 2:
                try:
                    result["scalars"][key] = float(row[1])
                except ValueError:
                    pass  # non-numeric scalar — skip
                continue

            # Unrecognized row — silently ignored

    return result


# ---------------------------------------------------------------------------
# 3. Diff
# ---------------------------------------------------------------------------

def compute_diff(
    csv_scalars: dict[str, Any],
    current_scalars: dict[str, Any],
    csv_arrays: dict[str, list[float]],
    current_arrays: dict[str, list[float]],
) -> list[dict]:
    """Compare CSV values against current controller values and return changed rows.

    Args:
        csv_scalars: Scalar values from the imported CSV file.
        current_scalars: Current scalar values from the live controller.
        csv_arrays: Array values from the imported CSV file.
        current_arrays: Current array values from the live controller.

    Returns:
        List of dicts with keys 'name', 'current', 'new' for each changed value.
        'current' is the live controller value; 'new' is the CSV (import) value.
        Empty list if no differences found.

    Note:
        Float equality uses abs(a - b) < 1e-9 to avoid spurious string diffs.
    """
    diffs: list[dict] = []

    # Scalar comparison — only compare vars present in CSV
    for var_name, csv_val in csv_scalars.items():
        ctrl_val = current_scalars.get(var_name)
        if ctrl_val is None:
            # Variable not in current controller state — include as changed
            diffs.append({
                "name": var_name,
                "current": "",
                "new": str(csv_val),
            })
            continue

        try:
            csv_float = float(csv_val)
            ctrl_float = float(ctrl_val)
        except (ValueError, TypeError):
            # Cannot compare numerically — treat as changed
            diffs.append({
                "name": var_name,
                "current": str(ctrl_val),
                "new": str(csv_val),
            })
            continue

        if abs(csv_float - ctrl_float) >= 1e-9:
            diffs.append({
                "name": var_name,
                "current": str(ctrl_float),
                "new": str(csv_float),
            })

    # Array comparison — only compare arrays present in CSV
    for array_name, csv_vals in csv_arrays.items():
        ctrl_vals = current_arrays.get(array_name, [])

        # Different lengths => changed
        if len(csv_vals) != len(ctrl_vals):
            diffs.append({
                "name": array_name,
                "current": ",".join(str(v) for v in ctrl_vals),
                "new": ",".join(str(v) for v in csv_vals),
            })
            continue

        # Element-wise comparison
        changed = any(
            abs(float(cv) - float(av)) >= 1e-9
            for cv, av in zip(csv_vals, ctrl_vals)
        )
        if changed:
            diffs.append({
                "name": array_name,
                "current": ",".join(str(v) for v in ctrl_vals),
                "new": ",".join(str(v) for v in csv_vals),
            })

    return diffs


# ---------------------------------------------------------------------------
# 4. Validate
# ---------------------------------------------------------------------------

def validate_import(parsed: dict) -> list[str]:
    """Validate a parsed profile dict before applying to the controller.

    Validation order:
      1. Machine type must match MACHINE_TYPE (if mismatch, return immediately).
      2. Each known scalar is checked for numeric type and min/max range.

    Args:
        parsed: Output of parse_profile_csv() or equivalent dict with keys
                'machine_type', 'scalars'.

    Returns:
        List of error strings. Empty list means the profile is valid.
        Unknown scalar var names are silently ignored.
    """
    errors: list[str] = []

    # Step 1: Machine type check
    if parsed.get("machine_type", "") != MACHINE_TYPE:
        errors.append(
            f"Machine type mismatch: CSV has '{parsed.get('machine_type', '')}', "
            f"expected '{MACHINE_TYPE}'"
        )
        return errors  # stop validation here

    # Step 2: Scalar range and numeric checks
    scalars = parsed.get("scalars", {})
    for var_name, value in scalars.items():
        param = _PARAM_BY_VAR.get(var_name)
        if param is None:
            # Unknown var — silently ignore per locked decision
            continue

        # Numeric check
        try:
            float_val = float(value)
        except (ValueError, TypeError):
            errors.append(
                f"'{var_name}' has non-numeric value: {value!r}"
            )
            continue

        # Range check
        if not (param["min"] <= float_val <= param["max"]):
            errors.append(
                f"'{var_name}' value {float_val} is out of range "
                f"[{param['min']}, {param['max']}]"
            )

    return errors
