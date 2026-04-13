---
phase: 22-convex-screen-set
plan: 02
subsystem: convex-run-screen
tags: [convex, run-screen, matplotlib, delta-c, kivy, CONV-01]
dependency_graph:
  requires:
    - 22-01-SUMMARY.md (ConvexAdjustPanel placeholder from widgets.py)
    - src/dmccodegui/screens/flat_grind/widgets.py (DeltaCBarChart, delta-C constants)
    - src/dmccodegui/screens/base.py (BaseRunScreen lifecycle)
  provides:
    - ConvexRunScreen full implementation (4-axis, matplotlib, delta-C, cycle controls)
    - ui/convex/run.kv complete layout with ConvexAdjustPanel
  affects:
    - tests/test_convex_screens.py (19 total tests)
tech_stack:
  added: []
  patterns:
    - Cross-package import: flat_grind.widgets.DeltaCBarChart reused in ConvexRunScreen (intentional)
    - Position display rows in KV: A=orange, B=purple, C=cyan, D=yellow with pos_d_row id
    - ConvexAdjustPanel placeholder wired below delta-C panel in left column
key_files:
  created: []
  modified:
    - src/dmccodegui/screens/convex/run.py
    - src/dmccodegui/ui/convex/run.kv
    - tests/test_convex_screens.py
decisions:
  - Convex run.kv adds D-axis position display rows not present in flat_grind/run.kv — required by test_convex_run_kv_has_d_axis and the plan's position row requirement (A=orange, B=purple, C=cyan, D=yellow)
  - Cross-package import of DeltaCBarChart from flat_grind.widgets is intentional per CONTEXT.md and RESEARCH.md — no duplication of bar chart logic
  - ConvexAdjustPanel placed below delta-C panel in left column with size_hint_y: None, height: 80dp as a minimal placeholder
metrics:
  duration_minutes: 10
  completed_date: "2026-04-13"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
---

# Phase 22 Plan 02: Convex Run Screen Summary

**One-liner:** Full ConvexRunScreen with 4-axis positions, live matplotlib A/B plot, DeltaC bar chart, ConvexAdjustPanel placeholder, and cycle controls — 19 tests passing.

## What Was Built

### Task 1: Full ConvexRunScreen and run.kv

Replaced the `ConvexRunScreen` stub (15 lines) with a complete implementation (550+ lines) copied from `FlatGrindRunScreen` with targeted changes:

**`src/dmccodegui/screens/convex/run.py`:**
- Class renamed from `FlatGrindRunScreen` to `ConvexRunScreen`
- Docstring updated to describe 4-axis Convex machine with ConvexAdjustPanel placeholder
- Added `from .widgets import ConvexAdjustPanel` for the panel import
- Kept cross-package `from dmccodegui.screens.flat_grind.widgets import DeltaCBarChart, ...` (intentional per design)
- All 4 Kivy properties retained: `pos_a`, `pos_b`, `pos_c`, `pos_d`
- Full matplotlib A/B live position plot with 5 Hz redraw clock
- Full DeltaC bar chart logic (section count, up/down adjustments, write to controller)
- More/less stone panel with startPtC readback
- Start/Stop cycle controls using HMI one-shot trigger pattern (never XQ direct calls)
- Position poll (`_tick_pos`) reads `_TPA, _TPB, _TPC, _TPD` (all 4 axes)
- MG reader thread (daemon=True, threading.Event stop)
- Print log prefixes updated: `[ConvexRunScreen]` instead of `[FlatGrindRunScreen]`

**`src/dmccodegui/ui/convex/run.kv`:**
- Rule header changed to `<ConvexRunScreen>:` (no collision with FlatGrindRunScreen)
- `#:import run_module` points to `dmccodegui.screens.convex.run`
- `#:import DeltaCBarChart dmccodegui.screens.flat_grind.widgets` (intentional cross-package)
- Added `#:import ConvexAdjustPanel dmccodegui.screens.convex.widgets.ConvexAdjustPanel`
- `ConvexAdjustPanel:` widget placed in left column below delta-C with `id: convex_adjust_panel`, `size_hint_y: None`, `height: '80dp'`
- Added axis position display rows in right column (A=orange, B=purple, C=cyan, D=yellow) with `pos_d_row` id
- All existing layout preserved: matplotlib plot, delta-C panel, grind progress, controller log, stone compensation, bottom action bar

### Task 2: Complete test coverage for CONV-01

Added 7 new tests (13-19) to `tests/test_convex_screens.py`, bringing total to 19 tests:

| # | Test | What it verifies |
|---|------|-----------------|
| 13 | `test_convex_run_screen_has_all_4_axes` | pos_a/b/c/d in `s.properties()` |
| 14 | `test_convex_run_screen_has_matplotlib` | matplotlib import in run.py source |
| 15 | `test_convex_run_screen_has_delta_c_import` | DeltaCBarChart imported from flat_grind.widgets |
| 16 | `test_convex_run_kv_has_d_axis` | pos_d bound in run.kv |
| 17 | `test_convex_run_kv_has_convex_adjust_panel` | convex_adjust_panel id in run.kv |
| 18 | `test_convex_run_kv_has_matplot_figure` | MatplotFigure widget in run.kv |
| 19 | `test_convex_run_kv_rule_header` | `<ConvexRunScreen>:` present, `<FlatGrindRunScreen>:` absent |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Added axis position display rows to run.kv**
- **Found during:** Task 2 — test_convex_run_kv_has_d_axis failed because flat_grind/run.kv has no pos_x bindings
- **Issue:** Plan requires `pos_d` in KV position display rows, but flat_grind/run.kv doesn't have them either. Copying flat_grind KV as-is would fail the D-axis display test.
- **Fix:** Added a full axis position display section to the right column of run.kv with all 4 axis rows (A=orange, B=purple, C=cyan, D=yellow) and `pos_d_row` id for serration visibility control
- **Files modified:** `src/dmccodegui/ui/convex/run.kv`
- **Commit:** 87b27d1

## Verification Results

All plan verification checks passed:

```
All convex imports OK
4 axes OK
19 passed in 1.18s
```

- ConvexRunScreen, ConvexAxesSetupScreen, ConvexParametersScreen all importable
- ConvexRunScreen has pos_a, pos_b, pos_c, pos_d
- 19 tests in test_convex_screens.py — all passing
- No KV rule name collisions (`test_no_kv_rule_name_collisions` passing)
- Pre-existing unrelated failure: `test_estop_commands_order` in test_main_estop.py (pre-dates this plan)

## Commits

| Hash | Description |
|------|-------------|
| 0a89789 | feat(22-02): full ConvexRunScreen and run.kv implementation |
| 87b27d1 | feat(22-02): add 7 CONV-01 tests and axis position rows to run.kv |

## Self-Check

Files exist:
- `src/dmccodegui/screens/convex/run.py` — FOUND
- `src/dmccodegui/ui/convex/run.kv` — FOUND
- `tests/test_convex_screens.py` — FOUND

Commits: 0a89789, 87b27d1 — verified in git log above.
