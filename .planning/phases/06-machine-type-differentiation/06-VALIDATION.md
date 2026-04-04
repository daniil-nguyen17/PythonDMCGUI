---
phase: 6
slug: machine-type-differentiation
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 06-01-01 | 01 | 0 | MACH-01 | unit | `pytest tests/test_machine_config.py::test_registry_has_all_types -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 0 | MACH-01 | unit | `pytest tests/test_machine_config.py::test_serration_axis_list -x` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 0 | MACH-01 | unit | `pytest tests/test_machine_config.py::test_is_serration -x` | ❌ W0 | ⬜ pending |
| 06-01-04 | 01 | 0 | MACH-01 | unit | `pytest tests/test_machine_config.py::test_persistence_roundtrip -x` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | MACH-02 | unit | `pytest tests/test_machine_config.py::test_param_defs_per_type -x` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 1 | MACH-02 | unit | `pytest tests/test_profiles.py::test_validate_import_uses_active_type -x` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 1 | MACH-03 | unit | `pytest tests/test_machine_config.py::test_unknown_type_raises -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_machine_config.py` — stubs for MACH-01, MACH-02, MACH-03 pure-Python logic
- [ ] `src/dmccodegui/machine_config.py` — the module itself (new file)

*Existing infrastructure — pytest via pyproject.toml, conftest.py, import-inside-function pattern — covers all other needs. No new framework install required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| D axis hidden on Serration AxesSetup | MACH-01 | Kivy widget visibility requires running app | Launch with Serration type, verify D button absent from sidebar |
| Delta-C vs bComp panel swap on RUN page | MACH-01 | Visual widget swap requires running app | Launch Flat (see Delta-C), launch Serration (see bComp) |
| Cycle status fields differ per type | MACH-01 | Visual layout check | Launch Serration — tooth/pass/depth visible; Flat — absent |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
