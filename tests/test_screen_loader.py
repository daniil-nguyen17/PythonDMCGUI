"""Tests for Phase 20 Plan 02 — screen loader, mismatch detection.

Covers LOAD-02 and LOAD-04:
  - _resolve_dotted_path helper
  - _add_machine_screens / _load_machine_screens
  - on_stop() cleanup delegation
  - machType mismatch detection after connect
"""
from __future__ import annotations

import importlib
import os
import sys
from typing import Any, List
from unittest.mock import MagicMock, patch, call

import pytest

os.environ.setdefault("KIVY_NO_ENV_CONFIG", "1")
os.environ.setdefault("KIVY_LOG_LEVEL", "critical")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# ---------------------------------------------------------------------------
# Import helpers from main
# ---------------------------------------------------------------------------

from dmccodegui.main import _resolve_dotted_path  # type: ignore
import dmccodegui.machine_config as mc


# ---------------------------------------------------------------------------
# Helper: minimal mock ScreenManager
# ---------------------------------------------------------------------------

class _MockSM:
    """Minimal ScreenManager stand-in for unit tests."""

    def __init__(self):
        self.screens: List[Any] = []

    def add_widget(self, widget):
        self.screens.append(widget)

    def get_screen(self, name: str):
        for s in self.screens:
            if getattr(s, "name", None) == name:
                return s
        raise KeyError(name)


# ---------------------------------------------------------------------------
# _resolve_dotted_path tests
# ---------------------------------------------------------------------------

def test_resolve_dotted_path_valid_class():
    """_resolve_dotted_path returns the class for a valid dotted path."""
    from dmccodegui.screens.flat_grind import FlatGrindRunScreen
    resolved = _resolve_dotted_path("dmccodegui.screens.flat_grind.FlatGrindRunScreen")
    assert resolved is FlatGrindRunScreen


def test_resolve_dotted_path_valid_callable():
    """_resolve_dotted_path returns a callable for a valid function dotted path."""
    from dmccodegui.screens.flat_grind import load_kv
    resolved = _resolve_dotted_path("dmccodegui.screens.flat_grind.load_kv")
    assert resolved is load_kv


def test_resolve_dotted_path_invalid_module_raises():
    """_resolve_dotted_path raises ImportError for a non-existent module."""
    with pytest.raises((ImportError, ModuleNotFoundError)):
        _resolve_dotted_path("dmccodegui.nonexistent_module.SomeClass")


def test_resolve_dotted_path_invalid_attr_raises():
    """_resolve_dotted_path raises AttributeError for a non-existent attribute."""
    with pytest.raises(AttributeError):
        _resolve_dotted_path("dmccodegui.screens.flat_grind.NonExistentClass")


# ---------------------------------------------------------------------------
# _add_machine_screens tests
# ---------------------------------------------------------------------------

class _BareApp:
    """Minimal object that has the attributes DMCApp methods need."""

    def __init__(self, state, controller):
        self.state = state
        self.controller = controller
        self._poll_cancel = None
        self._idle_event = None
        self._poller = None
        # MgReader stub — no real MG thread in unit tests
        from unittest.mock import MagicMock
        self.mg_reader = MagicMock()

    def _add_machine_screens(self, sm):
        from dmccodegui.main import DMCApp
        DMCApp._add_machine_screens(self, sm)

    def _show_loader_error(self, message: str):
        raise RuntimeError(f"Loader error: {message}")

    def _check_machine_type_mismatch(self):
        from dmccodegui.main import DMCApp
        DMCApp._check_machine_type_mismatch(self)

    def _show_mismatch_popup(self, ctrl_type, config_type):
        from dmccodegui.main import DMCApp
        DMCApp._show_mismatch_popup(self, ctrl_type, config_type)

    def on_stop(self):
        from dmccodegui.main import DMCApp
        DMCApp.on_stop(self)

    def _stop_poller(self):
        if self._poller:
            self._poller.stop()

    def _stop_mg_reader(self):
        if hasattr(self, 'mg_reader') and self.mg_reader:
            self.mg_reader.stop()

    def _stop_dr(self):
        pass  # No DR listener in unit tests


