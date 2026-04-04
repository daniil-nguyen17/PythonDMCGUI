# Architecture Patterns

**Domain:** Industrial machine control GUI — knife grinding, Python/Kivy/gclib
**Researched:** 2026-04-04
**Confidence:** HIGH (based on direct codebase analysis + established Kivy/Python patterns)

---

## Existing Architecture (Baseline)

The current app has a clear, well-structured foundation. New features must extend it without breaking these proven patterns.

```
DMCApp (kivy.app.App)
  ├── MachineState          — observable dataclass, pub/sub via subscribe()
  ├── GalilController       — thin wrapper around gclib.py handle
  ├── jobs.JobThread        — single background thread, FIFO queue
  └── RootLayout (KV)
        ├── SomeMenu_ActionBar   — global nav (Setup button + Actions spinner + E-STOP)
        ├── BannerLabel          — app.banner_text ticker
        └── ScreenManager
              ├── SetupScreen      (setup)
              ├── RestScreen       (rest)
              ├── StartScreen      (start)
              ├── AxisDSetupScreen (axisDSetup)
              ├── ParametersSetupScreen (params_setup)
              ├── ButtonsSwitchesScreen (buttons_switches)
              └── SerratedKnifeScreen   (serration_knife)
```

**Invariants to preserve:**
- All gclib I/O goes through `jobs.submit()` → `Clock.schedule_once()` back to UI thread
- Screens receive `controller` and `state` via injection from `main.py` after build
- `MachineState` is the single source of truth; screens subscribe and unsubscribe on enter/leave
- KV files load in dependency order, `base.kv` last

---

## Recommended Architecture for New Milestone

### Overview of Added Components

```
DMCApp
  ├── MachineState          (extended: +role, +user_id, +machine_type)
  ├── AuthManager           (NEW — PIN lookup, role enforcement)
  ├── MachineConfig         (NEW — machine_type enum, axis count, screen set)
  ├── GalilController       (unchanged)
  ├── jobs.JobThread        (unchanged)
  └── RootLayout
        ├── TabBar            (NEW — replaces ActionBar+Spinner nav)
        ├── BannerLabel       (unchanged)
        ├── PinOverlay        (NEW — modal overlay, floated above ScreenManager)
        └── ScreenManager
              ├── [Common screens]
              ├── RunScreen         (NEW — live plot + cycle control)
              ├── AxesSetupScreen   (NEW — unified jog/teach, replaces rest/start/axisDSetup)
              ├── ParametersScreen  (NEW — grouped cards, CSV import/export)
              ├── DiagnosticsScreen (NEW)
              └── [Machine-type screen sets — see below]
```

---

## Component Boundaries

### AuthManager

| Boundary | Detail |
|----------|--------|
| Responsibility | Store PIN-to-role mappings in memory (dict); validate PIN; return role; no persistence required |
| Exposes | `validate_pin(pin: str) -> Role | None`, `current_role: Role`, `current_user_id: str` |
| Communicates with | `MachineState` (writes `state.role`, `state.user_id` on login), `PinOverlay` (receives PIN string from UI) |
| Does NOT do | Hashing, encryption, file I/O, network. In-memory dict is sufficient per PROJECT.md |
| Build note | Hard-code user records for now; Admin screen creates/deletes at runtime in-memory |

**Role enum:**
```python
from enum import Enum

class Role(Enum):
    NONE = "none"         # unauthenticated
    OPERATOR = "operator" # run cycles, read-only on params
    SETUP = "setup"       # full config access, unlocked via PIN overlay
    ADMIN = "admin"       # user management
```

---

### MachineState (extended)

Add fields; do NOT break existing field names — screens depend on them.

```python
# NEW fields to add to the MachineState dataclass:
role: Role = Role.NONE
user_id: str = ""
machine_type: str = "flat_grind"   # "flat_grind" | "convex_grind" | "serration"
cycle_running: bool = False
cycle_progress: float = 0.0        # 0.0–1.0
```

**Data flow:** `AuthManager.validate_pin()` → writes `state.role` and `state.user_id` → calls `state.notify()` → all subscribed screens re-evaluate what they show/hide based on role.

