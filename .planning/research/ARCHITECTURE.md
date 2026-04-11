# Architecture Research

**Domain:** Per-machine-type screen refactor for industrial Kivy HMI
**Researched:** 2026-04-11
**Confidence:** HIGH — based on direct inspection of existing codebase, no speculation required

---

## Standard Architecture

### System Overview

```
+--------------------------------------------------------------------------+
|  SHARED CHROME LAYER (unchanged)                                          |
|  StatusBar | SetupBadge | TabBar                                          |
+--------------------------------------------------------------------------+
|  SCREEN MANAGER  (screens keyed by canonical name string)                 |
|                                                                           |
|  +----------+  +------------------------------------------------------+  |
|  | Shared   |  | Machine-specific screen set (one active at a time)   |  |
|  | Screens  |  |                                                      |  |
|  |          |  | flat_grind/    serration/         convex/            |  |
|  | setup    |  | FlatGrindRun   SerrationRun        ConvexRun         |  |
|  | profiles |  | FlatGrindAxes  SerrationAxes       ConvexAxes        |  |
|  | users    |  | FlatGrindParam SerrationParam       ConvexParam       |  |
|  | diag     |  | (all registered under "run", "axes_setup", "params") |  |
|  +----------+  +------------------------------------------------------+  |
+--------------------------------------------------------------------------+
|  BASE CLASS LAYER (new)                                                   |
|  BaseRunScreen | BaseAxesSetupScreen | BaseParametersScreen               |
+--------------------------------------------------------------------------+
|  SHARED HMI LAYER (unchanged)                                             |
|  GalilController | ControllerPoller | JobThread | dmc_vars               |
+--------------------------------------------------------------------------+
|  SHARED STATE LAYER (unchanged)                                           |
|  MachineState | machine_config | AuthManager                             |
+--------------------------------------------------------------------------+
```

### Component Responsibilities

| Component | Responsibility | Status |
|-----------|----------------|--------|
| `screens/base/run_base.py` | Poll wiring, plot setup/teardown, state subscription, HMI trigger helpers | New (extract from run.py) |
| `screens/base/axes_setup_base.py` | Jog mechanics, teach logic, CPM read, mode toggle, setup-loop enter/exit | New (extract from axes_setup.py) |
| `screens/base/parameters_base.py` | Dirty tracking, validation, apply, role gate, card builder | New (extract from parameters.py) |
| `screens/flat_grind/run.py` | FlatGrindRunScreen — deltaC panel, existing behavior preserved | New file (replaces run.py) |
| `screens/flat_grind/axes_setup.py` | FlatGrindAxesSetupScreen — 4-axis jog | New file (replaces axes_setup.py) |
| `screens/flat_grind/parameters.py` | FlatGrindParametersScreen — flat grind param_defs | New file (replaces parameters.py) |
| `screens/serration/run.py` | SerrationRunScreen — bComp panel, no D-axis plot elements | New |
| `screens/serration/axes_setup.py` | SerrationAxesSetupScreen — D row hidden, serration quick actions | New |
| `screens/serration/parameters.py` | SerrationParametersScreen — 3-axis param_defs | New |
| `screens/convex/run.py` | ConvexRunScreen — convex adjustment panel, 4-axis | New |
| `screens/convex/axes_setup.py` | ConvexAxesSetupScreen — full 4-axis jog, convex teach | New |
| `screens/convex/parameters.py` | ConvexParametersScreen — convex param_defs | New |
| `machine_config.py` | Add screen class name mapping per type | Modified |
| `main.py` | Add `_load_machine_screens()`, call on type select and startup | Modified |
| `ui/base.kv` | Remove static Run/AxesSetup/Parameters entries from ScreenManager | Modified |
| `ui/flat_grind/*.kv` | KV layout files for flat grind screens | New |
| `ui/serration/*.kv` | KV layout files for serration screens | New |
| `ui/convex/*.kv` | KV layout files for convex screens | New |

---

## Recommended Project Structure

