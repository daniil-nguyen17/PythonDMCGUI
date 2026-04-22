---
phase: 26
slug: pi-os-preparation-and-install-script
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (from pyproject.toml dev dependencies) |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` testpaths = ["tests"] |
| **Quick run command** | `pytest tests/test_data_dir.py tests/test_install_pi.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_data_dir.py tests/test_install_pi.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 26-01-01 | 01 | 0 | PI-01 | unit | `pytest tests/test_install_pi.py::test_requirements_pi_txt_exists -x` | ❌ W0 | ⬜ pending |
| 26-01-02 | 01 | 0 | PI-01 | unit | `pytest tests/test_install_pi.py::test_requirements_pi_txt_contains_kivy -x` | ❌ W0 | ⬜ pending |
| 26-01-03 | 01 | 0 | PI-04 | unit | `pytest tests/test_install_pi.py::test_install_sh_x11_first -x` | ❌ W0 | ⬜ pending |
| 26-01-04 | 01 | 0 | PI-05 | unit | `pytest tests/test_install_pi.py::test_install_sh_exists -x` | ❌ W0 | ⬜ pending |
| 26-01-05 | 01 | 0 | PI-05 | unit | `pytest tests/test_install_pi.py::test_install_sh_sections -x` | ❌ W0 | ⬜ pending |
| 26-01-06 | 01 | 0 | PI-05 | unit | `pytest tests/test_install_pi.py::test_install_sh_idempotent -x` | ❌ W0 | ⬜ pending |
| 26-02-01 | 02 | 1 | _get_data_dir | unit | `pytest tests/test_data_dir.py::test_linux_mode_returns_home_dir -x` | ❌ W0 | ⬜ pending |
| 26-01-07 | 01 | 0 | deploy files | unit | `pytest tests/test_install_pi.py::test_desktop_file_fields -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_install_pi.py` — stubs for PI-01, PI-04, PI-05 (new file, mirrors test_installer.py pattern)
- [ ] Add `test_linux_mode_returns_home_dir` to existing `tests/test_data_dir.py`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| install.sh runs on fresh Pi Bookworm | PI-05 | Requires real Pi hardware | Flash Bookworm 64-bit, transfer repo, run `sudo ./install.sh`, verify app launches |
| venv pip installs all deps on ARM | PI-01 | Requires real ARM hardware | After install.sh completes, activate venv, `python -c "import kivy; import matplotlib; import gclib"` |
| X11 session active after reboot | PI-04 | Requires real Pi with display | After install + reboot, verify `echo $XDG_SESSION_TYPE` returns "x11" |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
