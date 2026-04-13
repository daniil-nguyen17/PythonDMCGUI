# Phase 21: Serration Screen Set - Research

**Researched:** 2026-04-13
**Domain:** Kivy screen package creation, bComp list widget, 3-axis layout
**Confidence:** HIGH — all findings drawn from verified source code in this repo

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**bComp panel**
- Live functional panel (not a stub) — scrollable list/table of editable input fields, one row per serration
- Array sized by `numSerr` variable read from controller — displayed as "Serrations: N" in panel header
- Read/write DMC `bComp[]` array: auto-read on screen enter + manual "Read bComp" refresh button
- Save writes one element at a time (matches existing deltaC individual element assignment pattern for reliable writes)
- Values in mm with min/max validation (Claude picks reasonable defaults)
- Editable when machine is idle — no setup mode required
- All entries visible at once in a scrollable list (no pagination)
- New BCompPanel widget built from scratch — do NOT reuse _BaseBarChart (list UI is fundamentally different from bar chart)
- Lives in `screens/serration/widgets.py` — mirrors flat_grind package structure

**Run screen layout**
- No DeltaC bar chart — that is Flat Grind only
- No D-axis position labels or status anywhere — stripped completely, clean 3-axis layout
- Plot area: placeholder/stub — decide visualization after seeing real machine data
- bComp panel positioned below the plot stub area, full width
- Cycle controls: Start, Stop, session/station counters, progress bar, controller message log — same as Flat Grind
- More/less stone panel: up/down arrows (no tip/heel labels), same startPtC offset logic and DMC variables as Flat Grind, shows current startPtC value alongside arrows
- `numSerr` displayed near bComp panel header as read-only

**Axes Setup 3-axis layout**
- Same as Flat Grind minus D axis — [A, B, C] with identical roles, same accent colors (A=orange, B=purple, C=cyan)
- Same teach points: rest point and start point per axis
- Standard jog workflow: jog controls, teach, CPM read — no extra Serration-specific actions
- BaseAxesSetupScreen with mc.get_axis_list() handles the 3-axis constraint automatically

**Parameters grouping**
- Same groups as Flat Grind (Geometry, Feedrates, Calibration) minus D-axis parameters
- `_SERRATION_PARAM_DEFS` already defined in machine_config.py (Flat minus fdD, pitchD, ratioD, ctsRevD)
- `numSerr` is an editable parameter on the Parameters screen — operator sets it in setup
- When numSerr changes, bComp list on Run screen auto-resizes on next screen enter (re-reads numSerr)
- Room to add more Serration-specific params later — param_defs is a placeholder subset for now

**Screen package structure**
- Copy flat_grind package as starting point, then modify — full independence for future tuning
- Package: `screens/serration/` with `__init__.py`, `run.py`, `axes_setup.py`, `parameters.py`, `widgets.py`
- `__init__.py` exports `load_kv()` + all three Serration screen classes (same pattern as flat_grind)
- KV files in `ui/serration/`: `run.kv`, `axes_setup.kv`, `parameters.kv`
- Update `machine_config._REGISTRY["3-Axes Serration Grind"]` to point to real Serration classes and load_kv

**Testing**
- Mirror Flat Grind test patterns: screen instantiation, expected widgets present, D-axis widgets absent
- bComp panel renders with dummy data — verify list sizing from numSerr
- bComp read/write I/O testing deferred to hardware validation — no mocked controller tests for bComp
- KV rule name collision check: grep for duplicate `<ClassName>:` headers across all .kv files

### Claude's Discretion
- Exact bComp min/max validation range
- Plot stub visual design (empty axes, placeholder text, etc.)
- BCompPanel internal implementation (Kivy RecycleView, BoxLayout rows, etc.)
- numSerr parameter definition details (group, min, max)
- Exact KV layout proportions and spacing
- Test file organization

