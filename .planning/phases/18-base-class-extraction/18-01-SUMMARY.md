---
phase: 18-base-class-extraction
plan: "01"
subsystem: screens
tags: [base-classes, refactor, architecture, kivy, mixin]
dependency_graph:
  requires: []
  provides:
    - screens.base.BaseRunScreen
    - screens.base.BaseAxesSetupScreen
    - screens.base.BaseParametersScreen
    - screens.base.SetupScreenMixin
    - screens.flat_grind_widgets.DeltaCBarChart
    - screens.flat_grind_widgets._BaseBarChart
    - screens.flat_grind_widgets.stone_window_for_index
  affects:
    - src/dmccodegui/screens/base.py (new)
    - src/dmccodegui/screens/flat_grind_widgets.py (new)
    - tests/test_base_classes.py (new)
    - tests/test_flat_grind_widgets.py (new)
tech_stack:
  added: []
  patterns:
    - subscribe-on-enter/unsubscribe-on-leave via MachineState.subscribe()
    - Clock.schedule_once wrapping subscription callback for thread-safe UI
    - cooperative multiple inheritance with SetupScreenMixin (no __init__)
    - lazy imports inside mixin methods to avoid circular deps
key_files:
  created:
    - src/dmccodegui/screens/base.py
    - src/dmccodegui/screens/flat_grind_widgets.py
    - tests/test_base_classes.py
    - tests/test_flat_grind_widgets.py
  modified: []
decisions:
  - "BaseRunScreen is thin — no jog, no matplotlib, no setup mode"
  - "SetupScreenMixin has NO __init__ to prevent cooperative MRO breakage (Pitfall #3)"
  - "_state_unsub owned exclusively by base class; subclasses must not shadow it"
  - "BCompBarChart stays in run.py — Serration-specific, deferred to Phase 21"
  - "flat_grind_widgets.py is a standalone copy — run.py unmodified until Plan 02"
metrics:
  duration_minutes: 5
  tasks_completed: 3
  tasks_total: 3
  files_created: 4
  files_modified: 0
  lines_written: 1499
  completed_date: "2026-04-11"
requirements_addressed: [ARCH-01, ARCH-02, ARCH-04]
---

# Phase 18 Plan 01: Base Class Extraction Summary

**One-liner:** BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen, and SetupScreenMixin extracted into screens/base.py; DeltaCBarChart and stone geometry constants extracted into screens/flat_grind_widgets.py as standalone new files.

## What Was Built

### screens/base.py (856 lines)

Four classes that provide the shared inheritance foundation for all machine screens:

**SetupScreenMixin** — Owns the canonical `_SETUP_SCREENS` frozenset (consolidates the duplicate that existed in both axes_setup.py:79 and parameters.py:48). Provides `_enter_setup_if_needed()` and `_exit_setup_if_needed()` with motion guards. Uses lazy imports inside methods. No `__init__` (prevents cooperative MRO breakage).

**BaseRunScreen(Screen)** — Thin base. Owns `controller`/`state` ObjectProperties and the subscribe-on-enter/unsubscribe-on-leave lifecycle. `on_pre_enter` subscribes to MachineState and immediately calls `_on_state_change(state)`. `on_leave` unsubscribes and logs a warning if `_state_unsub` was unexpectedly None. Does NOT include SetupScreenMixin.

**BaseAxesSetupScreen(Screen, SetupScreenMixin)** — Includes jog infrastructure extracted from axes_setup.py. `jog_axis()` validates axes against `mc.get_axis_list()` so Serration/Convex machines automatically block invalid axes. CPM read pattern (`_schedule_cpm_read`, `_read_cpm_for_axis`) sets `_cpm_ready=True` once the read attempt completes. `on_pre_enter` also calls `_enter_setup_if_needed()`.

**BaseParametersScreen(Screen, SetupScreenMixin)** — Includes card builder, dirty tracking dict, `validate_field()`, `apply_to_controller()`, `read_from_controller()`, and `_rebuild_for_machine_type()`. All methods use `mc.get_param_defs()` dynamically — no machine-type coupling in the base.

### screens/flat_grind_widgets.py (325 lines)

Standalone extraction of Flat Grind-specific widgets from run.py (run.py is NOT modified — Plan 02 adds the import redirect):

- `_BaseBarChart` — shared Widget base for all bar chart types
- `DeltaCBarChart` — Knife Grind Adjustment bar chart with stone window overlay
- `DELTA_C_WRITABLE_START`, `DELTA_C_WRITABLE_END`, `DELTA_C_ARRAY_SIZE`, `DELTA_C_STEP`
- `STONE_SURFACE_MM`, `STONE_OVERHANG_MM`, `STEP_MM`, `STONE_WINDOW_INDICES`
- `stone_window_for_index()` — window clamping helper

`BCompBarChart` intentionally excluded — Serration-specific, deferred to Phase 21.

### tests/ (318 lines across 2 files)

`test_base_classes.py` — 7 tests covering ARCH-01 (inheritance hierarchy), ARCH-02 (subscribe/unsubscribe lifecycle with zero duplicate callbacks after two cycles), ARCH-04 (no lifecycle hooks in .kv files, verified via glob), SetupScreenMixin frozenset, and `_on_state_change` dispatch to subclass via `Clock.tick()`.

`test_flat_grind_widgets.py` — 4 tests covering import, `stone_window_for_index` bounds, DELTA_C constant values, and explicit assertion that `BCompBarChart` is NOT present.

**All 11 new tests pass.**

## Deviations from Plan

None — plan executed exactly as written. The only deviation note is that `test_axes_setup.py::test_mode_default_rest` and 14 other tests in the existing suite were already failing before Plan 01 started (confirmed by `git stash` regression check). These are pre-existing failures unrelated to Phase 18 work. Deferred to the existing technical debt backlog.

## Commits

| Hash | Message |
|------|---------|
| c096738 | feat(18-01): create screens/base.py with all four base classes |
| 2cdd33f | feat(18-01): create screens/flat_grind_widgets.py with DeltaC widgets |
| ecb3bac | test(18-01): add tests for base classes and flat grind widgets |

## Requirements Addressed

| ID | Status |
|----|--------|
| ARCH-01 | BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen importable from screens.base |
| ARCH-02 | Subscribe-on-enter/unsubscribe-on-leave enforced in base class; zero listener accumulation verified |
| ARCH-04 | All lifecycle hooks in Python; test_no_lifecycle_in_kv asserts no .kv definitions |

ARCH-03 (9 per-machine screen classes) is deferred to Phases 19-22 as documented in 18-RESEARCH.md Open Questions.

## Next Plan

Plan 02 will update run.py, axes_setup.py, and parameters.py to inherit from the new base classes, removing the duplicated code.

## Self-Check: PASSED

All 4 created files confirmed on disk. All 3 task commits confirmed in git history.
