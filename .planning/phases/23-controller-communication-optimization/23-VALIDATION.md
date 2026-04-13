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
| 23-01-01 | 01 | 0 | COMM-01 | unit | `python -m pytest tests/test_poll.py::TestMegaBatchRead -x` | ❌ W0 | ⬜ pending |
| 23-01-02 | 01 | 0 | COMM-01 | unit | `python -m pytest tests/test_poll.py::TestMegaBatchCallCount -x` | ❌ W0 | ⬜ pending |
| 23-01-03 | 01 | 0 | COMM-02 | unit | covered by COMM-01 mega-batch test | ❌ W0 | ⬜ pending |
| 23-01-04 | 01 | 0 | COMM-02 | unit | `python -m pytest tests/test_poll.py::TestStaleOnFailure -x` | ❌ W0 | ⬜ pending |
| 23-01-05 | 01 | 0 | COMM-03 | unit | `python -m pytest tests/test_mg_reader.py::TestStateDispatch -x` | ❌ W0 | ⬜ pending |
| 23-01-06 | 01 | 0 | COMM-04 | unit | `python -m pytest tests/test_mg_reader.py::TestStateHandlerCalledWithInt -x` | ❌ W0 | ⬜ pending |
| 23-01-07 | 01 | 0 | COMM-04 | unit | `python -m pytest tests/test_mg_reader.py::TestFilterStateFromLog -x` | ❌ W0 | ⬜ pending |
| 23-01-08 | 01 | 0 | COMM-05 | unit | `python -m pytest tests/test_controller.py::TestDirectFlag -x` | ❌ W0 | ⬜ pending |
| 23-01-09 | 01 | 0 | COMM-06 | unit | `python -m pytest tests/test_controller.py::TestPrimaryTimeout -x` | ❌ W0 | ⬜ pending |
| 23-01-10 | 01 | 0 | COMM-06 | unit | `python -m pytest tests/test_mg_reader.py::TestMgHandleTimeout -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_poll.py` — update existing mock responses from individual to batched format; add TestMegaBatchRead, TestMegaBatchCallCount, TestStaleOnFailure
- [ ] `tests/test_mg_reader.py` — new file; TestStateDispatch, TestStateHandlerCalledWithInt, TestFilterStateFromLog, TestMgHandleTimeout
- [ ] `tests/test_controller.py` — extend with TestDirectFlag, TestPrimaryTimeout

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
