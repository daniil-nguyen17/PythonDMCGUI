---
phase: 7
slug: admin-and-user-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | pyproject.toml (project root) |
| **Quick run command** | `pytest tests/test_auth_manager.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_auth_manager.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | AUTH-07 | unit | `pytest tests/test_auth_manager.py::test_create_user -x` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | AUTH-07 | unit | `pytest tests/test_auth_manager.py::test_create_user_duplicate_name -x` | ❌ W0 | ⬜ pending |
| 07-01-03 | 01 | 1 | AUTH-07 | unit | `pytest tests/test_auth_manager.py::test_create_user_duplicate_pin -x` | ❌ W0 | ⬜ pending |
| 07-01-04 | 01 | 1 | AUTH-07 | unit | `pytest tests/test_auth_manager.py::test_create_user_invalid_pin -x` | ❌ W0 | ⬜ pending |
| 07-01-05 | 01 | 1 | AUTH-07 | unit | `pytest tests/test_auth_manager.py::test_delete_user -x` | ❌ W0 | ⬜ pending |
| 07-01-06 | 01 | 1 | AUTH-07 | unit | `pytest tests/test_auth_manager.py::test_delete_last_admin_blocked -x` | ❌ W0 | ⬜ pending |
| 07-01-07 | 01 | 1 | AUTH-07 | unit | `pytest tests/test_auth_manager.py::test_update_user_pin -x` | ❌ W0 | ⬜ pending |
| 07-01-08 | 01 | 1 | AUTH-07 | unit | `pytest tests/test_auth_manager.py::test_update_self_role_blocked -x` | ❌ W0 | ⬜ pending |
| 07-01-09 | 01 | 1 | AUTH-07 | unit | `pytest tests/test_auth_manager.py::test_update_last_admin_demotion_blocked -x` | ❌ W0 | ⬜ pending |
| 07-02-01 | 02 | 2 | AUTH-08 | unit | `pytest tests/test_tab_bar.py -x` | ✅ (needs update) | ⬜ pending |
| 07-02-02 | 02 | 2 | AUTH-08 | unit | `pytest tests/test_tab_bar.py::TestTabsForRole::test_admin_tabs -x` | ✅ (needs update) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_auth_manager.py` — add test functions for CRUD methods (create, delete, update, validation, last-admin guard, self-demotion guard)
- [ ] `tests/test_tab_bar.py` — update `_tabs_for_role` mirror to include `"users"` in admin list, update `test_admin_tabs` assertion

*Existing infrastructure covers framework install — pytest already configured.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| UsersScreen layout renders correctly on touchscreen | AUTH-08 | Visual layout verification | Open app as Admin, navigate to Users tab, verify card layout and overlay positioning |
| Delete confirmation popup appears and functions | AUTH-07 | UI interaction flow | Tap Delete on a user card, verify popup, confirm deletion |
| Force-logout on self-deletion | AUTH-07 | End-to-end auth flow | Delete currently logged-in user, verify PIN overlay appears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
