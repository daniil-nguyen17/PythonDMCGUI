---
phase: 02-run-page
plan: "02"
subsystem: run-screen
tags: [kivy, canvas, widget, delta-c, bar-chart, touch]
dependency_graph:
  requires: [02-01]
  provides: [DeltaCBarChart-widget, KnifeGrindAdjustmentPanel]
  affects: [02-03]
tech_stack:
  added: []
  patterns: [canvas-instructions-draw, ListProperty-reactive-redraw, on_kv_post-binding, Widget-touch-selection]
key_files:
  created: []
  modified:
    - src/dmccodegui/screens/run.py
    - src/dmccodegui/ui/run.kv
decisions:
  - "DELTA_C_STEP updated from placeholder 10.0 to plan-specified 50 (int) — button labels show '- 50' / '+ 50'"
  - "delta_c_offsets promoted from plain list to ListProperty([0.0]) so KV bindings and canvas redraws fire correctly"
  - "DeltaCBarChart._draw() uses canvas.clear() + with self.canvas: pattern (not canvas.before) to allow full redraw on every property change"
  - "run_module import in KV (#:import run_module dmccodegui.screens.run) used for live DELTA_C_STEP on button text — no hardcoding"
metrics:
  duration_s: 159
  completed_date: "2026-04-04"
  tasks_completed: 2
  files_modified: 2
---

# Phase 2 Plan 02: Knife Grind Adjustment Panel Summary

**One-liner:** Custom DeltaCBarChart canvas widget with touch-selectable bars, per-section offset adjustment via +/-50 buttons, and batch Apply to controller deltaC array — wired into run.kv as a live 220dp panel.

## Tasks Completed

| # | Task | Commit | Key files |
|---|------|--------|-----------|
| 1 | Create DeltaCBarChart widget and adjustment logic in run.py | 1ec7998 | screens/run.py |
| 2 | Wire Knife Grind Adjustment panel into run.kv | be0f823 | ui/run.kv |

## What Was Built

### DeltaCBarChart widget (screens/run.py)

A `Widget` subclass that renders per-section deltaC offsets using Kivy canvas instructions:

- **Properties:** `offsets = ListProperty([])`, `selected_index = NumericProperty(-1)`, `max_offset = NumericProperty(500)`
- **Reactive triggers:** `on_offsets`, `on_selected_index`, `on_size`, `on_pos` all call `_draw()`
- **`_draw()`:** Clears canvas, draws grey zero-baseline (1px Rectangle), then for each section draws a bar proportional to `abs(offset) / max_offset * half_height` (minimum 2px). Positive offsets extend above mid_y, negative below. Selected bar is orange `(1.0, 0.65, 0.0)`, others blue `(0.235, 0.510, 0.960)`.
- **`on_touch_down()`:** Collide-checks, computes bar index from `(touch.x - self.x) / bar_w`, clamps to `[0, n-1]`, sets `selected_index`

### RunScreen additions (screens/run.py)

New Kivy properties:
- `delta_c_offsets = ListProperty([0.0])` — promoted from plain list
- `selected_section_value = StringProperty("0")` — live display in 'Selected: X cts' label

New methods:
- **`on_kv_post()`:** Binds `_on_chart_selection_changed` to `delta_c_chart.selected_index` after KV ids are assigned
- **`_on_chart_selection_changed(chart, idx)`:** Updates `selected_section_value` when bar is tapped or selection cleared
- **`on_adjust_up()`:** Reads `chart.selected_index`, adds `DELTA_C_STEP` to that offset, reassigns list, updates display label
- **`on_adjust_down()`:** Same but subtracts
- **`on_apply_delta_c()`:** Calls `_offsets_to_delta_c()`, submits `controller.download_array("deltaC", DELTA_C_WRITABLE_START, values)` on background thread

Updated:
- `DELTA_C_STEP` changed from `10.0` to `50` (int, per plan spec)

### Knife Grind Adjustment panel (ui/run.kv)

Replaced the 220dp placeholder with a full vertical layout:
- **Header row (28dp):** `KNIFE GRIND ADJUSTMENT` title label + `Sections:` label + `-` button + count label + `+` button
- **DeltaCBarChart (110dp):** `id: delta_c_chart`, `offsets: root.delta_c_offsets`
- **Controls row (40dp):** `Selected: X cts` label, `- 50` / `+ 50` buttons (with live DELTA_C_STEP from `run_module` import), `APPLY` button
- Added `#:import DeltaCBarChart dmccodegui.screens.run` and `#:import run_module dmccodegui.screens.run` at top of file

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written, with one minor adjustment: the KV import uses `#:import run_module dmccodegui.screens.run` (as the plan recommended as first choice) and it worked without issues.

## Verification

- `python -c "... assert DELTA_C_STEP == 50; print('Constants OK')"` — PASSED
- `pytest tests/test_delta_c_bar_chart.py -x -q` — 5 passed
- `python -c "Builder.load_file('src/dmccodegui/ui/run.kv'); print('run.kv loaded OK')"` — PASSED
- `pytest tests/ -x -q` — 41 passed, 0 failed

## Self-Check: PASSED

Files verified to exist:
- `src/dmccodegui/screens/run.py` — FOUND (contains DeltaCBarChart, on_kv_post, on_adjust_up, on_adjust_down, on_apply_delta_c)
- `src/dmccodegui/ui/run.kv` — FOUND (contains DeltaCBarChart id: delta_c_chart, adjustment panel)

Commits verified:
- `1ec7998` — FOUND (feat(02-02): implement DeltaCBarChart widget and adjustment logic)
- `be0f823` — FOUND (feat(02-02): wire Knife Grind Adjustment panel into run.kv)