---

### MachineConfig

| Boundary | Detail |
|----------|--------|
| Responsibility | Map `machine_type` string to axis count, available screen names, DMC array names |
| Exposes | `CONFIGS: dict[str, MachineTypeConfig]` — a module-level constant dict |
| Communicates with | `DMCApp.build()` (reads to load correct screen set), `TabBar` (reads to hide/show tabs) |
| Does NOT do | Runtime mutation. Config is static once production starts (per PROJECT.md) |

```python
@dataclass
class MachineTypeConfig:
    axes: list[str]                # e.g. ["A","B","C","D"] for flat/convex, ["A","B","C"] for serration
    screen_set: str                # "flat_grind" | "convex_grind" | "serration"
    dmc_arrays: dict[str, str]     # logical name → DMC array name

CONFIGS = {
    "flat_grind":    MachineTypeConfig(axes=["A","B","C","D"], screen_set="flat_grind",    ...),
    "convex_grind":  MachineTypeConfig(axes=["A","B","C","D"], screen_set="convex_grind",  ...),
    "serration":     MachineTypeConfig(axes=["A","B","C"],     screen_set="serration",     ...),
}
```

---

### PinOverlay

| Boundary | Detail |
|----------|--------|
| Responsibility | Full-screen modal PIN entry. Floated above `ScreenManager` in the KV layout using `FloatLayout` or `ModalView`. Dismisses on correct PIN or cancel |
| Exposes | `show(reason: str, on_success: Callable[[Role], None])` — called by any screen that needs elevation |
| Communicates with | `AuthManager` (sends collected PIN, receives role), screen callbacks |
| Does NOT do | Navigation. On success it calls the provided callback; the caller decides what happens next |

**Pattern — using Kivy ModalView:**
```python
class PinOverlay(ModalView):
    def show(self, reason: str, on_success):
        self._on_success = on_success
        self._reason = reason
        self.open()

    def _on_pin_submitted(self, pin: str):
        role = App.get_running_app().auth.validate_pin(pin)
        if role:
            self._on_success(role)
            self.dismiss()
        else:
            self._shake_feedback()  # visual error, no dismiss
```

**Why ModalView over a screen:** Navigation history is not polluted. The underlying screen remains visible behind the overlay (dimmed), which gives operators spatial context. Dismissing does not require managing ScreenManager history.

---

### TabBar

| Boundary | Detail |
|----------|--------|
| Responsibility | Replace `SomeMenu_ActionBar` with a fixed tab bar. Render tabs based on `state.machine_type`. Hide/show tabs based on `state.role` |
| Exposes | `set_active(screen_name: str)` — called on `ScreenManager.on_current` |
| Communicates with | `ScreenManager` (sets `.current`), `MachineState` (subscribes to role + machine_type) |
| Does NOT do | Auth. If a restricted tab is tapped, TabBar calls `PinOverlay.show()` |

**Role-to-tab visibility matrix:**

| Tab | OPERATOR | SETUP | ADMIN |
|-----|----------|-------|-------|
| Run | visible | visible | visible |
| Axes Setup | hidden (grayed) | visible | visible |
| Parameters | hidden (grayed) | visible | visible |
| Diagnostics | hidden (grayed) | visible | visible |
| Admin | hidden | hidden | visible |

Implementation: store tab visibility rules as a dict in TabBar; subscribe to `state.notify()`; update `Button.disabled` and `Button.opacity` on each state change.

---

### RunScreen

| Boundary | Detail |
|----------|--------|
| Responsibility | Live matplotlib A/B position plot, cycle status, progress bar, operation log, Start/Pause/Go-to-Rest/E-STOP |
| Exposes | `start_cycle()`, `pause_cycle()`, `go_to_rest()` — all submit to `jobs` |
| Communicates with | `GalilController` (via jobs), `MachineState` (subscribes for `pos`, `cycle_running`, `cycle_progress`), `DMCApp.e_stop()` (E-STOP delegates to app-level) |

**Matplotlib integration — the only non-trivial coupling:**

