"""StatusBar widget — connection info, user/role, banner ticker, E-STOP."""
from __future__ import annotations

from typing import Callable, Optional

from kivy.uix.boxlayout import BoxLayout
from kivy.properties import BooleanProperty, StringProperty, ListProperty


class StatusBar(BoxLayout):
    """Top status bar: connection status, user/role, banner ticker, E-STOP."""

    connection_text = StringProperty("Disconnected")
    connection_color = ListProperty([0.88, 0.06, 0.06, 1])
    user_text = StringProperty("No User")
    role_text = StringProperty("")
    banner_text = StringProperty("")
    machine_type_text = StringProperty("No Machine Type")
    recover_enabled = BooleanProperty(False)

    # State label: shows IDLE / GRINDING / SETUP / HOMING / OFFLINE / E-STOP
    state_text = StringProperty("OFFLINE")
    state_color = ListProperty([0.55, 0.55, 0.55, 1])  # default gray

    # Map dmc_state int -> (label, color) for connected states
    _STATE_MAP: dict = {
        1: ("IDLE",     [1.0,  0.6,  0.0,  1]),  # orange
        2: ("GRINDING", [0.13, 0.77, 0.37, 1]),  # green
        3: ("SETUP",    [0.9,  0.2,  0.2,  1]),  # red
        4: ("HOMING",   [1.0,  0.6,  0.0,  1]),  # orange
    }

    # Cache previous values to skip redundant UI updates
    _prev_connected: bool = False
    _prev_address: str = ""
    _prev_user: str = ""
    _prev_role: str = ""
    _prev_machine_type: str = ""

    # Callback for user area tap (set by main.py)
    _user_tap_cb: Optional[Callable[[], None]] = None

    # Callback for machine type area tap (set by main.py)
    _machine_type_tap_cb: Optional[Callable[[], None]] = None

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

    def bind_machine_type_tap(self, cb: Callable[[], None]) -> None:
        """Register a callback invoked when the machine type area is tapped."""
        self._machine_type_tap_cb = cb
        # Wire KV machine type button if it exists
        machine_type_btn = self.ids.get("machine_type_btn")
        if machine_type_btn is not None:
            machine_type_btn.bind(on_release=lambda *_: cb())

    def on_machine_type_tap(self) -> None:
        """Called from KV when the machine type button is pressed."""
        if self._machine_type_tap_cb:
            self._machine_type_tap_cb()

    def update_from_state(self, state) -> None:
        """Update properties from a MachineState instance (only when changed)."""
        connected = getattr(state, "connected", False)
        address = getattr(state, "connected_address", "")
        user = getattr(state, "current_user", "")
        role = getattr(state, "current_role", "")
        machine_type = getattr(state, "machine_type", "")
        program_running = getattr(state, "program_running", False)
        dmc_state = getattr(state, "dmc_state", 0)

        # Capture connected-changed flag BEFORE _prev_connected is updated below
        connected_changed = connected != self._prev_connected

        # RECOVER enabled when connected AND program is NOT running
        self.recover_enabled = connected and not program_running

        if connected_changed or address != self._prev_address:
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

        if machine_type != self._prev_machine_type:
            self._prev_machine_type = machine_type
            self.machine_type_text = machine_type if machine_type else "No Machine Type"

        # State label: always recompute (Kivy properties handle their own
        # change detection, so redundant assignments are essentially no-ops).
        if not connected:
            if not program_running:
                label, color = "E-STOP", [0.9, 0.2, 0.2, 1]
            else:
                label, color = "OFFLINE", [0.55, 0.55, 0.55, 1]
        else:
            label, color = self._STATE_MAP.get(
                dmc_state, ("OFFLINE", [0.55, 0.55, 0.55, 1])
            )
        self.state_text = label
        self.state_color = color