```
src/dmccodegui/
+-- screens/
|   +-- __init__.py            # export shared screens only
|   +-- base/
|   |   +-- __init__.py
|   |   +-- run_base.py        # BaseRunScreen: poll, plot, HMI trigger, state sub
|   |   +-- axes_setup_base.py # BaseAxesSetupScreen: jog, teach, CPM, mode toggle
|   |   +-- parameters_base.py # BaseParametersScreen: dirty tracking, apply, role gate
|   +-- flat_grind/
|   |   +-- __init__.py
|   |   +-- run.py             # FlatGrindRunScreen(BaseRunScreen) -- deltaC panel
|   |   +-- axes_setup.py      # FlatGrindAxesSetupScreen(BaseAxesSetupScreen)
|   |   +-- parameters.py      # FlatGrindParametersScreen(BaseParametersScreen)
|   +-- serration/
|   |   +-- __init__.py
|   |   +-- run.py             # SerrationRunScreen(BaseRunScreen) -- bComp panel, no D
|   |   +-- axes_setup.py      # SerrationAxesSetupScreen(BaseAxesSetupScreen)
|   |   +-- parameters.py      # SerrationParametersScreen(BaseParametersScreen)
|   +-- convex/
|   |   +-- __init__.py
|   |   +-- run.py             # ConvexRunScreen(BaseRunScreen) -- convex adjustment
|   |   +-- axes_setup.py      # ConvexAxesSetupScreen(BaseAxesSetupScreen)
|   |   +-- parameters.py      # ConvexParametersScreen(BaseParametersScreen)
|   +-- setup.py               # SetupScreen -- unchanged
|   +-- profiles.py            # ProfilesScreen -- unchanged
|   +-- users.py               # UsersScreen -- unchanged
|   +-- diagnostics.py         # DiagnosticsScreen -- unchanged
|   +-- pin_overlay.py         # PINOverlay -- unchanged
|   +-- status_bar.py          # StatusBar -- unchanged
|   +-- tab_bar.py             # TabBar -- unchanged
+-- ui/
|   +-- flat_grind/
|   |   +-- run.kv             # <FlatGrindRunScreen>
|   |   +-- axes_setup.kv      # <FlatGrindAxesSetupScreen>
|   |   +-- parameters.kv      # <FlatGrindParametersScreen>
|   +-- serration/
|   |   +-- run.kv
|   |   +-- axes_setup.kv
|   |   +-- parameters.kv
|   +-- convex/
|   |   +-- run.kv
|   |   +-- axes_setup.kv
|   |   +-- parameters.kv
|   +-- theme.kv               # unchanged -- always first
|   +-- base.kv                # RootLayout -- ScreenManager loses 3 static entries
|   +-- pin_overlay.kv         # unchanged
|   +-- status_bar.kv          # unchanged
|   +-- tab_bar.kv             # unchanged
|   +-- setup.kv               # unchanged
|   +-- profiles.kv            # unchanged
|   +-- diagnostics.kv         # unchanged
|   +-- users.kv               # unchanged
+-- machine_config.py          # add screen class name mapping per type
+-- main.py                    # add _load_machine_screens(), call on type select
+-- app_state.py               # unchanged
```

### Structure Rationale

- **screens/base/:** All logic that is identical across machine types lives here. Machine-specific subclasses are thin — only what differs per machine. Avoids three diverging copies of jog mechanics, dirty tracking, etc.
- **screens/{machine}/:** One sub-package per machine type. This is the isolation boundary. Editing serration code cannot affect flat grind.
- **ui/{machine}/:** Mirrors the Python package layout. Each machine type owns its KV files outright, enabling fully independent layout changes.
- **Shared screens stay flat** in `screens/` with no sub-package. They have zero machine-type variance and are never swapped.

---

## Architectural Patterns

### Pattern 1: Base Class Extraction

**What:** Move all logic identical across machine types into `BaseRunScreen`, `BaseAxesSetupScreen`, `BaseParametersScreen`. Machine-specific subclasses override only what differs.

**When to use:** Every attribute and method that all three machine types share goes into the base. Only machine-specific UI differences go into the subclass.

**Split analysis — what moves where:**

