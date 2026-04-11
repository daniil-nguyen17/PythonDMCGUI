"""Tests for screens/flat_grind/widgets.py.

Verifies that DeltaCBarChart, stone_window_for_index, and DELTA_C_* constants
are importable from the canonical flat_grind.widgets location and have the expected values.
"""
import os
import sys

os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest


def test_delta_c_bar_chart_importable():
    """DeltaCBarChart can be imported from screens.flat_grind.widgets."""
    from dmccodegui.screens.flat_grind.widgets import DeltaCBarChart
    assert DeltaCBarChart is not None, "DeltaCBarChart must be importable"


def test_stone_window_for_index():
    """stone_window_for_index returns valid (start, end) tuple within array bounds."""
    from dmccodegui.screens.flat_grind.widgets import stone_window_for_index, DELTA_C_ARRAY_SIZE

    start, end = stone_window_for_index(50)

    assert isinstance(start, int), "start must be an int"
    assert isinstance(end, int), "end must be an int"
    assert start >= 0, f"start ({start}) must be >= 0"
    assert end < DELTA_C_ARRAY_SIZE, f"end ({end}) must be < DELTA_C_ARRAY_SIZE ({DELTA_C_ARRAY_SIZE})"
    assert start <= end, f"start ({start}) must be <= end ({end})"


def test_delta_c_constants():
    """DELTA_C_ARRAY_SIZE == 100, DELTA_C_STEP == 50."""
    from dmccodegui.screens.flat_grind.widgets import DELTA_C_ARRAY_SIZE, DELTA_C_STEP

    assert DELTA_C_ARRAY_SIZE == 100, f"Expected DELTA_C_ARRAY_SIZE=100, got {DELTA_C_ARRAY_SIZE}"
    assert DELTA_C_STEP == 50, f"Expected DELTA_C_STEP=50, got {DELTA_C_STEP}"


def test_bcomp_not_in_flat_grind_widgets():
    """BCompBarChart must NOT be in flat_grind.widgets (Serration-specific, Phase 21)."""
    import dmccodegui.screens.flat_grind.widgets as fgw
    assert not hasattr(fgw, 'BCompBarChart'), (
        "BCompBarChart must NOT be in flat_grind/widgets.py -- "
        "it is Serration-specific and deferred to Phase 21"
    )


def test_backward_compat_wrapper_importable():
    """flat_grind_widgets.py wrapper re-exports DeltaCBarChart from flat_grind.widgets."""
    from dmccodegui.screens.flat_grind_widgets import DeltaCBarChart
    from dmccodegui.screens.flat_grind.widgets import DeltaCBarChart as Canonical
    assert DeltaCBarChart is Canonical, "Wrapper must re-export the same class object"


# ---------------------------------------------------------------------------
# Phase 19 verification: no duplicate KV rule headers
# ---------------------------------------------------------------------------

def test_no_duplicate_kv_rule_headers():
    """All .kv files under ui/ must have unique <ClassName>: rule headers."""
    import glob
    import re

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    kv_files = glob.glob(os.path.join(project_root, 'src', 'dmccodegui', 'ui', '**', '*.kv'), recursive=True)

    assert len(kv_files) > 0, "Expected at least one .kv file under ui/"

    # Pattern: <ClassName>: at start of line (with optional whitespace)
    header_pattern = re.compile(r'^\s*<(\w+)>:', re.MULTILINE)

    all_headers = []
    for kv_path in kv_files:
        try:
            with open(kv_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except OSError:
            continue
        headers = header_pattern.findall(content)
        all_headers.extend(headers)

    # Check for duplicates
    seen = set()
    duplicates = []
    for h in all_headers:
        if h in seen:
            duplicates.append(h)
        seen.add(h)

    assert duplicates == [], (
        f"Duplicate KV rule headers found: {duplicates}. "
        "Each class name must appear in exactly one .kv file."
    )


def test_flat_grind_package_imports():
    """FlatGrindRunScreen, FlatGrindAxesSetupScreen, FlatGrindParametersScreen importable from flat_grind."""
    from dmccodegui.screens.flat_grind import (
        FlatGrindRunScreen,
        FlatGrindAxesSetupScreen,
        FlatGrindParametersScreen,
    )
    assert FlatGrindRunScreen is not None
    assert FlatGrindAxesSetupScreen is not None
    assert FlatGrindParametersScreen is not None
