---
phase: 06-machine-type-differentiation
plan: 03
subsystem: ui
tags: [kivy, machine-config, run-screen, axes-setup, parameters, bar-chart]

# Dependency graph
requires:
  - phase: 06-01
    provides: machine_config module with get_param_defs, get_axis_list, is_serration API

provides:
  - BCompBarChart widget (mirrors DeltaCBarChart, uses bComp array, numSerr-driven size)
  - RunScreen machine-type panel switching (delta_c_panel/bcomp_panel opacity swap, pos_d_row hidden on Serration)
  - AxesSetupScreen axis sidebar filtering (D button hidden on Serration, teach methods axis-aware)
  - ParametersScreen dynamic PARAM_DEFS rebuild from machine_config on every screen entry

affects:
  - 06-02 (machine type selector UI — connects to these screen updates)
  - any future plans touching RunScreen, AxesSetupScreen, or ParametersScreen

# Tech tracking
tech-stack:
  added: []
  patterns:
    - opacity/disabled swap for panel visibility (no widget add/remove, preserves KV ids)
    - _apply_machine_type_widgets() pattern for on_pre_enter hot-swap reconfiguration
    - mc.is_serration() called at decision points, not at import time

key-files:
  created: []
  modified:
    - src/dmccodegui/screens/run.py
    - src/dmccodegui/ui/run.kv
    - src/dmccodegui/screens/axes_setup.py
    - src/dmccodegui/ui/axes_setup.kv
    - src/dmccodegui/screens/parameters.py
    - tests/test_machine_config.py
    - tests/test_run_screen.py

key-decisions:
  - "BCompBarChart extracted from shared _BaseBarChart base class (not full duplication)"
  - "PARAM_DEFS re-exported from parameters.py as alias for _FLAT_PARAM_DEFS for test backward compatibility"
  - "ParametersScreen._param_defs initialized from PARAM_DEFS in __init__ so tests work without on_pre_enter"
  - "is_serration BooleanProperty defaults to False (safe non-serration layout before first on_pre_enter)"

patterns-established:
  - "_apply_machine_type_widgets() called in on_pre_enter: hot-swap takes effect on every screen re-entry"
  - "mc.get_axis_list() called at poll time, not cached: always reflects active type without restart"
  - "Teach methods: build semicolon command dynamically from axis_list (no hardcoded 4-axis pattern)"

requirements-completed: [MACH-01, MACH-02]

# Metrics
duration: 11min
completed: 2026-04-04
---

# Phase 6 Plan 3: Differentiated Content Screens Summary

**RunScreen BCompBarChart + panel toggle, AxesSetupScreen D-axis hiding, ParametersScreen dynamic rebuild from machine_config — all three content screens now respond to machine type changes**

## Performance

- **Duration:** 11 min
- **Started:** 2026-04-04T15:38:09Z
- **Completed:** 2026-04-04T15:49:00Z
- **Tasks:** 3 + 1 auto-fix
- **Files modified:** 7

## Accomplishments

- BCompBarChart widget created via shared `_BaseBarChart` base; RunScreen switches delta_c_panel/bcomp_panel by opacity on every `on_pre_enter`
- AxesSetupScreen sidebar hides D axis button (opacity=0, disabled=True) on Serration via `_rebuild_axis_sidebar()`; teach methods build write commands from `mc.get_axis_list()` only
- ParametersScreen `_rebuild_for_machine_type()` rebuilds all cards from `mc.get_param_defs()` on every screen entry; no module-level static PARAM_DEFS as authoritative source
- Module-level `MACHINE_TYPE` and `IS_SERRATION` constants removed from run.py; all decision points use `mc.is_serration()` at runtime

## Task Commits

Each task was committed atomically:

1. **Task 1: RunScreen BCompBarChart, panel switching, remove stale constants** - `91ea0ce` (feat)
2. **Task 2: AxesSetupScreen sidebar filtering and teach axis awareness** - `3de5b4b` (feat)
3. **Task 3: ParametersScreen dynamic PARAM_DEFS from machine_config** - `0d43219` (feat)
4. **Auto-fix: update tests for removed constants** - `84d3d30` (fix)

