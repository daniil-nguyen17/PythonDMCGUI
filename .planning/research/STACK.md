# Stack Research

**Domain:** Per-machine-type Kivy screen management (v3.0 Multi-Machine HMI refactor)
**Researched:** 2026-04-11
**Confidence:** HIGH — Kivy internals verified from Builder source (`kivy/lang/builder.py`); ScreenManager API verified from official 2.3.1 docs; on_pre_enter bug confirmed from GitHub issue tracker (November 2023).

---

## Scope: What This Research Covers

The existing validated stack (Python 3.10+, Kivy 2.2+, gclib, matplotlib, kivy_matplotlib_widget, JobThread, MachineState, machine_config.py, auth, tab bar) does NOT change. This document covers only the patterns needed to refactor the single-screen-set into per-machine-type screen sets.

**Do not change:** Controller comms, auth flow, tab bar, status bar, machine_config.py registry, CSV profiles, poll architecture, theme, gclib threading discipline.

---

## Core Pattern Decision: Static Load, Python-Side Type Routing

**Recommended approach: load ALL machine-type kv files at startup, instantiate all screen classes at startup, swap which screens are registered in the ScreenManager when machine type changes.**

This is the only approach that works reliably in Kivy. Do NOT attempt runtime `Builder.unload_file()` + reload to hot-swap kv rules when machine type changes.

Why unload/reload fails:
- `Builder.unload_file()` is documented explicitly: *"This will not remove rules or templates already applied/used on current widgets. It will only effect the next widgets creation or template invocation."* Already-instantiated screens keep their existing layout regardless of unloading.
- The `_match_name_cache` is cleared by `unload_file()`, which invalidates style lookups for currently rendered widgets — causing visual inconsistencies on Pi where repaint is slower.
- Machine type changes are infrequent (once per physical deployment, or once per Setup session). Holding all three screen sets in memory is trivial (a few hundred widgets) versus the complexity of dynamic kv swapping.

---

## Recommended Stack (new patterns only)

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `kivy.uix.screenmanager.ScreenManager` | Kivy 2.2+ (existing) | Holds the active machine's screen set | `add_widget` / `remove_widget` are safe at runtime; `has_screen` guards against duplicate-name exceptions; `screens` list is the source of truth |
| Python base class inheritance (`base_screens.py`) | Python 3.10+ (existing) | Shared controller-wiring logic, lifecycle hooks, jog logic | Avoids copy-pasting 80% identical behavior across three machine types; kv handles layout per-type, Python base class handles behavior |
| `Builder.load_file()` — one call per machine kv file | Kivy 2.2+ (existing API) | Load all machine-type kv layouts at startup | All nine machine kv files loaded once in `KV_FILES`; each file defines a distinct class name (`<FlatGrindRunScreen>:` etc.); no collision possible |

### Supporting Patterns

| Pattern | Purpose | When to Use |
|---------|---------|-------------|
| `sm.add_widget(screen)` | Register a screen with the ScreenManager | Called once per screen instance at startup or on machine type swap |
| `sm.remove_widget(screen)` | De-register a screen from the ScreenManager | Called during machine type swap, before adding new set |
| `sm.has_screen(name)` | Guard before `add_widget` | Always check before adding — `add_widget` raises `ScreenManagerException` on duplicate name |
| `sm.get_screen(name)` | Access a specific screen instance | Used during dependency injection (controller, state) after screen set is added |
| `on_pre_enter` defined in Python base class (not kv) | Refresh positions/params when tab is entered | Avoids the Kivy first-screen bug (see Pitfalls / Version Compatibility) |
| Screen name resolver function | Translate logical tab name ('run') to active machine screen name ('flat_run') | Tab bar uses logical names; resolver bridges to actual ScreenManager names |

---

## Directory Layout

```
src/dmccodegui/
  screens/
    base_screens.py           # BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen
    flat_grind/
      __init__.py
      run.py                  # FlatGrindRunScreen(BaseRunScreen)
      axes_setup.py           # FlatGrindAxesSetupScreen(BaseAxesSetupScreen)
      parameters.py           # FlatGrindParametersScreen(BaseParametersScreen)
    serration/
      __init__.py
      run.py                  # SerrationRunScreen(BaseRunScreen)
      axes_setup.py           # SerrationAxesSetupScreen(BaseAxesSetupScreen)
      parameters.py           # SerrationParametersScreen(BaseParametersScreen)
    convex/
      __init__.py
      run.py                  # ConvexRunScreen(BaseRunScreen)
      axes_setup.py           # ConvexAxesSetupScreen(BaseAxesSetupScreen)
      parameters.py           # ConvexParametersScreen(BaseParametersScreen)
  ui/
    flat_grind/
      run.kv                  # <FlatGrindRunScreen>: layout
      axes_setup.kv           # <FlatGrindAxesSetupScreen>: layout
      parameters.kv           # <FlatGrindParametersScreen>: layout
    serration/
      run.kv                  # <SerrationRunScreen>: layout
      axes_setup.kv
      parameters.kv
    convex/
      run.kv                  # <ConvexRunScreen>: layout
      axes_setup.kv
      parameters.kv
    # Shared kv files stay at ui/ root (unchanged):
    theme.kv, pin_overlay.kv, status_bar.kv, tab_bar.kv,
    setup.kv, profiles.kv, diagnostics.kv, users.kv, base.kv
```

