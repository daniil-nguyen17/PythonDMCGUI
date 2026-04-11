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
    from dmccodegui.screens.flat_grind.parameters import PARAM_DEFS
    groups = {p['group'] for p in PARAM_DEFS}
    assert 'Geometry' in groups, "Missing Geometry group"
    assert 'Feedrates' in groups, "Missing Feedrates group"
    assert 'Calibration' in groups, "Missing Calibration group"


def test_param_def_structure():
    """PARAM-02: Each param def has required keys: label, var, unit, group, min, max."""
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import PARAM_DEFS
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
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen, PARAM_DEFS
    screen = ParametersScreen()
    screen._controller_vals = {p['var']: 1.0 for p in PARAM_DEFS}
    result = screen.validate_field('fdA', 'not_a_number')
    assert result == 'error', f"Expected 'error', got '{result}'"


def test_out_of_range_flags_red():
    """PARAM-03: on_field_text_change with value outside min/max returns 'error' state."""
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen, PARAM_DEFS
    screen = ParametersScreen()
    screen._controller_vals = {p['var']: 1.0 for p in PARAM_DEFS}
    # fdA has max=500.0, so 9999 should be error
    result = screen.validate_field('fdA', '9999')
    assert result == 'error', f"Expected 'error' for out-of-range, got '{result}'"


def test_zero_rejected_for_pitch():
    """PARAM-03: pitchA with value 0 is flagged as error."""
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen, PARAM_DEFS
    screen = ParametersScreen()
    screen._controller_vals = {p['var']: 1.0 for p in PARAM_DEFS}
    result = screen.validate_field('pitchA', '0')
    assert result == 'error', f"Expected 'error' for zero pitch, got '{result}'"


def test_negative_rejected_for_feedrates():
    """PARAM-03: fdA with value -5 is flagged as error."""
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen, PARAM_DEFS
    screen = ParametersScreen()
    screen._controller_vals = {p['var']: 1.0 for p in PARAM_DEFS}
    result = screen.validate_field('fdA', '-5')
    assert result == 'error', f"Expected 'error' for negative feedrate, got '{result}'"


def test_valid_returns_valid_when_matches_controller():
    """validate_field returns 'valid' when value matches controller value."""
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen, PARAM_DEFS
    screen = ParametersScreen()
    screen._controller_vals = {p['var']: 100.0 for p in PARAM_DEFS}
    result = screen.validate_field('fdA', '100.0')
    assert result == 'valid', f"Expected 'valid' for matching value, got '{result}'"


def test_valid_returns_modified_when_differs():
    """validate_field returns 'modified' when valid value differs from controller."""
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen, PARAM_DEFS
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
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen, PARAM_DEFS
    screen = ParametersScreen()
    screen._controller_vals = {p['var']: 100.0 for p in PARAM_DEFS}
    assert screen.pending_count == 0
    screen.on_field_text_change('fdA', '200.0')
    assert screen.pending_count == 1, f"Expected pending_count=1, got {screen.pending_count}"
    assert 'fdA' in screen._dirty, "fdA should be in _dirty dict"


def test_dirty_clear_on_revert():
    """PARAM-05: on_field_text_change with value matching controller removes from dirty."""
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen, PARAM_DEFS
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
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen, PARAM_DEFS
    screen = ParametersScreen()
    screen._controller_vals = {p['var']: 100.0 for p in PARAM_DEFS}
    screen._loading = True
    screen.on_field_text_change('fdA', '200.0')
    assert screen.pending_count == 0, "Loading flag should suppress dirty tracking"
    assert 'fdA' not in screen._dirty, "Loading flag should suppress dirty tracking"


