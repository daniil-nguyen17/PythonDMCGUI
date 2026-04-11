---
phase: 20-screen-registry-and-loader
plan: "01"
subsystem: ui
tags: [kivy, machine-config, screen-registry, cleanup, matplotlib, base-classes]

# Dependency graph
requires:
  - phase: 19-flat-grind-rename-and-kv-split
    provides: "FlatGrindRunScreen, FlatGrindAxesSetupScreen, FlatGrindParametersScreen, load_kv() in flat_grind/__init__.py"
  - phase: 18-base-class-extraction
    provides: "BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen with _state_unsub lifecycle"
provides:
  - "_REGISTRY with screen_classes and load_kv dotted import paths for all 3 machine types"
  - "cleanup() on BaseRunScreen (non-blocking teardown: pos_poll, mg_stop_event, plt.close, unsub)"
  - "cleanup() on BaseAxesSetupScreen and BaseParametersScreen (state unsub)"
  - "Tests verifying importlib resolution of all dotted paths"
affects:
  - phase: 20-screen-registry-and-loader plan 02 (screen loader reads screen_classes/load_kv)
  - phase: 21-serration-screen-set (will replace placeholder screen_classes entries)
  - phase: 22-convex-screen-set (will replace placeholder screen_classes entries)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_REGISTRY data contract: axes, has_bcomp, param_defs, load_kv, screen_classes"
    - "cleanup() teardown order: stop_poll -> signal_thread (no join) -> plt.close -> unsub"
    - "Dotted import paths resolved via importlib.import_module + rsplit('.', 1) + getattr"

key-files:
  created:
    - tests/test_base_classes.py (cleanup tests — 12 new tests added to existing file)
  modified:
    - src/dmccodegui/machine_config.py
    - src/dmccodegui/screens/base.py
    - tests/test_machine_config.py

key-decisions:
  - "Thread stop strategy (locked): cleanup() sets _mg_stop_event and clears _mg_thread reference — no join. Normal on_leave _stop_mg_reader() keeps its join."
  - "plt import at module level via try/except so tests can patch dmccodegui.screens.base.plt without importing matplotlib in each test"
  - "Convex and Serration placeholder screen_classes point to flat_grind with TODO Phase 21/22 comments — satisfies importlib resolution test immediately"

patterns-established:
  - "cleanup() is idempotent: all attribute reads guarded with getattr/is-not-None checks, attributes cleared after use"
  - "INFO logging in cleanup() uses [ClassName] prefix matching existing logger convention"

requirements-completed: [LOAD-01, LOAD-03]

# Metrics
duration: 3min
completed: 2026-04-11
---

# Phase 20 Plan 01: Screen Registry and Loader Foundation Summary

**_REGISTRY extended with screen_classes/load_kv dotted import paths; non-blocking idempotent cleanup() added to all three base screen classes**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-11T15:39:25Z
- **Completed:** 2026-04-11T15:42:05Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Extended `_REGISTRY` in machine_config.py with `screen_classes` (run/axes_setup/parameters dotted paths) and `load_kv` for all 3 machine types; Convex and Serration use flat_grind as placeholders with Phase 21/22 TODO comments
- All 6 dotted paths resolve to real classes/callables via importlib at test time, providing immediate verification of the data contract Plan 02 will consume
- Added `cleanup()` to `BaseRunScreen` with locked non-blocking teardown order: stop_pos_poll -> signal mg_stop_event (no join, clears thread ref) -> plt.close(_fig) -> unsub state
- Added `cleanup()` to `BaseAxesSetupScreen` and `BaseParametersScreen` (state unsub only)
- All three cleanup() methods are idempotent (safe to call twice) and log at INFO level

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend _REGISTRY with screen_classes and load_kv** - `7f5d130` (feat)
2. **Task 2: Add cleanup() methods to base screen classes** - `23dfa9f` (feat)

## Files Created/Modified

- `src/dmccodegui/machine_config.py` — Added screen_classes and load_kv keys to all 3 _REGISTRY entries
- `src/dmccodegui/screens/base.py` — Added matplotlib.pyplot import (try/except); cleanup() on all 3 base classes
- `tests/test_machine_config.py` — 6 new registry tests (key presence, value correctness, importlib resolution)
- `tests/test_base_classes.py` — 12 new cleanup tests (all steps, edge cases, idempotency, INFO logging)

## Decisions Made

- Thread stop strategy (locked): `cleanup()` sets `_mg_stop_event` and clears `_mg_thread = None` — does NOT call `_stop_mg_reader()` which joins. Normal navigation via `on_leave` keeps `_stop_mg_reader()` with its join. This preserves non-blocking semantics for forced screen swap.
- `plt` imported at module level via `try/except ImportError` so tests can patch `dmccodegui.screens.base.plt` with a single `patch()` call — consistent with the existing `submit` re-export pattern.
- Convex and Serration placeholder screen_classes point to flat_grind immediately so importlib resolution tests pass now without stubs.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

6 pre-existing test failures in test_main_estop.py and test_status_bar.py confirmed unrelated to this plan (verified by stash/test/restore cycle). No new failures introduced.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02 (screen loader) can now read `_REGISTRY[mtype]["load_kv"]` and `_REGISTRY[mtype]["screen_classes"]` to dynamically load KV and resolve screen class imports
- `cleanup()` provides the teardown contract Plan 02's `on_stop` wiring needs before calling `sm.remove_widget()`
- No blockers for Plan 02

---
*Phase: 20-screen-registry-and-loader*
*Completed: 2026-04-11*
