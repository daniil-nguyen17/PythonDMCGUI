"""Tests for screens/flat_grind_widgets.py.

Verifies that DeltaCBarChart, stone_window_for_index, and DELTA_C_* constants
are importable from the new location and have the expected values.
"""
import os
import sys

os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest


def test_delta_c_bar_chart_importable():
    """DeltaCBarChart can be imported from screens.flat_grind_widgets."""
    from dmccodegui.screens.flat_grind_widgets import DeltaCBarChart
    assert DeltaCBarChart is not None, "DeltaCBarChart must be importable"


def test_stone_window_for_index():
    """stone_window_for_index returns valid (start, end) tuple within array bounds."""
    from dmccodegui.screens.flat_grind_widgets import stone_window_for_index, DELTA_C_ARRAY_SIZE

    start, end = stone_window_for_index(50)

    assert isinstance(start, int), "start must be an int"
    assert isinstance(end, int), "end must be an int"
    assert start >= 0, f"start ({start}) must be >= 0"
    assert end < DELTA_C_ARRAY_SIZE, f"end ({end}) must be < DELTA_C_ARRAY_SIZE ({DELTA_C_ARRAY_SIZE})"
    assert start <= end, f"start ({start}) must be <= end ({end})"


def test_delta_c_constants():
    """DELTA_C_ARRAY_SIZE == 100, DELTA_C_STEP == 50."""
    from dmccodegui.screens.flat_grind_widgets import DELTA_C_ARRAY_SIZE, DELTA_C_STEP

    assert DELTA_C_ARRAY_SIZE == 100, f"Expected DELTA_C_ARRAY_SIZE=100, got {DELTA_C_ARRAY_SIZE}"
    assert DELTA_C_STEP == 50, f"Expected DELTA_C_STEP=50, got {DELTA_C_STEP}"


def test_bcomp_not_in_flat_grind_widgets():
    """BCompBarChart must NOT be in flat_grind_widgets (Serration-specific, Phase 21)."""
    import dmccodegui.screens.flat_grind_widgets as fgw
    assert not hasattr(fgw, 'BCompBarChart'), (
        "BCompBarChart must NOT be in flat_grind_widgets.py — "
        "it is Serration-specific and deferred to Phase 21"
    )
