---
phase: 13-setup-loop
plan: "02"
subsystem: axes-setup-screen, hmi-wiring
tags: [hmi-triggers, axes-setup, jog-gates, smart-enter-exit, new-session, tdd]
dependency_graph:
  requires: [13-01]
  provides: [smart-enter-exit-axes-setup, hmi-quick-actions, jog-state-gate, jog-motion-gate, new-session-trigger]
  affects:
    - src/dmccodegui/screens/axes_setup.py
    - tests/test_axes_setup.py
tech_stack:
  added: []
  patterns: [one-shot-hmi-trigger, state-gate-before-action, in-progress-motion-gate, tdd-red-green]
key_files:
  created: []
  modified:
    - src/dmccodegui/screens/axes_setup.py
    - tests/test_axes_setup.py
decisions:
  - "Smart enter skips hmiSetp=0 when dmc_state already STATE_SETUP — avoids re-triggering setup on sibling-screen navigation"
  - "_SETUP_SCREENS frozenset at module level defines which screens share the setup context (axes_setup + parameters)"
  - "on_leave fires hmiExSt=0 only to non-setup screens — controller stays in STATE_SETUP while navigating within setup siblings"
  - "_BG in-progress gate placed inside do_jog() at top — checked on background thread after state gate passes on main thread"
  - "Stale test assertions (swGoRest/swGoStart/swHomeAll and jog cmds[0]) updated as Rule 1 auto-fix alongside production changes"
metrics:
  duration_minutes: 6
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_modified: 2
---

# Phase 13 Plan 02: AxesSetupScreen HMI Rewire Summary

**One-liner:** AxesSetupScreen rewired from dead software variables to real HMI one-shot triggers, with smart setup enter/exit logic, dmc_state and motion-in-progress jog gates, and a New Session confirmation dialog.

## What Was Built

Replaced all dead `swGoRest=1` / `swGoStart=1` / `swHomeAll=1` software variable calls with proper HMI one-shot trigger commands, and added two smart lifecycle behaviors plus jog safety gates:

- **Smart enter:** `on_pre_enter` reads `dmc_state` first; only fires `hmiSetp=0` when NOT already in `STATE_SETUP`. Navigating from the parameters screen to axes_setup skips the re-fire and just refreshes values.
- **Smart exit:** `on_leave` fires `hmiExSt=0` only when navigating to a non-setup screen. The `_SETUP_SCREENS` frozenset (`{"axes_setup", "parameters"}`) defines sibling screens that share the setup context.
- **HMI quick actions:** `go_to_rest_all` → `hmiGoRs=0`, `go_to_start_all` → `hmiGoSt=0`, `home_all` → `hmiHome=0`. All via the new `_fire_hmi_trigger(var, label)` helper.
- **Jog state gate:** `jog_axis` returns early if `dmc_state != STATE_SETUP` (operator or grinding state — no jogging allowed).
- **Jog in-progress gate:** Inside `do_jog()`, `MG _BG{axis}` is checked before sending `PR/BG`. Returns early if previous jog still running.
- **New Session:** `on_new_session` gated on `state.setup_unlocked`. Unlocked users see a confirmation popup; operators are silently ignored. Confirmed → `_fire_new_session()` → `hmiNewS=0`.
- **Dead code removed:** `_send_sw_var` method removed entirely.

## Tasks Completed

### Task 1: Write failing tests (TDD RED)
- Commit: `bc737a2`
- Files: `tests/test_axes_setup.py`
- Added 11 new test functions covering all new behaviors
- 9 fail immediately on production code; 2 pass trivially (enter-fires-when-not-in-setup, exit-skips-sibling) because current code happens to satisfy them already

### Task 2: Rewire AxesSetupScreen (TDD GREEN)
- Commit: `2a7a923`
- Files: `src/dmccodegui/screens/axes_setup.py`, `tests/test_axes_setup.py`
- All production changes applied; all 31 axes_setup tests pass; 262 total suite green

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated stale test assertions for quick actions and jog counts**
- **Found during:** Task 2 GREEN phase
- **Issue:** Three existing `test_quick_action_*` tests asserted `cmd("swGoRest=1")` etc. (the old dead pattern). Two `test_jog_counts_*` tests asserted `cmds[0] == "PRA=12000"` but the new `_BG` in-progress gate makes `"MG _BGA"` the first command.
- **Fix:** Updated 5 existing tests to match new behavior (HMI triggers and new cmd order). Also added `state.dmc_state = STATE_SETUP` to the jog count tests since the new state gate requires it.
- **Files modified:** `tests/test_axes_setup.py`
- **Commit:** `2a7a923`

## Verification Results

1. `python -m pytest tests/test_axes_setup.py -v` — **31 passed**
2. `python -m pytest tests/ -x -q` — **262 passed**
3. `grep "swGoRest|swGoStart|swHomeAll|_send_sw_var" axes_setup.py` — **no matches** (dead code removed)
4. `grep "HMI_GO_REST|HMI_GO_START|HMI_EXIT_SETUP|HMI_HOME|HMI_NEWS" axes_setup.py` — **all present** (6 lines)

## Self-Check: PASSED
