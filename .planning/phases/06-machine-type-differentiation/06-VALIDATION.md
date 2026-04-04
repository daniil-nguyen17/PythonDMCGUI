---
phase: 6
slug: machine-type-differentiation
status: draft
nyquist_compliant: true
created: 2026-04-04
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (pyproject.toml `[tool.pytest.ini_options]`) |
| **Config file** | `pyproject.toml` — `testpaths = ["tests"]` |
| **Quick run command** | `pytest tests/test_machine_config.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_machine_config.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | MACH-01 | unit | `pytest tests/test_machine_config.py::test_registry_has_all_types -x` | Created by Plan 01 (TDD) | pending |
| 06-01-02 | 01 | 1 | MACH-01 | unit | `pytest tests/test_machine_config.py::test_serration_axis_list -x` | Created by Plan 01 (TDD) | pending |
| 06-01-03 | 01 | 1 | MACH-01 | unit | `pytest tests/test_machine_config.py::test_is_serration -x` | Created by Plan 01 (TDD) | pending |
| 06-01-04 | 01 | 1 | MACH-01 | unit | `pytest tests/test_machine_config.py::test_persistence_roundtrip -x` | Created by Plan 01 (TDD) | pending |
| 06-02-01 | 02 | 2 | MACH-03 | unit | `pytest tests/test_profiles.py -x` | Existing (updated by Plan 02 Task 2) | pending |
| 06-02-02 | 02 | 2 | MACH-03 | unit | `pytest tests/test_profiles.py::TestValidateImport::test_validate_import_uses_active_type -x` | Created by Plan 02 Task 2 | pending |
| 06-03-01 | 03 | 2 | MACH-01 | import | `python -c "from dmccodegui.screens.run import BCompBarChart, DeltaCBarChart; print('OK')"` | Created by Plan 03 Task 1 | pending |

*Status: pending / green / red / flaky*

---

## Wave Structure

- **Wave 1 (Plan 01):** TDD plan creates `tests/test_machine_config.py` and `src/dmccodegui/machine_config.py`. All foundation tests written RED then GREEN.
- **Wave 2 (Plans 02, 03):** Wire machine type into app shell and adapt screens. Plan 02 Task 2 updates `tests/test_profiles.py` (adds `test_validate_import_uses_active_type`, replaces stale `MACHINE_TYPE` import with `mc.get_active_type()` calls).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| D axis hidden on Serration AxesSetup | MACH-01 | Kivy widget visibility requires running app | Launch with Serration type, verify D button absent from sidebar |
| Delta-C vs bComp panel swap on RUN page | MACH-01 | Visual widget swap requires running app | Launch Flat (see Delta-C), launch Serration (see bComp) |
| Cycle status fields differ per type | MACH-01 | Visual layout check | Launch Serration — tooth/pass/depth visible; Flat — absent |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands (no `|| echo` fallbacks)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 1 TDD plan creates all test files referenced by later waves
- [x] Plan 02 Task 2 creates `test_validate_import_uses_active_type`
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending execution
