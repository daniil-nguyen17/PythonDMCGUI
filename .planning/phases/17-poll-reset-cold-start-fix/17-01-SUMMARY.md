---
phase: 17-poll-reset-cold-start-fix
plan: 01
subsystem: polling, ui
tags: [kivy, controller-poll, status-bar, tdd]

# Dependency graph
requires:
  - phase: 11-e-stop-safety
    provides: program_running field on MachineState and RECOVER button logic in StatusBar
  - phase: 10-state-poll
    provides: ControllerPoller lifecycle (start/stop) and _fail_count/_disconnect_start fields
provides:
  - ControllerPoller.stop() resets _fail_count and _disconnect_start to clean state
  - MachineState.program_running defaults True so cold-start renders OFFLINE not E-STOP
  - TestPollerStopResetsFailCount: TDD coverage for stop() reset behavior
  - TestColdStartShowsOffline: integration test from real MachineState through StatusBar
  - test_recover_enabled_chain: three-step lifecycle for RECOVER button state
affects: [status_bar, poll, app_state, reconnect-lifecycle]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Unconditional reset in stop() — _fail_count and _disconnect_start cleared even when no clock event was set"
    - "Conservative boolean defaults — program_running=True keeps RECOVER disabled until first confirmed poll"

key-files:
  created: []
  modified:
    - src/dmccodegui/hmi/poll.py
    - src/dmccodegui/app_state.py
    - tests/test_poll.py
    - tests/test_status_bar.py

key-decisions:
  - "stop() resets _fail_count and _disconnect_start unconditionally (outside the if block) so any stop() call guarantees clean state for the next start()"
  - "program_running default changed False->True: conservative pattern ensures cold-start shows OFFLINE, not E-STOP; consistent with Phase 11 _XQ-failure-defaults-True convention"

patterns-established:
  - "Unconditional reset in stop(): resets placed outside if-block so they run even when poller was never started"
  - "TDD integration: cold-start test uses real MachineState (not mock) to verify end-to-end default routing through StatusBar"

requirements-completed: [POLL-03, UI-02]

# Metrics
duration: 1min
completed: 2026-04-07
---

# Phase 17 Plan 01: Poll Reset and Cold-Start Fix Summary

**Two one-line production fixes: ControllerPoller.stop() resets reconnect counters and MachineState.program_running defaults True so cold-start shows OFFLINE instead of E-STOP**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-04-07T02:22:51Z
- **Completed:** 2026-04-07T02:24:26Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `ControllerPoller.stop()` now unconditionally resets `_fail_count=0` and `_disconnect_start=None`, ensuring every reconnection cycle starts from a clean failure counter
- `MachineState.program_running` default changed from `False` to `True` so a freshly-created state (before any poll) routes StatusBar to OFFLINE (gray) instead of E-STOP (red)
- Three new test classes covering stop-reset behavior, cold-start OFFLINE routing, and the three-step RECOVER enable/disable lifecycle

## Task Commits

Each task was committed atomically:

1. **Task 1: Production fixes and existing test update** - `e3ca39f` (feat)
2. **Task 2: Cold-start and RECOVER chain tests** - `be5746a` (test)

**Plan metadata:** _(docs commit follows)_

_Note: TDD tasks have RED test commits bundled with their GREEN production fixes in a single task commit here, since tests and fixes were so small and tightly coupled._

## Files Created/Modified
- `src/dmccodegui/hmi/poll.py` - Added two unconditional reset lines in stop()
- `src/dmccodegui/app_state.py` - Changed program_running default False -> True
- `tests/test_poll.py` - Added TestPollerStopResetsFailCount and TestColdStartShowsOffline; updated TestProgramRunningDefault assertion
- `tests/test_status_bar.py` - Added test_recover_enabled_chain covering three lifecycle states

## Decisions Made
- `stop()` resets placed unconditionally outside the `if self._clock_event is not None` block so they execute even when the poller was never started — guarantees clean state in all code paths.
- `program_running=True` default is consistent with Phase 11's `_XQ-failure-defaults-True` conservative pattern: when controller state is uncertain, assume program is running so RECOVER stays disabled.

## Deviations from Plan

None — plan executed exactly as written. The cold-start and RECOVER chain tests (Task 2) passed immediately as GREEN because Task 1 had already put the production code into the correct state. This is expected integration-test behavior.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- Poll reset and cold-start status bar rendering are now correct and covered by tests
- 308 tests passing, no regressions introduced
- Ready for any further v2.0 phase work

---
*Phase: 17-poll-reset-cold-start-fix*
*Completed: 2026-04-07*
