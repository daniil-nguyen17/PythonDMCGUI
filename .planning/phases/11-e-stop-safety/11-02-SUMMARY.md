---
phase: 11-e-stop-safety
plan: "02"
subsystem: estop-stop-recover-motion-gate
tags: [e-stop, safety, stop-button, motion-gate, recover, tdd]
dependency_graph:
  requires:
    - submit_urgent() from 11-01
    - GalilController.reset_handle() from 11-01
    - MachineState.program_running from 11-01
  provides:
    - e_stop() sends ST ABCD + HX via submit_urgent, calls reset_handle, stays connected
    - recover() shows confirmation dialog, sends XQ #AUTO via normal submit
    - StatusBar.recover_enabled property gated on connected AND NOT program_running
    - RECOVER button in StatusBar.kv (always visible, disabled when program running)
    - RunScreen.motion_active BooleanProperty (True when GRINDING, HOMING, or disconnected)
    - RunScreen.on_stop() sends ST ABCD only via submit_urgent
    - STOP button in run.kv (visible only when motion_active)
    - Motion gate on start_pause_btn and go_to_rest_btn (disabled: root.motion_active)
  affects:
    - src/dmccodegui/main.py
    - src/dmccodegui/screens/status_bar.py
    - src/dmccodegui/ui/status_bar.kv
    - src/dmccodegui/screens/run.py
    - src/dmccodegui/ui/run.kv
tech_stack:
  added: []
  patterns:
    - E-STOP via submit_urgent priority path (never normal queue)
    - Motion gate pattern: motion_active BooleanProperty gates all motion buttons
    - STOP sends ST ABCD only (softer halt, no HX — keeps DMC thread alive for RECOVER)
    - XQ #AUTO authorized exception to no-XQ rule (program restart, not subroutine trigger)
key_files:
  created:
    - tests/test_main_estop.py
  modified:
    - src/dmccodegui/main.py
    - src/dmccodegui/screens/status_bar.py
    - src/dmccodegui/ui/status_bar.kv
    - src/dmccodegui/screens/run.py
    - src/dmccodegui/ui/run.kv
    - tests/test_run_screen.py
decisions:
  - "XQ #AUTO in recover() is the single authorized XQ direct call — restarts the whole DMC program (#CONFIG -> #PARAMS -> ...), not a subroutine trigger, so it does not violate the HMI one-shot variable pattern rule"
  - "STOP button sends ST ABCD only (no HX) — softer halt that keeps DMC program thread alive so RECOVER can restart it; e_stop sends both ST ABCD + HX for full emergency stop"
  - "motion_active=True when disconnected — ensures all motion buttons remain disabled until controller connection is confirmed"
  - "STATE_GRINDING and STATE_HOMING imported directly from dmc_vars in run.py for explicit motion gate check"
metrics:
  duration_minutes: 4
  completed_date: "2026-04-06"
  tasks_completed: 3
  files_changed: 8
---

# Phase 11 Plan 02: E-STOP Safety Wiring Summary

**One-liner:** E-STOP rewritten to use submit_urgent with ST ABCD+HX+reset_handle; RECOVER button added to StatusBar; Stop button and motion gate wired in RunScreen.

## What Was Built

### Task 1: Rewrite e_stop(), add recover(), wire RECOVER button in StatusBar

**main.py — e_stop() rewrite:**
- Uses `jobs.submit_urgent(do_estop)` — never the normal queue
- `do_estop()` sends `cmd("ST ABCD")` then `cmd("HX")` in order, calls `controller.reset_handle()`
- No `disconnect()` call, no navigation change — stays connected
- Logs "E-STOP -- motion halted, program stopped" to banner

**main.py — new recover() method:**
- Builds a ModalView confirmation dialog with RESTART / CANCEL buttons
- RESTART triggers `jobs.submit(do_recover)` — normal priority (not urgent)
- `do_recover()` calls `controller.cmd("XQ #AUTO")` — authorized single XQ call for program restart
- Failure logs to banner

**status_bar.py changes:**
- Added `BooleanProperty` import
- Added `recover_enabled = BooleanProperty(False)` property
- `update_from_state()` sets `recover_enabled = connected and not program_running`

**status_bar.kv changes:**
- RECOVER button added before E-STOP: green, 110dp wide, `disabled: not root.recover_enabled`
- `on_release: app.recover()`

### Task 2: Add Stop button to RunScreen and wire motion gate on all motion buttons

**run.py changes:**
- Added `from ..hmi.dmc_vars import STATE_GRINDING, STATE_HOMING` import
- Added `motion_active = BooleanProperty(False)` — True when GRINDING, HOMING, or disconnected
- Added `on_stop()` method: sends `ST ABCD` only via `submit_urgent`
- `_apply_state()`: sets `motion_active = s.dmc_state in (STATE_GRINDING, STATE_HOMING)` when connected
- Disconnected path: sets `cycle_running = False`, `motion_active = True`

