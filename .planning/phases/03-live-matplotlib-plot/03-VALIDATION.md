---
phase: 3
slug: live-matplotlib-plot
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pyproject.toml (`[tool.pytest.ini_options]`) |
| **Quick run command** | `python -m pytest tests/test_run_screen.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_run_screen.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 0 | RUN-07 | unit | `python -m pytest tests/test_run_screen.py::test_plot_buffer_properties -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 0 | RUN-07 | unit | `python -m pytest tests/test_run_screen.py::test_trail_clears_on_start -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 0 | RUN-07 | unit | `python -m pytest tests/test_run_screen.py::test_plot_hz_constant_exists -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 0 | RUN-07 | unit | `python -m pytest tests/test_run_screen.py::test_plot_buffer_only_during_cycle -x` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 0 | RUN-07 | unit | `python -m pytest tests/test_run_screen.py::test_plot_buffer_maxlen -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Five new test functions in `tests/test_run_screen.py` covering RUN-07 behaviors listed above
- [ ] No new test files needed — all RUN-07 tests belong in the existing `test_run_screen.py`
- [ ] No new fixtures needed — existing Kivy-deferred import pattern in `test_run_screen.py` is sufficient

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| E-STOP responsive during plot update | RUN-07 | Requires real UI interaction timing | Run app, start cycle, tap E-STOP while plot is animating — must respond within 200ms |
| Plot renders at 800x480 resolution | RUN-07 | Requires visual inspection on target display | Resize window to 800x480, verify plot is readable and not clipped |
| Equal aspect ratio visually correct | RUN-07 | Geometric accuracy requires visual check | Draw a known square path, verify it appears square on screen |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
