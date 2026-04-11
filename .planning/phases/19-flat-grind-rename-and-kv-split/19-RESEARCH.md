# Phase 19: Flat Grind Rename and KV Split - Research

**Researched:** 2026-04-11
**Domain:** Kivy screen refactoring — class rename, KV file split, Python package restructure
**Confidence:** HIGH

## Summary

Phase 19 is a mechanical refactoring phase: rename three existing screen classes to FlatGrind* prefixed names, move them into a `screens/flat_grind/` package, split their KV files into `ui/flat_grind/`, and update all imports. The existing behavior must be preserved with zero functional changes.

The codebase is well-understood from Phase 18 research. The key risks are: (1) Kivy KV rule name collisions if old KV files are loaded alongside new ones, (2) import path breakage across the 20+ test files and production code, and (3) base.kv ScreenManager referencing old class names that must be updated to FlatGrind* names.

**Primary recommendation:** Execute as a strict rename-and-move operation. Copy file contents verbatim, change only class names and KV rule headers. Verify with existing test suite after each file group change.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- New `screens/flat_grind/` package with `__init__.py`, `run.py`, `axes_setup.py`, `parameters.py`, `widgets.py`
- File names mirror the base pattern (run.py, axes_setup.py, parameters.py) -- directory provides namespace
- `flat_grind_widgets.py` moves into the package as `screens/flat_grind/widgets.py`
- `__init__.py` exports all three FlatGrind* screen classes -- consumers import from package root
- `screens/__init__.py` updated to export FlatGrind* classes only (not old names)
- Old screen .py files become thin re-export wrappers (safety net for old imports)
- Re-exports include screen class only -- no BCompBarChart or other items re-exported
- Old `.kv` files left untouched on disk but NOT loaded by Builder -- removed from Builder.load_file calls in main.py
- KV files in `ui/flat_grind/` use same base names: `run.kv`, `axes_setup.kv`, `parameters.kv`
- KV content is exact copy from old files with only the rule header renamed
- `Builder.load_file()` calls placed in `screens/flat_grind/__init__.py` -- package is self-contained
- main.py imports FlatGrind* classes directly from `screens.flat_grind`
- ScreenManager canonical names preserved: `name='run'`, `name='axes_setup'`, `name='parameters'`
- All imports across codebase updated to use FlatGrind* class names directly
- All test files updated to import from `screens.flat_grind` with FlatGrind* names
- Log prefixes updated: `[RunScreen]` -> `[FlatGrindRunScreen]` etc.
- BCompBarChart and BCOMP_* constants removed entirely from old run.py
- `_BaseBarChart` stays in `screens/flat_grind/widgets.py`

### Claude's Discretion
- KV asset path strategy (relative vs absolute from project root) -- match existing patterns
- Builder.load_file path resolution method (pathlib vs Kivy resource path)
- Exact thin re-export wrapper implementation details
- Test file organization for Phase 19-specific tests

### Deferred Ideas (OUT OF SCOPE)
- End-of-v3.0-milestone audit: clean up old screen files, old kv files, and orphaned code
- Old ui/run.kv bComp widget references: noted for cleanup during audit
- BCompBarChart redesign: Phase 21 (Serration Screen Set)
- ProfilesScreen re-export or migration: not in scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FLAT-01 | Existing RunScreen renamed to FlatGrindRunScreen with own .kv file in ui/flat_grind/ | Package structure, KV loading pattern, import migration map |
| FLAT-02 | Existing AxesSetupScreen renamed to FlatGrindAxesSetupScreen with own .kv file | Same pattern as FLAT-01 applied to axes_setup |
| FLAT-03 | Existing ParametersScreen renamed to FlatGrindParametersScreen with own .kv file | Same pattern as FLAT-01 applied to parameters |
| FLAT-04 | All existing Flat Grind functionality preserved -- zero behavior change from v2.0 | Re-export wrappers, test suite pass, canonical screen names preserved |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Kivy | 2.3+ | UI framework | Already in use -- Builder.load_file, Screen, ScreenManager |
| Python | 3.13 | Runtime | Already in use -- f-strings, type hints, `from __future__` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib | stdlib | Path resolution for KV file loading | `__init__.py` Builder.load_file calls |
| os.path | stdlib | Path joins | Existing pattern in main.py -- match for consistency |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| os.path.join for KV paths | pathlib.Path | Either works; match existing main.py pattern (os.path) for consistency |
| Builder.load_file with os.path | Kivy resource_add_path | resource_add_path is global state; os.path.join is explicit and local |