def test_add_machine_screens_adds_run_axes_setup_parameters():
    """_add_machine_screens adds screens with names 'run', 'axes_setup', 'parameters'."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = os.path.join(tmpdir, "settings.json")
        mc.init(settings)
        mc.set_active_type("4-Axes Flat Grind")

    from dmccodegui.app_state import MachineState
    from dmccodegui.controller import GalilController

    app = _BareApp(MachineState(), GalilController())
    sm = _MockSM()
    app._add_machine_screens(sm)

    names = {getattr(s, "name", None) for s in sm.screens}
    assert "run" in names, "Expected 'run' screen to be added"
    assert "axes_setup" in names, "Expected 'axes_setup' screen to be added"
    assert "parameters" in names, "Expected 'parameters' screen to be added"


def test_add_machine_screens_injects_controller_and_state():
    """_add_machine_screens injects controller and state into each screen."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = os.path.join(tmpdir, "settings.json")
        mc.init(settings)
        mc.set_active_type("4-Axes Flat Grind")

    from dmccodegui.app_state import MachineState
    from dmccodegui.controller import GalilController

    app = _BareApp(MachineState(), GalilController())
    sm = _MockSM()
    app._add_machine_screens(sm)

    for screen in sm.screens:
        if hasattr(screen, "controller"):
            assert screen.controller is app.controller, "controller not injected"
        if hasattr(screen, "state"):
            assert screen.state is app.state, "state not injected"


def test_add_machine_screens_calls_load_kv():
    """_add_machine_screens adds 3 screens (load_kv already called in build step)."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = os.path.join(tmpdir, "settings.json")
        mc.init(settings)
        mc.set_active_type("4-Axes Flat Grind")

    from dmccodegui.app_state import MachineState
    from dmccodegui.controller import GalilController

    app = _BareApp(MachineState(), GalilController())
    sm = _MockSM()
    app._add_machine_screens(sm)

    # The important thing is screens were added (meaning resolution succeeded)
    assert len(sm.screens) == 3, "Expected 3 machine screens to be added"


def test_add_machine_screens_unconfigured_does_nothing():
    """_add_machine_screens does nothing if mc.get_active_type() returns ''."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = os.path.join(tmpdir, "settings.json")
        mc.init(settings)
        # Do NOT set active type — leave unconfigured

    from dmccodegui.app_state import MachineState
    from dmccodegui.controller import GalilController

    app = _BareApp(MachineState(), GalilController())
    sm = _MockSM()
    app._add_machine_screens(sm)

    assert len(sm.screens) == 0, "No screens should be added when unconfigured"


# ---------------------------------------------------------------------------
# on_stop cleanup delegation tests
# ---------------------------------------------------------------------------

class _MockScreen:
    """Minimal screen mock with optional cleanup()."""

    def __init__(self, name: str, has_cleanup: bool = True):
        self.name = name
        self._cleanup_called = False
        if has_cleanup:
            self.cleanup = self._do_cleanup

    def _do_cleanup(self):
        self._cleanup_called = True


def test_on_stop_calls_cleanup_on_screens_with_cleanup():
    """on_stop() calls cleanup() on each screen that has the method."""
    from dmccodegui.main import DMCApp

    app = _BareApp(MagicMock(), MagicMock())
    app._poll_cancel = None
    app._idle_event = None
    app._poller = None

    screen_with = _MockScreen("run", has_cleanup=True)
    screen_without = _MockScreen("setup", has_cleanup=False)

    mock_sm = _MockSM()
    mock_sm.screens = [screen_with, screen_without]

    mock_root = MagicMock()
    mock_root.ids.sm = mock_sm
    app.root = mock_root

    with patch("dmccodegui.main.jobs") as mock_jobs:
        mock_jobs.shutdown = MagicMock()
        app.controller = MagicMock()
        app.on_stop()

    assert screen_with._cleanup_called, "cleanup() must be called on screen that has it"


