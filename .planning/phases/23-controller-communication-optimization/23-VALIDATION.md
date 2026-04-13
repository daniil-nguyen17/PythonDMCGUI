---
phase: 23
slug: controller-communication-optimization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | implicit (`tests/` directory discovered) |
| **Quick run command** | `python -m pytest tests/test_poll.py tests/test_mg_reader.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_poll.py tests/test_mg_reader.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -q --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 23-01-01 | 01 | 1 | COMM-01, COMM-02 | unit | `python -m pytest tests/test_poll.py::TestMegaBatchRead -x` | W0 | pending |
| 23-01-02 | 01 | 1 | COMM-01 | unit | `python -m pytest tests/test_poll.py::TestBatchCallCount -x` | W0 | pending |
| 23-01-03 | 01 | 1 | COMM-01 | unit | `python -m pytest tests/test_poll.py::TestStaleOnFailure -x` | W0 | pending |
| 23-01-04 | 01 | 1 | COMM-05, COMM-06 | unit | `python -m pytest tests/test_poll.py::TestConnectionHardening -x` | W0 | pending |
| 23-02-01 | 02 | 1 | COMM-03, COMM-04 | unit | `python -m pytest tests/test_mg_reader.py::TestMgReaderDispatch -x` | W0 | pending |
| 23-02-02 | 02 | 1 | COMM-04 | unit | `python -m pytest tests/test_mg_reader.py::TestStateFilteredFromLog -x` | W0 | pending |
| 23-02-03 | 02 | 1 | COMM-04 | unit | `python -m pytest tests/test_mg_reader.py::TestHandlerRegistration -x` | W0 | pending |
| 23-02-04 | 02 | 1 | COMM-06 | unit | `python -m pytest tests/test_mg_reader.py::TestMgHandleTimeout -x` | W0 | pending |
| 23-02-05 | 02 | 1 | COMM-04 | unit | `python -m pytest tests/test_mg_reader.py::TestStartStop -x` | W0 | pending |
| 23-03-01 | 03 | 2 | COMM-01, COMM-02 | integration | `python -m pytest tests/test_run_screen.py tests/test_flat_grind_widgets.py -x -q` | exists | pending |
| 23-03-02 | 03 | 2 | COMM-03, COMM-04 | integration | `python -m pytest tests/ -q --tb=short` | exists | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_poll.py` -- update existing mock responses from individual to batched format; add TestMegaBatchRead, TestBatchCallCount, TestStaleOnFailure, TestConnectionHardening
- [ ] `tests/test_mg_reader.py` -- new file; TestMgReaderDispatch, TestStateFilteredFromLog, TestHandlerRegistration, TestMgHandleTimeout, TestStartStop

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| --direct bypasses gcaps on real hardware | COMM-05 | Requires physical Galil controller | Connect with --direct, observe "[CTRL] Connected to {addr} --direct" in logs |
| Timeout fires within spec'd ms on real hardware | COMM-06 | Network timing requires real controller | Disconnect network cable, observe timeout exception within 1000ms |
| DMC MG messages arrive sub-ms | COMM-03 | Requires DMC program running on real controller | Trigger state transition, observe MachineState update timestamp |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
