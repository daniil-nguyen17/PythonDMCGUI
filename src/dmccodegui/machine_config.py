"""machine_config — single source of truth for machine type data.

Provides the registry of all known machine types with their axis lists,
has_bcomp flags, and parameter definitions. Handles persistence of the
active machine type to settings.json.

Public API
----------
MACHINE_TYPES        : list[str]  — ordered list of all type strings
init(settings_path)  : load (or create) settings file, set active type
get_active_type()    : str — currently active type, or "" if unconfigured
set_active_type(t)   : persist and activate a type; raises ValueError if unknown
is_configured()      : bool — True once a valid type has been set/loaded
get_param_defs(t)    : list[dict] — param defs for the given (or active) type
get_axis_list(t)     : list[str] — axis identifiers for the given (or active) type
is_serration(t)      : bool — True only for 3-Axes Serration Grind
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

MACHINE_TYPES: List[str] = [
    "4-Axes Flat Grind",
    "4-Axes Convex Grind",
    "3-Axes Serration Grind",
]

# ---------------------------------------------------------------------------
# Parameter definitions
# ---------------------------------------------------------------------------

# Flat Grind param_defs — matches PARAM_DEFS in screens/parameters.py exactly.
_FLAT_PARAM_DEFS: List[Dict] = [
    # Geometry group
    {"label": "Knife Thickness", "var": "knfThk", "unit": "mm", "group": "Geometry", "min": 0.1, "max": 50.0},
    {"label": "Edge Thickness", "var": "edgeThk", "unit": "mm", "group": "Geometry", "min": 0.01, "max": 10.0},
    # Feedrates group
    {"label": "Feed Rate A", "var": "fdA", "unit": "mm/s", "group": "Feedrates", "min": 0.1, "max": 500.0},
    {"label": "Feed Rate B", "var": "fdB", "unit": "mm/s", "group": "Feedrates", "min": 0.1, "max": 500.0},
    {"label": "Feed Rate C Down", "var": "fdCdn", "unit": "mm/s", "group": "Feedrates", "min": 0.1, "max": 500.0},
    {"label": "Feed Rate C Up", "var": "fdCup", "unit": "mm/s", "group": "Feedrates", "min": 0.1, "max": 500.0},
    {"label": "Feed Rate Park", "var": "fdPark", "unit": "mm/s", "group": "Feedrates", "min": 0.1, "max": 500.0},
    {"label": "Feed Rate D", "var": "fdD", "unit": "mm/s", "group": "Feedrates", "min": 0.1, "max": 500.0},
    # Calibration group (pitch/ratio/ctsRev x 4 axes)
    {"label": "Pitch A", "var": "pitchA", "unit": "mm/rev", "group": "Calibration", "min": 0.001, "max": 100.0},
    {"label": "Pitch B", "var": "pitchB", "unit": "mm/rev", "group": "Calibration", "min": 0.001, "max": 100.0},
    {"label": "Pitch C", "var": "pitchC", "unit": "mm/rev", "group": "Calibration", "min": 0.001, "max": 100.0},
    {"label": "Pitch D", "var": "pitchD", "unit": "deg/rev", "group": "Calibration", "min": 0.001, "max": 3600.0},
    {"label": "Ratio A", "var": "ratioA", "unit": "", "group": "Calibration", "min": 0.001, "max": 1000.0},
    {"label": "Ratio B", "var": "ratioB", "unit": "", "group": "Calibration", "min": 0.001, "max": 1000.0},
    {"label": "Ratio C", "var": "ratioC", "unit": "", "group": "Calibration", "min": 0.001, "max": 1000.0},
    {"label": "Ratio D", "var": "ratioD", "unit": "", "group": "Calibration", "min": 0.001, "max": 1000.0},
    {"label": "Counts/Rev A", "var": "ctsRevA", "unit": "cts", "group": "Calibration", "min": 1.0, "max": 1000000.0},
    {"label": "Counts/Rev B", "var": "ctsRevB", "unit": "cts", "group": "Calibration", "min": 1.0, "max": 1000000.0},
    {"label": "Counts/Rev C", "var": "ctsRevC", "unit": "cts", "group": "Calibration", "min": 1.0, "max": 1000000.0},
    {"label": "Counts/Rev D", "var": "ctsRevD", "unit": "cts", "group": "Calibration", "min": 1.0, "max": 1000000.0},
]

# TODO: Convex Grind param_defs — placeholder copy of Flat.
# Real DMC variable list will be provided by the customer in a later update.
_CONVEX_PARAM_DEFS: List[Dict] = [d.copy() for d in _FLAT_PARAM_DEFS]

# TODO: Serration Grind param_defs — subset of Flat, D-axis entries removed.
# Real DMC variable list will be provided by the customer in a later update.
_D_AXIS_VARS = {"fdD", "pitchD", "ratioD", "ctsRevD"}
_SERRATION_PARAM_DEFS: List[Dict] = [
    d.copy() for d in _FLAT_PARAM_DEFS if d["var"] not in _D_AXIS_VARS
]

# ---------------------------------------------------------------------------
# Internal registry
# ---------------------------------------------------------------------------

_REGISTRY: Dict[str, Dict] = {
    "4-Axes Flat Grind": {
        "axes": ["A", "B", "C", "D"],
        "has_bcomp": False,
        "param_defs": _FLAT_PARAM_DEFS,
    },
    "4-Axes Convex Grind": {
        "axes": ["A", "B", "C", "D"],
        "has_bcomp": False,
        "param_defs": _CONVEX_PARAM_DEFS,
    },
    "3-Axes Serration Grind": {
        "axes": ["A", "B", "C"],
        "has_bcomp": True,
        "param_defs": _SERRATION_PARAM_DEFS,
    },
}

# ---------------------------------------------------------------------------
# Module-level state (reset by init())
# ---------------------------------------------------------------------------

_settings_path: str = ""
_active_type: str = ""
_configured: bool = False

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def init(settings_path: str) -> None:
    """Initialize the machine config module.

    Loads the active machine type from ``settings_path`` if the file exists
    and contains a valid ``machine_type`` key. If the file does not exist or
    the stored value is not a known type, the module starts unconfigured.

    Args:
        settings_path: Absolute path to settings.json (may not exist yet).
    """
    global _settings_path, _active_type, _configured

    _settings_path = settings_path
    _active_type = ""
    _configured = False

    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            stored = data.get("machine_type", "")
            if stored in _REGISTRY:
                _active_type = stored
                _configured = True
        except (json.JSONDecodeError, OSError):
            pass


def get_active_type() -> str:
    """Return the currently active machine type string, or "" if unconfigured."""
    return _active_type


def set_active_type(mtype: str) -> None:
    """Set and persist the active machine type.

    Args:
        mtype: One of the strings in MACHINE_TYPES.

    Raises:
        ValueError: If ``mtype`` is not a known machine type.
    """
    global _active_type, _configured

    if mtype not in _REGISTRY:
        raise ValueError(
            f"Unknown machine type: {mtype!r}. "
            f"Valid types: {MACHINE_TYPES}"
        )

    _active_type = mtype
    _configured = True
    _save()


def is_configured() -> bool:
    """Return True if a valid machine type has been set or loaded."""
    return _configured


def get_param_defs(mtype: Optional[str] = None) -> List[Dict]:
    """Return the parameter definitions for the given (or active) machine type.

    Args:
        mtype: Machine type string. Uses active type if None.

    Returns:
        List of param dicts, each with keys: label, var, unit, group, min, max.

    Raises:
        ValueError: If mtype is unknown.
    """
    resolved = _resolve_type(mtype)
    return _REGISTRY[resolved]["param_defs"]


def get_axis_list(mtype: Optional[str] = None) -> List[str]:
    """Return the axis identifier list for the given (or active) machine type.

    Args:
        mtype: Machine type string. Uses active type if None.

    Returns:
        List of axis strings, e.g. ["A", "B", "C", "D"].

    Raises:
        ValueError: If mtype is unknown.
    """
    resolved = _resolve_type(mtype)
    return _REGISTRY[resolved]["axes"]


def is_serration(mtype: Optional[str] = None) -> bool:
    """Return True if the given (or active) machine type is 3-Axes Serration Grind.

    Args:
        mtype: Machine type string. Uses active type if None.
    """
    resolved = _resolve_type(mtype)
    return resolved == "3-Axes Serration Grind"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _resolve_type(mtype: Optional[str]) -> str:
    """Return ``mtype`` if given, else the active type. Validates against registry.

    Raises:
        ValueError: If the resolved type is not in the registry.
    """
    resolved = mtype if mtype is not None else _active_type
    if resolved not in _REGISTRY:
        raise ValueError(
            f"Unknown machine type: {resolved!r}. "
            f"Valid types: {MACHINE_TYPES}"
        )
    return resolved


def _save() -> None:
    """Persist current active type to settings.json."""
    data: Dict = {}

    # Merge with existing file to avoid overwriting other settings
    if _settings_path and os.path.exists(_settings_path):
        try:
            with open(_settings_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            data = {}

    data["machine_type"] = _active_type

    if _settings_path:
        with open(_settings_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
