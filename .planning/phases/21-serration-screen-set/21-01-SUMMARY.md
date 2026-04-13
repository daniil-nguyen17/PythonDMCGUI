---
phase: 21-serration-screen-set
plan: 01
subsystem: screens/serration
tags: [serration, screens, package, registry, kv, tests]
dependency_graph:
  requires:
    - phase-18-base-class-extraction
    - phase-19-flat-grind-rename
    - phase-20-screen-registry-and-loader
  provides:
    - screens/serration package importable
    - SerrationAxesSetupScreen class
    - SerrationParametersScreen class
    - SerrationRunScreen stub
    - BCompPanel widget skeleton
    - numSerr in _SERRATION_PARAM_DEFS
    - BCOMP_ARRAY and BCOMP_NUM_SERR in dmc_vars
  affects:
    - machine_config._REGISTRY["3-Axes Serration Grind"] (now points to real Serration classes)
    - machine_config._SERRATION_PARAM_DEFS (numSerr added)
    - dmccodegui.hmi.dmc_vars (BCOMP_ARRAY, BCOMP_NUM_SERR added)
tech_stack:
  added: []
  patterns:
    - Per-machine screen package with deferred load_kv() (mirrors flat_grind pattern exactly)
    - Thin subclass pattern: Serration classes copy flat_grind code for full independence
    - BCompPanel as BoxLayout skeleton with stub methods for Plan 02 to fill in
key_files:
  created:
    - src/dmccodegui/screens/serration/__init__.py
    - src/dmccodegui/screens/serration/run.py
    - src/dmccodegui/screens/serration/axes_setup.py
    - src/dmccodegui/screens/serration/parameters.py
    - src/dmccodegui/screens/serration/widgets.py
    - src/dmccodegui/ui/serration/axes_setup.kv
    - src/dmccodegui/ui/serration/parameters.kv
    - src/dmccodegui/ui/serration/run.kv
    - tests/test_serration_screens.py
  modified:
    - src/dmccodegui/machine_config.py
    - src/dmccodegui/hmi/dmc_vars.py
decisions:
  - "Copied flat_grind code into serration classes (no import from flat_grind) for full independence per user decision"
  - "D-axis absent from serration/axes_setup.kv entirely — axis_row_d not created, ids.get() returns None gracefully"
  - "run.py is a stub class returning pass — Plan 02 replaces with full implementation"
  - "run.kv is a stub KV with minimal canvas — Plan 02 replaces with full run screen layout"
  - "numSerr appended to _SERRATION_PARAM_DEFS after the existing filtered list"
metrics:
  duration_seconds: 371
  completed_date: "2026-04-13"
  tasks_completed: 2
  tasks_total: 2
  files_created: 9
  files_modified: 2
  tests_added: 10
  tests_passing: 10
---

# Phase 21 Plan 01: Serration Screen Package Skeleton Summary

Serration screen package created with thin subclasses (SerrationAxesSetupScreen, SerrationParametersScreen, SerrationRunScreen stub), KV files (3-axis, no D-axis), BCompPanel skeleton, registry wired to real Serration classes, numSerr added to param_defs, and 10-test scaffold all passing.

## What Was Built

### Task 1: Serration package, thin subclasses, KV files, registry update

Created `src/dmccodegui/screens/serration/` package mirroring the flat_grind pattern:

- `__init__.py` — deferred `load_kv()` pattern, exports all three screen classes
- `run.py` — stub `class SerrationRunScreen(BaseRunScreen): pass` for Plan 02 to replace
- `axes_setup.py` — full copy of FlatGrindAxesSetupScreen renamed to SerrationAxesSetupScreen; `_rebuild_axis_rows()` uses `mc.get_axis_list()` which returns `["A","B","C"]` — D-axis row lookup returns None gracefully
- `parameters.py` — full copy of FlatGrindParametersScreen renamed to SerrationParametersScreen; backward-compat re-export uses `_SERRATION_PARAM_DEFS` instead of `_FLAT_PARAM_DEFS`
- `widgets.py` — BCompPanel skeleton inheriting BoxLayout with `num_serrations` property and stub methods

