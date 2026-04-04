# Phase 6: Machine-Type Differentiation - Research

**Researched:** 2026-04-04
**Domain:** Kivy app configuration, runtime persistence, dynamic UI adaptation
**Confidence:** HIGH (all findings based on direct code inspection of the existing codebase)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Each machine type has its own parameter groups — not just different variables inside the same groups
- Convex Grind is mostly the same as Flat Grind with some additional Convex-specific parameters
- Serration Grind shares some groups with Flat/Convex (e.g., Feedrates) but has many serration-specific variables
- Validation rules (min/max ranges) vary per machine type, even for shared variable names
- Specific DMC variable lists will be provided later — design the config structure to be plug-in friendly
- Group color scheme is consistent by group name across all machine types (orange=Geometry, cyan=Feedrates, purple=Calibration). New groups get new colors.
- Serration uses A/B/C only — same roles as Flat (A=Knife Length, B=Knife Curve, C=Grinder Up/Down)
- Convex uses all 4 axes identically to Flat (A=Knife Length, B=Knife Curve, C=Grinder Up/Down, D=Knife Angle)
- CPM defaults are the same across all machine types (A=1200, B=1200, C=800, D=500)
- On Serration, the D axis is hidden completely from the Axes Setup sidebar — not greyed out, removed
- Delta-C bar chart (Knife Grind Adjustment) is shown on Flat and Convex only — hidden on Serration
- Serration replaces Delta-C with a bComp (B-axis compensation) bar chart — same widget pattern as DeltaCBarChart
- Array size for bComp is driven by `numSerr` (number of serrations per knife, set in parameters)
- Each bar adjusts B-axis compensation for that tooth — `bComp` is the DMC array name; `numSerr` is the DMC variable for array size
- Live A/B position plot works identically on all three machine types
- Action buttons (Start, Pause, Go to Rest, E-STOP) are identical across all types
- Cycle status: Serration shows tooth/pass/depth fields; Flat/Convex do not
- Machine type is selected at runtime by Setup/Admin — NOT hard-coded
- Operator cannot change machine type
- Persisted to disk — survives restarts
- Hot-swap: changing machine type immediately reloads parameter groups, axes sidebar, RUN page widgets without restart
- Status bar displays current machine type name — tapping it (Setup/Admin only) opens a picker popup
- Picker popup shows 3 big buttons: "4-Axes Flat Grind", "4-Axes Convex Grind", "3-Axes Serration Grind"
- On first launch (no machine type set), the app forces the mandatory machine-type picker before anything else — cannot dismiss without selecting

### Claude's Discretion

- Storage location for persisted machine type (separate config file vs users.json vs new settings file)
- Internal config module architecture (one dict per type, registry pattern, etc.)
- bComp bar chart step size (can match Delta-C step or differ)
- How hot-swap triggers screen rebuilds (Kivy property binding, screen recreation, etc.)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MACH-01 | App supports three machine types: 4-Axes Flat Grind, 4-Axes Convex Grind, 3-Axes Serration Grind | MachineConfig module with per-type PARAM_DEFS and axis list; persistence via settings.json |
| MACH-02 | Each machine type has its own RUN page layout and parameter groups appropriate to its axis count and workflow | RunScreen hot-swap via BooleanProperty `is_serration` already gating cycle status fields; extend to gate Delta-C vs bComp panel; ParametersScreen rebuild driven by machine type |
| MACH-03 | Machine type is determined at deployment time (hard-coded per installation, not runtime-selectable) | NOTE: CONTEXT.md overrides this — machine type IS runtime-selectable by Setup/Admin, persisted to disk. Planner must implement the runtime-selection model from CONTEXT.md, not the hard-coded REQUIREMENTS.md model. |
</phase_requirements>

---

## Summary

Phase 6 introduces a `machine_config` module as the single authority for machine-type-specific data (parameter definitions, axis list, bComp support flag, display name). The module reads and writes a `settings.json` file alongside `users.json` to persist the selected type across restarts. A `MachineTypePicker` popup (3 big buttons) is opened from the StatusBar machine-type label, gated to Setup/Admin only. On first launch with no persisted type, the picker is shown unconditionally before the login PIN overlay.