| Screen | Into Base | Stays in Subclass |
|--------|-----------|-------------------|
| Run | Poll subscription, plot setup/teardown, `_stop_pos_poll`, `_stop_mg_reader`, state update handlers, HMI trigger helpers (`_fire_hmi_trigger`), knife count display, disconnect banner | deltaC vs bComp adjustment panel widget, which bar chart class to instantiate |
| AxesSetup | `__init__`, `on_pre_enter` orchestration, `on_leave`, jog mechanics (`jog_axis`), teach logic (`teach_rest_point`, `teach_start_point`), CPM read, mode toggle, quick-action triggers, `_SETUP_SCREENS` check, `_rebuild_axis_rows` (already data-driven via `mc.get_axis_list()`) | Nothing — the existing data-driven approach means no override is needed |
| Parameters | `__init__`, `validate_field`, `on_field_text_change`, `apply_to_controller`, `read_from_controller`, `_apply_role_mode`, `_update_apply_button`, `on_leave`, `build_param_cards`, `_rebuild_for_machine_type` (already calls `mc.get_param_defs()`) | Nothing — already fully data-driven via machine_config |

Key observation: `_rebuild_axis_rows()` already reads `mc.get_axis_list()` and `_rebuild_for_machine_type()` already calls `mc.get_param_defs()`. The existing adaptation logic is already data-driven and requires no per-machine override. The base classes inherit this logic unchanged. The only genuine per-machine differences are in the Run screen's adjustment panel (deltaC for flat/convex, bComp for serration).

**Trade-offs:** Base classes add an indirection layer. The payoff is that three machine types can diverge in layout without forking business logic. The axes_setup and parameters screens may end up with trivially thin subclasses — that is acceptable because it preserves the isolation boundary.

### Pattern 2: Canonical Screen Names (Do Not Change Navigation Strings)

**What:** All nine machine-specific screens register under the same canonical names in the ScreenManager: "run", "axes_setup", "parameters". The loader swaps the screen instances but never changes the names.

**Why this matters:** The entire codebase navigates by these string literals. TabBar wires `current_tab` directly to `sm.current`. `_on_login_success` sets `sm.current = "axes_setup"`. `_on_idle_timeout` checks `sm.current in ("axes_setup", "parameters", ...)`. The `_SETUP_SCREENS` frozenset in both AxesSetup and Parameters uses these same strings. Renaming would require touching 15+ call sites across 5 files.

**How the swap works:** The ScreenManager holds only one set of machine screens at a time. When machine type changes, the loader removes the three machine screens (by canonical name) and adds the new machine type's screens under the same canonical names. Shared screens (setup, profiles, users, diagnostics) are never removed.

**Implementation in main.py:**

```python
_MACHINE_SCREEN_CLASSES = {
    "4-Axes Flat Grind": {
        "run": "FlatGrindRunScreen",
        "axes_setup": "FlatGrindAxesSetupScreen",
        "parameters": "FlatGrindParametersScreen",
    },
    "3-Axes Serration Grind": {
        "run": "SerrationRunScreen",
        "axes_setup": "SerrationAxesSetupScreen",
        "parameters": "SerrationParametersScreen",
    },
    "4-Axes Convex Grind": {
        "run": "ConvexRunScreen",
        "axes_setup": "ConvexAxesSetupScreen",
        "parameters": "ConvexParametersScreen",
    },
}

def _load_machine_screens(self, mtype: str) -> None:
    sm = self.root.ids.sm
    # Navigate away before removing (cannot remove the current screen)
    sm.current = "setup"
    # Remove old machine screens
    for name in ("run", "axes_setup", "parameters"):
        if sm.has_screen(name):
            sm.remove_widget(sm.get_screen(name))
    # Instantiate and inject new screens
    for screen_name, class_name in _MACHINE_SCREEN_CLASSES[mtype].items():
        cls = Factory.get(class_name)
        screen = cls(name=screen_name)
        screen.controller = self.controller
        screen.state = self.state
        sm.add_widget(screen)
    sm.current = "run"
```

**Trade-offs:** Screen instances are created fresh at switch time. On Pi 4, Kivy screen instantiation takes under 200ms for these screens. Machine type changes are rare in production (once per machine lifetime). Acceptable cost.

### Pattern 3: Load All KV Files at Startup (Deferred Lazy Loading Rejected)

**What:** All nine machine-specific KV files are loaded at `build()` time alongside shared KV files. No lazy loading.

**Why not lazy:** Kivy `Builder.unload_file()` is available but brittle. It removes rules but does not unregister class names from the Factory. Re-loading a KV file after unloading can produce duplicate rule registration warnings. For an industrial kiosk where startup latency is not a UX concern, loading all nine KV files once at startup is simpler and more reliable.

**KV_FILES list in main.py:**