def test_error_does_not_add_to_dirty():
    """Error state does not add to dirty dict."""
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen, PARAM_DEFS
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
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen, PARAM_DEFS
    from dmccodegui.hmi.dmc_vars import STATE_IDLE

    screen = ParametersScreen()
    mock_controller = MagicMock()
    mock_controller.is_connected.return_value = True
    mock_controller.cmd.return_value = '100.0'
    screen.controller = mock_controller
    screen.state = MagicMock()
    screen.state.connected = True
    screen.state.dmc_state = STATE_IDLE
    screen._controller_vals = {p['var']: 100.0 for p in PARAM_DEFS}

    # Mark fdA as dirty
    screen._dirty = {'fdA': '200.0'}
    screen.pending_count = 1

    # Capture the background job function
    job_fn = None

    def capture_job(fn, *args, **kwargs):
        nonlocal job_fn
        job_fn = fn

    with patch('dmccodegui.screens.base.submit', side_effect=capture_job):
        with patch('dmccodegui.screens.base.mc.get_param_defs', return_value=PARAM_DEFS):
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
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen, PARAM_DEFS
    from dmccodegui.hmi.dmc_vars import STATE_IDLE

    screen = ParametersScreen()
    mock_controller = MagicMock()
    mock_controller.is_connected.return_value = True
    mock_controller.cmd.return_value = '100.0'
    screen.controller = mock_controller
    screen.state = MagicMock()
    screen.state.connected = True
    screen.state.dmc_state = STATE_IDLE
    screen._controller_vals = {p['var']: 100.0 for p in PARAM_DEFS}
    screen._dirty = {'fdA': '200.0'}
    screen.pending_count = 1

    job_fn = None

    def capture_job(fn, *args, **kwargs):
        nonlocal job_fn
        job_fn = fn

    with patch('dmccodegui.screens.base.submit', side_effect=capture_job):
        with patch('dmccodegui.screens.base.mc.get_param_defs', return_value=PARAM_DEFS):
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
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen, PARAM_DEFS
    from dmccodegui.hmi.dmc_vars import STATE_IDLE

    screen = ParametersScreen()
    mock_controller = MagicMock()
    mock_controller.is_connected.return_value = True
    mock_controller.cmd.return_value = ' 100.0000 \r\n'
    screen.controller = mock_controller
    screen.state = MagicMock()
    screen.state.connected = True
    screen.state.dmc_state = STATE_IDLE
    screen._controller_vals = {p['var']: 100.0 for p in PARAM_DEFS}
    screen._dirty = {'fdA': '200.0'}
    screen.pending_count = 1

    job_fn = None

    def capture_job(fn, *args, **kwargs):
        nonlocal job_fn
        job_fn = fn

    with patch('dmccodegui.screens.base.submit', side_effect=capture_job):
        with patch('dmccodegui.screens.base.mc.get_param_defs', return_value=PARAM_DEFS):
            screen.apply_to_controller()

    job_fn()

    calls = [c[0][0] for c in mock_controller.cmd.call_args_list]
    # Should have MG {var} reads for all params after BV
    mg_calls = [c for c in calls if c.startswith('MG ')]
    assert len(mg_calls) > 0, "Should have MG reads after BV"


def test_apply_skips_when_motion_active():
    """PARAM-06: apply_to_controller() is a no-op when motion is active (GRINDING)."""
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen, PARAM_DEFS
    from dmccodegui.hmi.dmc_vars import STATE_GRINDING

    screen = ParametersScreen()
    mock_controller = MagicMock()
    mock_controller.is_connected.return_value = True
    screen.controller = mock_controller
    screen.state = MagicMock()
    screen.state.connected = True
    screen.state.dmc_state = STATE_GRINDING
    screen._dirty = {'fdA': '200.0'}
    screen.pending_count = 1

    submitted = []

    with patch('dmccodegui.screens.base.submit', side_effect=lambda fn, *a, **k: submitted.append(fn)):
        screen.apply_to_controller()

    assert len(submitted) == 0, "Should not submit job when motion is active (GRINDING)"


# ---------------------------------------------------------------------------
# Read from controller tests
# ---------------------------------------------------------------------------

def test_read_clears_dirty():
    """PARAM-05: read_from_controller() clears _dirty dict and resets pending_count to 0."""
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen, PARAM_DEFS

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

    with patch('dmccodegui.screens.base.submit', side_effect=capture_job):
        with patch('dmccodegui.screens.base.mc.is_configured', return_value=True):
            with patch('dmccodegui.screens.base.mc.get_param_defs', return_value=PARAM_DEFS):
                screen.read_from_controller()

    assert job_fn is not None
    # job schedules UI update via Clock.schedule_once; patch to run immediately
    with patch('dmccodegui.screens.flat_grind.parameters.Clock.schedule_once', side_effect=lambda fn, *a: fn(0)):
        job_fn()

    assert screen.pending_count == 0, f"Expected pending_count=0 after read, got {screen.pending_count}"
    assert len(screen._dirty) == 0, f"Expected empty _dirty after read, got {screen._dirty}"


