# Phase 20: Screen Registry and Loader - Research

**Researched:** 2026-04-11
**Domain:** Kivy ScreenManager dynamic screen loading, importlib, Python module lifecycle
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Machine detection:**
- Local config only: settings.json `machine_type` determines which screens to load — no controller query for initial detection
- Screen set loaded at app startup during `build()`, before any connection attempt — screens are ready before ScreenManager renders
- Machine type change requires full app exit: save to settings.json, show "Machine type changed. Please restart the application." message, call cleanup then `App.stop()`. On Pi kiosk, systemd auto-restarts
- Mismatch warning: after connecting, query `machType` DMC variable. If it doesn't match settings.json, show a popup dialog asking operator to pick the correct machine type (with option to change and restart)
- If `machType` variable doesn't exist on controller (query fails or empty), skip check silently — graceful degradation

**Screen swap teardown:**
- Build a `cleanup()` method on base classes even though swap is restart-only — satisfies LOAD-03 and enables clean shutdown
- Teardown order: (1) stop `_pos_poll` thread, (2) stop `_mg_reader` thread, (3) `plt.close(fig)` on run screen, (4) unsubscribe state listeners, (5) `sm.remove_widget(screen)`
- `cleanup()` method on each base class: BaseRunScreen handles threads + figure, BaseAxesSetupScreen/BaseParametersScreen handle setup exit + unsubscribe
- `cleanup()` called both during screen swap AND during normal `App.on_stop()` shutdown — prevents thread-still-running-after-window-close
- Log each cleanup step at INFO level: `[FlatGrindRunScreen] cleanup: stopping pos_poll`, etc. — aids hardware debugging
- Thread stop strategy: set stop flag and don't wait — no blocking the UI thread. Thread finishes current iteration naturally

**Registry shape:**
- Import path strings in `_REGISTRY`: `'screen_classes': {'run': 'dmccodegui.screens.flat_grind.FlatGrindRunScreen', ...}` — avoids circular imports, lightweight
- Registry also stores `load_kv` path: `'load_kv': 'dmccodegui.screens.flat_grind.load_kv'` — loader imports and calls before resolving screen classes. Explicit, no convention magic
- Canonical screen names as keys: `{'run': '...', 'axes_setup': '...', 'parameters': '...'}` — matches ScreenManager `name=` values, tab bar and navigation unchanged
- Every machine type package follows identical `load_kv()` + class export pattern established by flat_grind in Phase 19

**First-launch UX:**
- Blocking picker popup when no machine type is configured (first launch) — operator must pick to proceed
- If settings.json contains unknown machine type string (corrupted/old), treat as unconfigured — show first-launch picker (self-healing)
- After first-launch pick: continue directly into the app without restart — nothing to tear down yet
- First-launch picker shows machine type names only ("4-Axes Flat Grind", etc.) — operators know their machine

**Error handling:**
- If screen loading fails (bad import, missing KV file): show error popup with exception message, then exit. Running without screens makes no sense
- Unknown machine type in settings.json: treated as unconfigured, shows first-launch picker

**Tab bar integration:**
- Same 5 tabs for all machine types: Run, Axes Setup, Parameters, Profiles, Users — navigation is identical across machines
- Status bar shows active machine type (already has tappable label for picker) — no tab bar changes
- Profiles and Users stay in base.kv as machine-agnostic screens — only Run, Axes Setup, Parameters go through the registry

