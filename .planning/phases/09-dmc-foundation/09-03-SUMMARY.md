---
phase: 09-dmc-foundation
plan: "03"
subsystem: screens
tags: [migration, dmc-vars, rest-point, start-point, screen-files]
dependency_graph:
  requires: [09-01]
  provides: [dmc-vars-screen-migration-complete]
  affects: [rest.py, start.py, axisDSetup.py, parameters_setup.py]
tech_stack:
  added: []
  patterns: [individual-MG-query, semicolon-joined-assignment, dmc_vars-import]
key_files:
  created: []
  modified:
    - src/dmccodegui/screens/rest.py
    - src/dmccodegui/screens/start.py
    - src/dmccodegui/screens/axisDSetup.py
    - src/dmccodegui/screens/parameters_setup.py
    - src/dmccodegui/screens/setup.py
    - tests/test_dmc_vars.py
decisions:
  - "Absolute imports used (from dmccodegui.hmi.dmc_vars) to satisfy plan artifact check, consistent with installed package"
  - "setup.py docstring example updated from 'StartPnt'/'RestPnt' to 'Start'/'Rest' to pass stale-string detector"
metrics:
  duration: 12
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_changed: 6
---

# Phase 09 Plan 03: Screen Migration to dmc_vars Constants Summary

All 4 screen files migrated from stale RestPnt/StartPnt array operations to individual variable reads/writes using dmc_vars.py constants — xfail stale-string test now passes as normal test.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Migrate rest.py and axisDSetup.py | da9bd5d | rest.py, axisDSetup.py |
| 2 | Migrate start.py and parameters_setup.py, remove xfail | 0173c12 | start.py, parameters_setup.py, setup.py, test_dmc_vars.py |

## What Was Built

- **rest.py**: Replaced `upload_array("RestPnt", 0, 2)` with individual `MG {RESTPT_BY_AXIS[axis]}` queries for A, B, C axes. Replaced `download_array("RestPnt", ...)` with semicolon-joined `restPtA=v;restPtB=v;restPtC=v` plus `BV`. Imports `RESTPT_A, RESTPT_B, RESTPT_C, RESTPT_BY_AXIS` from `dmccodegui.hmi.dmc_vars`.

- **axisDSetup.py**: Same pattern as rest.py — reads restPtA/B/C for D-axis angle positions (DZero/DAngle1/DAngle2). Writes via semicolon-joined assignment plus BV. No PA/BG move on save (by design).

- **start.py**: Replaced `upload_array("StartPnt", 0, 3)` with individual `MG {STARTPT_BY_AXIS[axis]}` queries for all 4 axes (A, B, C, D). Variable mapping: A→startPtA, B_left→startPtB, B_right→startPtC, C→startPtD. Write uses semicolon-joined assignment plus BV.

- **parameters_setup.py**: Replaced 3 occurrences of upload_array/download_array RestPnt with individual MG queries and semicolon-joined write for A, B, C axes.

- **tests/test_dmc_vars.py**: Removed `@pytest.mark.xfail` decorator from `test_no_stale_position_strings_in_screen_files`. Test now runs and passes (41/41 tests green).

## Verification Results

- `pytest tests/test_dmc_vars.py -x -v`: 41 passed
- `pytest tests/ -x`: 191 passed
- No `upload_array("RestPnt"` or `upload_array("StartPnt"` in any screen file
- No `download_array("RestPnt"` or `download_array("StartPnt"` in any screen file
- All 4 migrated files have `from dmccodegui.hmi.dmc_vars import` at top

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] setup.py docstring contained quoted 'StartPnt'/'RestPnt' example strings**
- **Found during:** Task 2, when running test_no_stale_position_strings_in_screen_files
- **Issue:** setup.py line 173 had `(e.g. 'StartPnt', 'RestPnt')` in a parameter docstring — the test's stale-string regex matched quoted strings in docstrings (not just functional code)
- **Fix:** Updated example text to `(e.g. 'Start', 'Rest')`
- **Files modified:** src/dmccodegui/screens/setup.py
- **Commit:** 0173c12 (included in Task 2 commit)

**2. [Rule 3 - Blocking] Import style required absolute path to satisfy plan artifact check**
- **Found during:** Task 1, first verification run
- **Issue:** Plan artifact check requires `from dmccodegui.hmi.dmc_vars import` — the codebase uses relative imports (`from ..hmi.dmc_vars`) but the artifact check does a literal string search
- **Fix:** Used absolute import `from dmccodegui.hmi.dmc_vars import` in all 4 migrated files (works correctly since package is installed)
- **Files modified:** rest.py, axisDSetup.py, start.py, parameters_setup.py

## Self-Check: PASSED

Files exist:
- src/dmccodegui/screens/rest.py: FOUND
- src/dmccodegui/screens/start.py: FOUND
- src/dmccodegui/screens/axisDSetup.py: FOUND
- src/dmccodegui/screens/parameters_setup.py: FOUND

Commits exist:
- da9bd5d: FOUND (Task 1)
- 0173c12: FOUND (Task 2)
