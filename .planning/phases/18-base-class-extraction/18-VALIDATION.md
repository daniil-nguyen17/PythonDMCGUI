---
phase: 18
slug: base-class-extraction
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (from pyproject.toml [tool.pytest.ini_options]) |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_base_classes.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_base_classes.py tests/test_run_screen.py tests/test_axes_setup.py tests/test_parameters.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 0 | ARCH-01 | unit | `pytest tests/test_base_classes.py::test_base_class_inheritance -x` | ❌ W0 | ⬜ pending |
| 18-01-02 | 01 | 0 | ARCH-02 | unit | `pytest tests/test_base_classes.py::test_subscription_lifecycle -x` | ❌ W0 | ⬜ pending |
| 18-01-03 | 01 | 0 | ARCH-04 | static | `pytest tests/test_base_classes.py::test_no_lifecycle_in_kv -x` | ❌ W0 | ⬜ pending |
| 18-02-01 | 02 | 1 | ARCH-01 | unit | `pytest tests/test_run_screen.py -x` | ✅ | ⬜ pending |
| 18-02-02 | 02 | 1 | ARCH-01 | unit | `pytest tests/test_axes_setup.py -x` | ✅ | ⬜ pending |
| 18-02-03 | 02 | 1 | ARCH-01 | unit | `pytest tests/test_parameters.py -x` | ✅ | ⬜ pending |
| 18-03-01 | 03 | 1 | ARCH-01 | unit | `pytest tests/test_flat_grind_widgets.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_base_classes.py` — stubs for ARCH-01, ARCH-02, ARCH-04 (base class inheritance, subscription lifecycle, no lifecycle in KV)
- [ ] `tests/test_flat_grind_widgets.py` — stubs for DeltaCBarChart import after move to flat_grind_widgets.py

*Existing infrastructure: pytest + pyproject.toml configuration already present. No framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| App runs identically to v2.0 after refactor | ARCH-01 | Visual/behavioral equivalence requires human observation | Launch app, navigate all screens, verify no visual differences |
| Navigate away and back twice, check no duplicate callbacks | ARCH-02 | Requires observing log output during live navigation | Run app with logging, navigate Run/Axes/Params screens twice, check logs for zero duplicate callback lines |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
