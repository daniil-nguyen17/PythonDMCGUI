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