```python
from kivy_garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib.pyplot as plt

class RunScreen(Screen):
    def on_kv_post(self, *_):
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvasKivyAgg(self.fig)
        self.ids.plot_container.add_widget(self.canvas)
        self._unsub = self.state.subscribe(self._on_state_change)

    def _on_state_change(self, state):
        # Always called on main thread (via Clock.schedule_once in poll loop)
        self._plot_buf_x.append(state.pos["A"])
        self._plot_buf_y.append(state.pos["B"])
        if len(self._plot_buf_x) > 500:
            self._plot_buf_x = self._plot_buf_x[-500:]
            self._plot_buf_y = self._plot_buf_y[-500:]
        self.ax.clear()
        self.ax.plot(self._plot_buf_x, self._plot_buf_y, color='orange')
        self.canvas.draw_idle()   # thread-safe Matplotlib refresh
```

**Key constraint:** `canvas.draw_idle()` must be called on the main thread. Since `MachineState.notify()` is called from `Clock.schedule_once()` (see `_poll_controller` in main.py), the callback is already on the main thread. The polling loop (currently commented out) must be re-enabled and tuned to ~100ms interval for smooth plotting without overloading the Pi.

---

### Machine-Type Screen Sets

**Pattern:** Each machine type gets its own screen name prefix. ScreenManager loads all three sets; `TabBar` and navigation only expose the set matching `state.machine_type`.

```
flat_grind_run       → RunScreen variant for 4-axis flat
flat_grind_axes      → AxesSetupScreen for A/B/C/D
convex_grind_run     → RunScreen variant for 4-axis convex
convex_grind_axes    → AxesSetupScreen for A/B/C/D
serration_run        → existing SerratedKnifeScreen (RUN tab adapted)
serration_axes       → AxesSetupScreen for A/B/C
```

**Alternative:** A single `RunScreen` class with a `machine_type` property that conditionally renders the correct plot and button set. This is simpler — prefer this unless the per-type differences are large. The serration screen is already divergent enough to keep separate.

**Recommendation:** Single `RunScreen` + single `AxesSetupScreen` with machine-type-aware rendering. Only the serration screen stays as its own class (it already exists and has complex custom layout).

---

### CSV Profile System

| Boundary | Detail |
|----------|--------|
| Responsibility | Import: parse CSV of `{dmc_array_name: [values]}`, send to controller. Export: read current arrays, write CSV |
| Exposes | `ProfileManager.import_csv(path)`, `ProfileManager.export_csv(path)` |
| Communicates with | `GalilController.download_array()` (import), `GalilController.upload_array_auto()` (export), `ParametersScreen` (triggers import/export) |
| Does NOT do | UI file dialogs. On Pi, file path is fixed (e.g., `/home/pi/profiles/`). On Windows, use `plyer.filechooser` or `tkinter.filedialog` via a conditional import |

---

### Kiosk Mode (Pi Deployment)

Kiosk mode is a systemd + X11 configuration concern, not a Python/Kivy code concern. The app itself needs only two things:

1. `Config.set('graphics', 'fullscreen', 'auto')` and `Config.set('graphics', 'borderless', '1')` in a Pi-specific config path (detect via `platform.machine()` or an env var like `DMC_KIOSK=1`).
2. The operator role must not surface any file manager, terminal, or browser access. Since the app runs full-screen with no desktop visible, this is handled by the OS-level kiosk setup, not by the application code.

**Pi kiosk systemd unit (reference, not code to write):**
- `/etc/systemd/system/dmcgui.service` → `ExecStart=python -m dmccodegui.main`
- X11 auto-login + `openbox` with single autostart entry pointing to the service
- `xset s off && xset -dpms` to prevent screensaver

---

## Data Flow

```
Controller HW
    │  (gclib GCommand/GArrayUpload/GArrayDownload)
    ▼
GalilController           ← lives on background thread (jobs.submit)
    │  returns Python types (str, float, List[float])
    ▼
Screen callback           ← posted to main thread via Clock.schedule_once
    │  writes to
    ▼
MachineState              ← single mutable object, main thread only
    │  calls notify() → iterates _listeners
    ▼
Subscribed Screens/Widgets ← receive state, update their Kivy properties
    │
    ├──► TabBar           → show/hide tabs based on state.role
    ├──► RunScreen        → update plot + progress bar
    ├──► BannerLabel      → app.banner_text (separate StringProperty path)
    └──► Any other screen currently visible
```

