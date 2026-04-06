---
phase: 04-axes-setup-and-parameters
plan: 01
subsystem: ui
tags: [kivy, galil, dmccode, axes, jog, position, teach, polling]

# Dependency graph
requires:
  - phase: 01-auth-and-navigation
    provides: MachineState with setup_unlocked, cycle_running, and role checks
  - phase: 02-run-page
    provides: jobs.submit/schedule background thread pattern
provides:
  - AxesSetupScreen with sidebar, jog, teach, polling, quick actions
  - AXIS_CPM_DEFAULTS dict (A/B/C/D counts-per-mm constants)
  - 16 unit tests covering jog math, teach sequences, polling lifecycle
affects:
  - 04-02 (parameters setup — shares screen injection and jobs pattern)
  - 04-03 (axis angles — same axis labeling conventions)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - PR{axis}={counts} + BG{axis} for relative jog (not PA)
    - Read all 4 TD positions then write semicolon-separated scalar DMC vars + BV for teach
    - swGoRest=1 / swGoStart=1 / swHomeAll=1 software variable command pattern for quick actions
    - Clock.schedule_interval at 3 Hz for position polling; cancelled in on_leave
    - jobs.submit() for all controller I/O; Clock.schedule_once() to post results back to UI

key-files:
  created:
    - src/dmccodegui/screens/axes_setup.py
    - tests/test_axes_setup.py
  modified:
    - src/dmccodegui/ui/axes_setup.kv

key-decisions:
  - "jog_axis uses PR+BG (position relative) per axis — locked decision, never PA"
  - "Teach captures all 4 axes at once into scalar DMC vars (restPtA/B/C/D, startPtA/B/C/D) + BV burn — no download_array"
  - "Quick action variable names swGoRest/swGoStart/swHomeAll are best-guess — confirmed at integration time"
  - "AXIS_CPM_DEFAULTS: A=1200, B=1200, C=800, D=500 — read live from controller on enter, fall back to defaults"

patterns-established:
  - "Axis accent colors: A=orange, B=purple, C=cyan, D=yellow — consistent across all axis-related UI"
  - "Step toggles (10/5/1) in 'step_sel' group with step_10 state=down by default"
  - "Sidebar axis selector in 'axis_sel' group with A state=down by default"

requirements-completed: [AXES-01, AXES-02, AXES-03, AXES-04, AXES-05, AXES-06]

# Metrics
duration: 20min
completed: 2026-04-04
---

# Phase 4 Plan 01: Axes Setup Screen Summary

**AxesSetupScreen with 4-axis sidebar, CPM-based mm-to-counts jog, all-4-axis teach+BV burn, 3 Hz polling, and quick-action software variable commands**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-04-04T10:50:15Z
- **Completed:** 2026-04-04T11:10:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Full AxesSetupScreen replacing the placeholder — sidebar with A/B/C/D axis ToggleButtons + 3 quick-action buttons, position cards (Rest/Start/Current), jog arrow controls with 10/5/1 step toggles, and Teach buttons
- CPM-based mm-to-counts jog math: `counts = int(direction * step_mm * cpm)` using PR{axis}+BG{axis} per axis
- All-4-axis teach operation that reads `MG _TDA/B/C/D`, writes `restPtA/B/C/D` (or `startPtA/B/C/D`) in one semicolon-separated command, and sends BV to burn NV memory
- 3 Hz position polling via `Clock.schedule_interval` with proper on_pre_enter start / on_leave cancel lifecycle
- 16 unit tests covering all requirements: jog math, guard conditions, teach sequences, quick actions, polling lifecycle

## Task Commits

Each task was committed atomically:

1. **Task 1: AxesSetupScreen Python class with jog, teach, polling, quick actions + tests** - `586f867` (feat)
2. **Task 2: AxesSetupScreen KV layout** - `10fc33a` (feat)

## Files Created/Modified

- `src/dmccodegui/screens/axes_setup.py` — AxesSetupScreen class replacing placeholder; exports AXIS_CPM_DEFAULTS
- `src/dmccodegui/ui/axes_setup.kv` — Full KV layout: sidebar, position cards, jog controls, teach buttons
- `tests/test_axes_setup.py` — 16 unit tests (TDD: written first, then implementation made them pass)

## Decisions Made

- **PR+BG for jog** — Uses PR (position relative) then BG per axis to move only the selected axis. PA was explicitly ruled out per locked project decisions.
- **Teach writes scalars, not arrays** — Each `restPtA/B/C/D` and `startPtA/B/C/D` is an individual DMC scalar variable, written via a single semicolon-separated command. No `download_array()` per locked decision.
- **Quick action variable names** — `swGoRest=1`, `swGoStart=1`, `swHomeAll=1` are best-guess names from CONTEXT.md research; actual DMC variable names will be confirmed at controller integration time.
- **AXIS_CPM_DEFAULTS** — A=1200, B=1200, C=800, D=500 counts/mm seeded as defaults; read from controller via `MG cpm{axis}` on screen enter and cached in `_axis_cpm`.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- AxesSetupScreen is complete and loadable; ready for wiring in main.py alongside the ParametersScreen (Plan 04-02)
- Quick action variable names (`swGoRest`, `swGoStart`, `swHomeAll`) will need confirmation against the actual DMC controller program at integration
- RestPnt → DAxisPnt rename (flagged in STATE.md blockers) is NOT required for this screen — it uses new scalar variables, not the old arrays

---
*Phase: 04-axes-setup-and-parameters*
*Completed: 2026-04-04*

## Self-Check: PASSED

- FOUND: src/dmccodegui/screens/axes_setup.py
- FOUND: src/dmccodegui/ui/axes_setup.kv
- FOUND: tests/test_axes_setup.py
- FOUND: .planning/phases/04-axes-setup-and-parameters/04-01-SUMMARY.md
- FOUND: commit 586f867 (Task 1)
- FOUND: commit 10fc33a (Task 2)