### Deferred Ideas (OUT OF SCOPE)
- Serration plot visualization design — decide after hardware validation with real machine data
- Additional Serration-specific parameters — add to _SERRATION_PARAM_DEFS when customer provides real DMC variable list
- bComp controller I/O testing — deferred to hardware validation phase
- Serration bComp write path tied to DMC program (SERR-04 partially addressed: panel functional, but DMC program integration pending customer)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SERR-01 | SerrationRunScreen created from Flat Grind base with D-axis elements removed | Full package copy pattern documented; `pos_d`, `cpm_d` properties and D-axis KV widgets must be absent; no DeltaCBarChart |
| SERR-02 | SerrationAxesSetupScreen created with 3-axis layout (A, B, C only) | `_rebuild_axis_rows()` in FlatGrindAxesSetupScreen already reads `mc.get_axis_list()`; D row hidden via opacity/disabled/size_hint_y=0; Serration class can reuse exact same approach |
| SERR-03 | SerrationParametersScreen created with serration-specific parameter groups | `_SERRATION_PARAM_DEFS` already built in machine_config.py; `BaseParametersScreen._rebuild_for_machine_type()` reads `mc.get_param_defs()` dynamically — inheriting this handles isolation automatically |
| SERR-04 | bComp panel stubbed/functional in SerrationRunScreen | Panel is live (not a stub per locked decisions); BCompPanel is a new widget in `screens/serration/widgets.py`; reads `numSerr` from controller on enter; writes `bComp[i]=val` one element at a time |
</phase_requirements>

---

## Summary

Phase 21 creates the `screens/serration/` package as a near-copy of `screens/flat_grind/`, then modifies it to remove D-axis elements, replace the DeltaCBarChart with a scrollable BCompPanel, and strip matplotlib in favour of a plot stub. The base classes (`BaseRunScreen`, `BaseAxesSetupScreen`, `BaseParametersScreen`) already handle the 3-axis constraint via `mc.get_axis_list()`, so the Serration axes-setup and parameters screens are thin subclasses that inherit almost everything.

The main new work is `BCompPanel` — a scrollable list of editable mm-value fields, one row per serration, sized dynamically by `numSerr` read from the controller on screen enter. The widget is Kivy-only (no matplotlib) and lives in `screens/serration/widgets.py`. The final integration step is updating `machine_config._REGISTRY["3-Axes Serration Grind"]` to point at the new classes and `load_kv`.

All controller I/O for bComp (array reads and individual element writes) follows the same single-channel `jobs.submit()` / `Clock.schedule_once()` discipline established in Flat Grind.

**Primary recommendation:** Copy flat_grind package, strip D-axis and DeltaC, add BCompPanel, update registry.

---

## Standard Stack

### Core (verified from source)
| Component | Location | Purpose |
|-----------|----------|---------|
| `BaseRunScreen` | `screens/base.py` | controller/state ObjectProperty, subscribe-on-enter lifecycle, cleanup() |
| `BaseAxesSetupScreen` | `screens/base.py` | Jog infrastructure, CPM read, setup-mode enter/exit, 3-axis gate via mc.get_axis_list() |
| `BaseParametersScreen` | `screens/base.py` | Card builder, dirty tracking, apply_to_controller, read_from_controller, _rebuild_for_machine_type |
| `SetupScreenMixin` | `screens/base.py` | _enter_setup_if_needed / _exit_setup_if_needed, _SETUP_SCREENS frozenset |
| `jobs.submit()` | `utils/jobs.py` | All controller I/O dispatched to background thread |
| `Clock.schedule_once()` | kivy.clock | All UI updates from background thread marshalled to main thread |
| `mc.get_axis_list()` | `machine_config.py` | Returns ["A","B","C"] for Serration — jog_axis and _rebuild_axis_rows use this |
| `mc.get_param_defs()` | `machine_config.py` | Returns `_SERRATION_PARAM_DEFS` for active Serration type — already defined, D-axis removed |
| `_REGISTRY["3-Axes Serration Grind"]` | `machine_config.py` | `has_bcomp=True`, `axes=["A","B","C"]` — needs `screen_classes` and `load_kv` updated |

