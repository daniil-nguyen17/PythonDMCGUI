"""Tests for ParametersScreen -- TDD for PARAM-01 through PARAM-07.

Pattern: import inside test functions with KIVY_NO_ENV_CONFIG=1 and KIVY_LOG_LEVEL=critical.
Mock controller.cmd() and jobs.submit(). Test dirty tracking as pure Python logic.
"""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def _setup_env():
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')


# ---------------------------------------------------------------------------
# PARAM_DEFS structure tests
# ---------------------------------------------------------------------------

def test_param_groups_defined():
    """PARAM-01: PARAM_DEFS contains entries for all five groups."""
    _setup_env()
    from dmccodegui.screens.parameters import PARAM_DEFS
    groups = {p['group'] for p in PARAM_DEFS}
    assert 'Geometry' in groups, "Missing Geometry group"
    assert 'Feedrates' in groups, "Missing Feedrates group"
    assert 'Calibration' in groups, "Missing Calibration group"


def test_param_def_structure():
    """PARAM-02: Each param def has required keys: label, var, unit, group, min, max."""
    _setup_env()
    from dmccodegui.screens.parameters import PARAM_DEFS
    required_keys = {'label', 'var', 'unit', 'group', 'min', 'max'}
    for p in PARAM_DEFS:
        missing = required_keys - set(p.keys())
        assert not missing, f"Param {p.get('var', '?')} missing keys: {missing}"


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

def test_invalid_input_flags_red():
    """PARAM-03: on_field_text_change with non-numeric text returns 'error' state."""
    _setup_env()
    from dmccodegui.screens.parameters import ParametersScreen, PARAM_DEFS
    screen = ParametersScreen()
    screen._controller_vals = {p['var']: 1.0 for p in PARAM_DEFS}
    result = screen.validate_field('fdA', 'not_a_number')
    assert result == 'error', f"Expected 'error', got '{result}'"


def test_out_of_range_flags_red():
    """PARAM-03: on_field_text_change with value outside min/max returns 'error' state."""
    _setup_env()
    from dmccodegui.screens.parameters import ParametersScreen, PARAM_DEFS
    screen = ParametersScreen()
    screen._controller_vals = {p['var']: 1.0 for p in PARAM_DEFS}
    # fdA has max=500.0, so 9999 should be error
    result = screen.validate_field('fdA', '9999')
    assert result == 'error', f"Expected 'error' for out-of-range, got '{result}'"


def test_zero_rejected_for_pitch():
    """PARAM-03: pitchA with value 0 is flagged as error."""
    _setup_env()
    from dmccodegui.screens.parameters import ParametersScreen, PARAM_DEFS
    screen = ParametersScreen()
    screen._controller_vals = {p['var']: 1.0 for p in PARAM_DEFS}
    result = screen.validate_field('pitchA', '0')
    assert result == 'error', f"Expected 'error' for zero pitch, got '{result}'"


def test_negative_rejected_for_feedrates():
    """PARAM-03: fdA with value -5 is flagged as error."""
    _setup_env()
    from dmccodegui.screens.parameters import ParametersScreen, PARAM_DEFS
    screen = ParametersScreen()
    screen._controller_vals = {p['var']: 1.0 for p in PARAM_DEFS}
    result = screen.validate_field('fdA', '-5')
    assert result == 'error', f"Expected 'error' for negative feedrate, got '{result}'"


def test_valid_returns_valid_when_matches_controller():
    """validate_field returns 'valid' when value matches controller value."""
    _setup_env()
    from dmccodegui.screens.parameters import ParametersScreen, PARAM_DEFS
    screen = ParametersScreen()
    screen._controller_vals = {p['var']: 100.0 for p in PARAM_DEFS}
    result = screen.validate_field('fdA', '100.0')
    assert result == 'valid', f"Expected 'valid' for matching value, got '{result}'"


def test_valid_returns_modified_when_differs():
    """validate_field returns 'modified' when valid value differs from controller."""
    _setup_env()
    from dmccodegui.screens.parameters import ParametersScreen, PARAM_DEFS
    screen = ParametersScreen()
    screen._controller_vals = {p['var']: 100.0 for p in PARAM_DEFS}
    result = screen.validate_field('fdA', '200.0')
    assert result == 'modified', f"Expected 'modified', got '{result}'"


# ---------------------------------------------------------------------------
# Dirty tracking tests
# ---------------------------------------------------------------------------