**Auth flow:**
```
Operator taps restricted tab
    │
    ▼
TabBar.on_tab_press()     → calls PinOverlay.show(reason, on_success_cb)
    │
    ▼
PinOverlay                → collects digit taps → calls AuthManager.validate_pin(pin)
    │  on success
    ▼
AuthManager               → sets state.role, state.user_id → state.notify()
    │
    ▼
MachineState.notify()     → TabBar re-renders (tabs unlock), ScreenManager navigates
```

**Profile import flow:**
```
Operator taps "Import Profile"
    │
    ▼
ParametersScreen          → shows file picker (platform-conditional)
    │
    ▼
ProfileManager.import_csv(path)  → parses CSV on main thread (fast, no I/O concern)
    │  for each array:
    ▼
jobs.submit(controller.download_array(...))  → background thread
    │  on complete:
    ▼
Clock.schedule_once → ParametersScreen.refresh()
```

---

## Build Order (Phase Dependencies)

The dependency graph drives recommended phase sequencing:

```
Phase 1: Auth + MachineState extension
    ↓  (all other features depend on role being in state)
Phase 2: TabBar + navigation refactor
    ↓  (RunScreen and other new screens need proper navigation to land in)
Phase 3: RunScreen + live plot
    ↓  (requires poll loop + state.pos flowing correctly)
Phase 4: AxesSetupScreen (unified jog/teach)
    │   (can parallel-track with Phase 3 — independent screen)
Phase 5: ParametersScreen + CSV profiles
    │   (independent of RunScreen)
Phase 6: Machine-type differentiation (screen sets per type)
    │   (requires all screens to exist first)
Phase 7: Admin screen (user management)
    │   (requires Auth to be solid)
Phase 8: Pi kiosk packaging + SD card image
    ↓  (last — packaging after features are stable)
```

**Earliest phases that can be parallelized:**
- Phase 3 (RunScreen) and Phase 4 (AxesSetupScreen) have no dependency on each other.
- Phase 5 (CSV) and Phase 7 (Admin) can start as soon as Phase 1 (Auth) is done.

---

## Patterns to Follow

### Pattern 1: Screen as Passive State Consumer

Every screen subscribes to `MachineState` in `on_kv_post` or `on_pre_enter`, unsubscribes in `on_leave`. Screens never call each other directly — they write to state and let other screens react.

```python
def on_pre_enter(self, *_):
    self._unsub = self.state.subscribe(
        lambda s: Clock.schedule_once(lambda *_: self._sync(s))
    )

def on_leave(self, *_):
    if self._unsub:
        self._unsub()
        self._unsub = None
```

This pattern already exists in `SetupScreen` — apply it consistently to all new screens.

### Pattern 2: Role Gate as Decorator

Wrap restricted methods with a role check that triggers PIN overlay instead of silently failing.

```python
def require_role(min_role: Role):
    def decorator(fn):
        def wrapper(self, *args, **kwargs):
            if self.state.role.value < min_role.value:
                App.get_running_app().pin_overlay.show(
                    reason=f"Requires {min_role.name} access",
                    on_success=lambda role: fn(self, *args, **kwargs)
                )
                return
            return fn(self, *args, **kwargs)
        return wrapper
    return decorator

# Usage:
class ParametersScreen(Screen):
    @require_role(Role.SETUP)
    def save_parameter(self, key, value):
        ...
```

### Pattern 3: Polling Loop for Live Plot

Re-enable the commented-out `_poll_controller` in `main.py`, post results to `MachineState`, let `RunScreen` subscribe. Do not have `RunScreen` poll directly.

```python
# In DMCApp:
self._poll_cancel = jobs.schedule(0.1, self._poll_controller)  # 100ms = 10 Hz

def _poll_controller(self):
    if not self.controller.is_connected():
        return
    st = self.controller.read_status()
    pos = st.get("pos", {})
    Clock.schedule_once(lambda *_: self.state.update_status(pos=pos, ...))
```