# ---------------------------------------------------------------------------
# Role-based readonly tests
# ---------------------------------------------------------------------------

def test_operator_readonly():
    """PARAM-07: _apply_role_mode(setup_unlocked=False) returns readonly=True."""
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen
    screen = ParametersScreen()
    result = screen._apply_role_mode(setup_unlocked=False)
    assert result is True, f"Expected readonly=True for operator, got {result}"


def test_setup_not_readonly():
    """PARAM-07: _apply_role_mode(setup_unlocked=True) returns readonly=False."""
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen
    screen = ParametersScreen()
    result = screen._apply_role_mode(setup_unlocked=True)
    assert result is False, f"Expected readonly=False for setup, got {result}"


# ---------------------------------------------------------------------------
# Varcalc integration tests (Plan 13-03)
# ---------------------------------------------------------------------------

def _make_apply_screen():
    """Helper: create ParametersScreen with one dirty param, mock controller.

    Does NOT configure machine_config globally — callers must patch
    'dmccodegui.screens.base.mc.get_param_defs' if the job will call it.
    """
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen, PARAM_DEFS

    screen = ParametersScreen()
    mock_controller = MagicMock()
    mock_controller.is_connected.return_value = True
    mock_controller.cmd.return_value = '100.0'
    screen.controller = mock_controller
    screen.state = MagicMock()
    screen.state.cycle_running = False
    screen.state.dmc_state = 1
    screen._controller_vals = {p['var']: 100.0 for p in PARAM_DEFS}
    screen._dirty = {'fdA': '200.0'}
    screen.pending_count = 1
    return screen, mock_controller


def _run_apply_job_with_mc_patch(screen):
    """Submit apply_to_controller capturing the job, run it synchronously.

    Patches mc.get_param_defs to return PARAM_DEFS so the job doesn't require
    machine_config to be globally initialized.
    """
    from dmccodegui.screens.flat_grind.parameters import PARAM_DEFS
    job_fn = None

    def capture_job(fn, *args, **kwargs):
        nonlocal job_fn
        job_fn = fn

    with patch('dmccodegui.screens.base.submit', side_effect=capture_job):
        with patch('dmccodegui.screens.base.mc.get_param_defs', return_value=PARAM_DEFS):
            screen.apply_to_controller()

    assert job_fn is not None, "apply_to_controller should submit a background job"
    job_fn()
    return job_fn


def test_apply_fires_hmi_calc():
    """SETP-06: apply_to_controller sends hmiCalc=0 after writing params."""
    _setup_env()
    screen, mock_controller = _make_apply_screen()

    _run_apply_job_with_mc_patch(screen)

    calls = [c[0][0] for c in mock_controller.cmd.call_args_list]
    assert any('hmiCalc=0' in s for s in calls), \
        f"Expected hmiCalc=0 cmd, got: {calls}"


def test_apply_readback_after_delay():
    """SETP-06: apply_to_controller calls time.sleep(0.5) then reads back all params."""
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import PARAM_DEFS
    screen, mock_controller = _make_apply_screen()

    sleep_calls = []
    with patch('dmccodegui.screens.base.mc.get_param_defs', return_value=PARAM_DEFS):
        with patch('dmccodegui.screens.base.submit', side_effect=lambda fn, *a, **k: fn()):
            with patch('time.sleep', side_effect=lambda s: sleep_calls.append(s)):
                screen.apply_to_controller()

    assert any(abs(s - 0.5) < 1e-9 for s in sleep_calls), \
        f"Expected time.sleep(0.5), got sleep calls: {sleep_calls}"

    calls = [c[0][0] for c in mock_controller.cmd.call_args_list]
    # After hmiCalc=0 + sleep, MG reads must follow
    calc_idx = next((i for i, c in enumerate(calls) if 'hmiCalc' in c), None)
    mg_indices = [i for i, c in enumerate(calls) if c.startswith('MG ')]
    assert calc_idx is not None, "hmiCalc=0 must be sent"
    assert len(mg_indices) > 0, "MG readback calls must occur after hmiCalc fire"
    assert all(i > calc_idx for i in mg_indices), \
        "All MG readbacks must come after hmiCalc=0"


