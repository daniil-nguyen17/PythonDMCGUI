---
phase: 2
slug: run-page
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing — tests/ directory with conftest.py) |
| **Config file** | none — runs with `pytest` from project root |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | 01 | 0 | RUN-02 | unit | `pytest tests/test_run_screen.py::test_no_estop_in_run_bar -x` | ❌ W0 | ⬜ pending |
| TBD | 01 | 0 | RUN-03 | unit | `pytest tests/test_run_screen.py::test_axis_positions_disconnected -x` | ❌ W0 | ⬜ pending |
| TBD | 01 | 0 | RUN-04 | unit | `pytest tests/test_run_screen.py::test_cycle_status_machine_type -x` | ❌ W0 | ⬜ pending |
| TBD | 01 | 0 | RUN-05 | unit | `pytest tests/test_run_screen.py::test_progress_and_eta -x` | ❌ W0 | ⬜ pending |
| TBD | 01 | 0 | RUN-06 | unit | `pytest tests/test_run_screen.py::test_delta_c_adjustment -x` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | RUN-01 | manual | N/A — visual: 44dp+ buttons, layout | N/A | ⬜ pending |
| TBD | 01 | 1 | RUN-03 | unit | `pytest tests/test_run_screen.py::test_axis_positions_disconnected -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_run_screen.py` — stubs for RUN-02, RUN-03, RUN-04, RUN-05, RUN-06 (Knife Grind)
- [ ] `tests/test_delta_c_bar_chart.py` — unit tests for DeltaCBarChart widget logic (offset math, section division, writable range)
- [ ] `tests/test_machine_state_cycle.py` — covers new cycle fields on MachineState (cycle_tooth, cycle_running, cycle_completion_pct, ETA calculation)

*Kivy-free pure-logic tests (MachineState, DeltaCBarChart math) can run headless. Screen/widget integration tests needing Kivy event loop require appropriate mocking or manual verification.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Start/Pause/Go to Rest buttons 44dp+ and touch-friendly | RUN-01 | Kivy widget size requires running UI for dp → pixel verification | Launch app, navigate to RUN page, verify buttons are large and tappable |
| E-STOP visually dominant and isolated in StatusBar | RUN-02 | Visual dominance is subjective; layout isolation verified by screen structure | Verify E-STOP is in StatusBar (persistent), not in RunScreen bottom bar |
| Full layout matches mockup grid structure | All | Visual fidelity requires human review against mockup | Compare running RUN page side-by-side with mockups/run_page.html |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
