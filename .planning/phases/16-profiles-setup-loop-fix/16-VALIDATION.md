---
phase: 16
slug: profiles-setup-loop-fix
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `pytest tests/test_profiles.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_profiles.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | SETP-01 | unit | `pytest tests/test_profiles.py::test_enter_skips_fire_when_already_setup -x` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | SETP-01 | unit | `pytest tests/test_profiles.py::test_enter_fires_when_not_in_setup -x` | ❌ W0 | ⬜ pending |
| 16-01-03 | 01 | 1 | SETP-08 | unit | `pytest tests/test_profiles.py::test_exit_fires_hmi_exit_setup -x` | ❌ W0 | ⬜ pending |
| 16-01-04 | 01 | 1 | SETP-08 | unit | `pytest tests/test_profiles.py::test_exit_does_not_send_hmiSetp -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_profiles.py` — add 4 new test functions for SETP-01 and SETP-08 (file exists, needs new tests added)

*Existing infrastructure covers all other phase requirements.*

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