### DMC Variables Needed
| Variable | Type | Purpose |
|----------|------|---------|
| `numSerr` | scalar | Number of serrations — drives bComp list size; read-only on Run, editable on Parameters |
| `bComp[i]` | array element | Per-serration B-axis compensation value in mm; read all on enter, write one at a time |
| `startPtC` | scalar | Already in `dmc_vars.py` as `STARTPT_C` — used identically by more/less stone panel |
| `HMI_MORE` / `HMI_LESS` | triggers | Same `hmiMore` / `hmiLess` one-shot pattern as Flat Grind — no changes needed |

### No New Dependencies
All required Kivy widgets (BoxLayout, ScrollView, TextInput, Label, Button) are used throughout the flat_grind package. No new pip packages required.

---

## Architecture Patterns

### Recommended Package Structure
```
src/dmccodegui/screens/serration/
├── __init__.py          # load_kv() + class exports
├── run.py               # SerrationRunScreen
├── axes_setup.py        # SerrationAxesSetupScreen
├── parameters.py        # SerrationParametersScreen
└── widgets.py           # BCompPanel

src/dmccodegui/ui/serration/
├── run.kv               # <SerrationRunScreen>:
├── axes_setup.kv        # <SerrationAxesSetupScreen>:
└── parameters.kv        # <SerrationParametersScreen>:
```

### Pattern 1: Package __init__.py (mirrors flat_grind exactly)
**What:** Deferred KV loading via `load_kv()` + class exports. Called from `main.py build()` before Factory instantiation.
**Why:** Avoids circular imports during package init; Kivy #:import directives in KV files need the parent package attribute already set.

```python
# screens/serration/__init__.py
import os
from kivy.lang import Builder

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_UI_DIR = os.path.normpath(os.path.join(_PKG_DIR, '..', '..', 'ui', 'serration'))
_kv_loaded = False

def load_kv() -> None:
    global _kv_loaded
    if _kv_loaded:
        return
    Builder.load_file(os.path.join(_UI_DIR, 'run.kv'))
    Builder.load_file(os.path.join(_UI_DIR, 'axes_setup.kv'))
    Builder.load_file(os.path.join(_UI_DIR, 'parameters.kv'))
    _kv_loaded = True

from .run import SerrationRunScreen          # noqa: E402
from .axes_setup import SerrationAxesSetupScreen  # noqa: E402
from .parameters import SerrationParametersScreen  # noqa: E402

__all__ = [
    "SerrationRunScreen",
    "SerrationAxesSetupScreen",
    "SerrationParametersScreen",
    "load_kv",
]
```

### Pattern 2: Registry Update (machine_config.py)
**What:** Replace flat_grind placeholder entries in `_REGISTRY["3-Axes Serration Grind"]` with real Serration class paths.

```python
# machine_config.py — _REGISTRY["3-Axes Serration Grind"]
{
    "axes": ["A", "B", "C"],
    "has_bcomp": True,
    "param_defs": _SERRATION_PARAM_DEFS,
    "load_kv": "dmccodegui.screens.serration.load_kv",
    "screen_classes": {
        "run":        "dmccodegui.screens.serration.SerrationRunScreen",
        "axes_setup": "dmccodegui.screens.serration.SerrationAxesSetupScreen",
        "parameters": "dmccodegui.screens.serration.SerrationParametersScreen",
    },
}
```

### Pattern 3: SerrationAxesSetupScreen — Trivially thin subclass
**What:** `FlatGrindAxesSetupScreen._rebuild_axis_rows()` already calls `mc.get_axis_list()` and hides the D row via `opacity=0 / disabled=True / size_hint_y=0 / height=0`. The Serration subclass can inherit this unchanged. The 3-axis constraint is automatic.

