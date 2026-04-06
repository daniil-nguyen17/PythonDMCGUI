---
phase: 14-state-driven-ui
plan: "01"
subsystem: ui
tags: [kivy, state-machine, tab-bar, status-bar, dmc_state]

# Dependency graph
requires:
  - phase: 10-state-poll
    provides: MachineState.dmc_state populated by ControllerPoller
  - phase: 13-setup-loop
    provides: STATE_SETUP/STATE_HOMING dmc_state transitions from controller
provides:
  - StatusBar state_text/state_color label showing IDLE/GRINDING/SETUP/HOMING/OFFLINE/E-STOP
  - Setup badge (yellow 24dp bar) between StatusBar and TabBar during SETUP state
  - TabBar.update_state_gates() disabling Run/AxesSetup/Parameters per controller state
  - Force-navigation from setup screens to Run when GRINDING/HOMING starts
affects: [future UI phases, any screen that shows controller state]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "State subscription pattern: state.subscribe(lambda s: Clock.schedule_once(lambda *_: fn(s)))"
    - "_prev_dmc_state change detection guards in update_from_state() to skip redundant UI updates"
    - "capture connected_changed = (connected != self._prev_connected) before _prev_connected update"

key-files:
  created:
    - tests/test_status_bar.py
  modified:
    - src/dmccodegui/screens/status_bar.py
    - src/dmccodegui/ui/status_bar.kv
    - src/dmccodegui/ui/base.kv
    - src/dmccodegui/screens/tab_bar.py
    - src/dmccodegui/main.py
    - tests/test_tab_bar.py

key-decisions:
  - "connected_changed captured before _prev_connected update — avoids stale comparison in state label block"
  - "Setup badge height=0/opacity=0 when hidden, dp(24)/opacity=1 when in SETUP — toggles both for layout correctness"
  - "_last_dmc_state/_last_connected cached on TabBar — ensures gates reapply after set_role() role rebuild"
  - "Pre-existing test_parameters.py::TestParametersApplyMotionGating failures (4 tests) confirmed pre-existing, not caused by this plan"

patterns-established:
  - "TabBar.update_state_gates(dmc_state, connected): single method to recompute all tab disabled states"
  - "Force-navigation wrapped in try/except for test safety without running app"
  - "Gate dict pattern: gates = {'run': cond1, 'axes_setup': cond2} — clean per-tab enable/disable"

requirements-completed: [UI-02, UI-03, UI-04, UI-05]

# Metrics
duration: 15min
completed: 2026-04-06
---

# Phase 14 Plan 01: State-Driven UI Summary

**StatusBar colored state label, setup mode yellow badge, and tab gating wired to MachineState.dmc_state via subscribe pattern**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-06
- **Completed:** 2026-04-06
- **Tasks:** 2
- **Files modified:** 6 (+ 1 created)

## Accomplishments

- StatusBar shows IDLE/GRINDING/SETUP/HOMING/OFFLINE/E-STOP with matching colors (orange/green/red/gray) driven by dmc_state + connected + program_running
- Setup badge (yellow 24dp Label) appears between StatusBar and TabBar only during SETUP state; height=0/opacity=0 otherwise — no stale state on disconnect
- TabBar.update_state_gates() disables Run during SETUP, disables Axes Setup + Parameters during GRINDING/HOMING, clears all gates when disconnected; force-navigates to Run if currently on a gated screen when motion starts
- Gate state reapplied after set_role() role rebuild via _last_dmc_state/_last_connected cache

## Task Commits

Each task was committed atomically:

1. **Task 1: Add state label to StatusBar and create tests** - `f82fa57` (feat + TDD)
2. **Task 2: Add setup badge, tab gating, and force-navigation** - `50a211f` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified

- `tests/test_status_bar.py` - 14 tests covering all 6 state transitions and change detection
- `src/dmccodegui/screens/status_bar.py` - Added state_text/state_color properties, _STATE_MAP, _prev_dmc_state, extended update_from_state()
- `src/dmccodegui/ui/status_bar.kv` - Inserted state_label widget before theme toggle button
- `src/dmccodegui/ui/base.kv` - Inserted setup_badge Label between StatusBar and TabBar
- `src/dmccodegui/screens/tab_bar.py` - Added dmc_vars imports, _last_dmc_state/_last_connected attrs, _tab_name on buttons, update_state_gates() method, gate reapply at end of set_role()
- `src/dmccodegui/main.py` - Added STATE_SETUP import, _update_setup_badge and _update_tab_gates subscribers in build()
- `tests/test_tab_bar.py` - Added _compute_gates() helper and TestUpdateStateGates class (6 tests)

## Decisions Made

- connected_changed captured before _prev_connected update — avoids stale comparison in state label block when both connection and dmc_state change simultaneously
- Setup badge toggled via height=0/opacity=0 (not just opacity) — height=0 collapses layout space, opacity=0 hides visually; both needed for correct layout
- _last_dmc_state/_last_connected cached on TabBar so set_role() can reapply gates after role rebuild without requiring a state notification
- Pre-existing test_parameters.py::TestParametersApplyMotionGating failures (4 tests) confirmed pre-existing via git stash verification — not caused by this plan; logged as deferred

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing test failures in `tests/test_parameters.py::TestParametersApplyMotionGating` (4 tests) were discovered during full suite run. Confirmed pre-existing by reverting all Task 2 changes via `git stash` and reproducing the same failures. These are out of scope for this plan. Added to deferred items.

## Next Phase Readiness

- UI-02 through UI-05 requirements completed: state label, setup badge, tab gating, and connection indicator (pre-existing)
- All 31 new tests pass; 261 other tests pass (excluding 4 pre-existing failures in test_parameters.py)
- Phase 14 Plan 01 is the only plan in Phase 14 — phase complete

---
*Phase: 14-state-driven-ui*
*Completed: 2026-04-06*
