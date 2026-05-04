---
phase: 31-bug-fixes-and-ui-polish
plan: 01
subsystem: hmi
tags: [kivy, opengl, angle, gclib, mg-reader, install-script, raspberry-pi]

# Dependency graph
requires:
  - phase: 30-codebase-audit
    provides: clean codebase with consistent naming and docstrings
provides:
  - GL backend startup log confirmation on all platforms
  - MgReader.start() works on Linux (no platform guard)
  - install.sh venv rsync exclude verified correct
affects: [32-per-machine-parameters, 34-pi-cython-protection]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "GL backend logged at startup for diagnostics"
    - "MgReader uses --direct only on win32 (handled in _loop, not start)"

key-files:
  created: []
  modified:
    - src/dmccodegui/main.py
    - src/dmccodegui/hmi/mg_reader.py
    - tests/test_main.py
    - tests/test_mg_reader.py

key-decisions:
  - "GL backend log line runs on ALL platforms (not just Windows) so Linux logs 'default (platform gl)'"
  - "Platform guard fully removed from start() -- _loop already handles --direct flag per-platform"

patterns-established:
  - "Startup diagnostics: log environment configuration values after setdefault calls"

requirements-completed: [FIX-03, FIX-04, FIX-05]

# Metrics
duration: 4min
completed: 2026-05-04
---

# Phase 31 Plan 01: Field Bug Fixes Summary

**GL backend startup log, MG reader Linux guard removal, and install.sh venv exclude verification (FIX-03/04/05)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-04T05:51:50Z
- **Completed:** 2026-05-04T05:55:52Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added GL backend log line in main.py that logs "GL backend: angle_sdl2" on Windows or "GL backend: default (platform gl)" on Linux at startup
- Removed 3-line Linux platform guard from MgReader.start() -- controller MG messages now flow on Pi
- Verified install.sh rsync --exclude='venv/' and venv existence check are correct (FIX-05 verify-and-close)
- 3 new tests added and passing; full suite 519 passed (3 pre-existing failures in test_delta_c_bar_chart.py)

## Task Commits

Each task was committed atomically:

1. **Task 1: ANGLE backend log + MG reader guard removal + tests**
   - `392e8d1` (test: add failing tests -- RED phase)
   - `5a19c59` (feat: GL backend log line + remove Linux guard -- GREEN phase)
2. **Task 2: Verify install.sh venv exclude + full regression** -- no code changes (verify-and-close)

**Plan metadata:** (pending)

_Note: Task 1 used TDD -- test commit then implementation commit._

## Files Created/Modified
- `src/dmccodegui/main.py` -- Added _log.info GL backend line after ANGLE setdefault
- `src/dmccodegui/hmi/mg_reader.py` -- Removed platform guard, updated start() docstring
- `tests/test_main.py` -- Added TestAngleBackend class with 2 tests
- `tests/test_mg_reader.py` -- Added test_start_not_blocked_on_linux to TestStartStop

## Decisions Made
- GL backend log line placed outside the `if sys.platform == "win32"` block so it runs on all platforms, logging the actual env var value (or "default (platform gl)" if unset)
- Platform guard fully removed from start() rather than just loosening it, since _loop already has the per-platform --direct handling

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None -- no external service configuration required.

## Next Phase Readiness
- FIX-03, FIX-04, FIX-05 all resolved
- Ready for Plan 02 (UI polish) and Plan 03 (remaining bug fixes)
- 3 pre-existing test failures in test_delta_c_bar_chart.py logged to deferred-items.md (out of scope)

## Self-Check: PASSED

All files verified present. All commits verified in history.

---
*Phase: 31-bug-fixes-and-ui-polish*
*Completed: 2026-05-04*