```python
# screens/serration/axes_setup.py
from ..flat_grind.axes_setup import (
    AXIS_CPM_DEFAULTS, AXIS_LABELS, AXIS_COLORS, _AXIS_ROW_IDS
)
from ..base import BaseAxesSetupScreen

class SerrationAxesSetupScreen(BaseAxesSetupScreen):
    """3-axis axes-setup screen. D-axis hidden automatically via mc.get_axis_list()."""
    # Inherits all of FlatGrindAxesSetupScreen's implementation
    # KV file: ui/serration/axes_setup.kv  (copy of flat_grind/axes_setup.kv, rename rule header)
    ...
```

Note: Serration's KV file is a copy of flat_grind's with `<FlatGrindAxesSetupScreen>:` replaced by `<SerrationAxesSetupScreen>:`. The D-axis row MUST still exist in the KV file (with id `axis_row_d`) because `_rebuild_axis_rows()` looks for it by id; it will just have opacity=0 at runtime.

### Pattern 4: SerrationParametersScreen — numSerr parameter addition
**What:** `BaseParametersScreen._rebuild_for_machine_type()` reads `mc.get_param_defs()` — which for Serration returns `_SERRATION_PARAM_DEFS`. Add `numSerr` to that list in `machine_config.py`.

```python
# machine_config.py — add numSerr to _SERRATION_PARAM_DEFS
_SERRATION_PARAM_DEFS: List[Dict] = [
    d.copy() for d in _FLAT_PARAM_DEFS if d["var"] not in _D_AXIS_VARS
]
_SERRATION_PARAM_DEFS.append({
    "label": "Num Serrations",
    "var": "numSerr",
    "unit": "",
    "group": "Geometry",
    "min": 1.0,
    "max": 200.0,
})
```

The parameters screen class itself is identical to `FlatGrindParametersScreen` — just a renamed thin subclass with its own KV file.

### Pattern 5: BCompPanel Widget
**What:** A new Kivy widget in `screens/serration/widgets.py`. Not a bar chart — a scrollable list of editable rows, one per serration. Uses `ScrollView` + `GridLayout` or `BoxLayout` with `minimum_height` binding.

```python
# screens/serration/widgets.py
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.properties import NumericProperty, ListProperty, StringProperty

BCOMP_MIN_MM: float = -5.0   # reasonable: ±5mm compensation range
BCOMP_MAX_MM: float = 5.0

class BCompPanel(Widget):
    """Scrollable list of per-serration bComp editable fields.

    Driven by num_serrations (read from controller on screen enter).
    Each row: index label + TextInput (mm value) + Save button.

    Save writes bComp[i]=val one element at a time via jobs.submit().
    """
    num_serrations = NumericProperty(0)
    # ...
```

Implementation choice for Claude's discretion: use `GridLayout(cols=3, size_hint_y=None)` with `bind(minimum_height=...)` inside a `ScrollView`. This is the standard Kivy pattern for dynamic scrollable lists without RecycleView complexity. RecycleView is overkill here (serration count is typically under 50).

### Pattern 6: bComp Read/Write Pattern
**What:** Read all `bComp[0]` through `bComp[numSerr-1]` on screen enter. Write one element at a time on Save (per the deltaC precedent).

```python
# In SerrationRunScreen — background job
def _read_bcomp(self):
    ctrl = self.controller
    n = int(float(ctrl.cmd("MG numSerr").strip()))
    values = []
    for i in range(n):
        raw = ctrl.cmd(f"MG bComp[{i}]").strip()
        values.append(float(raw))
    def _apply(*_):
        self._bcomp_values = values
        self._bcomp_panel.load_values(values)
    Clock.schedule_once(_apply)

def _write_bcomp_element(self, index: int, value_mm: float):
    ctrl = self.controller
    def _job():
        ctrl.cmd(f"bComp[{index}]={value_mm:.4f}")
    jobs.submit(_job)
```

Note: `bComp` array name is a placeholder pending the real Serration DMC program. The variable name must be confirmed on hardware. Flag this in code with a TODO comment.

