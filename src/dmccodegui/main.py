from __future__ import annotations

import os
from functools import partial
from typing import cast

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.factory import Factory

try:
    from .app_state import MachineState
    from .controller import GalilController
    from .utils import jobs
    from . import screens as _screens  # noqa: F401 - ensure screen classes are registered with Factory
except Exception:  # Allows running as a script: python src/dmccodegui/main.py
    from dmccodegui.app_state import MachineState
    from dmccodegui.controller import GalilController
    from dmccodegui.utils import jobs
    import dmccodegui.screens as _screens  # type: ignore  # noqa: F401


KV_FILES = [
    "ui/theme.kv",
    "ui/arrays.kv",  # base widget for Edge screens
    "ui/edges.kv",   # declares EdgePointB/EdgePointC
    "ui/rest.kv",
    "ui/start.kv",
    "ui/setup.kv",
    "ui/settings.kv",
    "ui/base.kv",    # load last so classes are registered first
]


class DMCApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state = MachineState()
        self.controller = GalilController()
        self._poll_cancel = None

    def build(self):
        for kv in KV_FILES:
            Builder.load_file(os.path.join(os.path.dirname(__file__), kv))

        root = Factory.RootLayout()

        # Inject controller/state into screens
        sm = root.ids.sm
        for screen in sm.screens:
            if hasattr(screen, 'controller') and hasattr(screen, 'state'):
                screen.controller = self.controller
                screen.state = self.state

        # Start periodic poll
        self._poll_cancel = jobs.schedule(0.1, self._poll_controller)
        # Hook controller logger to push messages into state and show banner
        self.controller.set_logger(lambda msg: Clock.schedule_once(lambda *_: self._log_message(msg)))
        return root

    def _poll_controller(self) -> None:
        if not self.controller.is_connected():
            return
        try:
            st = self.controller.read_status()
            pos = cast(dict, st.get("pos", {}))
            speed = cast(float, st.get("speeds", 0.0))
            def on_ui():
                self.state.update_status(pos=pos, interlocks_ok=True, speed=speed)
            Clock.schedule_once(lambda *_: on_ui())
        except Exception as e:
            Clock.schedule_once(lambda *_: self.state.log(f"poll error: {e}"))

    def on_stop(self):
        if self._poll_cancel:
            self._poll_cancel()
        jobs.shutdown()
        self.controller.disconnect()

    # Global actions
    def disconnect_and_refresh(self) -> None:
        def do_disc():
            self.controller.disconnect()
            def on_ui():
                self.state.set_connected(False)
                # Navigate to setup and refresh addresses
                try:
                    self.root.ids.sm.current = 'setup'
                    setup = next((s for s in self.root.ids.sm.screens if getattr(s, 'name', '') == 'setup'), None)
                    if setup and hasattr(setup, 'refresh_addresses'):
                        setup.refresh_addresses()
                except Exception:
                    pass
            Clock.schedule_once(lambda *_: on_ui())
        jobs.submit(do_disc)

    def e_stop(self) -> None:
        def do_estop():
            try:
                if self.controller.is_connected():
                    self.controller.cmd('AB')
            finally:
                self.controller.disconnect()
            def on_ui():
                self.state.set_connected(False)
                try:
                    self.root.ids.sm.current = 'setup'
                except Exception:
                    pass
            Clock.schedule_once(lambda *_: on_ui())
        jobs.submit(do_estop)

    # Actions helpers: switch Arrays screen with presets
    def open_rest(self) -> None:
        try:
            self.root.ids.sm.current = 'rest'
        except Exception:
            pass

    def open_start(self) -> None:
        try:
            self.root.ids.sm.current = 'start'
        except Exception:
            pass

    # Messaging helpers
    def _log_message(self, message: str) -> None:
        self.state.log(message)
        try:
            from kivy.uix.label import Label
            from kivy.uix.popup import Popup
            pop = Popup(title='Controller Message', content=Label(text=message), size_hint=(0.5, 0.25))
            pop.open()
            Clock.schedule_once(lambda *_: pop.dismiss(), 2.5)
        except Exception:
            pass


def main() -> None:
    DMCApp().run()


if __name__ == "__main__":
    main()

