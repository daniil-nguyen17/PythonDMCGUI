---
phase: 09-dmc-foundation
plan: 01
subsystem: hmi
tags: [galil, dmc, constants, app_state, python, tdd]

# Dependency graph
requires: []
provides:
  - "src/dmccodegui/hmi/__init__.py: new hmi package"
  - "src/dmccodegui/hmi/dmc_vars.py: all DMC variable name constants and hmiState encoding"
  - "MachineState.dmc_state field: stores polled hmiState value, default=0"
  - "tests/test_dmc_vars.py: 41 tests covering constants and dmc_state field"
affects: [09-02, 09-03, 10-state-poll, 12-run-page-wiring, 13-setup-loop]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "dmc_vars.py as single source of truth for all DMC variable names"
    - "TDD red-green for constants module (test → implement)"
    - "xfail marker for tests verifying future migration state (stale-string test)"

key-files:
  created:
    - src/dmccodegui/hmi/__init__.py
    - src/dmccodegui/hmi/dmc_vars.py
    - tests/test_dmc_vars.py
  modified:
    - src/dmccodegui/app_state.py

key-decisions:
  - "dmc_vars.py is the single source of truth for DMC variable names — screen files must import from here, never use raw string literals"
  - "xfail marker on stale-string test keeps suite green until plan 09-03 migrates screen files"
  - "dmc_state field added after cycle_completion_pct to keep auth/cycle field groupings intact"

patterns-established:
  - "ALL_HMI_TRIGGERS list enables batch initialization of trigger variables to default (1)"
  - "RESTPT_BY_AXIS / STARTPT_BY_AXIS dicts enable axis-keyed lookups without raw strings"
  - "HMI_TRIGGER_DEFAULT=1 / HMI_TRIGGER_FIRE=0 constants replace magic numbers in trigger code"

requirements-completed: [DMC-01, DMC-06]

# Metrics
duration: 22min
completed: 2026-04-06
---

# Phase 9 Plan 01: DMC Foundation — Constants Module Summary

**Python HMI-controller integration contract via dmc_vars.py: 8 trigger variable names, 5 state encoding constants, 8 position variable names with ordered lists and axis maps, and MachineState.dmc_state field**

## Performance

- **Duration:** 22 min
- **Started:** 2026-04-06T03:38:20Z
- **Completed:** 2026-04-06T04:00:20Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `src/dmccodegui/hmi/` package with `dmc_vars.py` as single source of truth for all DMC variable names (8 trigger vars, 5 state constants, 8 position vars, ordered lists, axis maps)
- Added `MachineState.dmc_state: int = 0` field to track polled hmiState value from controller
- 41-test suite in `tests/test_dmc_vars.py` covering all constants (exact values, 8-char DMC limit), lists, axis maps, and the dmc_state field — xfail guards stale-string test until plan 09-03

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for dmc_vars constants** - `6778812` (test)
2. **Task 1 GREEN: hmi package + dmc_vars.py implementation** - `dd2bb1d` (feat)
3. **Task 2: dmc_state field on MachineState** - `4c48922` (feat)

_Note: TDD task has two commits (test → feat). No refactor needed._

## Files Created/Modified

- `src/dmccodegui/hmi/__init__.py` - New HMI package, re-exports dmc_vars
- `src/dmccodegui/hmi/dmc_vars.py` - All DMC variable name constants and hmiState encoding
- `src/dmccodegui/app_state.py` - Added dmc_state field to MachineState dataclass
- `tests/test_dmc_vars.py` - 41 tests: constants values, 8-char limit, lists, maps, dmc_state field

## Decisions Made

- The `dmc_vars.py` module is placed in a new `hmi/` sub-package (not at the top `dmccodegui/` level) to signal it is specifically about HMI-controller communication and to keep future HMI modules co-located.
- The stale-string test (`test_no_stale_position_strings_in_screen_files`) is marked `xfail` rather than skipped so it will auto-promote to a real PASSED test once plan 09-03 migrates screen files — no manual cleanup needed.
- `dmc_state` field is positioned after `cycle_completion_pct` (the last cycle field) to preserve the existing field groupings (connection, machine type, auth, cycle status) and add DMC state as a distinct group.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `dmc_vars.py` is ready for import in all future screen files and the state poll worker
- `MachineState.dmc_state` is available for Phase 10 (State Poll) to store the polled hmiState value
- Blocker: Plan 09-02 (DMC file modification) must complete before plan 09-03 (screen migration) so the DMC variable names are live on the controller

## Self-Check: PASSED

- FOUND: src/dmccodegui/hmi/__init__.py
- FOUND: src/dmccodegui/hmi/dmc_vars.py
- FOUND: tests/test_dmc_vars.py
- FOUND: .planning/phases/09-dmc-foundation/09-01-SUMMARY.md
- FOUND commit: 6778812 (test RED phase)
- FOUND commit: dd2bb1d (feat GREEN phase)
- FOUND commit: 4c48922 (feat Task 2)

---
*Phase: 09-dmc-foundation*
*Completed: 2026-04-06*