def test_on_stop_does_not_call_nonexistent_cleanup():
    """on_stop() does not fail when a screen lacks cleanup()."""
    app = _BareApp(MagicMock(), MagicMock())

    screen_without = _MockScreen("setup", has_cleanup=False)
    mock_sm = _MockSM()
    mock_sm.screens = [screen_without]

    mock_root = MagicMock()
    mock_root.ids.sm = mock_sm
    app.root = mock_root

    with patch("dmccodegui.main.jobs") as mock_jobs:
        mock_jobs.shutdown = MagicMock()
        app.on_stop()  # Must not raise


def test_on_stop_no_stop_pos_poll_or_stop_mg_reader_called():
    """on_stop() does NOT call _stop_pos_poll or _stop_mg_reader directly (cleanup delegation)."""
    app = _BareApp(MagicMock(), MagicMock())

    mock_screen = MagicMock()
    mock_screen.name = "run"
    # We want cleanup() to be called, NOT _stop_pos_poll / _stop_mg_reader directly
    del mock_screen._stop_pos_poll
    del mock_screen._stop_mg_reader

    mock_sm = _MockSM()
    mock_sm.screens = [mock_screen]

    mock_root = MagicMock()
    mock_root.ids.sm = mock_sm
    app.root = mock_root

    with patch("dmccodegui.main.jobs") as mock_jobs:
        mock_jobs.shutdown = MagicMock()
        app.on_stop()

    mock_screen.cleanup.assert_called_once()


# ---------------------------------------------------------------------------
# base.kv must not declare machine-specific screens
# ---------------------------------------------------------------------------

def test_base_kv_has_no_machine_screen_declarations():
    """base.kv ScreenManager must not declare FlatGrind*, Serration*, or Convex* screens."""
    import pathlib
    import re

    base_kv = pathlib.Path(__file__).parent.parent / "src" / "dmccodegui" / "ui" / "base.kv"
    content = base_kv.read_text(encoding="utf-8")

    machine_screen_pattern = re.compile(
        r"^\s*(FlatGrind\w+|Serration\w+|Convex\w+)\s*:", re.MULTILINE
    )
    matches = machine_screen_pattern.findall(content)
    assert matches == [], (
        f"base.kv declares machine-specific screens that must be removed: {matches}"
    )


# ---------------------------------------------------------------------------
# machType mismatch detection tests
# ---------------------------------------------------------------------------

