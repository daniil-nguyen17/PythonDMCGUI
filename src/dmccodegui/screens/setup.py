from __future__ import annotations

from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

from ..app_state import MachineState
from ..controller import GalilController
from ..utils import jobs


class SetupScreen(Screen):
    controller: GalilController = ObjectProperty(None)  # type: ignore
    state: MachineState = ObjectProperty(None)  # type: ignore
    address: str = StringProperty("")
    addresses: list = []
    _autoconnect: bool = False

    def on_kv_post(self, *_):
        # initial discovery similar to prior populateControllers in on_kv_post/start
        self._autoconnect = True
        self.refresh_addresses()
        # reflect current connection immediately
        if self.controller and self.controller.verify_connection():
            self.state.set_connected(True)
            # Try to learn/display current address if known
            if not self.state.connected_address and self.address:
                self.state.connected_address = self.address

    def on_pre_enter(self, *_):
        # refresh when returning to this page
        self.refresh_addresses()

    def start(self) -> None:
        # parity with old API: kick off discovery
        self.refresh_addresses()

    def connect(self) -> None:
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
                    # Mirror old title update and banner
                    self._alert(f"Connected to: {addr}")
                else:
                    self._alert("Connect failed")
            Clock.schedule_once(lambda *_: on_ui())

        jobs.submit(do_connect)

    def disconnect(self) -> None:
        def do_disc() -> None:
            self.controller.disconnect()
            Clock.schedule_once(lambda *_: (self.state.set_connected(False), self._alert("Disconnected")))
            Clock.schedule_once(lambda *_: self.refresh_addresses())
        jobs.submit(do_disc)

    def teach_point(self, name: str) -> None:
        if not self.controller or not self.controller.is_connected():
            Clock.schedule_once(lambda *_: self._alert("No controller connected"))
            return
        def do_teach() -> None:
            try:
                self.controller.teach_point(name)
                # Pull positions and store
                st = self.controller.read_status()
                pos = st.get("pos", {})
                def on_ui() -> None:
                    self.state.taught_points[name] = {"pos": pos}
                    self.state.notify()
                Clock.schedule_once(lambda *_: on_ui())
            except Exception as e:
                msg = f"Teach error: {e}"
                Clock.schedule_once(lambda *_: self._alert(msg))

        jobs.submit(do_teach)

    # Discovery
    def refresh_addresses(self) -> None:
        def do_list() -> None:
            items = self.controller.list_addresses()
            def on_ui() -> None:
                self.addresses = [(k, v) for k, v in items.items()]
                grid = self.ids.get('addr_list')
                if not grid:
                    return
                grid.clear_widgets()
                from kivy.uix.button import Button
                for addr, desc in self.addresses:
                    label = desc.split('Rev')[0]
                    btn = Button(text=f"{label} | {addr}", size_hint_y=None, height='32dp')
                    btn.bind(on_release=lambda *_ , a=addr: self.select_address(a))
                    grid.add_widget(btn)
                # Attempt auto-connect once on startup if requested
                if self._autoconnect and not (self.state and self.state.connected):
                    import os
                    candidate = os.environ.get('DMC_ADDRESS') or (self.ids.get('address').text if self.ids.get('address') else '') or (self.addresses[0][0] if self.addresses else '')
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
        """Public helper to trigger refresh and auto-connect from app on boot."""
        self._autoconnect = True
        self.refresh_addresses()

    def select_address(self, addr: str) -> None:
        self.address = addr
        if self.ids.get('address'):
            self.ids['address'].text = addr

    def _alert(self, message: str) -> None:
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

