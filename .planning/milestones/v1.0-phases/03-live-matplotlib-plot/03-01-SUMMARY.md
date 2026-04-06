---
phase: 03-live-matplotlib-plot
plan: 01
subsystem: ui
tags: [matplotlib, kivy, kivy-matplotlib-widget, live-plot, deque, clock]

# Dependency graph
requires:
  - phase: 02-run-page
    provides: "RunScreen with _apply_ui, on_start_pause_toggle, on_pre_enter/on_leave lifecycle hooks, DeltaCBarChart widget already in layout"
provides:
  - "PLOT_UPDATE_HZ=5 and PLOT_BUFFER_SIZE=750 module constants"
  - "RunScreen._plot_buf_x/_plot_buf_y rolling deques (maxlen=750)"
  - "RunScreen._tick_plot() 5 Hz Kivy clock redraw using draw_idle"
  - "RunScreen._configure_plot_axes() dark-theme axis styling with equal aspect ratio"
  - "MatplotFigure widget (id: ab_plot) replacing placeholder Label in run.kv"
  - "5 RUN-07 tests in test_run_screen.py (12 total all passing)"
affects: [03-live-matplotlib-plot future plans, phase 5 CSV, any run-page changes]

# Tech tracking
tech-stack:
  added: [kivy_matplotlib_widget, matplotlib.figure.Figure, matplotlib.ticker.MaxNLocator, collections.deque]
  patterns:
    - "Figure + fig.add_subplot(111) directly — never pyplot/plt.subplots()"
    - "draw_idle() for async non-blocking redraws — never blocking draw()"
    - "Separate 5 Hz plot clock from 10 Hz poll clock to protect E-STOP latency"
    - "Touch disabled on MatplotFigure (do_pan_x/y=False, do_scale=False, touch_mode='none')"
    - "Buffer appends only in _apply_ui when cycle_running is True — saves Pi CPU at idle"
    - "Trail cleared synchronously before cycle start in on_start_pause_toggle"

key-files:
  created: []
  modified:
    - src/dmccodegui/screens/run.py
    - src/dmccodegui/ui/run.kv
    - tests/test_run_screen.py

key-decisions:
  - "kivy_matplotlib_widget 0.16.0 used for MatplotFigure — registered in Kivy Factory via import"
  - "deque(maxlen=750) chosen as rolling buffer — old points auto-evicted, O(1) append"
  - "5 Hz plot clock separate from 10 Hz poll clock — avoids plot redraw blocking controller poll"
  - "draw_idle() used for all matplotlib redraws — async, does not block Kivy event loop"
  - "Touch interaction fully disabled on MatplotFigure — preserves E-STOP button responsiveness"
  - "equal aspect ratio (adjustable=datalim) preserves geometric accuracy of grinding path"

patterns-established:
  - "Matplotlib integration: Figure/Axes only, no pyplot globals, no backend_kivyagg"
  - "Plot lifecycle: init in on_kv_post, clock start in on_pre_enter, clock cancel in on_leave"
  - "Buffer guard: cycle_running check in _apply_ui before appending to deques"

requirements-completed: [RUN-07]

# Metrics
duration: 3min
completed: 2026-04-04
---

# Phase 03 Plan 01: Live A/B Position Plot Summary

**MatplotFigure widget embedded in RUN page left column, feeding A/B positions into a deque(maxlen=750) at 10 Hz and redrawing the trail at 5 Hz on a separate Kivy clock with all touch interaction disabled**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-04T09:43:35Z
- **Completed:** 2026-04-04T09:46:25Z
- **Tasks:** 2 (TDD: RED test scaffold + GREEN implementation)
- **Files modified:** 3

## Accomplishments

- Replaced placeholder Label with kivy_matplotlib_widget MatplotFigure (id: ab_plot) in run.kv
- Added rolling deque buffers (_plot_buf_x/_plot_buf_y, maxlen=750) populated during active cycles only
- Implemented 5 Hz _tick_plot clock (separate from 10 Hz poll) using draw_idle for async redraws
- Trail clears synchronously on cycle Start before background job submission
- All touch interaction disabled on plot widget to preserve E-STOP responsiveness
- Equal aspect ratio ensures grinding path is geometrically accurate on screen
- 5 new RUN-07 tests covering constants, buffer structure, idle guard, and trail clear behavior

## Task Commits

Each task was committed atomically:

1. **Task 1: Add RUN-07 test scaffolds** - `da062c0` (test)
2. **Task 2: Implement MatplotFigure widget, rolling buffer, 5 Hz redraw** - `e01aa45` (feat)

_Note: TDD — Task 1 was RED (5 failing tests), Task 2 was GREEN (all 12 tests pass)_

## Files Created/Modified

- `tests/test_run_screen.py` - Added 5 RUN-07 tests (12 total, all passing)
- `src/dmccodegui/screens/run.py` - Added imports (deque, Figure, MaxNLocator, kivy_matplotlib_widget), PLOT_UPDATE_HZ/PLOT_BUFFER_SIZE/color constants, __init__ for deque init, _configure_plot_axes(), _tick_plot(), extended on_kv_post/on_pre_enter/on_leave/_apply_ui/on_start_pause_toggle
- `src/dmccodegui/ui/run.kv` - Added kivy_matplotlib_widget import, replaced placeholder BoxLayout+Label with BoxLayout+MatplotFigure (id: ab_plot)

## Decisions Made

- Used `Figure() + fig.add_subplot(111)` directly — no pyplot globals (thread-safety and no shared state)
- Chose `deque(maxlen=750)` — old points auto-evicted without explicit management
- Kept plot clock at 5 Hz separate from 10 Hz poll — decoupling protects E-STOP button latency
- `draw_idle()` over `draw()` — queues the redraw without blocking the Kivy event loop
- Touch mode set to 'none' on MatplotFigure — kivy-matplotlib-widget can intercept touch events that would otherwise block E-STOP tap

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — implementation matched plan spec precisely. The "Start cycle error" logged during tests is the expected silent failure when controller is None (test environment).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RUN-07 fully implemented: live A/B line trail renders during active cycles
- Plot widget present on RUN page, wired to the existing poll loop
- Pi performance benchmarking still flagged as a concern (see STATE.md blockers) — `draw_idle()` should be sufficient but blit animation remains as a fallback option if CPU load is too high on hardware

---
*Phase: 03-live-matplotlib-plot*
*Completed: 2026-04-04*