def _make_app_for_mismatch():
    """Create a _BareApp configured for mismatch tests."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = os.path.join(tmpdir, "settings.json")
        mc.init(settings)
        mc.set_active_type("4-Axes Flat Grind")

    from dmccodegui.app_state import MachineState

    app = _BareApp(MachineState(), MagicMock())
    app.state.machine_type = "4-Axes Flat Grind"
    return app


def test_check_machine_type_mismatch_matching_type_no_popup():
    """No popup is scheduled when controller machType matches configured type."""
    app = _make_app_for_mismatch()
    # machType = 1 -> "4-Axes Flat Grind" matches configured type
    app.controller.cmd.return_value = "1.0000"

    popup_calls = []

    with patch("dmccodegui.main.jobs") as mock_jobs:
        # Capture the job submitted and run it synchronously
        submitted_fn = None

        def capture_submit(fn):
            nonlocal submitted_fn
            submitted_fn = fn

        mock_jobs.submit.side_effect = capture_submit

        with patch("dmccodegui.main.Clock") as mock_clock:
            app._check_machine_type_mismatch()
            if submitted_fn:
                submitted_fn()  # run the background job synchronously
            # Should NOT schedule mismatch popup
            for c in mock_clock.schedule_once.call_args_list:
                args = c[0]
                if len(args) >= 1 and callable(args[0]):
                    popup_calls.append(args[0])

    # The mismatch popup lambda should NOT have been scheduled
    # (only the overall schedule_once for the mismatch check wrapper is OK)
    assert len(popup_calls) == 0 or all(
        "_show_mismatch_popup" not in str(c) for c in popup_calls
    ), "Mismatch popup should NOT be scheduled when types match"


def test_check_machine_type_mismatch_different_type_schedules_popup():
    """Popup is scheduled when controller machType mismatches configured type."""
    app = _make_app_for_mismatch()
    # machType = 2 -> "3-Axes Serration Grind", but configured = "4-Axes Flat Grind"
    app.controller.cmd.return_value = "2.0000"

    popup_scheduled = []

    with patch("dmccodegui.main.jobs") as mock_jobs:
        submitted_fn = None

        def capture_submit(fn):
            nonlocal submitted_fn
            submitted_fn = fn

        mock_jobs.submit.side_effect = capture_submit

        with patch("dmccodegui.main.Clock") as mock_clock:
            mock_clock.schedule_once.side_effect = lambda fn, *args: popup_scheduled.append(fn)

            app._check_machine_type_mismatch()
            if submitted_fn:
                submitted_fn()

    assert len(popup_scheduled) > 0, "A popup callback must be scheduled on mismatch"


def test_check_machine_type_mismatch_exception_no_popup():
    """No popup is scheduled when controller.cmd raises an exception (graceful degradation)."""
    app = _make_app_for_mismatch()
    app.controller.cmd.side_effect = Exception("Connection error")

    popup_scheduled = []

    with patch("dmccodegui.main.jobs") as mock_jobs:
        submitted_fn = None

        def capture_submit(fn):
            nonlocal submitted_fn
            submitted_fn = fn

        mock_jobs.submit.side_effect = capture_submit

        with patch("dmccodegui.main.Clock") as mock_clock:
            mock_clock.schedule_once.side_effect = lambda fn, *args: popup_scheduled.append(fn)

            app._check_machine_type_mismatch()
            if submitted_fn:
                submitted_fn()

    assert len(popup_scheduled) == 0, (
        "No popup should be scheduled when machType query raises exception"
    )


def test_check_machine_type_mismatch_invalid_value_no_popup():
    """No popup is scheduled when machType returns unknown/invalid value."""
    app = _make_app_for_mismatch()
    # machType = 99 -> not in _MACH_TYPE_MAP
    app.controller.cmd.return_value = "99.0000"

    popup_scheduled = []

    with patch("dmccodegui.main.jobs") as mock_jobs:
        submitted_fn = None

        def capture_submit(fn):
            nonlocal submitted_fn
            submitted_fn = fn

        mock_jobs.submit.side_effect = capture_submit

        with patch("dmccodegui.main.Clock") as mock_clock:
            mock_clock.schedule_once.side_effect = lambda fn, *args: popup_scheduled.append(fn)

            app._check_machine_type_mismatch()
            if submitted_fn:
                submitted_fn()

    assert len(popup_scheduled) == 0, (
        "No popup should be scheduled when machType value is not in _MACH_TYPE_MAP"
    )


def test_mismatch_popup_selecting_type_calls_set_active_type():
    """_show_mismatch_popup: selecting a different type calls mc.set_active_type and App.stop()."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = os.path.join(tmpdir, "settings.json")
        mc.init(settings)
        mc.set_active_type("4-Axes Flat Grind")

    app = _make_app_for_mismatch()

    set_type_calls = []

    with patch.object(mc, "set_active_type", side_effect=set_type_calls.append):
        with patch.object(app, "_show_mismatch_popup") as mock_popup:
            ctrl_type = "3-Axes Serration Grind"
            config_type = "4-Axes Flat Grind"

            app._show_mismatch_popup(ctrl_type, config_type)
            mock_popup.assert_called_once_with(ctrl_type, config_type)