Hot-swap is implemented via a `MachineState.machine_type` StringProperty (or a dedicated Kivy StringProperty on the app level). Screens subscribe to changes on `on_pre_enter` or via `MachineState.subscribe()`, then call a `rebuild()` method that clears and repopulates dynamic content (axis sidebar buttons, parameter cards). The `RunScreen` conditionally shows either the existing `DeltaCBarChart` (Flat/Convex) or a new `BCompBarChart` (Serration) by using `opacity`/`disabled` swaps on the container — avoiding widget removal/re-addition, which can break KV id bindings (a lesson already learned in Phase 01-03 with the PIN overlay user list).

The largest integration points are: `parameters.py` (PARAM_DEFS must become per-type), `axes_setup.py` (axis list filtered by type), `run.py` (Delta-C vs bComp panel), `profiles.py` (MACHINE_TYPE reads from config, not hardcoded string), and `status_bar.py` + `status_bar.kv` (machine type label + tap handler).

**Primary recommendation:** Create `src/dmccodegui/machine_config.py` as the single source of truth — a registry dict keyed by machine type string, exposing `get_param_defs(mtype)`, `get_axis_list(mtype)`, `is_serration(mtype)`, `load()`, and `save()`. All screens query this module.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Kivy | >=2.2.0 | UI framework, properties system | Already in project; hot-swap via StringProperty observers |
| Python stdlib `json` | 3.10+ | Settings persistence | Already used by AuthManager for users.json; same pattern |
| Python stdlib `pathlib` | 3.10+ | File path resolution | Already used throughout (profiles.py, auth_manager.py) |
| Python stdlib `dataclasses` | 3.10+ | MachineState | Already used; add `machine_type: str` field |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `kivy.properties.StringProperty` | >=2.2.0 | Reactive machine type propagation | Bind screens to type changes without manual event wiring |
| `kivy.uix.modalview.ModalView` | >=2.2.0 | Machine type picker popup | Same pattern as FileChooserOverlay in profiles.py |
| `kivy.uix.popup.Popup` | >=2.2.0 | Error/confirmation dialogs | Already used in profiles.py export flow |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| settings.json alongside users.json | Add machine_type key to users.json | Separate file is cleaner — concerns separated; users.json is auth-only |
| StringProperty on MachineState | Global module-level variable | Property fires Kivy observers automatically; module variable requires manual callback wiring |
| Opacity/disabled swap for widget visibility | Remove/add widgets dynamically | Opacity swap preserves KV id bindings (learned in Phase 01-03 with PIN overlay) |

**Installation:** No new packages required. All functionality from Kivy >=2.2.0 and Python stdlib.

---

## Architecture Patterns

### Recommended Project Structure

```
src/dmccodegui/
├── machine_config.py        # NEW: single source of truth for machine-type data
├── app_state.py             # MODIFIED: add machine_type StringProperty field
├── main.py                  # MODIFIED: first-launch picker logic, settings load
├── screens/
│   ├── status_bar.py        # MODIFIED: machine type label + tap handler
│   ├── run.py               # MODIFIED: Delta-C vs bComp hot-swap
│   ├── axes_setup.py        # MODIFIED: axis list filtered by machine type
│   ├── parameters.py        # MODIFIED: PARAM_DEFS per machine type
│   └── profiles.py          # MODIFIED: MACHINE_TYPE from config, not constant
├── ui/
│   ├── status_bar.kv        # MODIFIED: add machine_type_label + tap button
│   └── run.kv               # MODIFIED: bComp panel (hidden on Flat/Convex)
```

### Pattern 1: Machine Config Registry

**What:** A single `machine_config.py` module that holds all per-type data as a registry dict and provides a simple API. The active type is persisted to `settings.json` using the same directory-relative path pattern as `users.json`.

**When to use:** Any time a screen needs to know what parameters or axes to show.