### Pattern 7: Run Screen — D-axis properties stripped
**What:** `SerrationRunScreen` does NOT declare `pos_d` or `cpm_d` Kivy properties. The KV file has no D-axis labels. The matplotlib figure is replaced with a plot stub (Label with placeholder text inside a panel-colored box).

```python
class SerrationRunScreen(BaseRunScreen):
    # 3-axis position strings only
    pos_a = StringProperty("---")
    pos_b = StringProperty("---")
    pos_c = StringProperty("---")
    # No pos_d

    # bComp / numSerr state
    num_serr = NumericProperty(0)
    num_serr_str = StringProperty("Serrations: --")
    # ...
```

### Pattern 8: More/Less Stone Panel (Serration variant)
**What:** Same `HMI_MORE` / `HMI_LESS` trigger pattern, same `startPtC` read. The only difference from Flat Grind is removing tip/heel labels (no DeltaCBarChart section labels). The Python logic is identical.

```python
# From dmc_vars.py (already exists, no changes)
HMI_MORE: str = "hmiMore"
HMI_LESS: str = "hmiLess"
STARTPT_C: str = "startPtC"
```

### Anti-Patterns to Avoid
- **Copying FlatGrindRunScreen's `_fig` / matplotlib imports into SerrationRunScreen:** The Serration run screen has no matplotlib. `cleanup()` inherited from `BaseRunScreen` checks `if fig is not None` — safe to inherit as-is since `_fig` defaults to `None`.
- **Defining a new `_state_unsub` in SerrationRunScreen:** Base owns it. Any additional subscriptions must use a differently-named attribute (e.g., `_bcomp_unsub`).
- **Putting lifecycle hooks in KV files:** All `on_pre_enter`, `on_enter`, `on_leave` must be in Python. Kivy #2565 silently drops `on_pre_enter` for first kv-loaded screen.
- **Using `@` array syntax in controller commands:** The DMC 8-char limit and gclib pattern requires `bComp[i]=val` not `@bComp[i]=val`.
- **Eager KV loading at import time:** Use deferred `load_kv()` pattern — NOT `Builder.load_file()` at module top level. Circular import risk.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 3-axis constraint | Custom axis filter logic | `mc.get_axis_list()` returns `["A","B","C"]` already | Already returns correct list; jog_axis validates against it automatically |
| Param isolation | Custom param filter | `mc.get_param_defs()` with active type | `_SERRATION_PARAM_DEFS` already built; `_rebuild_for_machine_type()` calls it |
| Dirty tracking | Custom change tracking | `BaseParametersScreen._dirty` dict | Fully implemented in base |
| Setup-mode gate | Custom state checks | `SetupScreenMixin._enter/_exit_setup_if_needed()` | Already handles all edge cases |
| Background I/O | Custom threading | `jobs.submit()` | Single patch target in tests; disciplined queue |
| UI thread marshalling | Custom queue | `Clock.schedule_once()` | Standard Kivy pattern; required for Kivy property updates |
| Scrollable list | RecycleView | `ScrollView` + `GridLayout(minimum_height)` | bComp list is small (< 200 rows); RecycleView adds complexity without benefit |
| KV path resolution | Custom path builder | `os.path.normpath(os.path.join(_PKG_DIR, '..', '..', 'ui', 'serration'))` | Same pattern as flat_grind `__init__.py` |

---

## Common Pitfalls

### Pitfall 1: KV Rule Name Collision
**What goes wrong:** If `<SerrationAxesSetupScreen>:` is accidentally named `<FlatGrindAxesSetupScreen>:` in the new KV file, the second rule silently shadows the first. The Flat Grind screen would render with Serration layout.
**Why it happens:** Copy-paste from flat_grind KV files without renaming the `<ClassName>:` header.
**How to avoid:** The existing `test_no_duplicate_kv_rule_headers` test in `tests/test_flat_grind_widgets.py` catches this — it scans all `.kv` files under `ui/`. Adding the new KV files under `ui/serration/` is automatically covered.
**Warning signs:** Test `test_no_duplicate_kv_rule_headers` fails.