---

## Screen Name Convention

Each machine type's screens use namespaced name strings in the ScreenManager:

```python
# Flat Grind
FlatGrindRunScreen(name='flat_run')
FlatGrindAxesSetupScreen(name='flat_axes')
FlatGrindParametersScreen(name='flat_params')

# Serration
SerrationRunScreen(name='serration_run')
SerrationAxesSetupScreen(name='serration_axes')
SerrationParametersScreen(name='serration_params')

# Convex
ConvexRunScreen(name='convex_run')
ConvexAxesSetupScreen(name='convex_axes')
ConvexParametersScreen(name='convex_params')
```

Tab bar continues to use logical names ('run', 'axes_setup', 'parameters'). A screen resolver in DMCApp translates logical name to the active machine's screen name:

```python
_SCREEN_MAP = {
    "4-Axes Flat Grind":      {"run": "flat_run",       "axes_setup": "flat_axes",       "parameters": "flat_params"},
    "3-Axes Serration Grind": {"run": "serration_run",  "axes_setup": "serration_axes",  "parameters": "serration_params"},
    "4-Axes Convex Grind":    {"run": "convex_run",     "axes_setup": "convex_axes",     "parameters": "convex_params"},
}

def resolve_screen(logical_name: str) -> str:
    mtype = mc.get_active_type()
    return _SCREEN_MAP.get(mtype, {}).get(logical_name, logical_name)
```

The tab bar's `bind(current_tab=...)` lambda passes through `resolve_screen()` before setting `sm.current`:

```python
tab_bar.bind(current_tab=lambda inst, val: setattr(sm, 'current', resolve_screen(val)))
```

---

## KV Loading Pattern

### Updated KV_FILES list in main.py

```python
KV_FILES = [
    # Shared styles — always first
    "ui/theme.kv",
    "ui/pin_overlay.kv",
    "ui/status_bar.kv",
    "ui/tab_bar.kv",
    "ui/setup.kv",
    "ui/profiles.kv",
    "ui/diagnostics.kv",
    "ui/users.kv",

    # Per-machine layouts — all loaded at startup (distinct class names, no collision)
    "ui/flat_grind/run.kv",
    "ui/flat_grind/axes_setup.kv",
    "ui/flat_grind/parameters.kv",

    "ui/serration/run.kv",
    "ui/serration/axes_setup.kv",
    "ui/serration/parameters.kv",

    "ui/convex/run.kv",
    "ui/convex/axes_setup.kv",
    "ui/convex/parameters.kv",

    # Root layout — always last
    "ui/base.kv",
]
```

### Why all at startup, not lazy

`Builder.load_file()` must run on the UI thread and is not safe to call from a jobs worker thread. Lazy loading (triggered by machine type selection after controller connect) would require `Clock.schedule_once()` chaining to defer navigation until kv is loaded, and creates a window where the user can navigate to a screen before its rules are applied. Loading all nine machine kv files at startup avoids this entirely. Parse time for nine small kv files is under 100ms on Pi 4.

### Duplicate class name behavior — verified from Builder source

`Builder.match_rule_name()` collects all matching rules in load order from its internal `self.rules` list via `rules.extend(parser.rules)`. If two kv files both define `<RunScreen>:`, both rule sets are applied to every `RunScreen` instance — additive, not replacement. This is why each machine type's screen must use a **distinct class name** (`FlatGrindRunScreen`, `SerrationRunScreen`, `ConvexRunScreen`). Do not reuse the name `RunScreen` across machine kv files.

---

## Base Class Pattern

### base_screens.py (Python)

```python
from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty

class BaseRunScreen(Screen):
    """Shared controller wiring and lifecycle for all Run screen variants."""
    controller = ObjectProperty(None, allownone=True)
    state      = ObjectProperty(None, allownone=True)

    # Defined in Python — NOT in kv — to avoid Kivy first-screen on_pre_enter bug
    def on_pre_enter(self, *args):
        if self.state:
            self._refresh_from_state(self.state)

    def on_pre_leave(self, *args):
        self._stop_pos_poll()
        self._stop_mg_reader()

    def _refresh_from_state(self, state): pass  # override in subclass
    def _stop_pos_poll(self): pass               # override in subclass
    def _stop_mg_reader(self): pass              # override in subclass


class BaseAxesSetupScreen(Screen):
    controller = ObjectProperty(None, allownone=True)
    state      = ObjectProperty(None, allownone=True)

    def on_pre_enter(self, *args):
        self._rebuild_axis_rows()
        self._read_positions()

    def _rebuild_axis_rows(self): pass
    def _read_positions(self): pass


class BaseParametersScreen(Screen):
    controller = ObjectProperty(None, allownone=True)
    state      = ObjectProperty(None, allownone=True)

    def on_pre_enter(self, *args):
        self._load_param_defs()

    def _load_param_defs(self): pass
```