## Architecture Patterns

### Recommended Project Structure (after Phase 19)
```
src/dmccodegui/
  screens/
    __init__.py              # Exports FlatGrind* classes + base classes + other screens
    base.py                  # Unchanged -- BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen
    flat_grind/
      __init__.py            # Builder.load_file() calls + re-exports FlatGrind* classes
      run.py                 # FlatGrindRunScreen (renamed from screens/run.py)
      axes_setup.py          # FlatGrindAxesSetupScreen (renamed from screens/axes_setup.py)
      parameters.py          # FlatGrindParametersScreen (renamed from screens/parameters.py)
      widgets.py             # DeltaCBarChart, _BaseBarChart (moved from flat_grind_widgets.py)
    run.py                   # Thin re-export wrapper: FlatGrindRunScreen as RunScreen
    axes_setup.py            # Thin re-export wrapper: FlatGrindAxesSetupScreen as AxesSetupScreen
    parameters.py            # Thin re-export wrapper: FlatGrindParametersScreen as ParametersScreen
    flat_grind_widgets.py    # Thin re-export wrapper -> flat_grind.widgets
    ...other screens unchanged...
  ui/
    flat_grind/
      run.kv                 # <FlatGrindRunScreen>: (copy of ui/run.kv with rule header renamed)
      axes_setup.kv          # <FlatGrindAxesSetupScreen>:
      parameters.kv          # <FlatGrindParametersScreen>:
    run.kv                   # OLD -- left on disk, NOT loaded by Builder
    axes_setup.kv            # OLD -- left on disk, NOT loaded by Builder
    parameters.kv            # OLD -- left on disk, NOT loaded by Builder
    ...other kv files unchanged...
```

### Pattern 1: Package __init__.py as Self-Contained Loader
**What:** The `screens/flat_grind/__init__.py` file both loads KV files via Builder.load_file() and exports all screen classes. Importing the package triggers KV loading.
**When to use:** Every machine-specific screen package (flat_grind, serration, convex).
**Example:**
```python
# screens/flat_grind/__init__.py
import os
from kivy.lang import Builder

_KV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'ui', 'flat_grind')

Builder.load_file(os.path.join(_KV_DIR, 'run.kv'))
Builder.load_file(os.path.join(_KV_DIR, 'axes_setup.kv'))
Builder.load_file(os.path.join(_KV_DIR, 'parameters.kv'))

from .run import FlatGrindRunScreen
from .axes_setup import FlatGrindAxesSetupScreen
from .parameters import FlatGrindParametersScreen

__all__ = [
    "FlatGrindRunScreen",
    "FlatGrindAxesSetupScreen",
    "FlatGrindParametersScreen",
]
```

### Pattern 2: Thin Re-Export Wrapper
**What:** Old file locations become single-line re-exports so external code importing old names still works.
**When to use:** Every old screen .py file that moves into the package.
**Example:**
```python
# screens/run.py (old location -- now a thin wrapper)
"""Backward-compatibility wrapper. Real implementation in screens.flat_grind.run."""
from .flat_grind.run import FlatGrindRunScreen as RunScreen  # noqa: F401

# Module-level constants that tests import directly from this path:
from .flat_grind.run import (  # noqa: F401
    PLOT_BUFFER_SIZE, PLOT_UPDATE_HZ,
    CYCLE_VAR_TOOTH, CYCLE_VAR_PASS, CYCLE_VAR_DEPTH,
)
from .flat_grind.widgets import (  # noqa: F401
    DeltaCBarChart, _BaseBarChart,
    DELTA_C_WRITABLE_START, DELTA_C_WRITABLE_END,
    DELTA_C_ARRAY_SIZE, DELTA_C_STEP,
    STONE_SURFACE_MM, STONE_OVERHANG_MM, STEP_MM,
    STONE_WINDOW_INDICES, stone_window_for_index,
)
```

### Pattern 3: base.kv ScreenManager Update
**What:** The base.kv ScreenManager must reference FlatGrind* class names while keeping canonical `name:` values.
**Example:**
```
# ui/base.kv -- ScreenManager section
FlatGrindRunScreen:
    name: 'run'
FlatGrindAxesSetupScreen:
    name: 'axes_setup'
FlatGrindParametersScreen:
    name: 'parameters'
```