**Example:**
```python
# src/dmccodegui/machine_config.py

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Optional

MACHINE_TYPES = [
    "4-Axes Flat Grind",
    "4-Axes Convex Grind",
    "3-Axes Serration Grind",
]

# Registry: machine type string -> config dict
_REGISTRY: dict[str, dict] = {
    "4-Axes Flat Grind": {
        "axes": ["A", "B", "C", "D"],
        "has_bcomp": False,
        "param_defs": [
            # Populated with Flat Grind-specific PARAM_DEFS
            # Structure identical to existing PARAM_DEFS entries
        ],
    },
    "4-Axes Convex Grind": {
        "axes": ["A", "B", "C", "D"],
        "has_bcomp": False,
        "param_defs": [
            # Convex-specific — superset of Flat with additional Convex params
        ],
    },
    "3-Axes Serration Grind": {
        "axes": ["A", "B", "C"],  # D hidden
        "has_bcomp": True,
        "param_defs": [
            # Serration-specific — shares Feedrates group, adds serration vars
        ],
    },
}

_SETTINGS_PATH: Optional[str] = None
_active_type: Optional[str] = None


def init(settings_path: str) -> None:
    """Call once at app start. Loads persisted machine type from settings.json."""
    global _SETTINGS_PATH, _active_type
    _SETTINGS_PATH = settings_path
    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        _active_type = data.get("machine_type")
    else:
        _active_type = None


def get_active_type() -> Optional[str]:
    return _active_type


def set_active_type(mtype: str) -> None:
    global _active_type
    if mtype not in _REGISTRY:
        raise ValueError(f"Unknown machine type: {mtype!r}")
    _active_type = mtype
    _save()


def is_configured() -> bool:
    return _active_type is not None


def get_param_defs(mtype: Optional[str] = None) -> list[dict]:
    t = mtype or _active_type
    if t is None:
        return []
    return _REGISTRY[t]["param_defs"]


def get_axis_list(mtype: Optional[str] = None) -> list[str]:
    t = mtype or _active_type
    if t is None:
        return ["A", "B", "C", "D"]
    return _REGISTRY[t]["axes"]


def is_serration(mtype: Optional[str] = None) -> bool:
    t = mtype or _active_type
    return t == "3-Axes Serration Grind"


def _save() -> None:
    if _SETTINGS_PATH is None:
        return
    data = {"machine_type": _active_type}
    with open(_SETTINGS_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
```

### Pattern 2: MachineState machine_type Field

**What:** Add `machine_type: str = ""` to the `MachineState` dataclass. When `machine_config.set_active_type()` is called, also set `state.machine_type = mtype` and call `state.notify()`. Screens subscribed via `state.subscribe()` receive the change and can rebuild.

**When to use:** For screens that already subscribe to state (e.g. ParametersScreen, RunScreen).

**Example:**
```python
# app_state.py addition
machine_type: str = ""  # add to MachineState dataclass
```

### Pattern 3: Hot-Swap via on_pre_enter + rebuild()

**What:** Each affected screen implements a `_rebuild_for_machine_type()` method. This method reads the active type from `machine_config`, clears dynamic content, and rebuilds it. It is called from `on_pre_enter` every time the screen is entered — ensuring it is always current. For immediate hot-swap (no screen navigation needed), `main.py` also calls rebuild on all screens when type changes.

**When to use:** ParametersScreen (parameter cards), AxesSetupScreen (axis sidebar buttons), RunScreen (Delta-C vs bComp panel visibility).

**Example — ParametersScreen:**
```python
def on_pre_enter(self, *args):
    self._rebuild_for_machine_type()
    setup_unlocked = True
    if self.state is not None:
        setup_unlocked = self.state.setup_unlocked
    self._apply_role_mode(setup_unlocked)
    self.read_from_controller()

def _rebuild_for_machine_type(self) -> None:
    import dmccodegui.machine_config as mc
    self._param_defs = {p["var"]: p for p in mc.get_param_defs()}
    self._field_widgets.clear()
    self._dirty.clear()
    self.pending_count = 0
    self.build_param_cards()
```

### Pattern 4: Opacity/Disabled Swap for Widget Visibility

**What:** Use `opacity = 0` + `disabled = True` to hide widgets rather than removing them. This preserves KV `ids` bindings. This is the established pattern from Phase 01-03 (PIN overlay user list).

**When to use:** RunScreen Delta-C panel vs bComp panel. Both panels exist in KV, only one is visible.

**Example:**
```python
# RunScreen hot-swap between Delta-C and bComp panels
def _apply_machine_type_widgets(self) -> None:
    import dmccodegui.machine_config as mc
    serration = mc.is_serration()
    # Delta-C panel: visible on Flat/Convex, hidden on Serration
    delta_c_panel = self.ids.get("delta_c_panel")
    if delta_c_panel:
        delta_c_panel.opacity = 0 if serration else 1
        delta_c_panel.disabled = serration
    # bComp panel: visible on Serration, hidden on Flat/Convex
    bcomp_panel = self.ids.get("bcomp_panel")
    if bcomp_panel:
        bcomp_panel.opacity = 1 if serration else 0
        bcomp_panel.disabled = not serration
    # D axis pos display: visible on Flat/Convex, hidden on Serration
    pos_d_row = self.ids.get("pos_d_row")
    if pos_d_row:
        pos_d_row.opacity = 0 if serration else 1
```

