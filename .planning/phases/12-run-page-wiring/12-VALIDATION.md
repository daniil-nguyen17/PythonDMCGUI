---
phase: 12
slug: run-page-wiring
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-06
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing suite) |
| **Config file** | none — discovered by default |
| **Quick run command** | `python -m pytest tests/test_run_screen.py -x` |
| **Full suite command** | `python -m pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_run_screen.py -x`
- **After every plan wave:** Run `python -m pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | RUN-01 | unit | `python -m pytest tests/test_run_screen.py::test_start_grind_sends_hmi_trigger -x` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | RUN-01 | unit | `python -m pytest tests/test_run_screen.py::test_start_grind_clears_plot_buffers -x` | ❌ W0 | ⬜ pending |
| 12-01-03 | 01 | 1 | RUN-05 | unit | `python -m pytest tests/test_run_screen.py::test_more_stone_sends_hmi_trigger -x` | ❌ W0 | ⬜ pending |
| 12-01-04 | 01 | 1 | RUN-05 | unit | `python -m pytest tests/test_run_screen.py::test_less_stone_sends_hmi_trigger -x` | ❌ W0 | ⬜ pending |
| 12-01-05 | 01 | 1 | RUN-05 | unit | `python -m pytest tests/test_run_screen.py::test_more_stone_reads_startptc_before_and_after -x` | ❌ W0 | ⬜ pending |
| 12-01-06 | 01 | 1 | RUN-04 | unit | `python -m pytest tests/test_run_screen.py::test_stop_sends_st_only -x` | ✅ | ⬜ pending |
| 12-01-07 | 01 | 1 | RUN-07 | unit | `python -m pytest tests/test_run_screen.py::test_plot_buffer_only_during_cycle -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_run_screen.py` — add `test_start_grind_sends_hmi_trigger`
- [ ] `tests/test_run_screen.py` — add `test_start_grind_clears_plot_buffers` (rename existing `test_trail_clears_on_start`)
- [ ] `tests/test_run_screen.py` — add `test_more_stone_sends_hmi_trigger`
- [ ] `tests/test_run_screen.py` — add `test_less_stone_sends_hmi_trigger`
- [ ] `tests/test_run_screen.py` — add `test_more_stone_reads_startptc_before_and_after`

*Existing infrastructure covers framework/fixtures — only new test stubs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| RUN-02: Go To Rest | RUN-02 | Removed from scope per CONTEXT.md | N/A — requirement addressed by removal |
| RUN-03: Go To Start | RUN-03 | Removed from scope per CONTEXT.md | N/A — requirement addressed by removal |
| RUN-06: New Session | RUN-06 | Moved to Phase 13 per CONTEXT.md | N/A — deferred to Phase 13 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
