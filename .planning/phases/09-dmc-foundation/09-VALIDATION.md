---
phase: 9
slug: dmc-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (from pyproject.toml dev deps) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` testpaths=["tests"] |
| **Quick run command** | `pytest tests/test_dmc_vars.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_dmc_vars.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | DMC-01 | unit | `pytest tests/test_dmc_vars.py::test_hmi_trigger_names -x` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | DMC-06 | unit | `pytest tests/test_dmc_vars.py::test_constants_values -x` | ❌ W0 | ⬜ pending |
| 09-01-03 | 01 | 1 | DMC-06 | unit | `pytest tests/test_dmc_vars.py::test_no_stale_array_names -x` | ❌ W0 | ⬜ pending |
| 09-01-04 | 01 | 1 | DMC-06 | unit | `pytest tests/test_dmc_vars.py::test_app_state_dmc_state -x` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 1 | DMC-02 | manual | DMC file review after edit | N/A | ⬜ pending |
| 09-02-02 | 02 | 1 | DMC-03 | manual | DMC file review after edit | N/A | ⬜ pending |
| 09-02-03 | 02 | 1 | DMC-04 | manual | Verify via gclib query after XQ #AUTO | N/A | ⬜ pending |
| 09-02-04 | 02 | 1 | DMC-05 | manual | DMC file review after edit | N/A | ⬜ pending |
| 09-03-01 | 03 | 2 | SC-5 | unit | `pytest tests/test_dmc_vars.py::test_disconnect_closes_handle -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_dmc_vars.py` — stubs for DMC-01 (name validation), DMC-06 (no stale strings, constant values, app_state field), SC-5 (disconnect mock test)

*Existing tests pass without new test file; Wave 0 only needs the new test file.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| #WtAtRt OR conditions present for all 5 button blocks | DMC-02 | Requires real Galil controller or DMC emulator | Review modified DMC file, verify `IF (@IN[x]=0) \| (hmiVar=0)` syntax in each #WtAtRt block |
| hmiVar reset is first line inside each triggered block | DMC-03 | DMC file structure verification | Verify each triggered block begins with `hmiVar=1` before any motion commands |
| hmiState is nonzero at each state boundary | DMC-04 | Requires gclib query after XQ #AUTO | Upload DMC, run XQ #AUTO, query hmiState at each state |
| #SULOOP OR conditions present for all 4 button blocks | DMC-05 | Requires real Galil controller or DMC emulator | Review modified DMC file, verify OR conditions in #SULOOP blocks |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
