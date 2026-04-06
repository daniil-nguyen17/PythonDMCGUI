import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_run_screen_has_cycle_running_property():
    """RUN-04: RunScreen must expose cycle_running as a Kivy property."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    r = RunScreen()
    assert hasattr(r, 'cycle_running'), "RunScreen missing cycle_running property"


def test_run_screen_has_position_properties():
    """RUN-03: RunScreen must expose pos_a through pos_d."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    r = RunScreen()
    for axis in ('pos_a', 'pos_b', 'pos_c', 'pos_d'):
        assert hasattr(r, axis), f"RunScreen missing {axis} property"


def test_axis_positions_disconnected():
    """RUN-03: When disconnected, axis positions show '---'."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    r = RunScreen()
    # Default (no controller) should show '---'
    assert r.pos_a == '---', f"Expected '---', got '{r.pos_a}'"
    assert r.pos_b == '---', f"Expected '---', got '{r.pos_b}'"
    assert r.pos_c == '---', f"Expected '---', got '{r.pos_c}'"
    assert r.pos_d == '---', f"Expected '---', got '{r.pos_d}'"


def test_no_estop_in_run_bar():
    """RUN-02: E-STOP must NOT be in RunScreen — it is in StatusBar only."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    r = RunScreen()
    # RunScreen should not have any e_stop method or property
    assert not hasattr(r, 'e_stop_button'), "RunScreen should not have e_stop_button"


def test_cycle_status_machine_type():
    """RUN-04: is_serration flag controls cycle status field visibility.

    is_serration is now a dynamic BooleanProperty set from mc.is_serration()
    in on_pre_enter. Default is False (non-serration layout).
    IS_SERRATION module constant removed — machine_config is the authority.
    """
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    r = RunScreen()
    assert hasattr(r, 'is_serration'), "RunScreen missing is_serration property"
    # Default is False — set dynamically in on_pre_enter from mc.is_serration()
    assert r.is_serration is False, f"Expected is_serration default False, got {r.is_serration}"


def test_progress_and_eta():
    """RUN-05: RunScreen exposes cycle_completion_pct and cycle_eta."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    r = RunScreen()
    assert hasattr(r, 'cycle_completion_pct'), "Missing cycle_completion_pct"
    assert hasattr(r, 'cycle_eta'), "Missing cycle_eta"
    assert r.cycle_completion_pct == 0
    assert r.cycle_eta == '--:--'


def test_delta_c_adjustment():
    """RUN-06: RunScreen has section_count and delta_c_offsets for Knife Grind Adjustment."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    r = RunScreen()
    assert hasattr(r, 'section_count'), "Missing section_count"
    assert hasattr(r, 'delta_c_offsets'), "Missing delta_c_offsets"


# ---------------------------------------------------------------------------
# RUN-07: Live A/B Position Plot tests
# ---------------------------------------------------------------------------

def test_plot_hz_constant_exists():
    """RUN-07: PLOT_UPDATE_HZ constant exists and equals 5."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import PLOT_UPDATE_HZ
    assert PLOT_UPDATE_HZ == 5, f"Expected PLOT_UPDATE_HZ == 5, got {PLOT_UPDATE_HZ}"


def test_plot_buffer_size_constant_exists():
    """RUN-07: PLOT_BUFFER_SIZE constant exists and is in the valid range 500-1000."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import PLOT_BUFFER_SIZE
    assert 500 <= PLOT_BUFFER_SIZE <= 1000, (
        f"Expected 500 <= PLOT_BUFFER_SIZE <= 1000, got {PLOT_BUFFER_SIZE}"
    )


def test_plot_buffer_properties():
    """RUN-07: RunScreen has _plot_buf_x and _plot_buf_y as deques with correct maxlen."""
    import collections
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen, PLOT_BUFFER_SIZE
    r = RunScreen()
    assert hasattr(r, '_plot_buf_x'), "RunScreen missing _plot_buf_x"
    assert hasattr(r, '_plot_buf_y'), "RunScreen missing _plot_buf_y"
    assert isinstance(r._plot_buf_x, collections.deque), "_plot_buf_x must be a deque"
    assert isinstance(r._plot_buf_y, collections.deque), "_plot_buf_y must be a deque"
    assert r._plot_buf_x.maxlen == PLOT_BUFFER_SIZE, (
        f"_plot_buf_x.maxlen expected {PLOT_BUFFER_SIZE}, got {r._plot_buf_x.maxlen}"
    )
    assert r._plot_buf_y.maxlen == PLOT_BUFFER_SIZE, (
        f"_plot_buf_y.maxlen expected {PLOT_BUFFER_SIZE}, got {r._plot_buf_y.maxlen}"
    )


