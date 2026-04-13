---
phase: 23
plan: 01
subsystem: controller-communication
tags: [polling, batching, gclib, dmc, tdd]
dependency_graph:
  requires: [phase-18-base-class-extraction]
  provides: [BATCH_CMD, read_all_state, PRIMARY_FLAGS, STATE-N-dmc-output]
  affects: [src/dmccodegui/hmi/poll.py, src/dmccodegui/hmi/dmc_vars.py, src/dmccodegui/controller.py, "4 Axis Stainless grind.dmc"]
tech_stack:
  added: []
  patterns: [stale-on-failure, mega-batch-MG, direct-connection-flags, tdd-red-green-refactor]
key_files:
  created: []
  modified:
    - src/dmccodegui/hmi/dmc_vars.py
    - src/dmccodegui/hmi/poll.py
    - src/dmccodegui/controller.py
    - tests/test_poll.py
    - tests/test_jobs.py
    - "4 Axis Stainless grind.dmc"
decisions:
  - "_TDA/_TDB/_TDC/_TDD (told/desired position) used in BATCH_CMD, not _TPA/_TPB/_TPC/_TPD"
  - "read_all_state() is module-level (not a method) so Plan 03 RunScreen._tick_pos can import it"
  - "Batch failure treats all 8 values as unavailable — stale-on-failure, not partial update"
  - "PRIMARY_FLAGS appended to GOpen address string; bare address stored in self._address for MG handle"
metrics:
  duration: 423s
  completed: 2026-04-13
  tasks_completed: 3
  files_changed: 6
---

# Phase 23 Plan 01: Controller Communication Optimization — Batch Reads and Connection Hardening Summary

Single-line summary: Mega-batch MG polling (7-8 individual calls collapsed to 1), gclib --direct/--timeout connection hardening, and STATE:N structured DMC output at every hmiState transition.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Add BATCH_CMD and read_all_state() with TDD | 16a4835 | dmc_vars.py, poll.py, tests/test_poll.py |
| 2 | Harden controller connections with --direct and --timeout | a0736e5 | controller.py, tests/test_poll.py |
| 3 | Add STATE:N emissions to DMC program | e789588 | 4 Axis Stainless grind.dmc, tests/test_jobs.py |

## What Was Built

### Task 1: Mega-batch MG polling

Added `BATCH_CMD` constant to `dmc_vars.py`:
```python
BATCH_CMD = "MG _TDA,_TDB,_TDC,_TDD,hmiState,ctSesKni,ctStnKni,_XQ"
```

Added module-level `read_all_state(ctrl)` to `poll.py` — issues exactly 1 `ctrl.cmd(BATCH_CMD)` call and returns `(a, b, c, d, dmc_state, ses_kni, stn_kni, program_running)` or `None` on failure.

Refactored `ControllerPoller._do_read()` from 7-8 individual MG calls to one `read_all_state()` call with stale-on-failure: if `None`, increment `_fail_count` and return without touching MachineState.

All 10 existing poll tests updated to use batched response format. 13 new tests added across `TestMegaBatchRead`, `TestBatchCallCount`, `TestStaleOnFailure`.

### Task 2: Connection hardening

Added `PRIMARY_FLAGS = "--direct --timeout 1000 -MG 0"` to `controller.py`. Both `connect()` and `reset_handle()` now call `GOpen(f"{address} {PRIMARY_FLAGS}")`. The bare address is stored in `self._address` for the MG handle (Plan 02) to use. Log message updated to include `--direct` and `timeout=1000ms`.

5 new `TestConnectionHardening` tests verify GOpen flags, log message format, and address fallback.

### Task 3: DMC STATE:N output

Added `MG "STATE:", hmiState {F0}` at all 9 `hmiState` assignment points in the DMC program (10 lines total including the #MAIN entry). Updated the `#MAIN` idle MG line to include `hmiState`, `ctSesKni`, and `ctStnKni` alongside position values.

## Decisions Made

1. **_TD vs _TP**: BATCH_CMD uses `_TDA/_TDB/_TDC/_TDD` (told/desired position). Per user decision captured in CONTEXT.md — told position is what the HMI cares about for display.

2. **read_all_state as module-level function**: Not a method on `ControllerPoller` so that Plan 03 `RunScreen._tick_pos` can import and reuse it without instantiating a poller.

3. **Stale-on-failure for entire batch**: If any part of the batch fails the entire `read_all_state()` returns `None`. Partial updates (e.g., positions succeed but state fails) are not possible with a single MG command — this simplifies failure handling.

4. **PRIMARY_FLAGS constant location**: Defined in `controller.py` module scope so tests can import it directly (`from dmccodegui.controller import PRIMARY_FLAGS`) and assert GOpen call arguments without hardcoding the flag string.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_jobs.py TestResetHandle to use PRIMARY_FLAGS format**
- **Found during:** Task 3 full suite run
- **Issue:** `test_reset_handle_calls_gclose_gopen` and `test_reset_handle_uses_stored_address_when_none_given` expected `GOpen("192.168.0.1")` but after Task 2, `reset_handle()` now calls `GOpen("192.168.0.1 --direct --timeout 1000 -MG 0")`
- **Fix:** Updated assertions to use `f"{addr} {PRIMARY_FLAGS}"` format
- **Files modified:** tests/test_jobs.py (included in Task 3 commit)
- **Commit:** e789588

### Pre-existing Failures (Out of Scope)

The following test failures existed before this plan and are NOT caused by plan changes:
- `tests/test_status_bar.py::TestStatusBarStateLabel` — 5 tests returning Vietnamese strings instead of English ("CHO" instead of "IDLE", etc.)
- `tests/test_main_estop.py::TestEStop::test_estop_commands_order`

Confirmed pre-existing by running `git stash` and verifying same failures before any plan changes.

## Verification Results

- `python -m pytest tests/test_poll.py -x -q` — 31 passed
- No individual `MG _TPA` calls remain in poll.py (grep returns 0)
- `--direct` appears 3 times in controller.py (PRIMARY_FLAGS constant + connect + reset_handle)
- `_TDA` appears in dmc_vars.py BATCH_CMD (told position confirmed, not _TP)
- `STATE:` appears 10 times in DMC file at all hmiState transition boundaries
- `ctSesKni` appears in the #MAIN IDLING MG line

## Self-Check: PASSED

All files verified present. All three task commits verified in git log:
- 16a4835: feat(23-01): add BATCH_CMD constant and read_all_state() with tests
- a0736e5: feat(23-01): harden controller connections with --direct and --timeout flags
- e789588: feat(23-01): add STATE:N emissions and hmiState/ctSesKni/ctStnKni to DMC idle output