```python
KV_FILES = [
    "ui/theme.kv",                     # always first
    "ui/pin_overlay.kv",
    "ui/status_bar.kv",
    "ui/tab_bar.kv",
    "ui/setup.kv",
    "ui/profiles.kv",
    "ui/diagnostics.kv",
    "ui/users.kv",
    # Machine-specific -- all loaded at startup
    "ui/flat_grind/run.kv",
    "ui/flat_grind/axes_setup.kv",
    "ui/flat_grind/parameters.kv",
    "ui/serration/run.kv",
    "ui/serration/axes_setup.kv",
    "ui/serration/parameters.kv",
    "ui/convex/run.kv",
    "ui/convex/axes_setup.kv",
    "ui/convex/parameters.kv",
    "ui/base.kv",                      # always last
]
```

**Trade-offs:** Nine additional KV files add approximately 100-200ms to startup on Pi 4. Acceptable for an industrial kiosk. All class names are registered in the Factory before any screen is instantiated, eliminating "class not found" errors during dynamic screen creation.

### Pattern 4: machine_config.py Extended with Screen Class Mapping

**What:** Add a `screen_classes` key to each registry entry in `_REGISTRY`, listing the Python class names for the three machine-specific screens. This keeps the mapping co-located with the other machine type data and out of main.py.

```python
# machine_config.py addition
_REGISTRY = {
    "4-Axes Flat Grind": {
        "axes": ["A", "B", "C", "D"],
        "has_bcomp": False,
        "param_defs": _FLAT_PARAM_DEFS,
        "screen_classes": {
            "run": "FlatGrindRunScreen",
            "axes_setup": "FlatGrindAxesSetupScreen",
            "parameters": "FlatGrindParametersScreen",
        },
    },
    ...
}

def get_screen_classes(mtype: Optional[str] = None) -> dict:
    """Return {canonical_name: class_name} for the given (or active) machine type."""
    resolved = _resolve_type(mtype)
    return _REGISTRY[resolved]["screen_classes"]
```

**Trade-offs:** One more field in the registry. Keeps machine type configuration in one file. main.py calls `mc.get_screen_classes()` instead of maintaining its own dict.

---

## Data Flow

### Machine Type Selection Flow

```
Operator taps machine type in picker
    -> _on_type_selected(mtype)
        -> mc.set_active_type(mtype)          # persist to settings.json
        -> state.machine_type = mtype
        -> state.notify()                      # StatusBar updates display
        -> _load_machine_screens(mtype)        # swap ScreenManager screens
        -> sm.current = "run"
```

### Startup Flow (machine type already configured)

```
DMCApp.build()
    -> KV files loaded (all 9 machine KV files included)
    -> Factory.RootLayout() -- ScreenManager built with shared screens only
    -> mc.is_configured() == True
        -> _load_machine_screens(mc.get_active_type())  # add machine screens
    -> screen injection: controller + state into all screens
    -> sm.current = "setup"
```

### Screen Entry Flow (unchanged from v2.0)

```
TabBar tap -> sm.current = "run"
    -> RunScreen.on_pre_enter()
        -> subscribes to state
        -> starts _pos_poll (background thread)
        -> starts _mg_reader (background thread)
    [on leave]
    -> RunScreen.on_leave()
        -> _stop_pos_poll()
        -> _stop_mg_reader()
        -> unsubscribes from state
```

### Controller I/O Flow (unchanged)

```
Screen method calls jobs.submit(fn)
    -> fn() runs on JobThread (off UI thread)
    -> controller.cmd(str) -> gclib -> DMC
    -> Clock.schedule_once(ui_update) posts result back
    -> ui_update() runs on Kivy main thread
```

---

## Integration Points

### New vs Modified — Explicit List

**New files (create):**