### Claude's Discretion
- Exact `_load_machine_screens()` implementation details
- importlib resolution strategy for dotted path strings
- Mismatch popup dialog layout and wording
- Test structure for verifying screen loading and cleanup

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LOAD-01 | machine_config._REGISTRY includes screen_classes mapping machine type to its screen class names | Registry shape decided: import path strings + load_kv path. Add `screen_classes` and `load_kv` keys to existing `_REGISTRY` dict entries |
| LOAD-02 | main.py `_load_machine_screens()` dynamically adds/removes machine-specific screens under canonical names | importlib.import_module() pattern resolves dotted path strings; sm.add_widget/remove_widget with name= is the established Kivy swap mechanism |
| LOAD-03 | Screen swap stops background threads and closes matplotlib figure before removing outgoing screens | `cleanup()` on base classes; teardown order is locked; _stop_pos_poll / _stop_mg_reader already exist on FlatGrindRunScreen; plt.close(fig) cleans matplotlib handle |
| LOAD-04 | App detects machine type on connect (controller variable + local config) and loads correct screen set | machType DMC variable query follows HMI one-shot read pattern; mismatch popup reuses existing `_show_machine_type_picker()`; silently skip if query fails |
</phase_requirements>

---

## Summary

Phase 20 wires the machine_config registry to the Kivy ScreenManager so the app loads the correct per-machine screens at startup and cleans up properly on exit or machine type change. All architectural decisions are locked in CONTEXT.md; research confirms every design choice is compatible with the existing codebase.

The core technical work has three parts: (1) extend `_REGISTRY` in machine_config.py with `screen_classes` and `load_kv` import-path strings, (2) replace the hard-coded flat_grind import in `main.py build()` with a registry-driven `_load_machine_screens()` that uses importlib and `sm.add_widget/remove_widget`, and (3) add `cleanup()` methods to the three base classes and wire them into `App.on_stop()`.

The existing codebase already has all the plumbing needed: `_stop_pos_poll()` and `_stop_mg_reader()` exist on `FlatGrindRunScreen`, `_state_unsub` unsubscription is in the base class `on_leave()` hooks, `_fig` is the matplotlib figure handle on RunScreen, and the existing `_show_machine_type_picker()` in main.py is reusable for the mismatch popup. The main.py `on_stop()` already manually calls `_stop_pos_poll()` and `_stop_mg_reader()` — Phase 20 replaces that ad-hoc code with `cleanup()` delegation.

**Primary recommendation:** Work in three well-scoped tasks — registry extension, loader + build() refactor, cleanup() base class methods — each testable independently without a live controller.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| importlib | stdlib | Resolve dotted import-path strings to classes | Zero deps; safe for deferred imports; used by Kivy Factory internally |
| kivy.uix.screenmanager.ScreenManager | Kivy 2.x | add_widget / remove_widget for screen swap | The only Kivy-supported swap mechanism (Builder.unload_file rejected in STATE.md) |
| matplotlib.pyplot | already in project | `plt.close(fig)` to destroy figure handle | Already imported in run.py; closes figure and releases memory |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| logging (stdlib) | stdlib | INFO-level cleanup step logging | Locked decision: log each cleanup step |
| kivy.uix.modalview.ModalView | Kivy 2.x | Mismatch warning popup | Already used by existing `_show_machine_type_picker()` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| importlib dotted path | Direct import at top of main.py | Direct import causes circular import at load time; dotted path defers import until build() runs |
| sm.add_widget/remove_widget | Builder.unload_file + re-load | Builder.unload_file does not affect instantiated widgets — explicitly rejected in STATE.md |

**Installation:**
No new packages required. All dependencies already present in the project.

## Architecture Patterns

### Recommended Project Structure

No new files or directories needed for the registry and loader. The changes land in:

```
src/dmccodegui/
├── machine_config.py          # add screen_classes + load_kv to _REGISTRY
├── main.py                    # replace hard-coded load_kv import; add _load_machine_screens()
│                              # wire _on_connect_from_setup → machType query
│                              # replace ad-hoc on_stop cleanup with cleanup() calls
└── screens/
    └── base.py                # add cleanup() to BaseRunScreen, BaseAxesSetupScreen,
                               # BaseParametersScreen
```

### Pattern 1: Registry Import Path Strings

**What:** Each registry entry stores the fully-qualified dotted path to the `load_kv` callable and each screen class as a string. No import happens at module load time.

**When to use:** When you need machine-specific code without creating a circular import at startup.

