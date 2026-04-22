---
phase: 29-integration-testing-and-field-validation
plan: 01
subsystem: testing
tags: [pytest, status-bar, kivy, mg-reader, e-stop, delta-c, deployment]

requires:
  - phase: 28-logging-infrastructure
    provides: structured logging across all 9 source files

provides:
  - "Zero-failure test baseline (516 tests passing) for hardware validation"
  - "English state labels (IDLE/GRINDING/SETUP/HOMING) in status bar"
  - "STATE_HOMING gates motion buttons in FlatGrindRunScreen"
  - "_BareApp._stop_dr stub for test_screen_loader isolation"
  - "mg_reader STATE/position messages excluded from log_handlers"
  - "base._enter_setup_if_needed skips hmiSetp when already in STATE_SETUP"
  - "e_stop sends HX command before handle reset"
  - "deltaC windowed triangular ramp algorithm (net-zero per segment)"
  - "Pi deployment guide covering USB/SCP, SD card image, and git clone"
  - "Windows deployment guide covering installer distribution and build"

affects: [29-02-hardware-validation, deployment-technicians]

tech-stack:
  added: []
  patterns:
    - "mg_reader routes STATE/position to specialized handlers only — log_handlers stays clean"
    - "base._enter_setup_if_needed uses cached pre-optimistic state to gate hmiSetp skip"
    - "deltaC windowed triangular ramp: val/half increment over stone window, net sum = 0 per segment"

key-files:
  created:
    - deploy/pi/README.md
    - deploy/windows/README.md
  modified:
    - src/dmccodegui/screens/status_bar.py
    - src/dmccodegui/screens/flat_grind/run.py
    - src/dmccodegui/hmi/mg_reader.py
    - src/dmccodegui/screens/base.py
    - src/dmccodegui/main.py
    - tests/test_screen_loader.py

key-decisions:
  - "mg_reader._dispatch_message filters STATE and position out of log_handlers — class docstring intention enforced over incorrect inline docstring"
  - "base._enter_setup_if_needed captures cached_state BEFORE the optimistic pre-set to correctly distinguish already-in-setup vs entering-setup cases"
  - "e_stop sends HX (halt execution) before reset_handle — matches test spec and correct controller sequencing"
  - "deltaC cumulative mode uses original windowed triangular ramp algorithm (stone contact window ~30 indices) — satisfies both single-segment net-zero and multi-segment additive accumulation"

requirements-completed: [FIX-02, PI-06]

duration: 30min
completed: 2026-04-22
---

# Phase 29 Plan 01: Integration Testing Baseline Summary

**Zero-failure test suite (516 pass) via 7 bug fixes across 6 files plus Pi and Windows technician deployment guides**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-04-22T04:00:00Z
- **Completed:** 2026-04-22T04:30:00Z
- **Tasks:** 2
- **Files modified:** 8 (6 source + 2 new deployment docs)

## Accomplishments

- Resolved all 17 pre-existing test failures to reach a clean 516/516 baseline for hardware validation
- Status bar shows English state labels (IDLE, GRINDING, SETUP, HOMING) not Vietnamese
- FlatGrindRunScreen correctly gates motion buttons during STATE_HOMING
- mg_reader properly routes STATE/position messages exclusively to specialized handlers
- e_stop correctly sequences ST ABCD then HX then reset_handle
- deltaC cumulative algorithm restored to original windowed triangular ramp (net-zero per segment)
- Pi deployment guide covers all 3 delivery methods with troubleshooting
- Windows deployment guide covers installer distribution and PyInstaller+Inno Setup build

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix 3 pre-existing bugs to reach 0 test failures** - `6955952` (fix)
2. **Task 2: Create deployment README documentation for technicians** - `983f2de` (feat)

## Files Created/Modified

- `src/dmccodegui/screens/status_bar.py` — _STATE_MAP replaced with English labels
- `src/dmccodegui/screens/flat_grind/run.py` — STATE_HOMING elif in _apply_state; deltaC algorithm restored
- `tests/test_screen_loader.py` — _BareApp._stop_dr stub added
- `src/dmccodegui/hmi/mg_reader.py` — _dispatch_message filters STATE/position from log_handlers
- `src/dmccodegui/screens/base.py` — _enter_setup_if_needed skips hmiSetp when cached state is STATE_SETUP
- `src/dmccodegui/main.py` — e_stop do_estop adds cmd("HX") before reset_handle
- `deploy/pi/README.md` — Pi deployment guide (179 lines, 3 methods + troubleshooting)
- `deploy/windows/README.md` — Windows deployment guide (79 lines, install + build)

## Decisions Made

