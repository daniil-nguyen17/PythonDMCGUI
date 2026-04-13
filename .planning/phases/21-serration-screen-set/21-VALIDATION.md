---
phase: 21
slug: serration-screen-set
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/test_serration_screens.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_serration_screens.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 1 | SERR-01 | unit | `pytest tests/test_serration_screens.py::test_serration_run_screen_importable -x` | ❌ W0 | ⬜ pending |
| 21-01-02 | 01 | 1 | SERR-01 | unit | `pytest tests/test_serration_screens.py::test_serration_run_screen_no_d_axis -x` | ❌ W0 | ⬜ pending |
| 21-01-03 | 01 | 1 | SERR-01 | unit | `pytest tests/test_serration_screens.py::test_registry_points_to_serration_classes -x` | ❌ W0 | ⬜ pending |
| 21-01-04 | 01 | 1 | SERR-02 | unit | `pytest tests/test_serration_screens.py::test_serration_axes_setup_inherits_base -x` | ❌ W0 | ⬜ pending |
| 21-01-05 | 01 | 1 | SERR-02 | static | `pytest tests/test_serration_screens.py::test_serration_axes_setup_kv_no_d_axis -x` | ❌ W0 | ⬜ pending |
| 21-01-06 | 01 | 1 | SERR-03 | unit | `pytest tests/test_serration_screens.py::test_serration_params_no_d_axis_vars -x` | ❌ W0 | ⬜ pending |
| 21-01-07 | 01 | 1 | SERR-03 | unit | `pytest tests/test_serration_screens.py::test_serration_param_defs_has_numserr -x` | ❌ W0 | ⬜ pending |
| 21-01-08 | 01 | 1 | SERR-04 | unit | `pytest tests/test_serration_screens.py::test_bcomp_panel_importable -x` | ❌ W0 | ⬜ pending |
| 21-01-09 | 01 | 1 | SERR-04 | unit | `pytest tests/test_serration_screens.py::test_bcomp_panel_renders_rows -x` | ❌ W0 | ⬜ pending |
| 21-01-10 | 01 | 1 | ALL | static | `pytest tests/test_flat_grind_widgets.py::test_no_duplicate_kv_rule_headers -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_serration_screens.py` — stubs for SERR-01, SERR-02, SERR-03, SERR-04
- [ ] `src/dmccodegui/ui/serration/` directory — must exist before KV files can be loaded
- [ ] `src/dmccodegui/screens/serration/` directory — package root

*Existing infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| bComp read/write to DMC controller | SERR-04 | Requires hardware connection | Connect to Serration machine, verify bComp[] reads/writes match controller values |
| More/less stone arrows update startPtC | SERR-04 | Requires hardware connection | Press up/down arrows, verify startPtC value changes on controller |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