## Files Created/Modified

- `src/dmccodegui/screens/run.py` - Removed MACHINE_TYPE/IS_SERRATION; added _BaseBarChart, BCompBarChart; added _apply_machine_type_widgets(); bComp controller stubs; import mc
- `src/dmccodegui/ui/run.kv` - Added id: delta_c_panel, id: bcomp_panel (opacity/disabled), id: pos_d_row; BCompBarChart widget with full adjustment UI
- `src/dmccodegui/screens/axes_setup.py` - Added _rebuild_axis_sidebar(), _AXIS_BTN_IDS; teach methods now axis-aware; polling skips D on Serration; import mc
- `src/dmccodegui/ui/axes_setup.kv` - Added id: axis_btn_a/b/c/d to sidebar ToggleButtons; updated teach label
- `src/dmccodegui/screens/parameters.py` - Removed static PARAM_DEFS as authority; added _rebuild_for_machine_type(); build_param_cards() uses mc.get_param_defs(); PARAM_DEFS re-exported for compat
- `tests/test_machine_config.py` - Updated test_flat_param_defs_match_existing to use _FLAT_PARAM_DEFS
- `tests/test_run_screen.py` - Updated test_cycle_status_machine_type to not import IS_SERRATION

## Decisions Made

- `_BaseBarChart` shared base class extracted rather than duplicating DeltaCBarChart — the two charts are structurally identical; only the DMC array name and step constant differ
- `PARAM_DEFS` re-exported from `parameters.py` as `from machine_config import _FLAT_PARAM_DEFS as PARAM_DEFS` to preserve test backward compatibility without keeping a separate authoritative list
- `ParametersScreen._param_defs` initialized from `PARAM_DEFS` defaults in `__init__` so pure Python tests (no `on_pre_enter`) still work; `_rebuild_for_machine_type()` overrides this on screen entry
- `is_serration` BooleanProperty defaults to `False` in RunScreen (safe: Flat Grind layout shown until first `on_pre_enter` resolves the actual type)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Broke existing tests by removing PARAM_DEFS and IS_SERRATION module symbols**
- **Found during:** Post-task verification (pytest run after Task 3)
- **Issue:** Three test files imported `PARAM_DEFS` from `parameters.py` and `IS_SERRATION` from `run.py`; these constants were removed as part of the plan's stated goal. Tests returned ImportError and logic failure.
- **Fix:** (a) Re-export `PARAM_DEFS` in `parameters.py` as alias for `_FLAT_PARAM_DEFS`; (b) init `ParametersScreen._param_defs` from defaults in `__init__`; (c) update `test_machine_config.py` to import `_FLAT_PARAM_DEFS` directly; (d) update `test_run_screen.py` to not import `IS_SERRATION`, assert default `False`
- **Files modified:** `src/dmccodegui/screens/parameters.py`, `tests/test_machine_config.py`, `tests/test_run_screen.py`
- **Verification:** `pytest tests/ -x -q` → 126 passed
- **Committed in:** `84d3d30`

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Necessary for test suite integrity. All changes consistent with the plan's intent — machine_config remains authoritative, tests now correctly import from machine_config instead of parameters.py.

## Issues Encountered

None beyond the auto-fixed test breakage above.

## Next Phase Readiness

- All three content screens dynamically adapt to machine type: hot-swap by changing type and re-entering any screen shows the correct layout
- Plan 06-02 (machine type selector UI) can now connect to these screens — changing type in UI will take effect immediately on next screen entry
- Run page D-axis position row remains visible but opacity=0 on Serration (size_hint_y: None height 52dp still occupies space); if layout tightness is a concern, consider adding `height: 0 if root.is_serration else '52dp'` in a future pass

---
*Phase: 06-machine-type-differentiation*
*Completed: 2026-04-04*