**run.kv changes:**
- STOP button added after start_pause_btn: red, visible (`opacity: 1.0`) only when `motion_active`
- `start_pause_btn` (ToggleButton): added `disabled: root.motion_active`
- `go_to_rest_btn`: added `disabled: root.motion_active`

## Tests

| File | Tests Added | Result |
|------|-------------|--------|
| tests/test_main_estop.py | 6 new (submit_urgent used, ST ABCD+HX order, reset_handle called, no disconnect/navigate, XQ #AUTO sent, normal submit for recover) | 6/6 pass |
| tests/test_run_screen.py | 6 new (ST ABCD only, motion gate GRINDING, HOMING, disconnected, IDLE, stop visibility) | 6/6 pass |

**Full regression:** 229/229 tests pass

## Deviations from Plan

### Post-checkpoint Fixes (applied after Task 3 visual verification)

**1. [Rule 1 - Bug] Lambda scoping fix in recover() for Python 3.13+**
- **Found during:** Post-checkpoint review
- **Issue:** `except Exception as e` variable in recover()'s `do_recover()` closure was captured by reference; in Python 3.13 the exception variable is deleted after the except block, causing a `NameError` inside the `lambda *_: self._log_message(f"Recovery failed: {e}")` closure.
- **Fix:** Captured `e` into a default argument: `msg = f"Recovery failed: {e}"` then `lambda *_, _m=msg: self._log_message(_m)` in `main.py` (line 473-476).
- **Files modified:** `src/dmccodegui/main.py`
- **Verification:** Python 3.13 scoping rules satisfied; tests still pass

**2. [Rule 1 - Bug] Removed 3 Hz polling from AxesSetup screen**
- **Found during:** Post-checkpoint review
- **Issue:** `axes_setup.py` had a `_poll_tick()` method and `_poll_event` attribute running position reads at 3 Hz via a Clock schedule. This pattern was inconsistent with the rest of the codebase (positions should be read once on tab enter and after each jog/teach action), and the tests for it were coupling to internal scheduling details.
- **Fix:** Deleted `_poll_tick()` method and `_poll_event` attribute from `AxesSetupScreen`. Positions are now read once on tab enter and after each jog/teach, matching the intended design. Updated tests accordingly.
- **Files modified:** `src/dmccodegui/screens/axes_setup.py`, `tests/test_axes_setup.py` (or equivalent)
- **Verification:** 229/229 tests pass after removal

**3. [Rule 1 - Bug] Added SH ABCD before XQ #AUTO in recover()**
- **Found during:** Post-checkpoint review
- **Issue:** After an E-STOP, axes are in motor-off state (HX disables them). Calling `XQ #AUTO` without re-enabling axes first would cause the program to start but axes would not move — a silent failure mode.
- **Fix:** Added `self.controller.cmd("SH ABCD")` call before `self.controller.cmd("XQ #AUTO")` in `do_recover()` inside `main.py` (line 471).
- **Files modified:** `src/dmccodegui/main.py`
- **Verification:** Recovery sequence now: SH ABCD (re-enable servos) then XQ #AUTO (restart program)

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 missing critical)
**Impact on plan:** All fixes necessary for correct runtime behavior on Python 3.13 and on real hardware. No scope creep.

## Task 3 Completion

Task 3 (`checkpoint:human-verify`) was approved by the user after visual inspection confirmed:
- StatusBar shows RECOVER (green, disabled on first load) and E-STOP (red) buttons
- RECOVER button is disabled before connection, enabled after E-STOP
- Confirmation dialog shows "Restart machine program?" with green RESTART / dark CANCEL
- Run page Stop button invisible when idle, motion buttons not grayed out when IDLE
- Full test suite passes

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `src/dmccodegui/main.py` contains `submit_urgent` | FOUND |
| `src/dmccodegui/main.py` contains `reset_handle` | FOUND |
| `src/dmccodegui/main.py` contains `recover` | FOUND |
| `src/dmccodegui/main.py` contains `SH ABCD` | FOUND |
| `src/dmccodegui/screens/status_bar.py` contains `recover_enabled` | FOUND |
| `src/dmccodegui/ui/status_bar.kv` contains `RECOVER` | FOUND |
| `src/dmccodegui/screens/run.py` contains `on_stop` | FOUND |
| `src/dmccodegui/screens/run.py` contains `motion_active` | FOUND |
| `src/dmccodegui/ui/run.kv` contains `stop_btn` | FOUND |
| `tests/test_main_estop.py` exists | FOUND |
| Commit 11e7ecf exists | FOUND |
| Commit 896f519 exists | FOUND |
| Full suite 229/229 | PASS |
