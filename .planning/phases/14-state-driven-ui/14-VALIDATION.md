---
phase: 14
slug: state-driven-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | none — pytest auto-discovers tests/ |
| **Quick run command** | `python -m pytest tests/test_status_bar.py tests/test_tab_bar.py -x -q` |
| **Full suite command** | `python -m pytest -x -q` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_status_bar.py tests/test_tab_bar.py -x -q`
- **After every plan wave:** Run `python -m pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 8 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 0 | UI-02 | unit | `python -m pytest tests/test_status_bar.py -x -q` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 0 | UI-04 | unit | `python -m pytest tests/test_tab_bar.py -x -q` | ✅ extend | ⬜ pending |
| 14-01-03 | 01 | 1 | UI-02 | unit | `python -m pytest tests/test_status_bar.py -x -q` | ❌ W0 | ⬜ pending |
| 14-01-04 | 01 | 1 | UI-02 | unit | `python -m pytest tests/test_status_bar.py -x -q` | ❌ W0 | ⬜ pending |
| 14-02-01 | 02 | 1 | UI-03 | unit | `python -m pytest tests/test_main_estop.py -x -q` | ✅ extend | ⬜ pending |
| 14-03-01 | 03 | 1 | UI-04 | unit | `python -m pytest tests/test_tab_bar.py -x -q` | ✅ extend | ⬜ pending |
| 14-04-01 | 04 | 2 | UI-01 | unit | `python -m pytest tests/test_profiles.py -x -q` | ✅ | ⬜ pending |
| 14-04-02 | 04 | 2 | UI-01 | unit | `python -m pytest tests/test_parameters.py -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_status_bar.py` — stubs for UI-02: state_text per dmc_state, E-STOP vs OFFLINE, color properties
- [ ] Extend `tests/test_tab_bar.py` — stubs for UI-04: update_state_gates method tests

*Existing infrastructure covers UI-01, UI-05 requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Setup badge visible between StatusBar and content area | UI-03 | Visual layout positioning requires render | Run app, enter SETUP state, verify yellow bar appears between StatusBar and tabs |
| Connection indicator visible on every screen | UI-05 | Already implemented, visual confirmation | Navigate all screens while connected/disconnected |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 8s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