### Pattern 5: First-Launch Mandatory Picker

**What:** In `DMCApp.build()`, after loading KV and before anything else UI-wise, check `machine_config.is_configured()`. If not configured, show a `MachineTypePicker` ModalView with `auto_dismiss=False`. The picker has 3 buttons. On selection, call `machine_config.set_active_type(mtype)` then dismiss. Only after this does the normal startup flow (PIN overlay etc.) continue.

**When to use:** First launch with no settings.json, or settings.json missing machine_type key.

**Example:**
```python
# main.py addition in DMCApp.build() after Factory.RootLayout()
import dmccodegui.machine_config as mc
settings_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "auth", "settings.json"
)
mc.init(settings_path)
if not mc.is_configured():
    Clock.schedule_once(lambda *_: self._show_machine_type_picker(), 0.1)
```

### Pattern 6: StatusBar Machine Type Label

**What:** Add a `machine_type_text` StringProperty to StatusBar. Add a Button/Label in `status_bar.kv` showing the type. Tap calls `app._show_machine_type_picker()` gated to `setup_unlocked`. StatusBar's `update_from_state()` reads `state.machine_type`.

**Anti-Patterns to Avoid**

- **Importing PARAM_DEFS at module level in profiles.py:** profiles.py currently does `from dmccodegui.screens.parameters import PARAM_DEFS` at import time. After Phase 6, `PARAM_DEFS` no longer exists as a flat list — replace with `mc.get_param_defs()` called at runtime (inside functions, not at module level).
- **Calling rebuild() inside background threads:** `build_param_cards()` creates Kivy widgets — must run on main thread only. Always wrap with `Clock.schedule_once()` if triggered from a background job.
- **Removing/re-adding axis sidebar buttons dynamically from KV:** The axis sidebar in `axes_setup.kv` is declared statically. For Serration (3 axes), set D button `opacity=0, disabled=True` rather than removing it from the widget tree.
- **Using IS_SERRATION module constant:** `run.py` currently has a module-level `IS_SERRATION = MACHINE_TYPE == "3axis_serration"` constant. This is evaluated at import time and will not respond to hot-swap. Replace with `mc.is_serration()` called at runtime.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-type param definitions | Custom ORM or class hierarchy | Plain list-of-dicts per type in registry | PARAM_DEFS is already a list-of-dicts; keep same structure, just per-type |
| Settings persistence | Custom serialization | `json.dump/load` with pathlib | Exact same pattern as `AuthManager._save()`/`_load()` — proven, simple |
| Reactive hot-swap notification | Custom event bus | `MachineState.subscribe()` already exists | Observer pattern already implemented; add `machine_type` field and notify |
| Widget visibility toggle | Remove/add widgets | `opacity=0, disabled=True` swap | Preserves KV ids; established in Phase 01-03 |
| Picker popup | Custom modal framework | `ModalView(auto_dismiss=False)` | Same as `FileChooserOverlay` in profiles.py |

**Key insight:** Every mechanism needed for this phase already exists in the codebase. The work is wiring existing patterns together, not building new infrastructure.

---

## Common Pitfalls

### Pitfall 1: Module-Level IS_SERRATION Constant

**What goes wrong:** `run.py` evaluates `IS_SERRATION = MACHINE_TYPE == "3axis_serration"` once at import time. Changing machine type at runtime does not update `IS_SERRATION`. Code paths using `if IS_SERRATION:` silently use the stale value.

**Why it happens:** Hot-swap was not a concern when these constants were written (they were Phase 6 placeholders).

**How to avoid:** Replace all `if IS_SERRATION:` and `if MACHINE_TYPE == ...:` in `run.py` with `if mc.is_serration():` called at the decision point. Same for the `is_serration = BooleanProperty(IS_SERRATION)` initialization — set it from `mc.is_serration()` in `on_pre_enter` or `on_kv_post`.

**Warning signs:** Test passes at import time but fails after a type change — indicates stale module-level constant.

### Pitfall 2: PARAM_DEFS Imported at Module Level in profiles.py