| File | Contents |
|------|----------|
| `screens/base/__init__.py` | Package marker |
| `screens/base/run_base.py` | `BaseRunScreen(Screen)` — extract from run.py |
| `screens/base/axes_setup_base.py` | `BaseAxesSetupScreen(Screen)` — extract from axes_setup.py |
| `screens/base/parameters_base.py` | `BaseParametersScreen(Screen)` — extract from parameters.py |
| `screens/flat_grind/__init__.py` | Package marker |
| `screens/flat_grind/run.py` | `FlatGrindRunScreen(BaseRunScreen)` — deltaC panel |
| `screens/flat_grind/axes_setup.py` | `FlatGrindAxesSetupScreen(BaseAxesSetupScreen)` |
| `screens/flat_grind/parameters.py` | `FlatGrindParametersScreen(BaseParametersScreen)` |
| `screens/serration/__init__.py` | Package marker |
| `screens/serration/run.py` | `SerrationRunScreen(BaseRunScreen)` — bComp panel, no D-axis elements |
| `screens/serration/axes_setup.py` | `SerrationAxesSetupScreen(BaseAxesSetupScreen)` |
| `screens/serration/parameters.py` | `SerrationParametersScreen(BaseParametersScreen)` |
| `screens/convex/__init__.py` | Package marker |
| `screens/convex/run.py` | `ConvexRunScreen(BaseRunScreen)` — convex adjustment panel |
| `screens/convex/axes_setup.py` | `ConvexAxesSetupScreen(BaseAxesSetupScreen)` |
| `screens/convex/parameters.py` | `ConvexParametersScreen(BaseParametersScreen)` |
| `ui/flat_grind/run.kv` | `<FlatGrindRunScreen>:` — existing run.kv content, class name updated |
| `ui/flat_grind/axes_setup.kv` | `<FlatGrindAxesSetupScreen>:` — existing axes_setup.kv content, class name updated |
| `ui/flat_grind/parameters.kv` | `<FlatGrindParametersScreen>:` — existing parameters.kv content, class name updated |
| `ui/serration/run.kv` | `<SerrationRunScreen>:` — fork of flat_grind run.kv with bComp panel |
| `ui/serration/axes_setup.kv` | `<SerrationAxesSetupScreen>:` — fork with D row hidden |
| `ui/serration/parameters.kv` | `<SerrationParametersScreen>:` — same structure, different param count |
| `ui/convex/run.kv` | `<ConvexRunScreen>:` |
| `ui/convex/axes_setup.kv` | `<ConvexAxesSetupScreen>:` |
| `ui/convex/parameters.kv` | `<ConvexParametersScreen>:` |

**Modified files:**

| File | What Changes |
|------|-------------|
| `main.py` | Add `_load_machine_screens()`. Call it on startup when `mc.is_configured()`, and from `_on_type_selected()`. Add all 9 machine KV files to `KV_FILES`. Remove static screen injection loop (replaced by per-screen injection in loader). |
| `machine_config.py` | Add `screen_classes` dict to each `_REGISTRY` entry. Add `get_screen_classes()` public function. |
| `screens/__init__.py` | Remove exports of `RunScreen`, `AxesSetupScreen`, `ParametersScreen`. Add imports of all 9 machine-specific screen classes (required for Factory registration at import time). Add imports of base classes. |
| `ui/base.kv` | Remove `RunScreen`, `AxesSetupScreen`, `ParametersScreen` from the `ScreenManager` block. These are now added dynamically by `_load_machine_screens()`. |

**Deleted files (after migration validated):**

| File | Replaced By |
|------|-------------|
| `ui/run.kv` | `ui/flat_grind/run.kv` |
| `ui/axes_setup.kv` | `ui/flat_grind/axes_setup.kv` |
| `ui/parameters.kv` | `ui/flat_grind/parameters.kv` |
| `screens/run.py` | `screens/base/run_base.py` + `screens/flat_grind/run.py` |
| `screens/axes_setup.py` | `screens/base/axes_setup_base.py` + `screens/flat_grind/axes_setup.py` |
| `screens/parameters.py` | `screens/base/parameters_base.py` + `screens/flat_grind/parameters.py` |

**Unchanged files (zero modifications):**

