---
phase: 28
slug: logging-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (pyproject.toml: `[tool.pytest.ini_options] testpaths = ["tests"]`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/test_logging.py tests/test_bundle_exclusions.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_logging.py tests/test_bundle_exclusions.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 28-01-01 | 01 | 1 | APP-01 | unit | `pytest tests/test_logging.py::test_log_file_created -x` | ❌ W0 | ⬜ pending |
| 28-01-02 | 01 | 1 | APP-01 | unit | `pytest tests/test_logging.py::test_rotating_handler_config -x` | ❌ W0 | ⬜ pending |
| 28-01-03 | 01 | 1 | APP-01 | unit | `pytest tests/test_logging.py::test_log_format -x` | ❌ W0 | ⬜ pending |
| 28-01-04 | 01 | 1 | APP-01 | unit | `pytest tests/test_logging.py::test_linux_log_path -x` | ❌ W0 | ⬜ pending |
| 28-01-05 | 01 | 1 | APP-02 | unit | `pytest tests/test_logging.py::test_excepthook_patched -x` | ❌ W0 | ⬜ pending |
| 28-01-06 | 01 | 1 | APP-02 | unit | `pytest tests/test_logging.py::test_excepthook_logs_traceback -x` | ❌ W0 | ⬜ pending |
| 28-01-07 | 01 | 1 | APP-02 | unit | `pytest tests/test_logging.py::test_excepthook_keyboard_interrupt -x` | ❌ W0 | ⬜ pending |
| 28-02-01 | 02 | 1 | APP-03 | content-inspection | `pytest tests/test_bundle_exclusions.py::test_spec_no_md_files -x` | ❌ W0 | ⬜ pending |
| 28-02-02 | 02 | 1 | APP-03 | content-inspection | `pytest tests/test_bundle_exclusions.py::test_spec_no_planning_dir -x` | ❌ W0 | ⬜ pending |
| 28-02-03 | 02 | 1 | APP-03 | content-inspection | `pytest tests/test_bundle_exclusions.py::test_install_sh_excludes_noncritical -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_logging.py` — covers APP-01 and APP-02 (7 tests)
- [ ] `tests/test_bundle_exclusions.py` — covers APP-03 (3 tests)

*No framework or fixture gaps — pytest + existing conftest.py are sufficient.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Log file appears at correct APPDATA path on real Windows | APP-01 SC-1 | Requires frozen PyInstaller build on real Windows | Build installer, run on Windows, check %APPDATA%/BinhAnHMI/logs/app.log |
| Log file appears at ~/.binh-an-hmi/logs/ on real Pi | APP-01 SC-1 | Requires real Pi hardware | Deploy to Pi, run app, check log location |
| Windows bundle contains no .md/.xlsx/.dmc files | APP-03 SC-3 | Requires full PyInstaller build | Build bundle, scan output directory |

*Manual verifications deferred to Phase 29 (Integration Testing and Field Validation).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