10 Hz is sufficient for a position plot and safe for the Pi's single gclib connection. Do not exceed 20 Hz — gclib does not support concurrent calls and the FIFO queue will back up.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Multiple Background Threads Calling gclib

**What goes wrong:** `jobs.JobThread` is a single FIFO worker. If a screen starts its own thread for polling, and another screen submits a command, they race on the shared `globalDMC` handle.

**Why bad:** gclib's `py()` handle is not thread-safe. Concurrent `GCommand` calls produce corrupted responses or connection drops.

**Instead:** All controller I/O routes through `jobs.submit()`. One worker thread, one gclib handle, no exceptions.

---

### Anti-Pattern 2: Storing Role in a Screen Property

**What goes wrong:** Role stored in `some_screen.current_role` is invisible to other screens. TabBar can't react to it.

**Why bad:** Requires explicit cross-screen communication; screens become coupled.

**Instead:** Store role exclusively in `MachineState.role`. Every component that cares subscribes to state.

---

### Anti-Pattern 3: Calling canvas.draw() from a Background Thread

**What goes wrong:** `FigureCanvasKivyAgg.draw()` called from the jobs thread triggers OpenGL calls off the main thread on some platforms, causing crashes or blank canvases.

**Why bad:** Kivy's GL context is main-thread-only. matplotlib's canvas is a Kivy widget.

**Instead:** Update plot data in the main-thread `MachineState` subscriber, then call `canvas.draw_idle()`. `draw_idle()` schedules the redraw safely on the next Kivy frame.

---

### Anti-Pattern 4: Loading All Screen KV Files Regardless of Machine Type

**What goes wrong:** Three full screen sets (flat, convex, serration) all loaded into the ScreenManager simultaneously adds startup time and memory overhead on the Pi.

**Why bad:** Pi 4 has 4GB RAM so this is not a crisis, but unnecessary widget trees cause slower `on_kv_post` chains.

**Instead:** Load only the KV files for the active machine type. `MachineConfig` drives which KV files are included in `KV_FILES`. Machine type is set at deploy time (env var or first-run config), not at runtime.

---

### Anti-Pattern 5: PIN Overlay as a Screen

**What goes wrong:** Pushing a PIN screen onto ScreenManager means every screen transition that requires auth adds to navigation history. Back-navigation bypasses auth.

**Why bad:** Operators can press back to skip authentication.

**Instead:** Use `ModalView` (as described in PinOverlay section above). ModalView has no navigation history. Dismissing without correct PIN leaves the operator exactly where they were.

---

## Scalability Considerations

This is a closed embedded system. Scalability in the traditional sense does not apply. The relevant constraints are:

| Concern | Pi 4 Reality | Mitigation |
|---------|-------------|------------|
| Poll rate | 10 Hz saturates gclib on a busy machine | Cap at 10 Hz; pause poll during array upload |
| Plot buffer | 10 Hz x 60s = 600 points; matplotlib redraws full canvas | Cap buffer at 500 points (rolling window) |
| Screen memory | 7 screens x KV widget tree | Load only active machine type's KV files |
| Startup time | All KV files parsed at launch | Keep KV file count low; `Builder.load_file` is sequential |
| Touch latency | Kivy default 60 fps render loop | No changes needed; no heavy computation on main thread |

---

## Sources

- Direct codebase analysis: `src/dmccodegui/main.py`, `app_state.py`, `controller.py`, `utils/jobs.py`, `screens/setup.py`, `screens/rest.py`, `screens/serration_knife.py`, `ui/base.kv`, `ui/theme.kv`
- Kivy ModalView pattern: training data (HIGH confidence — ModalView API is stable)
- `FigureCanvasKivyAgg` + `draw_idle()` pattern: training data (MEDIUM confidence — verify kivy-garden.matplotlib version against Pi Python environment)
- gclib thread safety: training data + Galil documentation (HIGH confidence — single-handle constraint is documented in gclib API)
- Raspberry Pi kiosk mode (systemd + openbox): training data (MEDIUM confidence — verify against current Raspberry Pi OS Bookworm; the `lightdm` vs `labwc` Wayland transition in Pi OS may require different approach)
