"""
Tests for AxesSetupScreen — mode toggle, jog math, teach/save, quick actions,
axis row visibility.

Pattern: import inside test functions, set env vars before kivy import.
All Kivy properties are tested against the real Screen instance.
Controller I/O is mocked so no hardware required.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_screen():
    """Instantiate AxesSetupScreen with a mock controller and state."""
    from unittest.mock import MagicMock
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    ctrl.cmd.return_value = "0.0000"
    screen.controller = ctrl
    screen.state = MagicMock()
    screen.state.cycle_running = False
    return screen, ctrl


# ── Mode toggle ──────────────────────────────────────────────────────────────


def test_mode_default_rest():
    """_mode defaults to 'rest'."""
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    screen = AxesSetupScreen()
    assert screen._mode == "rest"


def test_set_mode_start():
    """set_mode('start') changes _mode to 'start'."""
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    screen = AxesSetupScreen()
    screen.set_mode("start")
    assert screen._mode == "start"


def test_set_mode_rest():
    """set_mode('rest') changes _mode back to 'rest'."""
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    screen = AxesSetupScreen()
    screen.set_mode("start")
    screen.set_mode("rest")
    assert screen._mode == "rest"


# ── Save delegation ─────────────────────────────────────────────────────────


def test_save_points_rest_mode():
    """save_points() in rest mode calls teach_rest_point."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    screen._mode = "rest"
    screen.teach_rest_point = MagicMock()
    screen.teach_start_point = MagicMock()
    screen.save_points()
    screen.teach_rest_point.assert_called_once()
    screen.teach_start_point.assert_not_called()


def test_save_points_start_mode():
    """save_points() in start mode calls teach_start_point."""
    from unittest.mock import MagicMock
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    screen._mode = "start"
    screen.teach_rest_point = MagicMock()
    screen.teach_start_point = MagicMock()
    screen.save_points()
    screen.teach_start_point.assert_called_once()
    screen.teach_rest_point.assert_not_called()


# ── Step size ────────────────────────────────────────────────────────────────


def test_step_mm_property():
    """_current_step_mm defaults to 10.0; set_step changes it."""
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    screen = AxesSetupScreen()
    assert screen._current_step_mm == 10.0
    screen.set_step(5.0)
    assert screen._current_step_mm == 5.0
    screen.set_step(1.0)
    assert screen._current_step_mm == 1.0


def test_cpm_defaults():
    """AXIS_CPM_DEFAULTS has all 4 axes with positive values."""
    from dmccodegui.screens.axes_setup import AXIS_CPM_DEFAULTS
    assert set(AXIS_CPM_DEFAULTS.keys()) == {"A", "B", "C", "D"}
    for axis, cpm in AXIS_CPM_DEFAULTS.items():
        assert cpm > 0, f"CPM for {axis} must be positive, got {cpm}"


# ── Jog math ─────────────────────────────────────────────────────────────────


def test_jog_counts_calculation():
    """jog_axis('A', +1) with step_mm=10.0 and cpm=1200 produces PR A=12000."""
    from unittest.mock import MagicMock, patch, call
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    # MG _BGA returns 0.0 (motion complete) so poll exits immediately
    ctrl.cmd.return_value = " 0.0000 "
    screen.controller = ctrl

    screen._axis_cpm = {"A": 1200.0, "B": 1200.0, "C": 800.0, "D": 500.0}
    screen._cpm_ready = True
    screen._current_step_mm = 10.0

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen.jog_axis("A", 1)

    assert len(submitted_fns) == 1
    submitted_fns[0]()

    cmds = [c[0][0] for c in ctrl.cmd.call_args_list]
    assert cmds[0] == "PRA=12000"
    assert cmds[1] == "BGA"
    assert "MG _BGA" in cmds  # motion-complete poll
    assert cmds[-1] == "MG _TDA"  # readback position after motion complete


def test_jog_counts_negative():
    """jog_axis('A', -1) with step_mm=5.0 and cpm=1200 produces PR A=-6000."""
    from unittest.mock import MagicMock, patch, call
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    ctrl.cmd.return_value = " 0.0000 "
    screen.controller = ctrl
    screen._axis_cpm = {"A": 1200.0, "B": 1200.0, "C": 800.0, "D": 500.0}
    screen._cpm_ready = True
    screen._current_step_mm = 5.0

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen.jog_axis("A", -1)

    assert len(submitted_fns) == 1
    submitted_fns[0]()
    cmds = [c[0][0] for c in ctrl.cmd.call_args_list]
    assert cmds[0] == "PRA=-6000"
    assert cmds[1] == "BGA"
    assert cmds[-1] == "MG _TDA"  # readback after motion complete


