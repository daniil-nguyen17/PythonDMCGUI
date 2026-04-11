---
phase: 20
slug: screen-registry-and-loader
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | None — sys.path insert in each test file |
| **Quick run command** | `pytest tests/test_machine_config.py tests/test_base_classes.py -x` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_machine_config.py tests/test_base_classes.py -x`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 1 | LOAD-01 | unit | `pytest tests/test_machine_config.py -k registry_screen_classes -x` | ❌ W0 | ⬜ pending |
| 20-01-02 | 01 | 1 | LOAD-01 | unit | `pytest tests/test_machine_config.py -k load_kv_path -x` | ❌ W0 | ⬜ pending |
| 20-01-03 | 01 | 1 | LOAD-03 | unit | `pytest tests/test_base_classes.py -k cleanup -x` | ❌ W0 | ⬜ pending |
| 20-01-04 | 01 | 1 | LOAD-03 | unit | `pytest tests/test_base_classes.py -k cleanup_nonblocking -x` | ❌ W0 | ⬜ pending |
| 20-02-01 | 02 | 2 | LOAD-02 | unit | `pytest tests/test_screen_loader.py -k load_machine_screens -x` | ❌ W0 | ⬜ pending |
| 20-02-02 | 02 | 2 | LOAD-02 | unit | `pytest tests/test_screen_loader.py -k screen_names -x` | ❌ W0 | ⬜ pending |
| 20-02-03 | 02 | 2 | LOAD-04 | unit | `pytest tests/test_screen_loader.py -k mismatch -x` | ❌ W0 | ⬜ pending |
| 20-02-04 | 02 | 2 | LOAD-04 | unit | `pytest tests/test_screen_loader.py -k mismatch_graceful -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_screen_loader.py` — stubs for LOAD-02, LOAD-04 (new file; mock ScreenManager)
- [ ] Add to `tests/test_machine_config.py`: `test_registry_has_screen_classes_key`, `test_registry_load_kv_path_resolves`
- [ ] Add to `tests/test_base_classes.py`: `test_base_run_screen_cleanup_stops_resources`, `test_base_run_screen_cleanup_nonblocking`

*Existing infrastructure covers framework installation — pytest already present.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| machType mismatch popup dialog | LOAD-04 | Visual UI popup rendering requires live Kivy event loop | 1. Set settings.json to "4-Axes Flat Grind", 2. Connect to controller with different machType, 3. Verify popup appears with picker |
| App exit on machine type change | LOAD-04 | Process restart behavior | 1. Change machine type via status bar picker, 2. Verify cleanup runs (check logs), 3. Verify app exits with message |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
