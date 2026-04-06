---
phase: 13
slug: setup-loop
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/test_axes_setup.py tests/test_parameters.py tests/test_dmc_vars.py -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_axes_setup.py tests/test_parameters.py tests/test_dmc_vars.py -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 0 | SETP-01 | unit | `pytest tests/test_axes_setup.py -k "enter_setup" -x` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 0 | SETP-01 | unit | `pytest tests/test_axes_setup.py -k "skip_reenter" -x` | ❌ W0 | ⬜ pending |
| 13-01-03 | 01 | 0 | SETP-02 | unit | `pytest tests/test_axes_setup.py -k "home_all_fires_hmi" -x` | ❌ W0 | ⬜ pending |
| 13-01-04 | 01 | 0 | SETP-03 | unit | `pytest tests/test_axes_setup.py -k "jog_blocked_not_setup" -x` | ❌ W0 | ⬜ pending |
| 13-01-05 | 01 | 0 | SETP-03 | unit | `pytest tests/test_axes_setup.py -k "jog_blocked_in_progress" -x` | ❌ W0 | ⬜ pending |
| 13-01-06 | 01 | 0 | SETP-07 | unit | `pytest tests/test_parameters.py -k "apply_fires_calc" -x` | ❌ W0 | ⬜ pending |
| 13-01-07 | 01 | 0 | SETP-07 | unit | `pytest tests/test_parameters.py -k "apply_readback" -x` | ❌ W0 | ⬜ pending |
| 13-01-08 | 01 | 0 | SETP-08 | unit | `pytest tests/test_axes_setup.py -k "exit_setup_fires" -x` | ❌ W0 | ⬜ pending |
| 13-01-09 | 01 | 0 | SETP-08 | unit | `pytest tests/test_axes_setup.py -k "no_exit_sibling" -x` | ❌ W0 | ⬜ pending |
| 13-01-10 | 01 | 0 | SETP-08 | unit | `pytest tests/test_dmc_vars.py -k "go_rest or go_start or exit_setup" -x` | ❌ W0 | ⬜ pending |
| 13-02-01 | 02 | 1 | SETP-04 | unit | `pytest tests/test_axes_setup.py::test_teach_rest_burns_nv -x` | ✅ | ⬜ pending |
| 13-02-02 | 02 | 1 | SETP-05 | unit | `pytest tests/test_axes_setup.py::test_teach_start_burns_nv -x` | ✅ | ⬜ pending |
| 13-02-03 | 02 | 1 | SETP-06 | unit | `pytest tests/test_parameters.py -k "apply" -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_axes_setup.py` — add tests for: smart enter (SETP-01 guard), home_all HMI trigger (SETP-02), jog not-in-setup gate (SETP-03), jog in-progress gate (SETP-03), smart exit (SETP-08 fires / SETP-08 no-fire)
- [ ] `tests/test_parameters.py` — add tests for: apply_to_controller fires hmiCalc=0 (SETP-07), readback after delay (SETP-07 readback)
- [ ] `tests/test_dmc_vars.py` — add tests for three new constants: HMI_GO_REST, HMI_GO_START, HMI_EXIT_SETUP (name values, <=8 chars)

*Existing infrastructure covers framework and fixtures — no new test files needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Axes physically move to home positions | SETP-02 | Requires real controller + axes | Tap Home on HMI, observe all axes return to home |
| Axis physically moves on jog tap | SETP-03 | Requires real controller + axes | Tap jog +/- on any axis, observe movement |
| Teach Rest saves correct positions | SETP-04 | Requires real axis positions | Move axes, tap Teach Rest, verify restPt[] via terminal |
| Teach Start saves correct positions | SETP-05 | Requires real axis positions | Move axes, tap Teach Start, verify startPt[] via terminal |
| varcalc produces correct derived values | SETP-07 | Requires real DMC firmware | Edit pitch, apply, verify cpmA recalculated via terminal |
| 500ms wait sufficient for varcalc | SETP-07 | Hardware timing dependent | Apply params, verify readback values match expected |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
