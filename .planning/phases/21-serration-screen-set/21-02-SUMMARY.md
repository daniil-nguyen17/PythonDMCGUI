---
phase: 21-serration-screen-set
plan: 02
subsystem: screens/serration
tags: [serration, run-screen, bcomp, widgets, kv, tests]
dependency_graph:
  requires:
    - 21-01
    - phase-18-base-class-extraction
    - phase-19-flat-grind-rename
  provides:
    - SerrationRunScreen full implementation
    - BCompPanel scrollable editable list widget
    - ui/serration/run.kv complete layout
    - 18 total serration tests passing
  affects:
    - src/dmccodegui/screens/serration/run.py (stub replaced with full implementation)
    - src/dmccodegui/screens/serration/widgets.py (skeleton replaced with full widget)
    - src/dmccodegui/ui/serration/run.kv (stub replaced with full layout)
    - tests/test_serration_screens.py (8 new tests added)
tech_stack:
  added: []
  patterns:
    - BCompPanel as BoxLayout with GridLayout(cols=3) scrollable rows — not a bar chart
    - Individual element bComp write pattern — mirrors deltaC write in FlatGrindRunScreen
    - submit()/submit_urgent() + Clock.schedule_once() for all controller I/O
    - All lifecycle hooks in Python only (per Kivy #2565)
    - MG reader thread with Event-based stop, daemon=True
    - Busy guard on position poll to prevent job queue pileup
key_files:
  created: []
  modified:
    - src/dmccodegui/screens/serration/run.py
    - src/dmccodegui/screens/serration/widgets.py
    - src/dmccodegui/ui/serration/run.kv
    - tests/test_serration_screens.py
decisions:
  - "BCompPanel is a scrollable BoxLayout/GridLayout list — not a bar chart (user decision, critical note in plan)"
  - "D-axis completely absent from SerrationRunScreen — no pos_d property, no D-axis KV row"
  - "No matplotlib in serration/run.py — plot stub is a Label placeholder in a BoxLayout"
  - "bComp writes use individual element commands: bComp[i]=value (same pattern as deltaC)"
  - "BCompPanel wired in on_pre_enter via self.ids.get('bcomp_panel') — not in KV lifecycle"
  - "Position poll reads MG _TPA, _TPB, _TPC (3 axes only, no _TPD)"
metrics:
  duration_seconds: 480
  completed_date: "2026-04-13"
  tasks_completed: 2
  tasks_total: 2
  files_created: 0
  files_modified: 4
  tests_added: 8
  tests_passing: 18
---

# Phase 21 Plan 02: Serration Run Screen Implementation Summary

Full SerrationRunScreen with functional bComp scrollable list (read/write/validation), 3-axis position display, cycle controls, more/less stone, plot stub, and complete KV layout — 18 tests all passing.

## What Was Built

### Task 1: BCompPanel widget and SerrationRunScreen

**`src/dmccodegui/screens/serration/widgets.py`** — BCompPanel full implementation replacing Plan 01 skeleton:

- `BoxLayout(orientation='vertical')` with header area and scrollable body
- Header: title label (cyan accent, bound to num_serrations) + "Doc bComp" refresh button
- Body: `ScrollView` containing `GridLayout(cols=3, size_hint_y=None)` with `bind(minimum_height=...)`
- Each row: index `Label` + `TextInput(input_filter='float', multiline=False)` + "Luu" `Button`
- Row height: `dp(44)` for each cell
- `build_rows(values)` — clears grid, rebuilds from values list, sets `num_serrations = len(values)`
- `_on_save(index, text)` — validates against BCOMP_MIN_MM / BCOMP_MAX_MM, calls `save_callback` or flashes red
- `save_callback` and `refresh_callback` — set by SerrationRunScreen on screen entry
- Constants: `BCOMP_MIN_MM = -5.0`, `BCOMP_MAX_MM = 5.0`, `BCOMP_ARRAY_VAR`, `BCOMP_NUM_SERR_VAR`

**`src/dmccodegui/screens/serration/run.py`** — Full SerrationRunScreen replacing stub:

- Kivy properties: `pos_a`, `pos_b`, `pos_c` (no `pos_d`), `cycle_running`, `motion_active`, `start_pt_c`, `num_serr`, `num_serr_str`, `session_knife_count`, `stone_knife_count`, `disconnect_banner`, `mg_log_text`
- `_read_bcomp()` — background job: reads `numSerr`, then reads `bComp[0]` through `bComp[n-1]` individually; updates panel on main thread via `Clock.schedule_once`
- `_write_bcomp_element(index, value_mm)` — background job: sends `bComp[{index}]={value_mm:.4f}` to controller
- `_tick_pos()` — 5 Hz clock: reads `MG _TPA, _TPB, _TPC` (3 axes) + hmiState/knife counts in 2 round-trips; busy guard prevents queue pileup
- `on_start_grind()`, `on_stop()`, `on_more_stone()`, `on_less_stone()` — cycle controls using HMI one-shot trigger pattern
- `_on_state_change()` / `_apply_state()` — updates A/B/C positions, cycle status, disconnect banner
- `on_pre_enter()` — stops centralized poller, starts position poll, reads startPtC, wires bComp panel callbacks, auto-reads bComp, starts MG reader
- `on_leave()` — stops position poll, MG reader, restarts centralized poller, calls `super().on_leave()`
- MG reader thread: daemon=True, Event-based stop, 100ms poll interval

### Task 2: Serration run.kv and complete test coverage

**`src/dmccodegui/ui/serration/run.kv`** — Complete Serration run screen layout:

- `<SerrationRunScreen>:` rule (no KV collision with FlatGrindRunScreen)
- `#:import BCompPanel dmccodegui.screens.serration.widgets.BCompPanel`
- Left column: 3-axis position rows (A=orange, B=purple, C=cyan), plot stub (`id: plot_stub`, Label "Plot: pending hardware data"), `BCompPanel` (`id: bcomp_panel`), grind progress panel
- Right column: controller log (ScrollView + MG log label), stone compensation panel with `start_pt_c` label + less/more stone buttons
- Bottom action bar: "BAT DAU MAI" start button + "STOP" button (opacity-gated on motion_active)
- No `pos_d`, no `MatplotFigure`, no `DeltaCBarChart`

**`tests/test_serration_screens.py`** — Added 8 new tests (11-18):

11. `test_serration_run_screen_no_d_axis` — pos_d not in properties, pos_a/b/c are present
12. `test_serration_run_screen_has_bcomp_methods` — _read_bcomp and _write_bcomp_element callable
13. `test_serration_run_screen_no_matplotlib` — source file has no import matplotlib lines
14. `test_bcomp_panel_renders_rows` — build_rows([0.1, 0.2, 0.3]) sets num_serrations == 3
15. `test_bcomp_panel_validation` — BCOMP_MIN_MM < 0 < BCOMP_MAX_MM, both float
16. `test_serration_run_kv_no_d_axis` — run.kv text does not contain 'pos_d'
17. `test_serration_run_kv_no_matplotlib` — run.kv text does not contain 'MatplotFigure'
18. `test_serration_run_kv_has_bcomp` — run.kv text contains 'bcomp_panel'

## Verification

```
pytest tests/test_serration_screens.py -x -v
# 18 passed in 1.21s

pytest tests/test_flat_grind_widgets.py::test_no_duplicate_kv_rule_headers -x
# 1 passed (no KV rule name collisions)

pytest tests/ -x
# 205 passed, 1 pre-existing failure (test_main_estop, unrelated to Phase 21)

python -c "from dmccodegui.screens.serration import SerrationRunScreen; print(hasattr(SerrationRunScreen, 'pos_d'))"
# False

python -c "from dmccodegui.screens.serration.widgets import BCompPanel; p = BCompPanel(); p.build_rows([1.0, 2.0]); print(p.num_serrations)"
# 2
```

## Commits

| Hash | Message |
|------|---------|
| dde4a11 | feat(21-02): implement BCompPanel widget and SerrationRunScreen |
| 38428da | feat(21-02): create serration run.kv and add 8 Plan 02 tests |

## Deviations from Plan

None — plan executed exactly as written.

- D-axis completely absent as specified
- No matplotlib imports in serration/run.py
- BCompPanel is a list widget (not bar chart) as specified in critical note
- All controller I/O via submit()/Clock.schedule_once() as required by gclib comms architecture

## Self-Check

Modified files exist:
- src/dmccodegui/screens/serration/run.py — FOUND
- src/dmccodegui/screens/serration/widgets.py — FOUND
- src/dmccodegui/ui/serration/run.kv — FOUND
- tests/test_serration_screens.py — FOUND

Commits exist:
- dde4a11 — FOUND
- 38428da — FOUND

## Self-Check: PASSED
