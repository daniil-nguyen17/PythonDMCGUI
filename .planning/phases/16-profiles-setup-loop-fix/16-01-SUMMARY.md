---
phase: 16-profiles-setup-loop-fix
plan: "01"
subsystem: ui
tags: [kivy, hmi, setup-loop, state-machine, dmc-vars]

# Dependency graph
requires:
  - phase: 13-setup-loop
    provides: Smart-enter/exit pattern with STATE_SETUP guard and hmiExSt=0 exit command
provides:
  - ProfilesScreen with smart-enter guard skipping hmiSetp=0 when already in STATE_SETUP
  - ProfilesScreen on_leave sending hmiExSt=0 instead of hmiSetp=1
  - 4 new tests confirming correct smart-enter and exit behavior
affects: [any future screens that enter/exit setup mode]

# Tech tracking
tech-stack:
  added: []
  patterns: [smart-enter guard checks dmc_state == STATE_SETUP before firing hmiSetp=0, profiles always fires hmiExSt=0 on leave (no sibling screen check)]

key-files:
  created: []
  modified:
    - src/dmccodegui/screens/profiles.py
    - tests/test_profiles.py

key-decisions:
  - "ProfilesScreen on_leave always fires hmiExSt=0 on leave — no _SETUP_SCREENS sibling check because profiles screen has no sibling setup screens"
  - "Smart-enter guard uses is_connected() check in addition to STATE_SETUP check — consistent with axes_setup and parameters pattern"

patterns-established:
  - "Smart-enter: check dmc_state == STATE_SETUP before sending hmiSetp=0 to avoid re-entering setup when already there"
  - "Exit: send HMI_EXIT_SETUP=HMI_TRIGGER_FIRE (hmiExSt=0) not HMI_SETP=HMI_TRIGGER_DEFAULT"

requirements-completed: [SETP-01, SETP-08]

# Metrics
duration: 2min
completed: 2026-04-07
---

# Phase 16 Plan 01: Profiles Screen Setup Loop Fix Summary

**ProfilesScreen smart-enter guard skips hmiSetp=0 when already in STATE_SETUP, and on_leave sends hmiExSt=0 instead of the old hmiSetp=1 bug**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-07T00:33:56Z
- **Completed:** 2026-04-07T00:35:56Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Fixed on_pre_enter to use smart-enter guard: only fires hmiSetp=0 when not already in STATE_SETUP
- Fixed on_leave to send hmiExSt=0 (HMI_EXIT_SETUP) instead of hmiSetp=1 (HMI_TRIGGER_DEFAULT)
- Added 4 new TDD tests confirming correct behavior; all 305 tests green

## Task Commits

Each task was committed atomically:

1. **Task 1: Add smart-enter and exit tests to test_profiles.py** - `4447508` (test)
2. **Task 2: Fix on_pre_enter and on_leave in profiles.py** - `25c6b62` (fix)

**Plan metadata:** (docs commit follows)

_Note: Task 1 is TDD RED — 3 tests failed confirming bugs existed, 1 passed confirming unconditional fire. Task 2 is TDD GREEN — all 4 tests pass._

## Files Created/Modified
- `src/dmccodegui/screens/profiles.py` - Fixed on_pre_enter smart-enter guard and on_leave exit command
- `tests/test_profiles.py` - Added 4 new test functions and _make_profiles_screen helper

## Decisions Made
- ProfilesScreen on_leave always fires hmiExSt=0 — no _SETUP_SCREENS sibling check because profiles has no sibling setup screens (unlike axes_setup/parameters which are siblings of each other)
- Smart-enter guard also checks is_connected() before firing, consistent with the pattern in axes_setup and parameters screens

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 16 complete. ProfilesScreen now uses the same correct smart-enter/exit pattern as AxesSetupScreen and ParametersScreen.
- All three setup screens (axes_setup, parameters, profiles) consistently implement STATE_SETUP guard on enter and HMI_EXIT_SETUP on leave.
- No known blockers.

---
*Phase: 16-profiles-setup-loop-fix*
*Completed: 2026-04-07*
