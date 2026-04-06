---
phase: 01-auth-and-navigation
plan: 01
subsystem: auth
tags: [auth, data-layer, tdd, pytest]
dependency_graph:
  requires: []
  provides: [auth-manager, machine-state-auth]
  affects: [01-02, 01-03, 01-04]
tech_stack:
  added: [pytest]
  patterns: [dataclass-extension, json-persistence, tdd-red-green]
key_files:
  created:
    - src/dmccodegui/auth/__init__.py
    - src/dmccodegui/auth/auth_manager.py
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_auth_manager.py
    - tests/test_app_state.py
  modified:
    - src/dmccodegui/app_state.py
    - pyproject.toml
decisions:
  - "AuthManager stores users in a plain JSON dict (no sqlite, no hashing) per project decision"
  - "MachineState auth fields added as dataclass fields with default values to preserve backward compat"
  - "setup_unlocked derived from role in set_auth() — not a separate stored value"
metrics:
  duration: "~2 minutes"
  completed_date: "2026-04-04"
  tasks_completed: 2
  files_created: 6
  files_modified: 2
---

# Phase 1 Plan 1: AuthManager and MachineState Auth Foundation Summary

**One-liner:** Plain-Python AuthManager (JSON PIN store) plus MachineState auth fields with TDD — 16 tests green.

## What Was Built

### AuthManager (`src/dmccodegui/auth/auth_manager.py`)

PIN validation against a `users.json` file. On first boot the file is created with three default users: Admin (0000), Operator (1234), Setup (5678). `validate_pin(username, pin)` returns the role string on success or `None` on failure; successful logins persist `last_user` to disk so the next boot pre-selects the right user. `user_names` and `last_user` are read-only properties.

### MachineState auth extension (`src/dmccodegui/app_state.py`)

Three new fields added to the existing dataclass: `current_user: str`, `current_role: str`, `setup_unlocked: bool`. Two new methods: `set_auth(user, role)` derives `setup_unlocked` from the role and calls `notify()`; `lock_setup()` clears `setup_unlocked` and calls `notify()`. All existing fields and methods are untouched.

### Test infrastructure (`tests/`)

`conftest.py` provides a `tmp_users_path` fixture. 8 AuthManager tests and 8 MachineState tests — 16 total, all green.

## Decisions Made

- AuthManager stores users in plain JSON with plain-text PINs per the locked project decision (no hashing, no sqlite).
- `setup_unlocked` is derived at call time in `set_auth()` rather than being persisted separately — simpler and correct.
- MachineState auth fields use dataclass defaults so all existing construction sites (`MachineState()`) continue to work without changes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Import] Python path collision with another project**
- **Found during:** Task 1 GREEN phase
- **Issue:** Python was resolving `dmccodegui.auth` to a different project installed in site-packages (`Binh-An-App` worktree). Tests collected 0 items and failed with ImportError.
- **Fix:** Ran `pip install -e .` to install the current project in editable mode, which places `src/` at the front of the package resolution order.
- **Files modified:** None (system-level fix)
- **Commit:** Part of Task 1 execution (no separate commit needed — fix is structural)

## Self-Check

- [x] `src/dmccodegui/auth/__init__.py` exists
- [x] `src/dmccodegui/auth/auth_manager.py` exists (80 lines, > 40 minimum)
- [x] `src/dmccodegui/app_state.py` modified (auth fields + set_auth + lock_setup)
- [x] `tests/test_auth_manager.py` exists (8 tests, > 30 lines minimum)
- [x] `tests/test_app_state.py` exists (8 tests, > 20 lines minimum)
- [x] All 16 tests pass: `python -m pytest tests/ -v` — 16 passed
- [x] Task 1 commit: `7ed70f5`
- [x] Task 2 commit: `076e76e`
