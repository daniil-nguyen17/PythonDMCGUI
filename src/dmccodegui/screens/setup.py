from __future__ import annotations

"""
setup.py — SetupScreen

This is the first screen the operator sees. It handles:
  - Discovering available Galil controller network addresses (via controller.list_addresses())
  - Connecting / disconnecting from the controller
  - Displaying current connection status (synced to MachineState via subscription)
  - Auto-connecting on startup (reads DMC_ADDRESS env var or first discovered address)
  - Teaching / recording named axis positions ('teach_point')

KV FILE: ui/setup.kv
  - ids.addr_list  — GridLayout populated dynamically with one Button per found address
  - ids.address    — TextInput showing the currently selected address
  - connection_status — StringProperty bound to a Label in the KV to show "Connected to X"

THREADING MODEL:
  All controller I/O (connect, disconnect, list_addresses, teach_point) runs in a
  background thread via jobs.submit(). UI mutations are always posted back to the
  Kivy main thread via Clock.schedule_once().
"""

from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

from ..app_state import MachineState
from ..controller import GalilController
from ..utils import jobs


class SetupScreen(Screen):
    # Injected by main.py after the ScreenManager is built
    controller: GalilController = ObjectProperty(None)  # type: ignore
    state: MachineState = ObjectProperty(None)          # type: ignore

    address: str = StringProperty("")          # Currently selected controller address
    addresses: list = []                       # List of (addr, description) tuples from discovery
    _autoconnect: bool = False                 # True on first launch — triggers auto-connect once
    connection_status: str = StringProperty("Not connected")  # Shown in KV Label
    _unsubscribe = None                        # Callable returned by state.subscribe() — call to unsubscribe
    _on_connect_cb = None                      # Callback invoked after successful connection

    def on_kv_post(self, *_):
        """
        Called by Kivy once the KV rule for this screen has been applied and
        all child widgets are instantiated (ids are accessible).

        What this does:
          1. Triggers address discovery with auto-connect enabled
          2. Checks if a controller is already connected (e.g. from a previous session)
             and syncs that state immediately
          3. Subscribes to MachineState changes so the connection_status label
             updates automatically whenever state.connected changes elsewhere in the app

        Do NOT move controller I/O here — it runs on the main thread; use refresh_addresses().
        """
        # Enable auto-connect for the first discovery pass
        self._autoconnect = True
        self.refresh_addresses()

        # Reflect pre-existing connection immediately (e.g. controller was already open)
        if self.controller and self.controller.verify_connection():
            self.state.set_connected(True)
            if not self.state.connected_address and self.address:
                self.state.connected_address = self.address

        # Subscribe to state changes so the status label stays in sync
        try:
            if hasattr(self.state, 'subscribe') and self._unsubscribe is None:
                self._unsubscribe = self.state.subscribe(
                    lambda *_: Clock.schedule_once(lambda __: self._sync_connection_status())
                )
        except Exception:
            pass

        self._sync_connection_status()

    def on_pre_enter(self, *_):
        """
        Called by Kivy each time the operator navigates back to this screen.

        Refreshes the address list and re-syncs the connection status label.
        This catches the case where the controller was disconnected from another screen.
        """
        self.refresh_addresses()
        self._sync_connection_status()

    def on_leave(self, *_):
        """
        Called by Kivy when navigating away from this screen.

        Unsubscribes from MachineState to avoid stale callbacks firing while this
        screen is not visible. The subscription is re-established in on_kv_post or
        on_pre_enter via refresh / initial_refresh.
        """
        if self._unsubscribe:
            try:
                self._unsubscribe()
            except Exception:
                pass
            self._unsubscribe = None

    def start(self) -> None:
        """
        Legacy alias kept for API parity with older code that called 'start()'.
        Kicks off a fresh address discovery pass.
        """
        self.refresh_addresses()

    def connect(self) -> None:
        """
        Attempt to connect to the controller at the address currently in self.address.

        Flow (all I/O is off the main thread):
          1. Reads self.address (set via select_address() or the TextInput)
          2. Calls controller.connect(addr) in a background thread
          3. On success: sets state.connected = True, records state.connected_address,
             shows a banner, and updates the status label
          4. On failure: shows an alert banner

        To change what happens on successful connection (e.g. navigate to another screen),
        add logic inside the on_ui() closure below.
        """
        addr = self.address.strip()
        if not addr:
            Clock.schedule_once(lambda *_: self._alert("No address provided"))
            return

        def do_connect() -> None:
            ok = self.controller.connect(addr)

            def on_ui() -> None:
                self.state.set_connected(ok)
                if ok:
                    self.state.connected_address = addr
                    self._alert("Connection established")
                    if self._on_connect_cb:
                        self._on_connect_cb()
                else:
                    self._alert("Connect failed")
                self._sync_connection_status()

            Clock.schedule_once(lambda *_: on_ui())

        jobs.submit(do_connect)

    def disconnect(self) -> None:
        """
        Disconnect from the currently connected controller.

        Runs disconnect() in a background thread, then on the main thread:
          - Sets state.connected = False
          - Shows 'Disconnected' banner
          - Refreshes the address list
          - Syncs the status label
        """
        def do_disc() -> None:
            self.controller.disconnect()
            Clock.schedule_once(lambda *_: (self.state.set_connected(False), self._alert("Disconnected")))
            Clock.schedule_once(lambda *_: self.refresh_addresses())
            Clock.schedule_once(lambda *_: self._sync_connection_status())

        jobs.submit(do_disc)

    def teach_point(self, name: str) -> None:
        """
        Record the current axis positions as a named point and store in MachineState.

        Calls controller.teach_point(name) in the background, then reads back the
        axis positions via read_status() and stores them in state.taught_points[name].

        Parameters
        ----------
        name : str — arbitrary label for the point (e.g. 'Start', 'Rest')

        The taught position is available to other screens as:
            self.state.taught_points[name]["pos"]  →  {"A": x, "B": y, ...}

        To trigger a notification to subscribed screens after teaching, state.notify()
        is called automatically inside on_ui().
        """
        if not self.controller or not self.controller.is_connected():
            Clock.schedule_once(lambda *_: self._alert("No controller connected"))
            return

        def do_teach() -> None:
            try:
                self.controller.teach_point(name)
                st  = self.controller.read_status()
                pos = st.get("pos", {})

                def on_ui() -> None:
                    self.state.taught_points[name] = {"pos": pos}
                    self.state.notify()

                Clock.schedule_once(lambda *_: on_ui())
            except Exception as e:
                msg = f"Teach error: {e}"
                Clock.schedule_once(lambda *_: self._alert(msg))

        jobs.submit(do_teach)

    def refresh_addresses(self) -> None:
        """
        Discover available controller addresses and populate the addr_list GridLayout.

        Runs controller.list_addresses() in a background thread. On completion,
        populates ids.addr_list with one Button per found address. Clicking a button
        calls select_address() to set self.address.

        Auto-connect logic (runs once per session if self._autoconnect is True):
          Priority: DMC_ADDRESS env var → ids.address TextInput → first discovered address
          After auto-connect fires, self._autoconnect is set to False so it doesn't
          repeat on subsequent calls to refresh_addresses().

        To change the button style for discovered addresses: edit the Button creation
        inside on_ui() below.
        """
        def do_list() -> None:
            items = self.controller.list_addresses()

            def on_ui() -> None:
                self.addresses = [(k, v) for k, v in items.items()]
                grid = self.ids.get('addr_list')
                if not grid:
                    return

                # Repopulate the address grid
                grid.clear_widgets()
                from kivy.uix.button import Button
                for addr, desc in self.addresses:
                    label = desc.split('Rev')[0]  # Trim firmware revision info from display
                    btn = Button(text=f"{label} | {addr}", size_hint_y=None, height='32dp')
                    btn.bind(on_release=lambda *_, a=addr: self.select_address(a))
                    grid.add_widget(btn)

                # One-time auto-connect on startup
                if self._autoconnect and not (self.state and self.state.connected):
                    import os
                    candidate = (
                        os.environ.get('DMC_ADDRESS')
                        or (self.ids.get('address').text if self.ids.get('address') else '')
                        or (self.addresses[0][0] if self.addresses else '')
                    )
                    if candidate:
                        self._autoconnect = False
                        self.address = candidate
                        if self.ids.get('address'):
                            self.ids['address'].text = candidate
                        self.connect()
                    else:
                        self._autoconnect = False

            Clock.schedule_once(lambda *_: on_ui())

        jobs.submit(do_list)

    def initial_refresh(self) -> None:
        """
        Public entry point called by main.py after build() to trigger the first
        address discovery and auto-connect attempt.

        Sets _autoconnect = True then calls refresh_addresses(). This ensures that
        if the screen was already built but not yet visible, auto-connect still fires.
        """
        self._autoconnect = True
        self.refresh_addresses()

    def _sync_connection_status(self) -> None:
        """
        Update the connection_status StringProperty from the current MachineState.

        This property is bound to a Label in setup.kv via:
            Label:
                text: root.connection_status

        Called from:
          - on_kv_post (initial)
          - on_pre_enter (on return to screen)
          - State subscription callback (on any state change)
          - After connect() / disconnect() complete
        """
        try:
            if self.state and self.state.connected:
                if getattr(self.state, 'connected_address', ''):
                    self.connection_status = f"Connected to {self.state.connected_address}"
                else:
                    self.connection_status = "Connected"
            else:
                self.connection_status = "Not connected"
        except Exception:
            self.connection_status = "Not connected"

    def set_on_connect_callback(self, cb) -> None:
        """Register a callback invoked after a successful connection."""
        self._on_connect_cb = cb

    def select_address(self, addr: str) -> None:
        """
        Set the selected address from the discovery list into self.address and the TextInput.

        Called when the operator clicks one of the address buttons in addr_list.
        Does NOT automatically trigger a connection — operator must press 'Connect'.

        Parameters
        ----------
        addr : str — the IP or serial address to select (e.g. '192.168.0.100')
        """
        self.address = addr
        if self.ids.get('address'):
            self.ids['address'].text = addr

    def _alert(self, message: str) -> None:
        """
        Push a message to the app-wide banner ticker via DMCApp._log_message().

        Falls back to state.log() if the app is not running (e.g. during unit tests).
        All messages are also stored in state.log_history for review.

        Parameters
        ----------
        message : str — text to show in the banner
        """
        try:
            from kivy.app import App
            app = App.get_running_app()
            if app and hasattr(app, "_log_message"):
                getattr(app, "_log_message")(message)
                return
        except Exception:
            pass
        if self.state:
            self.state.log(message)
