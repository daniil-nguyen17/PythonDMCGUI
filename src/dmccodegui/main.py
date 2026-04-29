from __future__ import annotations

import sys
if getattr(sys, 'frozen', False):
    import os as _os
    _meipass = getattr(sys, '_MEIPASS', '')
    if _meipass:
        _os.environ['GCLIB_ROOT'] = _meipass
    del _meipass

import importlib
import logging
import logging.handlers
import os
import traceback


def _get_data_dir() -> str:
    """Return writable directory for mutable data files.

    Frozen (PyInstaller onedir, Windows): %APPDATA%\\BinhAnHMI\\
    Linux (Pi, dev on Linux):             ~/.binh-an-hmi/
    Dev (Windows, non-frozen):            src/dmccodegui/auth/
    """
    if getattr(sys, 'frozen', False):
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        data_dir = os.path.join(appdata, 'BinhAnHMI')
    elif sys.platform == 'linux':
        data_dir = os.path.join(os.path.expanduser('~'), '.binh-an-hmi')
    else:
        data_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'auth'
        )
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def setup_logging() -> None:
    """Configure the root logger with a rotating file handler and optional console handler.

    File handler: logs/app.log under _get_data_dir(), 5 MB limit, 3 backups, UTF-8.
    Console handler: only attached when sys.stderr is not None (frozen apps with
    console=False have stderr=None, so we guard against that).
    Root logger level set to DEBUG so all records reach handlers.

    Call this once at startup, before any Kivy imports.
    """
    log_dir = os.path.join(_get_data_dir(), "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "app.log")
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(module)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)

    # Guard: frozen apps with console=False set sys.stderr = None.
    # When stderr is available, always write to sys.__stderr__ (the real OS
    # stderr) rather than sys.stderr. Kivy replaces sys.stderr with its own
    # logger proxy after import, which would create an infinite logging loop
    # (StreamHandler → Kivy stderr proxy → root logger → StreamHandler …).
    if sys.stderr is not None:
        real_stderr = getattr(sys, "__stderr__", sys.stderr) or sys.stderr
        console_handler = logging.StreamHandler(real_stderr)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)


def _setup_excepthook() -> None:
    """Patch sys.excepthook to log uncaught exceptions before the process exits.

    KeyboardInterrupt is passed through to the original hook without logging —
    it is a user-initiated exit, not an unexpected crash.

    All other exceptions are logged at CRITICAL level via the 'dmccodegui' logger
    with the full formatted traceback before calling the original hook.

    Call this once at startup, after setup_logging().
    """
    _original_excepthook = sys.__excepthook__

    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            _original_excepthook(exc_type, exc_value, exc_tb)
            return
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logging.getLogger("dmccodegui").critical("Uncaught exception:\n%s", msg)
        _original_excepthook(exc_type, exc_value, exc_tb)

    sys.excepthook = _excepthook


# ---------------------------------------------------------------------------
# Display preset detection -- runs before any Kivy import
# ---------------------------------------------------------------------------
# Density values are initial estimates pending hardware validation on each
# display size. Kept as named constants here for easy tuning.
_DISPLAY_PRESETS: dict[str, dict] = {
    "7inch": {
        "density": "0.65",
        "width": 800,
        "height": 480,
        "fullscreen_mode": "auto",
        "borderless": "0",
        "maximized": "0",
        "resizable": "0",
    },
    "10inch": {
        "density": "0.75",
        "width": 1024,
        "height": 600,
        "fullscreen_mode": "auto",
        "borderless": "0",
        "maximized": "0",
        "resizable": "0",
    },
    "15inch": {
        "density": "1",
        "width": 1920,
        "height": 1080,
        "fullscreen_mode": "0",
        "borderless": "0",
        "maximized": "1",
        "resizable": "1",
    },
}