### Machine-specific subclass (Python)

```python
# screens/flat_grind/run.py
from ..base_screens import BaseRunScreen

class FlatGrindRunScreen(BaseRunScreen):
    # All Flat Grind run logic here — lifted from existing RunScreen
    # IDs come from ui/flat_grind/run.kv <FlatGrindRunScreen>: block

    def _refresh_from_state(self, state):
        # Flat-grind-specific state sync (4 axes, delta-C bar chart, etc.)
        ...

    def _stop_pos_poll(self):
        # Cancel the 10 Hz poll clock event
        ...
```

### Machine-specific kv (layout only)

```kv
# ui/flat_grind/run.kv
<FlatGrindRunScreen>:
    BoxLayout:
        orientation: 'vertical'
        # Full Flat Grind run layout
        # id: references used by Python code defined here
```

**Rule:** Do NOT define `on_pre_enter:` handlers in kv files. Define lifecycle hooks in Python only. (See Version Compatibility for the bug reference.)

---

## Updated base.kv — Remove Inline Machine Screens

Machine screens are no longer declared in the ScreenManager kv block. They are injected by `DMCApp.build()` via `_load_screen_set()`. The shared non-machine screens (setup, profiles, diagnostics, users) can remain in kv.

```kv
# base.kv (updated)
<RootLayout@BoxLayout>:
    ...
    ScreenManager:
        id: sm
        transition: NoTransition()
        SetupScreen:
            name: 'setup'
        ProfilesScreen:
            name: 'profiles'
        DiagnosticsScreen:
            name: 'diagnostics'
        UsersScreen:
            name: 'users'
        # Machine screens added by DMCApp.build() via _load_screen_set()
```

---

## DMCApp Screen Loader Pattern

```python
# In DMCApp — pre-instantiate all screen sets at build time
def _build_all_screens(self):
    """Instantiate all machine screen sets. Called once in build()."""
    from .screens.flat_grind.run import FlatGrindRunScreen
    from .screens.flat_grind.axes_setup import FlatGrindAxesSetupScreen
    from .screens.flat_grind.parameters import FlatGrindParametersScreen
    from .screens.serration.run import SerrationRunScreen
    # ... etc.

    self._screen_sets = {
        "4-Axes Flat Grind": {
            "run":        FlatGrindRunScreen(name='flat_run'),
            "axes_setup": FlatGrindAxesSetupScreen(name='flat_axes'),
            "parameters": FlatGrindParametersScreen(name='flat_params'),
        },
        "3-Axes Serration Grind": {
            "run":        SerrationRunScreen(name='serration_run'),
            "axes_setup": SerrationAxesSetupScreen(name='serration_axes'),
            "parameters": SerrationParametersScreen(name='serration_params'),
        },
        "4-Axes Convex Grind": {
            "run":        ConvexRunScreen(name='convex_run'),
            "axes_setup": ConvexAxesSetupScreen(name='convex_axes'),
            "parameters": ConvexParametersScreen(name='convex_params'),
        },
    }

def _load_screen_set(self, sm, mtype):
    """Add the screen set for mtype to sm and inject dependencies."""
    for screen in self._screen_sets[mtype].values():
        if not sm.has_screen(screen.name):
            sm.add_widget(screen)
        screen.controller = self.controller
        screen.state = self.state

def _swap_screen_set(self, sm, old_mtype, new_mtype):
    """Remove old machine screens, add new set. Called on machine type change."""
    # Navigate away from machine screens before removal
    if sm.current not in ('setup', 'profiles', 'diagnostics', 'users'):
        sm.current = 'setup'
    # Remove old machine screens
    for screen in self._screen_sets[old_mtype].values():
        if sm.has_screen(screen.name):
            sm.remove_widget(screen)
    # Add new machine screens
    self._load_screen_set(sm, new_mtype)
```

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Distinct Python class per machine type (`FlatGrindRunScreen`) | Single `RunScreen` class with runtime widget add/remove inside the screen | Single class fighting Kivy's widget tree; IDs break when children are added/removed dynamically; worse than the problem being solved |
| All kv files loaded at startup | Lazy-load kv on first machine type selection | Requires thread-safe deferred loading; first-navigation delay on Pi; `Clock.schedule_once` chaining adds complexity for negligible memory saving |
| `on_pre_enter` in Python base class | `on_pre_enter` in kv per screen | Kivy bug #2565 (unresolved as of 2.2.1, November 2023): first screen silently skips `on_pre_enter`/`on_enter` when defined in kv |
| `sm.add_widget` / `sm.remove_widget` for screen set swap | `Builder.unload_file()` + reload to hot-swap kv rules | `unload_file` explicitly documented as not affecting already-instantiated widgets; kv rules on live screens are baked in at instantiation time; no visual effect on the running app |
| Tab bar logical name + resolver function | Tab bar uses machine-specific names directly | Tab bar is shared infrastructure; coupling it to machine type knowledge breaks the clean separation already established |
| `sm.has_screen()` guard before `add_widget` | Unchecked `sm.add_widget()` | `add_widget` raises `ScreenManagerException` on duplicate name — the guard is mandatory |
| Pre-instantiate all screen sets at build() time | Instantiate on-demand when machine type is first selected | On-demand instantiation happens after kv is loaded but `Factory.RootLayout()` already rendered; timing is tricky. Pre-instantiation at build() is deterministic. |

