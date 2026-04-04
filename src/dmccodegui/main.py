from __future__ import annotations

import os
os.environ["KIVY_DPI_AWARE"] = "1"
os.environ["KIVY_METRICS_DENSITY"] = "1"
os.environ["KIVY_MOUSE"] = "mouse,multitouch_on_demand"
from typing import cast
from kivy.config import Config

Config.set('graphics', 'fullscreen', '0')   # disable fullscreen
Config.set('graphics', 'maximized', '0')    # start not maximized
Config.set('graphics', 'borderless', '0')   # keep window borders
Config.set('graphics', 'resizable', '1')    # allow window resizing
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')  # ensure mouse input

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.properties import StringProperty
from kivy.core.window import Window

Window.size = (1920, 1080)                   # pick a window size you want

IDLE_TIMEOUT = 30 * 60  # 30 minutes in seconds

try:
    from .app_state import MachineState
    from .auth.auth_manager import AuthManager
    from .controller import GalilController
    from .utils import jobs
    from . import screens as _screens  # noqa: F401 - ensure screen classes are registered with Factory
    from .screens.pin_overlay import PINOverlay
except Exception:  # Allows running as a script: python src/dmccodegui/main.py
    from dmccodegui.app_state import MachineState
    from dmccodegui.auth.auth_manager import AuthManager
    from dmccodegui.controller import GalilController
    from dmccodegui.utils import jobs
    import dmccodegui.screens as _screens  # type: ignore  # noqa: F401
    from dmccodegui.screens.pin_overlay import PINOverlay


KV_FILES = [
    "ui/theme.kv",         # base styles - always first
    "ui/pin_overlay.kv",   # PINOverlay ModalView
    "ui/status_bar.kv",    # StatusBar widget
    "ui/tab_bar.kv",       # TabBar widget
    "ui/setup.kv",         # SetupScreen (connection)
    "ui/run.kv",           # RunScreen placeholder
    "ui/axes_setup.kv",    # AxesSetupScreen placeholder
    "ui/parameters.kv",    # ParametersScreen placeholder
    "ui/diagnostics.kv",   # DiagnosticsScreen placeholder
    "ui/base.kv",          # RootLayout - always last
]


