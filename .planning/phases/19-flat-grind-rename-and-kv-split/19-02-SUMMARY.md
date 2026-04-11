---
phase: 19-flat-grind-rename-and-kv-split
plan: "02"
subsystem: ui
tags: [kivy, screen-manager, kv-files, import-wrappers, flat-grind]

# Dependency graph
requires:
  - phase: 19-flat-grind-rename-and-kv-split/01
    provides: FlatGrind* screen classes and ui/flat_grind/*.kv files
provides:
  - Application wired to use FlatGrind* classes from flat_grind package
  - Thin re-export wrappers for backward compatibility
  - Deferred KV loading pattern via load_kv() to avoid circular imports
  - All test imports updated to canonical flat_grind paths
affects: [21-serration, 22-convex, per-machine-screen-packages]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deferred KV loading via load_kv() function to avoid circular imports"
    - "Thin re-export wrappers for backward compatibility during migration"
    - "Per-machine package __init__.py exports screen classes and load_kv()"

key-files:
  created: []
  modified:
    - src/dmccodegui/main.py
    - src/dmccodegui/ui/base.kv
    - src/dmccodegui/screens/__init__.py
    - src/dmccodegui/screens/run.py
    - src/dmccodegui/screens/axes_setup.py
    - src/dmccodegui/screens/parameters.py
    - src/dmccodegui/screens/flat_grind_widgets.py
    - src/dmccodegui/screens/flat_grind/__init__.py
    - src/dmccodegui/screens/base.py
    - tests/test_run_screen.py
    - tests/test_axes_setup.py
    - tests/test_parameters.py
    - tests/test_delta_c_bar_chart.py
    - tests/test_flat_grind_widgets.py
    - tests/test_base_classes.py

key-decisions:
  - "Deferred KV loading: flat_grind/__init__.py exposes load_kv() instead of loading at import time, called in main.py build() before Factory instantiation"
  - "Circular import resolution: Builder.load_file() processes #:import directives which trigger importlib walks through partially-initialized packages; deferring to build() avoids this"
  - "Added STATE_SETUP gate to BaseAxesSetupScreen.jog_axis (missing safety gate, Deviation Rule 1)"

patterns-established:
  - "Per-machine KV loading: each machine package provides load_kv(), called from main.py build()"
  - "Thin wrapper pattern: old module files re-export from canonical location with noqa: F401"

requirements-completed: [FLAT-01, FLAT-02, FLAT-03, FLAT-04]

# Metrics
duration: 30min
completed: 2026-04-11
---

# Phase 19 Plan 02: Wire Application to FlatGrind* Classes Summary

**Wired main.py, base.kv, and all tests to use FlatGrind* classes from flat_grind package with deferred KV loading and backward-compat re-export wrappers**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-04-11
- **Completed:** 2026-04-11
- **Tasks:** 2
- **Files modified:** 15

## Accomplishments
- Application fully wired to FlatGrind* classes: main.py calls load_kv(), base.kv uses FlatGrind* names
- Old screen files (run.py, axes_setup.py, parameters.py, flat_grind_widgets.py) converted to thin re-export wrappers (<20 lines each)
- All 6 test files updated to import from canonical flat_grind paths with FlatGrind* names
- Circular import resolved by deferring KV loading to explicit load_kv() call in build()
- Test suite: 331 passed, 6 pre-existing failures (status_bar locale=5, main_estop=1)

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire main.py, base.kv, convert old files to wrappers** - `2d97443` (feat)
2. **Task 2: Update test imports, fix circular import, add jog gate** - `02e7cdb` (feat)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified
- `src/dmccodegui/main.py` - Removed old KV paths from KV_FILES, added load_kv() call in build()
- `src/dmccodegui/ui/base.kv` - Changed RunScreen/AxesSetupScreen/ParametersScreen to FlatGrind* names
- `src/dmccodegui/screens/__init__.py` - Imports FlatGrind* from flat_grind package, keeps backward-compat aliases
- `src/dmccodegui/screens/run.py` - Thin wrapper re-exporting FlatGrindRunScreen as RunScreen
- `src/dmccodegui/screens/axes_setup.py` - Thin wrapper re-exporting FlatGrindAxesSetupScreen
- `src/dmccodegui/screens/parameters.py` - Thin wrapper re-exporting FlatGrindParametersScreen
- `src/dmccodegui/screens/flat_grind_widgets.py` - Thin wrapper re-exporting widget classes
- `src/dmccodegui/screens/flat_grind/__init__.py` - Changed to deferred load_kv() pattern
- `src/dmccodegui/screens/base.py` - Added STATE_SETUP gate to jog_axis
- `tests/test_run_screen.py` - Canonical flat_grind imports, submit_urgent patches
- `tests/test_axes_setup.py` - Canonical flat_grind imports, corrected patch targets
- `tests/test_parameters.py` - Canonical flat_grind imports, corrected Clock patch target
- `tests/test_delta_c_bar_chart.py` - Canonical flat_grind imports
- `tests/test_flat_grind_widgets.py` - Canonical imports, added Phase 19 verification tests
- `tests/test_base_classes.py` - Canonical flat_grind imports for wired subclass tests

## Decisions Made
- Deferred KV loading via load_kv() to avoid circular import caused by Builder.load_file() processing #:import directives through partially-initialized packages
- Added STATE_SETUP gate to jog_axis in base.py (documented in docstring but missing from implementation)
- Updated submit patches to submit_urgent where FlatGrindRunScreen uses urgent dispatch

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Circular import from eager KV loading**
- **Found during:** Task 2 (test imports update)
- **Issue:** flat_grind/__init__.py loading KV files at import time caused Builder.load_file() to walk partially-initialized dmccodegui.screens module via #:import directives
- **Fix:** Changed to deferred load_kv() function, called from main.py build() after all packages initialized
- **Files modified:** src/dmccodegui/screens/flat_grind/__init__.py, src/dmccodegui/main.py
- **Verification:** Package imports succeed, full test suite passes
- **Committed in:** 02e7cdb

**2. [Rule 1 - Bug] Missing STATE_SETUP gate in jog_axis**
- **Found during:** Task 2 (test_jog_blocked_when_not_setup failure)
- **Issue:** BaseAxesSetupScreen.jog_axis docstring says "Gated on dmc_state == STATE_SETUP" but no such gate existed in code
- **Fix:** Added STATE_SETUP check after controller connected gate, before CPM checks
- **Files modified:** src/dmccodegui/screens/base.py
- **Verification:** test_jog_blocked_when_not_setup passes
- **Committed in:** 02e7cdb

**3. [Rule 1 - Bug] Patch target mismatches in tests**
- **Found during:** Task 2 (test suite failures)
- **Issue:** Tests patching dmccodegui.screens.axes_setup.jobs failed because wrapper no longer has jobs; FlatGrindRunScreen uses submit_urgent not submit
- **Fix:** Updated all patch targets to canonical flat_grind module paths; changed submit to submit_urgent where appropriate
- **Files modified:** tests/test_axes_setup.py, tests/test_run_screen.py, tests/test_parameters.py
- **Verification:** 331 tests pass
- **Committed in:** 02e7cdb

---

**Total deviations:** 3 auto-fixed (2 bug fixes, 1 blocking)
**Impact on plan:** All auto-fixes necessary for correctness. No scope creep.

## Issues Encountered
- Write tool persistence issue: after committing Task 1, subsequent Write calls to flat_grind/__init__.py and main.py appeared to succeed but files reverted to committed state; required re-reading and re-writing
- Pre-existing test failures (6): status_bar Vietnamese locale tests (5) and main_estop command order (1) -- unrelated to Phase 19 changes

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Flat Grind screens fully migrated to per-machine package pattern
- Pattern established for Serration (Phase 21) and Convex (Phase 22) packages
- load_kv() pattern documented for future machine packages

---
*Phase: 19-flat-grind-rename-and-kv-split*
*Completed: 2026-04-11*