**Example:**
```python
# machine_config.py — extend _REGISTRY
_REGISTRY = {
    "4-Axes Flat Grind": {
        "axes": ["A", "B", "C", "D"],
        "has_bcomp": False,
        "param_defs": _FLAT_PARAM_DEFS,
        "load_kv": "dmccodegui.screens.flat_grind.load_kv",
        "screen_classes": {
            "run":        "dmccodegui.screens.flat_grind.FlatGrindRunScreen",
            "axes_setup": "dmccodegui.screens.flat_grind.FlatGrindAxesSetupScreen",
            "parameters": "dmccodegui.screens.flat_grind.FlatGrindParametersScreen",
        },
    },
    # "4-Axes Convex Grind" and "3-Axes Serration Grind" get placeholder paths
    # pointing to FlatGrind classes until Phases 21-22 create real classes
}
```

### Pattern 2: importlib Dotted Path Resolution

**What:** `_load_machine_screens()` splits each dotted path at the last `.` — left side is the module, right side is the attribute name. Uses `importlib.import_module()` to load the module and `getattr()` for the attribute.

**When to use:** Any time a string like `"dmccodegui.screens.flat_grind.FlatGrindRunScreen"` must be resolved to the actual class at runtime.

**Example:**
```python
import importlib

def _resolve_dotted(path: str):
    """Resolve 'a.b.c.ClassName' → getattr(import('a.b.c'), 'ClassName')."""
    module_path, attr_name = path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, attr_name)
```

This is HIGH confidence — it is the standard Python pattern for plugin-style dynamic imports and is used by Django's INSTALLED_APPS, Celery task discovery, and Kivy's own Factory.

### Pattern 3: `_load_machine_screens()` in main.py

**What:** Called from `build()` after `mc.init()`. Resolves registry entries, calls `load_kv()`, instantiates screen classes with canonical `name=` values, injects controller/state, and calls `sm.add_widget()`.

**When to use:** Startup screen set selection — not a hot-swap, always called once during build.

**Example sketch:**
```python
def _load_machine_screens(self, sm) -> None:
    mtype = mc.get_active_type()
    entry = mc._REGISTRY[mtype]

    # 1. Load KV files for this machine type
    load_kv_fn = _resolve_dotted(entry["load_kv"])
    load_kv_fn()

    # 2. Instantiate and add screens under canonical names
    for canonical_name, class_path in entry["screen_classes"].items():
        cls = _resolve_dotted(class_path)
        screen = cls(name=canonical_name)
        screen.controller = self.controller
        screen.state = self.state
        sm.add_widget(screen)
```

The `build()` method currently has:
```python
from .screens.flat_grind import load_kv as _load_flat_grind_kv
_load_flat_grind_kv()
```
This hard-coded call is replaced by `_load_machine_screens()`.

`base.kv` currently has `FlatGrindRunScreen`, `FlatGrindAxesSetupScreen`, `FlatGrindParametersScreen` declared directly in the ScreenManager rule. These three must be **removed** from `base.kv` — they are replaced by programmatic `sm.add_widget()` in `_load_machine_screens()`.

### Pattern 4: cleanup() on Base Classes

**What:** A `cleanup()` method added to each base class that performs ordered teardown of resources owned by that class. Called from `App.on_stop()` and from any future machine swap path.

**Teardown order (locked in CONTEXT.md):**
1. `_stop_pos_poll()` — cancel Kivy Clock interval (BaseRunScreen: delegates to FlatGrindRunScreen)
2. `_stop_mg_reader()` — set stop event on background threading.Thread (BaseRunScreen)
3. `plt.close(fig)` — destroy matplotlib figure handle (BaseRunScreen: `if self._fig is not None: plt.close(self._fig); self._fig = None`)
4. Unsubscribe state listeners — call `_state_unsub()` if set (BaseRunScreen)
5. `sm.remove_widget(screen)` — done by caller after cleanup() returns