### Pitfall 2: D-axis Row Must Exist in KV File
**What goes wrong:** `_rebuild_axis_rows()` calls `self.ids.get("axis_row_d")` and silently skips missing ids. If `axis_row_d` is physically absent from the Serration KV file, no error occurs — but this also means no show/hide is ever applied. At runtime (Serration machine), D would not appear. But if the machine type is reconfigured to Flat Grind later, the axes_setup screen would need to show D — and since screen objects are rebuilt on type swap, this is not a live concern. However, D must still be absent from the Serration KV or it will show up on a Serration machine.
**Resolution:** In `SerrationAxesSetupScreen.kv`, simply omit the `axis_row_d` widget entirely. The `_rebuild_axis_rows()` skips missing ids gracefully. Do NOT include D-axis widgets in Serration KV at all.

### Pitfall 3: numSerr Read Before bComp Panel Sizes
**What goes wrong:** If `on_pre_enter` reads `numSerr` asynchronously but the BCompPanel tries to render before the value arrives, the panel shows 0 rows.
**Why it happens:** Background job completes after `on_pre_enter` returns.
**How to avoid:** `_read_bcomp` job reads `numSerr` first, then reads `bComp[]`, then calls `Clock.schedule_once` to populate the panel with both the count and values in one atomic UI update.

### Pitfall 4: bComp Array Variable Name Unknown
**What goes wrong:** `bComp` is a placeholder name. If the real Serration DMC program uses a different array name, all read/write commands fail silently (gclib returns error or empty).
**Why it happens:** Customer DMC program not yet available.
**How to avoid:** Wrap the DMC array name in a named constant at module top: `BCOMP_ARRAY_VAR = "bComp"`. Add a prominent `# TODO: verify bComp array name against real Serration DMC program` comment. Screen should log a warning if read returns no data.

### Pitfall 5: Serration Registry Not Updated Before Screen Loader Runs
**What goes wrong:** `main.py._add_machine_screens()` resolves class paths from the registry at runtime. If the registry still points to `FlatGrindRunScreen`, the serration machine loads flat grind screens — SERR-01 fails the acceptance test.
**Why it happens:** Forgetting the `machine_config.py` registry update in the same wave as the new screen classes.
**How to avoid:** The registry update and the package creation are in the same plan/wave.

### Pitfall 6: _btn_unsub Leak in SerrationParametersScreen
**What goes wrong:** `FlatGrindParametersScreen.on_pre_enter` adds a second subscription (`_btn_unsub`) for apply button gating. If `SerrationParametersScreen` copies this and `on_leave` does not clean it up, subscriptions accumulate.
**How to avoid:** Copy the full `on_leave` override from `FlatGrindParametersScreen` which unsubscribes `_btn_unsub` before calling `super().on_leave()`.

---

## Code Examples

### BCompPanel scrollable list (pure Python, no KV needed for internal structure)
```python
# Source: Kivy ScrollView + GridLayout minimum_height pattern (Kivy docs)
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty

class BCompPanel(Widget):
    num_serrations = NumericProperty(0)

    def build_rows(self, values: list[float]) -> None:
        """Rebuild the scroll list from a list of float values."""
        self.clear_widgets()
        sv = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=3, size_hint_y=None, spacing=4, padding=4)
        grid.bind(minimum_height=grid.setter('height'))
        for i, val in enumerate(values):
            grid.add_widget(Label(text=str(i), size_hint_y=None, height=44))
            ti = TextInput(text=f"{val:.4f}", multiline=False,
                           size_hint_y=None, height=44)
            ti.bind(on_text_validate=lambda w, idx=i: self._on_save(idx, w.text))
            grid.add_widget(ti)
            btn = Button(text="Save", size_hint_y=None, height=44)
            btn.bind(on_release=lambda b, idx=i, w=ti: self._on_save(idx, w.text))
            grid.add_widget(btn)
        sv.add_widget(grid)
        self.add_widget(sv)

    def _on_save(self, index: int, text: str) -> None:
        # Validated and dispatched to parent screen via callback
        pass
```