- `screens/setup.py`, `screens/profiles.py`, `screens/users.py`, `screens/diagnostics.py`, `screens/pin_overlay.py`, `screens/status_bar.py`, `screens/tab_bar.py`
- `app_state.py`
- `hmi/controller.py`, `hmi/poll.py`, `hmi/dmc_vars.py`, `hmi/job_thread.py`
- `auth/auth_manager.py`
- `ui/theme.kv`, `ui/pin_overlay.kv`, `ui/status_bar.kv`, `ui/tab_bar.kv`, `ui/setup.kv`, `ui/profiles.kv`, `ui/diagnostics.kv`, `ui/users.kv`

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Machine screens -> machine_config | `mc.get_axis_list()`, `mc.get_param_defs()`, `mc.get_screen_classes()` | Already the established pattern; no change |
| Machine screens -> MachineState | ObjectProperty injection by `_load_machine_screens()` after screen creation | Same injection pattern as existing `screen.controller = self.controller` |
| Machine screens -> JobThread | `jobs.submit(fn)`, `Clock.schedule_once(ui_fn)` | Unchanged — all machine types share the same job queue |
| main.py -> ScreenManager | `sm.remove_widget()`, `sm.add_widget()`, `sm.current` | New pattern; existing code only uses `sm.current` |
| TabBar -> ScreenManager | `tab_bar.bind(current_tab=lambda inst, val: setattr(sm, 'current', val))` | Unchanged — canonical screen names mean TabBar wiring requires zero changes |

---

## Build Order

Dependencies drive the order. Each step can only begin once its predecessor is validated.

**Step 1 — Base classes (no machine-specific logic, no KV)**

Extract `BaseRunScreen`, `BaseAxesSetupScreen`, `BaseParametersScreen` from the existing three screens. The base classes are complete, stand-alone, testable Python. No KV files needed at this step. Verify the existing test suite still passes — the base class must be API-compatible with the existing screen classes.

This step is the riskiest because it is a refactor of working code. Do it first while there are no machine-specific variants to break.

**Step 2 — Flat Grind screens and KV (reference implementation)**

Create `FlatGrindRunScreen(BaseRunScreen)`, `FlatGrindAxesSetupScreen`, `FlatGrindParametersScreen`. Copy existing KV content into `ui/flat_grind/*.kv` with class header name updated (e.g. `<RunScreen>:` becomes `<FlatGrindRunScreen>:`). Load these KV files in addition to the existing ones (do not delete old files yet). Add `Factory.register` or ensure imports cause registration.

Validate that Flat Grind still works end-to-end with the new class names. This is the existing v2.0 behavior — the acceptance bar is "nothing changed for the operator."

**Step 3 — main.py screen loader + base.kv update**

Add `_load_machine_screens()` to DMCApp. Remove `RunScreen`, `AxesSetupScreen`, `ParametersScreen` from `ui/base.kv`. Remove `run.kv`, `axes_setup.kv`, `parameters.kv` from `KV_FILES`. Add all nine machine KV files to `KV_FILES`. Call `_load_machine_screens()` on startup with the configured type.

At this point the app runs with the dynamic loader for a single machine type. This validates the swap mechanism before adding the other machine types.

**Step 4 — Serration screens and KV**

Create Serration subclasses. The D-axis hiding is already handled in the base `_rebuild_axis_rows()` via `mc.get_axis_list()` — Serration AxesSetup may not need to override anything. The Serration Run screen needs a bComp panel instead of the deltaC panel; this is the primary machine-specific difference in layout. Validate machine type picker switching: flat grind -> serration -> flat grind.

**Step 5 — Convex screens and KV**

Create Convex subclasses. Convex is 4-axis like Flat Grind; the run screen adjustment panel differs. Start from the flat grind KV as a template. The Convex param_defs in `machine_config.py` are currently a placeholder copy of Flat Grind — this is noted as a TODO; the screen will work, it just uses the same params until real specs are provided.

**Step 6 — Clean up**

Delete `ui/run.kv`, `ui/axes_setup.kv`, `ui/parameters.kv` (replaced). Delete `screens/run.py`, `screens/axes_setup.py`, `screens/parameters.py` (replaced). Update `screens/__init__.py` to remove old exports. Run full test suite.

---

## Anti-Patterns

### Anti-Pattern 1: Machine Type Branching Inside Shared Screen Classes

**What people do:** Add `if mc.is_serration(): ... else: ...` blocks directly inside the existing single-screen classes instead of creating subclasses. The existing `_rebuild_axis_rows()` is an example of this pattern taken as far as it should go.

**Why it's wrong:** Works for minor differences (showing/hiding a row) but becomes unmaintainable when the Serration and Convex screens need meaningfully different layouts. After three machine types with three conditional branches each, every screen method reads like a state machine with no clear owner.

**Do this instead:** Put machine-specific UI in subclasses with their own KV files. The base class can still call `mc.get_axis_list()` for data-driven differences (axis count) without branching on machine type strings.