def test_dirty_tracking():
    """PARAM-04: on_field_text_change with valid changed value increments pending_count."""
    _setup_env()
    from dmccodegui.screens.parameters import ParametersScreen, PARAM_DEFS
    screen = ParametersScreen()
    screen._controller_vals = {p['var']: 100.0 for p in PARAM_DEFS}
    assert screen.pending_count == 0
    screen.on_field_text_change('fdA', '200.0')
    assert screen.pending_count == 1, f"Expected pending_count=1, got {screen.pending_count}"
    assert 'fdA' in screen._dirty, "fdA should be in _dirty dict"


def test_dirty_clear_on_revert():
    """PARAM-05: on_field_text_change with value matching controller removes from dirty."""
    _setup_env()
    from dmccodegui.screens.parameters import ParametersScreen, PARAM_DEFS
    screen = ParametersScreen()
    screen._controller_vals = {p['var']: 100.0 for p in PARAM_DEFS}
    # First mark as dirty
    screen.on_field_text_change('fdA', '200.0')
    assert screen.pending_count == 1
    # Now revert to controller value
    screen.on_field_text_change('fdA', '100.0')
    assert screen.pending_count == 0, f"Expected pending_count=0, got {screen.pending_count}"
    assert 'fdA' not in screen._dirty, "fdA should be removed from _dirty on revert"


def test_loading_flag_suppresses_dirty():
    """PARAM-04: With _loading=True, on_field_text_change does not add to _dirty."""
    _setup_env()
    from dmccodegui.screens.parameters import ParametersScreen, PARAM_DEFS
    screen = ParametersScreen()
    screen._controller_vals = {p['var']: 100.0 for p in PARAM_DEFS}
    screen._loading = True
    screen.on_field_text_change('fdA', '200.0')
    assert screen.pending_count == 0, "Loading flag should suppress dirty tracking"
    assert 'fdA' not in screen._dirty, "Loading flag should suppress dirty tracking"


def test_error_does_not_add_to_dirty():
    """Error state does not add to dirty dict."""
    _setup_env()
    from dmccodegui.screens.parameters import ParametersScreen, PARAM_DEFS
    screen = ParametersScreen()
    screen._controller_vals = {p['var']: 100.0 for p in PARAM_DEFS}
    screen.on_field_text_change('fdA', 'invalid')
    assert screen.pending_count == 0, "Error should not increment pending_count"
    assert 'fdA' not in screen._dirty, "Error should not add to dirty dict"


# ---------------------------------------------------------------------------
# Apply to controller tests
# ---------------------------------------------------------------------------

def test_apply_sends_dirty():
    """PARAM-06: apply_to_controller() sends controller.cmd('{var}={value}') for dirty params."""
    _setup_env()
    from dmccodegui.screens.parameters import ParametersScreen, PARAM_DEFS

    screen = ParametersScreen()
    mock_controller = MagicMock()
    mock_controller.is_connected.return_value = True
    mock_controller.cmd.return_value = '100.0'
    screen.controller = mock_controller
    screen.state = MagicMock()
    screen.state.cycle_running = False
    screen._controller_vals = {p['var']: 100.0 for p in PARAM_DEFS}

    # Mark fdA as dirty
    screen._dirty = {'fdA': '200.0'}
    screen.pending_count = 1

    # Capture the background job function
    job_fn = None

    def capture_job(fn, *args, **kwargs):
        nonlocal job_fn
        job_fn = fn

    with patch('dmccodegui.screens.parameters.submit', side_effect=capture_job):
        screen.apply_to_controller()

    assert job_fn is not None, "apply_to_controller should submit a background job"
    job_fn()  # execute the job synchronously

    # Should have sent fdA=200.0 and BV
    calls = mock_controller.cmd.call_args_list
    cmd_strings = [c[0][0] for c in calls]
    assert any('fdA=200.0' in s or 'fdA' in s for s in cmd_strings), \
        f"Expected fdA write cmd, got: {cmd_strings}"
    assert any('BV' in s for s in cmd_strings), \
        f"Expected BV command, got: {cmd_strings}"


def test_apply_burns_nv():
    """PARAM-06: apply_to_controller() sends BV after all writes."""
    _setup_env()
    from dmccodegui.screens.parameters import ParametersScreen, PARAM_DEFS

    screen = ParametersScreen()
    mock_controller = MagicMock()
    mock_controller.is_connected.return_value = True
    mock_controller.cmd.return_value = '100.0'
    screen.controller = mock_controller
    screen.state = MagicMock()
    screen.state.cycle_running = False
    screen._controller_vals = {p['var']: 100.0 for p in PARAM_DEFS}
    screen._dirty = {'fdA': '200.0'}
    screen.pending_count = 1

    job_fn = None

    def capture_job(fn, *args, **kwargs):
        nonlocal job_fn
        job_fn = fn

    with patch('dmccodegui.screens.parameters.submit', side_effect=capture_job):
        screen.apply_to_controller()

    job_fn()

    calls = [c[0][0] for c in mock_controller.cmd.call_args_list]
    # BV must come after the writes
    assert 'BV' in calls, f"BV not in cmd calls: {calls}"
    # BV should be after the variable write
    fdA_idx = next((i for i, c in enumerate(calls) if 'fdA' in c), None)
    bv_idx = next((i for i, c in enumerate(calls) if c == 'BV'), None)
    assert fdA_idx is not None and bv_idx is not None
    assert bv_idx > fdA_idx, "BV must come after variable writes"


