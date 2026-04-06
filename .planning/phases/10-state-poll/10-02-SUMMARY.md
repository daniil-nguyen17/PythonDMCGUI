---
phase: 10-state-poll
plan: 02
subsystem: hmi
tags: [dmc, galil, poller, threading, kivy-clock, disconnect-recovery, tdd]

# Dependency graph
requires:
  - phase: 10-state-poll
    plan: 01
    provides: CT_SES_KNI/CT_STN_KNI constants, MachineState knife count fields, cycle_running @property

provides:
  - ControllerPoller class in hmi/poll.py (10 Hz polling of hmiState, 4 axis positions, 2 knife counts)
  - 3-failure disconnect detection with handle close for clean reconnect
  - Auto-reconnect via controller.connect() on next tick after disconnect
  - GalilController.disconnect() sets _driver = None for clean reconnect
  - Poller lifecycle wired into DMCApp (start on connect, stop on disconnect/shutdown)

affects: [10-03-run-screen, 12-run-page-wiring, 14-state-driven-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Background polling via jobs.submit(_do_read) called from Clock.schedule_interval tick"
    - "Clock.schedule_once for all MachineState mutations — never mutate state on worker thread"
    - "TYPE_CHECKING guard for circular-import-safe type hints in poll.py"
    - "DISCONNECT_THRESHOLD=3 counter with auto-reset on success"
    - "Poller reconnect: close handle on disconnect, try connect() on next tick before reads"

key-files:
  created:
    - src/dmccodegui/hmi/poll.py
    - tests/test_poll.py
  modified:
    - src/dmccodegui/hmi/__init__.py
    - src/dmccodegui/main.py
    - src/dmccodegui/controller.py

key-decisions:
  - "TYPE_CHECKING guard used in poll.py to avoid circular import (hmi -> app_state -> hmi)"
  - "hmi/__init__.py does NOT eagerly import poll — poll pulls in Kivy which would break app_state import chain"
  - "7 separate MG commands (not batch) per poll cycle — safe per RESEARCH.md individual command recommendation"
  - "Poller reconnect does NOT call connect() from within _do_read if is_connected() is True — only attempts reconnect when handle is confirmed closed"

# Metrics
duration: 16min
completed: 2026-04-06
---

# Phase 10 Plan 02: ControllerPoller Module Summary

**ControllerPoller reads hmiState + 4 axis positions + 2 knife counts at 10 Hz, writes to MachineState on main thread, with 3-failure disconnect detection and automatic reconnect**

## Performance

- **Duration:** 16 min
- **Started:** 2026-04-06T04:54:20Z
- **Completed:** 2026-04-06
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created `src/dmccodegui/hmi/poll.py` with `ControllerPoller` class (108 lines)
- 10 Hz polling via `Clock.schedule_interval` → `jobs.submit(_do_read)` pattern
- All 7 reads use individual `MG` commands (hmiState, _TPA/_TPB/_TPC/_TPD, ctSesKni, ctStnKni)
- Disconnect detection: 3 consecutive failures → `state.connected = False`, close handle via `jobs.submit(controller.disconnect)`
- Reconnect path: on next tick, if `is_connected()` is False, tries `controller.connect(state.connected_address)` before reads; successful `_apply()` restores `state.connected = True`
- All `MachineState` mutations and `notify()` posted to main thread via `Clock.schedule_once`
- `GalilController.disconnect()` now sets `self._driver = None` for fresh handle on reconnect
- `controller.cmd()` debug suppression extended to `MG hmi*` and `MG ct*` prefixes
- `DMCApp._start_poller()` / `_stop_poller()` wired at all connection/disconnect/shutdown points
- Full test suite: 206 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ControllerPoller module with tests** — `b4aaeea` (feat, TDD)
2. **Task 2: Wire poller into main.py and fix controller reconnect** — `6573977` (feat)

## Files Created/Modified

- `src/dmccodegui/hmi/poll.py` — ControllerPoller class (new, 108 lines)
- `tests/test_poll.py` — 8 unit tests covering all required behaviors (new, 215 lines)
- `src/dmccodegui/hmi/__init__.py` — poll added to `__all__` (no eager import to avoid circular)
- `src/dmccodegui/main.py` — ControllerPoller import, `_poller` field, `_start_poller()`/`_stop_poller()` methods, lifecycle wiring
- `src/dmccodegui/controller.py` — `disconnect()` sets `_driver = None`; `cmd()` suppresses poll-frequency MG prefixes

## Decisions Made

- **TYPE_CHECKING guard:** `poll.py` imports `MachineState` and `GalilController` only under `TYPE_CHECKING` to avoid circular import. The import chain is `app_state.py` → `hmi/dmc_vars.py` and `hmi/__init__.py` → (would import poll → app_state again). Lazy import at runtime is not needed since the type hints are strings only.
- **No eager import in hmi/__init__.py:** Importing `poll` eagerly would trigger Kivy import during `app_state.py` initialization, breaking the test suite. `poll` is available in `__all__` for explicit import consumers.
- **7 separate MG commands:** Individual reads per RESEARCH.md recommendation — batch `MG var1, var2` parsing is medium confidence and untested on this firmware.

## Deviations from Plan

**1. [Rule 1 - Bug] Circular import when hmi/__init__.py eagerly imported poll**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** `hmi/__init__.py` importing `poll` caused `app_state.py` to fail with circular import because `app_state` imports `hmi.dmc_vars` and `hmi.__init__` would then import `poll` which imports `app_state`
- **Fix:** Removed eager import from `__init__.py`; added `poll` to `__all__` only. Used `TYPE_CHECKING` guard in `poll.py` for type hint imports.
- **Files modified:** `src/dmccodegui/hmi/__init__.py`, `src/dmccodegui/hmi/poll.py`
- **Commit:** `b4aaeea`

## Issues Encountered

None beyond the circular import deviation (auto-fixed).

## User Setup Required

None.

## Next Phase Readiness

- Plan 03 (RunScreen wiring) can now bind to `MachineState.dmc_state`, `pos`, `session_knife_count`, `stone_knife_count`, `cycle_running` — all updated at 10 Hz
- Phase 11 (E-STOP) builds on the disconnect/reconnect infrastructure established here
- All 206 tests pass

## Self-Check: PASSED

Files verified:
- `src/dmccodegui/hmi/poll.py` — FOUND
- `tests/test_poll.py` — FOUND
- Task commits `b4aaeea` and `6573977` — FOUND in git log

---
*Phase: 10-state-poll*
*Completed: 2026-04-06*
