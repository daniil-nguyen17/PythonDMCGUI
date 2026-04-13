---
phase: 22-convex-screen-set
plan: "01"
subsystem: convex-screens
tags: [convex, screens, kv, machine-config, registry, tests]
dependency_graph:
  requires: [phase-18-base-classes, phase-19-flat-grind-rename, phase-20-screen-registry]
  provides: [convex-package-skeleton, convex-kv-files, convex-registry-entry, convex-param-defs]
  affects: [machine_config._REGISTRY, machine_config._CONVEX_PARAM_DEFS]
tech_stack:
  added: []
  patterns: [thin-subclass-pattern, deferred-kv-loading, explicit-list-literal-param-defs]
key_files:
  created:
    - src/dmccodegui/screens/convex/__init__.py
    - src/dmccodegui/screens/convex/run.py
    - src/dmccodegui/screens/convex/axes_setup.py
    - src/dmccodegui/screens/convex/parameters.py
    - src/dmccodegui/screens/convex/widgets.py
    - src/dmccodegui/ui/convex/run.kv
    - src/dmccodegui/ui/convex/axes_setup.kv
    - src/dmccodegui/ui/convex/parameters.kv
    - tests/test_convex_screens.py
  modified:
    - src/dmccodegui/machine_config.py
decisions:
  - "Convex package fully independent — no imports from flat_grind in any Python file (copied code pattern, same as Phase 21 Serration decision)"
  - "_CONVEX_PARAM_DEFS replaced with explicit 20-entry list literal — no shallow copy, each dict is a distinct object with placeholder comment"
  - "Registry '4-Axes Convex Grind' updated to real Convex class dotted paths — Phase 20 TODO comment removed"
  - "ConvexAdjustPanel is a placeholder BoxLayout widget pending customer convex specs"
  - "ConvexRunScreen is a stub (pass body) — full implementation deferred to Plan 02"
metrics:
  duration: "5 minutes"
  completed_date: "2026-04-13"
  tasks_completed: 2
  tasks_total: 2
  files_created: 9
  files_modified: 1
  tests_added: 12
  tests_passing: 12
---

# Phase 22 Plan 01: Convex Screen Set Skeleton Summary

**One-liner:** Convex screen package with thin subclasses, explicit _CONVEX_PARAM_DEFS literal, 4-axis KV files, and updated registry pointing to real Convex classes.

## What Was Built

Created the complete `screens/convex/` Python package and `ui/convex/` KV file set:

- **`screens/convex/__init__.py`** — Deferred `load_kv()` pattern (idempotent, `_kv_loaded` guard), exports ConvexRunScreen, ConvexAxesSetupScreen, ConvexParametersScreen, load_kv
- **`screens/convex/run.py`** — Stub `class ConvexRunScreen(BaseRunScreen): pass` — Plan 02 replaces with full implementation
- **`screens/convex/axes_setup.py`** — Full `ConvexAxesSetupScreen` copied from flat_grind/axes_setup.py with all FlatGrind references renamed; all 4 axes (A, B, C, D) present; no flat_grind imports
- **`screens/convex/parameters.py`** — Full `ConvexParametersScreen` copied from flat_grind/parameters.py; re-exports `_CONVEX_PARAM_DEFS as PARAM_DEFS`
- **`screens/convex/widgets.py`** — `ConvexAdjustPanel` placeholder BoxLayout with cyan header and grey "Pending customer specs" label; TODO docstring for post-sign-off replacement
- **`ui/convex/run.kv`** — Minimal stub `<ConvexRunScreen>:` with placeholder Label
- **`ui/convex/axes_setup.kv`** — `<ConvexAxesSetupScreen>:` with all 4 axis rows including `axis_row_d`; same accent colors as flat_grind (A=orange, B=purple, C=cyan, D=yellow)
- **`ui/convex/parameters.kv`** — `<ConvexParametersScreen>:` identical layout to flat_grind/parameters.kv
- **`machine_config.py`** — `_CONVEX_PARAM_DEFS` replaced with explicit 20-entry list literal (placeholder comment above); `_REGISTRY["4-Axes Convex Grind"]` updated to real Convex class paths, TODO comment removed

## Tests

`tests/test_convex_screens.py` — 12 tests, all passing:

1. `test_convex_run_screen_importable` — ConvexRunScreen subclasses BaseRunScreen
2. `test_convex_axes_setup_importable` — ConvexAxesSetupScreen subclasses BaseAxesSetupScreen
3. `test_convex_axes_setup_inherits_base` — BaseAxesSetupScreen in MRO
4. `test_convex_params_importable` — ConvexParametersScreen subclasses BaseParametersScreen
5. `test_convex_param_defs_has_all_flat_grind_vars` — all 20 expected vars present via get_param_defs()
6. `test_convex_param_defs_independent` — _CONVEX_PARAM_DEFS is distinct list with distinct dicts
7. `test_convex_param_defs_has_placeholder_comment` — "Placeholder" in 2 lines before definition
8. `test_convex_adjust_panel_importable` — ConvexAdjustPanel is BoxLayout with children >= 1
9. `test_registry_points_to_convex_classes` — registry values contain "convex", not "flat_grind"
10. `test_convex_axes_setup_kv_has_d_axis` — axis_row_d present in axes_setup.kv
11. `test_no_kv_rule_name_collisions` — no duplicate `<ClassName>:` headers across all KV files
12. `test_convex_load_kv_callable` — load_kv exported and callable

## Deviations from Plan

None — plan executed exactly as written.

## Pre-existing Failures (out of scope, logged)

Six test failures existed before this plan and remain unchanged:
- `tests/test_main_estop.py::TestEStop::test_estop_commands_order` (1 failure)
- `tests/test_status_bar.py::TestStatusBarStateLabel::*` (5 failures, Unicode display text mismatch)

These are not caused by this plan's changes.

## Self-Check

Files created:

- `src/dmccodegui/screens/convex/__init__.py` — EXISTS
- `src/dmccodegui/screens/convex/run.py` — EXISTS
- `src/dmccodegui/screens/convex/axes_setup.py` — EXISTS
- `src/dmccodegui/screens/convex/parameters.py` — EXISTS
- `src/dmccodegui/screens/convex/widgets.py` — EXISTS
- `src/dmccodegui/ui/convex/run.kv` — EXISTS
- `src/dmccodegui/ui/convex/axes_setup.kv` — EXISTS
- `src/dmccodegui/ui/convex/parameters.kv` — EXISTS
- `tests/test_convex_screens.py` — EXISTS

Commits:
- `22841df` — feat(22-01): convex package skeleton, thin subclasses, KV files, registry update
- `e073764` — test(22-01): add convex screen test scaffold (12 tests, all passing)

## Self-Check: PASSED
