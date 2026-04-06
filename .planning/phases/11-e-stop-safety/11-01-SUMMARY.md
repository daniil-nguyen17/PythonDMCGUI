---
phase: 11-e-stop-safety
plan: "01"
subsystem: jobs-controller-poll
tags: [e-stop, safety, priority-queue, polling, tdd]
dependency_graph:
  requires: []
  provides:
    - submit_urgent() priority job mechanism
    - GalilController.reset_handle() GClose+GOpen wrapper
    - MachineState.program_running field
    - ControllerPoller _XQ read feeding program_running
  affects:
    - src/dmccodegui/utils/jobs.py
    - src/dmccodegui/controller.py
    - src/dmccodegui/app_state.py
    - src/dmccodegui/hmi/poll.py
tech_stack:
  added: []
  patterns:
    - Priority queue with maxsize=1 for urgent job preemption
    - threading.Event for cancel signaling to in-flight jobs
    - Isolated try/except for _XQ poll to prevent disconnect cascades
    - Conservative safety default (program_running=True on read failure)
key_files:
  created:
    - tests/test_jobs.py
  modified:
    - src/dmccodegui/utils/jobs.py
    - src/dmccodegui/controller.py
    - src/dmccodegui/app_state.py
    - src/dmccodegui/hmi/poll.py
    - tests/test_poll.py
decisions:
  - "_cancel_event is cleared by the worker after executing the urgent job, not by the caller — avoids race where caller clears before urgent job runs"
  - "program_running defaults to True on _XQ read failure — conservative safety: RECOVER button stays disabled when controller state is uncertain"
  - "_apply() uses default arg program_running=True so existing tests calling _apply with 7 args continue to work without modification"
  - "MG _XQ suppressed in is_status_command check to avoid 10 Hz log flood alongside other polling commands"
metrics:
  duration_minutes: 3
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_changed: 5
---

# Phase 11 Plan 01: Priority Job Infrastructure and Program Running Poll Summary

**One-liner:** Priority queue with urgent preemption, GClose/GOpen handle reset, and _XQ-based program_running field for E-STOP safety foundation.

## What Was Built

### Task 1: submit_urgent() and reset_handle()

**jobs.py — JobThread priority queue:**
- `_urgent_queue: Queue(maxsize=1)` — bounded so only one urgent job can be pending
- `_cancel_event: threading.Event` — set on `submit_urgent()`, cleared by worker after running urgent job
- `submit_urgent()` method: sets cancel event, drains stale queue entry, enqueues new urgent job
- `_run()` checks urgent queue at loop top and after each normal job (two check points)
- `cancel_event` read-only property for in-flight jobs to observe
- Module-level `submit_urgent()` convenience function

**controller.py — reset_handle():**
- `self._address` stored in `__init__`, populated on successful `connect()`
- `reset_handle(address=None)` tries `GClose()` then `GOpen(addr)`: returns True on success, sets `_connected=False` on failure
- `MG _XQ` added to `is_status_command` suppression list

### Task 2: program_running field and _XQ poll

**app_state.py:**
- `program_running: bool = False` added to `MachineState` dataclass after `stone_knife_count`

**poll.py — _XQ isolated read:**
- After the 7-variable main try block, a separate try/except reads `MG _XQ`
- `program_running = (xq_raw >= 0)` — negative _XQ means no program thread running
- Failure defaults to `program_running = True` (conservative: disable RECOVER if uncertain)
- `_apply()` accepts `program_running: bool = True` as 8th arg and writes `state.program_running`

## Tests

| File | Tests Added | Result |
|------|-------------|--------|
| tests/test_jobs.py | 7 new (priority ordering, cancel event, module-level, GClose/GOpen order, failure path, no-address guard, stored address) | 7/7 pass |
| tests/test_poll.py | 5 new (default False, apply True, apply False, XQ failure conservative, XQ failure no fail_count increment) | 5/5 pass |

**Full regression:** 218/218 tests pass

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

**Additional test:** Added `test_reset_handle_uses_stored_address_when_none_given` and `test_reset_handle_returns_false_when_no_address` — these were implied by the spec but not explicitly listed. Added for completeness.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `src/dmccodegui/utils/jobs.py` contains `submit_urgent` | FOUND |
| `src/dmccodegui/controller.py` contains `reset_handle` | FOUND |
| `src/dmccodegui/app_state.py` contains `program_running` | FOUND |
| `src/dmccodegui/hmi/poll.py` contains `MG _XQ` | FOUND |
| `tests/test_jobs.py` exists | FOUND |
| Commit f53764f exists | FOUND |
| Commit 4e4fb38 exists | FOUND |
| JobThread.submit_urgent is callable | PASS |
| cancel_event is a property | PASS |
| module-level submit_urgent is callable | PASS |
| GalilController.reset_handle exists | PASS |
| MachineState.program_running field exists | PASS |
| ControllerPoller._apply has program_running param | PASS |
| Full suite 218/218 | PASS |
