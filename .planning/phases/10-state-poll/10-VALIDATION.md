---
phase: 10
slug: state-poll
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (from pyproject.toml `[tool.pytest.ini_options]`) |
| **Config file** | `pyproject.toml` — `testpaths = ["tests"]` |
| **Quick run command** | `pytest tests/test_app_state.py tests/test_dmc_vars.py tests/test_machine_state_cycle.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_app_state.py tests/test_dmc_vars.py tests/test_machine_state_cycle.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 0 | POLL-01 | unit | `pytest tests/test_poll.py::test_poller_writes_dmc_state -x` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 0 | POLL-01 | unit | `pytest tests/test_app_state.py::test_cycle_running_derived_from_dmc_state -x` | ❌ W0 | ⬜ pending |
| 10-01-03 | 01 | 0 | POLL-02 | unit | `pytest tests/test_poll.py::test_poller_writes_positions -x` | ❌ W0 | ⬜ pending |
| 10-01-04 | 01 | 0 | POLL-03 | unit | `pytest tests/test_poll.py::test_disconnect_after_three_failures -x` | ❌ W0 | ⬜ pending |
| 10-01-05 | 01 | 0 | POLL-03 | unit | `pytest tests/test_poll.py::test_reconnect_clears_disconnect -x` | ❌ W0 | ⬜ pending |
| 10-01-06 | 01 | 0 | POLL-04 | unit | `pytest tests/test_app_state.py::test_knife_count_fields -x` | ❌ W0 | ⬜ pending |
| 10-01-07 | 01 | 0 | POLL-04 | unit | `pytest tests/test_poll.py::test_poller_writes_knife_counts -x` | ❌ W0 | ⬜ pending |
| 10-01-08 | 01 | 0 | POLL-02 | unit | `pytest tests/test_dmc_vars.py::TestKnifeCountConstants -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_poll.py` — stubs for POLL-01, POLL-02, POLL-03, POLL-04 poller behavior with mock controller
- [ ] `tests/test_app_state.py` needs new test methods: `test_cycle_running_derived_from_dmc_state`, `test_knife_count_fields`
- [ ] `tests/test_dmc_vars.py` needs new test class: `TestKnifeCountConstants` (CT_SES_KNI, CT_STN_KNI)

*Existing infrastructure covers framework and fixtures; only new test files/methods needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Axis positions update within 200ms on real hardware | POLL-02 | Requires physical controller + axes | Jog axes from DMC terminal, observe RunScreen labels |
| Network cable disconnect detected within 2s | POLL-03 | Requires physical network disruption | Unplug cable, verify HMI shows disconnected status |
| Reconnect resumes polling without restart | POLL-03 | Requires physical reconnection | Replug cable, verify HMI resumes position updates |
| Knife count matches controller query | POLL-04 | Requires running DMC program | Run grind cycle, compare RunScreen label with `MG ctSesKni` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
