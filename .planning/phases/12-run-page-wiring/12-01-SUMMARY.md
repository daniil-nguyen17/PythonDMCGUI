---
phase: 12-run-page-wiring
plan: "01"
subsystem: run-screen
tags: [hmi-triggers, one-shot-pattern, kivy, run-screen]
dependency_graph:
  requires: [phase-11-e-stop-safety]
  provides: [on_start_grind, on_more_stone, on_less_stone]
  affects: [src/dmccodegui/screens/run.py, src/dmccodegui/ui/run.kv]
tech_stack:
  added: []
  patterns: [HMI one-shot trigger pattern, jobs.submit background worker]
key_files:
  created: []
  modified:
    - src/dmccodegui/screens/run.py
    - src/dmccodegui/ui/run.kv
    - tests/test_run_screen.py
decisions:
  - "Buffer clear happens after connection guard — only clears when controller is connected and cycle will actually start"
  - "test_trail_clears_on_start updated to use on_start_grind (old toggle removed per plan)"
  - "on_less_stone mirrors on_more_stone exactly except uses HMI_LESS and 'Stone -:' prefix"
metrics:
  duration_minutes: 3
  completed_date: "2026-04-06"
  tasks_completed: 3
  files_modified: 3
---

# Phase 12 Plan 01: Run Page Wiring Summary

**One-liner:** Replaced XQ-based Start/Pause toggle and Go To Rest with HMI one-shot triggers (hmiGrnd, hmiMore, hmiLess=0) via jobs.submit, with startPtC read-fire-read readback pattern for More/Less Stone.

## What Was Built

Three new RunScreen callbacks wired to real DMC subroutines via the HMI one-shot trigger pattern, replacing legacy XQ direct calls. The KV layout was updated to match: ToggleButton replaced with plain START GRIND Button, Go To Rest removed, More Stone and Less Stone added.

**Callbacks added:**
- `on_start_grind()` — sends `hmiGrnd=0` via `jobs.submit`, clears A/B plot buffers for fresh cycle view
- `on_more_stone()` — reads `startPtC` before, sends `hmiMore=0`, sleeps 400ms, reads `startPtC` after, posts before/after alert
- `on_less_stone()` — mirror of on_more_stone using `hmiLess=0`, prefixed "Stone -:"

**Callbacks removed:**
- `on_start_pause_toggle()` — had XQ #CYCLE and HX direct calls
- `on_go_to_rest()` — had XQ #REST direct call

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 0 | Wave 0 — write failing test stubs | 57a6438 | tests/test_run_screen.py |
| 1 | Replace Python callbacks with HMI one-shot triggers | 36de196 | src/dmccodegui/screens/run.py, tests/test_run_screen.py |
| 2 | Update KV layout — replace ToggleButton, remove Go To Rest, add More/Less Stone | 1a7b6f4 | src/dmccodegui/ui/run.kv |

## Verification Results

1. `python -m pytest tests/test_run_screen.py -x -v` — 23 passed (18 existing + 5 new)
2. `python -m pytest tests/ -x` — 239 passed
3. `grep -n "XQ" src/dmccodegui/screens/run.py` — no matches (comment text only, no calls)
4. Old references check — no `on_start_pause_toggle`, `on_go_to_rest`, `start_pause_btn`, `go_to_rest_btn`
5. All 4 HMI constants imported: `HMI_GRND`, `HMI_MORE`, `HMI_LESS`, `STARTPT_C`
6. No raw string literals (`"hmiGrnd"`, etc.) in run.py

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_trail_clears_on_start called removed method**
- **Found during:** Task 1 implementation
- **Issue:** Existing test `test_trail_clears_on_start` called `r.on_start_pause_toggle("down")` which was deleted per plan scope. Test failed with AttributeError.
- **Fix:** Updated test body to call `r.on_start_grind()` with a connected mock controller (buffer clear only fires after connection guard passes). Added mock controller setup to both `test_trail_clears_on_start` and `test_start_grind_clears_plot_buffers`.
- **Files modified:** tests/test_run_screen.py
- **Commit:** 36de196

## Decisions Made

- Buffer clear happens after the connection guard in `on_start_grind` — semantically correct since there's no point clearing if the cycle won't actually start.
- `on_less_stone` is a direct mirror of `on_more_stone` (no shared helper) for readability and isolation.

## Self-Check: PASSED

- `src/dmccodegui/screens/run.py` — exists and contains all 3 new methods
- `src/dmccodegui/ui/run.kv` — exists, contains `start_grind_btn`, no ToggleButton, no `go_to_rest_btn`
- `tests/test_run_screen.py` — exists, 23 tests pass
- Commits 57a6438, 36de196, 1a7b6f4 — all present
