# Phase 22: Convex Screen Set - Research

**Researched:** 2026-04-13
**Domain:** Kivy per-machine screen package, copy-then-modify pattern, Python widget classes
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Convex adjustment panel**
- Same base controls as Flat Grind (DeltaC bar chart, more/less stone with tip/heel labels, startPtC offset) — carried over unchanged
- Additional "Convex Adjustments" panel as a labeled section with placeholder text ("Pending customer specs")
- Own widget class `ConvexAdjustPanel` in `screens/convex/widgets.py` — clean separation
- Panel content and behavior are TBD pending customer specifications

**Axis roles and labels**
- Same roles as Flat Grind: A=cross-travel, B=in-feed, C=stone-advance, D=wheel-dress
- Same accent colors: A=orange, B=purple, C=cyan, D=yellow
- Same teach points (rest point + start point per axis) and same jog workflow

**Run screen layout**
- Keeps live A/B matplotlib position plot (toolpath preview + live trace)
- Keeps DeltaC bar chart with tip/heel labels and up/down arrows
- Keeps more/less stone panel with startPtC offset logic
- Keeps cycle controls: Start, Stop, session/station counters, progress bar, controller message log
- ConvexAdjustPanel added to layout — position at Claude's discretion

**Param_defs**
- `_CONVEX_PARAM_DEFS` explicitly defined as its own list (NOT a shallow copy)
- Same groups as Flat Grind for now: Geometry, Feedrates, Calibration — all 4 axes
- Single top-level placeholder comment: "Placeholder — mirrors Flat Grind, pending customer convex specs"
- No dynamic bridging parameter (like numSerr) for now

**Screen package structure**
- Copy flat_grind package as starting point, then modify — full independence (Phase 21 pattern)
- Package: `screens/convex/` with `__init__.py`, `run.py`, `axes_setup.py`, `parameters.py`, `widgets.py`
- `__init__.py` exports `load_kv()` + all three Convex screen classes (deferred loading pattern from Phase 19)
- KV files in `ui/convex/`: `run.kv`, `axes_setup.kv`, `parameters.kv`
- Update `machine_config._REGISTRY["4-Axes Convex Grind"]` to point to real Convex classes and load_kv

**Testing**
- Mirror Flat Grind test patterns: screen instantiation, expected widgets present
- ConvexAdjustPanel renders with placeholder content
- KV rule name collision check: grep for duplicate `<ClassName>:` headers across all .kv files
- Same test coverage approach as Phase 21 (Serration)

### Claude's Discretion
- ConvexAdjustPanel position in run screen layout
- ConvexAdjustPanel placeholder visual design
- Exact KV layout proportions and spacing
- Test file organization
- widgets.py internal structure for ConvexAdjustPanel

### Deferred Ideas (OUT OF SCOPE)
- Convex-specific adjustment controls — add when customer provides real convex specifications
- Additional convex-specific parameters — add when customer provides real DMC variable list
- Dynamic bridging parameter (numSerr equivalent)
- Convex plot visualization customization
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONV-01 | ConvexRunScreen created from Flat Grind base with convex-specific adjustment panel | Copy flat_grind/run.py → convex/run.py; add ConvexAdjustPanel widget instance; import from convex/widgets.py |
| CONV-02 | ConvexAxesSetupScreen created with 4-axis layout | Copy flat_grind/axes_setup.py → convex/axes_setup.py; copy axes_setup.kv with all 4 axis rows present (A, B, C, D) |
| CONV-03 | ConvexParametersScreen created with convex-specific parameter groups | Copy flat_grind/parameters.py → convex/parameters.py; re-export `_CONVEX_PARAM_DEFS` as PARAM_DEFS |
| CONV-04 | Placeholder param_defs noted — production sign-off requires real customer specs | Replace `_CONVEX_PARAM_DEFS = [d.copy() for d in _FLAT_PARAM_DEFS]` with an explicit list literal bearing a placeholder comment |
</phase_requirements>

---

## Summary

