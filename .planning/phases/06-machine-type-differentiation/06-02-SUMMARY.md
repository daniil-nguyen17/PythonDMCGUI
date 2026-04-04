---
phase: 06-machine-type-differentiation
plan: 02
subsystem: app-shell
tags: [machine-type, status-bar, picker, profiles, runtime-config]
dependency_graph:
  requires: [06-01]
  provides: [machine-type-selection-ui, first-launch-flow, dynamic-profiles]
  affects: [main.py, status_bar.py, profiles.py]
tech_stack:
  added: []
  patterns:
    - Kivy ModalView picker with role-gated access
    - Callback chaining for first-launch mandatory flow (no independent Clock.schedule_once)
    - Function-scoped machine_config imports (read at call time, not module level)
key_files:
  created: []
  modified:
    - src/dmccodegui/main.py
    - src/dmccodegui/screens/status_bar.py
    - src/dmccodegui/ui/status_bar.kv
    - src/dmccodegui/screens/profiles.py
    - tests/test_profiles.py
decisions:
  - "_show_startup_flow() chains picker->PIN via callback, not independent Clock calls (per RESEARCH.md Pitfall 5)"
  - "machine_config imported inside functions in profiles.py — reads live active type at call time (per RESEARCH.md Pitfall 2)"
  - "MachineTypePicker uses force=True for first-launch bypass of role check; role check applied on all voluntary taps"
  - "StatusBar machine_type_btn width 260dp, font 17sp — fits between user area and banner ticker"
metrics:
  duration_minutes: 4
  completed_date: "2026-04-04"
  tasks_completed: 2
  files_modified: 5
---

# Phase 06 Plan 02: Machine Type Selection UI Summary

Machine type picker wired into app shell: StatusBar displays active type, Setup/Admin can tap to change, first launch shows mandatory picker before PIN overlay, and profiles.py reads machine type dynamically at call time.

## Tasks Completed

| Task | Description | Commit | Key Files |
|------|-------------|--------|-----------|
| 1 | MachineTypePicker, StatusBar integration, first-launch flow | 4528637 | main.py, status_bar.py, status_bar.kv |
| 2 | Wire profiles.py to dynamic machine type, update test_profiles.py | 355b987 | profiles.py, tests/test_profiles.py |

## What Was Built

### Task 1: MachineTypePicker and StatusBar Machine Type Display

**StatusBar (status_bar.py):**
- Added `machine_type_text = StringProperty("No Machine Type")`
- Added `_machine_type_tap_cb` callback field
- Added `bind_machine_type_tap(cb)` — same pattern as `bind_user_tap()`
- Added `on_machine_type_tap()` — called from KV, invokes callback
- `update_from_state()` now reads `state.machine_type` with change detection

**StatusBar KV (status_bar.kv):**
- Added `machine_type_btn` Button (260dp wide, 17sp font) between user area and banner ticker
- Text binds to `root.machine_type_text`, `on_release` calls `root.on_machine_type_tap()`
- Dark navy background (0.08, 0.12, 0.22) matching app theme

**main.py:**
- Imports `dmccodegui.machine_config as mc` in both try/except import blocks
- `__init__`: calls `mc.init(settings_path)` where settings_path is `auth/settings.json`
- Added `_show_machine_type_picker(on_selected=None, force=False)`:
  - Role check: only "setup" or "admin" can open picker (force bypasses)
  - Creates ModalView with 3 large buttons (64dp, 20sp) — one per `mc.MACHINE_TYPES`
  - On selection: `mc.set_active_type()`, `state.machine_type = mtype`, `state.notify()`, dismiss, callback
- Added `_show_startup_flow()`:
  - If `not mc.is_configured()`: shows mandatory picker with `on_selected=lambda: _show_pin_on_start()`
  - If already configured: calls `_show_pin_on_start()` directly