def test_jog_blocked_before_cpm_read():
    """jog_axis does nothing when _cpm_ready is False (CPM not yet read from controller)."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    screen.controller = ctrl
    # _cpm_ready defaults to False — jog must be blocked
    assert screen._cpm_ready is False

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen.jog_axis("A", 1)

    assert len(submitted_fns) == 0


def test_jog_no_controller():
    """jog_axis does nothing when controller is None."""
    from unittest.mock import patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    screen.controller = None

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen.jog_axis("A", 1)

    assert len(submitted_fns) == 0


def test_jog_disconnected():
    """jog_axis does nothing when controller is disconnected."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = False
    screen.controller = ctrl

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen.jog_axis("A", 1)

    assert len(submitted_fns) == 0


# ── Teach ─────────────────────────────────────────────────────────────────────


def test_teach_rest_burns_nv():
    """teach_rest_point() reads TD positions, writes restPtA/B/C/D, sends BV."""
    from unittest.mock import MagicMock, patch, call
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True

    ctrl.cmd.side_effect = [
        "  1000.0000  ",  # _TDA
        "  2000.0000  ",  # _TDB
        "  3000.0000  ",  # _TDC
        "  4000.0000  ",  # _TDD
        "",                # write cmd
        "",                # BV
        # Readback: restPt + _TD for each axis (A, B, C, D)
        "  1000.0000  ", "  1000.0000  ",
        "  2000.0000  ", "  2000.0000  ",
        "  3000.0000  ", "  3000.0000  ",
        "  4000.0000  ", "  4000.0000  ",
    ]
    screen.controller = ctrl
    screen.state = MagicMock()
    screen.state.cycle_running = False

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        with patch('dmccodegui.screens.axes_setup.Clock'):
            mock_jobs.submit = lambda fn: submitted_fns.append(fn)
            screen.teach_rest_point()

    assert len(submitted_fns) == 1
    submitted_fns[0]()

    calls = ctrl.cmd.call_args_list
    cmds_sent = [c[0][0] for c in calls]

    assert "MG _TDA" in cmds_sent
    assert "MG _TDB" in cmds_sent
    assert "MG _TDC" in cmds_sent
    assert "MG _TDD" in cmds_sent

    write_cmd = next((c for c in cmds_sent if "restPtA" in c and "restPtB" in c), None)
    assert write_cmd is not None, f"Expected combined restPt write, got: {cmds_sent}"

    assert "BV" in cmds_sent


def test_teach_start_burns_nv():
    """teach_start_point() reads TD positions, writes startPtA/B/C/D, sends BV."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    ctrl.cmd.side_effect = [
        "  500.0000  ",
        "  600.0000  ",
        "  700.0000  ",
        "  800.0000  ",
        "",
        "",
        # Readback: startPt + _TD for each axis
        "  500.0000  ", "  500.0000  ",
        "  600.0000  ", "  600.0000  ",
        "  700.0000  ", "  700.0000  ",
        "  800.0000  ", "  800.0000  ",
    ]
    screen.controller = ctrl
    screen.state = MagicMock()
    screen.state.cycle_running = False

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        with patch('dmccodegui.screens.axes_setup.Clock'):
            mock_jobs.submit = lambda fn: submitted_fns.append(fn)
            screen.teach_start_point()

    assert len(submitted_fns) == 1
    submitted_fns[0]()

    cmds_sent = [c[0][0] for c in ctrl.cmd.call_args_list]

    write_cmd = next((c for c in cmds_sent if "startPtA" in c and "startPtB" in c), None)
    assert write_cmd is not None, f"Expected combined startPt write, got: {cmds_sent}"
    assert "BV" in cmds_sent


def test_teach_skips_when_cycle_running():
    """teach_rest_point() does nothing when cycle_running=True."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    screen.controller = ctrl
    screen.state = MagicMock()
    screen.state.cycle_running = True

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen.teach_rest_point()

    assert len(submitted_fns) == 0


# ── Quick actions ─────────────────────────────────────────────────────────────


def test_quick_action_go_rest():
    """go_to_rest_all() submits swGoRest=1 to controller."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    ctrl.cmd.return_value = ""
    screen.controller = ctrl

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen.go_to_rest_all()

    assert len(submitted_fns) == 1
    submitted_fns[0]()
    ctrl.cmd.assert_called_once_with("swGoRest=1")


def test_quick_action_go_start():
    """go_to_start_all() submits swGoStart=1 to controller."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    ctrl.cmd.return_value = ""
    screen.controller = ctrl

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen.go_to_start_all()

    assert len(submitted_fns) == 1
    submitted_fns[0]()
    ctrl.cmd.assert_called_once_with("swGoStart=1")