Phase 22 creates a `screens/convex/` package that mirrors the `screens/flat_grind/` package exactly, with two targeted differences: (1) a `ConvexAdjustPanel` placeholder widget added to the run screen left column, and (2) `_CONVEX_PARAM_DEFS` promoted from a shallow copy expression to a fully explicit list literal with a placeholder comment. Every other element — axes, colors, matplotlib plot, DeltaC bar chart, more/less stone, teach-point workflow — is identical to Flat Grind.

The Phase 21 (Serration) work established that the copy-then-modify pattern is the correct approach. Serration diverged structurally (3 axes, no matplotlib, bComp panel). Convex diverges minimally — it is Flat Grind plus one labeled placeholder panel — making the copy even more straightforward.

The only integration touch-point outside the new package is `machine_config.py`: replace the `_CONVEX_PARAM_DEFS` expression and update the `"4-Axes Convex Grind"` registry entry's `load_kv` and `screen_classes` dotted paths. `main.py._add_machine_screens()` requires no changes.

**Primary recommendation:** Copy `screens/flat_grind/` in its entirety to `screens/convex/`, rename all class identifiers from `FlatGrind*` to `Convex*`, copy `ui/flat_grind/` KV files to `ui/convex/` updating their `#:import` paths, add `ConvexAdjustPanel` to `convex/widgets.py` and wire it into `run.kv`, then update `machine_config.py`. Write a `tests/test_convex_screens.py` mirroring `test_serration_screens.py`.

---

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Kivy | >=2.2.0 | Widget framework, KV language, Screen lifecycle | Project foundation |
| kivy_matplotlib_widget | installed | MatplotFigure KV widget for live A/B plot | Required by FlatGrindRunScreen; Convex keeps same plot |
| matplotlib | installed | Figure/axes for live position trace | Same as above |
| pytest | installed | Test runner | Project test framework (pyproject.toml testpaths=tests) |

No new packages are required. All libraries used by Flat Grind transfer to Convex without modification.

**Installation:** None needed.

---

## Architecture Patterns

### Recommended Package Structure

```
src/dmccodegui/screens/convex/
├── __init__.py          # load_kv() + exports
├── run.py               # ConvexRunScreen
├── axes_setup.py        # ConvexAxesSetupScreen
├── parameters.py        # ConvexParametersScreen
└── widgets.py           # ConvexAdjustPanel

src/dmccodegui/ui/convex/
├── run.kv               # <ConvexRunScreen>: layout
├── axes_setup.kv        # <ConvexAxesSetupScreen>: layout
└── parameters.kv        # <ConvexParametersScreen>: layout

tests/
└── test_convex_screens.py
```

### Pattern 1: Deferred KV Loading (`__init__.py`)

**What:** `load_kv()` function loads KV files on demand; called from `main.py build()` before `Factory.RootLayout()`. Not called at import time to avoid circular import via `#:import` directives in KV files.

**When to use:** Every per-machine screen package in this project.

**Example:**
```python
# Source: screens/flat_grind/__init__.py (verbatim pattern)
import os
from kivy.lang import Builder

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_UI_DIR = os.path.normpath(os.path.join(_PKG_DIR, '..', '..', 'ui', 'convex'))

_kv_loaded = False

def load_kv() -> None:
    """Load Convex KV files. Safe to call multiple times (idempotent)."""
    global _kv_loaded
    if _kv_loaded:
        return
    Builder.load_file(os.path.join(_UI_DIR, 'run.kv'))
    Builder.load_file(os.path.join(_UI_DIR, 'axes_setup.kv'))
    Builder.load_file(os.path.join(_UI_DIR, 'parameters.kv'))
    _kv_loaded = True

from .run import ConvexRunScreen          # noqa: E402
from .axes_setup import ConvexAxesSetupScreen  # noqa: E402
from .parameters import ConvexParametersScreen  # noqa: E402

__all__ = [
    "ConvexRunScreen",
    "ConvexAxesSetupScreen",
    "ConvexParametersScreen",
    "load_kv",
]
```

### Pattern 2: KV Import Paths for Convex

**What:** KV files use `#:import` at the top to bring in Python symbols. The path must reference `convex` module, not `flat_grind`.

**Example (run.kv header):**
```kv
#:import theme dmccodegui.theme_manager.theme
#:import DeltaCBarChart dmccodegui.screens.flat_grind.widgets
#:import run_module dmccodegui.screens.convex.run
#:import kivy_matplotlib_widget kivy_matplotlib_widget

<ConvexRunScreen>:
    ...
```