def test_apply_bv_after_readback():
    """SETP-06: BV is sent after readback (not before varcalc)."""
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import PARAM_DEFS
    screen, mock_controller = _make_apply_screen()

    with patch('dmccodegui.screens.base.mc.get_param_defs', return_value=PARAM_DEFS):
        with patch('dmccodegui.screens.base.submit', side_effect=lambda fn, *a, **k: fn()):
            with patch('time.sleep'):
                screen.apply_to_controller()

    calls = [c[0][0] for c in mock_controller.cmd.call_args_list]
    calc_idx = next((i for i, c in enumerate(calls) if 'hmiCalc' in c), None)
    mg_indices = [i for i, c in enumerate(calls) if c.startswith('MG ')]
    bv_idx = next((i for i, c in enumerate(calls) if c == 'BV'), None)

    assert calc_idx is not None, "hmiCalc=0 must be present"
    assert len(mg_indices) > 0, "MG readbacks must be present"
    assert bv_idx is not None, "BV must be present"
    last_mg = max(mg_indices)
    assert bv_idx > last_mg, f"BV must come after all MG readbacks (bv={bv_idx}, last_mg={last_mg})"
    assert bv_idx > calc_idx, "BV must come after hmiCalc=0"


# ---------------------------------------------------------------------------
# Smart enter/exit tests (Plan 13-03)
# ---------------------------------------------------------------------------

def test_enter_skips_fire_when_already_setup():
    """SETP-07: on_pre_enter with dmc_state=STATE_SETUP does NOT send hmiSetp=0."""
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen
    from dmccodegui.hmi.dmc_vars import STATE_SETUP

    screen = ParametersScreen()
    mock_controller = MagicMock()
    mock_controller.is_connected.return_value = True
    screen.controller = mock_controller
    state = MagicMock()
    state.dmc_state = STATE_SETUP  # already in setup
    state.setup_unlocked = True
    screen.state = state

    # submit executes lambdas synchronously so ctrl.cmd calls are visible
    with patch('dmccodegui.screens.base.submit', side_effect=lambda fn, *a, **kw: fn()):
        screen.on_pre_enter()

    calls = [c[0][0] for c in mock_controller.cmd.call_args_list]
    assert not any('hmiSetp=0' in s for s in calls), \
        f"Should NOT send hmiSetp=0 when already in setup, got: {calls}"


def test_enter_fires_when_not_in_setup():
    """SETP-07: on_pre_enter with dmc_state=STATE_IDLE sends hmiSetp=0."""
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen
    from dmccodegui.hmi.dmc_vars import STATE_IDLE

    screen = ParametersScreen()
    mock_controller = MagicMock()
    mock_controller.is_connected.return_value = True
    screen.controller = mock_controller
    state = MagicMock()
    state.dmc_state = STATE_IDLE  # not in setup
    state.setup_unlocked = True
    screen.state = state

    # submit executes lambdas synchronously so ctrl.cmd calls are visible
    with patch('dmccodegui.screens.base.submit', side_effect=lambda fn, *a, **kw: fn()):
        screen.on_pre_enter()

    calls = [c[0][0] for c in mock_controller.cmd.call_args_list]
    assert any('hmiSetp=0' in s for s in calls), \
        f"Should send hmiSetp=0 when not in setup, got: {calls}"


def test_exit_fires_to_non_setup_screen():
    """SETP-08: on_leave when manager.current='run' sends hmiExSt=0."""
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen

    screen = ParametersScreen()
    mock_controller = MagicMock()
    mock_controller.is_connected.return_value = True
    screen.controller = mock_controller

    mock_manager = MagicMock()
    mock_manager.current = "run"
    screen.manager = mock_manager

    # submit executes lambdas synchronously so ctrl.cmd calls are visible
    with patch('dmccodegui.screens.base.submit', side_effect=lambda fn, *a, **kw: fn()):
        screen.on_leave()

    calls = [c[0][0] for c in mock_controller.cmd.call_args_list]
    assert any('hmiExSt=0' in s for s in calls), \
        f"Should send hmiExSt=0 when navigating to non-setup screen, got: {calls}"