- `build()`: calls `_show_startup_flow()` instead of `_show_pin_on_start()` for all connection paths
- `build()`: sets `state.machine_type = mc.get_active_type()` if already configured at startup
- `build()`: wires `status_bar.bind_machine_type_tap(lambda: self._show_machine_type_picker())`

### Task 2: profiles.py Dynamic Machine Type and test_profiles.py Update

**profiles.py:**
- Removed module-level `MACHINE_TYPE` constant
- Removed module-level `from dmccodegui.screens.parameters import PARAM_DEFS`
- Removed module-level `_PARAM_BY_VAR` dict
- `export_profile()`: `machine_type` parameter default changed from constant to `None`; reads `mc.get_active_type()` inside function when None
- `parse_profile_csv()`: builds local `_param_by_var` from `mc.get_param_defs()` at call time
- `validate_import()`: reads `mc.get_active_type()` and builds local `_param_by_var` from `mc.get_param_defs()` at call time
- `ProfilesScreen._run_export` and `_on_file_selected`: use `mc.get_param_defs()` instead of `PARAM_DEFS`

**test_profiles.py:**
- Removed `MACHINE_TYPE` from import block
- Added `import dmccodegui.machine_config as mc`
- Added `@pytest.fixture(autouse=True) _init_machine_config(tmp_path)` — calls `mc.init()` + `mc.set_active_type("4-Axes Flat Grind")` before each test
- `test_export_writes_machine_type`: uses `mc.get_active_type()` instead of `MACHINE_TYPE`
- `test_parse_returns_metadata`: uses `mc.get_active_type()` instead of `MACHINE_TYPE`
- `_valid_parsed()`: uses `mc.get_active_type()` instead of `MACHINE_TYPE`
- Added `test_validate_import_uses_active_type`: proves dynamic type reading by switching to Serration and verifying no errors

## Test Results

```
42 passed in 0.83s
  - 16 tests/test_machine_config.py (Plan 01 — unbroken)
  - 26 tests/test_profiles.py (25 original + 1 new)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] ProfilesScreen Kivy methods still referenced PARAM_DEFS**
- **Found during:** Task 2 — grep check after removing module-level import
- **Issue:** `_run_export()` and `_on_file_selected()` inside ProfilesScreen Kivy class used `PARAM_DEFS` directly, which would cause NameError at runtime
- **Fix:** Added `import dmccodegui.machine_config as mc` inside each closure (`_job()` lambdas) and replaced `PARAM_DEFS` with `mc.get_param_defs()`
- **Files modified:** `src/dmccodegui/screens/profiles.py`
- **Commit:** 355b987

**2. [Rule 3 - Blocking] Verification command used /tmp/ path (Unix) on Windows**
- **Found during:** Task 1 verification
- **Issue:** Plan verification used `/tmp/test_settings.json` which doesn't exist on Windows
- **Fix:** Used `tempfile.gettempdir()` in manual verification; plan command not changed (environment-specific)
- **Files modified:** None — runtime-only issue

## Self-Check: PASSED

Files verified present:
- src/dmccodegui/main.py: contains `mc.init`, `_show_machine_type_picker`, `_show_startup_flow`, `bind_machine_type_tap`
- src/dmccodegui/screens/status_bar.py: contains `machine_type_text`, `bind_machine_type_tap`, `on_machine_type_tap`
- src/dmccodegui/ui/status_bar.kv: contains `machine_type_btn`, `machine_type_text`
- src/dmccodegui/screens/profiles.py: no `MACHINE_TYPE` constant, no module-level `PARAM_DEFS`, `mc.get_active_type()` present
- tests/test_profiles.py: no `MACHINE_TYPE` import, `mc.get_active_type()` assertions, `_init_machine_config` fixture, `test_validate_import_uses_active_type` present

Commits verified:
- 4528637: feat(06-02): MachineTypePicker, StatusBar machine type display, first-launch flow
- 355b987: feat(06-02): wire profiles.py to dynamic machine type, update test_profiles.py
