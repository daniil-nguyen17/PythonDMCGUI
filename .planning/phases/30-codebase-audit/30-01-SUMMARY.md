---
phase: 30-codebase-audit
plan: "01"
subsystem: tooling
tags: [ruff, vulture, lint, ci, import-ordering, dead-code]

dependency_graph:
  requires: []
  provides: [lint-tooling, ruff-config, vulture-allowlist, ci-lint-gate]
  affects: [30-02, 30-03]

tech_stack:
  added:
    - ruff>=0.15 (linter/formatter)
    - vulture>=2.16 (dead code detector)
  patterns:
    - Kivy deferred imports behind try/except with noqa comments for legitimate E402
    - Vulture allowlist generated from KV file parsing (not hand-maintained)
    - Underscore-prefix convention (_dt, _inst, _chart_widget) to suppress unused-param warnings

key_files:
  created:
    - pyproject.toml ([tool.ruff] config, dev deps)
    - .vulture_allowlist.py (314 lines, 22 classes, 165 KV-referenced attributes)
    - scripts/gen_vulture_allowlist.py (KV parser script, ~180 lines)
    - tests/test_lint.py (CI gate: ruff + vulture subprocess checks)
  modified:
    - src/dmccodegui/controller.py (F821 bug fix in write_array, import reorganization)
    - src/dmccodegui/main.py (noqa E402 comments, F841/E741 fixes)
    - src/dmccodegui/screens/base.py (E702/E741 fixes)
    - src/dmccodegui/hmi/data_record.py (vulture _dt rename)
    - src/dmccodegui/hmi/mg_reader.py (vulture _dt rename x3)
    - src/dmccodegui/hmi/poll.py (vulture _dt rename x3)
    - src/dmccodegui/screens/flat_grind/run.py (logger reposition, _dt rename)
    - src/dmccodegui/screens/convex/run.py (logger reposition, _dt rename)
    - src/dmccodegui/screens/serration/run.py (_dt rename x3)
    - src/dmccodegui/screens/setup.py (docstring reposition)
    - src/dmccodegui/screens/users.py (F401 unused TextInput removed)
    - src/dmccodegui/screens/profiles.py (E702 fix x2)
    - src/dmccodegui/machine_config.py (E501 line splits x3)
    - src/dmccodegui/screens/flat_grind/axes_setup.py (E702 fix x2)
    - src/dmccodegui/screens/convex/axes_setup.py (E702 fix x2)
    - src/dmccodegui/screens/serration/axes_setup.py (E702 fix x2)
    - src/dmccodegui/utils/transport.py (import reorganization)

decisions:
  - "N rules excluded from ruff select (not E/F/I/W) — naming convention changes are Phase 02 scope only"
  - "Kivy deferred imports (post-Config.set) use targeted noqa E402 rather than blanket file-level ignore"
  - "vulture allowlist is auto-generated from KV files, not hand-maintained — gen script is source of truth"
  - "import time as _t; _t.sleep() pattern replaced with two-line form using noqa PLC0415"

metrics:
  duration_minutes: ~90
  tasks_completed: 2
  tasks_total: 2
  files_modified: 37
  files_created: 4
  completed_date: "2026-05-04"
---

# Phase 30 Plan 01: Ruff and Vulture Lint Tooling Summary

Configured ruff (E/F/I/W rules, 120-char limit) and vulture (80% confidence, auto-generated KV allowlist) across all 37 source files, with a pytest CI gate confirming both tools pass.

## What Was Built

### Task 1: Tooling Configuration + KV Allowlist (602b693)

**pyproject.toml** gained two tool sections and two new dev deps. The `[tool.ruff]` block selects E/F/I/W rules at 120-char line length targeting Python 3.10. Per-file ignores exempt `dmc_vars.py` from N (hardware variable naming is a hardware contract) and five backward-compat shim files from F401.

**scripts/gen_vulture_allowlist.py** parses every `.kv` file under `src/dmccodegui/ui/` via regex, extracts all `root.<attr>` and `app.<attr>` references, maps KV rule class names to their Python counterparts, and writes `.vulture_allowlist.py`. An `EXTRA_ALLOWLIST` section covers Kivy lifecycle hooks (`on_kv_post`, `on_pre_enter`, `on_leave`, `on_touch_down`), machine_config._REGISTRY (dynamic access), and DataRecordListener callbacks.