---

## What NOT to Change

| Do Not Touch | Why |
|--------------|-----|
| `KV_FILES` load order (theme.kv first, base.kv last) | Theme rules must precede widget rules; base.kv must be last because `RootLayout` references all screen class names that must be registered by the time it is parsed |
| `jobs.submit()` for all gclib I/O | Must stay in all new screen subclasses — no direct controller calls on the UI thread |
| `Clock.schedule_once()` for all UI updates from background threads | Required in all new screen subclasses — Kivy widget mutations are not thread-safe |
| `MachineState.subscribe()` / `state.notify()` observer pattern | All screens hook here for state updates; new screens must follow the same pattern |
| `machine_config.py` registry | Tempting to add screen class names here, but wrong — screen management belongs in DMCApp, not in the data registry |
| `LabelBase.register('Roboto', ...)` + `Config.set` before all Kivy imports | Must stay at top of main.py; new screen modules must never import Kivy at module level in a way that runs before main.py initializes |
| `NoTransition()` on ScreenManager | Animated transitions add latency on Pi and are listed as Out of Scope in PROJECT.md |

---

## Version Compatibility

| Package | Version | Notes |
|---------|---------|-------|
| Kivy | 2.2+ | `ScreenManager.add_widget` signature: the parameter was renamed from `screen` to `widget` in 2.1.0. Use positional argument to stay compatible across versions. |
| Kivy | 2.2+ | `Builder.unload_file()` clears `_match_name_cache` — safe to call but only affects future widget instantiations, not existing ones. Confirmed from builder source. |
| Kivy | 2.2 through 2.3.1 | `on_pre_enter` and `on_enter` defined in kv do not fire for the first screen added to a ScreenManager (GitHub issue #2565, confirmed unresolved November 2023). Define all lifecycle hooks in Python. |
| Python | 3.10+ | No change. |

---

## Installation

No new packages required. All patterns use existing Kivy 2.2+ API and stdlib Python.

```bash
# Verify Kivy version
python -c "import kivy; print(kivy.__version__)"
# Expected: 2.2.x or higher

# No pip installs needed for this milestone
```

---

## Sources

- [Kivy ScreenManager API — 2.3.1](https://kivy.org/doc/stable/api-kivy.uix.screenmanager.html) — `add_widget`, `remove_widget`, `has_screen`, `get_screen`, `screen_names`, `screens`, lifecycle events (HIGH confidence)
- [Kivy Builder source — 2.3.1](https://kivy.org/doc/stable/_modules/kivy/lang/builder.html) — `match_rule_name` implementation (rules additive across files), `unload_file` implementation and documented limitation (HIGH confidence — read from source)
- [Kivy Builder API — 2.3.1](https://kivy.org/doc/stable/api-kivy.lang.builder.html) — `load_file`, `unload_file`, `rulesonly` parameter documentation (HIGH confidence)
- [GitHub Issue #2565 — on_pre_enter not fired for kv-declared first screen](https://github.com/kivy/kivy/issues/2565) — confirmed unresolved in Kivy 2.2.1, November 2023; Python-side definition is the established workaround (HIGH confidence)
- [Kivy kv language guide — 2.3.1](https://kivy.org/doc/stable/guide/lang.html) — dynamic class inheritance `<ClassName@BaseClass>:`, multi-class shared rules `<A,B>:` syntax (HIGH confidence)
- Existing codebase `main.py`, `screens/__init__.py`, `ui/base.kv`, `machine_config.py` — current patterns confirmed from direct inspection (HIGH confidence)

---

*Stack research for: DMC Grinding GUI — v3.0 Multi-Machine screen architecture*
*Researched: 2026-04-11*