**Thread stop strategy (locked):** Set stop flag and return — do not block. `_stop_pos_poll()` already cancels the Clock event immediately (no blocking). `_stop_mg_reader()` currently calls `_mg_thread.join(timeout=2.0)` — this MUST be changed to set-flag-only to avoid blocking the UI thread during cleanup.

**Example:**
```python
# In BaseRunScreen
def cleanup(self) -> None:
    """Stop all background resources. Non-blocking — sets flags only."""
    logger.info("[%s] cleanup: stopping pos_poll", self.__class__.__name__)
    if hasattr(self, '_stop_pos_poll'):
        self._stop_pos_poll()

    logger.info("[%s] cleanup: stopping mg_reader", self.__class__.__name__)
    if hasattr(self, '_stop_mg_reader'):
        self._stop_mg_reader()

    logger.info("[%s] cleanup: closing matplotlib figure", self.__class__.__name__)
    fig = getattr(self, '_fig', None)
    if fig is not None:
        import matplotlib.pyplot as plt
        plt.close(fig)
        self._fig = None

    logger.info("[%s] cleanup: unsubscribing state listener", self.__class__.__name__)
    if self._state_unsub is not None:
        self._state_unsub()
        self._state_unsub = None
```

### Pattern 5: machType Mismatch Check

**What:** After connection succeeds (in `_on_connect_from_setup`), submit a background job that queries `machType` from the controller. If the value doesn't match `mc.get_active_type()`, schedule a popup on the main thread. If the query fails, skip silently.

**HMI one-shot pattern (from memory file):** The query is a read-only `MG machType` command — no XQ, no variable write. Returns a numeric value that maps to a machine type. Graceful degradation: any exception or empty response → skip check.

**Example:**
```python
def _check_machine_type_mismatch(self) -> None:
    """Query machType from controller; show mismatch popup if needed."""
    def _do():
        try:
            raw = self.controller.cmd("MG machType").strip()
            ctrl_type = _MACH_TYPE_MAP.get(int(float(raw)), "")
        except Exception:
            return  # graceful degradation — skip check
        config_type = mc.get_active_type()
        if ctrl_type and ctrl_type != config_type:
            Clock.schedule_once(
                lambda *_: self._show_mismatch_popup(ctrl_type, config_type)
            )
    jobs.submit(_do)
```

Note: `machType` numeric-to-string mapping needs to be defined (e.g., `{1: "4-Axes Flat Grind", 2: "3-Axes Serration Grind", 3: "4-Axes Convex Grind"}`). The actual mapping must be verified against the DMC controller program. If the mapping is unknown, skip the mismatch check or compare raw numeric values.

### Anti-Patterns to Avoid

- **Removing base.kv screen entries without removing the hard-coded import in build():** These two changes must happen in the same commit or the app will fail to start (Factory will find no class for the KV rule).
- **Blocking join() in cleanup():** `_stop_mg_reader()` currently calls `self._mg_thread.join(timeout=2.0)`. This must be changed to signal-only (set the event, clear the thread reference, return) when called from `cleanup()`. A join timeout blocks the UI thread and can cause Kivy to hang on close.
- **Calling cleanup() twice:** `_state_unsub` is set to None after first call — second call logs a warning (existing behavior from on_leave). Set all handles to None after cleanup to make it idempotent.
- **Adding machine screens to base.kv instead of programmatically:** The whole point of this phase is moving from KV-declared to Python-instantiated screens. Do not add screen declarations back to base.kv.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Resolve "a.b.c.ClassName" to class | Custom string splitter | `importlib.import_module` + `getattr` | stdlib, handles edge cases, no re-invention |
| Screen swap | Re-parsing KV files | `sm.add_widget` / `sm.remove_widget` | Kivy's supported API; Builder.unload_file explicitly rejected |
| Thread stop guard | Custom atomic flag class | `threading.Event` already used | Already on `_mg_stop_event`; consistent with existing code |
| Settings persistence | Custom file writer | `mc.set_active_type()` | Already writes to settings.json with merge logic |

**Key insight:** The entire loader is 30-40 lines of Python using only stdlib and existing project APIs. No new libraries, no custom frameworks.