def _classify_resolution(width: int, height: int) -> str:
    """Classify a display resolution into a preset name.

    Uses the short dimension (min of width/height) to handle portrait vs
    landscape orientations uniformly.

    Thresholds (inclusive):
      short <= 480  → '7inch'
      short <= 600  → '10inch'
      else          → '15inch'

    Ambiguous resolutions round DOWN to the larger preset (bigger fonts)
    because the <= thresholds include each preset's native short dimension.

    Args:
        width: Display width in pixels.
        height: Display height in pixels.

    Returns:
        One of '7inch', '10inch', '15inch'.
    """
    short = min(width, height)
    if short <= 480:
        return "7inch"
    if short <= 600:
        return "10inch"
    return "15inch"


def _early_settings_path() -> str:
    """Return the settings.json path using the same logic as _get_data_dir().

    This is a pre-init bootstrap read: Kivy has not been imported yet and
    no App instance exists. We intentionally duplicate the path logic here
    rather than calling _get_data_dir() so that this function has no side
    effects (makedirs) at detection time.

    Frozen (PyInstaller onedir, Windows): %APPDATA%\\BinhAnHMI\\settings.json
    Linux (Pi, dev on Linux):             ~/.binh-an-hmi/settings.json
    Dev (Windows, non-frozen):            src/dmccodegui/auth/settings.json
    """
    if getattr(sys, 'frozen', False):
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        data_dir = os.path.join(appdata, 'BinhAnHMI')
    elif sys.platform == 'linux':
        data_dir = os.path.join(os.path.expanduser('~'), '.binh-an-hmi')
    else:
        data_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'auth'
        )
    return os.path.join(data_dir, 'settings.json')


def _detect_preset(settings_path: str) -> str:
    """Detect the display preset to use, with settings.json override support.

    Resolution detection priority:
      1. settings.json ``display_size`` key (if file exists and value is valid).
         Invalid value → return '15inch' immediately (do NOT fall through to
         auto-detect, per locked decision).
      2. screeninfo.get_monitors() auto-detection via _classify_resolution().
      3. Any screeninfo failure → fall back to '15inch' (safe desktop default).

    Args:
        settings_path: Absolute path to settings.json. May not exist.

    Returns:
        One of '7inch', '10inch', '15inch'.
    """
    _VALID_PRESETS = set(_DISPLAY_PRESETS.keys())

    # Priority 1: settings.json override
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as fh:
                data = fh.read()
            import json as _json
            parsed = _json.loads(data)
            override = parsed.get("display_size", "")
            if override:
                if override in _VALID_PRESETS:
                    _log.info("Preset override from settings: %s", override)
                    return override
                else:
                    # Invalid override value — do NOT fall through to auto-detect
                    _log.warning("Invalid display_size '%s' in settings.json -- using 15inch default", override)
                    return "15inch"
        except Exception:
            pass  # Corrupt/unreadable settings — fall through to auto-detect

    # Priority 2: screeninfo auto-detection
    try:
        from screeninfo import get_monitors
        from screeninfo.common import ScreenInfoError  # noqa: F401
        monitors = get_monitors()
        if monitors:
            mon = monitors[0]
            preset = _classify_resolution(mon.width, mon.height)
            _log.info("Auto-detected preset '%s' from %dx%d", preset, mon.width, mon.height)
            return preset
    except Exception as exc:
        _log.warning("screeninfo unavailable (%s) -- using 15inch default", exc)

    # Priority 3: safe fallback
    return "15inch"


# Initialize logging before anything else in the pre-Kivy block.
# This ensures all subsequent startup messages (including _detect_preset)
# go to the rotating log file.
setup_logging()
_setup_excepthook()

# Module-level logger — must be defined after setup_logging() so the root logger
# is configured, and before _detect_preset() so its _log.info/warning calls work.
_log = logging.getLogger(__name__)

# Run preset detection and configure Kivy environment before any Kivy imports.
_ACTIVE_PRESET_NAME: str = _detect_preset(_early_settings_path())
_PRESET = _DISPLAY_PRESETS[_ACTIVE_PRESET_NAME]

os.environ["KIVY_DPI_AWARE"] = "1"
os.environ["KIVY_METRICS_DENSITY"] = _PRESET["density"]
os.environ["KIVY_MOUSE"] = "mouse,multitouch_on_demand"
# Use ANGLE (DirectX) backend on Windows to avoid AMD OpenGL driver crashes
# (atio6axx.dll faults under sustained matplotlib plot redraws).
# Linux (Pi) uses native EGL/GLES2 — no change needed.
if sys.platform == "win32":
    os.environ.setdefault("KIVY_GL_BACKEND", "angle_sdl2")
