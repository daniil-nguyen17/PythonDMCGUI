---
phase: 20-screen-registry-and-loader
plan: "02"
subsystem: ui
tags: [kivy, importlib, screen-registry, machine-type, cleanup, mismatch-detection]

# Dependency graph
requires:
  - phase: 20-01
    provides: "_REGISTRY with screen_classes/load_kv keys; cleanup() methods on all base classes"
  - phase: 19-02
    provides: "flat_grind package with load_kv(), FlatGrindRunScreen, FlatGrindAxesSetupScreen, FlatGrindParametersScreen"
provides:
  - "_resolve_dotted_path() module-level helper using importlib"
  - "DMCApp._add_machine_screens(): registry-driven screen instantiation injected into ScreenManager"
  - "build() loads machine KV and screens from registry — no hard-coded flat_grind import"
  - "First-launch picker loads machine screens inline without restart"
  - "on_stop() delegates teardown to screen.cleanup() — no ad-hoc _stop_pos_poll/_stop_mg_reader"
  - "_check_machine_type_mismatch(): background job detects controller/config type disagreement"
  - "_show_mismatch_popup(): offers machine type change with restart or keep-current dismiss"
  - "base.kv ScreenManager contains only machine-agnostic screens (setup, profiles, diagnostics, users)"
  - "tests/test_screen_loader.py: 17 tests covering LOAD-02 and LOAD-04"
affects: [21-serration-screen-set, 22-convex-screen-set, 23-controller-comm-optimization]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Registry-driven screen loading: _add_machine_screens resolves dotted paths via importlib at runtime"
    - "Cleanup delegation: on_stop loops sm.screens calling hasattr(screen, 'cleanup') — screens own teardown"
    - "Two-step KV load: load_kv() called before KV_FILES loop; _add_machine_screens called after Factory.RootLayout()"
    - "Background job + Clock.schedule_once pattern for controller query -> UI popup"

key-files:
  created:
    - tests/test_screen_loader.py
  modified:
    - src/dmccodegui/main.py
    - src/dmccodegui/ui/base.kv

key-decisions:
  - "_MACH_TYPE_MAP maps controller machType int (1/2/3) to machine type strings — TODO: verify on hardware"
  - "machType query failures and unknown values silently ignored (graceful degradation — no popup)"
  - "_add_machine_screens called AFTER Factory.RootLayout() so sm exists; load_kv called BEFORE for KV class registration"
  - "First-launch inline screen loading: checks for 'run' screen absence before calling load_kv + _add_machine_screens"
  - "_show_loader_error shows blocking popup + stop() on registry resolution failure to prevent half-initialised state"

patterns-established:
  - "Screen loader pattern: resolve load_kv -> call it -> resolve screen classes -> instantiate with name= -> inject controller/state -> add_widget"
  - "Cleanup delegation: on_stop never knows screen implementation details — hasattr guard for graceful no-op"

requirements-completed: [LOAD-02, LOAD-04]

# Metrics
duration: 35min
completed: 2026-04-11
---

# Phase 20 Plan 02: Screen Registry and Loader (Wire) Summary

**Registry-driven screen loader wired into main.py: _add_machine_screens() resolves FlatGrind* classes from _REGISTRY via importlib, base.kv purged of hard-coded machine screens, on_stop() delegates to cleanup(), machType mismatch popup added**

## Performance

- **Duration:** 35 min
- **Started:** 2026-04-11T15:45:00Z
- **Completed:** 2026-04-11T16:20:00Z
- **Tasks:** 2 (combined into 1 commit — both tasks share test file)
- **Files modified:** 3

## Accomplishments
- `_resolve_dotted_path()` module-level helper resolves any dotted import path to the named attribute via importlib
- `DMCApp._add_machine_screens(sm)` reads `mc._REGISTRY[active_type]["screen_classes"]`, resolves each class, instantiates with canonical name, injects controller/state, calls `sm.add_widget()` — fully decoupled from machine type
- `build()` now calls registry-based KV load + `_add_machine_screens()` instead of hard-coded `from .screens.flat_grind import load_kv`
- `base.kv` ScreenManager reduced to 4 machine-agnostic screens: setup, profiles, diagnostics, users
- First-launch type picker loads machine screens inline without requiring a restart
- `on_stop()` replaces `run_screen._stop_pos_poll()` / `_stop_mg_reader()` with a cleanup() delegation loop over all screens
- `_check_machine_type_mismatch()` submits a background job querying `MG machType`, silently ignores failures and unknown values, schedules mismatch popup only on type disagreement
- `_show_mismatch_popup()` offers machine type selection buttons + "Keep Current" dismiss; on selection calls `mc.set_active_type()` and shows exit prompt

## Task Commits

Each task was committed atomically:

1. **Tasks 1+2: Screen loader, base.kv update, cleanup delegation, mismatch detection** - `0feb209` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `src/dmccodegui/main.py` — added `_resolve_dotted_path`, `_MACH_TYPE_MAP`, `_add_machine_screens`, `_show_loader_error`, `_check_machine_type_mismatch`, `_show_mismatch_popup`; updated `build()`, `_on_type_selected`, `_on_connect_from_setup`, `on_stop()`
- `src/dmccodegui/ui/base.kv` — removed FlatGrindRunScreen, FlatGrindAxesSetupScreen, FlatGrindParametersScreen from ScreenManager
- `tests/test_screen_loader.py` — 17 tests covering _resolve_dotted_path, _add_machine_screens, on_stop cleanup delegation, base.kv state, and machType mismatch behavior

## Decisions Made
- `_MACH_TYPE_MAP = {1: "4-Axes Flat Grind", 2: "3-Axes Serration Grind", 3: "4-Axes Convex Grind"}` — mapping is a TODO pending hardware verification
- machType query failures and unknown int values silently ignored — per Phase 20 locked decision on graceful degradation
- `_add_machine_screens` called AFTER `Factory.RootLayout()` so `sm = root.ids.sm` exists; `load_kv()` called BEFORE the `KV_FILES` loop so machine screen KV rules are registered before `base.kv` is parsed
- First-launch detection: checks `any(s.name == "run" for s in sm.screens)` before calling load_kv — prevents double-load if screens already exist
- `_show_loader_error` shows a blocking modal + `self.stop()` on registry failure — partial screen set is worse than no app

## Deviations from Plan

None — plan executed exactly as written. Both tasks completed in a single commit (they share the test file and the implementation is cohesive; splitting would have left the test file in a broken import state between commits).

## Issues Encountered
- `object.__new__(DMCApp)` is not safe (Kivy App subclass uses `__new__`); worked around by creating `_BareApp` helper class in tests that delegates to `DMCApp` unbound methods — cleaner pattern than trying to bypass Kivy's metaclass

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Phase 20 is now fully complete: registry extended (Plan 01) and loader wired (Plan 02)
- Phase 21 (Serration Screen Set) can begin — it will replace the flat_grind placeholder paths in _REGISTRY with real serration screen classes
- Phase 22 (Convex Screen Set) similarly ready once Serration is done
- machType mismatch popup will correctly detect wrong machine type when hardware is available — requires hardware verification of _MACH_TYPE_MAP integer values

---
*Phase: 20-screen-registry-and-loader*
*Completed: 2026-04-11*