**What goes wrong:** `profiles.py` does `from dmccodegui.screens.parameters import PARAM_DEFS` at module import time. After Phase 6, `PARAM_DEFS` in `parameters.py` becomes dynamic (per machine type). The profile engine's `_PARAM_BY_VAR` lookup dict will be stale after a hot-swap.

**Why it happens:** Phase 5 was built with a hard-coded machine type; the import was safe then.

**How to avoid:** In `profiles.py`, replace the module-level import and `_PARAM_BY_VAR` construction with a function call to `mc.get_param_defs()` inside `parse_profile_csv()` and `validate_import()`. The `machine_type` parameter to `export_profile()` should come from `mc.get_active_type()` rather than the module constant.

**Warning signs:** CSV import accepts a profile from the wrong machine type after a hot-swap.

### Pitfall 3: build_param_cards() Called on Background Thread

**What goes wrong:** If `_rebuild_for_machine_type()` is triggered via a state change notification that fires on a background thread (e.g., after `state.notify()` called from a jobs.submit worker), `build_param_cards()` will attempt to create Kivy widgets off the main thread — causing silent failures or crashes.

**Why it happens:** `MachineState.notify()` calls listeners synchronously, and if `set_active_type` is called inside a background job, the listener runs on that thread.

**How to avoid:** `set_active_type()` should always be called on the main thread (Kivy event handlers are on main thread). If ever called from background, wrap the rebuild in `Clock.schedule_once()`.

**Warning signs:** Parameter cards appear blank or the app silently freezes after a type change.

### Pitfall 4: Axes Setup Teach Commands Always Write 4 Axes

**What goes wrong:** `teach_rest_point()` and `teach_start_point()` currently always read and write `restPtA/B/C/D` for all 4 axes — including D. On Serration (3-axis), querying `MG _TDD` or writing `restPtD=...` may fail or be meaningless.

**Why it happens:** The teach methods were written for 4-axis machines only.

**How to avoid:** Filter the axis list in teach methods using `mc.get_axis_list()`. Only read/write axes that exist for the active machine type. Build the semicolon-separated write command dynamically.

**Warning signs:** Teach fails silently on Serration machines; controller logs show "undefined variable" errors for `restPtD`.

### Pitfall 5: First-Launch Race Condition with PIN Overlay

**What goes wrong:** `DMCApp.build()` schedules both the machine-type picker and the PIN overlay on `Clock.schedule_once`. If both fire at nearly the same time, the PIN overlay may appear before the machine type is set, or both modals open simultaneously.

**Why it happens:** `Clock.schedule_once` with `0` delay fires on the next frame — ordering between two such calls is not guaranteed to be visually sequential.

**How to avoid:** Use a callback chain: show machine-type picker → on selection callback → then show PIN overlay (or normal startup). Never schedule both independently at startup. The machine-type picker's selection button dismisses and then triggers the normal startup flow.

**Warning signs:** Two modal dialogs stacked on first launch; or app proceeds to PIN login without machine type set.

---

## Code Examples

### BCompBarChart (new widget — mirrors DeltaCBarChart)

```python
# Source: mirrors existing DeltaCBarChart in run.py
class BCompBarChart(Widget):
    """Per-tooth B-axis compensation bar chart for Serration machines.

    Array size is driven by numSerr (read from controller).
    Each bar adjusts B-axis grind depth for that tooth.
    DMC array name: bComp. DMC size variable: numSerr.
    """
    offsets = ListProperty([])
    selected_index = NumericProperty(-1)
    max_offset = NumericProperty(500)

    # on_offsets, on_selected_index, on_size, on_pos, _draw(), on_touch_down
    # — identical implementation to DeltaCBarChart.
    # Step size: BCOMP_STEP (Claude's discretion — recommend same as DELTA_C_STEP = 50)
```

### Settings persistence pattern (mirrors AuthManager)

```python
# machine_config.py — path construction matches auth_manager.py pattern
_settings_dir = os.path.dirname(os.path.abspath(__file__))
settings_path = os.path.join(_settings_dir, "auth", "settings.json")
```

### StatusBar machine type addition

```python
# status_bar.py addition
machine_type_text = StringProperty("")

def update_from_state(self, state) -> None:
    # ... existing connection/user update logic ...
    mtype = getattr(state, "machine_type", "")
    if mtype != getattr(self, "_prev_machine_type", ""):
        self._prev_machine_type = mtype
        self.machine_type_text = mtype if mtype else "No Machine Type"
```

### AxesSetupScreen axis list filtering