def test_plot_buffer_only_during_cycle():
    """RUN-07: _apply_state only appends to plot buffers when cycle is running and connected."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    import sys, os as _os
    sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', 'src'))
    from dmccodegui.screens.run import RunScreen
    from dmccodegui.app_state import MachineState
    from dmccodegui.hmi.dmc_vars import STATE_GRINDING, STATE_IDLE

    r = RunScreen()

    # With dmc_state=STATE_IDLE (not grinding), buffer should stay empty
    s = MachineState(connected=True, dmc_state=STATE_IDLE,
                     pos={"A": 100.0, "B": 200.0, "C": 0.0, "D": 0.0})
    r._apply_state(s)
    assert len(r._plot_buf_x) == 0, "Buffer should be empty when not grinding"
    assert len(r._plot_buf_y) == 0, "Buffer should be empty when not grinding"

    # With dmc_state=STATE_GRINDING and connected, buffer should receive one entry
    s2 = MachineState(connected=True, dmc_state=STATE_GRINDING,
                      pos={"A": 100.0, "B": 200.0, "C": 0.0, "D": 0.0})
    r._apply_state(s2)
    assert len(r._plot_buf_x) == 1, f"Expected 1 entry in _plot_buf_x, got {len(r._plot_buf_x)}"
    assert len(r._plot_buf_y) == 1, f"Expected 1 entry in _plot_buf_y, got {len(r._plot_buf_y)}"


def test_trail_clears_on_start():
    """RUN-07: on_start_pause_toggle('down') clears both plot buffers."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    r = RunScreen()
    # Manually add data to buffers
    r._plot_buf_x.append(1.0)
    r._plot_buf_x.append(2.0)
    r._plot_buf_y.append(10.0)
    r._plot_buf_y.append(20.0)
    assert len(r._plot_buf_x) == 2, "Pre-condition: buffer should have 2 entries"
    # Trigger start — controller is None so background job will fail silently
    r.on_start_pause_toggle("down")
    assert len(r._plot_buf_x) == 0, "_plot_buf_x must be cleared on Start"
    assert len(r._plot_buf_y) == 0, "_plot_buf_y must be cleared on Start"


# ---------------------------------------------------------------------------
# SAFE-02: Stop button and motion gate tests (Phase 11 Plan 02)
# ---------------------------------------------------------------------------

def test_stop_sends_st_only():
    """on_stop() must send ST ABCD only (no HX) via submit_urgent."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.run import RunScreen
    from dmccodegui.controller import GalilController

    r = RunScreen()
    mock_ctrl = MagicMock(spec=GalilController)
    mock_ctrl.is_connected.return_value = True
    r.controller = mock_ctrl

    captured_fn = []

    def capture_urgent(fn, *a, **kw):
        captured_fn.append(fn)

    with patch('dmccodegui.utils.jobs.submit_urgent', side_effect=capture_urgent):
        r.on_stop()

    assert len(captured_fn) == 1, "on_stop must call submit_urgent once"
    # Execute the do_stop inner function
    captured_fn[0]()
    cmd_calls = [c[0][0] for c in mock_ctrl.cmd.call_args_list]
    assert 'ST ABCD' in cmd_calls, f"Expected 'ST ABCD' in cmd calls, got {cmd_calls}"
    assert 'HX' not in cmd_calls, f"on_stop must NOT send HX; got {cmd_calls}"


def test_motion_gate_grinding():
    """motion_active must be True when dmc_state is STATE_GRINDING."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    from dmccodegui.app_state import MachineState
    from dmccodegui.hmi.dmc_vars import STATE_GRINDING

    r = RunScreen()
    s = MachineState(connected=True, dmc_state=STATE_GRINDING,
                     pos={"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0})
    r._apply_state(s)
    assert r.motion_active is True, \
        f"Expected motion_active=True during GRINDING, got {r.motion_active}"


def test_motion_gate_homing():
    """motion_active must be True when dmc_state is STATE_HOMING."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    from dmccodegui.app_state import MachineState
    from dmccodegui.hmi.dmc_vars import STATE_HOMING

    r = RunScreen()
    s = MachineState(connected=True, dmc_state=STATE_HOMING,
                     pos={"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0})
    r._apply_state(s)
    assert r.motion_active is True, \
        f"Expected motion_active=True during HOMING, got {r.motion_active}"


def test_motion_gate_disconnected():
    """motion_active must be True when disconnected (disables all motion buttons)."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    from dmccodegui.app_state import MachineState

    r = RunScreen()
    s = MachineState(connected=False)
    r._apply_state(s)
    assert r.motion_active is True, \
        f"Expected motion_active=True when disconnected, got {r.motion_active}"


def test_motion_gate_idle():
    """motion_active must be False when dmc_state is STATE_IDLE and connected."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    from dmccodegui.app_state import MachineState
    from dmccodegui.hmi.dmc_vars import STATE_IDLE

    r = RunScreen()
    s = MachineState(connected=True, dmc_state=STATE_IDLE,
                     pos={"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0})
    r._apply_state(s)
    assert r.motion_active is False, \
        f"Expected motion_active=False when IDLE and connected, got {r.motion_active}"


def test_stop_visible_during_motion():
    """motion_active=True should drive stop button visibility (property exists and is True)."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    from dmccodegui.app_state import MachineState
    from dmccodegui.hmi.dmc_vars import STATE_GRINDING

    r = RunScreen()
    s = MachineState(connected=True, dmc_state=STATE_GRINDING,
                     pos={"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0})
    r._apply_state(s)
    assert hasattr(r, 'motion_active'), "RunScreen must have motion_active property"
    assert r.motion_active is True, \
        "Stop button must be visible (motion_active=True) during GRINDING"
