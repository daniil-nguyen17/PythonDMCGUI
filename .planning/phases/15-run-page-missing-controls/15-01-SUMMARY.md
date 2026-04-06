---
phase: 15-run-page-missing-controls
plan: 01
subsystem: run-screen
tags: [layout, kivy, tdd, traceability]
dependency_graph:
  requires: [phase-12-run-page-wiring]
  provides: [stone-compensation-card, start-pt-c-readback]
  affects: [src/dmccodegui/ui/run.kv, src/dmccodegui/screens/run.py, .planning/REQUIREMENTS.md, .planning/ROADMAP.md]
tech_stack:
  added: []
  patterns: [kivy-stringproperty-binding, tdd-red-green, background-job-readback]
key_files:
  created: []
  modified:
    - src/dmccodegui/ui/run.kv
    - src/dmccodegui/screens/run.py
    - tests/test_run_screen.py
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
decisions:
  - Stone Compensation card placed in right column below Axis Positions — operator always sees current stone position without needing to scroll or navigate
  - Before-read removed from on_more_stone/on_less_stone — persistent label replaces toast-style before/after alert
  - More Stone uses green theme (0.02/0.12/0.06 bg, 0.133/0.773/0.369 text), Less Stone uses orange theme (0.15/0.08/0.02 bg, 0.984/0.573/0.235 text) matching delta_c_panel buttons
  - RUN-02, RUN-03, RUN-06 re-mapped to Phase 13 — these requirements are satisfied by existing AxesSetupScreen implementation
metrics:
  duration_minutes: 5
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_modified: 5
---

# Phase 15 Plan 01: Stone Compensation Card Layout and Traceability Re-mapping Summary

**One-liner:** Stone Compensation card with green/orange More/Less Stone buttons and persistent startPtC readback label moved from bottom bar into right column, with RUN-02/03/06 re-mapped to Phase 13.

## What Was Built

### Task 1: Stone Compensation Card Layout and startPtC Readback

**run.py changes:**
- Added `start_pt_c = StringProperty("---")` property
- Added `_read_start_pt_c()` method: submits a background job that reads `STARTPT_C` from controller via `MG startPtC`, updates `start_pt_c` with `"Stone Pos: {val:,}"` on success or `"---"` on failure
- Added `self._read_start_pt_c()` call at end of `on_pre_enter` so the label is populated on screen entry
- Refactored `on_more_stone()`: removed "before" read entirely; fires trigger, sleeps 0.4s, reads after to update `start_pt_c` via `setattr`; error `_alert` preserved for trigger failure only
- Refactored `on_less_stone()`: identical changes

**run.kv changes:**
- Removed `more_stone_btn` and `less_stone_btn` from bottom action bar (bottom bar now has only START GRIND + STOP)
- Added Stone Compensation card as third child of right column BoxLayout:
  - `STONE COMPENSATION` section header (11sp, bold)
  - `start_pt_c_label` bound to `root.start_pt_c` (12sp, persistent readback)
  - `more_stone_btn`: green theme (`0.02, 0.12, 0.06, 1` bg / `0.133, 0.773, 0.369, 1` text), `disabled: root.motion_active`
  - `less_stone_btn`: orange theme (`0.15, 0.08, 0.02, 1` bg / `0.984, 0.573, 0.235, 1` text), `disabled: root.motion_active`

**test_run_screen.py changes (TDD):**
- Added 4 new tests: `test_run_screen_has_start_pt_c`, `test_read_start_pt_c_submits_job`, `test_more_stone_updates_start_pt_c`, `test_less_stone_updates_start_pt_c`
- Updated `test_more_stone_reads_startptc_before_and_after` → renamed to `test_more_stone_reads_startptc_after` (now asserts exactly 1 MG call, not 2)

### Task 2: Traceability Re-mapping

**REQUIREMENTS.md:**
- Marked RUN-02, RUN-03, RUN-06 as complete (`[ ]` → `[x]`)
- Updated traceability table: all three now show `Phase 13 | Complete`

**ROADMAP.md:**
- Phase 15 requirements note updated to reflect layout-only scope
- Plan 15-01 marked as complete (`[ ]` → `[x]`)
- Phase 13 requirements line extended to include RUN-02, RUN-03, RUN-06

## Deviations from Plan

**1. [Rule 1 - Bug] Updated test_more_stone_reads_startptc_before_and_after to match new behavior**
- **Found during:** Task 1 implementation (GREEN phase)
- **Issue:** Existing test expected 2 MG calls (before + after); new implementation only does 1 (after only), so the test failed after refactor
- **Fix:** Renamed test to `test_more_stone_reads_startptc_after`, updated assertion to `len(mg_calls) == 1`, updated side_effect sequence to remove before-read value
- **Files modified:** tests/test_run_screen.py
- **Commit:** 4ae8560

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 4ae8560 | feat | Stone Compensation card with persistent startPtC readback (Task 1) |
| a9c6433 | chore | Re-map RUN-02, RUN-03, RUN-06 traceability to Phase 13 (Task 2) |

## Verification Results

- `python -m pytest tests/test_run_screen.py -x -q`: 27 passed (4 new + existing)
- `python -m pytest tests/ -x -q`: 301 passed (0 failures, 0 regressions)
- `grep "STONE COMPENSATION" src/dmccodegui/ui/run.kv`: 1 match (card exists)
- `grep "start_pt_c" src/dmccodegui/screens/run.py`: property, method, and on_pre_enter call all present
- `grep "RUN-02 | Phase 13 | Complete" .planning/REQUIREMENTS.md`: 1 match
- Bottom action bar: only `start_grind_btn` and `stop_btn` remain

## Self-Check: PASSED

All files found on disk. Both commits verified in git log. 301 tests pass.