**.vulture_allowlist.py** covers 22 Python classes and 165 KV-referenced attributes. Uses bare `ClassName.method_name` expression format that vulture recognizes.

**tests/test_lint.py** has two tests: `test_ruff_check` and `test_vulture_check`, each running the respective tool as a subprocess and asserting returncode == 0. Captures stdout/stderr and prints them on failure to aid CI debugging.

### Task 2: Ruff --fix + Manual Violation Resolution (ff2a549)

**Auto-fixed via `ruff --fix`:** 142 issues — import reordering to stdlib/third-party/local groups across all 37 files, whitespace normalization, trailing comma insertion.

**Manual fixes:**

| Rule | Count | Fix Applied |
|------|-------|-------------|
| F821 (undefined name) | 1 | `written = 0` init added in `controller.write_array()`; return type corrected to `-> int` |
| E402 (import not at top) | ~42 | Category 1: Kivy pattern — `# noqa: E402`; Category 2: misplaced `logger =` — moved after imports; Category 3: docstring after `from __future__` — moved before |
| E702 (semicolon) | 8 | `import time as _t; _t.sleep(N)` split into 2 lines with `# noqa: PLC0415` |
| E741 (ambiguous `l`) | 4 | `lambda *_, l=label:` renamed to `lambda *_, lbl=label:` in base.py |
| E501 (line too long) | 5 | Long lines split in controller.py and machine_config.py |
| F401 (unused import) | 1 | `TextInput` removed from users.py |
| F841 (unused local) | 1 | `new_mode = app_theme.toggle()` reduced to `app_theme.toggle()` in main.py |
| vulture dt unused | 12 | `dt` → `_dt` in Clock callback params across hmi/ and run screens |
| vulture inst/chart_widget | 2 | `inst` → `_inst`, `chart_widget` → `_chart_widget` |

## Verification Results

```
ruff check src/                                   → All checks passed!
ruff check --select I src/                        → All checks passed!
ruff check --select F401 src/                     → All checks passed!
vulture src/ .vulture_allowlist.py --min-confidence 80  → (no output, exit 0)
pytest tests/test_lint.py -v                      → 2 passed
pytest tests/ -q --ignore=tests/test_delta_c_bar_chart.py  → 506 passed
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed undefined variable `written` in `controller.write_array()`**
- Found during: Task 2 (ruff --fix revealed F821 violation)
- Issue: `written += line.count("=")` used in loop body before any initialization — would raise `UnboundLocalError` at runtime when the flush-at-end branch executed
- Fix: Added `written = 0` before the loop; changed return type annotation from `-> None` to `-> int` to match the actual return value
- Files modified: `src/dmccodegui/controller.py`
- Commit: ff2a549

**2. [Rule 2 - Missing critical] Added `# noqa: PLC0415` to intentional local imports**
- Found during: Task 2 (E702 split created import-inside-function lines)
- Issue: Splitting `import time as _t; _t.sleep(N)` into two lines caused ruff to flag the `import time` inside the function as PLC0415 (import not at top of file)
- Fix: Added `# noqa: PLC0415` comment on the import line to document the intentional pattern
- Files modified: base.py (x2), flat_grind/axes_setup.py (x2), convex/axes_setup.py (x2), serration/axes_setup.py (x2), profiles.py (x2)
- Commit: ff2a549

### Out-of-Scope Discoveries (deferred)

Pre-existing test failures in `tests/test_delta_c_bar_chart.py` (3 tests) were present before this plan began. Confirmed via `git stash` check — not caused by our changes. Excluded from pytest runs via `--ignore` flag.

## Self-Check

### Files Created

- [x] `.vulture_allowlist.py` — FOUND
- [x] `scripts/gen_vulture_allowlist.py` — FOUND
- [x] `tests/test_lint.py` — FOUND
- [x] `.planning/phases/30-codebase-audit/30-01-SUMMARY.md` — FOUND (this file)

### Commits

- [x] `602b693` — feat(30-01): configure ruff/vulture tooling and generate KV allowlist
- [x] `ff2a549` — fix(30-01): resolve all ruff and vulture violations across 37 source files

## Self-Check: PASSED
