---
phase: 28-logging-infrastructure
plan: "02"
subsystem: logging
tags: [logging, migration, print-to-logger, structured-logging]
dependency_graph:
  requires: [28-01]
  provides: [zero-print-production-code, full-logging-coverage]
  affects: [controller, screens, hmi, utils]
tech_stack:
  added: []
  patterns: [module-level-logger, percent-style-format, level-heuristic]
key_files:
  created: []
  modified:
    - src/dmccodegui/controller.py
    - src/dmccodegui/hmi/mg_reader.py
    - src/dmccodegui/utils/transport.py
    - src/dmccodegui/screens/flat_grind/run.py
    - src/dmccodegui/screens/flat_grind/axes_setup.py
    - src/dmccodegui/screens/serration/run.py
    - src/dmccodegui/screens/serration/axes_setup.py
    - src/dmccodegui/screens/convex/run.py
    - src/dmccodegui/screens/convex/axes_setup.py
decisions:
  - "controller.py uses log (not logger) — matches existing pattern established before plan 02"
  - "serration/run.py was already partially migrated (bComp/cComp logger calls) — only MG reader loop prints remained"
  - "Pre-existing test failure (test_enter_setup_skips_fire_when_already_setup) confirmed pre-existing, not caused by this plan"
metrics:
  duration_minutes: 9
  completed_date: "2026-04-22"
  tasks_completed: 2
  files_modified: 9
requirements: [APP-01]
---

# Phase 28 Plan 02: Print-to-Logger Migration Summary

All 135 production print() calls across 9 source files migrated to structured logging. Zero print() calls remain in production code (controller.py __main__ block excluded per plan spec).

## What Was Built

Completed the print-to-logger migration started in Plan 01. Every file now has a module-level `logger = logging.getLogger(__name__)` and uses `%s`-style format specifiers. Log levels assigned per the research heuristic:
- `debug` — protocol traces, individual command sends/responses, verbose reads
- `info` — state transitions, connections, startup events
- `warning` — recoverable failures, parse errors, retry triggers
- `error` — operation failures that surface to operator

## Tasks Completed

### Task 1: Core infrastructure files (commit 0531a32)

- **controller.py** (~35 production print() calls): `cmd()` method traces, `upload_array()` fallback traces, `wait_for_ready()`, `discover_length()`, `diagnose_controller_state()`, `read_array_slice()`. Note: file already had `import logging` and `log = logging.getLogger(__name__)` from an earlier partial migration — retained `log` name to avoid churn.
- **hmi/mg_reader.py** (4 calls): gclib import check, GOpen success/failure, handle close on exit.
- **utils/transport.py** (2 calls): command retry warnings, final give-up error.

### Task 2: Screen files (commit 9d8366f)

- **flat_grind/run.py** (29 calls): Shutdown sequence (hmiSetp/hmiHome/BV), More/Less stone readbacks, deltaC apply/write, compensation mode toggle, stone contour reads, MG reader thread lifecycle.
- **flat_grind/axes_setup.py** (13 calls): CPM reads and overrides, teach_rest/start guards, _fire_hmi_trigger errors, _read_one errors, initial value readback logs.
- **serration/run.py** (4 calls): MG reader thread open/connected/failed/closed — bComp/cComp methods were already migrated.
- **serration/axes_setup.py** (12 calls): Same pattern as flat_grind axes_setup.
- **convex/run.py** (18 calls): More/Less stone, deltaC apply, compensation toggle, stone contour reads, deltaC baseline read.
- **convex/axes_setup.py** (12 calls): Same pattern as flat_grind axes_setup.

## Deviations from Plan

None — plan executed exactly as written.

The pre-existing test failure (`test_enter_setup_skips_fire_when_already_setup`) was confirmed pre-existing by running the test suite before applying any changes. It is out of scope.

## Self-Check: PASSED

- SUMMARY.md: FOUND
- Task 1 commit 0531a32: FOUND
- Task 2 commit 9d8366f: FOUND
- Zero production print() calls: VERIFIED
- All 9 files have module-level logger: VERIFIED
