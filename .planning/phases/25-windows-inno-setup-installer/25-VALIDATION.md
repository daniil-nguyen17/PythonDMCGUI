---
phase: 25
slug: windows-inno-setup-installer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-21
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (pyproject.toml `[tool.pytest.ini_options]`) |
| **Config file** | `pyproject.toml` — `testpaths = ["tests"]` |
| **Quick run command** | `pytest tests/test_installer.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_installer.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 25-W0-01 | W0 | 0 | WIN-03 | unit/content | `pytest tests/test_installer.py::test_iss_start_menu_shortcut -x` | ❌ W0 | ⬜ pending |
| 25-W0-02 | W0 | 0 | WIN-03 | unit/content | `pytest tests/test_installer.py::test_iss_desktop_shortcut -x` | ❌ W0 | ⬜ pending |
| 25-W0-03 | W0 | 0 | WIN-04 | unit/content | `pytest tests/test_installer.py::test_iss_appname_publisher -x` | ❌ W0 | ⬜ pending |
| 25-W0-04 | W0 | 0 | WIN-04 | unit/content | `pytest tests/test_installer.py::test_iss_appid -x` | ❌ W0 | ⬜ pending |
| 25-W0-05 | W0 | 0 | WIN-06 | unit/content | `pytest tests/test_installer.py::test_iss_startup_task_unchecked -x` | ❌ W0 | ⬜ pending |
| 25-W0-06 | W0 | 0 | WIN-06 | unit/content | `pytest tests/test_installer.py::test_iss_hkcu_run_key -x` | ❌ W0 | ⬜ pending |
| 25-W0-07 | W0 | 0 | WIN-03 | smoke | `pytest tests/test_installer.py::test_installer_exe_exists -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_installer.py` — stubs for WIN-03, WIN-04, WIN-06 via .iss content inspection (parse .iss as text, assert required patterns)
- [ ] Existing `tests/conftest.py` — may need fixture for .iss file path

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Shortcuts launch the app | WIN-03 | Requires Windows desktop environment | Install on clean VM, click Start Menu and Desktop shortcuts, verify app launches |
| Uninstaller removes all files | WIN-04 | Requires real Windows install/uninstall cycle | Install, then uninstall via Settings > Apps, verify Program Files cleaned, APPDATA preserved |
| Auto-start on login | WIN-06 | Requires Windows login cycle | Install with checkbox checked, reboot, verify app launches on login |
| Firewall rules created | CONTEXT | Requires admin Windows environment | Install, check `netsh advfirewall firewall show rule name="Binh An HMI - Galil DR"` |
| Firewall rules removed on uninstall | CONTEXT | Requires real uninstall | Uninstall, verify rules no longer present |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
