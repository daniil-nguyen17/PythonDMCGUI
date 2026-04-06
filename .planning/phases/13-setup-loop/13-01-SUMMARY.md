---
phase: 13-setup-loop
plan: "01"
subsystem: dmc-program, hmi-vars
tags: [dmc, hmi-triggers, setup-loop, constants]
dependency_graph:
  requires: []
  provides: [hmiGoRs-dmc-var, hmiGoSt-dmc-var, hmiExSt-dmc-var, HMI_GO_REST-py, HMI_GO_START-py, HMI_EXIT_SETUP-py]
  affects: [4 Axis Stainless grind.dmc, src/dmccodegui/hmi/dmc_vars.py]
tech_stack:
  added: []
  patterns: [one-shot-hmi-trigger, dmc-vars-single-source-of-truth]
key_files:
  created: []
  modified:
    - "4 Axis Stainless grind.dmc"
    - src/dmccodegui/hmi/dmc_vars.py
    - tests/test_dmc_vars.py
decisions:
  - "ALL_HMI_TRIGGERS grew from 8 to 11 — updated count assertion in test_all_hmi_triggers_list_has_8_items"
metrics:
  duration_minutes: 2
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_modified: 3
---

# Phase 13 Plan 01: HMI Setup-Loop Trigger Variables Summary

**One-liner:** Three new HMI one-shot trigger variables (hmiGoRs, hmiGoSt, hmiExSt) wired into DMC #PARAMS and #SULOOP with matching Python constants in dmc_vars.py.

## What Was Built

Added the DMC-side and Python-side foundation for three setup-loop controls:
- **Go To Rest** (`hmiGoRs` / `HMI_GO_REST`): fires JS #GOREST when set to 0
- **Go To Start** (`hmiGoSt` / `HMI_GO_START`): fires JS #GOSTR when set to 0
- **Exit Setup** (`hmiExSt` / `HMI_EXIT_SETUP`): combined OR with existing @IN[32] physical button

All three follow the established one-shot pattern: declared with default=1 in #PARAMS, reset to 1 as the first statement inside the triggered IF block.

## Tasks Completed

### Task 1: Add three HMI trigger variables to DMC program
- Commit: `e4d1834`
- Files: `4 Axis Stainless grind.dmc`
- Added hmiGoRs, hmiGoSt, hmiExSt declarations to #PARAMS (lines ~507-509)
- Added IF (hmiGoRs = 0) and IF (hmiGoSt = 0) blocks in #SULOOP after hmiCalc block
- Replaced bare `IF (@IN[32] = 0)` with `IF (@IN[32] = 0) | (hmiExSt = 0)` combined OR

### Task 2: Add Python constants and tests (TDD)
- RED commit: `c498504` — 5 failing tests for new constants
- GREEN commit: `4ac25e1` — constants + auto-fix for count assertion
- Files: `src/dmccodegui/hmi/dmc_vars.py`, `tests/test_dmc_vars.py`
- Added HMI_GO_REST, HMI_GO_START, HMI_EXIT_SETUP to dmc_vars.py
- Added all three to ALL_HMI_TRIGGERS (8 -> 11 items)
- 244 total tests pass

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated stale count assertion in existing test**
- **Found during:** Task 2 GREEN phase
- **Issue:** `test_all_hmi_triggers_list_has_8_items` asserted `len == 8`, but the plan requires adding 3 new items to ALL_HMI_TRIGGERS, making the count 11
- **Fix:** Updated assertion to `len == 11` with comment explaining the change
- **Files modified:** tests/test_dmc_vars.py
- **Commit:** 4ac25e1

## Verification Results

1. `grep -c "hmiGoRs|hmiGoSt|hmiExSt" "4 Axis Stainless grind.dmc"` returned **9** (>= 6 required)
2. `python -m pytest tests/test_dmc_vars.py -x -v` — **50 passed**
3. `python -m pytest tests/ -x` — **244 passed**

## Self-Check: PASSED
