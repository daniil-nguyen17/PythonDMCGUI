"""Tests for Phase 18 base screen classes.

Covers ARCH-01 (base class inheritance), ARCH-02 (subscribe/unsubscribe lifecycle),
and ARCH-04 (no lifecycle hooks in .kv files).
"""
import os
import sys

# Set Kivy env vars before any Kivy import (Pitfall #4 from RESEARCH.md)
os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest


# ---------------------------------------------------------------------------
# ARCH-01: Base class inheritance
# ---------------------------------------------------------------------------

def test_base_class_inheritance():
    """ARCH-01: All base classes importable and inherit from Screen correctly."""
    from kivy.uix.screenmanager import Screen
    from dmccodegui.screens.base import (
        BaseRunScreen,
        BaseAxesSetupScreen,
        BaseParametersScreen,
        SetupScreenMixin,
    )

    # All three inherit from Screen
    assert issubclass(BaseRunScreen, Screen), "BaseRunScreen must inherit from Screen"
    assert issubclass(BaseAxesSetupScreen, Screen), "BaseAxesSetupScreen must inherit from Screen"
    assert issubclass(BaseParametersScreen, Screen), "BaseParametersScreen must inherit from Screen"

    # SetupScreenMixin applied to correct classes
    assert issubclass(BaseAxesSetupScreen, SetupScreenMixin), \
        "BaseAxesSetupScreen must inherit from SetupScreenMixin"
    assert issubclass(BaseParametersScreen, SetupScreenMixin), \
        "BaseParametersScreen must inherit from SetupScreenMixin"

    # BaseRunScreen does NOT use SetupScreenMixin
    assert not issubclass(BaseRunScreen, SetupScreenMixin), \
        "BaseRunScreen must NOT inherit from SetupScreenMixin (run screens don't enter setup mode)"


# ---------------------------------------------------------------------------
# Mock MachineState helper
# ---------------------------------------------------------------------------

class _MockMachineState:
    """Minimal MachineState mock with a working subscribe/unsubscribe pattern."""

    def __init__(self):
        self._listeners = []
        self.dmc_state = 0
        self.connected = True
        self.cycle_running = False
        self.setup_unlocked = True

    def subscribe(self, fn):
        self._listeners.append(fn)

        def unsubscribe():
            try:
                self._listeners.remove(fn)
            except ValueError:
                pass  # already removed — safe to call twice

        return unsubscribe

    def notify(self):
        """Simulate a state change notification."""
        for fn in list(self._listeners):
            fn(self)


# ---------------------------------------------------------------------------
# ARCH-02: Subscribe/unsubscribe lifecycle — BaseRunScreen
# ---------------------------------------------------------------------------

def test_subscription_lifecycle():
    """ARCH-02: BaseRunScreen subscribes on_pre_enter, unsubscribes on_leave.

    After two enter/leave cycles, zero duplicate callbacks remain in the mock
    listener list.
    """
    from dmccodegui.screens.base import BaseRunScreen

    state = _MockMachineState()
    screen = BaseRunScreen()
    screen.state = state

    assert len(state._listeners) == 0, "No listeners before on_pre_enter"

    # Cycle 1
    screen.on_pre_enter()
    assert screen._state_unsub is not None, "_state_unsub must be set after on_pre_enter"
    assert len(state._listeners) == 1, "Exactly 1 listener after on_pre_enter"

    screen.on_leave()
    assert screen._state_unsub is None, "_state_unsub must be None after on_leave"
    assert len(state._listeners) == 0, "Zero listeners after on_leave"

    # Cycle 2
    screen.on_pre_enter()
    assert len(state._listeners) == 1, "Exactly 1 listener after second on_pre_enter"

    screen.on_leave()
    assert len(state._listeners) == 0, "Zero listeners after second on_leave (no accumulation)"


# ---------------------------------------------------------------------------
# ARCH-02: Subscribe/unsubscribe lifecycle — BaseAxesSetupScreen
# ---------------------------------------------------------------------------

def test_subscribe_on_enter_unsubscribe_on_leave_axes():
    """ARCH-02: BaseAxesSetupScreen subscribe/unsubscribe lifecycle."""
    from dmccodegui.screens.base import BaseAxesSetupScreen

    state = _MockMachineState()
    screen = BaseAxesSetupScreen()
    screen.state = state
    # No controller → _enter/_exit_setup_if_needed are no-ops

    assert len(state._listeners) == 0

    screen.on_pre_enter()
    assert screen._state_unsub is not None
    assert len(state._listeners) == 1

    screen.on_leave()
    assert screen._state_unsub is None
    assert len(state._listeners) == 0

    # Two cycles — no accumulation
    screen.on_pre_enter()
    screen.on_leave()
    assert len(state._listeners) == 0


# ---------------------------------------------------------------------------
# ARCH-02: Subscribe/unsubscribe lifecycle — BaseParametersScreen
# ---------------------------------------------------------------------------