## Common Pitfalls

### Pitfall 1: base.kv Still Declares Machine Screens
**What goes wrong:** If `FlatGrindRunScreen`, `FlatGrindAxesSetupScreen`, `FlatGrindParametersScreen` are left in the `ScreenManager` rule in `base.kv`, Kivy instantiates them at `Factory.RootLayout()` time — before `_load_machine_screens()` runs. The programmatic `sm.add_widget()` then tries to add a second screen with the same `name=`, causing a Kivy error or silent duplicate.

**Why it happens:** `base.kv` is loaded before `_load_machine_screens()` in the current `build()` flow.

**How to avoid:** Remove the three machine screen entries from `base.kv`'s ScreenManager rule in the same commit that adds `_load_machine_screens()`.

**Warning signs:** Kivy warning "Screen with name 'run' already exists" in the console; ScreenManager has 2 screens named 'run'.

### Pitfall 2: Circular Import When load_kv() Imports Screen Classes

**What goes wrong:** `flat_grind/__init__.py` imports `FlatGrindRunScreen` at module level (lines 32-34). If `_load_machine_screens()` calls `importlib.import_module("dmccodegui.screens.flat_grind")` before the Kivy Factory is ready, the class import may trigger Builder rules that reference Factory names not yet registered.

**Why it happens:** Phase 19 solved this with deferred KV loading (`load_kv()` called from build()). The same deferral applies here — `load_kv()` from the registry must be called after `Builder.load_file(KV_FILES)` loop completes. Currently the loop runs AFTER `_load_flat_grind_kv()`, so order matters.

**How to avoid:** Call `_load_machine_screens()` (which calls `load_kv()`) BEFORE the `KV_FILES` loop, matching the current `_load_flat_grind_kv()` call position. Verify this ordering in the plan.

**Warning signs:** `FactoryException: Unknown class <FlatGrindRunScreen>` at startup.

### Pitfall 3: `_stop_mg_reader()` Blocks UI Thread in cleanup()

**What goes wrong:** Current `_stop_mg_reader()` calls `self._mg_thread.join(timeout=2.0)`. When called from `cleanup()` on `App.on_stop()`, this blocks the main thread for up to 2 seconds before Kivy can close the window. On Pi kiosk, this can look like a hang.

**Why it happens:** The join was added to ensure clean shutdown in on_leave. For `cleanup()`, the design decision is "set flag and don't wait."

**How to avoid:** In `cleanup()`, call a non-blocking variant: set `_mg_stop_event`, set `_mg_thread = None` without joining. The daemon thread will be killed when the process exits. The existing `_stop_mg_reader()` on `on_leave` can keep its join for normal screen navigation.

**Warning signs:** App appears to hang for 2 seconds on close before exiting.

### Pitfall 4: machType Variable Not Present on Controller

**What goes wrong:** If the DMC controller program does not define `machType`, the `MG machType` command returns an error string or raises a gclib exception. If not caught, this crashes the connection callback.

**Why it happens:** `machType` is a DMC user variable that must exist in the controller program. Early firmware versions may not have it.

**How to avoid:** Wrap the `MG machType` query in a bare `except Exception: return`. The locked decision is graceful degradation — skip the check if query fails.

**Warning signs:** Connection callback crashes; app goes to disconnected state after successful connect.

### Pitfall 5: First-Launch Screen Not Yet Loaded

**What goes wrong:** During first-launch flow, `_show_machine_type_picker()` is called before `_load_machine_screens()`. After the operator picks a machine type, the screens are not yet in the ScreenManager. Navigation to 'run' will fail with "Screen 'run' not found."

**Why it happens:** `build()` calls `_load_machine_screens()` with `mc.is_configured() == False` initially. The screens cannot be loaded until the machine type is known.

**How to avoid:** On first-launch pick: (a) call `_load_machine_screens()` immediately after `mc.set_active_type()`, then (b) inject controller/state into the new screens, then (c) continue to PIN overlay. This is what "continue directly into the app without restart" means — load the screens at that moment.

