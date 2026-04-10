from __future__ import annotations

import os
os.environ["KIVY_DPI_AWARE"] = "1"
os.environ["KIVY_METRICS_DENSITY"] = "1"
os.environ["KIVY_MOUSE"] = "mouse,multitouch_on_demand"
from typing import cast
from kivy.config import Config

Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'maximized', '1')    # start maximized (fullscreen)
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

# Register Noto Sans as the default font (Vietnamese + full Latin support)
from kivy.core.text import LabelBase

_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'assets', 'fonts', 'Noto_Sans', 'static')
LabelBase.register(
    name='Roboto',
    fn_regular=os.path.join(_FONT_DIR, 'NotoSans-Regular.ttf'),
    fn_bold=os.path.join(_FONT_DIR, 'NotoSans-Bold.ttf'),
    fn_italic=os.path.join(_FONT_DIR, 'NotoSans-Italic.ttf'),
    fn_bolditalic=os.path.join(_FONT_DIR, 'NotoSans-BoldItalic.ttf'),
)

IDLE_TIMEOUT = 30 * 60  # 30 minutes in seconds

try:
    from .app_state import MachineState
    from .auth.auth_manager import AuthManager
    from .controller import GalilController
    from .utils import jobs
    from . import screens as _screens  # noqa: F401 - ensure screen classes are registered with Factory
    from .screens.pin_overlay import PINOverlay
    from .theme_manager import theme as app_theme
    from .hmi.poll import ControllerPoller
    from .hmi.dmc_vars import STATE_SETUP
    import dmccodegui.machine_config as mc
except Exception:  # Allows running as a script: python src/dmccodegui/main.py
    from dmccodegui.app_state import MachineState
    from dmccodegui.auth.auth_manager import AuthManager
    from dmccodegui.controller import GalilController
    from dmccodegui.utils import jobs
    import dmccodegui.screens as _screens  # type: ignore  # noqa: F401
    from dmccodegui.screens.pin_overlay import PINOverlay
    from dmccodegui.theme_manager import theme as app_theme
    from dmccodegui.hmi.poll import ControllerPoller
    from dmccodegui.hmi.dmc_vars import STATE_SETUP
    import dmccodegui.machine_config as mc


