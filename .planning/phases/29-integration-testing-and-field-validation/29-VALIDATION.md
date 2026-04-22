---
phase: 29
slug: integration-testing-and-field-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (pyproject.toml config) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/ -q --tb=no` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -q --tb=no`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before hardware validation:** Full suite must be green (0 failures)
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 29-01-01 | 01 | 1 | FIX-02 | unit | `pytest tests/test_status_bar.py -x` | ✅ (failing) | ⬜ pending |
| 29-01-02 | 01 | 1 | FIX-02 | unit | `pytest tests/test_run_screen.py::test_motion_gate_homing -x` | ✅ (failing) | ⬜ pending |
| 29-01-03 | 01 | 1 | FIX-02 | unit | `pytest tests/test_screen_loader.py -x` | ✅ (failing) | ⬜ pending |
| 29-01-04 | 01 | 1 | PI-06 | content | manual review of deploy/pi/README.md | ❌ W0 | ⬜ pending |
| 29-01-05 | 01 | 1 | PI-06 | content | manual review of deploy/windows/README.md | ❌ W0 | ⬜ pending |
| 29-02-01 | 02 | 2 | FIX-02 | manual (hardware) | N/A — Windows installer + controller gate | N/A | ⬜ pending |
| 29-02-02 | 02 | 2 | PI-06 | manual (hardware) | N/A — Pi deployment methods gate | N/A | ⬜ pending |
| 29-02-03 | 02 | 2 | FIX-02 | manual (hardware) | N/A — Pi + controller Flat Grind gate | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `deploy/pi/README.md` — technician deployment guide covering all 3 PI-06 methods
- [ ] `deploy/windows/README.md` — Windows installer instructions
- [ ] Fix 17 pre-existing test failures (3 distinct bugs: status_bar Vietnamese strings, STATE_HOMING not handled, _BareApp missing _stop_dr)

*Existing test infrastructure is sufficient — no new test framework or fixtures needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Windows installer launches on clean PC with Defender | FIX-02 SC-1 | Requires physical clean Windows machine | Install .exe, launch, verify no AV/DLL errors |
| Flat Grind cycle on real controller (Windows) | FIX-02 SC-2 | Requires live Galil controller | Login, start Flat Grind, verify plot/buttons/state |
| Three Pi deployment methods boot to login | PI-06 SC-3 | Requires physical Pi + touchscreen | Test each method: USB/SCP, SD image, git clone |
| Flat Grind cycle on Pi with DR streaming | FIX-02 SC-4 | Requires Pi + controller | Connect controller, run Flat Grind, verify DR data |
| Display preset validation on real screens | Phase 27 tuning | Requires physical touchscreens | Check UI legibility on each screen size |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