def test_exit_skips_to_sibling_setup_screen():
    """SETP-08: on_leave when manager.current='axes_setup' does NOT send hmiExSt=0."""
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen

    screen = ParametersScreen()
    mock_controller = MagicMock()
    mock_controller.is_connected.return_value = True
    screen.controller = mock_controller

    mock_manager = MagicMock()
    mock_manager.current = "axes_setup"
    screen.manager = mock_manager

    # submit executes lambdas synchronously so ctrl.cmd calls are visible
    with patch('dmccodegui.screens.base.submit', side_effect=lambda fn, *a, **kw: fn()):
        screen.on_leave()

    calls = [c[0][0] for c in mock_controller.cmd.call_args_list]
    assert not any('hmiExSt=0' in s for s in calls), \
        f"Should NOT send hmiExSt=0 when navigating to sibling setup screen, got: {calls}"


# ---------------------------------------------------------------------------
# UI-01: motion_active gating on Parameters Apply button
# ---------------------------------------------------------------------------

def _make_state_with_dmc(connected: bool, dmc_state: int):
    """Create a mock state with connected and dmc_state fields."""
    state = MagicMock()
    state.connected = connected
    state.dmc_state = dmc_state
    # cycle_running is derived from dmc_state == STATE_GRINDING
    from dmccodegui.hmi.dmc_vars import STATE_GRINDING
    state.cycle_running = (dmc_state == STATE_GRINDING)
    return state


def _make_apply_screen_with_state(connected: bool, dmc_state: int):
    """Create a ParametersScreen with a mock state configured for motion_active tests.

    The screen has one dirty param (fdA) and a connected mock controller.
    """
    _setup_env()
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen, PARAM_DEFS

    screen = ParametersScreen()
    mock_controller = MagicMock()
    mock_controller.is_connected.return_value = True
    mock_controller.cmd.return_value = '100.0'
    screen.controller = mock_controller
    screen.state = _make_state_with_dmc(connected=connected, dmc_state=dmc_state)
    screen._controller_vals = {p['var']: 100.0 for p in PARAM_DEFS}
    screen._dirty = {'fdA': '200.0'}
    screen.pending_count = 1
    return screen, mock_controller


class TestParametersApplyMotionGating:
    """apply_to_controller() uses motion_active gate (dmc_state) not cycle_running."""

    def _run_apply(self, screen):
        """Run apply_to_controller() and return submitted jobs list.

        Patches mc.get_param_defs so apply_to_controller() can proceed past the
        guard (when motion_active=False) without requiring machine_config init.
        """
        from dmccodegui.screens.flat_grind.parameters import PARAM_DEFS
        submitted = []
        with patch('dmccodegui.screens.base.submit', side_effect=lambda fn, *a, **k: submitted.append(fn)):
            with patch('dmccodegui.screens.base.mc.get_param_defs', return_value=PARAM_DEFS):
                screen.apply_to_controller()
        return submitted

    def test_apply_skips_when_grinding(self):
        """apply_to_controller() does not submit job when dmc_state=STATE_GRINDING."""
        from dmccodegui.hmi.dmc_vars import STATE_GRINDING
        screen, _ = _make_apply_screen_with_state(connected=True, dmc_state=STATE_GRINDING)

        submitted = self._run_apply(screen)

        assert len(submitted) == 0, \
            "Should not submit job when dmc_state=STATE_GRINDING"

    def test_apply_skips_when_homing(self):
        """apply_to_controller() does not submit job when dmc_state=STATE_HOMING."""
        from dmccodegui.hmi.dmc_vars import STATE_HOMING
        screen, _ = _make_apply_screen_with_state(connected=True, dmc_state=STATE_HOMING)

        submitted = self._run_apply(screen)

        assert len(submitted) == 0, \
            "Should not submit job when dmc_state=STATE_HOMING"

    def test_apply_skips_when_disconnected(self):
        """apply_to_controller() does not submit job when connected=False."""
        from dmccodegui.hmi.dmc_vars import STATE_IDLE
        screen, _ = _make_apply_screen_with_state(connected=False, dmc_state=STATE_IDLE)

        submitted = self._run_apply(screen)

        assert len(submitted) == 0, \
            "Should not submit job when disconnected"

    def test_apply_proceeds_when_idle(self):
        """apply_to_controller() submits job when dmc_state=STATE_IDLE and connected."""
        from dmccodegui.hmi.dmc_vars import STATE_IDLE
        screen, _ = _make_apply_screen_with_state(connected=True, dmc_state=STATE_IDLE)

        submitted = self._run_apply(screen)

        assert len(submitted) == 1, \
            "Should submit job when dmc_state=STATE_IDLE and connected"

    def test_apply_proceeds_when_setup(self):
        """apply_to_controller() submits job when dmc_state=STATE_SETUP and connected."""
        from dmccodegui.hmi.dmc_vars import STATE_SETUP
        screen, _ = _make_apply_screen_with_state(connected=True, dmc_state=STATE_SETUP)

        submitted = self._run_apply(screen)

        assert len(submitted) == 1, \
            "Should submit job when dmc_state=STATE_SETUP and connected"