### Registry update pattern (machine_config.py)
```python
# Replace the TODO placeholder in _REGISTRY["3-Axes Serration Grind"]
"3-Axes Serration Grind": {
    "axes": ["A", "B", "C"],
    "has_bcomp": True,
    "param_defs": _SERRATION_PARAM_DEFS,
    "load_kv": "dmccodegui.screens.serration.load_kv",
    "screen_classes": {
        "run":        "dmccodegui.screens.serration.SerrationRunScreen",
        "axes_setup": "dmccodegui.screens.serration.SerrationAxesSetupScreen",
        "parameters": "dmccodegui.screens.serration.SerrationParametersScreen",
    },
},
```

### numSerr param definition
```python
# Recommended: add to _SERRATION_PARAM_DEFS after D-axis removal
{
    "label": "Num Serrations",
    "var": "numSerr",
    "unit": "",
    "group": "Geometry",
    "min": 1.0,
    "max": 200.0,
}
```
Rationale for 1–200: serration knives typically have 5–100 serrations; 200 is a safe ceiling. Group "Geometry" fits with the other shape parameters.

---

## State of the Art

| Old State | Current State | Impact |
|-----------|---------------|--------|
| Serration registry pointed at FlatGrind placeholders | Phase 21 replaces with real Serration classes | Connecting with Serration machine type now loads distinct screen set |
| BCompBarChart referenced in old run.py (removed in Phase 19) | Phase 21 creates BCompPanel from scratch | No dead code reuse |
| D-axis hidden in FlatGrindAxesSetupScreen via mc.get_axis_list() | SerrationAxesSetupScreen inherits this | Zero new axis-filter logic needed |

**Deprecated/outdated:**
- `FlatGrindRunScreen.is_serration` property: this was a flag on the flat grind screen to toggle Serration-specific visibility. With a dedicated `SerrationRunScreen`, that property is no longer needed in the Serration screen. It remains in `FlatGrindRunScreen` for its own layout control but should NOT be copied into `SerrationRunScreen`.

---

## Open Questions

1. **bComp DMC array variable name**
   - What we know: The Python placeholder uses `bComp` throughout (confirmed in CONTEXT.md, STATE.md)
   - What's unclear: Whether the real Serration DMC program uses `bComp`, `bcomp`, or a different name
   - Recommendation: Use named constant `BCOMP_ARRAY_VAR = "bComp"` with a visible TODO comment; validate on first hardware connection

2. **numSerr DMC variable name**
   - What we know: CONTEXT.md uses `numSerr` consistently
   - What's unclear: Exact casing in the DMC program (Galil is case-sensitive for array names but generally case-insensitive for scalar variable names in some contexts)
   - Recommendation: Use `BCOMP_NUM_SERR_VAR = "numSerr"` constant; flag for hardware verification

