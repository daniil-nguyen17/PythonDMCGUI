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
