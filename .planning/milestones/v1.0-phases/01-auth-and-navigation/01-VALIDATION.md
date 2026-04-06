---
phase: 1
slug: auth-and-navigation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (declared in pyproject.toml dev deps) |
| **Config file** | None — Wave 0 adds `[tool.pytest.ini_options]` to pyproject.toml |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | AUTH-02 | unit | `pytest tests/test_auth_manager.py::test_last_user_persistence -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 0 | AUTH-03 | unit | `pytest tests/test_auth_manager.py::test_validate_pin -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 0 | AUTH-06 | unit | `pytest tests/test_app_state.py::test_lock_setup -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 0 | NAV-04 | unit | `pytest tests/test_app_state.py::test_connection_status -x` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 0 | NAV-05 | unit | `pytest tests/test_app_state.py::test_set_auth -x` | ❌ W0 | ⬜ pending |
| 1-01-06 | 01 | 0 | AUTH-04 | unit | `pytest tests/test_tab_bar.py::test_operator_tabs -x` | ❌ W0 | ⬜ pending |
| 1-01-07 | 01 | 0 | NAV-03 | unit | `pytest tests/test_tab_bar.py::test_role_tab_counts -x` | ❌ W0 | ⬜ pending |
| 1-01-08 | 01 | 0 | UI-04 | unit | `pytest tests/test_main.py::test_no_transition -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — package init
- [ ] `tests/test_auth_manager.py` — stubs for AUTH-02, AUTH-03
- [ ] `tests/test_app_state.py` — stubs for AUTH-06, NAV-04, NAV-05
- [ ] `tests/test_tab_bar.py` — stubs for AUTH-04, NAV-03
- [ ] `tests/test_main.py` — stubs for UI-04
- [ ] `tests/conftest.py` — shared fixtures (mock AuthManager, mock MachineState)
- [ ] Add `[tool.pytest.ini_options] testpaths = ["tests"]` to pyproject.toml

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PIN overlay opens on startup; numpad input produces masked dots | AUTH-01 | Requires Kivy display/event loop | Launch app → verify overlay appears → tap digits → confirm dots |
| Setup role taps restricted tab → PIN overlay opens | AUTH-05 | Requires Kivy touch event pipeline | Log in as Setup → tap restricted tab → verify PIN overlay |
| TabBar renders visible buttons matching role | NAV-01 | Visual layout verification | Log in as each role → visually confirm correct tabs |
| E-STOP button exists in StatusBar | NAV-02 | Visual presence check | Launch app → verify E-STOP visible on all screens |
| Dark palette constants used in new KV files | UI-01 | Visual theming check | Inspect app appearance against dark palette spec |
| Axis colors unchanged in theme.kv | UI-02 | Visual regression | Compare axis colors before/after changes |
| All buttons height >= 44dp in new KV | UI-03 | Touch target sizing | Inspect button sizes on target display |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
