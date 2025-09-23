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

    def on_kv_post(self, *_):
        # initial discovery similar to prior populateControllers in on_kv_post/start
        self.refresh_addresses()

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
                    self.state.log(f"Connected to: {addr}")
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
            Clock.schedule_once(lambda *_: on_ui())
        jobs.submit(do_list)

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

