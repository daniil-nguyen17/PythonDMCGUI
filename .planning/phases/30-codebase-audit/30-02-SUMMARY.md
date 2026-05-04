---
phase: 30-codebase-audit
plan: "02"
subsystem: code-quality
tags: [ruff, vulture, naming, dead-code, logger, controller]

dependency_graph:
  requires: [30-01]
  provides: [naming-consistency, n-rules-clean, logger-rename]
  affects: [30-03]

tech_stack:
  added: []
  patterns:
    - logger = logging.getLogger(__name__) in every module (no log= pattern)
    - Exception names carry Error suffix per PEP 8 / N818 (backward-compat aliases retained)
    - Local constants use snake_case not UPPER_CASE (N806 rule)
    - globalDMC -> global_dmc (N816 mixedCase global variable)

key_files:
  created: []
  modified:
    - src/dmccodegui/controller.py (log->logger, globalDMC->global_dmc, ControllerNotReady->ControllerNotReadyError, IndexOutOfRange->IndexOutOfRangeError + backward-compat aliases)
    - src/dmccodegui/main.py (_VALID_PRESETS -> _valid_presets)
    - src/dmccodegui/screens/base.py (CARD_HEIGHT, GROUP_COLORS, GROUP_ICONS, BORDER_*, DOT_* -> snake_case)
    - src/dmccodegui/screens/convex/run.py (_CPM_DEFAULTS -> _cpm_defaults)
    - src/dmccodegui/screens/flat_grind/run.py (_CPM_DEFAULTS -> _cpm_defaults x2)

decisions:
  - "Exception class aliases retained for backward-compat (ControllerNotReady = ControllerNotReadyError) — internal code uses the Error-suffixed primary name"
  - "N-rules applied across all files, not just controller.py — ruff --select N revealed violations in main.py, base.py, convex/run.py, flat_grind/run.py beyond the plan scope"
  - "vulture was already clean from Plan 01 — Task 1 required no changes"

metrics:
  duration_minutes: ~25
  tasks_completed: 2
  tasks_total: 2
  files_modified: 5
  files_created: 0
  completed_date: "2026-05-04"
---

# Phase 30 Plan 02: Dead Code Resolution and Naming Consistency Summary

Renamed `log` to `logger` in controller.py, renamed exception classes to carry `Error` suffix, renamed five categories of UPPER_CASE local variables to snake_case across main.py/base.py/convex/flat_grind run screens, bringing ruff N-rules from 17 violations to zero.

## What Was Built

### Task 1: Dead code analysis and resolution

Vulture was already clean (exit 0) from Plan 01's work. No additional dead code changes were required.

- `ControllerPoller` in `hmi/poll.py`: retained — `tests/test_poll.py` imports it directly via `from dmccodegui.hmi.poll import ControllerPoller`. Already in vulture allowlist.
- KV-registered screen classes: all live — confirmed via `_REGISTRY` in `machine_config.py`.
- `vulture src/ .vulture_allowlist.py --min-confidence 80` → exit 0 (no changes needed).
- `pytest tests/ -x -q` → 506 passed (pre-existing `test_delta_c_bar_chart.py` failures excluded as noted in Plan 01).

### Task 2: Naming consistency — rename controller.py logger + verify N-rules (abbd220)

**Ruff N-rule violations found (17 total across 5 files):**

| Rule | Location | Original | Fixed |
|------|----------|----------|-------|
| N (log var) | controller.py:13 | `log = logging.getLogger` | `logger = logging.getLogger` |
| N816 | controller.py:24,27,29 | `globalDMC` | `global_dmc` |
| N818 | controller.py:48 | `ControllerNotReady(Exception)` | `ControllerNotReadyError(Exception)` |
| N818 | controller.py:52 | `IndexOutOfRange(Exception)` | `IndexOutOfRangeError(Exception)` |
| N806 | main.py:210 | `_VALID_PRESETS` | `_valid_presets` |
| N806 | base.py:950 | `CARD_HEIGHT` | `card_height` |
| N806 | base.py:953 | `GROUP_COLORS` | `group_colors` |
| N806 | base.py:962 | `GROUP_ICONS` | `group_icons` |
| N806 | base.py:1241-1245 | `BORDER_NORMAL/AMBER/RED`, `DOT_AMBER/RED` | snake_case equivalents |
| N806 | convex/run.py:818 | `_CPM_DEFAULTS` | `_cpm_defaults` |
| N806 | flat_grind/run.py:430 | `_CPM_DEFAULTS` | `_cpm_defaults` |
| N806 | flat_grind/run.py:1159 | `_CPM_DEFAULTS` | `_cpm_defaults` |

**Backward-compat aliases added for exception renames:**
```python
ControllerNotReady = ControllerNotReadyError  # backward-compat
IndexOutOfRange = IndexOutOfRangeError         # backward-compat
```
No external tests imported these names, but aliases prevent silent breakage if user code depends on them.

**Internal usages updated:** All `raise ControllerNotReady(...)` and `except ControllerNotReady:` updated to use `ControllerNotReadyError`. Same for `IndexOutOfRange`.

## Verification Results

```
vulture src/ .vulture_allowlist.py --min-confidence 80  → exit 0 (no output)
ruff check --select N src/                              → All checks passed!
ruff check src/                                         → All checks passed!
grep -rn "^log = logging" src/                          → (empty, exit 1 = no matches)
pytest tests/ -x -q (excluding test_delta_c_bar_chart)  → 506 passed
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] N-rule violations extended beyond controller.py**
- Found during: Task 2 (ruff --select N revealed 17 violations, not just the log rename)
- Issue: Plan only mentioned `log`->`logger` rename, but N-rules flagged 4 additional violation categories across main.py, base.py, convex/run.py, flat_grind/run.py
- Fix: Applied all N806/N816/N818 fixes in scope — local constants to snake_case, global variable rename, exception class renaming with backward-compat aliases
- Files modified: main.py, base.py, convex/run.py, flat_grind/run.py (in addition to controller.py)
- Commit: abbd220

## Self-Check

### Files Modified

- [x] `src/dmccodegui/controller.py` — FOUND (logger rename, globalDMC rename, exception renames)
- [x] `src/dmccodegui/main.py` — FOUND (_valid_presets rename)
- [x] `src/dmccodegui/screens/base.py` — FOUND (card_height, group_colors, group_icons, border/dot vars)
- [x] `src/dmccodegui/screens/convex/run.py` — FOUND (_cpm_defaults)
- [x] `src/dmccodegui/screens/flat_grind/run.py` — FOUND (_cpm_defaults x2)
- [x] `.planning/phases/30-codebase-audit/30-02-SUMMARY.md` — FOUND (this file)

### Commits

- [x] `abbd220` — fix(30-02): rename log->logger, fix N-rule naming violations across 5 files

## Self-Check: PASSED
