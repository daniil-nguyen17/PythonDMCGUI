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