KV_FILES = [
    "ui/theme.kv",         # base styles - always first
    "ui/pin_overlay.kv",   # PINOverlay ModalView
    "ui/status_bar.kv",    # StatusBar widget
    "ui/tab_bar.kv",       # TabBar widget
    "ui/setup.kv",         # SetupScreen (connection)
    "ui/run.kv",           # RunScreen placeholder
    "ui/axes_setup.kv",    # AxesSetupScreen placeholder
    "ui/parameters.kv",    # ParametersScreen placeholder
    "ui/profiles.kv",      # ProfilesScreen (CSV import/export)
    "ui/diagnostics.kv",   # DiagnosticsScreen placeholder
    "ui/users.kv",         # UsersScreen (Admin)
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
        self._poller = None
        self._idle_event = None
        # AuthManager — path resolved at __init__ time so tests can override
        users_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "auth", "users.json"
        )
        self.auth_manager = AuthManager(users_path)
        # Initialize machine_config — loads persisted machine type from settings.json
        settings_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "auth", "settings.json"
        )
        mc.init(settings_path)

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

        # Inject auth_manager into UsersScreen
        users_screen = next((s for s in sm.screens if getattr(s, 'name', '') == 'users'), None)
        if users_screen:
            if hasattr(users_screen, 'auth_manager'):
                users_screen.auth_manager = self.auth_manager
            if hasattr(users_screen, 'state'):
                users_screen.state = self.state

        # Wire TabBar -> ScreenManager
        tab_bar = root.ids.tab_bar
        tab_bar.bind(current_tab=lambda inst, val: setattr(sm, 'current', val))

        # Wire StatusBar banner to app.banner_text
        status_bar = root.ids.status_bar
        self.bind(banner_text=status_bar.setter('banner_text'))

        # Subscribe StatusBar to state changes
        self.state.subscribe(lambda s: Clock.schedule_once(lambda *_: status_bar.update_from_state(s)))

        # Setup badge wiring — yellow bar between StatusBar and TabBar during SETUP
        setup_badge = root.ids.setup_badge

        def _update_setup_badge(s):
            from kivy.metrics import dp
            in_setup = s.connected and s.dmc_state == STATE_SETUP
            setup_badge.opacity = 1.0 if in_setup else 0.0
            setup_badge.height = dp(24) if in_setup else 0

        self.state.subscribe(
            lambda s: Clock.schedule_once(lambda *_: _update_setup_badge(s))
        )

        # Tab state gates wiring — gate tabs based on controller state
        def _update_tab_gates(s):
            tab_bar.update_state_gates(s.dmc_state, s.connected)

        self.state.subscribe(
            lambda s: Clock.schedule_once(lambda *_: _update_tab_gates(s))
        )

        # Wire user area in StatusBar to open switch-user overlay
        status_bar.bind_user_tap(lambda: self._show_pin_overlay("switch"))

        # Wire machine type tap in StatusBar to open picker (Setup/Admin only)
        status_bar.bind_machine_type_tap(lambda: self._show_machine_type_picker())

        # Wire restricted tab callback
        tab_bar.set_restricted_callback(lambda: self._show_pin_overlay("unlock"))

        # Create PIN overlay instance
        self._pin_overlay = PINOverlay()

        # Default TabBar to operator (no auth yet) — PIN overlay will set real role
        tab_bar.set_role("operator", "run")

        # Set machine type on state if already configured
        if mc.is_configured():
            self.state.machine_type = mc.get_active_type()
            self.state.notify()

        # Set initial screen to setup (connection screen)
        sm.current = 'setup'

        # Polling is handled by ControllerPoller (started when controller connects)

        # Hook controller logger to push messages into state and show banner
        self.controller.set_logger(lambda msg: Clock.schedule_once(lambda *_: self._log_message(msg)))

        # Detect pre-existing connection (e.g., controller opened by previous run)
        if self.controller.verify_connection():
            self.state.set_connected(True)
            self._start_poller()
            # Connection present — show machine type picker first if not configured,
            # then PIN overlay. Use callback chaining to guarantee order.
            Clock.schedule_once(lambda *_: self._show_startup_flow(), 0)
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
                            self.state.log(f"Connected to: {addr}")
                            self._start_poller()
                            # Auto-connect succeeded — startup flow (picker then PIN)
                            Clock.schedule_once(lambda *_: self._show_startup_flow(), 0)
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
    # Startup flow: machine type picker (if needed) then PIN overlay
    # ------------------------------------------------------------------

    def _show_startup_flow(self) -> None:
        """Show mandatory machine type picker if not configured, then PIN overlay."""
        if not mc.is_configured():
            # First launch — force picker before PIN overlay
            self._show_machine_type_picker(
                on_selected=lambda mtype: self._show_pin_on_start(),
                force=True,
            )
        else:
            self._show_pin_on_start()

    # ------------------------------------------------------------------
    # Machine type picker
    # ------------------------------------------------------------------

    def _show_machine_type_picker(self, on_selected=None, force: bool = False) -> None:
        """Open the machine type selection popup.

        Args:
            on_selected: Optional callback(mtype: str) called after selection.
            force: If True, bypass role check (used for first-launch mandatory picker).
        """
        if not force:
            # Role check — only Setup/Admin can change machine type
            role = getattr(self.state, "current_role", "")
            if role not in ("setup", "admin"):
                return

        from kivy.uix.modalview import ModalView
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.uix.button import Button

        picker = ModalView(auto_dismiss=False, size_hint=(0.55, 0.6))

        layout = BoxLayout(orientation="vertical", padding="20dp", spacing="16dp")

        # Header label
        header = Label(
            text="Select Machine Type",
            font_size="24sp",
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height="48dp",
            halign="center",
            valign="middle",
        )
        header.bind(size=header.setter("text_size"))
        layout.add_widget(header)

        def _on_type_selected(mtype: str) -> None:
            mc.set_active_type(mtype)
            self.state.machine_type = mtype
            self.state.notify()
            picker.dismiss()
            if callable(on_selected):
                on_selected(mtype)

        # One button per machine type
        for mtype in mc.MACHINE_TYPES:
            btn = Button(
                text=mtype,
                font_size="20sp",
                size_hint_y=None,
                height="64dp",
                background_normal="",
                background_down="",
                background_color=(0.1, 0.25, 0.5, 1),
                color=(1, 1, 1, 1),
            )
            # Capture mtype in default argument to avoid closure issue
            btn.bind(on_release=lambda inst, t=mtype: _on_type_selected(t))
            layout.add_widget(btn)

        picker.add_widget(layout)
        picker.open()

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
        """Callback on successful PIN entry (login or switch).

        Routes to the screen that matches the controller's current state:
          - SETUP + setup/admin role → axes_setup (resume setup session)
          - GRINDING / HOMING → run (monitor active motion)
          - IDLE / uninitialized → run (default)
        """
        self.state.set_auth(username, role)
        try:
            tab_bar = self.root.ids.tab_bar
            sm = self.root.ids.sm

            # Pick the target screen based on controller state
            target = "run"
            if (self.state.dmc_state == STATE_SETUP
                    and role in ("setup", "admin")):
                target = "axes_setup"

            tab_bar.set_role(role, target)
            sm.current = target
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
        """Called when setup screen successfully connects. Show picker then PIN overlay."""
        self._start_poller()
        Clock.schedule_once(lambda *_: self._show_startup_flow(), 0)

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
                if sm.current in ("axes_setup", "parameters", "diagnostics", "users"):
                    sm.current = "run"
                # Reset tab bar to operator view
                tab_bar._current_role = ""  # force rebuild
                tab_bar.set_role("operator", "run")
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Centralized controller poller (Phase 10)
    # ------------------------------------------------------------------

    def _start_poller(self) -> None:
        """Create and start the ControllerPoller if not already running."""
        if self._poller is None:
            self._poller = ControllerPoller(self.controller, self.state)
        self._poller.start()

    def _stop_poller(self) -> None:
        """Stop the ControllerPoller if it is running."""
        if self._poller:
            self._poller.stop()

    # ------------------------------------------------------------------
    # Controller poll (legacy — disabled; centralized poller handles this now)
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
        self._stop_poller()
        if self._idle_event:
            self._idle_event.cancel()
        jobs.shutdown()
        self.controller.disconnect()

    # ------------------------------------------------------------------
    # Global actions
    # ------------------------------------------------------------------

    def toggle_theme(self) -> None:
        """Toggle between light and dark mode."""
        new_mode = app_theme.toggle()
        # Force tab bar to rebuild with new theme colors
        try:
            tab_bar = self.root.ids.tab_bar
            role = tab_bar._current_role
            tab_bar._current_role = ""  # force rebuild
            tab_bar.set_role(role, tab_bar.current_tab)
        except Exception:
            pass

    def disconnect_and_refresh(self) -> None:
        self._stop_poller()
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
        """Emergency stop: ST ABCD + HX via priority path, then handle reset.

        Stays connected — no disconnect() call, no navigation change.
        """
        def do_estop():
            try:
                if self.controller.is_connected():
                    self.controller.cmd("ST ABCD")
                    self.controller.reset_handle()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error("e_stop error: %s", e)
            # Stay connected -- no disconnect() call, no navigation change
            Clock.schedule_once(lambda *_: self._log_message("E-STOP -- motion halted, program stopped"))
        jobs.submit_urgent(do_estop)

    def recover(self) -> None:
        """Show confirmation dialog, then send XQ #AUTO to restart DMC program.

        NOTE: XQ #AUTO is the single authorized XQ call in the codebase.
        It restarts the entire DMC program from the top (#CONFIG -> #PARAMS ->
        #COMPED -> #HOME -> #MAIN -> waiting loop). This is NOT a subroutine
        trigger and does not violate the HMI one-shot variable pattern rule.
        """
        from kivy.uix.modalview import ModalView
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.label import Label

        modal = ModalView(auto_dismiss=True, size_hint=(0.45, 0.35))
        layout = BoxLayout(orientation='vertical', padding='20dp', spacing='16dp')
        layout.add_widget(Label(text='Restart machine program?', font_size='22sp'))

        def _confirm(*_):
            modal.dismiss()
            def do_recover():
                try:
                    self.controller.cmd("SH ABCD") #ENABLE ALL AXIS -- in case of e-stop or other fault
                    self.controller.cmd("XQ #AUTO") #restart program from the top then flow to main loop
                except Exception as e:
                    msg = f"Recovery failed: {e}"
                    Clock.schedule_once(
                        lambda *_, _m=msg: self._log_message(_m)
                    )
            jobs.submit(do_recover)  # Normal submit -- recovery is not urgent

        btn_row = BoxLayout(size_hint_y=None, height='56dp', spacing='12dp')
        btn_confirm = Button(text='RESTART', background_color=(0.1, 0.4, 0.2, 1))
        btn_cancel = Button(text='CANCEL', background_color=(0.2, 0.2, 0.2, 1))
        btn_confirm.bind(on_release=_confirm)
        btn_cancel.bind(on_release=lambda *_: modal.dismiss())
        btn_row.add_widget(btn_confirm)
        btn_row.add_widget(btn_cancel)
        layout.add_widget(btn_row)
        modal.add_widget(layout)
        modal.open()

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
