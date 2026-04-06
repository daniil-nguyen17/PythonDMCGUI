---
phase: 10-state-poll
plan: 01
subsystem: hmi
tags: [dmc, galil, machine-state, knife-count, polling, dataclass, property]

# Dependency graph
requires:
  - phase: 09-dmc-foundation
    provides: dmc_vars.py single source of truth for DMC variable names, MachineState.dmc_state field, STATE_GRINDING constant

provides:
  - CT_SES_KNI and CT_STN_KNI constants in dmc_vars.py for knife count variable names
  - MachineState.session_knife_count and stone_knife_count int fields (default 0)
  - MachineState.cycle_running @property derived from dmc_state == STATE_GRINDING
  - DMC ctStnKni variable: declared in #PARAMS, incremented at grind completion, reset in #NEWSESS
  - DMC lastSt variable: declared in #PARAMS for Thread 2 state tracking
  - DMC Thread 2 (#THRD2): passive observer loop started from #AUTO, runs at 10 Hz

affects: [10-02-poller, 10-03-run-screen, 12-run-page-wiring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "cycle_running as derived @property on dataclass — computed from dmc_state, never stored"
    - "DMC inline knife counting at grind completion block (#DONE) rather than Thread 2 observer"
    - "Thread 2 as passive observer placeholder — state transitions remain in main thread subroutines"

key-files:
  created:
    - tests/test_dmc_vars.py (TestKnifeCountConstants class added)
    - tests/test_app_state.py (knife count and cycle_running property tests added)
  modified:
    - src/dmccodegui/hmi/dmc_vars.py
    - src/dmccodegui/app_state.py
    - "4 Axis Stainless grind.dmc"

key-decisions:
  - "cycle_running is a @property on MachineState, not a stored bool — state authority is always the controller's hmiState"
  - "Knife counting is inline at grind completion (#DONE block) not via Thread 2 — simpler and more reliable"
  - "Thread 2 is a passive WT 100 observer loop, ready for future background monitoring but currently a no-op"

patterns-established:
  - "Derived properties from dmc_state: use @property pattern for any Python-side value that must reflect controller state"
  - "DMC variable names <= 8 chars: constants in dmc_vars.py prevent typos and keep Python/DMC in sync"

requirements-completed: [POLL-01, POLL-04]

# Metrics
duration: 18min
completed: 2026-04-06
---

# Phase 10 Plan 01: State Poll Foundation Summary

**CT_SES_KNI/CT_STN_KNI constants, MachineState knife count fields, derived cycle_running @property, and DMC ctStnKni/Thread 2 — foundation for Plan 02 poller and Plan 03 RunScreen**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-06T00:00:00Z
- **Completed:** 2026-04-06
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added CT_SES_KNI = "ctSesKni" and CT_STN_KNI = "ctStnKni" constants to dmc_vars.py with 8-char length enforcement
- Replaced stored MachineState.cycle_running bool field with @property returning dmc_state == STATE_GRINDING, making controller the single source of truth
- Added session_knife_count and stone_knife_count integer fields to MachineState (default 0)
- Extended DMC program with ctStnKni declaration, inline knife counting at #DONE, reset in #NEWSESS, and passive Thread 2 observer loop

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend dmc_vars.py and MachineState with knife count support** - `1593bd3` (feat)
2. **Task 2: Add Thread 2 and ctStnKni to DMC program** - `dc7d372` (feat)

_Note: Task 1 used TDD (RED then GREEN within single commit)_

## Files Created/Modified
- `src/dmccodegui/hmi/dmc_vars.py` - Added CT_SES_KNI and CT_STN_KNI constants in new "Knife count variable names" section
- `src/dmccodegui/app_state.py` - Added STATE_GRINDING import, session_knife_count/stone_knife_count fields, cycle_running @property; removed stored cycle_running bool
- `4 Axis Stainless grind.dmc` - Added ctStnKni/lastSt to #PARAMS, XQ #THRD2,1 in #AUTO, inline knife increment in #DONE, ctStnKni reset in #NEWSESS, new #THRD2 label
- `tests/test_dmc_vars.py` - Added TestKnifeCountConstants class with 4 tests
- `tests/test_app_state.py` - Added test_knife_count_fields_exist, test_cycle_running_derived_from_dmc_state, test_cycle_running_not_assignable

## Decisions Made
- **cycle_running as @property:** The plan specified this; confirmed it is the right pattern because Python-side state authority must always be the controller's hmiState value. The @property prevents accidental assignment and makes the derivation explicit.
- **Inline knife counting in #DONE:** RESEARCH.md noted both options (Thread 2 observer vs. inline). Chose inline at grind completion because it is simpler, more reliable (no race condition between threads), and Thread 2 is still added as a passive observer for future needs.
- **Thread 2 as passive no-op loop:** Added as a placeholder per the plan spec. Main thread subroutines already handle all hmiState transitions from Phase 9.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 02 (poller) can now reference CT_SES_KNI and CT_STN_KNI from dmc_vars.py
- Plan 03 (RunScreen) can now bind to MachineState.session_knife_count, stone_knife_count, and cycle_running property
- DMC program has ctStnKni variable ready to be polled
- All 198 tests pass

## Self-Check: PASSED

All files exist. Both task commits verified in git log.

---
*Phase: 10-state-poll*
*Completed: 2026-04-06*