### Pattern 4: KV Import Directive Update
**What:** KV files using `#:import` directives that reference `dmccodegui.screens.run` must be updated to `dmccodegui.screens.flat_grind.run` (or `flat_grind.widgets`).
**Current run.kv imports to update:**
```
#:import DeltaCBarChart dmccodegui.screens.run          -> dmccodegui.screens.flat_grind.widgets
#:import BCompBarChart dmccodegui.screens.run            -> REMOVE (BComp removed per decision)
#:import run_module dmccodegui.screens.run               -> dmccodegui.screens.flat_grind.run
```

### Anti-Patterns to Avoid
- **Loading both old and new KV files:** Builder would apply BOTH `<RunScreen>:` and `<FlatGrindRunScreen>:` rules. Old KV files MUST be removed from KV_FILES list in main.py.
- **Shadowing base class attributes:** FlatGrind* classes must NOT re-declare controller/state ObjectProperties already in base classes.
- **Breaking import chains:** The re-export wrappers must also re-export module-level constants (PARAM_DEFS, PLOT_BUFFER_SIZE, etc.) that tests import from the old paths.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| KV path resolution | Manual string manipulation | `os.path.join(os.path.dirname(os.path.abspath(__file__)), ...)` | Existing pattern in main.py; handles spaces in paths, platform differences |
| KV rule duplication check | Manual file inspection | `grep -rh "^<[A-Z]" src/dmccodegui/ui/ \| sort \| uniq -d` | Automated check catches collisions across all KV files |
| Import migration verification | Manual review | `python -c "from dmccodegui.screens.flat_grind import FlatGrindRunScreen"` | Python import system validates the entire chain |

## Common Pitfalls

### Pitfall 1: KV Rule Name Collision (CRITICAL)
**What goes wrong:** If both old `ui/run.kv` (with `<RunScreen>:`) and new `ui/flat_grind/run.kv` (with `<FlatGrindRunScreen>:`) are loaded, AND the old `RunScreen` class still exists via re-export, Kivy applies the old rule to a class that no longer matches -- causing silent layout failures.
**Why it happens:** Builder.load_file is additive; unloading rules is not reliable.
**How to avoid:** Remove old KV paths from main.py KV_FILES list. New KV loading happens in `screens/flat_grind/__init__.py`. Old KV files stay on disk but are never loaded.
**Warning signs:** Widgets missing, layout looks wrong, no error message.

### Pitfall 2: Circular Import in __init__.py
**What goes wrong:** If `screens/flat_grind/__init__.py` imports screen classes before Builder.load_file() runs, and those screen classes reference KV ids at class body level, Kivy raises "No rule found for FlatGrindRunScreen".
**Why it happens:** Python evaluates class bodies at import time; KV rules must be loaded first.
**How to avoid:** Builder.load_file() calls MUST come before class imports in `__init__.py`. The pattern shown above (load files first, then import classes) handles this correctly.
**Warning signs:** `WidgetException: No rule found` or missing `ids` attributes.

### Pitfall 3: KV #:import Directives Still Pointing to Old Paths
**What goes wrong:** The new `ui/flat_grind/run.kv` file contains `#:import DeltaCBarChart dmccodegui.screens.run` -- this still works via re-export wrapper, but is fragile and confusing.
**Why it happens:** Copy-paste from old KV without updating import directives.
**How to avoid:** Update all `#:import` directives in new KV files to point to canonical new locations: `dmccodegui.screens.flat_grind.widgets` for DeltaCBarChart, `dmccodegui.screens.flat_grind.run` for run_module.
**Warning signs:** Import succeeds but via multiple redirects; confusing stack traces.

### Pitfall 4: base.kv Still References Old Class Names
**What goes wrong:** `base.kv` ScreenManager section uses `RunScreen:` which resolves to the old class. If old class is now a re-export alias, Kivy creates an instance of the FlatGrind class (fine) but KV rule matching uses the registered name, which may not match `<FlatGrindRunScreen>:`.
**Why it happens:** Kivy KV rule matching uses the exact class name. `RunScreen` alias creates an instance whose `__class__.__name__` is still `FlatGrindRunScreen`, so the rule `<RunScreen>:` (from the old, now-unloaded KV) won't apply, and `<FlatGrindRunScreen>:` rule (from new KV) WILL apply -- but only if the class name matches exactly.
**How to avoid:** Update base.kv to use `FlatGrindRunScreen:`, `FlatGrindAxesSetupScreen:`, `FlatGrindParametersScreen:` with canonical `name:` values preserved.
**Warning signs:** Blank screen, no layout applied to screens.