from typing import cast
from kivy.config import Config

Config.set('graphics', 'fullscreen', _PRESET["fullscreen_mode"])
Config.set('graphics', 'maximized', _PRESET["maximized"])
Config.set('graphics', 'borderless', _PRESET["borderless"])
Config.set('graphics', 'resizable', _PRESET["resizable"])
# Only set explicit width/height for non-maximized presets (Pi touchscreens).
# For maximized presets (desktop/laptop), the window manager determines the
# size — setting explicit dimensions causes Kivy to use those instead of
# the actual maximized area, clipping content on screens that don't match.
if _PRESET["maximized"] != "1":
    Config.set('graphics', 'width', str(_PRESET["width"]))
    Config.set('graphics', 'height', str(_PRESET["height"]))
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')  # ensure mouse input

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.properties import StringProperty
from kivy.core.window import Window

# Config.set('graphics', 'maximized', '1') is unreliable — Kivy may ignore
# it depending on the SDL2 backend and platform.  Calling Window.maximize()
# after the Window object exists guarantees the window fills the screen.
if _PRESET["maximized"] == "1":
    Window.maximize()

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

# Suppress Kivy's verbose DEBUG output so it doesn't flood app.log.
# Kivy uses its own logger; setting it to WARNING keeps errors visible
# without the per-frame and OpenGL debug noise.
logging.getLogger("kivy").setLevel(logging.WARNING)

IDLE_TIMEOUT = 30 * 60  # 30 minutes in seconds

try:
    from .app_state import MachineState
    from .auth.auth_manager import AuthManager
    from .controller import GalilController
    from .utils import jobs
    from . import screens as _screens  # noqa: F401 - ensure screen classes are registered with Factory
    from .screens.pin_overlay import PINOverlay
    from .theme_manager import theme as app_theme
    from .hmi.data_record import DataRecordListener, get_hmi_ip
    from .hmi.mg_reader import MgReader
    from .hmi.dmc_vars import STATE_SETUP
    import dmccodegui.machine_config as mc
    from dmccodegui import __version__
except Exception:  # Allows running as a script: python src/dmccodegui/main.py
    from dmccodegui.app_state import MachineState
    from dmccodegui.auth.auth_manager import AuthManager
    from dmccodegui.controller import GalilController
    from dmccodegui.utils import jobs
    import dmccodegui.screens as _screens  # type: ignore  # noqa: F401
    from dmccodegui.screens.pin_overlay import PINOverlay
    from dmccodegui.theme_manager import theme as app_theme
    from dmccodegui.hmi.data_record import DataRecordListener, get_hmi_ip
    from dmccodegui.hmi.mg_reader import MgReader
    from dmccodegui.hmi.dmc_vars import STATE_SETUP
    import dmccodegui.machine_config as mc
    from dmccodegui import __version__


KV_FILES = [
    "ui/theme.kv",         # base styles - always first
    "ui/pin_overlay.kv",   # PINOverlay ModalView
    "ui/status_bar.kv",    # StatusBar widget
    "ui/tab_bar.kv",       # TabBar widget
    "ui/setup.kv",         # SetupScreen (connection)
    # Machine-specific KV loaded by _add_machine_screens() before this loop
    "ui/profiles.kv",      # ProfilesScreen (CSV import/export)
    "ui/users.kv",         # UsersScreen (Admin)
    "ui/base.kv",          # RootLayout - always last
]

# machType DMC variable value -> machine type string.
# Each machine's DMC program sets machType in #AUTO on power-on:
#   1 = 4-Axes Flat Grind      (4 Axis Stainless grind.dmc)
#   2 = 3-Axes Serration Grind (3 Axis Serration grind.dmc)
#   3 = 4-Axes Convex Grind    (Convex DMC — set machType=3 in #AUTO)
# Read by _check_machine_type_mismatch() on every connect.
_MACH_TYPE_MAP = {
    1: "4-Axes Flat Grind",
    2: "3-Axes Serration Grind",
    3: "4-Axes Convex Grind",
}