```python
# axes_setup.py — rebuild sidebar for current machine type
def _rebuild_axis_sidebar(self) -> None:
    import dmccodegui.machine_config as mc
    axis_list = mc.get_axis_list()
    # Show all 4 axis buttons; hide D if not in axis_list
    sidebar = self.ids.get("axis_sidebar")
    if sidebar is None:
        return
    for axis in ("A", "B", "C", "D"):
        btn = self.ids.get(f"axis_btn_{axis.lower()}")
        if btn is not None:
            visible = axis in axis_list
            btn.opacity = 1 if visible else 0
            btn.disabled = not visible
    # If selected axis is now hidden, switch to first visible
    if self._selected_axis not in axis_list:
        self._selected_axis = axis_list[0]
```

### MachineTypePicker popup

```python
# In main.py or a dedicated screens/machine_type_picker.py
def _show_machine_type_picker(self, on_selected=None) -> None:
    from kivy.uix.modalview import ModalView
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    import dmccodegui.machine_config as mc

    content = BoxLayout(orientation="vertical", padding="20dp", spacing="16dp")
    lbl = Label(
        text="Select Machine Type",
        font_size="24sp",
        size_hint_y=None,
        height="48dp",
    )
    content.add_widget(lbl)

    picker = ModalView(auto_dismiss=False, size_hint=(0.6, 0.5))

    def make_handler(mtype):
        def handler(*_):
            mc.set_active_type(mtype)
            if self.state:
                self.state.machine_type = mtype
                self.state.notify()
            picker.dismiss()
            if on_selected:
                on_selected(mtype)
        return handler

    for mtype in mc.MACHINE_TYPES:
        btn = Button(
            text=mtype,
            font_size="20sp",
            size_hint_y=None,
            height="64dp",
        )
        btn.bind(on_release=make_handler(mtype))
        content.add_widget(btn)

    picker.add_widget(content)
    picker.open()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hard-coded `MACHINE_TYPE = "4axis_flat"` in run.py | Runtime-selectable, persisted in settings.json | Phase 6 | Screens must not use module-level constants for type decisions |
| Hard-coded `MACHINE_TYPE = "4-Axes Flat Grind"` in profiles.py | `mc.get_active_type()` at call time | Phase 6 | CSV import validation uses live machine type |
| Single flat `PARAM_DEFS` list in parameters.py | Per-type param defs in machine_config registry | Phase 6 | ParametersScreen builds cards from `mc.get_param_defs()` |

**Deprecated/outdated:**

- `MACHINE_TYPE` constant in `run.py`: Remove after Phase 6 — replaced by `mc.get_active_type()`
- `IS_SERRATION` constant in `run.py`: Remove after Phase 6 — replaced by `mc.is_serration()`
- `MACHINE_TYPE` constant in `profiles.py`: Remove after Phase 6 — was already marked "Phase 6 will add a proper machine-type module"

---

## Open Questions

1. **Exact parameter variable lists per machine type**
   - What we know: Phase 6 decision says "specific DMC variable lists will be provided later"
   - What's unclear: Which specific DMC var names/ranges are Convex-only, which are Serration-only
   - Recommendation: Implement the registry architecture with Flat Grind populated from existing `PARAM_DEFS`. Leave Convex and Serration as copies of Flat with a clear TODO comment. The planner should include a "stub param defs" task in Wave 0 so the structure is correct even before the real variable lists arrive.

2. **Axes Setup KV sidebar button IDs**
   - What we know: `axes_setup.kv` exists but was not read in this research session
   - What's unclear: Whether the sidebar buttons already have `id: axis_btn_a` / `id: axis_btn_d` style IDs for programmatic access
   - Recommendation: Plan should include reading `axes_setup.kv` and either adding IDs if absent or using a different filtering approach (iterating `children` by index).

3. **bComp step size**
   - What we know: Claude's discretion; DeltaCBarChart uses `DELTA_C_STEP = 50`
   - What's unclear: Whether the physical machine requires a different granularity for B-axis compensation
   - Recommendation: Use `BCOMP_STEP = 50` (same as Delta-C) as the initial value. Document as a tuning constant.

4. **settings.json path on first launch**
   - What we know: Should be alongside `users.json` in `src/dmccodegui/auth/`
   - What's unclear: Whether the `auth/` subdirectory is the right conceptual home for a machine config setting
   - Recommendation: Place `settings.json` in `auth/` directory alongside `users.json` — `init()` mirrors the `AuthManager.__init__` path construction pattern exactly. Both files travel together on the SD card.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (pyproject.toml `[tool.pytest.ini_options]`) |
| Config file | `pyproject.toml` — `testpaths = ["tests"]` |
| Quick run command | `pytest tests/test_machine_config.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MACH-01 | Registry contains all 3 machine types | unit | `pytest tests/test_machine_config.py::test_registry_has_all_types -x` | Wave 0 |
| MACH-01 | `get_axis_list("3-Axes Serration Grind")` returns `["A","B","C"]` only | unit | `pytest tests/test_machine_config.py::test_serration_axis_list -x` | Wave 0 |
| MACH-01 | `is_serration("3-Axes Serration Grind")` returns True | unit | `pytest tests/test_machine_config.py::test_is_serration -x` | Wave 0 |
| MACH-01 | `set_active_type` writes settings.json; `init` reads it back | unit | `pytest tests/test_machine_config.py::test_persistence_roundtrip -x` | Wave 0 |
| MACH-02 | ParametersScreen `_rebuild_for_machine_type()` uses `mc.get_param_defs()` | unit | `pytest tests/test_machine_config.py::test_param_defs_per_type -x` | Wave 0 |
| MACH-02 | `validate_import` uses live machine type (not module constant) | unit | `pytest tests/test_profiles.py::test_validate_import_uses_active_type -x` | Wave 0 |
| MACH-03 | `set_active_type` raises ValueError for unknown type | unit | `pytest tests/test_machine_config.py::test_unknown_type_raises -x` | Wave 0 |

