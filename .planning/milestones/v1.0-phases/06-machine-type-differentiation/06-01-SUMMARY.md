---
phase: "06-machine-type-differentiation"
plan: "01"
subsystem: "machine-config"
tags: [machine-type, registry, persistence, app-state, tdd]

dependency_graph:
  requires: []
  provides: [machine_config_module, machine_state_machine_type]
  affects: [06-02, 06-03]

tech_stack:
  added: []
  patterns: [json-persistence, registry-dict, tdd-red-green]

key_files:
  created:
    - src/dmccodegui/machine_config.py
    - tests/test_machine_config.py
  modified:
    - src/dmccodegui/app_state.py

decisions:
  - "Convex and Serration param_defs are stubs (copies/subsets of Flat) — real DMC variable lists to be provided by customer later"
  - "Serration param_defs excludes D-axis vars (fdD, pitchD, ratioD, ctsRevD)"
  - "_REGISTRY keyed by type string, plug-in friendly — each type owns its complete param_defs list"
  - "machine_type field added to MachineState with str = '' default to preserve backward compatibility"
  - "settings.json merges with existing file content rather than overwriting to protect other settings"

metrics:
  duration_seconds: 103
  completed_date: "2026-04-04"
  tasks_completed: 2
  files_modified: 3
---

# Phase 6 Plan 01: Machine Config Registry + MachineState Extension Summary

**One-liner:** JSON-persisted machine type registry with axis lists, has_bcomp flags, and param_defs stubs for all three grinder variants, backed by 16 passing TDD tests.

## What Was Built

`machine_config.py` — the single source of truth for machine type data. Provides:

- `MACHINE_TYPES`: ordered list of 3 type strings
- `_REGISTRY`: internal dict keyed by type, each entry containing `axes`, `has_bcomp`, `param_defs`
- `init(settings_path)`: loads or creates settings.json, reads back persisted type
- `get_active_type()`, `set_active_type()`, `is_configured()`: active-type state management
- `get_param_defs()`, `get_axis_list()`, `is_serration()`: query API (all accept optional `mtype` arg)
- `_save()`: JSON persistence mirroring the AuthManager pattern; merges with existing file data

`app_state.py` extended with `machine_type: str = ""` field so MachineState can propagate the active type via `notify()` to all subscribers.

`tests/test_machine_config.py` — 16 tests covering registry completeness, axis lists per type, is_serration, has_bcomp flags, param_defs structure, flat-grind match against parameters.py, fresh-init unconfigured, unknown-type ValueError, persistence roundtrip, and MachineState field + notify behavior.

## Tasks Completed

| Task | Type | Description | Commit |
|------|------|-------------|--------|
| RED  | test | Failing tests for machine_config + MachineState | 66829f9 |
| GREEN | feat | machine_config.py implementation + app_state.py extension | 5e579e0 |

## Success Criteria Check

- [x] All 16 tests pass (`pytest tests/test_machine_config.py -v`)
- [x] machine_config.py exports all 8 public functions (MACHINE_TYPES + 7 functions)
- [x] MachineState.machine_type field exists with "" default
- [x] Settings roundtrip works (write + re-init reads same type)
- [x] No Kivy dependency in machine_config.py (pure Python, runs headless)

## Deviations from Plan

**1. [Rule 2 - Enhancement] Extra test for is_serration False on Convex**

- Found during: RED phase
- Issue: Plan listed `test_is_serration_false_flat` but not a symmetric test for Convex
- Fix: Added `test_is_serration_false_convex` as the natural counterpart (total: 16 tests vs 15 planned)
- Files modified: tests/test_machine_config.py
- Commit: 66829f9

No other deviations — plan executed exactly as written.