3. **More/less stone panel applicability**
   - What we know: CONTEXT.md says same `startPtC` logic and DMC variables as Flat Grind
   - What's unclear: Whether the Serration DMC program actually uses `hmiMore`/`hmiLess` with the same semantics
   - Recommendation: Implement identically to Flat Grind; flag with TODO for hardware validation

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (inferred from `.cpython-313-pytest-9.0.2.pyc` cache files) |
| Quick run command | `pytest tests/test_serration_screens.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SERR-01 | Serration machine type loads SerrationRunScreen (not FlatGrindRunScreen) | unit | `pytest tests/test_serration_screens.py::test_serration_run_screen_importable -x` | Wave 0 |
| SERR-01 | SerrationRunScreen has no pos_d property | unit | `pytest tests/test_serration_screens.py::test_serration_run_screen_no_d_axis -x` | Wave 0 |
| SERR-01 | Registry for "3-Axes Serration Grind" resolves to SerrationRunScreen | unit | `pytest tests/test_serration_screens.py::test_registry_points_to_serration_classes -x` | Wave 0 |
| SERR-02 | SerrationAxesSetupScreen importable and is subclass of BaseAxesSetupScreen | unit | `pytest tests/test_serration_screens.py::test_serration_axes_setup_inherits_base -x` | Wave 0 |
| SERR-02 | No D-axis widgets in serration/axes_setup.kv | static | `pytest tests/test_serration_screens.py::test_serration_axes_setup_kv_no_d_axis -x` | Wave 0 |
| SERR-03 | SerrationParametersScreen writes only _SERRATION_PARAM_DEFS vars | unit | `pytest tests/test_serration_screens.py::test_serration_params_no_d_axis_vars -x` | Wave 0 |
| SERR-03 | numSerr is in _SERRATION_PARAM_DEFS | unit | `pytest tests/test_serration_screens.py::test_serration_param_defs_has_numserr -x` | Wave 0 |
| SERR-04 | BCompPanel importable from screens.serration.widgets | unit | `pytest tests/test_serration_screens.py::test_bcomp_panel_importable -x` | Wave 0 |
| SERR-04 | BCompPanel renders N rows for numSerr=N (no crash) | unit | `pytest tests/test_serration_screens.py::test_bcomp_panel_renders_rows -x` | Wave 0 |
| ALL | No duplicate KV rule headers (extends existing test) | static | `pytest tests/test_flat_grind_widgets.py::test_no_duplicate_kv_rule_headers -x` | Exists |

### Sampling Rate
- **Per task commit:** `pytest tests/test_serration_screens.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_serration_screens.py` — all SERR-* test functions listed above
- [ ] `src/dmccodegui/ui/serration/` directory — must exist before KV files can be loaded
- [ ] `src/dmccodegui/screens/serration/` directory — package root

---

## Sources

### Primary (HIGH confidence — all read from source files in this repo)
- `src/dmccodegui/screens/flat_grind/__init__.py` — exact load_kv pattern to replicate
- `src/dmccodegui/screens/flat_grind/run.py` — FlatGrindRunScreen: properties to strip (pos_d, cpm_d, delta_c_offsets, matplotlib), properties to keep (cycle_running, pos_a/b/c, motion_active, start_pt_c)
- `src/dmccodegui/screens/flat_grind/axes_setup.py` — `_rebuild_axis_rows()` confirmed uses `mc.get_axis_list()` with opacity/disabled/size_hint_y pattern
- `src/dmccodegui/screens/flat_grind/parameters.py` — `FlatGrindParametersScreen` thin subclass pattern; `_btn_unsub` second subscription
- `src/dmccodegui/screens/flat_grind/widgets.py` — confirmed `_BaseBarChart` is NOT to be reused for BCompPanel
- `src/dmccodegui/screens/base.py` — full base class API; cleanup() teardown order; `_state_unsub` ownership rule
- `src/dmccodegui/machine_config.py` — `_SERRATION_PARAM_DEFS` already built; registry structure; `_D_AXIS_VARS` set
- `src/dmccodegui/hmi/dmc_vars.py` — `HMI_MORE`, `HMI_LESS`, `STARTPT_C` confirmed available; no bComp/numSerr constants exist yet
- `src/dmccodegui/main.py` — `_add_machine_screens()` resolves dotted paths from registry at runtime
- `tests/test_flat_grind_widgets.py` — `test_no_duplicate_kv_rule_headers` already covers all .kv files including future `ui/serration/`
- `tests/test_base_classes.py` — test pattern for screen instantiation, enter/leave lifecycle, two-cycle no-leak tests

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified from source code; all referenced APIs and classes exist exactly as described
- Architecture: HIGH — all patterns copied from working flat_grind implementation; no new external libraries
- Pitfalls: HIGH — KV collision test already exists; D-axis row pattern verified in axes_setup.py; registry path verified in main.py
- bComp DMC variable name: LOW — flagged as hardware-validation item; not verifiable without Serration DMC program

**Research date:** 2026-04-13
**Valid until:** Stable — internal codebase; no external dependencies changing