def test_quick_action_home_all():
    """home_all() submits swHomeAll=1 to controller."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    ctrl.cmd.return_value = ""
    screen.controller = ctrl

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen.home_all()

    assert len(submitted_fns) == 1
    submitted_fns[0]()
    ctrl.cmd.assert_called_once_with("swHomeAll=1")


# ── No-polling verification ──────────────────────────────────────────────────


def test_no_poll_tick_method():
    """AxesSetupScreen has no _poll_tick — polling was removed."""
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    assert not hasattr(AxesSetupScreen, '_poll_tick')


def test_no_selected_axis():
    """AxesSetupScreen no longer has _selected_axis — all axes visible."""
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    screen = AxesSetupScreen()
    assert not hasattr(screen, '_selected_axis')


# ── Smart enter/exit (Plan 02) ────────────────────────────────────────────────


def test_enter_setup_skips_fire_when_already_setup():
    """on_pre_enter with dmc_state=STATE_SETUP does NOT fire hmiSetp=0."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    from dmccodegui.hmi.dmc_vars import STATE_SETUP, HMI_SETP, HMI_TRIGGER_FIRE

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    ctrl.cmd.return_value = "0.0000"
    screen.controller = ctrl
    screen.state = MagicMock()
    screen.state.dmc_state = STATE_SETUP  # already in setup

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        with patch('dmccodegui.screens.axes_setup.Clock'):
            mock_jobs.submit = lambda fn: submitted_fns.append(fn)
            screen.on_pre_enter()

    # Execute the submitted background job(s)
    for fn in submitted_fns:
        fn()

    setp_fire_cmd = f"{HMI_SETP}={HMI_TRIGGER_FIRE}"
    all_cmds = [c[0][0] for c in ctrl.cmd.call_args_list]
    assert setp_fire_cmd not in all_cmds, (
        f"hmiSetp=0 must NOT be sent when already in setup, but got: {all_cmds}"
    )


def test_enter_setup_fires_when_not_in_setup():
    """on_pre_enter with dmc_state != STATE_SETUP fires hmiSetp=0."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    from dmccodegui.hmi.dmc_vars import STATE_IDLE, HMI_SETP, HMI_TRIGGER_FIRE

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    ctrl.cmd.return_value = "0.0000"
    screen.controller = ctrl
    screen.state = MagicMock()
    screen.state.dmc_state = STATE_IDLE  # not in setup

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        with patch('dmccodegui.screens.axes_setup.Clock'):
            mock_jobs.submit = lambda fn: submitted_fns.append(fn)
            screen.on_pre_enter()

    for fn in submitted_fns:
        fn()

    setp_fire_cmd = f"{HMI_SETP}={HMI_TRIGGER_FIRE}"
    all_cmds = [c[0][0] for c in ctrl.cmd.call_args_list]
    assert setp_fire_cmd in all_cmds, (
        f"hmiSetp=0 must be sent when transitioning into setup, but got: {all_cmds}"
    )


def test_exit_fires_to_non_setup_screen():
    """on_leave when navigating to 'run' screen fires hmiExSt=0."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    from dmccodegui.hmi.dmc_vars import HMI_EXIT_SETUP, HMI_TRIGGER_FIRE

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    screen.controller = ctrl

    manager = MagicMock()
    manager.current = "run"
    screen.manager = manager

    screen.on_leave()

    exit_cmd = f"{HMI_EXIT_SETUP}={HMI_TRIGGER_FIRE}"
    all_cmds = [c[0][0] for c in ctrl.cmd.call_args_list]
    assert exit_cmd in all_cmds, (
        f"hmiExSt=0 must fire when leaving to non-setup screen, but got: {all_cmds}"
    )