Created `src/dmccodegui/ui/serration/`:
- `axes_setup.kv` — 3-axis layout (A, B, C only — no axis_row_d widget)
- `parameters.kv` — identical structure to flat_grind/parameters.kv with `<SerrationParametersScreen>:` header
- `run.kv` — minimal stub for Plan 02 to replace

Updated `machine_config.py`:
- Appended `numSerr` to `_SERRATION_PARAM_DEFS` (group=Geometry, min=1, max=200)
- Wired `_REGISTRY["3-Axes Serration Grind"]` to real Serration classes (removed Phase 20 TODO placeholders)

Updated `dmc_vars.py`:
- Added `BCOMP_ARRAY = "bComp"` and `BCOMP_NUM_SERR = "numSerr"` with TODO hardware-verification comments

### Task 2: Test scaffold for SERR requirements

Created `tests/test_serration_screens.py` with 10 tests:

1. `test_serration_run_screen_importable` — import + BaseRunScreen subclass check
2. `test_serration_axes_setup_importable` — import + BaseAxesSetupScreen subclass check
3. `test_serration_axes_setup_inherits_base` — MRO verification
4. `test_serration_params_importable` — import + BaseParametersScreen subclass check
5. `test_serration_param_defs_has_numserr` — verifies numSerr with group/min/max metadata
6. `test_serration_params_no_d_axis_vars` — confirms fdD, pitchD, ratioD, ctsRevD absent
7. `test_bcomp_panel_importable` — import + BoxLayout subclass check
8. `test_registry_points_to_serration_classes` — all screen_class paths contain "serration" not "flat_grind"
9. `test_serration_axes_setup_kv_no_d_axis` — file text does not contain "axis_row_d"
10. `test_dmc_vars_bcomp_constants` — BCOMP_ARRAY and BCOMP_NUM_SERR are non-empty strings

All 10 tests pass. Full suite: 215 passing, 1 pre-existing failure in `test_main_estop.py::TestEStop::test_estop_commands_order` (unrelated to this plan — was already failing before Phase 21).

## Verification

```
python -c "from dmccodegui.screens.serration import SerrationRunScreen, SerrationAxesSetupScreen, SerrationParametersScreen, load_kv; print('All imports OK')"
# All imports OK

pytest tests/test_serration_screens.py -x -v
# 10 passed in 1.14s

pytest tests/test_flat_grind_widgets.py::test_no_duplicate_kv_rule_headers -x
# 1 passed (no KV rule name collisions)

pytest tests/ -x
# 215 passed, 1 pre-existing failure (test_main_estop, unrelated)
```

## Commits

| Hash | Message |
|------|---------|
| 64e405d | feat(21-01): create serration screen package, KV files, registry update |
| 338446d | test(21-01): add test scaffold for SERR requirements |

## Deviations from Plan

None — plan executed exactly as written. The run.kv stub was required by `load_kv()` calling `Builder.load_file(run.kv)` — plan documented this as needed.

## Self-Check

All created files exist:
- src/dmccodegui/screens/serration/__init__.py — FOUND
- src/dmccodegui/screens/serration/run.py — FOUND
- src/dmccodegui/screens/serration/axes_setup.py — FOUND
- src/dmccodegui/screens/serration/parameters.py — FOUND
- src/dmccodegui/screens/serration/widgets.py — FOUND
- src/dmccodegui/ui/serration/axes_setup.kv — FOUND
- src/dmccodegui/ui/serration/parameters.kv — FOUND
- src/dmccodegui/ui/serration/run.kv — FOUND
- tests/test_serration_screens.py — FOUND

Commits exist:
- 64e405d — FOUND
- 338446d — FOUND

## Self-Check: PASSED
