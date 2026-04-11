---
phase: 18-base-class-extraction
plan: 02
subsystem: ui
tags: [kivy, screen, inheritance, mro, base-class, refactor]

# Dependency graph
requires:
  - phase: 18-base-class-extraction/18-01
    provides: BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen, SetupScreenMixin in base.py
provides:
  - RunScreen(BaseRunScreen) with subscribe/unsubscribe lifecycle inherited from base
  - AxesSetupScreen(BaseAxesSetupScreen) with jog and CPM infrastructure inherited from base
  - ParametersScreen(BaseParametersScreen) with card builder, dirty tracking, apply/read inherited from base
  - screens/__init__.py exports base classes and DeltaCBarChart for downstream phases
  - module-level submit and mc imports in base.py enabling test patching at base.submit/base.mc
affects: [19-machine-type-screens, 20-serration-screens, 21-convex-screens, 22-ui-polish]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "super().on_pre_enter() first / super().on_leave() last — ensures base lifecycle runs in correct order"
    - "module-level submit import in base.py makes all jobs.submit() calls patchable at dmccodegui.screens.base.submit"
    - "SetupScreenMixin uses module-level submit (not lazy jobs.submit) so entry/exit tests patch correctly"

key-files:
  created: []
  modified:
    - src/dmccodegui/screens/run.py
    - src/dmccodegui/screens/axes_setup.py
    - src/dmccodegui/screens/parameters.py
    - src/dmccodegui/screens/__init__.py
    - src/dmccodegui/screens/base.py
    - tests/test_axes_setup.py
    - tests/test_parameters.py
    - tests/test_base_classes.py

key-decisions:
  - "base.py adds module-level 'from dmccodegui.utils.jobs import submit' so all submit() calls in SetupScreenMixin, jog_axis, apply_to_controller, read_from_controller are patchable at dmccodegui.screens.base.submit"
  - "SetupScreenMixin._enter/_exit_setup_if_needed changed from lazy 'from ..utils import jobs; jobs.submit()' to module-level 'submit()' for test patchability"
  - "Entry/exit tests updated to patch dmccodegui.screens.base.submit with side_effect=lambda fn, *a, **kw: fn() for synchronous execution"
  - "Jog tests updated from dmccodegui.screens.axes_setup.jobs to dmccodegui.screens.base.submit since jog_axis lives in base.py"
  - "BCompBarChart stays in run.py (Serration-specific, deferred to Phase 21)"

patterns-established:
  - "Test patchability pattern: all module-level jobs.submit() calls flow through base.submit, making dmccodegui.screens.base.submit the single patch target for all screen I/O in tests"
  - "super-first/super-last lifecycle ordering: on_pre_enter calls super() first, on_leave calls super() last — threads stop before unsubscribe"

requirements-completed: [ARCH-01, ARCH-02, ARCH-03, ARCH-04]

# Metrics
duration: 90min
completed: 2026-04-11
---

# Phase 18 Plan 02: Wire Existing Screens to Base Classes Summary

**RunScreen, AxesSetupScreen, and ParametersScreen wired to inherit from Phase 18-01 base classes; module-level submit import in base.py enables single-target test patching across all three screens**

## Performance

- **Duration:** ~90 min
- **Started:** 2026-04-11T00:00:00Z
- **Completed:** 2026-04-11T00:00:00Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- All three screen classes now inherit from their respective base classes with zero behavior change
- base.py updated with module-level `submit` and `mc` imports enabling clean test patching
- 3 previously-failing tests fixed (entry/exit tests that needed the module-level submit path)
- 9 regression tests added to test_base_classes.py covering inheritance, no-duplicate-frozenset, no-inline-ObjectProperty, and two-cycle leak checks

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire RunScreen to inherit from BaseRunScreen** - `7538b25` (feat)
2. **Task 2: Wire AxesSetupScreen and ParametersScreen to base classes** - `958d94a` (feat)
3. **Task 3: Add Plan 18-02 regression tests** - `7739b67` (test)

**Plan metadata:** (this commit — docs)

