---
phase: 15
slug: run-page-missing-controls
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — invoked directly |
| **Quick run command** | `pytest tests/test_run_screen.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_run_screen.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 0 | (layout) | unit | `pytest tests/test_run_screen.py::test_run_screen_has_start_pt_c -x` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 0 | (layout) | unit | `pytest tests/test_run_screen.py::test_read_start_pt_c_submits_job -x` | ❌ W0 | ⬜ pending |
| 15-01-03 | 01 | 0 | (layout) | unit | `pytest tests/test_run_screen.py::test_more_stone_updates_start_pt_c -x` | ❌ W0 | ⬜ pending |
| 15-01-04 | 01 | 0 | (layout) | unit | `pytest tests/test_run_screen.py::test_less_stone_updates_start_pt_c -x` | ❌ W0 | ⬜ pending |
| 15-01-05 | 01 | 1 | (layout) | unit | `pytest tests/test_run_screen.py -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_run_screen.py::test_run_screen_has_start_pt_c` — covers new StringProperty default
- [ ] `tests/test_run_screen.py::test_read_start_pt_c_submits_job` — covers on_pre_enter read
- [ ] `tests/test_run_screen.py::test_more_stone_updates_start_pt_c` — covers label update after more stone
- [ ] `tests/test_run_screen.py::test_less_stone_updates_start_pt_c` — covers label update after less stone

*All four are new test functions added to the existing `tests/test_run_screen.py` file. No new test files needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Stone Compensation card visual match (border, radius, colors) | layout | Canvas rendering requires visual inspection | Launch app, navigate to Run page, verify card matches Cycle Status and Axis Positions style |
| Button touch targets ≥44dp | layout | Physical size requires device/emulator | Measure button height in Kivy inspector or visual check |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