def test_exit_skips_to_sibling_setup_screen():
    """on_leave when navigating to 'parameters' screen does NOT fire hmiExSt=0."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    from dmccodegui.hmi.dmc_vars import HMI_EXIT_SETUP, HMI_TRIGGER_FIRE

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    screen.controller = ctrl

    manager = MagicMock()
    manager.current = "parameters"
    screen.manager = manager

    screen.on_leave()

    exit_cmd = f"{HMI_EXIT_SETUP}={HMI_TRIGGER_FIRE}"
    all_cmds = [c[0][0] for c in ctrl.cmd.call_args_list]
    assert exit_cmd not in all_cmds, (
        f"hmiExSt=0 must NOT fire when leaving to sibling setup screen, but got: {all_cmds}"
    )


# ── HMI trigger quick actions (Plan 02) ──────────────────────────────────────


def test_home_all_fires_hmi_trigger():
    """home_all() fires hmiHome=0 (not swHomeAll=1)."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    from dmccodegui.hmi.dmc_vars import HMI_HOME, HMI_TRIGGER_FIRE

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    ctrl.cmd.return_value = ""
    screen.controller = ctrl

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen.home_all()

    assert len(submitted_fns) == 1
    submitted_fns[0]()
    ctrl.cmd.assert_called_once_with(f"{HMI_HOME}={HMI_TRIGGER_FIRE}")


def test_go_to_rest_fires_hmi_trigger():
    """go_to_rest_all() fires hmiGoRs=0 (not swGoRest=1)."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    from dmccodegui.hmi.dmc_vars import HMI_GO_REST, HMI_TRIGGER_FIRE

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    ctrl.cmd.return_value = ""
    screen.controller = ctrl

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen.go_to_rest_all()

    assert len(submitted_fns) == 1
    submitted_fns[0]()
    ctrl.cmd.assert_called_once_with(f"{HMI_GO_REST}={HMI_TRIGGER_FIRE}")


def test_go_to_start_fires_hmi_trigger():
    """go_to_start_all() fires hmiGoSt=0 (not swGoStart=1)."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    from dmccodegui.hmi.dmc_vars import HMI_GO_START, HMI_TRIGGER_FIRE

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    ctrl.cmd.return_value = ""
    screen.controller = ctrl

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen.go_to_start_all()

    assert len(submitted_fns) == 1
    submitted_fns[0]()
    ctrl.cmd.assert_called_once_with(f"{HMI_GO_START}={HMI_TRIGGER_FIRE}")


# ── Jog gates (Plan 02) ───────────────────────────────────────────────────────


def test_jog_blocked_when_not_setup():
    """jog_axis returns without any cmd when dmc_state != STATE_SETUP."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    from dmccodegui.hmi.dmc_vars import STATE_IDLE

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    ctrl.cmd.return_value = " 0.0000 "
    screen.controller = ctrl
    screen.state = MagicMock()
    screen.state.dmc_state = STATE_IDLE  # NOT setup
    screen._axis_cpm = {"A": 1200.0}
    screen._cpm_ready = True

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen.jog_axis("A", 1)

    assert len(submitted_fns) == 0, (
        "No job should be submitted when dmc_state != STATE_SETUP"
    )


def test_jog_blocked_when_in_progress():
    """jog_axis does not send PR/BG when _BG{axis} is nonzero (motion in progress)."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    from dmccodegui.hmi.dmc_vars import STATE_SETUP

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    # _BG returns nonzero = motion in progress
    ctrl.cmd.return_value = " 1.0000 "
    screen.controller = ctrl
    screen.state = MagicMock()
    screen.state.dmc_state = STATE_SETUP
    screen._axis_cpm = {"A": 1200.0}
    screen._cpm_ready = True

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen.jog_axis("A", 1)

    # Job is submitted, but do_jog should bail before PR/BG
    for fn in submitted_fns:
        fn()

    all_cmds = [c[0][0] for c in ctrl.cmd.call_args_list]
    assert "PRA=12000" not in all_cmds, (
        f"PR must NOT be sent when motion in progress, got: {all_cmds}"
    )
    assert "BGA" not in all_cmds, (
        f"BG must NOT be sent when motion in progress, got: {all_cmds}"
    )


# ── New Session (Plan 02) ─────────────────────────────────────────────────────


def test_new_session_fires_hmi_news():
    """_fire_new_session() fires hmiNewS=0."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    from dmccodegui.hmi.dmc_vars import HMI_NEWS, HMI_TRIGGER_FIRE

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    ctrl.cmd.return_value = ""
    screen.controller = ctrl

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen._fire_new_session()

    assert len(submitted_fns) == 1
    submitted_fns[0]()
    ctrl.cmd.assert_called_once_with(f"{HMI_NEWS}={HMI_TRIGGER_FIRE}")


def test_new_session_blocked_for_operator():
    """on_new_session() with setup_unlocked=False does not open a Popup."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    screen.state = MagicMock()
    screen.state.setup_unlocked = False

    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        submitted_fns = []
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen.on_new_session()

    # No jobs submitted means no trigger fired — operator was blocked
    assert len(submitted_fns) == 0, (
        "on_new_session must not submit any job when setup_unlocked=False"
    )