**Warning signs:** Kivy `ScreenManagerException: No Screen with name 'run'` after first-launch pick.

## Code Examples

### Registry Extension in machine_config.py

```python
# Source: CONTEXT.md locked decision — import path strings
_REGISTRY: Dict[str, Dict] = {
    "4-Axes Flat Grind": {
        "axes": ["A", "B", "C", "D"],
        "has_bcomp": False,
        "param_defs": _FLAT_PARAM_DEFS,
        "load_kv": "dmccodegui.screens.flat_grind.load_kv",
        "screen_classes": {
            "run":        "dmccodegui.screens.flat_grind.FlatGrindRunScreen",
            "axes_setup": "dmccodegui.screens.flat_grind.FlatGrindAxesSetupScreen",
            "parameters": "dmccodegui.screens.flat_grind.FlatGrindParametersScreen",
        },
    },
    "4-Axes Convex Grind": {
        "axes": ["A", "B", "C", "D"],
        "has_bcomp": False,
        "param_defs": _CONVEX_PARAM_DEFS,
        # Phase 22 will replace these with Convex-specific classes
        "load_kv": "dmccodegui.screens.flat_grind.load_kv",
        "screen_classes": {
            "run":        "dmccodegui.screens.flat_grind.FlatGrindRunScreen",
            "axes_setup": "dmccodegui.screens.flat_grind.FlatGrindAxesSetupScreen",
            "parameters": "dmccodegui.screens.flat_grind.FlatGrindParametersScreen",
        },
    },
    "3-Axes Serration Grind": {
        "axes": ["A", "B", "C"],
        "has_bcomp": True,
        "param_defs": _SERRATION_PARAM_DEFS,
        # Phase 21 will replace these with Serration-specific classes
        "load_kv": "dmccodegui.screens.flat_grind.load_kv",
        "screen_classes": {
            "run":        "dmccodegui.screens.flat_grind.FlatGrindRunScreen",
            "axes_setup": "dmccodegui.screens.flat_grind.FlatGrindAxesSetupScreen",
            "parameters": "dmccodegui.screens.flat_grind.FlatGrindParametersScreen",
        },
    },
}
```

Note: Serration and Convex point to flat_grind classes as placeholders until Phases 21-22. This is intentional and noted with TODO comments.

### importlib Helper Function

```python
# Source: Python stdlib importlib docs — standard plugin resolution pattern
import importlib

def _resolve_dotted_path(dotted: str):
    """Resolve 'module.path.ClassName' to the class object.

    Raises ImportError or AttributeError if path is invalid.
    """
    module_path, attr_name = dotted.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, attr_name)
```

### _load_machine_screens() in main.py

```python
def _load_machine_screens(self, sm) -> None:
    """Load and add machine-specific screens to the ScreenManager.

    Resolves screen classes from machine_config._REGISTRY import paths.
    Called from build() before Factory.RootLayout() if configured,
    or after first-launch picker if not yet configured.
    """
    mtype = mc.get_active_type()
    if not mtype:
        return  # unconfigured — first-launch picker will call this after pick

    try:
        entry = mc._REGISTRY[mtype]
        load_kv_fn = _resolve_dotted_path(entry["load_kv"])
        load_kv_fn()

        for canonical_name, class_path in entry["screen_classes"].items():
            cls = _resolve_dotted_path(class_path)
            screen = cls(name=canonical_name)
            screen.controller = self.controller
            screen.state = self.state
            sm.add_widget(screen)

    except Exception as exc:
        # Show error popup then exit — running without screens is not viable
        self._show_load_error_and_exit(exc)
```

### cleanup() on BaseRunScreen

