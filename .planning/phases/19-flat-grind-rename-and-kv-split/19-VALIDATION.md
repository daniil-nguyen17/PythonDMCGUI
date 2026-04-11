---
phase: 19
slug: flat-grind-rename-and-kv-split
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pytest.ini or pyproject.toml (standard discovery) |
| **Quick run command** | `python -m pytest tests/ -x --tb=short` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x --tb=short`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 0 | FLAT-04 | smoke | `grep -rh "^<[A-Z]" src/dmccodegui/ui/ \| sort \| uniq -d` | ❌ W0 | ⬜ pending |
| 19-01-02 | 01 | 1 | FLAT-01 | unit | `python -m pytest tests/test_run_screen.py -x` | ✅ (needs update) | ⬜ pending |
| 19-01-03 | 01 | 1 | FLAT-02 | unit | `python -m pytest tests/test_axes_setup.py -x` | ✅ (needs update) | ⬜ pending |
| 19-01-04 | 01 | 1 | FLAT-03 | unit | `python -m pytest tests/test_parameters.py -x` | ✅ (needs update) | ⬜ pending |
| 19-01-05 | 01 | 2 | FLAT-04 | integration | `python -m pytest tests/ -v` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_kv_collision.py` — grep-based test for duplicate `<ClassName>:` headers across all .kv files (SC-3)
- [ ] `tests/test_flat_grind_screens.py` — stubs for FlatGrind* screen instantiation checks

*Existing test infrastructure (pytest, conftest.py) covers all other needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hardware smoke test (Run page cycle, jog, teach, parameter write) | FLAT-04 SC-4 | Requires real/simulated controller | Run app with controller connected, verify Run page cycle, jog buttons, teach, and parameter write all function |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
