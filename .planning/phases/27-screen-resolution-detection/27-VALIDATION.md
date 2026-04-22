---
phase: 27
slug: screen-resolution-detection
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (pyproject.toml: `[tool.pytest.ini_options] testpaths = ["tests"]`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/test_display_preset.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_display_preset.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 27-01-01 | 01 | 1 | APP-04 | unit | `pytest tests/test_display_preset.py::test_classify_7inch -x` | ❌ W0 | ⬜ pending |
| 27-01-02 | 01 | 1 | APP-04 | unit | `pytest tests/test_display_preset.py::test_classify_10inch -x` | ❌ W0 | ⬜ pending |
| 27-01-03 | 01 | 1 | APP-04 | unit | `pytest tests/test_display_preset.py::test_classify_15inch -x` | ❌ W0 | ⬜ pending |
| 27-01-04 | 01 | 1 | APP-04 | unit | `pytest tests/test_display_preset.py::test_classify_ambiguous -x` | ❌ W0 | ⬜ pending |
| 27-01-05 | 01 | 1 | APP-04 | unit | `pytest tests/test_display_preset.py::test_screeninfo_failure_fallback -x` | ❌ W0 | ⬜ pending |
| 27-01-06 | 01 | 1 | APP-04 | unit | `pytest tests/test_display_preset.py::test_override_valid -x` | ❌ W0 | ⬜ pending |
| 27-01-07 | 01 | 1 | APP-04 | unit | `pytest tests/test_display_preset.py::test_override_invalid -x` | ❌ W0 | ⬜ pending |
| 27-01-08 | 01 | 1 | APP-04 | unit | `pytest tests/test_display_preset.py::test_no_settings_file -x` | ❌ W0 | ⬜ pending |
| 27-01-09 | 01 | 1 | APP-04 | unit | `pytest tests/test_display_preset.py::test_startup_log_line -x` | ❌ W0 | ⬜ pending |
| 27-01-10 | 01 | 1 | APP-04 | unit | `pytest tests/test_display_preset.py::test_density_values -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_display_preset.py` — stubs for all APP-04 unit tests listed above
- [ ] `screeninfo==0.8.1` added to `deploy/pi/requirements-pi.txt`
- [ ] `screeninfo` available in dev environment (`pip install screeninfo==0.8.1`)

*Note: Tests mock `screeninfo.get_monitors` — no hardware required. Follow `importlib.reload(m)` + `monkeypatch` pattern from `tests/test_data_dir.py`.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 7" Pi touchscreen legible fonts | APP-04 SC-1 | Requires physical 800x480 Pi touchscreen | Launch on Pi, visually confirm fonts/buttons are tappable |
| True fullscreen on Windows | APP-04 (CONTEXT) | Requires visual verification of window behavior | Launch on Windows, confirm app fills entire screen without dragging |
| True fullscreen on Pi | APP-04 (CONTEXT) | Requires physical Pi with display | Launch on Pi, confirm fullscreen fills display |

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