```python
def cleanup(self) -> None:
    """Release all background resources owned by this screen.

    Non-blocking: sets stop flags but does not join threads.
    Safe to call multiple times (idempotent after first call).
    """
    logger.info("[%s] cleanup: stopping pos_poll", self.__class__.__name__)
    if hasattr(self, '_stop_pos_poll') and callable(self._stop_pos_poll):
        self._stop_pos_poll()

    logger.info("[%s] cleanup: stopping mg_reader", self.__class__.__name__)
    # Signal thread stop without joining (avoid blocking UI thread)
    stop_evt = getattr(self, '_mg_stop_event', None)
    if stop_evt is not None:
        stop_evt.set()
    # Clear thread reference — daemon thread exits with the process
    if hasattr(self, '_mg_thread'):
        self._mg_thread = None
    if hasattr(self, '_mg_stop_event'):
        self._mg_stop_event = None

    logger.info("[%s] cleanup: closing matplotlib figure", self.__class__.__name__)
    fig = getattr(self, '_fig', None)
    if fig is not None:
        try:
            import matplotlib.pyplot as plt
            plt.close(fig)
        except Exception:
            pass
        self._fig = None

    logger.info("[%s] cleanup: unsubscribing state listener", self.__class__.__name__)
    if self._state_unsub is not None:
        self._state_unsub()
        self._state_unsub = None
```

### on_stop() Replacement in main.py