All test patterns follow the established project convention:
- Import inside test function with `KIVY_NO_ENV_CONFIG=1, KIVY_LOG_LEVEL=critical`
- `machine_config` is pure Python (no Kivy), so no env setup needed for its tests
- `ParametersScreen` tests follow `test_parameters.py` pattern: no Kivy import needed for logic-only tests

### Sampling Rate

- **Per task commit:** `pytest tests/test_machine_config.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_machine_config.py` — covers MACH-01, MACH-02, MACH-03 pure-Python logic
- [ ] `src/dmccodegui/machine_config.py` — the module itself (new file, does not exist)

*(Existing test infrastructure — pytest via pyproject.toml, conftest.py, import-inside-function pattern — covers all other needs. No new framework install required.)*

---

## Sources

### Primary (HIGH confidence)

- Direct code inspection: `src/dmccodegui/screens/run.py` — `MACHINE_TYPE`, `IS_SERRATION`, `DeltaCBarChart`, hot-swap comment
- Direct code inspection: `src/dmccodegui/screens/axes_setup.py` — `AXIS_LABELS`, `AXIS_COLORS`, `AXIS_CPM_DEFAULTS`, teach methods
- Direct code inspection: `src/dmccodegui/screens/parameters.py` — `PARAM_DEFS`, `GROUP_COLORS`, `build_param_cards()`
- Direct code inspection: `src/dmccodegui/screens/profiles.py` — `MACHINE_TYPE` constant, `PARAM_DEFS` import, `validate_import`
- Direct code inspection: `src/dmccodegui/auth/auth_manager.py` — JSON persistence pattern (model for settings.json)
- Direct code inspection: `src/dmccodegui/app_state.py` — `MachineState`, `subscribe()`, `notify()` observer pattern
- Direct code inspection: `src/dmccodegui/screens/status_bar.py` — `update_from_state()`, StringProperty pattern
- Direct code inspection: `src/dmccodegui/main.py` — startup flow, PIN overlay scheduling, state wiring
- Direct code inspection: `.planning/phases/06-machine-type-differentiation/06-CONTEXT.md` — all locked decisions
- Direct code inspection: `tests/test_parameters.py` — established test pattern (import inside function, no Kivy env)
- Direct code inspection: `pyproject.toml` — pytest configuration, testpaths

### Secondary (MEDIUM confidence)

- `.planning/STATE.md` accumulated decisions — Phase 01-03 "opacity/disabled swap avoids removing/re-adding widgets" lesson applied here

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tooling already in use; no new dependencies
- Architecture: HIGH — all patterns directly copied from or consistent with existing code in the project
- Pitfalls: HIGH — three of the five pitfalls are directly identified from existing code comments ("Phase 6 will replace this") and documented Phase decisions

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable codebase; no external dependency changes expected)