class TestParametersUpdateApplyButton:
    """_update_apply_button() visually gates Apply button based on motion_active."""

    def _make_screen_with_apply_btn(self, connected: bool, dmc_state: int):
        """Create a ParametersScreen with a mock apply button."""
        _setup_env()
        from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen

        screen = ParametersScreen()
        screen.state = _make_state_with_dmc(connected=connected, dmc_state=dmc_state)
        # Inject mock apply button via _apply_btn attribute
        mock_btn = MagicMock()
        mock_btn.disabled = False
        mock_btn.opacity = 1.0
        screen._apply_btn = mock_btn
        # setup_unlocked = True so role gate doesn't interfere
        screen.state.setup_unlocked = True
        return screen, mock_btn

    def test_apply_btn_disabled_when_grinding(self):
        """_update_apply_button() disables apply button when dmc_state=STATE_GRINDING."""
        from dmccodegui.hmi.dmc_vars import STATE_GRINDING
        screen, btn = self._make_screen_with_apply_btn(connected=True, dmc_state=STATE_GRINDING)

        screen._update_apply_button()

        assert btn.disabled is True, "Apply button should be disabled during GRINDING"
        assert btn.opacity == pytest.approx(0.4), "Apply button opacity should be 0.4 during GRINDING"

    def test_apply_btn_disabled_when_homing(self):
        """_update_apply_button() disables apply button when dmc_state=STATE_HOMING."""
        from dmccodegui.hmi.dmc_vars import STATE_HOMING
        screen, btn = self._make_screen_with_apply_btn(connected=True, dmc_state=STATE_HOMING)

        screen._update_apply_button()

        assert btn.disabled is True, "Apply button should be disabled during HOMING"
        assert btn.opacity == pytest.approx(0.4), "Apply button opacity should be 0.4 during HOMING"

    def test_apply_btn_disabled_when_disconnected(self):
        """_update_apply_button() disables apply button when connected=False."""
        from dmccodegui.hmi.dmc_vars import STATE_IDLE
        screen, btn = self._make_screen_with_apply_btn(connected=False, dmc_state=STATE_IDLE)

        screen._update_apply_button()

        assert btn.disabled is True, "Apply button should be disabled when disconnected"
        assert btn.opacity == pytest.approx(0.4), "Apply button opacity should be 0.4 when disconnected"

    def test_apply_btn_enabled_when_idle(self):
        """_update_apply_button() enables apply button when dmc_state=STATE_IDLE and connected."""
        from dmccodegui.hmi.dmc_vars import STATE_IDLE
        screen, btn = self._make_screen_with_apply_btn(connected=True, dmc_state=STATE_IDLE)

        screen._update_apply_button()

        assert btn.disabled is False, "Apply button should be enabled when IDLE and connected"
        assert btn.opacity == pytest.approx(1.0), "Apply button opacity should be 1.0 when IDLE"

    def test_apply_btn_enabled_when_setup(self):
        """_update_apply_button() enables apply button when dmc_state=STATE_SETUP and connected."""
        from dmccodegui.hmi.dmc_vars import STATE_SETUP
        screen, btn = self._make_screen_with_apply_btn(connected=True, dmc_state=STATE_SETUP)

        screen._update_apply_button()

        assert btn.disabled is False, "Apply button should be enabled when SETUP and connected"
        assert btn.opacity == pytest.approx(1.0), "Apply button opacity should be 1.0 when SETUP"
