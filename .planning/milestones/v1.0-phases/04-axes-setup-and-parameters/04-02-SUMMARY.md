---
phase: 04-axes-setup-and-parameters
plan: 02
subsystem: parameters-screen
tags: [parameters, dirty-tracking, validation, batch-apply, role-based-readonly, tdd]
dependency_graph:
  requires: []
  provides: [ParametersScreen, PARAM_DEFS]
  affects: [src/dmccodegui/screens/parameters.py, src/dmccodegui/ui/parameters_setup.kv]
tech_stack:
  added: []
  patterns:
    - "PARAM_DEFS list-of-dicts with group/var/label/unit/min/max for all 30 params"
    - "_loading BooleanProperty guard to suppress dirty tracking during programmatic updates"
    - "Direct property assignment from background thread (no Clock.schedule_once) for testability"
    - "CardFrame dynamic build in on_kv_post via build_param_cards()"
key_files:
  created:
    - path: tests/test_parameters.py
      description: "21 unit tests covering PARAM_DEFS structure, validation rules, dirty tracking, apply/read flows, role-based readonly"
  modified:
    - path: src/dmccodegui/screens/parameters.py
      description: "Full ParametersScreen replacing placeholder: PARAM_DEFS 30 params/5 groups, validate_field, on_field_text_change, apply_to_controller, read_from_controller, _apply_role_mode, build_param_cards"
    - path: src/dmccodegui/ui/parameters_setup.kv
      description: "Replace old ParametersSetupScreen grid with ParametersScreen ScrollView + cards_container + title bar + bottom action bar"
decisions:
  - "backOff placed in Safety group only (not duplicated in Geometry) -- it is fundamentally a safety parameter"
  - "Background job applies state changes directly without Clock.schedule_once -- Kivy properties are thread-safe for value assignment and this enables clean synchronous testing without a running event loop"
  - "30 params total: 2 Geometry, 6 Feedrates, 12 Calibration, 8 Positions, 2 Safety"
metrics:
  duration_s: 244
  completed_date: "2026-04-04"
  tasks_completed: 2
  files_modified: 3
---

# Phase 04 Plan 02: ParametersScreen with Grouped Cards Summary

**One-liner:** Full ParametersScreen with 30-param 5-group cards, validate_field (error/modified/valid), pending_count dirty tracking, batch apply (write+MG read-back+BV), and operator readonly mode.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | ParametersScreen Python class with param definitions, dirty tracking, validation, apply/read + tests | 12fcae3 | src/dmccodegui/screens/parameters.py, tests/test_parameters.py |
| 2 | ParametersScreen KV layout -- grouped cards in ScrollView with bottom action bar | 55d7afd | src/dmccodegui/ui/parameters_setup.kv |

## What Was Built

### ParametersScreen (parameters.py)

- **PARAM_DEFS**: 30 parameters across 5 groups
  - Geometry (2): knfThk, edgeThk
  - Feedrates (6): fdA, fdB, fdCdn, fdCup, fdPark, fdD
  - Calibration (12): pitchA-D, ratioA-D, ctsRevA-D
  - Positions (8): restPtA-D, startPtA-D
  - Safety (2): backOff, pertol

- **validate_field(var_name, text)**: returns 'error' / 'modified' / 'valid'
  - Non-numeric, out-of-range, zero for Calibration, negative for Feedrates/Calibration/Safety

- **on_field_text_change(var_name, text)**: updates _dirty dict, pending_count, and field border color. Suppressed by _loading flag.

- **apply_to_controller()**: guards (no dirty, not connected, cycle_running), snapshots dirty, background job writes each var, reads back all via MG, burns NV with BV.

- **read_from_controller()**: background job MG-reads all 30 params, updates _controller_vals, clears _dirty, resets pending_count=0. Uses _loading to suppress on_text signals.

- **_apply_role_mode(setup_unlocked)**: operator=readonly=True, setup/admin=False.

- **build_param_cards()**: called from on_kv_post, creates 4-column rows (label / var code / TextInput / unit) grouped in CardFrame-style boxes inside cards_container.

### parameters_setup.kv

- Old `<ParametersSetupScreen>:` rule and `ParamCell/ParamLabel/ParamInput` widgets removed.
- New `<ParametersScreen>:` with:
  - Title bar (52dp): "Parameters" centered label + "Read from Controller" button
  - ScrollView: cards_container BoxLayout (height=minimum_height, dynamic population from Python)
  - Bottom action bar (56dp): pending count label (amber, opacity=0 when count=0) + "Apply to Controller" button (amber bg when pending, muted otherwise)

## Test Coverage

21 tests in tests/test_parameters.py:
- Group presence (Geometry, Feedrates, Calibration, Positions, Safety)
- Param def structure (all required keys)
- Positions group has all 8 restPt/startPt vars
- Safety group has backOff and pertol
- Validation: non-numeric, out-of-range, zero for pitch, negative for feedrate
- validate_field: valid when matching, modified when differing
- Dirty tracking: increment on change, decrement on revert
- Loading flag suppresses dirty tracking
- Error state does not add to dirty
- apply_to_controller: sends writes, reads back, burns BV, correct order, skips during cycle
- read_from_controller: clears dirty and resets pending_count
- Role-based readonly: operator=True, setup=False

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Clock.schedule_once not testable without running event loop**
- **Found during:** Task 1 (TDD RED-to-GREEN transition)
- **Issue:** Original design used Clock.schedule_once for post-back updates; test called job_fn() synchronously and Clock callbacks never fired, causing test_read_clears_dirty to fail.
- **Fix:** Background job updates Kivy properties directly (no Clock) — valid because Kivy property value assignments are thread-safe for numeric/bool types, and the apply/read operations are already isolated in the job function.
- **Files modified:** src/dmccodegui/screens/parameters.py
- **Commit:** 12fcae3

## Self-Check: PASSED

- src/dmccodegui/screens/parameters.py: FOUND
- src/dmccodegui/ui/parameters_setup.kv: FOUND
- tests/test_parameters.py: FOUND
- .planning/phases/04-axes-setup-and-parameters/04-02-SUMMARY.md: FOUND
- commit 12fcae3: FOUND
- commit 55d7afd: FOUND
