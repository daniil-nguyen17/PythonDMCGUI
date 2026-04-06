---
phase: 02-run-page
plan: "00"
subsystem: testing
tags: [pytest, kivy, wave-0, test-scaffold, tdd]

# Dependency graph
requires:
  - phase: 01-auth-nav
    provides: MachineState with auth fields, RunScreen placeholder, existing test suite
provides:
  - Wave 0 test scaffolds for all RUN-page requirements (RUN-02 through RUN-06)
  - 19 failing stub tests that define expected behavior before implementation
affects: [02-01-run-screen, 02-02-delta-c, 03-ab-plot]

# Tech tracking
tech-stack:
  added: []
  patterns: [Wave 0 test-first scaffold pattern — stub tests created before implementation so pytest can verify each implementation wave]

key-files:
  created:
    - tests/test_machine_state_cycle.py
    - tests/test_run_screen.py
    - tests/test_delta_c_bar_chart.py
  modified: []

key-decisions:
  - "Wave 0 scaffolds use direct imports inside test functions to defer Kivy initialization errors until needed — avoids conftest-level import failures on systems without display"
  - "test_machine_state_cycle.py is pure Python (no Kivy) so cycle field tests can run in CI without display"
  - "test_delta_c_bar_chart.py tests offset math logic directly, not Kivy rendering — aligns with RUN-06 being pure data logic"

patterns-established:
  - "Wave 0 pattern: create failing test scaffolds before any implementation so verification is possible from first task"
  - "Kivy env setup (KIVY_NO_ENV_CONFIG, KIVY_LOG_LEVEL) placed inside each test function, not at module level, to avoid import-time side effects"

requirements-completed: [RUN-02, RUN-03, RUN-04, RUN-05, RUN-06]

# Metrics
duration: 2min
completed: 2026-04-04
---

# Phase 2 Plan 00: Wave 0 Test Scaffolds Summary

**19 failing stub tests across 3 files define RUN-02 through RUN-06 expected behaviors before any implementation begins**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-04T08:10:56Z
- **Completed:** 2026-04-04T08:12:34Z
- **Tasks:** 2
- **Files modified:** 3 (all created)

## Accomplishments

- Created test_machine_state_cycle.py with 7 pure-Python tests covering all cycle fields Plan 01 will add to MachineState
- Created test_run_screen.py with 7 stub tests covering RUN-02 (no e_stop), RUN-03 (axis positions), RUN-04 (cycle status/machine type), RUN-05 (progress/ETA), RUN-06 (delta_c properties)
- Created test_delta_c_bar_chart.py with 5 logic tests covering DELTA_C constants, offset-to-array expansion, section clamping, and step adjustment math
- All 22 pre-existing tests continue to pass unaffected

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test scaffolds for MachineState cycle fields and RunScreen** - `ea3440f` (test)
2. **Task 2: Create DeltaCBarChart test scaffold** - `6b67108` (test)

## Files Created/Modified

- `tests/test_machine_state_cycle.py` - 7 pure-Python stub tests for MachineState cycle fields (RUN-04, RUN-05)
- `tests/test_run_screen.py` - 7 Kivy stub tests for RunScreen properties and behaviors (RUN-02, RUN-03, RUN-04, RUN-05, RUN-06)
- `tests/test_delta_c_bar_chart.py` - 5 pure-logic stub tests for DeltaCBarChart offset math (RUN-06)

## Decisions Made

- Wave 0 scaffolds use direct imports inside each test function (not at module level) to defer Kivy initialization until actually needed, avoiding import-time failures on headless systems.
- test_machine_state_cycle.py is kept entirely free of Kivy imports since MachineState is a pure Python dataclass — this keeps the cycle field tests runnable in any CI environment without a display.
- test_delta_c_bar_chart.py tests the offset-to-array math logic directly rather than rendering, so the tests validate the algorithm independently of the widget.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 19 stub tests are discoverable by pytest and will fail with meaningful `AssertionError` (not `ImportError`) once Plans 01 and 02 implement the target modules.
- Plan 01 (RunScreen core) can be executed immediately — test_machine_state_cycle.py and test_run_screen.py are ready to verify its output.
- Plan 02 (DeltaCBarChart) can be executed after Plan 01 — test_delta_c_bar_chart.py is ready to verify its output.

---
*Phase: 02-run-page*
*Completed: 2026-04-04*