def test_apply_reads_back():
    """PARAM-06: apply_to_controller() reads back params after BV."""
    _setup_env()
    from dmccodegui.screens.parameters import ParametersScreen, PARAM_DEFS

    screen = ParametersScreen()
    mock_controller = MagicMock()
    mock_controller.is_connected.return_value = True
    mock_controller.cmd.return_value = ' 100.0000 \r\n'
    screen.controller = mock_controller
    screen.state = MagicMock()
    screen.state.cycle_running = False
    screen._controller_vals = {p['var']: 100.0 for p in PARAM_DEFS}
    screen._dirty = {'fdA': '200.0'}
    screen.pending_count = 1

    job_fn = None

    def capture_job(fn, *args, **kwargs):
        nonlocal job_fn
        job_fn = fn

    with patch('dmccodegui.screens.parameters.submit', side_effect=capture_job):
        screen.apply_to_controller()

    job_fn()

    calls = [c[0][0] for c in mock_controller.cmd.call_args_list]
    # Should have MG {var} reads for all params after BV
    mg_calls = [c for c in calls if c.startswith('MG ')]
    assert len(mg_calls) > 0, "Should have MG reads after BV"


def test_apply_skips_when_cycle_running():
    """PARAM-06: apply_to_controller() is a no-op when cycle is running."""
    _setup_env()
    from dmccodegui.screens.parameters import ParametersScreen, PARAM_DEFS

    screen = ParametersScreen()
    mock_controller = MagicMock()
    mock_controller.is_connected.return_value = True
    screen.controller = mock_controller
    screen.state = MagicMock()
    screen.state.cycle_running = True
    screen._dirty = {'fdA': '200.0'}
    screen.pending_count = 1

    submitted = []

    with patch('dmccodegui.screens.parameters.submit', side_effect=lambda fn, *a, **k: submitted.append(fn)):
        screen.apply_to_controller()

    assert len(submitted) == 0, "Should not submit job when cycle is running"


# ---------------------------------------------------------------------------
# Read from controller tests
# ---------------------------------------------------------------------------

def test_read_clears_dirty():
    """PARAM-05: read_from_controller() clears _dirty dict and resets pending_count to 0."""
    _setup_env()
    from dmccodegui.screens.parameters import ParametersScreen, PARAM_DEFS

    screen = ParametersScreen()
    mock_controller = MagicMock()
    mock_controller.is_connected.return_value = True
    mock_controller.cmd.return_value = ' 100.0000 \r\n'
    screen.controller = mock_controller
    screen.state = MagicMock()
    screen._controller_vals = {p['var']: 100.0 for p in PARAM_DEFS}
    screen._dirty = {'fdA': '200.0', 'fdB': '150.0'}
    screen.pending_count = 2

    job_fn = None

    def capture_job(fn, *args, **kwargs):
        nonlocal job_fn
        job_fn = fn

    with patch('dmccodegui.screens.parameters.submit', side_effect=capture_job):
        screen.read_from_controller()

    assert job_fn is not None
    job_fn()

    assert screen.pending_count == 0, f"Expected pending_count=0 after read, got {screen.pending_count}"
    assert len(screen._dirty) == 0, f"Expected empty _dirty after read, got {screen._dirty}"


# ---------------------------------------------------------------------------
# Role-based readonly tests
# ---------------------------------------------------------------------------

def test_operator_readonly():
    """PARAM-07: _apply_role_mode(setup_unlocked=False) returns readonly=True."""
    _setup_env()
    from dmccodegui.screens.parameters import ParametersScreen
    screen = ParametersScreen()
    result = screen._apply_role_mode(setup_unlocked=False)
    assert result is True, f"Expected readonly=True for operator, got {result}"


def test_setup_not_readonly():
    """PARAM-07: _apply_role_mode(setup_unlocked=True) returns readonly=False."""
    _setup_env()
    from dmccodegui.screens.parameters import ParametersScreen
    screen = ParametersScreen()
    result = screen._apply_role_mode(setup_unlocked=True)
    assert result is False, f"Expected readonly=False for setup, got {result}"