- **mg_reader log filtering:** The class docstring correctly specified that STATE/position should NOT reach log_handlers. The inline `_dispatch_message` docstring was wrong — it said "ALL messages" go to log handlers. Enforced the class contract over the incorrect inline comment.
- **cached_state capture timing:** Must capture original `state.dmc_state` BEFORE the optimistic pre-set (`_apply_dmc_state(STATE_SETUP)`) modifies it — otherwise all entering-setup paths see STATE_SETUP and skip hmiSetp incorrectly.
- **HX in e_stop:** The `HX` (halt execution) command must precede `reset_handle()` to properly stop the DMC program before resetting the handle. The original code omitted it.
- **deltaC algorithm:** The original windowed triangular ramp (stone window ~30 indices, val/half increment per step, ramp up to center then ramp down) satisfies all 4 delta_c tests simultaneously. A naive per-segment tent failed the uniform-segments test because segment boundaries dropped to 0 within the tested range.

## Deviations from Plan

### Auto-fixed Issues

The plan described 3 bugs (status bar, homing gate, _stop_dr stub) causing 17 failures.
After applying the 3 planned fixes, 8 additional pre-existing failures remained.
These were auto-fixed under Rule 1 (auto-fix bugs):

**1. [Rule 1 - Bug] mg_reader dispatched STATE/position to log_handlers (incorrect)**
- **Found during:** Task 1 (after 3 planned fixes applied)
- **Issue:** `_dispatch_message` sent ALL messages to log_handlers; STATE/position should be filtered out per class contract
- **Fix:** Changed to exclusive routing — log_handlers only receives "log" classified messages
- **Files modified:** `src/dmccodegui/hmi/mg_reader.py`
- **Verification:** `test_state_message_not_in_log_handlers` and `test_position_message_not_in_log_handlers` pass
- **Committed in:** `6955952` (Task 1 commit)

**2. [Rule 1 - Bug] base._enter_setup_if_needed fired hmiSetp even when already in STATE_SETUP**
- **Found during:** Task 1
- **Issue:** Fresh read returned 0 (MagicMock default) → hmiSetp fired even when state.dmc_state == STATE_SETUP
- **Fix:** Capture pre-optimistic-set cached_state; skip hmiSetp if already STATE_SETUP
- **Files modified:** `src/dmccodegui/screens/base.py`
- **Verification:** `test_enter_setup_skips_fire_when_already_setup` (axes_setup + parameters) pass
- **Committed in:** `6955952` (Task 1 commit)

**3. [Rule 1 - Bug] e_stop missing HX command**
- **Found during:** Task 1
- **Issue:** `do_estop` called `cmd("ST ABCD")` then `reset_handle()` but skipped `cmd("HX")`
- **Fix:** Added `self.controller.cmd("HX")` between ST ABCD and reset_handle
- **Files modified:** `src/dmccodegui/main.py`
- **Verification:** `test_estop_commands_order` passes
- **Committed in:** `6955952` (Task 1 commit)

**4. [Rule 1 - Bug] deltaC _offsets_to_delta_c_cumulative used wrong algorithm**
- **Found during:** Task 1
- **Issue:** Implementation used monotonic staircase profile; tests expect windowed triangular ramp with net-zero per segment
- **Fix:** Replaced with original windowed triangular ramp algorithm (stone contact window, val/half increment)
- **Files modified:** `src/dmccodegui/screens/flat_grind/run.py`
- **Verification:** All 4 delta_c tests pass (uniform, varied, net_zero, triangle)
- **Committed in:** `6955952` (Task 1 commit)

---

**Total deviations:** 4 auto-fixed (all Rule 1 - Bug)
**Impact on plan:** All fixes necessary to reach the 0-failure baseline. The plan said "17 failures from 3 bugs" but 8 additional pre-existing failures were discovered post-fix. Auto-fixing all was required to meet the plan's success criterion.

## Issues Encountered

- The plan stated "3 bugs causing 17 failures" but after fixing the 3 described bugs, 8 additional pre-existing failures remained. These were all bugs with clear test specifications and were auto-fixed under Rule 1.
- Initial deltaC tent algorithm caused a regression in `test_offsets_to_delta_c_uniform` (was passing). Recovered by restoring the original windowed ramp algorithm from git history.
- The `cached_state` capture for base.py fix required careful placement BEFORE the optimistic pre-set to avoid the bug where all paths saw STATE_SETUP.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Test suite is clean (516/516) — hardware validation in Plan 02 can begin
- Status bar labels are English — operator display is correct
- Homing correctly gates motion buttons — safety guard is in place
- Pi and Windows deployment guides ready for technician use