### Pitfall 5: Test Files with Per-Function Imports
**What goes wrong:** Test files import `from dmccodegui.screens.run import RunScreen` inside each test function (not at module top). There are 70+ such import statements across test files.
**Why it happens:** Historical pattern in this codebase -- lazy imports for Kivy environment isolation in tests.
**How to avoid:** The thin re-export wrappers make old import paths work. However, per the locked decision, tests should be updated to use new FlatGrind* names. The re-export wrappers are a safety net, not the primary path.

### Pitfall 6: BCompBarChart Removal Breaks Old KV #:import
**What goes wrong:** Old `ui/run.kv` line 3 has `#:import BCompBarChart dmccodegui.screens.run`. Since BCompBarChart is being removed from run.py, this import would fail if the old KV is ever loaded.
**Why it happens:** Old KV file stays on disk but has dangling imports.
**How to avoid:** Old KV file is NOT loaded (removed from KV_FILES). This is fine. The new `ui/flat_grind/run.kv` should not include the BCompBarChart import. Document in deferred-audit notes.

## Code Examples

### screens/flat_grind/__init__.py -- Package Initializer
```python
"""Flat Grind screen package.

Loads KV files and exports screen classes. Importing this package
automatically registers KV rules for all Flat Grind screens.
"""
import os
from kivy.lang import Builder

# KV files live in ui/flat_grind/ relative to the package root.
# Use os.path to match the existing pattern in main.py (line 110).
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_UI_DIR = os.path.normpath(os.path.join(_PKG_DIR, '..', '..', 'ui', 'flat_grind'))

Builder.load_file(os.path.join(_UI_DIR, 'run.kv'))
Builder.load_file(os.path.join(_UI_DIR, 'axes_setup.kv'))
Builder.load_file(os.path.join(_UI_DIR, 'parameters.kv'))

from .run import FlatGrindRunScreen  # noqa: E402
from .axes_setup import FlatGrindAxesSetupScreen  # noqa: E402
from .parameters import FlatGrindParametersScreen  # noqa: E402

__all__ = [
    "FlatGrindRunScreen",
    "FlatGrindAxesSetupScreen",
    "FlatGrindParametersScreen",
]
```

### Thin Re-Export Wrapper (screens/axes_setup.py)
```python
"""Backward-compatibility wrapper. Real implementation in screens.flat_grind.axes_setup."""
from .flat_grind.axes_setup import FlatGrindAxesSetupScreen as AxesSetupScreen  # noqa: F401
from .flat_grind.axes_setup import (  # noqa: F401
    AXIS_CPM_DEFAULTS, AXIS_LABELS, AXIS_COLORS, _AXIS_ROW_IDS,
)
```

### main.py KV_FILES Update
```python
KV_FILES = [
    "ui/theme.kv",         # base styles - always first
    "ui/pin_overlay.kv",   # PINOverlay ModalView
    "ui/status_bar.kv",    # StatusBar widget
    "ui/tab_bar.kv",       # TabBar widget
    "ui/setup.kv",         # SetupScreen (connection)
    # NOTE: run.kv, axes_setup.kv, parameters.kv removed --
    # Flat Grind KV loaded by screens.flat_grind.__init__
    "ui/profiles.kv",      # ProfilesScreen (CSV import/export)
    "ui/diagnostics.kv",   # DiagnosticsScreen placeholder
    "ui/users.kv",         # UsersScreen (Admin)
    "ui/base.kv",          # RootLayout - always last
]
```

### KV Rule Header Rename (ui/flat_grind/run.kv, first lines)
```
#:import theme dmccodegui.theme_manager.theme
#:import DeltaCBarChart dmccodegui.screens.flat_grind.widgets
#:import run_module dmccodegui.screens.flat_grind.run
#:import kivy_matplotlib_widget kivy_matplotlib_widget

<FlatGrindRunScreen>:
    canvas.before:
        Color:
            rgba: theme.bg_dark
```

## Inventory of Changes

### Files to CREATE (new)
| File | Contents | Lines (est.) |
|------|----------|-------------|
| `screens/flat_grind/__init__.py` | Builder.load_file + exports | ~25 |
| `screens/flat_grind/run.py` | FlatGrindRunScreen (copy of run.py, class renamed) | ~1266 |
| `screens/flat_grind/axes_setup.py` | FlatGrindAxesSetupScreen (copy, renamed) | ~635 |
| `screens/flat_grind/parameters.py` | FlatGrindParametersScreen (copy, renamed) | ~194 |
| `screens/flat_grind/widgets.py` | DeltaCBarChart etc. (copy of flat_grind_widgets.py) | ~325 |
| `ui/flat_grind/run.kv` | Copy of ui/run.kv, rule header renamed, BComp import removed | ~630 |
| `ui/flat_grind/axes_setup.kv` | Copy of ui/axes_setup.kv, rule header renamed | ~781 |
| `ui/flat_grind/parameters.kv` | Copy of ui/parameters.kv, rule header renamed | ~114 |

