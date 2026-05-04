---
phase: 31
slug: bug-fixes-and-ui-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-04
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (519 tests collected) |
| **Config file** | pyproject.toml (pytest section) |
| **Quick run command** | `python -m pytest tests/test_mg_reader.py tests/test_display_preset.py tests/test_install_pi.py tests/test_main.py -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_mg_reader.py tests/test_display_preset.py tests/test_install_pi.py tests/test_main.py -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 31-01-01 | 01 | 1 | FIX-03 | unit | `python -m pytest tests/test_main.py -k angle -q` | ❌ W0 | ⬜ pending |
| 31-01-02 | 01 | 1 | FIX-03 | unit | `python -m pytest tests/test_main.py -k gl_backend -q` | ❌ W0 | ⬜ pending |
| 31-01-03 | 01 | 1 | FIX-03 | manual | n/a — AMD hardware soak | manual-only | ⬜ pending |
| 31-01-04 | 01 | 1 | FIX-04 | unit | `python -m pytest tests/test_mg_reader.py -k linux -q` | ❌ W0 (conditional) | ⬜ pending |
| 31-01-05 | 01 | 1 | FIX-04 | manual | n/a — Pi hardware required | manual-only | ⬜ pending |
| 31-01-06 | 01 | 1 | FIX-05 | unit | `python -m pytest tests/test_install_pi.py -k venv -q` | ✅ | ⬜ pending |
| 31-01-07 | 01 | 1 | FIX-05 | manual | n/a — Pi re-install | manual-only | ⬜ pending |
| 31-02-01 | 02 | 2 | UI-01 | unit | `python -m pytest tests/test_display_preset.py -q` | ✅ (needs update) | ⬜ pending |
| 31-02-02 | 02 | 2 | UI-01 | manual | visual 44dp audit | manual-only | ⬜ pending |
| 31-02-03 | 02 | 2 | UI-02 | manual | grep spacing values | manual-only | ⬜ pending |
| 31-02-04 | 02 | 2 | UI-02 | manual | tab switch visual test | manual-only | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_main.py` — add `test_angle_backend_env_set` (verifies KIVY_GL_BACKEND=angle_sdl2 on win32)
- [ ] `tests/test_main.py` — add `test_gl_backend_log_line` (verifies GL backend info logged at startup)
- [ ] `tests/test_mg_reader.py` — add `test_start_not_blocked_on_linux` (conditional: only if platform guard removed)
- [ ] `tests/test_display_preset.py` — update tests to reflect 7"/10" preset removal

*Existing infrastructure covers FIX-05 (test_install_pi.py:155 already tests venv idempotency).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 30-min AMD plot soak | FIX-03 | Hardware-dependent — requires AMD GPU machine | Launch app on AMD machine, run sustained grind cycle with live plot for 30+ min, confirm no crash |
| Pi MG subscription | FIX-04 | Hardware-dependent — requires Pi with Galil controller | Start app on Pi, run grind, check controller log box for MG messages |
| Pi re-install venv | FIX-05 | Hardware-dependent — requires Pi with existing install | Re-run install.sh on Pi with existing venv, verify packages preserved |
| 44dp visual audit | UI-01 | Visual — element sizes depend on rendering | Open each screen on 15.6" 1920x1080, verify all tap targets >= 44dp |
| Spacing token check | UI-02 | Visual + grep — confirm values map to 4/8/12/16/24dp scale | Grep all .kv files for dp values, verify against token scale |
| Tab switch stability | UI-02 | Visual — requires seeing screen transitions | Switch between all tabs, verify no elements jump position or change size |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
