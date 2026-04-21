---
phase: 24
slug: windows-pyinstaller-bundle
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-21
---

# Phase 24 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already installed, tests/ directory active) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` testpaths = ["tests"] |
| **Quick run command** | `python -m pytest tests/test_data_dir.py tests/test_version.py tests/test_auth_manager.py tests/test_machine_config.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_data_dir.py tests/test_version.py tests/test_auth_manager.py tests/test_machine_config.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Requirement Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| WIN-01 | App launches on clean Windows 11 from onedir bundle | smoke/manual | VM checklist (see Manual-Only below) | manual-only | ⬜ pending |
| WIN-02 | gclib DLL loads from bundle, controller connects | smoke/manual | VM checklist step 3 | manual-only | ⬜ pending |
| WIN-05 | _get_data_dir() returns APPDATA when frozen | unit | `python -m pytest tests/test_data_dir.py -x -q` | ❌ W0 | ⬜ pending |
| WIN-05 | users.json seeded to APPDATA on first launch | unit | `python -m pytest tests/test_auth_manager.py -x -q` | ✅ (extend) | ⬜ pending |
| WIN-07 | __version__ == '4.0.0' in __init__.py | unit | `python -m pytest tests/test_version.py -x -q` | ❌ W0 | ⬜ pending |
| WIN-07 | DMCApp.title contains 'Binh An HMI v4.0.0' | unit | part of test_version.py | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_data_dir.py` — covers WIN-05: `_get_data_dir()` returns APPDATA path when `sys.frozen=True`, local `auth/` path otherwise
- [ ] `tests/test_version.py` — covers WIN-07: `__version__ == '4.0.0'` in `__init__.py`, `DMCApp.title` contains version string

*Existing test infrastructure covers auth_manager and machine_config — no gaps there*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bundle launches on clean Windows 11 VM | WIN-01 | Requires real VM with no Python/SDK installed | 1. Copy onedir folder to VM. 2. Run BinhAnHMI.exe. 3. Verify PIN login screen appears. |
| gclib DLL loads and controller connects | WIN-02 | Requires real Galil controller + clean VM | 1. Run bundle on VM with controller connected. 2. Verify connection log matches dev environment. |
| EXE file properties show version | WIN-07 | Requires inspecting Windows file properties dialog | 1. Right-click BinhAnHMI.exe. 2. Properties > Details tab. 3. Verify version shows 4.0.0. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
