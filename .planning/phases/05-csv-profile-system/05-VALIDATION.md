---
phase: 5
slug: csv-profile-system
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (no version pin; `pyproject.toml` dev dep) |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options] testpaths = ["tests"]` |
| **Quick run command** | `pytest tests/test_profiles.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_profiles.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 0 | CSV-01 | unit | `pytest tests/test_profiles.py::test_export_writes_machine_type -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 0 | CSV-01 | unit | `pytest tests/test_profiles.py::test_export_writes_all_scalars -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 0 | CSV-01 | unit | `pytest tests/test_profiles.py::test_export_writes_array_row -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 0 | CSV-01 | unit | `pytest tests/test_profiles.py::test_export_csv_parseable -x` | ❌ W0 | ⬜ pending |
| 05-01-05 | 01 | 0 | CSV-02 | unit | `pytest tests/test_profiles.py::test_parse_returns_scalars_and_arrays -x` | ❌ W0 | ⬜ pending |
| 05-01-06 | 01 | 0 | CSV-02 | unit | `pytest tests/test_profiles.py::test_diff_only_changed -x` | ❌ W0 | ⬜ pending |
| 05-01-07 | 01 | 0 | CSV-02 | unit | `pytest tests/test_profiles.py::test_diff_numeric_comparison -x` | ❌ W0 | ⬜ pending |
| 05-01-08 | 01 | 0 | CSV-02 | unit | `pytest tests/test_profiles.py::test_import_validates_scalars -x` | ❌ W0 | ⬜ pending |
| 05-01-09 | 01 | 0 | CSV-03 | unit | `pytest tests/test_profiles.py::test_machine_type_mismatch_blocked -x` | ❌ W0 | ⬜ pending |
| 05-01-10 | 01 | 0 | CSV-04 | unit | `pytest tests/test_profiles.py::test_import_disabled_when_cycle_running -x` | ❌ W0 | ⬜ pending |
| 05-01-11 | 01 | 0 | CSV-05 | unit | `pytest tests/test_tab_bar.py::test_profiles_tab_role_visibility -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_profiles.py` — stubs for CSV-01, CSV-02, CSV-03, CSV-04 (pure Python, no Kivy)
- [ ] `src/dmccodegui/screens/profiles.py` — new screen module
- [ ] `src/dmccodegui/ui/profiles.kv` — KV layout
- [ ] Extend `tests/test_tab_bar.py` — add test for "profiles" tab visibility per role (CSV-05)

*Existing infrastructure covers framework needs — no new test framework install required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| FileChooser opens and navigates to CSV files | CSV-02 | Kivy UI interaction requires running app | 1. Navigate to Profiles tab 2. Tap Import 3. Verify FileChooser opens with .csv filter |
| Confirmation dialog shows diff before applying | CSV-02 | Visual UI dialog requires human verification | 1. Import a CSV with 2-3 changed values 2. Verify diff dialog appears with old/new values 3. Confirm or cancel |
| Import button visually greyed out during cycle | CSV-04 | Visual state requires running app with cycle | 1. Start grinding cycle 2. Navigate to Profiles tab 3. Verify Import button is visually disabled |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