```python
def on_stop(self):
    # Cancel timers and poller first
    if self._poll_cancel:
        self._poll_cancel()
    self._stop_poller()
    if self._idle_event:
        self._idle_event.cancel()

    # Delegate cleanup to screen instances via cleanup() — replaces ad-hoc code
    try:
        sm = self.root.ids.sm
        for screen in list(sm.screens):
            if hasattr(screen, 'cleanup'):
                screen.cleanup()
    except Exception:
        pass

    jobs.shutdown()
    self.controller.disconnect()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hard-coded `from .screens.flat_grind import load_kv` in build() | Registry-driven `_load_machine_screens()` | Phase 20 | Enables Serration/Convex without modifying main.py |
| Machine screens declared in base.kv | Programmatic `sm.add_widget()` | Phase 20 | Machine type determines which classes are added; KV has only machine-agnostic screens |
| Ad-hoc `_stop_pos_poll()` / `_stop_mg_reader()` calls in on_stop() | `cleanup()` method on each base class | Phase 20 | Reusable teardown path for swap and shutdown |

**Deprecated/outdated patterns after this phase:**
- Hard-coded flat_grind import at top of `build()` → removed, replaced by registry lookup
- Manual run screen teardown in `on_stop()` → replaced by `cleanup()` delegation loop
- FlatGrindRunScreen/AxesSetupScreen/ParametersScreen in base.kv ScreenManager → removed

## Open Questions

1. **machType numeric mapping**
   - What we know: machType is a DMC user variable. MG command returns a float. We need a mapping from float → machine type string.
   - What's unclear: The actual numeric values (1=FlatGrind? 2=Serration? 3=Convex?) depend on the DMC controller program. Not documented in any file reviewed.
   - Recommendation: Define a `_MACH_TYPE_MAP` constant with best-guess values and mark with TODO for hardware verification. If mapping is wrong, mismatch popup may false-fire — graceful degradation (skip if query fails) contains the blast radius.

2. **Convex and Serration placeholder classes**
   - What we know: Phases 21-22 create real Serration/Convex screens. Until then, the registry must point to valid classes.
   - What's unclear: Should Serration/Convex in the registry point to flat_grind classes (works but shows wrong UI) or should the entry be omitted (safe but blocks first-launch pick for those types)?
   - Recommendation: Point to flat_grind classes with TODO comments. This allows testing the full registry flow before Phases 21-22. The machine type picker already shows all 3 types (MACHINE_TYPES list), so an operator could pick Serration and get FlatGrind screens — acceptable placeholder behavior.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x |
| Config file | None detected — sys.path insert in each test file |
| Quick run command | `pytest tests/test_machine_config.py tests/test_base_classes.py -x` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LOAD-01 | `_REGISTRY["4-Axes Flat Grind"]["screen_classes"]` has keys "run", "axes_setup", "parameters" | unit | `pytest tests/test_machine_config.py -k registry_screen_classes -x` | ❌ Wave 0 |
| LOAD-01 | `_REGISTRY` load_kv path resolves to a callable | unit | `pytest tests/test_machine_config.py -k load_kv_path -x` | ❌ Wave 0 |
| LOAD-02 | `_load_machine_screens()` adds screens with canonical names to a mock ScreenManager | unit | `pytest tests/test_screen_loader.py -k load_machine_screens -x` | ❌ Wave 0 |
| LOAD-02 | After `_load_machine_screens()`, ScreenManager has screens named "run", "axes_setup", "parameters" | unit | `pytest tests/test_screen_loader.py -k screen_names -x` | ❌ Wave 0 |
| LOAD-03 | `BaseRunScreen.cleanup()` calls `_stop_pos_poll`, signals `_mg_stop_event`, closes `_fig`, unsubscribes state | unit | `pytest tests/test_base_classes.py -k cleanup -x` | ❌ Wave 0 |
| LOAD-03 | `cleanup()` is non-blocking (no thread.join) | unit | `pytest tests/test_base_classes.py -k cleanup_nonblocking -x` | ❌ Wave 0 |
| LOAD-04 | machType mismatch → popup scheduled on main thread (mock controller returns mismatched value) | unit | `pytest tests/test_screen_loader.py -k mismatch -x` | ❌ Wave 0 |
| LOAD-04 | machType query failure → no popup, no exception (graceful degradation) | unit | `pytest tests/test_screen_loader.py -k mismatch_graceful -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_machine_config.py tests/test_base_classes.py -x`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green (minus the 6 pre-existing failures in test_status_bar.py and test_main_estop.py which are unrelated to this phase)

### Wave 0 Gaps

- [ ] `tests/test_screen_loader.py` — covers LOAD-02, LOAD-04 (new test file; no ScreenManager needed — mock sm with a list and add_widget)
- [ ] Add to `tests/test_machine_config.py`: `test_registry_has_screen_classes_key`, `test_registry_load_kv_path_resolves`
- [ ] Add to `tests/test_base_classes.py`: `test_base_run_screen_cleanup_stops_resources`, `test_base_run_screen_cleanup_nonblocking`

## Sources

### Primary (HIGH confidence)
- Direct source inspection: `src/dmccodegui/main.py` — current build() flow, on_stop(), _show_machine_type_picker()
- Direct source inspection: `src/dmccodegui/machine_config.py` — existing _REGISTRY shape, public API
- Direct source inspection: `src/dmccodegui/screens/base.py` — BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen
- Direct source inspection: `src/dmccodegui/screens/flat_grind/__init__.py` — load_kv() pattern
- Direct source inspection: `src/dmccodegui/screens/flat_grind/run.py` — _stop_pos_poll, _stop_mg_reader, _fig handle
- Direct source inspection: `src/dmccodegui/ui/base.kv` — current ScreenManager screen declarations
- Python stdlib docs: importlib.import_module() — standard dotted path resolution pattern

### Secondary (MEDIUM confidence)
- STATE.md: Builder.unload_file() explicitly rejected; all lifecycle hooks in Python only (Kivy #2565)
- STATE.md: Phase 19-02 decision — deferred KV loading pattern; load_kv() called from build()

### Tertiary (LOW confidence)
- machType numeric mapping — inferred; not found in any codebase file. Marked for hardware verification.

## Metadata

**Confidence breakdown:**
- Registry extension (LOAD-01): HIGH — direct inspection of existing _REGISTRY; shape is fully decided
- _load_machine_screens() loader (LOAD-02): HIGH — importlib pattern is stdlib standard; ScreenManager API confirmed in base.kv
- cleanup() base class methods (LOAD-03): HIGH — _stop_pos_poll/_stop_mg_reader/_fig all confirmed in run.py source
- machType mismatch check (LOAD-04): MEDIUM — query pattern confirmed; numeric mapping value unknown (hardware-dependent)

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (stable project; no fast-moving dependencies)
