"""
Tests for AxesSetupScreen — jog math, teach sequences, polling lifecycle, quick actions.

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


# ── Property defaults ─────────────────────────────────────────────────────────


def test_selected_axis_default():
    """AXES-01: _selected_axis defaults to 'A'."""
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    screen = AxesSetupScreen()
    assert screen._selected_axis == "A"


def test_select_axis():
    """AXES-01: select_axis('B') updates _selected_axis."""
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    screen = AxesSetupScreen()
    screen.select_axis("B")
    assert screen._selected_axis == "B"


def test_step_mm_property():
    """AXES-02: _current_step_mm defaults to 10.0; set_step changes it."""
    from dmccodegui.screens.axes_setup import AxesSetupScreen
    screen = AxesSetupScreen()
    assert screen._current_step_mm == 10.0
    screen.set_step(5.0)
    assert screen._current_step_mm == 5.0
    screen.set_step(1.0)
    assert screen._current_step_mm == 1.0


def test_cpm_defaults():
    """AXES-02: AXIS_CPM_DEFAULTS has all 4 axes with positive values."""
    from dmccodegui.screens.axes_setup import AXIS_CPM_DEFAULTS
    assert set(AXIS_CPM_DEFAULTS.keys()) == {"A", "B", "C", "D"}
    for axis, cpm in AXIS_CPM_DEFAULTS.items():
        assert cpm > 0, f"CPM for {axis} must be positive, got {cpm}"


# ── Jog math ─────────────────────────────────────────────────────────────────


def test_jog_counts_calculation():
    """AXES-02: jog_axis('A', +1) with step_mm=10.0 and cpm=1200 produces PR A=12000."""
    from unittest.mock import MagicMock, patch, call
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    screen.controller = ctrl

    # Inject CPM
    screen._axis_cpm = {"A": 1200.0, "B": 1200.0, "C": 800.0, "D": 500.0}
    screen._current_step_mm = 10.0

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen.jog_axis("A", 1)

    # Should have submitted exactly one background job
    assert len(submitted_fns) == 1

    # Execute the submitted job to inspect what it sends
    submitted_fns[0]()

    calls = ctrl.cmd.call_args_list
    assert len(calls) == 2
    assert calls[0] == call("PRA=12000")
    assert calls[1] == call("BGA")


def test_jog_counts_negative():
    """AXES-02: jog_axis('A', -1) with step_mm=5.0 and cpm=1200 produces PR A=-6000."""
    from unittest.mock import MagicMock, patch, call
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    screen.controller = ctrl
    screen._axis_cpm = {"A": 1200.0, "B": 1200.0, "C": 800.0, "D": 500.0}
    screen._current_step_mm = 5.0

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen.jog_axis("A", -1)

    assert len(submitted_fns) == 1
    submitted_fns[0]()
    calls = ctrl.cmd.call_args_list
    assert calls[0] == call("PRA=-6000")
    assert calls[1] == call("BGA")


def test_jog_no_controller():
    """AXES-02: jog_axis does nothing when controller is None."""
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
    """AXES-02: jog_axis does nothing when controller is disconnected."""
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
    """AXES-03: teach_rest_point() reads TD positions, writes restPtA/B/C/D, sends BV."""
    from unittest.mock import MagicMock, patch, call
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True

    # Simulate controller returning position values
    ctrl.cmd.side_effect = [
        "  1000.0000  ",  # _TDA
        "  2000.0000  ",  # _TDB
        "  3000.0000  ",  # _TDC
        "  4000.0000  ",  # _TDD
        "",                # write cmd (semicolon-separated)
        "",                # BV
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

    # Must read all 4 TD positions
    assert "MG _TDA" in cmds_sent
    assert "MG _TDB" in cmds_sent
    assert "MG _TDC" in cmds_sent
    assert "MG _TDD" in cmds_sent

    # Must write all 4 rest points
    write_cmd = next((c for c in cmds_sent if "restPtA" in c and "restPtB" in c), None)
    assert write_cmd is not None, f"Expected combined restPt write, got: {cmds_sent}"

    # Must send BV to burn NV memory
    assert "BV" in cmds_sent


def test_teach_start_burns_nv():
    """AXES-03: teach_start_point() reads TD positions, writes startPtA/B/C/D, sends BV."""
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
    """AXES-03: teach_rest_point() does nothing when cycle_running=True."""
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
    """AXES-04: go_to_rest_all() submits swGoRest=1 to controller."""
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
    """AXES-04: go_to_start_all() submits swGoStart=1 to controller."""
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
    """AXES-04: home_all() submits swHomeAll=1 to controller."""
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


# ── Polling ───────────────────────────────────────────────────────────────────


def test_poll_disconnected_noop():
    """AXES-05: _poll_tick does nothing when controller is not connected."""
    from unittest.mock import MagicMock, patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    ctrl = MagicMock()
    ctrl.is_connected.return_value = False
    screen.controller = ctrl

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen._poll_tick(0)

    assert len(submitted_fns) == 0


def test_poll_no_controller_noop():
    """AXES-05: _poll_tick does nothing when controller is None."""
    from unittest.mock import patch
    from dmccodegui.screens.axes_setup import AxesSetupScreen

    screen = AxesSetupScreen()
    screen.controller = None

    submitted_fns = []
    with patch('dmccodegui.screens.axes_setup.jobs') as mock_jobs:
        mock_jobs.submit = lambda fn: submitted_fns.append(fn)
        screen._poll_tick(0)

    assert len(submitted_fns) == 0
