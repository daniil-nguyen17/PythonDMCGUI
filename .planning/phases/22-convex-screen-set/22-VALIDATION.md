---
phase: 22
slug: convex-screen-set
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (pyproject.toml: `[tool.pytest.ini_options] testpaths = ["tests"]`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/test_convex_screens.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_convex_screens.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 1 | CONV-01 | unit | `pytest tests/test_convex_screens.py::test_convex_run_screen_importable -x` | ❌ W0 | ⬜ pending |
| 22-01-02 | 01 | 1 | CONV-01 | unit | `pytest tests/test_convex_screens.py::test_convex_run_screen_has_all_4_axes -x` | ❌ W0 | ⬜ pending |
| 22-01-03 | 01 | 1 | CONV-01 | unit | `pytest tests/test_convex_screens.py::test_convex_adjust_panel_importable -x` | ❌ W0 | ⬜ pending |
| 22-01-04 | 01 | 1 | CONV-01 | unit | `pytest tests/test_convex_screens.py::test_registry_points_to_convex_classes -x` | ❌ W0 | ⬜ pending |
| 22-01-05 | 01 | 1 | CONV-02 | unit | `pytest tests/test_convex_screens.py::test_convex_axes_setup_importable -x` | ❌ W0 | ⬜ pending |
| 22-01-06 | 01 | 1 | CONV-02 | unit | `pytest tests/test_convex_screens.py::test_convex_axes_setup_kv_has_d_axis -x` | ❌ W0 | ⬜ pending |
| 22-01-07 | 01 | 1 | CONV-03 | unit | `pytest tests/test_convex_screens.py::test_convex_params_importable -x` | ❌ W0 | ⬜ pending |
| 22-01-08 | 01 | 1 | CONV-04 | unit | `pytest tests/test_convex_screens.py::test_convex_param_defs_independent -x` | ❌ W0 | ⬜ pending |
| 22-01-09 | 01 | 1 | CONV-04 | unit | `pytest tests/test_convex_screens.py::test_convex_param_defs_has_placeholder_comment -x` | ❌ W0 | ⬜ pending |
| 22-01-10 | 01 | 1 | All | unit | `pytest tests/test_convex_screens.py::test_no_kv_rule_name_collisions -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_convex_screens.py` — stubs for CONV-01 through CONV-04
- [ ] `src/dmccodegui/screens/convex/__init__.py` — package skeleton
- [ ] `src/dmccodegui/ui/convex/` — directory with KV files

*Existing test infrastructure — pytest, conftest.py, Kivy env vars pattern — fully covers all other infrastructure needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ConvexAdjustPanel visual layout in left column | CONV-01 | Visual positioning cannot be unit-tested | Launch app, connect as convex, verify panel appears between DeltaC chart and more/less stone |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