def test_subscribe_on_enter_unsubscribe_on_leave_params():
    """ARCH-02: BaseParametersScreen subscribe/unsubscribe lifecycle."""
    from dmccodegui.screens.base import BaseParametersScreen

    state = _MockMachineState()
    screen = BaseParametersScreen()
    screen.state = state

    assert len(state._listeners) == 0

    screen.on_pre_enter()
    assert screen._state_unsub is not None
    assert len(state._listeners) == 1

    screen.on_leave()
    assert screen._state_unsub is None
    assert len(state._listeners) == 0

    # Two cycles — no accumulation
    screen.on_pre_enter()
    screen.on_leave()
    assert len(state._listeners) == 0


# ---------------------------------------------------------------------------
# ARCH-04: No lifecycle hooks in .kv files
# ---------------------------------------------------------------------------

def test_no_lifecycle_in_kv():
    """ARCH-04: on_pre_enter, on_enter, on_leave must NOT be defined in any .kv file.

    Kivy silently skips on_pre_enter for the first kv-loaded screen (GitHub #2565).
    All lifecycle hooks must live in Python base classes only.
    """
    import glob
    import re

    # Find all .kv files in the project
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    kv_files = glob.glob(os.path.join(project_root, '**', '*.kv'), recursive=True)

    assert len(kv_files) > 0, "Expected at least one .kv file in the project"

    # Pattern: lifecycle callback definition at start of line (with optional indent)
    # Matches: "on_pre_enter:", "on_enter:", "on_leave:" as event handlers in kv
    lifecycle_pattern = re.compile(r'^\s*(on_pre_enter|on_enter|on_leave)\s*:', re.MULTILINE)

    violations = []
    for kv_path in kv_files:
        try:
            with open(kv_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except OSError:
            continue

        matches = lifecycle_pattern.findall(content)
        if matches:
            violations.append(f"{kv_path}: defines {set(matches)}")

    assert violations == [], (
        "Lifecycle hooks found in .kv files (must be in Python base classes only):\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# SetupScreenMixin: _SETUP_SCREENS frozenset
# ---------------------------------------------------------------------------

def test_setup_mixin_setup_screens_frozenset():
    """SetupScreenMixin._SETUP_SCREENS is a frozenset with required screen names."""
    from dmccodegui.screens.base import SetupScreenMixin

    screens = SetupScreenMixin._SETUP_SCREENS

    assert isinstance(screens, frozenset), "_SETUP_SCREENS must be a frozenset"
    assert "axes_setup" in screens, "'axes_setup' must be in _SETUP_SCREENS"
    assert "parameters" in screens, "'parameters' must be in _SETUP_SCREENS"
    assert "profiles" in screens, "'profiles' must be in _SETUP_SCREENS"


# ---------------------------------------------------------------------------
# _on_state_change dispatch
# ---------------------------------------------------------------------------

def test_on_state_change_dispatches_to_subclass():
    """BaseRunScreen._on_state_change is called with current state on enter and on notify.

    Verifies:
    1. on_pre_enter triggers _on_state_change with the current state immediately.
    2. A subscription callback (state.notify()) also triggers _on_state_change.
    """
    from dmccodegui.screens.base import BaseRunScreen
    from kivy.clock import Clock

    state = _MockMachineState()

    calls = []

    class _TestRunScreen(BaseRunScreen):
        def _on_state_change(self, s):
            calls.append(s)

    screen = _TestRunScreen()
    screen.state = state

    # on_pre_enter: immediate call with current state
    screen.on_pre_enter()
    assert len(calls) >= 1, "_on_state_change must be called immediately in on_pre_enter"
    assert calls[0] is state, "_on_state_change must receive the state object"

    # subscription callback triggers via Clock.schedule_once
    # We need to tick the clock to process scheduled calls
    calls.clear()
    state.notify()
    Clock.tick()  # process pending schedule_once callbacks

    assert len(calls) >= 1, "_on_state_change must be called on state.notify() after Clock.tick()"
    assert calls[0] is state

    # Cleanup
    screen.on_leave()


# ---------------------------------------------------------------------------
# Plan 18-02 regression tests: wired subclasses
# ---------------------------------------------------------------------------

def test_run_screen_inherits_base():
    """18-02: RunScreen is a subclass of BaseRunScreen."""
    from dmccodegui.screens.flat_grind.run import FlatGrindRunScreen as RunScreen
    from dmccodegui.screens.base import BaseRunScreen

    assert issubclass(RunScreen, BaseRunScreen), \
        "RunScreen must inherit from BaseRunScreen"


def test_axes_setup_inherits_base():
    """18-02: AxesSetupScreen is a subclass of BaseAxesSetupScreen."""
    from dmccodegui.screens.flat_grind.axes_setup import FlatGrindAxesSetupScreen as AxesSetupScreen
    from dmccodegui.screens.base import BaseAxesSetupScreen

    assert issubclass(AxesSetupScreen, BaseAxesSetupScreen), \
        "AxesSetupScreen must inherit from BaseAxesSetupScreen"


def test_parameters_inherits_base():
    """18-02: ParametersScreen is a subclass of BaseParametersScreen."""
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen
    from dmccodegui.screens.base import BaseParametersScreen

    assert issubclass(ParametersScreen, BaseParametersScreen), \
        "ParametersScreen must inherit from BaseParametersScreen"


def test_no_duplicate_setup_screens_frozenset():
    """18-02: _SETUP_SCREENS is NOT defined in flat_grind/axes_setup.py or flat_grind/parameters.py.

    It must exist only in SetupScreenMixin (base.py).
    """
    import ast
    import pathlib

    src_root = pathlib.Path(__file__).parent.parent / "src" / "dmccodegui" / "screens" / "flat_grind"

    for filename in ("axes_setup.py", "parameters.py"):
        src = (src_root / filename).read_text(encoding="utf-8")
        tree = ast.parse(src)

        # Walk the AST looking for an assignment with name '_SETUP_SCREENS'
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = getattr(node, 'targets', []) or [getattr(node, 'target', None)]
                for t in targets:
                    if isinstance(t, ast.Name) and t.id == "_SETUP_SCREENS":
                        raise AssertionError(
                            f"_SETUP_SCREENS is defined in flat_grind/{filename} — must only exist in base.py"
                        )


def test_run_screen_no_inline_object_properties():
    """18-02: FlatGrindRunScreen does not directly declare controller or state ObjectProperty.

    Both properties must be inherited from BaseRunScreen.
    """
    import ast
    import pathlib

    src = (pathlib.Path(__file__).parent.parent / "src" / "dmccodegui" / "screens" / "flat_grind" / "run.py").read_text(encoding="utf-8")
    tree = ast.parse(src)

    # Find the FlatGrindRunScreen class node
    run_screen_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "FlatGrindRunScreen":
            run_screen_node = node
            break

    assert run_screen_node is not None, "FlatGrindRunScreen class not found in flat_grind/run.py"

    # Look for top-level class body assignments named 'controller' or 'state'
    for item in run_screen_node.body:
        if isinstance(item, ast.Assign):
            for t in item.targets:
                if isinstance(t, ast.Name) and t.id in ("controller", "state"):
                    raise AssertionError(
                        f"FlatGrindRunScreen directly declares '{t.id}' ObjectProperty — "
                        "must be inherited from BaseRunScreen"
                    )


def test_two_enter_leave_cycles_no_leak_run():
    """18-02: RunScreen — two enter/leave cycles produce zero leaked subscriptions."""
    from unittest.mock import patch
    from dmccodegui.screens.flat_grind.run import FlatGrindRunScreen as RunScreen

    state = _MockMachineState()
    screen = RunScreen()
    screen.state = state

    for _ in range(2):
        with patch('dmccodegui.screens.base.submit'):
            with patch.object(screen, '_start_pos_poll', create=True, return_value=None):
                with patch.object(screen, '_stop_pos_poll', create=True, return_value=None):
                    try:
                        screen.on_pre_enter()
                    except Exception:
                        pass
                    try:
                        screen.on_leave()
                    except Exception:
                        pass

    assert len(state._listeners) == 0, \
        f"RunScreen leaked {len(state._listeners)} subscription(s) after two enter/leave cycles"


def test_two_enter_leave_cycles_no_leak_axes():
    """18-02: AxesSetupScreen — two enter/leave cycles produce zero leaked subscriptions."""
    from unittest.mock import patch
    from dmccodegui.screens.flat_grind.axes_setup import FlatGrindAxesSetupScreen as AxesSetupScreen

    state = _MockMachineState()
    screen = AxesSetupScreen()
    screen.state = state

    for _ in range(2):
        with patch('dmccodegui.screens.base.submit'):
            try:
                screen.on_pre_enter()
            except Exception:
                pass
            try:
                screen.on_leave()
            except Exception:
                pass

    assert len(state._listeners) == 0, \
        f"AxesSetupScreen leaked {len(state._listeners)} subscription(s) after two enter/leave cycles"


def test_two_enter_leave_cycles_no_leak_params():
    """18-02: ParametersScreen — two enter/leave cycles produce zero leaked subscriptions."""
    from unittest.mock import patch
    from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen as ParametersScreen

    state = _MockMachineState()
    screen = ParametersScreen()
    screen.state = state

    for _ in range(2):
        with patch('dmccodegui.screens.base.submit'):
            try:
                screen.on_pre_enter()
            except Exception:
                pass
            try:
                screen.on_leave()
            except Exception:
                pass

    assert len(state._listeners) == 0, \
        f"ParametersScreen leaked {len(state._listeners)} subscription(s) after two enter/leave cycles"
