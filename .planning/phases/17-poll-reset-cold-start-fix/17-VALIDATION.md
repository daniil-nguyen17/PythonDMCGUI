---
phase: 17
slug: poll-reset-cold-start-fix
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `pytest tests/test_poll.py tests/test_status_bar.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_poll.py tests/test_status_bar.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 0 | POLL-03 | unit | `pytest tests/test_poll.py::TestPollerStopResetsFailCount -x` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 0 | UI-02 | unit | `pytest tests/test_poll.py::TestColdStartStatusBar -x` | ❌ W0 | ⬜ pending |
| 17-01-03 | 01 | 0 | UI-02 | unit | `pytest tests/test_status_bar.py -k recover_chain -x` | ❌ W0 | ⬜ pending |
| 17-01-04 | 01 | 0 | UI-02 | unit | `pytest tests/test_poll.py::TestProgramRunningDefault -x` | ✅ (update) | ⬜ pending |
| 17-01-05 | 01 | 1 | POLL-03 | unit | `pytest tests/test_poll.py::TestPollerStopResetsFailCount -x` | ❌ W0 | ⬜ pending |
| 17-01-06 | 01 | 1 | UI-02 | unit | `pytest tests/test_poll.py::TestColdStartStatusBar -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `TestPollerStopResetsFailCount` class in `tests/test_poll.py` — stubs for POLL-03 fail_count/disconnect_start reset
- [ ] `TestColdStartStatusBar` class in `tests/test_poll.py` — stubs for UI-02 cold-start OFFLINE
- [ ] `test_recover_enabled_chain` in `tests/test_status_bar.py` — stubs for UI-02 RECOVER chain
- [ ] Update `TestProgramRunningDefault` assertion — flip to assertTrue after default change

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