### Anti-Pattern 2: Removing Screens From ScreenManager While One Is Active

**What people do:** Call `sm.remove_widget(screen)` while `sm.current` points at that screen.

**Why it's wrong:** Kivy raises a `ScreenManagerException` and the screen swap fails. The current screen must be changed before the removal.

**Do this instead:** In `_load_machine_screens()`, always navigate to "setup" before removing any machine screens. Navigate to "run" after adding the new screens. The sequence is: navigate -> remove -> add -> navigate.

### Anti-Pattern 3: Static Screen Declaration in base.kv for Machine-Specific Screens

**What people do:** Keep `RunScreen`, `AxesSetupScreen`, `ParametersScreen` hardcoded in the `<RootLayout>` KV rule's ScreenManager block.

**Why it's wrong:** KV is evaluated at `Factory.RootLayout()` time, before the machine type is known. The ScreenManager is pre-populated with exactly one set of screen classes — whichever names appear in the KV. Dynamic swapping requires the ScreenManager to start empty of machine screens.

**Do this instead:** Remove the three machine-specific screens from `base.kv`'s ScreenManager. Add them programmatically in `_load_machine_screens()`. Shared screens (setup, profiles, users, diagnostics) remain in `base.kv` since they never change.

### Anti-Pattern 4: Duplicate Class Names Across Machine Packages

**What people do:** Name all three run screens `RunScreen` in different modules and rely on module paths to distinguish them.

**Why it's wrong:** Kivy's Factory resolves class names globally, not by module. Two classes both named `RunScreen` collide in the Factory registry — the second registration silently shadows the first. KV rules (`<RunScreen>:`) apply to whichever class registered last.

**Do this instead:** Use distinct class names per machine type: `FlatGrindRunScreen`, `SerrationRunScreen`, `ConvexRunScreen`. KV rule headers must match: `<FlatGrindRunScreen>:`. There is no ambiguity.

### Anti-Pattern 5: Skipping the _stop_pos_poll/_stop_mg_reader Calls on Screen Swap

**What people do:** Remove the old machine screen from the ScreenManager without calling `_stop_pos_poll()` and `_stop_mg_reader()` on the RunScreen first.

**Why it's wrong:** These background threads hold a reference to `self.controller` and keep submitting to the jobs queue. After the screen is removed from the ScreenManager, the threads are orphaned but not stopped. On machine type change, two RunScreens are now polling simultaneously.

**Do this instead:** In `_load_machine_screens()`, before removing the old screens, find the current "run" screen and call `_stop_pos_poll()` and `_stop_mg_reader()` on it. The existing `on_stop()` pattern in `DMCApp` already does this correctly — replicate that logic in the screen swap path.

---

## Existing Patterns to Preserve

These are load-bearing constraints from the project memory that must not change during the refactor:

- **HMI one-shot variable pattern** — screens fire `hmiVar=0` to trigger; never `XQ` calls directly. All three machine type base classes inherit this from the existing implementations.
- **JobThread single channel** — all controller I/O via `jobs.submit()`. No screen spawns threads directly.
- **`on_leave` exit-setup gate** — both AxesSetup and Parameters fire `hmiExSt=0` only when leaving to a non-setup screen. The `_SETUP_SCREENS` frozenset check uses canonical screen names — this works unchanged with the dynamic screen swap pattern.
- **Poll rate switching** — ControllerPoller handles poll rate. Machine screens never manage poll rate directly.
- **Quiet exit (no ST)** — `DMCApp.on_stop()` stops threads before disconnect; never sends `ST`. Not affected by this refactor.
- **Machine order** — Flat Grind first, then Serration, then Convex. This is the build order for Steps 2, 4, 5.

---

## Sources

- Direct inspection: `src/dmccodegui/main.py`, `screens/run.py`, `screens/axes_setup.py`, `screens/parameters.py`, `screens/tab_bar.py`, `screens/__init__.py`, `machine_config.py`, `app_state.py`, `ui/base.kv`, `ui/run.kv`, `ui/axes_setup.kv`
- Project constraints: `.planning/PROJECT.md` v3.0 milestone section
- Project memory: MEMORY.md — no XQ commands, machine order, gclib comms architecture, shutdown pattern

---
*Architecture research for: DMC Grinding GUI — per-machine-type screen refactor (v3.0)*
*Researched: 2026-04-11*
