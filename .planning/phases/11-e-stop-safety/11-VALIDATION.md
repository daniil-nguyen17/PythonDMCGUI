---
phase: 11
slug: e-stop-safety
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (installed in dev extras) |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options] testpaths = ["tests"]` |
| **Quick run command** | `pytest tests/test_jobs.py tests/test_app_state.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_jobs.py tests/test_app_state.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 0 | SAFE-01 | unit | `pytest tests/test_jobs.py::test_submit_urgent_runs_before_normal -x` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 0 | SAFE-01 | unit | `pytest tests/test_jobs.py::test_submit_urgent_sets_cancel_event -x` | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 0 | SAFE-01 | unit | `pytest tests/test_main_estop.py::test_estop_uses_submit_urgent -x` | ❌ W0 | ⬜ pending |
| 11-01-04 | 01 | 0 | SAFE-01 | unit | `pytest tests/test_main_estop.py::test_estop_commands -x` | ❌ W0 | ⬜ pending |
| 11-01-05 | 01 | 0 | SAFE-01 | unit | `pytest tests/test_main_estop.py::test_estop_stays_connected -x` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 1 | SAFE-02 | unit | `pytest tests/test_run_screen.py::test_stop_sends_st_only -x` | ❌ new | ⬜ pending |
| 11-03-01 | 03 | 1 | SAFE-03 | unit | `pytest tests/test_run_screen.py::test_motion_gate_grinding -x` | ❌ new | ⬜ pending |
| 11-03-02 | 03 | 1 | SAFE-03 | unit | `pytest tests/test_run_screen.py::test_motion_gate_homing -x` | ❌ new | ⬜ pending |
| 11-03-03 | 03 | 1 | SAFE-03 | unit | `pytest tests/test_run_screen.py::test_motion_gate_disconnected -x` | ❌ new | ⬜ pending |
| 11-03-04 | 03 | 1 | SAFE-03 | unit | `pytest tests/test_run_screen.py::test_motion_gate_idle -x` | ❌ new | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_jobs.py` — stubs for SAFE-01 submit_urgent behavior (new file)
- [ ] `tests/test_main_estop.py` — stubs for SAFE-01 e_stop() behavior (new file)
- [ ] `tests/test_run_screen.py` — add SAFE-02 and SAFE-03 test stubs to existing file

*Existing `test_app_state.py` and `test_poll.py` cover Phase 10 and need no changes for Phase 11.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| E-STOP halts motion within 200ms | SAFE-01 | Requires hardware timing measurement | 1. Start grind cycle 2. Press E-STOP 3. Measure axis stop time via controller response |
| GClose+GOpen handle reset maintains connection | SAFE-01 | Requires hardware validation | 1. Connect to controller 2. Trigger E-STOP 3. Verify cmd() works after reset |
| _XQ returns -1 immediately after HX | SAFE-01/02 | Galil firmware-specific timing | 1. Run program 2. Send HX 3. Read _XQ immediately |
| RECOVER XQ #AUTO restarts program correctly | SAFE-01 | Requires DMC program with #AUTO label | 1. E-STOP to kill program 2. Press RECOVER 3. Verify program restarts from #AUTO |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
