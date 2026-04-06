from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List


ChangeListener = Callable[["MachineState"], None]


@dataclass
class MachineState:
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
    cycle_running: bool = False
    cycle_tooth: int = 0
    cycle_pass: int = 0
    cycle_depth: float = 0.0
    cycle_elapsed_s: float = 0.0
    cycle_completion_pct: float = 0.0

    # DMC controller state field (Phase 9)
    dmc_state: int = 0  # hmiState from controller; 0=uninitialized, 1=IDLE, 2=GRINDING, 3=SETUP, 4=HOMING

    _listeners: List[ChangeListener] = field(default_factory=list, repr=False)

    def subscribe(self, fn: ChangeListener) -> Callable[[], None]:
        self._listeners.append(fn)

        def unsubscribe() -> None:
            try:
                self._listeners.remove(fn)
            except ValueError:
                pass

        return unsubscribe

    def notify(self) -> None:
        for fn in list(self._listeners):
            try:
                fn(self)
            except Exception:
                # ignore listener failures
                pass

    # Convenience updaters
    def set_connected(self, value: bool) -> None:
        self.connected = value
        self.notify()

    def update_status(self, pos: Dict[str, float], interlocks_ok: bool, speed: float) -> None:
        self.pos.update(pos)
        self.interlocks_ok = interlocks_ok
        self.speed = speed
        self.notify()

    def log(self, message: str) -> None:
        self.messages.append(message)
        if len(self.messages) > 200:
            self.messages[:] = self.messages[-200:]
        self.notify()

    def clear_messages(self) -> None:
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

