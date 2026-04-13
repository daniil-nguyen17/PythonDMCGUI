---
phase: 23
plan: 03
subsystem: hmi/controller-communication
tags: [integration, mg-reader, batch-read, refactor, run-screen]
dependency_graph:
  requires: ["23-01", "23-02"]
  provides: ["unified-tick-pos", "app-wide-mg-reader", "per-screen-mg-removal"]
  affects: ["flat_grind/run.py", "serration/run.py", "convex/run.py", "main.py", "base.py"]
tech_stack:
  added: []
  patterns:
    - "App-wide MgReader handler registration pattern (add_log_handler -> unreg callable)"
    - "read_all_state() single-call batch replacing 2-call position+state reads"
    - "Screen registers on on_pre_enter, unregisters on on_leave via stored callable"
key_files:
  created: []
  modified:
    - src/dmccodegui/screens/flat_grind/run.py
    - src/dmccodegui/screens/serration/run.py
    - src/dmccodegui/screens/convex/run.py
    - src/dmccodegui/main.py
    - src/dmccodegui/screens/base.py
    - tests/test_base_classes.py
    - tests/test_screen_loader.py
decisions:
  - "MgReader lifecycle uses _start_mg_reader() / _stop_mg_reader() on DMCApp to encapsulate address resolution"
  - "Serration _on_mg_log keeps 100-line cap matching existing behavior; flat_grind/convex _append_mg_log keeps 200-line cap"
  - "base.py cleanup() now unregisters _mg_log_unreg instead of signalling per-screen thread"
  - "test_base_classes.py and test_screen_loader.py updated to reflect new MgReader handler pattern"
metrics:
  duration_minutes: 9
  tasks_completed: 2
  tasks_total: 2
  files_changed: 7
  completed_date: "2026-04-13"
---

# Phase 23 Plan 03: Integration — read_all_state + app-wide MgReader Summary

Integration plan that wires read_all_state() and app-wide MgReader into all 3 RunScreens, replacing 2-batch MG calls in _tick_pos and removing all per-screen MG reader thread infrastructure.

## What Was Built

**Task 1: Unify _tick_pos in all 3 run screens**

All three `_tick_pos` methods now call `read_all_state(ctrl)` (Plan 01 output) as a single-batch MG command instead of the previous 2-round-trip pattern (separate positions batch + state batch).

- `flat_grind/run.py`: added `from ...hmi.poll import read_all_state`; replaced 2-batch `ctrl.cmd()` calls with `result = read_all_state(ctrl)`. Plot buffer feed and grind-end detection preserved.
- `serration/run.py`: same import; D axis from batch result ignored (unpacked as `_d`) — Serration has no D display.
- `convex/run.py`: same import and identical replacement to flat_grind.

Busy guard, cancel_event bail, and all screen-specific post-read logic preserved unchanged.

**Task 2: App-wide MgReader lifecycle + per-screen removal**

`main.py` changes:
- Imports `MgReader` from `hmi.mg_reader`
- Creates `self.mg_reader = MgReader()` in `__init__` (public attribute — screens access via `App.get_running_app().mg_reader`)
- `_start_mg_reader()` resolves address from `state.connected_address` or controller `_address`, then calls `self.mg_reader.start(addr)`
- `_stop_mg_reader()` calls `self.mg_reader.stop()`
- Start called in: `_on_connect_from_setup`, pre-existing connection path in `build()`, auto-connect path in `build()`
- Stop called in: `on_stop()`, `disconnect_and_refresh()`

All 3 run screens — per-screen MG infrastructure removed:
- `import threading` removed from flat_grind/run.py and convex/run.py (serration also removed)
- `_mg_thread` and `_mg_stop_event` class attributes removed from all 3
- `_start_mg_reader()`, `_stop_mg_reader()`, `_mg_reader_loop()` methods deleted from all 3
- `on_pre_enter`: replaced `self._start_mg_reader()` with MgReader handler registration (`add_log_handler`)
- `on_leave`: replaced `self._stop_mg_reader()` with unregister callable call

`base.py` cleanup() updated:
- Removed `_mg_stop_event.set()` signal and `_mg_thread = None` assignment
- Added `_mg_log_unreg()` call to unregister screen handler if it was registered
- Updated docstring to reflect new teardown step 2

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_base_classes.py had 2 stale tests expecting old _mg_thread/_mg_stop_event cleanup behavior**
- **Found during:** Task 2 verification
- **Issue:** `test_cleanup_base_run_screen_sets_mg_stop_event` and `test_cleanup_base_run_screen_clears_mg_thread_reference` tested the removed per-screen thread pattern
- **Fix:** Replaced with `test_cleanup_base_run_screen_calls_mg_log_unreg` and `test_cleanup_base_run_screen_clears_mg_log_unreg_reference` that verify the new MgReader handler unregistration behavior
- **Files modified:** tests/test_base_classes.py
- **Commit:** 85dea33

**2. [Rule 3 - Blocker] test_screen_loader.py _BareApp missing mg_reader and _stop_mg_reader**
- **Found during:** Task 2 verification
- **Issue:** `_BareApp` mock used in 3 on_stop tests doesn't have `mg_reader` or `_stop_mg_reader` — `DMCApp.on_stop()` now calls `self._stop_mg_reader()` which raised `AttributeError`
- **Fix:** Added `self.mg_reader = MagicMock()` to `_BareApp.__init__` and added `_stop_mg_reader()` stub method that delegates to `self.mg_reader.stop()`
- **Files modified:** tests/test_screen_loader.py
- **Commit:** 85dea33

## Test Results

- Pre-plan baseline: 6 pre-existing failures (status_bar localization + test_main_estop)
- Post-plan: same 6 pre-existing failures, 0 new failures
- Task 1 target tests: 71 passed (test_run_screen + test_flat_grind_widgets + test_serration_screens + test_convex_screens)
- Full suite: 444 passed, 6 pre-existing failures

## Self-Check: PASSED

All modified files exist. Both task commits verified (26113ad, 85dea33). Full test suite confirms 444 passed with no new failures introduced.