class DMCApp(App):
    # Top-of-app banner text for alerts/logs
    banner_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state = MachineState()
        self.controller = GalilController()
        self._poll_cancel = None
        self._idle_event = None
        # AuthManager — path resolved at __init__ time so tests can override
        users_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "auth", "users.json"
        )
        self.auth_manager = AuthManager(users_path)

    def build(self):
        if Window:
            Window.bind(on_cursor_enter=lambda *args: Window.show())

        from kivy.resources import resource_add_path
        resource_add_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'images'))

        for kv in KV_FILES:
            Builder.load_file(os.path.join(os.path.dirname(__file__), kv))

        root = Factory.RootLayout()

        # Inject controller/state into screens
        sm = root.ids.sm
        for screen in sm.screens:
            if hasattr(screen, 'controller') and hasattr(screen, 'state'):
                screen.controller = self.controller
                screen.state = self.state

        # Wire TabBar -> ScreenManager
        tab_bar = root.ids.tab_bar
        tab_bar.bind(current_tab=lambda inst, val: setattr(sm, 'current', val))

        # Wire StatusBar banner to app.banner_text
        status_bar = root.ids.status_bar
        self.bind(banner_text=status_bar.setter('banner_text'))

        # Subscribe StatusBar to state changes
        self.state.subscribe(lambda s: Clock.schedule_once(lambda *_: status_bar.update_from_state(s)))

        # Wire user area in StatusBar to open switch-user overlay
        status_bar.bind_user_tap(lambda: self._show_pin_overlay("switch"))

        # Wire restricted tab callback
        tab_bar.set_restricted_callback(lambda: self._show_pin_overlay("unlock"))

        # Create PIN overlay instance
        self._pin_overlay = PINOverlay()

        # Default TabBar to operator (no auth yet) — PIN overlay will set real role
        tab_bar.set_role("operator", "run")

        # Set initial screen to setup (connection screen)
        sm.current = 'setup'

        # Start periodic poll (disabled for now to prevent spam)
        # self._poll_cancel = jobs.schedule(1.0, self._poll_controller)

        # Hook controller logger to push messages into state and show banner
        self.controller.set_logger(lambda msg: Clock.schedule_once(lambda *_: self._log_message(msg)))

        # Detect pre-existing connection (e.g., controller opened by previous run)
        if self.controller.verify_connection():
            self.state.set_connected(True)
            # Connection present — show PIN overlay immediately
            Clock.schedule_once(lambda *_: self._show_pin_on_start(), 0)
        else:
            # Optional auto-connect via env var
            addr = os.environ.get('DMC_ADDRESS', '').strip()
            if addr:
                def do_auto():
                    ok = self.controller.connect(addr)
                    def on_ui():
                        self.state.set_connected(ok)
                        if ok:
                            self.state.connected_address = addr
                            self._log_message(f"Connected to: {addr}")
                            # Auto-connect succeeded — show PIN overlay
                            Clock.schedule_once(lambda *_: self._show_pin_on_start(), 0)
                        else:
                            self._log_message("Auto-connect failed")
                    Clock.schedule_once(lambda *_: on_ui())
                jobs.submit(do_auto)

        # Trigger the setup screen to refresh and (optionally) auto-connect
        try:
            setup = next((s for s in root.ids.sm.screens if getattr(s, 'name', '') == 'setup'), None)
            if setup and hasattr(setup, 'initial_refresh'):
                setup.initial_refresh()
        except Exception:
            pass

        # Wire setup screen: after successful connection, show PIN overlay
        try:
            setup = next((s for s in root.ids.sm.screens if getattr(s, 'name', '') == 'setup'), None)
            if setup and hasattr(setup, 'set_on_connect_callback'):
                setup.set_on_connect_callback(self._on_connect_from_setup)
        except Exception:
            pass

        # Idle auto-lock timer — fires after 30 minutes with no touch input
        Window.bind(on_touch_down=self._reset_idle_timer)
        self._reset_idle_timer()

        return root

    # ------------------------------------------------------------------
    # PIN overlay management
    # ------------------------------------------------------------------

    def _show_pin_on_start(self) -> None:
        """Show the login PIN overlay if connected."""
        if self.state.connected:
            self._show_pin_overlay("login")

    def _show_pin_overlay(self, mode: str = "login") -> None:
        """Open the PIN overlay in the specified mode."""
        if mode == "login":
            self._pin_overlay.open_for_login(self.auth_manager, self._on_login_success)
        elif mode == "unlock":
            self._pin_overlay.open_for_unlock(self.auth_manager, self._on_unlock_success)
        elif mode == "switch":
            self._pin_overlay.open_for_switch(self.auth_manager, self._on_login_success)

    def _on_login_success(self, username: str, role: str) -> None:
        """Callback on successful PIN entry (login or switch)."""
        self.state.set_auth(username, role)
        try:
            tab_bar = self.root.ids.tab_bar
            sm = self.root.ids.sm
            tab_bar.set_role(role, "run")
            sm.current = "run"
        except Exception:
            pass

    def _on_unlock_success(self, username: str, role: str) -> None:
        """Callback on successful Setup/Admin PIN for role elevation."""
        if role not in ("setup", "admin"):
            return
        self.state.set_auth(username, role)
        try:
            tab_bar = self.root.ids.tab_bar
            tab_bar.set_role(role, tab_bar.current_tab)
        except Exception:
            pass

    def _on_connect_from_setup(self) -> None:
        """Called when setup screen successfully connects. Show PIN overlay."""
        Clock.schedule_once(lambda *_: self._show_pin_on_start(), 0)

    # ------------------------------------------------------------------
    # Idle auto-lock
    # ------------------------------------------------------------------

    def _reset_idle_timer(self, *args) -> None:
        """Reset the 30-minute idle auto-lock timer on any touch input."""
        if self._idle_event:
            self._idle_event.cancel()
        self._idle_event = Clock.schedule_once(self._on_idle_timeout, IDLE_TIMEOUT)

    def _on_idle_timeout(self, dt) -> None:
        """Auto-lock: drop Setup role back to Operator view after 30 min idle."""
        if self.state.setup_unlocked:
            self.state.lock_setup()
            try:
                tab_bar = self.root.ids.tab_bar
                sm = self.root.ids.sm
                if sm.current in ("axes_setup", "parameters", "diagnostics"):
                    sm.current = "run"
                # Reset tab bar to operator view
                tab_bar._current_role = ""  # force rebuild
                tab_bar.set_role("operator", "run")
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Controller poll
    # ------------------------------------------------------------------

    def _poll_controller(self) -> None:
        if not self.controller.is_connected():
            return
        try:
            st = self.controller.read_status()
            pos = cast(dict, st.get("pos", {}))
            speed = cast(float, st.get("speeds", 0.0))
            Clock.schedule_once(lambda *_: self.state.update_status(pos=pos, interlocks_ok=True, speed=speed))
        except Exception as e:
            msg = f"poll error: {e}"             # capture here
            Clock.schedule_once(lambda *_: self.state.log(msg))

    def on_stop(self):
        if self._poll_cancel:
            self._poll_cancel()
        if self._idle_event:
            self._idle_event.cancel()
        jobs.shutdown()
        self.controller.disconnect()

    # ------------------------------------------------------------------
    # Global actions
    # ------------------------------------------------------------------

    def disconnect_and_refresh(self) -> None:
        def do_disc():
            self.controller.disconnect()
            def on_ui():
                self.state.set_connected(False)
                # Reset auth state on disconnect
                self.state.set_auth("", "")
                # Navigate to setup and refresh addresses
                try:
                    sm = self.root.ids.sm
                    tab_bar = self.root.ids.tab_bar
                    sm.current = 'setup'
                    tab_bar._current_role = ""  # force rebuild on next set_role
                    tab_bar.set_role("operator", "run")
                    setup = next((s for s in sm.screens if getattr(s, 'name', '') == 'setup'), None)
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

    # ------------------------------------------------------------------
    # Messaging helpers
    # ------------------------------------------------------------------

    def _log_message(self, message: str) -> None:
        # Push to ticker only; avoid spammy popups
        # Filter duplicate consecutive messages
        if message and message != self.banner_text:
            self.banner_text = message
            self.state.log(message)


def main() -> None:
    DMCApp().run()


if __name__ == "__main__":
    main()
