---
phase: 14-state-driven-ui
plan: "02"
subsystem: profiles-parameters-ui-gating
tags: [tdd, motion-gate, dmc-state, kivy, profiles, parameters]
dependency_graph:
  requires: [14-01]
  provides: [motion_active gating on ProfilesScreen import button, motion_active gating on ParametersScreen apply button]
  affects: [src/dmccodegui/screens/profiles.py, src/dmccodegui/screens/parameters.py]
tech_stack:
  added: []
  patterns: [motion_active gate using dmc_state, live subscription via state.subscribe + Clock.schedule_once]
key_files:
  created: []
  modified:
    - src/dmccodegui/screens/profiles.py
    - src/dmccodegui/screens/parameters.py
    - tests/test_profiles.py
    - tests/test_parameters.py
decisions:
  - motion_active gate checks not self.state.connected OR dmc_state in (GRINDING, HOMING) — disconnected treated as motion_active=True per Phase 11 decision
  - _update_apply_button uses _apply_btn attribute first, then falls back to ids.get('apply_btn') — matches existing _apply_role_mode pattern
  - test helpers use ids.update() to inject mock buttons into Kivy ObservableDict rather than replacing ids property (which is read-only in Kivy)
  - Pre-existing test failures fixed: test_apply_sends_dirty/burns_nv/reads_back were failing due to mc.get_param_defs() called without machine_config initialized — fixed with mc.get_param_defs patch
  - test_apply_skips_when_cycle_running renamed to test_apply_skips_when_motion_active with dmc_state=STATE_GRINDING
metrics:
  duration_minutes: 12
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_modified: 4
---

# Phase 14 Plan 02: Profiles and Parameters motion_active gating Summary

Motion_active gating wired on ProfilesScreen import button and ParametersScreen apply button using authoritative dmc_state instead of derived cycle_running flag.

## What Was Built

Both the import button on ProfilesScreen and the apply button on ParametersScreen are now disabled when:
- `dmc_state` is `STATE_GRINDING` (2)
- `dmc_state` is `STATE_HOMING` (4)
- `connected` is `False`

They re-enable when the state returns to `STATE_IDLE` or `STATE_SETUP` with `connected=True`.

Additionally, ParametersScreen now has live visual gating via a state subscription that fires `_update_apply_button()` on every poll tick.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rewire ProfilesScreen import button to motion_active gate | f402871 | profiles.py, test_profiles.py |
| 2 | Add live motion_active gate to Parameters Apply button | 4f75619 | parameters.py, test_parameters.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pre-existing test failures in test_parameters.py**
- **Found during:** Task 2
- **Issue:** `test_apply_sends_dirty`, `test_apply_burns_nv`, `test_apply_reads_back`, `test_read_clears_dirty` were all failing before this plan with `ValueError: Unknown machine type: ''` because `mc.get_param_defs()` is called in the outer scope of `apply_to_controller()` without machine_config being initialized in those tests
- **Fix:** Added `with patch('dmccodegui.screens.parameters.mc.get_param_defs', return_value=PARAM_DEFS)` to each affected test. Added `mc.is_configured` patch to `test_read_clears_dirty`
- **Files modified:** tests/test_parameters.py
- **Commit:** 4f75619

**2. [Rule 1 - Bug] test_apply_skips_when_cycle_running was semantically stale**
- **Found during:** Task 2
- **Issue:** The test used `state.cycle_running = True` to test blocking behavior, but my implementation replaced `cycle_running` with `dmc_state`-based check. The old test passed with old code but became invalid after the guard was rewritten
- **Fix:** Renamed to `test_apply_skips_when_motion_active` and updated to use `state.dmc_state = STATE_GRINDING` which accurately reflects the new gate
- **Files modified:** tests/test_parameters.py
- **Commit:** 4f75619

**3. [Rule 1 - Bug] Kivy ids ObservableDict cannot be replaced by attribute assignment**
- **Found during:** Task 1 (TDD RED → GREEN debugging)
- **Issue:** Test helper tried `screen.ids = mock_ids` to inject a mock button, but Kivy's `ids` is an `ObservableDict` property on the `Screen` class that ignores attribute assignment
- **Fix:** Changed test helper to use `screen.ids.update({'import_btn': btn})` which injects into the existing ObservableDict without replacing it
- **Files modified:** tests/test_profiles.py
- **Commit:** f402871

## Success Criteria Verification

- [x] Profile import button disabled during GRINDING, HOMING, and disconnected
- [x] Profile import button enabled during IDLE and SETUP
- [x] Parameters Apply button visually disabled during GRINDING, HOMING, and disconnected
- [x] Parameters Apply button enabled during IDLE and SETUP
- [x] Parameters Read from Controller always accessible (not gated)
- [x] apply_to_controller() guard uses motion_active (dmc_state), not cycle_running
- [x] _update_import_button() uses motion_active (dmc_state), not cycle_running
- [x] Live subscription updates apply button on state changes
- [x] Full test suite passes with no regressions (297 passed)

## Self-Check: PASSED

- profiles.py: FOUND
- parameters.py: FOUND
- test_profiles.py: FOUND
- test_parameters.py: FOUND
- commit 3970fa2: FOUND (test RED profiles)
- commit f402871: FOUND (feat profiles gate)
- commit d0ca741: FOUND (test RED parameters)
- commit 4f75619: FOUND (feat parameters gate)
