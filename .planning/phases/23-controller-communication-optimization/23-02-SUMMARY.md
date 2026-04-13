---
phase: 23-controller-communication-optimization
plan: "02"
subsystem: hmi
tags: [mg-reader, gclib, threading, kivy, tdd]
dependency_graph:
  requires: []
  provides: [MgReader]
  affects: [flat_grind/run.py, serration/run.py, convex/run.py]
tech_stack:
  added: []
  patterns: [Clock.schedule_once dispatch, --subscribe MG gclib handle, TDD red-green]
key_files:
  created:
    - src/dmccodegui/hmi/mg_reader.py
    - tests/test_mg_reader.py
  modified: []
decisions:
  - "_dispatch_message routes each message type to its typed handler list; state and position are explicitly excluded from log_handlers"
  - "_classify_line is a @staticmethod for pure testability — no thread machinery needed"
  - "_AXIS_PATTERN regex handles arbitrary KEY:VALUE pairs (e.g. hmiState:3, ctSesKni:5) naturally without hardcoding axis names"
  - "Unregister callables use 'if fn in list' guard so double-unregister is safe"
metrics:
  duration: "2m"
  completed_date: "2026-04-13"
  tasks_completed: 1
  files_changed: 2
---

# Phase 23 Plan 02: MgReader Module Summary

**One-liner:** App-wide MG subscriber with typed handler registration, Clock-dispatched delivery, and --direct --subscribe MG --timeout 500 handle.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Create MgReader module with tests (TDD red-green) | afbc987 (feat), 5220852 (test) | src/dmccodegui/hmi/mg_reader.py, tests/test_mg_reader.py |

## What Was Built

`src/dmccodegui/hmi/mg_reader.py` — standalone `MgReader` class that:

- Opens a second gclib handle with `"{address} --direct --subscribe MG --timeout 500"` and calls `GTimeout(500)` immediately after `GOpen`
- Classifies each incoming line via `_classify_line(line)` (static method, pure):
  - `STATE:N` → `("state", int)`
  - Lines starting with `IDLING FOR INPUT`, `PRE-LI`, `RUNNING`, `END REACHED` → `("position", dict)` where dict contains parsed float axis values and `"prefix"` key
  - Everything else → `("log", str)`
- Dispatches to typed handler lists via `Clock.schedule_once` (Kivy main thread)
- Filters STATE and position messages from log handlers (operator log stays clean)
- `add_log_handler` / `add_state_handler` / `add_position_handler` each return unregister callables
- `start(address)` / `stop()` thread lifecycle: double-start is no-op, `stop()` joins within 2s timeout

`tests/test_mg_reader.py` — 25 tests across 5 classes:
- `TestMgReaderDispatch`: `_classify_line` for all 4 position prefixes, STATE:N, freeform, negative values, extra keys
- `TestStateFilteredFromLog`: state and position never reach log handlers; freeform does
- `TestHandlerRegistration`: unregister callables work; multiple handlers receive same message
- `TestMgHandleTimeout`: `--direct --subscribe MG --timeout 500` in GOpen arg, GTimeout(500) called, GClose on exit
- `TestStartStop`: thread created on start, stop joins it, double-start is no-op, stop before start is safe

## Verification

```
python -m pytest tests/test_mg_reader.py -x -q
25 passed in 0.12s

python -m pytest tests/ -q --tb=short
436 passed, 8 pre-existing failures (test_status_bar, test_poll, test_main_estop — unrelated to MgReader)
```

## Deviations from Plan

None — plan executed exactly as written.

The pre-existing 8 test failures in test_status_bar, test_poll, and test_main_estop were present before this plan and are out of scope.

## Self-Check: PASSED