### Files to MODIFY (existing)
| File | Changes |
|------|---------|
| `screens/__init__.py` | Replace old class exports with FlatGrind* imports |
| `screens/run.py` | Replace with thin re-export wrapper; remove BCompBarChart |
| `screens/axes_setup.py` | Replace with thin re-export wrapper |
| `screens/parameters.py` | Replace with thin re-export wrapper |
| `screens/flat_grind_widgets.py` | Replace with thin re-export wrapper -> flat_grind.widgets |
| `main.py` | Remove 3 KV paths from KV_FILES; import from screens.flat_grind |
| `ui/base.kv` | Change RunScreen/AxesSetupScreen/ParametersScreen to FlatGrind* in ScreenManager |
| `tests/test_run_screen.py` | Update ~25 import statements to FlatGrind* |
| `tests/test_axes_setup.py` | Update ~30 import statements to FlatGrind* |
| `tests/test_parameters.py` | Update ~20 import statements to FlatGrind* |
| `tests/test_delta_c_bar_chart.py` | Update ~6 import statements |
| `tests/test_flat_grind_widgets.py` | Update ~3 import statements |
| `tests/test_base_classes.py` | Update ~8 import statements |

### Files LEFT UNTOUCHED (on disk, not loaded)
| File | Reason |
|------|--------|
| `ui/run.kv` | Old KV -- not loaded, stays for reference |
| `ui/axes_setup.kv` | Old KV -- not loaded, stays for reference |
| `ui/parameters.kv` | Old KV -- not loaded, stays for reference |

## Import Migration Map

### Production Code
| Old Import | New Import |
|-----------|-----------|
| `from .screens.run import RunScreen` | `from .screens.flat_grind import FlatGrindRunScreen` |
| `from .screens.axes_setup import AxesSetupScreen` | `from .screens.flat_grind import FlatGrindAxesSetupScreen` |
| `from .screens.parameters import ParametersScreen` | `from .screens.flat_grind import FlatGrindParametersScreen` |
| `from .screens.flat_grind_widgets import DeltaCBarChart` | `from .screens.flat_grind.widgets import DeltaCBarChart` |

### Test Code
| Old Import | New Import |
|-----------|-----------|
| `from dmccodegui.screens.run import RunScreen` | `from dmccodegui.screens.flat_grind.run import FlatGrindRunScreen` |
| `from dmccodegui.screens.run import RunScreen, PLOT_BUFFER_SIZE` | `from dmccodegui.screens.flat_grind.run import FlatGrindRunScreen, PLOT_BUFFER_SIZE` |
| `from dmccodegui.screens.run import RunScreen, DELTA_C_ARRAY_SIZE` | `from dmccodegui.screens.flat_grind.run import FlatGrindRunScreen` + `from dmccodegui.screens.flat_grind.widgets import DELTA_C_ARRAY_SIZE` |
| `from dmccodegui.screens.axes_setup import AxesSetupScreen` | `from dmccodegui.screens.flat_grind.axes_setup import FlatGrindAxesSetupScreen` |
| `from dmccodegui.screens.parameters import ParametersScreen, PARAM_DEFS` | `from dmccodegui.screens.flat_grind.parameters import FlatGrindParametersScreen, PARAM_DEFS` |
| `from dmccodegui.screens.flat_grind_widgets import DeltaCBarChart` | `from dmccodegui.screens.flat_grind.widgets import DeltaCBarChart` |

### Internal Imports Within Moved Files
| In File | Old Import | New Import |
|---------|-----------|-----------|
| `flat_grind/run.py` | `from .flat_grind_widgets import DeltaCBarChart, ...` | `from .widgets import DeltaCBarChart, ...` |
| `flat_grind/run.py` | `from ..app_state import MachineState` | `from ...app_state import MachineState` (3 levels up) |
| `flat_grind/run.py` | `from .base import BaseRunScreen` | `from ..base import BaseRunScreen` |
| `flat_grind/axes_setup.py` | `from ..app_state import MachineState` | `from ...app_state import MachineState` |
| `flat_grind/axes_setup.py` | `from .base import BaseAxesSetupScreen` | `from ..base import BaseAxesSetupScreen` |
| `flat_grind/parameters.py` | `from .base import BaseParametersScreen` | `from ..base import BaseParametersScreen` |

