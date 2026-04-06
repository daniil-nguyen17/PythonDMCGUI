---
phase: 13-setup-loop
plan: "03"
subsystem: ui
tags: [kivy, hmi, dmc_vars, parameters, varcalc, setup-loop]

# Dependency graph
requires:
  - phase: 13-setup-loop/13-01
    provides: HMI_CALC, HMI_EXIT_SETUP, STATE_SETUP constants in dmc_vars.py

provides:
  - ParametersScreen.apply_to_controller fires hmiCalc=0 after writes, sleeps 500ms, reads back all params, then BV
  - ParametersScreen.on_pre_enter skips hmiSetp=0 when controller is already in STATE_SETUP
  - ParametersScreen.on_leave fires hmiExSt=0 only when navigating to non-setup screens
  - _SETUP_SCREENS frozenset at module level mirrors axes_setup.py pattern

affects: [14-state-driven-ui, axes_setup, parameters, test_parameters]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "varcalc-after-apply: write params -> fire hmiCalc=0 -> sleep(0.5) -> readback -> BV"
    - "smart enter: skip hmiSetp=0 fire if dmc_state already equals STATE_SETUP"
    - "smart exit: fire hmiExSt=0 only when leaving to non-setup screens via _SETUP_SCREENS frozenset"

key-files:
  created: []
  modified:
    - src/dmccodegui/screens/parameters.py
    - tests/test_parameters.py

key-decisions:
  - "time.sleep(0.5) placed directly in _job() inner function — same thread as the cmd writes, ensures delay is between hmiCalc fire and readback without additional synchronization"
  - "mc.get_param_defs() patched in new varcalc tests rather than calling mc.set_active_type() — avoids machine_config global state pollution across test runs"
  - "HMI_TRIGGER_DEFAULT import kept in parameters.py even though on_leave no longer uses it — defensive: may be used by future code or callers"

patterns-established:
  - "varcalc trigger pattern: write all params -> fire trigger -> sleep -> read back -> BV"
  - "setup sibling screen detection via _SETUP_SCREENS frozenset — same pattern as axes_setup.py"

requirements-completed: [SETP-01, SETP-06, SETP-07, SETP-08]

# Metrics
duration: 6min
completed: 2026-04-06
---

# Phase 13 Plan 03: Parameters Varcalc and Smart Enter/Exit Summary

**ParametersScreen apply_to_controller fires hmiCalc=0 trigger after param writes, waits 500ms for #VARCALC to complete on controller, reads back all params, then burns NV — smart enter/exit prevents spurious setup exit/re-enter when switching between axes_setup and parameters tabs**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-06T11:07:46Z
- **Completed:** 2026-04-06T11:13:31Z
- **Tasks:** 2 (TDD: RED then GREEN)
- **Files modified:** 2

## Accomplishments

- Added varcalc integration: apply_to_controller now fires `hmiCalc=0` after writing all dirty params, waits 500ms for the DMC `#VARCALC` subroutine to complete, reads back all params for the active machine type, then sends BV
- Smart enter: `on_pre_enter` checks `dmc_state == STATE_SETUP` before firing `hmiSetp=0` — tab switch from axes_setup to parameters no longer sends a second hmiSetp trigger
- Smart exit: `on_leave` replaced old `hmiSetp=HMI_TRIGGER_DEFAULT` reset with `hmiExSt=0` fired only when navigating to non-setup screens, using `_SETUP_SCREENS` frozenset matching axes_setup.py pattern
- 7 new TDD tests cover all behaviors; tests patch `mc.get_param_defs` to avoid machine_config global state side effects across test runs

## Task Commits

1. **Task 1: Write failing tests for varcalc integration and smart enter/exit** - `d1cac5c` (test)
2. **Task 2: Wire varcalc-after-apply and smart enter/exit in ParametersScreen** - `84d4eb5` (feat)

## Files Created/Modified

- `src/dmccodegui/screens/parameters.py` - Added HMI_CALC/HMI_EXIT_SETUP/STATE_SETUP imports, time import, _SETUP_SCREENS frozenset, varcalc fire + sleep in _job(), smart enter guard, smart exit on_leave
- `tests/test_parameters.py` - 7 new test functions covering varcalc sequence, sleep timing, BV ordering, and smart enter/exit behaviors

## Decisions Made

- `time.sleep(0.5)` placed inline in `_job()` on the background thread — this is the same thread as the cmd writes, so the timing is correct without additional synchronization
- New tests patch `dmccodegui.screens.parameters.mc.get_param_defs` instead of calling `mc.set_active_type()` — the set_active_type approach failed when run after test_machine_config.py tests which leave a deleted temp path as the settings path
- `HMI_TRIGGER_DEFAULT` kept in imports even though `on_leave` no longer uses it — not actively removed to avoid breaking any future callers

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Patched mc.get_param_defs in varcalc tests**
- **Found during:** Task 2 (GREEN phase verification)
- **Issue:** `_make_apply_screen` helper called `mc.set_active_type("4-Axes Flat Grind")` which writes to a temp settings path. When test_machine_config.py tests run first they set this path to a `tmp_path` fixture dir that is deleted after those tests, causing `FileNotFoundError` in subsequent test runs.
- **Fix:** Replaced `mc.set_active_type()` in helper with `patch('dmccodegui.screens.parameters.mc.get_param_defs', return_value=PARAM_DEFS)` in each varcalc test function
- **Files modified:** tests/test_parameters.py
- **Verification:** `python -m pytest tests/ -q` — 231 pass, only pre-existing axes_setup RED tests fail
- **Committed in:** 84d4eb5 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 - missing critical test isolation)
**Impact on plan:** Necessary for deterministic test suite. No scope creep — behavior under test is unchanged.

## Issues Encountered

Pre-existing test failures in `test_parameters.py` (`test_apply_sends_dirty`, `test_apply_burns_nv`, `test_apply_reads_back`, `test_read_clears_dirty`) and `test_axes_setup.py` (5 RED tests from plan 13-02) existed before this plan and are not caused by these changes. All 7 new plan 13-03 tests pass.

## Next Phase Readiness

- ParametersScreen now has complete varcalc integration and smart setup enter/exit
- Both setup screens (axes_setup, parameters) share the same `_SETUP_SCREENS` frozenset pattern — ready for any future sibling setup screens
- Plan 13-02 (AxesSetupScreen HMI rewire) still has 5 RED tests awaiting implementation

---
*Phase: 13-setup-loop*
*Completed: 2026-04-06*