def _resolve_dotted_path(dotted: str):
    """Resolve a dotted import path string to the named attribute.

    Args:
        dotted: A fully-qualified dotted path, e.g.
            "dmccodegui.screens.flat_grind.FlatGrindRunScreen".

    Returns:
        The resolved object (class, function, etc.).

    Raises:
        ImportError: If the module portion cannot be imported.
        AttributeError: If the attribute does not exist on the module.
    """
    module_path, attr_name = dotted.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, attr_name)


class DMCApp(App):
    title = f'Binh An HMI v{__version__}'
    # Top-of-app banner text for alerts/logs
    banner_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state = MachineState()
        self.controller = GalilController()
        self._poll_cancel = None
        self._dr_listener = None
        self._idle_event = None
        self.mg_reader = MgReader()
        # AuthManager — path resolved at __init__ time so tests can override
        data_dir = _get_data_dir()
        users_path = os.path.join(data_dir, "users.json")
        self.auth_manager = AuthManager(users_path)
        # Initialize machine_config — loads persisted machine type from settings.json
        settings_path = os.path.join(data_dir, "settings.json")
        mc.init(settings_path)

    def build(self):
        if Window:
            Window.bind(on_cursor_enter=lambda *args: Window.show())

        from kivy.resources import resource_add_path
        resource_add_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'images'))

        # Step 1: Load machine-specific KV files (before base.kv instantiates RootLayout).
        # Resolved from _REGISTRY so no hard-coded machine type references live here.
        if mc.is_configured():
            try:
                entry = mc._REGISTRY[mc.get_active_type()]
                _load_kv_fn = _resolve_dotted_path(entry["load_kv"])
                _load_kv_fn()
            except Exception as exc:
                _log.error("Failed to load machine KV: %s", exc)

        for kv in KV_FILES:
            Builder.load_file(os.path.join(os.path.dirname(__file__), kv))

        root = Factory.RootLayout()

        # Step 2: Add machine screens programmatically into the ScreenManager.
        sm = root.ids.sm
        self._add_machine_screens(sm)

        # Inject controller/state into ALL screens (KV-declared + programmatic)
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

        # State streaming handled by DataRecordListener (started when controller connects)

        # Hook controller logger to push messages into state and show banner
        self.controller.set_logger(lambda msg: Clock.schedule_once(lambda *_: self._log_message(msg)))

        # Detect pre-existing connection (e.g., controller opened by previous run)
        if self.controller.verify_connection():
            self.state.set_connected(True)
            self._start_dr()
            self._start_mg_reader()
            self._preload_params()
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
                            self.state.connected_address = self.controller._strip_flags(addr)
                            self.state.log(f"Connected to: {addr}")
                            self._start_dr()
                            self._start_mg_reader()
                            self._preload_params()
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
        """Auto-detect machine type from controller if unconfigured, else continue.

        Flow on first launch (unconfigured):
          1. Try to read MG machType from the controller in a background job.
          2. If the read succeeds and the value is a known machine type,
             auto-select it via mc.set_active_type() and proceed to PIN.
          3. If the read fails, the value is unknown, or the controller is
             not connected, fall back to the manual picker (legacy path).

        Flow when already configured:
          - Skip auto-detect and go straight to PIN. _check_machine_type_mismatch
            will fire 1 sec later and catch any mismatch between the saved config
            and the actual controller.
        """
        if mc.is_configured():
            self._show_pin_on_start()
            return

        # Unconfigured — try auto-detect from controller's machType first
        ctrl = self.controller
        if not ctrl or not ctrl.is_connected():
            # No controller yet — fall back to manual picker
            self._show_machine_type_picker(
                on_selected=lambda mtype: self._show_pin_on_start(),
                force=True,
            )
            return

        def _do_detect():
            detected: str | None = None
            try:
                raw = ctrl.cmd("MG machType").strip()
                mach_int = int(float(raw))
                detected = _MACH_TYPE_MAP.get(mach_int)
            except Exception:
                detected = None

            def _apply(*_):
                if detected:
                    # Auto-select and persist
                    try:
                        mc.set_active_type(detected)
                        self.state.machine_type = detected
                        self.state.notify()
                        self._log_message(f"Auto-detected machine type: {detected}")
                    except Exception as exc:
                        self._log_message(f"Auto-detect apply failed: {exc}")
                        # Fall through to manual picker
                        self._show_machine_type_picker(
                            on_selected=lambda mtype: self._show_pin_on_start(),
                            force=True,
                        )
                        return
                    # First-launch path: screens are not yet loaded for this type.
                    # Load them inline so PIN + subsequent nav work without restart.
                    try:
                        self._load_machine_screens(detected)
                    except Exception as exc:
                        self._log_message(f"Screen load failed: {exc}")
                    self._show_pin_on_start()
                else:
                    # Read failed or unknown value — manual picker fallback
                    self._show_machine_type_picker(
                        on_selected=lambda mtype: self._show_pin_on_start(),
                        force=True,
                    )

            Clock.schedule_once(_apply)

        jobs.submit(_do_detect)

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
            # Delegate screen-loading to the shared helper. This handles both
            # the first-launch inline load and the type-change restart prompt.
            self._load_machine_screens(mtype)

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
    # Registry-driven machine screen loader
    # ------------------------------------------------------------------

    def _load_machine_screens(self, mtype: str) -> None:
        """Load machine-specific KV and screens inline for the chosen type.

        Shared by the manual picker path and the auto-detect path. Called
        after mc.set_active_type() has already been set.

        Behavior:
          - If no 'run' screen exists yet (first launch), load the machine KV
            and instantiate/add screens, injecting controller and state.
          - If a 'run' screen already exists (machine type CHANGED at runtime),
            show the restart prompt per Phase 20 spec. Kivy can't cleanly
            swap machine screen classes in-place.

        Silent no-op on any exception — the caller is responsible for reporting.
        """
        try:
            sm = self.root.ids.sm
            has_run = any(getattr(s, "name", "") == "run" for s in sm.screens)
            if not has_run:
                # First launch — load KV and instantiate screens inline
                entry = mc._REGISTRY[mtype]
                _load_kv_fn = _resolve_dotted_path(entry["load_kv"])
                _load_kv_fn()
                self._add_machine_screens(sm)
                # Inject controller/state into newly added screens
                for screen in sm.screens:
                    if hasattr(screen, "controller") and hasattr(screen, "state"):
                        screen.controller = self.controller
                        screen.state = self.state
            else:
                # Machine type changed at runtime — requires restart
                from kivy.uix.modalview import ModalView
                from kivy.uix.boxlayout import BoxLayout
                from kivy.uix.label import Label
                from kivy.uix.button import Button
                restart_modal = ModalView(auto_dismiss=False, size_hint=(0.45, 0.3))
                restart_layout = BoxLayout(orientation="vertical", padding="20dp", spacing="12dp")
                restart_layout.add_widget(Label(
                    text="Machine type changed.\nPlease restart the application.",
                    font_size="18sp",
                    halign="center",
                ))
                exit_btn = Button(
                    text="Exit Now",
                    size_hint_y=None,
                    height="56dp",
                    background_color=(0.1, 0.4, 0.2, 1),
                )

                def _do_exit(*_):
                    restart_modal.dismiss()
                    try:
                        for screen in list(sm.screens):
                            if hasattr(screen, "cleanup"):
                                screen.cleanup()
                    except Exception:
                        pass
                    self.stop()

                exit_btn.bind(on_release=_do_exit)
                restart_layout.add_widget(exit_btn)
                restart_modal.add_widget(restart_layout)
                restart_modal.open()
        except Exception:
            pass

    def _add_machine_screens(self, sm) -> None:
        """Instantiate machine-type screens from the registry and add to ScreenManager.

        Reads mc._REGISTRY[active_type]["screen_classes"], resolves each dotted
        class path via importlib, instantiates with the canonical screen name, injects
        controller and state, then calls sm.add_widget().

        Does nothing if mc.get_active_type() returns "" (app not yet configured).

        On any resolution or instantiation failure, shows an error popup and stops
        the app rather than leaving it in a half-initialised state.

        Args:
            sm: A Kivy ScreenManager (or compatible add_widget container).
        """
        mtype = mc.get_active_type()
        if not mtype:
            _log.debug("_add_machine_screens: no active machine type — skipping")
            return

        try:
            entry = mc._REGISTRY[mtype]
            for canonical_name, class_path in entry["screen_classes"].items():
                cls = _resolve_dotted_path(class_path)
                screen = cls(name=canonical_name)
                if hasattr(screen, "controller"):
                    screen.controller = self.controller
                if hasattr(screen, "state"):
                    screen.state = self.state
                sm.add_widget(screen)
                _log.info("_add_machine_screens: added %r (%s)", canonical_name, class_path)
        except Exception as exc:
            _log.error("_add_machine_screens failed: %s", exc)
            self._show_loader_error(str(exc))

    def _show_loader_error(self, message: str) -> None:
        """Show a blocking error popup then stop the app."""
        from kivy.uix.modalview import ModalView
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.uix.button import Button

        modal = ModalView(auto_dismiss=False, size_hint=(0.6, 0.4))
        layout = BoxLayout(orientation="vertical", padding="20dp", spacing="16dp")
        layout.add_widget(Label(
            text=f"Failed to load machine screens:\n{message}",
            font_size="18sp",
            halign="center",
        ))
        btn = Button(
            text="Exit",
            size_hint_y=None,
            height="56dp",
            background_color=(0.6, 0.1, 0.1, 1),
        )
        btn.bind(on_release=lambda *_: self.stop())
        layout.add_widget(btn)
        modal.add_widget(layout)
        modal.open()

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
        self._start_dr()
        self._start_mg_reader()
        self._preload_params()
        Clock.schedule_once(lambda *_: self._show_startup_flow(), 0)
        # Delay machType check to give poller time to establish connection
        Clock.schedule_once(lambda *_: self._check_machine_type_mismatch(), 1.0)

    def _check_machine_type_mismatch(self) -> None:
        """Query machType from controller and compare against the configured type.

        Runs in a background job. On any query failure or unknown value, returns
        silently (graceful degradation — per Phase 20 locked decision).

        If the controller reports a different machine type than the current config,
        schedules _show_mismatch_popup on the UI thread.
        """
        def _do():
            try:
                raw = self.controller.cmd("MG machType").strip()
                mach_int = int(float(raw))
                ctrl_type = _MACH_TYPE_MAP.get(mach_int)
                if ctrl_type is None:
                    # Unknown machType value — graceful degradation
                    return
                config_type = mc.get_active_type()
                if not config_type:
                    return
                if ctrl_type != config_type:
                    Clock.schedule_once(
                        lambda *_: self._show_mismatch_popup(ctrl_type, config_type)
                    )
            except Exception:
                # Query failure — silently ignore per locked decision
                return

        jobs.submit(_do)

    def _show_mismatch_popup(self, ctrl_type: str, config_type: str) -> None:
        """Show a popup when controller machType mismatches the configured type.

        Offers machine type selection buttons to switch and restart. Also provides
        a 'Keep Current' button to dismiss the popup without action.

        Args:
            ctrl_type: Machine type string reported by the controller.
            config_type: Machine type string from local settings.json.
        """
        from kivy.uix.modalview import ModalView
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.uix.button import Button

        popup = ModalView(auto_dismiss=False, size_hint=(0.6, 0.7))
        layout = BoxLayout(orientation="vertical", padding="20dp", spacing="14dp")

        # Header
        header = Label(
            text="Machine Type Mismatch",
            font_size="22sp",
            bold=True,
            color=(1, 0.85, 0, 1),
            size_hint_y=None,
            height="44dp",
            halign="center",
            valign="middle",
        )
        header.bind(size=header.setter("text_size"))
        layout.add_widget(header)

        # Description
        desc = Label(
            text=(
                f"Controller reports:\n[b]{ctrl_type}[/b]\n\n"
                f"App configured for:\n[b]{config_type}[/b]\n\n"
                "Select the correct machine type:"
            ),
            markup=True,
            font_size="18sp",
            halign="center",
            valign="top",
        )
        desc.bind(size=desc.setter("text_size"))
        layout.add_widget(desc)

        def _on_type_selected(selected: str) -> None:
            if selected != mc.get_active_type():
                mc.set_active_type(selected)
            popup.dismiss()
            # Show restart notice — per Phase 20 spec, machine type change
            # requires full app exit and restart to load correct screens.
            restart_modal = ModalView(auto_dismiss=False, size_hint=(0.45, 0.3))
            restart_layout = BoxLayout(orientation="vertical", padding="20dp", spacing="12dp")
            restart_layout.add_widget(Label(
                text="Machine type changed.\nPlease restart the application.",
                font_size="18sp",
                halign="center",
            ))
            exit_btn = Button(
                text="Exit Now",
                size_hint_y=None,
                height="56dp",
                background_color=(0.1, 0.4, 0.2, 1),
            )

            def _do_exit(*_):
                restart_modal.dismiss()
                try:
                    sm = self.root.ids.sm
                    for screen in list(sm.screens):
                        if hasattr(screen, "cleanup"):
                            screen.cleanup()
                except Exception:
                    pass
                self.stop()

            exit_btn.bind(on_release=_do_exit)
            restart_layout.add_widget(exit_btn)
            restart_modal.add_widget(restart_layout)
            restart_modal.open()

        # One button per machine type
        for mtype in mc.MACHINE_TYPES:
            btn = Button(
                text=mtype,
                font_size="18sp",
                size_hint_y=None,
                height="56dp",
                background_normal="",
                background_down="",
                background_color=(0.1, 0.25, 0.5, 1),
                color=(1, 1, 1, 1),
            )
            btn.bind(on_release=lambda inst, t=mtype: _on_type_selected(t))
            layout.add_widget(btn)

        # Keep Current dismiss button
        keep_btn = Button(
            text="Keep Current",
            font_size="18sp",
            size_hint_y=None,
            height="56dp",
            background_normal="",
            background_down="",
            background_color=(0.25, 0.25, 0.25, 1),
            color=(1, 1, 1, 1),
        )
        keep_btn.bind(on_release=lambda *_: popup.dismiss())
        layout.add_widget(keep_btn)

        popup.add_widget(layout)
        popup.open()

    def _preload_params(self) -> None:
        """Bulk-read common controller parameters into state.cached_params.

        Runs on the jobs worker thread. Screens can read from the cache
        instead of issuing redundant GCommand reads on each entry.
        """
        ctrl = self.controller
        state = self.state
        if not ctrl or not ctrl.is_connected():
            return

        def _do():
            params: dict[str, float] = {}
            try:
                from .hmi.dmc_vars import (
                    HMI_STATE_VAR, CT_SES_KNI, CT_STN_KNI,
                    RESTPT_VARS, STARTPT_VARS,
                )
            except ImportError:
                from dmccodegui.hmi.dmc_vars import (
                    HMI_STATE_VAR, CT_SES_KNI, CT_STN_KNI,
                    RESTPT_VARS, STARTPT_VARS,
                )
            # Batch 1: state + knife counts
            try:
                raw = ctrl.cmd(f"MG {HMI_STATE_VAR}, {CT_SES_KNI}, {CT_STN_KNI}").strip()
                vals = [float(v) for v in raw.split()]
                params[HMI_STATE_VAR] = vals[0]
                params[CT_SES_KNI] = vals[1]
                params[CT_STN_KNI] = vals[2]
            except Exception:
                pass
            # Batch 2: rest points
            try:
                refs = ", ".join(RESTPT_VARS)
                raw = ctrl.cmd(f"MG {refs}").strip()
                vals = [float(v) for v in raw.split()]
                for name, val in zip(RESTPT_VARS, vals):
                    params[name] = val
            except Exception:
                pass
            # Batch 3: start points
            try:
                refs = ", ".join(STARTPT_VARS)
                raw = ctrl.cmd(f"MG {refs}").strip()
                vals = [float(v) for v in raw.split()]
                for name, val in zip(STARTPT_VARS, vals):
                    params[name] = val
            except Exception:
                pass
            # Batch 4: CPM values
            for axis in ("A", "B", "C", "D"):
                try:
                    raw = ctrl.cmd(f"MG cpm{axis}").strip()
                    params[f"cpm{axis}"] = float(raw)
                except Exception:
                    pass
            # Batch 5: positions
            try:
                raw = ctrl.cmd("MG _TPA, _TPB, _TPC, _TPD").strip()
                vals = [float(v) for v in raw.split()]
                params["_TPA"] = vals[0]
                params["_TPB"] = vals[1]
                params["_TPC"] = vals[2]
                params["_TPD"] = vals[3]
            except Exception:
                pass

            def _apply(*_):
                state.cached_params.update(params)
                # Also update live state fields from preloaded data
                if HMI_STATE_VAR in params:
                    state.dmc_state = int(params[HMI_STATE_VAR])
                if CT_SES_KNI in params:
                    state.session_knife_count = int(params[CT_SES_KNI])
                if CT_STN_KNI in params:
                    state.stone_knife_count = int(params[CT_STN_KNI])
                for axis, key in zip("ABCD", ("_TPA", "_TPB", "_TPC", "_TPD")):
                    if key in params:
                        state.pos[axis] = params[key]
                state.notify()
                _log.info("Cached %d params from controller", len(params))

            Clock.schedule_once(_apply)

        jobs.submit(_do)

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
                if sm.current in ("axes_setup", "parameters", "users"):
                    sm.current = "run"
                # Reset tab bar to operator view
                tab_bar._current_role = ""  # force rebuild
                tab_bar.set_role("operator", "run")
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Data Record (DR) streaming — replaces ControllerPoller
    # ------------------------------------------------------------------

    def _start_dr(self) -> None:
        """Create and start the DataRecordListener if not already running."""
        if self._dr_listener is None:
            self._dr_listener = DataRecordListener(self.state)
        if not self._dr_listener.is_running():
            addr = self.state.connected_address or getattr(self.controller, '_address', '')
            if addr:
                hmi_ip = get_hmi_ip(addr)
                self._dr_listener.start(self.controller, hmi_ip)

    def _stop_dr(self) -> None:
        """Stop the DataRecordListener if it is running."""
        if self._dr_listener and self._dr_listener.is_running():
            self._dr_listener.stop(self.controller)

    def _start_mg_reader(self) -> None:
        """Start the app-wide MgReader using the controller's connected address."""
        addr = getattr(self.state, 'connected_address', '') or ''
        if not addr:
            # Try to get address from controller directly
            try:
                addr = getattr(self.controller, '_address', '') or ''
            except Exception:
                pass
        if addr:
            self.mg_reader.start(addr)
            _log.info("MgReader start requested with addr=%s, log_handlers=%d",
                      addr, len(self.mg_reader._log_handlers))
        else:
            _log.warning("MgReader: no address available -- MG reader not started")

    def _stop_mg_reader(self) -> None:
        """Stop the app-wide MgReader."""
        self.mg_reader.stop()

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
        # Cancel timers and poller first — no more commands queued
        if self._poll_cancel:
            self._poll_cancel()
        self._stop_dr()
        self._stop_mg_reader()
        if self._idle_event:
            self._idle_event.cancel()

        # Delegate teardown to each screen's cleanup() method.
        # This replaces ad-hoc _stop_pos_poll / _stop_mg_reader calls — each
        # screen knows how to tear itself down cleanly.
        try:
            sm = self.root.ids.sm
            for screen in list(sm.screens):
                if hasattr(screen, 'cleanup'):
                    screen.cleanup()
        except Exception:
            pass

        # Shut down jobs thread, then quietly close the TCP handle.
        # No ST/AB/MO sent — controller keeps running independently.
        # On next HMI start, we pick up whatever state the controller is in.
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
        self._stop_dr()
        self._stop_mg_reader()
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
        """Emergency stop: ST ABCD via priority path, then handle reset.

        Stays connected — no disconnect() call, no navigation change.
        """
        def do_estop():
            try:
                if self.controller.is_connected():
                    self.controller.cmd("ST ABCD")
                    self.controller.cmd("HX")
                    self.controller.reset_handle()
            except Exception as e:
                _log.error("e_stop error: %s", e)
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
