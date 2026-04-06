---
phase: 07-admin-and-user-management
plan: 01
subsystem: auth
tags: [crud, auth-manager, tab-bar, tdd]
dependency_graph:
  requires: []
  provides: [AuthManager.create_user, AuthManager.delete_user, AuthManager.update_user, AuthManager.get_all_users, TabBar.users-tab]
  affects: [07-02-PLAN.md]
tech_stack:
  added: []
  patterns: [TDD red-green, plain-JSON persistence, bullet-masked PIN display]
key_files:
  created: []
  modified:
    - src/dmccodegui/auth/auth_manager.py
    - tests/test_auth_manager.py
    - src/dmccodegui/screens/tab_bar.py
    - tests/test_tab_bar.py
decisions:
  - "create_user validates 4-6 digit PIN and uniqueness across all users before insertion"
  - "update_user runs all validation before any mutation — atomic check-then-apply pattern"
  - "update_user PIN duplicate check excludes self so setting same PIN is not an error"
  - "delete_user last-admin guard counts admin roles at deletion time, not cached"
  - "get_all_users uses U+2022 bullet repeated per PIN length for masked display"
  - "ROLE_TABS[admin] extended to include 'users' at the end — appended, not inserted"
metrics:
  duration_seconds: 122
  completed_date: "2026-04-06"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
---

# Phase 07 Plan 01: AuthManager CRUD and Users Tab Summary

**One-liner:** Full CRUD on users.json with validation guards via four new AuthManager methods, plus "users" tab registered for admin role in TabBar.

## What Was Built

### Task 1: AuthManager CRUD Methods (TDD)

Four methods added to `src/dmccodegui/auth/auth_manager.py`:

- `create_user(name, pin, role)` — validates non-empty name, unique name, 4-6 digit PIN, unique PIN; returns None on success or error string
- `delete_user(name)` — validates existence, blocks last-admin deletion; returns None or error string
- `update_user(name, new_name, new_pin, new_role, current_user)` — validates all changes before any mutation: self-demotion guard, last-admin demotion guard, PIN uniqueness excluding self, name uniqueness, last_user rename sync
- `get_all_users()` — returns list of `{name, role, pin_masked}` with bullet (U+2022) masking

29 tests in `tests/test_auth_manager.py` — all pass.

### Task 2: Users Tab in TabBar

- `ALL_TABS` extended with `("users", "Users")` as last entry
- `ROLE_TABS["admin"]` extended with `"users"` at the end
- `tests/test_tab_bar.py` mirror updated to match; `test_admin_tabs` assertion updated
- `TestUsersTabRoleVisibility` added: operator/setup excluded, admin included

11 tests in `tests/test_tab_bar.py` — all pass. Combined: 40/40.

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

- `update_user` PIN duplicate check excludes the user being updated so that "set same PIN as current" is valid rather than a false-duplicate error — matches the behavior specified in `test_update_user_pin_same_user_ok`
- All validation in `update_user` runs before any mutation to ensure atomicity — no partial updates on failure

## Self-Check

### Created files exist
- `.planning/phases/07-admin-and-user-management/07-01-SUMMARY.md` (this file)

### Commits exist

- `3edf40d` test(07-01): add failing CRUD tests for AuthManager — FOUND
- `90c0366` feat(07-01): implement AuthManager CRUD methods — FOUND
- `c439a75` feat(07-01): register users tab in TabBar for admin role — FOUND

## Self-Check: PASSED