**CRITICAL NOTE on relative imports:** Files moving from `screens/` to `screens/flat_grind/` go one level deeper. All `..` relative imports become `...` (three dots). This is the most error-prone part of the refactoring.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single screens/ directory | Per-machine packages (screens/flat_grind/) | Phase 19 (now) | Enables Phase 20 dynamic loader |
| Shared KV files in ui/ | Per-machine KV dirs (ui/flat_grind/) | Phase 19 (now) | Eliminates KV rule collisions |
| Generic class names (RunScreen) | Prefixed names (FlatGrindRunScreen) | Phase 19 (now) | Unique class names for KV rule matching |

## Open Questions

1. **BCompBarChart references in run.py body**
   - What we know: RunScreen currently imports BCompBarChart from run.py. The decision says to remove BCompBarChart from old run.py. But the *current* RunScreen class body likely references BCompBarChart for creating the bComp widget.
   - What's unclear: Does FlatGrindRunScreen need BCompBarChart code in its class body, or was it already factored out?
   - Recommendation: Check run.py lines that reference BCompBarChart. If FlatGrindRunScreen still uses it, keep it in flat_grind/run.py (not in widgets.py). If it is Serration-only, remove it entirely. The CONTEXT.md says "BCompBarChart removed entirely from old run.py" which suggests the new flat_grind/run.py should NOT contain it either.

2. **DELTA_C constants import chain in tests**
   - What we know: test_delta_c_bar_chart.py imports `DELTA_C_ARRAY_SIZE` and `DELTA_C_STEP` from `dmccodegui.screens.run`. These constants are actually defined in flat_grind_widgets.py and re-exported.
   - What's unclear: Whether to update test imports to flat_grind.widgets or flat_grind.run.
   - Recommendation: Update to `dmccodegui.screens.flat_grind.widgets` (canonical location). The re-export wrapper in old run.py handles backward compat.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pytest.ini or pyproject.toml (standard discovery) |
| Quick run command | `python -m pytest tests/ -x --tb=short` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FLAT-01 | FlatGrindRunScreen class exists, inherits BaseRunScreen, has own KV | unit | `python -m pytest tests/test_run_screen.py -x` | Needs update (rename imports) |
| FLAT-02 | FlatGrindAxesSetupScreen exists, inherits BaseAxesSetupScreen, has own KV | unit | `python -m pytest tests/test_axes_setup.py -x` | Needs update (rename imports) |
| FLAT-03 | FlatGrindParametersScreen exists, inherits BaseParametersScreen, has own KV | unit | `python -m pytest tests/test_parameters.py -x` | Needs update (rename imports) |
| FLAT-04 | Zero behavior change -- all existing tests pass with new names | integration | `python -m pytest tests/ -x` | Existing suite covers this |
| SC-3 | No duplicate KV rule headers across all KV files | smoke | `grep -rh "^<[A-Z]" src/dmccodegui/ui/ \| sort \| uniq -d` | Wave 0 -- new test |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x --tb=short`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green + KV collision grep returns zero matches

### Wave 0 Gaps
- [ ] New test: KV rule collision check (`grep` for duplicate `<ClassName>:` headers across all .kv files)
- [ ] New tests: FlatGrind* screen instantiation with expected widgets/properties present
- [ ] Update all existing test imports to FlatGrind* names (70+ import statements across 6 test files)

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection -- all findings verified by reading actual source files
- `screens/__init__.py` -- current export structure (line 1-32)
- `main.py` -- KV_FILES list (lines 64-77), Builder.load_file pattern (line 110)
- `ui/base.kv` -- ScreenManager screen declarations (lines 46-51)
- `screens/run.py`, `axes_setup.py`, `parameters.py` -- class definitions and imports
- `screens/base.py` -- base class structure (all lifecycle hooks)
- Test files -- import patterns across 6 test files

### Secondary (MEDIUM confidence)
- Kivy Builder.load_file behavior -- well-documented, additive rule loading
- Kivy KV rule matching by class name -- `__class__.__name__` exact match

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, pure refactoring
- Architecture: HIGH -- all patterns derived from existing codebase conventions
- Pitfalls: HIGH -- all identified from direct code inspection and Kivy KV rule behavior
- Import migration: HIGH -- complete inventory from grep of all .py files

**Research date:** 2026-04-11
**Valid until:** No expiry -- pure refactoring research based on existing codebase
