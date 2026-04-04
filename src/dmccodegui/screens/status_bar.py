"""StatusBar widget — connection info, user/role, banner ticker, E-STOP."""
from __future__ import annotations

from typing import Callable, Optional

from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ListProperty


class StatusBar(BoxLayout):
    """Top status bar: connection status, user/role, banner ticker, E-STOP."""

    connection_text = StringProperty("Disconnected")
    connection_color = ListProperty([0.88, 0.06, 0.06, 1])
    user_text = StringProperty("No User")
    role_text = StringProperty("")
    banner_text = StringProperty("")

    # Cache previous values to skip redundant UI updates
    _prev_connected: bool = False
    _prev_address: str = ""
    _prev_user: str = ""
    _prev_role: str = ""

    # Callback for user area tap (set by main.py)
    _user_tap_cb: Optional[Callable[[], None]] = None

    def bind_user_tap(self, cb: Callable[[], None]) -> None:
        """Register a callback invoked when the user/role area is tapped."""
        self._user_tap_cb = cb
        # Wire KV user button if it exists
        user_btn = self.ids.get("user_btn")
        if user_btn is not None:
            user_btn.bind(on_release=lambda *_: cb())

    def on_user_tap(self) -> None:
        """Called from KV when the user/role button is pressed."""
        if self._user_tap_cb:
            self._user_tap_cb()

    def update_from_state(self, state) -> None:
        """Update properties from a MachineState instance (only when changed)."""
        connected = getattr(state, "connected", False)
        address = getattr(state, "connected_address", "")
        user = getattr(state, "current_user", "")
        role = getattr(state, "current_role", "")

        if connected != self._prev_connected or address != self._prev_address:
            self._prev_connected = connected
            self._prev_address = address
            if connected:
                self.connection_text = f"Connected: {address}" if address else "Connected"
                self.connection_color = [0.13, 0.77, 0.37, 1]  # green
            else:
                self.connection_text = "Disconnected"
                self.connection_color = [0.88, 0.06, 0.06, 1]  # red

        if user != self._prev_user or role != self._prev_role:
            self._prev_user = user
            self._prev_role = role
            self.user_text = user if user else "No User"
            self.role_text = role if role else ""