Note: `DeltaCBarChart` is still imported from `flat_grind.widgets` — that module is not duplicated into convex. `ConvexAdjustPanel` is imported from `dmccodegui.screens.convex.widgets`.

### Pattern 3: ConvexAdjustPanel — Labeled Placeholder Widget

**What:** A `BoxLayout` subclass with a visible label section header and "Pending customer specs" placeholder text. No DMC I/O. No callbacks required at this stage.

**When to use:** Left column of `run.kv`, between the DeltaC bar chart and more/less stone panel (or below it — Claude's discretion).

**Example (widgets.py):**
```python
# Source: pattern from serration/widgets.py BCompPanel header section
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.metrics import dp

class ConvexAdjustPanel(BoxLayout):
    """Placeholder panel for convex-specific adjustments.

    Will hold convex-specific controls once customer provides real
    convex specifications. Currently displays a labeled placeholder.

    TODO: Replace placeholder content with real controls after customer sign-off.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault('orientation', 'vertical')
        super().__init__(**kwargs)

        header = Label(
            text='Convex Adjustments',
            font_size='13sp',
            bold=True,
            color=[0.024, 0.714, 0.831, 1],  # cyan accent
            size_hint_y=None,
            height=dp(32),
            halign='left',
            valign='middle',
        )
        header.bind(size=header.setter('text_size'))
        self.add_widget(header)

        placeholder = Label(
            text='Pending customer specs',
            font_size='12sp',
            color=[0.396, 0.455, 0.545, 1],  # subdued grey
            halign='center',
            valign='middle',
        )
        self.add_widget(placeholder)
```

### Pattern 4: `_CONVEX_PARAM_DEFS` as Explicit List (machine_config.py)

**What:** Replace the existing shallow-copy expression with a full literal list that independently defines the same parameters as Flat Grind for now, bearing a comment marking it as a placeholder.

**Current (wrong — shallow copy, not independent):**
```python
_CONVEX_PARAM_DEFS: List[Dict] = [d.copy() for d in _FLAT_PARAM_DEFS]
```

**Correct (explicit independent list with placeholder comment):**
```python
# Placeholder — mirrors Flat Grind, pending customer convex specs.
# Replace entries with real convex DMC variable names after customer sign-off (CONV-05).
_CONVEX_PARAM_DEFS: List[Dict] = [
    {"label": "Knife Thickness", "var": "knfThk",  "unit": "mm",     "group": "Geometry",    "min": 0.1,   "max": 50.0},
    {"label": "Edge Thickness",  "var": "edgeThk",  "unit": "mm",     "group": "Geometry",    "min": 0.01,  "max": 10.0},
    {"label": "Feed Rate A",     "var": "fdA",       "unit": "mm/s",  "group": "Feedrates",   "min": 0.1,   "max": 500.0},
    # ... (all remaining Flat Grind entries, including D-axis entries)
]
```

### Pattern 5: Registry Update (machine_config.py)

**What:** Replace the `"4-Axes Convex Grind"` entry's `load_kv` and `screen_classes` strings to point to the new convex package.

**Example:**
```python
"4-Axes Convex Grind": {
    "axes": ["A", "B", "C", "D"],
    "has_bcomp": False,
    "param_defs": _CONVEX_PARAM_DEFS,
    "load_kv": "dmccodegui.screens.convex.load_kv",
    "screen_classes": {
        "run":        "dmccodegui.screens.convex.ConvexRunScreen",
        "axes_setup": "dmccodegui.screens.convex.ConvexAxesSetupScreen",
        "parameters": "dmccodegui.screens.convex.ConvexParametersScreen",
    },
},
```

### Anti-Patterns to Avoid

- **Importing from flat_grind inside convex Python files:** The only acceptable cross-package import from flat_grind is `DeltaCBarChart` in the KV file via `#:import`. Python classes in `convex/run.py`, `convex/axes_setup.py`, `convex/parameters.py` must import from `..base` and `..` (the screens package), never from `..flat_grind.*`.
- **Eager KV loading at import time:** Never call `Builder.load_file()` at module level in `__init__.py`. It must be inside `load_kv()` (guarded by `_kv_loaded`).
- **Duplicate `<ClassName>:` KV rules:** All six Convex KV rule headers must use `Convex*` names, never reusing any name already defined in flat_grind or serration KV files.
- **Copying `_FLAT_PARAM_DEFS` with list comprehension:** The `[d.copy() for d in _FLAT_PARAM_DEFS]` expression leaves `_CONVEX_PARAM_DEFS` invisibly coupled to `_FLAT_PARAM_DEFS`. Use an explicit literal list.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Background controller I/O | Custom thread/queue | `jobs.submit()` via module-level `submit` import in base.py | All screens already use this pattern; base.py exports `submit` as the single patch target for tests |
| UI thread updates from background | Direct widget mutation in background thread | `Clock.schedule_once(lambda *_: ...)` | Kivy requires all widget updates on main thread |
| Screen lifecycle (enter/leave) | Custom flags | `BaseRunScreen.on_pre_enter` / `on_leave` subscribe/unsubscribe pattern | Base class enforces subscribe-on-enter / unsubscribe-on-leave (ARCH-02) |
| Parameter card UI | Custom form widgets | `BaseParametersScreen.build_param_cards()` | Base class builds grouped cards with dirty tracking, validation, apply/read — zero new code needed |
| Setup-mode entry/exit | Custom hmiSetp calls | `SetupScreenMixin._enter_setup_if_needed()` / `_exit_setup_if_needed()` | Already in base class; axes_setup and parameters screens inherit it |
| Axis jog commands | Direct PR/BG strings | `BaseAxesSetupScreen.jog_axis()` (gated on STATE_SETUP + `_cpm_ready`) | Handles counts calculation, STATE_SETUP gate, and _BG flag check |

---

## Common Pitfalls

### Pitfall 1: KV Rule Name Collision

**What goes wrong:** Two KV files define `<SameClassName>:`. The second file loaded silently shadows the first. Convex screens render as Flat Grind screens (or vice versa).

**Why it happens:** Kivy's `Builder` is global; rule names are not namespaced. If any convex KV file accidentally uses `FlatGrind*` class names in its rule headers, it will shadow the flat_grind rules loaded earlier.

**How to avoid:** Every KV rule header in `ui/convex/` must use `Convex*` class names. After writing, run a grep across all KV files checking for duplicate `<ClassName>:` headers. The test file should include this check.

**Warning signs:** Screen loads but displays Flat Grind widgets; `ids.get('convex_adjust_panel')` returns None.

### Pitfall 2: `#:import` Path Still Points to flat_grind

**What goes wrong:** After copying `ui/flat_grind/run.kv` to `ui/convex/run.kv`, the `#:import run_module` path is still `dmccodegui.screens.flat_grind.run`. Any references to `run_module.*` constants in convex KV will silently use flat_grind values.

**Why it happens:** Copy-paste without updating import paths.

**How to avoid:** In `ui/convex/run.kv`, update `#:import run_module` to point to `dmccodegui.screens.convex.run`. The `DeltaCBarChart` import from `flat_grind.widgets` is intentional and correct — do not change it.

### Pitfall 3: `_CONVEX_PARAM_DEFS` Remains a Shallow Copy

**What goes wrong:** The current `machine_config.py` has `_CONVEX_PARAM_DEFS: List[Dict] = [d.copy() for d in _FLAT_PARAM_DEFS]`. Mutating either list at runtime affects the other. Future additions to `_FLAT_PARAM_DEFS` silently change Convex params too.

**Why it happens:** Phase 20 intentionally used a placeholder. Phase 22 must replace it with an explicit list literal.

**How to avoid:** Replace the comprehension with a full literal list. CONV-04 test should verify the list is independently defined and contains a code comment marking it as a placeholder.

### Pitfall 4: Forgetting `main.py` KV Load Call

**What goes wrong:** If `load_kv()` is not called from `main.py` before `Factory.RootLayout()`, Kivy raises `FactoryException` when trying to instantiate `ConvexRunScreen` from KV.

**Why it happens:** The convex package uses deferred loading — `load_kv()` is not called automatically at import time.

**How to avoid:** Check `main.py._add_machine_screens()` — it calls `load_kv()` from the registry's `load_kv` dotted path using `importlib`. The registry entry update (Pattern 5) is sufficient. No direct edit to `main.py` required.

**Verification:** `main.py` uses `importlib` to dynamically call `load_kv` from the registry string:
```python
"load_kv": "dmccodegui.screens.convex.load_kv"
```
This is resolved at connect time. If the string is correct, `main.py` will call `convex.load_kv()` automatically.

### Pitfall 5: ConvexAdjustPanel Has No `id` in KV

**What goes wrong:** Test tries `screen.ids.get('convex_adjust_panel')` but the KV file did not assign `id: convex_adjust_panel` to the panel instance.

**How to avoid:** Assign `id: convex_adjust_panel` to the `ConvexAdjustPanel:` widget in `run.kv`. Tests can then verify the widget is present and correctly typed.

### Pitfall 6: `pos_d` Missing from ConvexRunScreen Properties

**What goes wrong:** Flat Grind run screen has `pos_d = StringProperty("---")`. If the copy-then-rename accidentally drops this property, the KV file will error because it binds `root.pos_d`.

**How to avoid:** Convex is 4-axis — keep `pos_d` in `ConvexRunScreen`. The Serration pattern (drop pos_d) does NOT apply here.

---

## Code Examples

Verified patterns from existing codebase:

### ConvexRunScreen class header (run.py)
```python
# Source: screens/flat_grind/run.py + screens/serration/run.py patterns
from ..base import BaseRunScreen
from .widgets import ConvexAdjustPanel
from dmccodegui.screens.flat_grind.widgets import (
    DeltaCBarChart,
    _BaseBarChart,
    DELTA_C_WRITABLE_START,
    DELTA_C_WRITABLE_END,
    DELTA_C_ARRAY_SIZE,
    DELTA_C_STEP,
    stone_window_for_index,
)

class ConvexRunScreen(BaseRunScreen):
    """ConvexRunScreen — operator run screen for Convex grinding machines.

    4-axis (A, B, C, D) position display, live matplotlib A/B plot,
    DeltaC bar chart, more/less stone panel, cycle controls,
    and ConvexAdjustPanel placeholder.

    KV file: ui/convex/run.kv
    """
    # 4-axis properties (identical to FlatGrindRunScreen)
    pos_a = StringProperty("---")
    pos_b = StringProperty("---")
    pos_c = StringProperty("---")
    pos_d = StringProperty("---")  # D-axis present (4-axis machine)
    ...
```

### ConvexParametersScreen PARAM_DEFS re-export (parameters.py)
```python
# Source: screens/flat_grind/parameters.py + screens/serration/parameters.py patterns
from dmccodegui.machine_config import _CONVEX_PARAM_DEFS as PARAM_DEFS  # noqa: F401
```

### Test: registry does not point to flat_grind (test_convex_screens.py)
```python
def test_registry_points_to_convex_classes():
    from dmccodegui.machine_config import _REGISTRY
    convex_entry = _REGISTRY["4-Axes Convex Grind"]
    screen_classes = convex_entry["screen_classes"]
    for role, dotted_path in screen_classes.items():
        assert "convex" in dotted_path, f"screen_classes['{role}'] must reference convex module"
        assert "flat_grind" not in dotted_path, f"screen_classes['{role}'] must NOT reference flat_grind"
```

### Test: ConvexAdjustPanel renders without error
```python
def test_convex_adjust_panel_importable():
    from dmccodegui.screens.convex.widgets import ConvexAdjustPanel
    from kivy.uix.boxlayout import BoxLayout
    assert issubclass(ConvexAdjustPanel, BoxLayout)
    panel = ConvexAdjustPanel()
    # Panel must have children (header + placeholder label)
    assert len(panel.children) >= 1
```

### Test: _CONVEX_PARAM_DEFS is independent (not same object as _FLAT_PARAM_DEFS)
```python
def test_convex_param_defs_independent():
    from dmccodegui.machine_config import _CONVEX_PARAM_DEFS, _FLAT_PARAM_DEFS
    assert _CONVEX_PARAM_DEFS is not _FLAT_PARAM_DEFS, (
        "_CONVEX_PARAM_DEFS must be a separate list object from _FLAT_PARAM_DEFS"
    )
    # Spot check: modifying one does not affect the other
    original_len = len(_CONVEX_PARAM_DEFS)
    assert original_len == len(_FLAT_PARAM_DEFS), (
        "Both should have same number of entries since Convex mirrors Flat Grind for now"
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single RunScreen / AxesSetupScreen / ParametersScreen | Per-machine screen packages in `screens/{machine}/` | Phase 19 | Full layout independence; each machine type has its own KV files |
| Eager KV loading at import | Deferred `load_kv()` called from `main.py build()` | Phase 19 | Avoids circular imports from `#:import` directives in KV files |
| Placeholder `[d.copy() for d in _FLAT_PARAM_DEFS]` | Explicit `_CONVEX_PARAM_DEFS` literal | Phase 22 (this phase) | Independent editability for future convex-specific parameters |
| Flat Grind placeholders in Convex registry | Real Convex class dotted paths | Phase 22 (this phase) | Connecting with convex machine loads Convex screens, not Flat Grind |

**Deprecated/outdated:**
- `_CONVEX_PARAM_DEFS = [d.copy() for d in _FLAT_PARAM_DEFS]`: Replace with explicit literal in this phase.
- `"load_kv": "dmccodegui.screens.flat_grind.load_kv"` in Convex registry entry: Replace with `dmccodegui.screens.convex.load_kv`.
- Flat Grind class names in `_REGISTRY["4-Axes Convex Grind"]["screen_classes"]`: Replace with Convex class names.

---

## Open Questions

1. **ConvexAdjustPanel position in run.kv left column**
   - What we know: Left column has: matplotlib plot (top, large), DeltaC bar chart (mid), more/less stone (bottom). Adding a 4th section will shrink proportions.
   - What's unclear: Whether panel goes between DeltaC and more/less stone, or below more/less stone.
   - Recommendation: Place below the DeltaC bar chart, above the more/less stone panel. Use `size_hint_y: None; height: '80dp'` so it takes minimal space as a placeholder. Panel will grow when real controls are added.

2. **Whether `DeltaCBarChart` import in convex KV files should remain from `flat_grind.widgets`**
   - What we know: `DeltaCBarChart` lives in `screens/flat_grind/widgets.py`. Convex uses the same widget without modification.
   - What's unclear: Whether the planner should copy `flat_grind/widgets.py` into `convex/widgets.py` alongside `ConvexAdjustPanel`, or keep them separate.
   - Recommendation: Do NOT copy `flat_grind/widgets.py` into convex. Keep `DeltaCBarChart` imported from `flat_grind.widgets` in the KV file. `convex/widgets.py` only contains `ConvexAdjustPanel`. This avoids code duplication. The KV `#:import` line `#:import DeltaCBarChart dmccodegui.screens.flat_grind.widgets` is intentionally cross-package.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (pyproject.toml: `[tool.pytest.ini_options] testpaths = ["tests"]`) |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/test_convex_screens.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONV-01 | ConvexRunScreen importable, is subclass of BaseRunScreen | unit | `pytest tests/test_convex_screens.py::test_convex_run_screen_importable -x` | Wave 0 |
| CONV-01 | ConvexRunScreen has pos_a, pos_b, pos_c, pos_d properties (4-axis) | unit | `pytest tests/test_convex_screens.py::test_convex_run_screen_has_all_4_axes -x` | Wave 0 |
| CONV-01 | ConvexAdjustPanel importable from convex.widgets, subclass of BoxLayout | unit | `pytest tests/test_convex_screens.py::test_convex_adjust_panel_importable -x` | Wave 0 |
| CONV-01 | Registry screen_classes for Convex contain "convex" not "flat_grind" | unit | `pytest tests/test_convex_screens.py::test_registry_points_to_convex_classes -x` | Wave 0 |
| CONV-02 | ConvexAxesSetupScreen importable, is subclass of BaseAxesSetupScreen | unit | `pytest tests/test_convex_screens.py::test_convex_axes_setup_importable -x` | Wave 0 |
| CONV-02 | ui/convex/axes_setup.kv exists and contains axis_row_d | unit | `pytest tests/test_convex_screens.py::test_convex_axes_setup_kv_has_d_axis -x` | Wave 0 |
| CONV-03 | ConvexParametersScreen importable, is subclass of BaseParametersScreen | unit | `pytest tests/test_convex_screens.py::test_convex_params_importable -x` | Wave 0 |
| CONV-04 | _CONVEX_PARAM_DEFS is not the same object as _FLAT_PARAM_DEFS | unit | `pytest tests/test_convex_screens.py::test_convex_param_defs_independent -x` | Wave 0 |
| CONV-04 | machine_config.py contains placeholder comment for _CONVEX_PARAM_DEFS | unit | `pytest tests/test_convex_screens.py::test_convex_param_defs_has_placeholder_comment -x` | Wave 0 |
| All | KV rule name collision check — no duplicate <ClassName>: across all KV files | unit | `pytest tests/test_convex_screens.py::test_no_kv_rule_name_collisions -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_convex_screens.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_convex_screens.py` — covers all CONV-01 through CONV-04 tests above
- [ ] `src/dmccodegui/screens/convex/__init__.py` — package skeleton
- [ ] `src/dmccodegui/ui/convex/` — directory with KV files

*(Existing test infrastructure — pytest, conftest.py, Kivy env vars pattern — fully covers all other infrastructure needs.)*

---

## Sources

### Primary (HIGH confidence)

- `src/dmccodegui/screens/flat_grind/__init__.py` — Deferred `load_kv()` pattern; exact `__all__` export shape
- `src/dmccodegui/screens/serration/__init__.py` — Phase 21 confirmation of the identical pattern for a second machine type
- `src/dmccodegui/machine_config.py` — Exact current state of `_CONVEX_PARAM_DEFS` (shallow copy), `_REGISTRY["4-Axes Convex Grind"]` (Flat Grind placeholders), and full `_FLAT_PARAM_DEFS` list to copy as literal
- `src/dmccodegui/screens/flat_grind/run.py` — Import list, Kivy property declarations, `ConvexRunScreen` must keep all 4 `pos_*` properties
- `src/dmccodegui/screens/flat_grind/widgets.py` — `DeltaCBarChart` lives here; correct cross-package import path for KV files
- `src/dmccodegui/screens/serration/widgets.py` — `BCompPanel` as structural model for `ConvexAdjustPanel` (BoxLayout with header + content)
- `src/dmccodegui/screens/flat_grind/axes_setup.py` — Full `FlatGrindAxesSetupScreen` implementation; `ConvexAxesSetupScreen` copies with rename only
- `src/dmccodegui/screens/flat_grind/parameters.py` — Full `FlatGrindParametersScreen`; `ConvexParametersScreen` copies with `_CONVEX_PARAM_DEFS` re-export
- `tests/test_serration_screens.py` — Template for `test_convex_screens.py`; 18-test structure to mirror
- `pyproject.toml` — pytest config; `testpaths = ["tests"]`; `pytest tests/test_convex_screens.py -x` is the correct quick run command
- `.planning/phases/22-convex-screen-set/22-CONTEXT.md` — All locked decisions verified

### Secondary (MEDIUM confidence)

- `src/dmccodegui/ui/flat_grind/run.kv` — KV `#:import` header format; `<FlatGrindRunScreen>:` layout structure; left column proportions for placing `ConvexAdjustPanel`
- `src/dmccodegui/ui/serration/run.kv` — Confirms the `#:import BCompPanel` cross-package import pattern is acceptable in KV files
- `.planning/STATE.md` Accumulated Context section — Critical pitfalls list (KV rule collision, thread leak on screen removal, etc.)

### Tertiary (LOW confidence)

- None required. All research findings are grounded in direct code reading.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — No new dependencies; all packages already installed and verified in flat_grind and serration packages
- Architecture: HIGH — Pattern is identical to Phase 19 (Flat Grind) and Phase 21 (Serration); both packages exist as verified reference implementations
- Pitfalls: HIGH — All pitfalls sourced from actual code issues documented in STATE.md accumulated context plus direct code reading
- Test patterns: HIGH — `test_serration_screens.py` provides the exact template to mirror

**Research date:** 2026-04-13
**Valid until:** 2026-06-01 (stable Kivy codebase; no external dependency changes expected)