## Files Created/Modified
- `src/dmccodegui/screens/run.py` - Changed to `RunScreen(BaseRunScreen)`, removed inline DeltaC widgets, added `_on_state_change` delegation
- `src/dmccodegui/screens/axes_setup.py` - Changed to `AxesSetupScreen(BaseAxesSetupScreen)`, removed jog_axis, CPM methods, setup entry/exit, ObjectProperties
- `src/dmccodegui/screens/parameters.py` - Changed to `ParametersScreen(BaseParametersScreen)`, removed card builder, validate_field, dirty tracking, apply/read methods
- `src/dmccodegui/screens/__init__.py` - Added exports: BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen, SetupScreenMixin, DeltaCBarChart
- `src/dmccodegui/screens/base.py` - Added module-level `import dmccodegui.machine_config as mc` and `from dmccodegui.utils.jobs import submit`; converted all local `jobs.submit()` calls to module-level `submit()`
- `tests/test_axes_setup.py` - Updated jog and enter/exit test patch targets from `axes_setup.jobs` to `base.submit`
- `tests/test_parameters.py` - Updated apply/read test patches from `parameters.submit/mc` to `base.submit/mc`; updated enter/exit tests to use synchronous side_effect
- `tests/test_base_classes.py` - Added 9 regression tests for Plan 18-02

## Decisions Made
- Added `from dmccodegui.utils.jobs import submit` at module level in base.py so all submit() calls are patchable at a single location (`dmccodegui.screens.base.submit`). This replaces the scattered lazy-import pattern that made tests brittle.
- `SetupScreenMixin._enter/_exit_setup_if_needed` changed from `from ..utils import jobs; jobs.submit(...)` to module-level `submit(...)` so the same patch target works for all screen entry/exit operations.
- Entry/exit tests use `side_effect=lambda fn, *a, **kw: fn()` to execute lambdas synchronously, making `ctrl.cmd` assertions visible in the test.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] base.py needed module-level submit import for test patchability**
- **Found during:** Task 2 (test_parameters.py patch path update)
- **Issue:** base.py used local `from dmccodegui.utils.jobs import submit` inside each method body. Tests patching `dmccodegui.screens.base.submit` got `AttributeError` because `submit` was not a module-level name.
- **Fix:** Added `from dmccodegui.utils.jobs import submit` at module level in base.py; replaced all local `jobs.submit()` calls in SetupScreenMixin, jog_axis, _schedule_cpm_read, apply_to_controller, read_from_controller with module-level `submit()`.
- **Files modified:** src/dmccodegui/screens/base.py
- **Verification:** All 15 tests in test_parameters.py pass after fix; patch targets resolve correctly
- **Committed in:** 958d94a (Task 2 commit)

**2. [Rule 1 - Bug] Entry/exit tests needed synchronous submit side_effect**
- **Found during:** Task 2 (test_enter_fires_when_not_in_setup)
- **Issue:** `_enter_setup_if_needed` calls `submit(lambda: ctrl.cmd(...))`. Tests patched `submit` with a bare MagicMock (swallows lambda), so `ctrl.cmd` was never called and assertions failed.
- **Fix:** Updated 8 entry/exit tests in both test files to use `patch('dmccodegui.screens.base.submit', side_effect=lambda fn, *a, **kw: fn())`. This also fixed 3 previously-failing tests that were pre-existing failures.
- **Files modified:** tests/test_axes_setup.py, tests/test_parameters.py
- **Verification:** Entry/exit tests now pass; net improvement from 18 pre-existing failures to 15
- **Committed in:** 958d94a (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 × Rule 1 - Bug)
**Impact on plan:** Both fixes necessary for test infrastructure correctness. Net improvement: 3 previously-failing tests now pass.

## Issues Encountered
- Pre-existing test failures (18 before Phase 18-02): `test_mode_default_rest` (AxesSetupScreen._mode defaults to '' not 'rest'), `test_jog_blocked_when_not_setup` (jog_axis has no dmc_state gate in the original code), 7 run_screen tests, 5 status_bar tests, 1 main_estop test. These are out of scope for this phase.
- After Phase 18-02: 15 failures remain (3 fixed, 0 new introduced).

## Next Phase Readiness
- BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen are wired and tested
- screens/__init__.py exports all base classes ready for Phase 19 per-machine subclasses
- ARCH-01 through ARCH-04 requirements verified

---
*Phase: 18-base-class-extraction*
*Completed: 2026-04-11*
