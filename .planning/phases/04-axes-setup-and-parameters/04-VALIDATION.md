---
phase: 4
slug: axes-setup-and-parameters
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | none — run from project root |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

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
| 04-01-01 | 01 | 1 | AXES-01 | unit | `pytest tests/test_axes_setup.py::test_selected_axis_property -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | AXES-01 | unit | `pytest tests/test_axes_setup.py::test_select_axis -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | AXES-02 | unit | `pytest tests/test_axes_setup.py::test_position_properties -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | AXES-03 | unit | `pytest tests/test_axes_setup.py::test_jog_counts_calculation -x` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 1 | AXES-03 | unit | `pytest tests/test_axes_setup.py::test_step_mm -x` | ❌ W0 | ⬜ pending |
| 04-01-06 | 01 | 1 | AXES-04 | unit (mock controller) | `pytest tests/test_axes_setup.py::test_teach_rest_burns_nv -x` | ❌ W0 | ⬜ pending |
| 04-01-07 | 01 | 1 | AXES-06 | integration | manual-only (requires Kivy display) | n/a | ⬜ pending |
| 04-02-01 | 02 | 2 | PARAM-01 | unit | `pytest tests/test_parameters.py::test_param_groups_defined -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | PARAM-03 | unit | `pytest tests/test_parameters.py::test_invalid_input_flags_red -x` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 2 | PARAM-04 | unit | `pytest tests/test_parameters.py::test_dirty_tracking -x` | ❌ W0 | ⬜ pending |
| 04-02-04 | 02 | 2 | PARAM-05 | unit (mock controller) | `pytest tests/test_parameters.py::test_apply_sends_dirty -x` | ❌ W0 | ⬜ pending |
| 04-02-05 | 02 | 2 | PARAM-05 | unit (mock controller) | `pytest tests/test_parameters.py::test_apply_burns_nv -x` | ❌ W0 | ⬜ pending |
| 04-02-06 | 02 | 2 | PARAM-06 | unit (mock controller) | `pytest tests/test_parameters.py::test_read_clears_dirty -x` | ❌ W0 | ⬜ pending |
| 04-02-07 | 02 | 2 | PARAM-07 | unit | `pytest tests/test_parameters.py::test_operator_readonly -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_axes_setup.py` — stubs for AXES-01, AXES-02, AXES-03, AXES-04
- [ ] `tests/test_parameters.py` — stubs for PARAM-01, PARAM-03, PARAM-04, PARAM-05, PARAM-06, PARAM-07
- [ ] Both test files follow established pattern: deferred Kivy init with `KIVY_NO_ENV_CONFIG=1` and `KIVY_LOG_LEVEL=critical`

*Existing pytest infrastructure covers framework needs — no new install required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| AxesSetupScreen is in Setup/Admin role tabs | AXES-06 | Requires Kivy display loop for role-based tab visibility | 1. Run app 2. Log in as Setup user 3. Verify Axes Setup tab visible 4. Log in as Operator 5. Verify tab hidden |
| Quick action button DMC responses | AXES-05 | Requires live controller connection | 1. Connect to DMC 2. Tap "Go to Rest All" 3. Verify all axes move to rest positions |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
