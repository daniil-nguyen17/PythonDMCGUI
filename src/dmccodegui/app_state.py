from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from .hmi.dmc_vars import STATE_GRINDING

ChangeListener = Callable[["MachineState"], None]


@dataclass
class MachineState:
    """Observable application state shared across all screens.

    Implements a minimal observer pattern: call subscribe(fn) to register a
    listener and notify() to push the current state to all listeners.

    State authority notes:
    - dmc_state: authoritative from DR streaming (ZAA); never derived by Python.
    - cycle_running: computed property — do not set directly.
    - Position fields (pos): updated by DataRecordListener._apply_to_state().
    - Auth fields: updated exclusively via set_auth() / lock_setup().
    """
    connected: bool = False
    connected_address: str = ""
    running: bool = False
    pos: Dict[str, float] = field(default_factory=lambda: {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0})
    interlocks_ok: bool = False
    speed: float = 0.0
    messages: List[str] = field(default_factory=list)
    arrays: Dict[str, List[float]] = field(default_factory=dict)
    taught_points: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Machine type (Phase 6) — mirrors machine_config.get_active_type()
    machine_type: str = ""

    # Auth fields
    current_user: str = ""
    current_role: str = ""  # values: "operator" | "setup" | "admin" | ""
    setup_unlocked: bool = False

    # Cycle status fields (Phase 2)
    # NOTE: cycle_running is a @property derived from dmc_state — not a stored field.
    cycle_tooth: int = 0
    cycle_pass: int = 0
    cycle_depth: float = 0.0
    cycle_elapsed_s: float = 0.0
    cycle_completion_pct: float = 0.0

    # DMC controller state field (Phase 9)
    dmc_state: int = 0  # hmiState from controller; 0=uninitialized, 1=IDLE, 2=GRINDING, 3=SETUP, 4=HOMING

    # Knife count fields (Phase 10)
    session_knife_count: int = 0  # Increments each grind; resets on new stone session
    stone_knife_count: int = 0    # Increments each grind; resets only when stone changes

    # E-STOP safety field (Phase 11)
    # True when _XQ >= 0 (DMC program thread active on controller)
    program_running: bool = True

    # Stone position — streamed via ZAD in the data record
    start_pt_c: int = 0

    # Cached controller parameters — bulk-loaded on connect, refreshed per-screen
    cached_params: Dict[str, float] = field(default_factory=dict, repr=False)

    _listeners: List[ChangeListener] = field(default_factory=list, repr=False)

    @property
    def cycle_running(self) -> bool:
        """Derived from dmc_state — True only when the controller reports GRINDING (2).

        State authority is the controller's hmiState variable. Python does not store
        cycle_running independently; it is computed from the polled dmc_state value.
        Read-only — assignment raises AttributeError.
        """
        return self.dmc_state == STATE_GRINDING

    def subscribe(self, fn: ChangeListener) -> Callable[[], None]:
        """Register *fn* as a state change listener.

        Args:
            fn: Callable(state) invoked on every notify() call.

        Returns:
            An unsubscribe callable that removes *fn* from the listener list.
        """
        self._listeners.append(fn)

        def unsubscribe() -> None:
            try:
                self._listeners.remove(fn)
            except ValueError:
                pass

        return unsubscribe

    def notify(self) -> None:
        """Push current state to all registered listeners. Exceptions are suppressed."""
        for fn in list(self._listeners):
            try:
                fn(self)
            except Exception:
                # ignore listener failures
                pass

    # Convenience updaters
    def set_connected(self, value: bool) -> None:
        """Set connected state and notify all listeners.

        Args:
            value: True when the HMI has an active TCP handle to the controller.
        """
        self.connected = value
        self.notify()

    def update_status(self, pos: Dict[str, float], interlocks_ok: bool, speed: float) -> None:
        """Bulk-update position, interlocks, and speed, then notify.

        Args:
            pos: Dict of axis letter -> position in counts (e.g. {"A": 1234.0}).
            interlocks_ok: True when all controller hardware interlocks are satisfied.
            speed: Current motion speed reading (axis A, in counts/sec).
        """
        self.pos.update(pos)
        self.interlocks_ok = interlocks_ok
        self.speed = speed
        self.notify()

    def log(self, message: str) -> None:
        """Append *message* to the message log (capped at 200 entries) and notify.

        Args:
            message: Human-readable log line from the controller or HMI.
        """
        self.messages.append(message)
        if len(self.messages) > 200:
            self.messages[:] = self.messages[-200:]
        self.notify()

    def clear_messages(self) -> None:
        """Clear all log messages and notify listeners."""
        self.messages.clear()
        self.notify()

    # Auth updaters
    def set_auth(self, user: str, role: str) -> None:
        """Set authenticated user and role, updating setup lock state."""
        self.current_user = user
        self.current_role = role
        self.setup_unlocked = role in ("setup", "admin")
        self.notify()

    def lock_setup(self) -> None:
        """Clear setup access, keeping user/role intact."""
        self.setup_unlocked = False
        self.notify()

