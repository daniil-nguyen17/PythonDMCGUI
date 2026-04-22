---
phase: 28-logging-infrastructure
plan: "01"
subsystem: logging
tags: [logging, tdd, infrastructure, print-migration]
dependency_graph:
  requires: []
  provides: [setup_logging, _setup_excepthook, module-level _log]
  affects: [src/dmccodegui/main.py, tests/test_logging.py, tests/test_display_preset.py]
tech_stack:
  added: [logging.handlers.RotatingFileHandler]
  patterns: [pre-Kivy logging init, sys.__stderr__ guard against Kivy proxy loop, module-level _log]
key_files:
  created: [tests/test_logging.py]
  modified: [src/dmccodegui/main.py, tests/test_display_preset.py]
decisions:
  - _log placed in pre-Kivy execution block (after setup_logging() call) so _detect_preset() can use it at module load time
  - StreamHandler uses sys.__stderr__ (not sys.stderr) to avoid Kivy's stderr-proxy infinite recursion loop
  - test_startup_log_line updated to use log capture handler instead of capsys (print migrated to logger)
metrics:
  duration_seconds: 449
  completed: "2026-04-22T02:42:41Z"
  tasks_completed: 2
  files_changed: 3
  new_tests: 8
---

# Phase 28 Plan 01: Logging Infrastructure Setup Summary

**One-liner:** RotatingFileHandler logging infrastructure with excepthook patch, pre-Kivy _log placement, and 7 print() calls migrated to structured logger calls.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | TDD — setup_logging() + _setup_excepthook() | 48fd3dc | tests/test_logging.py, src/dmccodegui/main.py |
| 2 | Migrate main.py print() calls to logger | 0f3fb9d | src/dmccodegui/main.py, tests/test_display_preset.py |

## What Was Built

### setup_logging()
- Creates `_get_data_dir()/logs/app.log` with `RotatingFileHandler` (5 MB limit, 3 backups, UTF-8)
- Formatter: `%(asctime)s %(levelname)s [%(module)s] %(message)s` with `%Y-%m-%d %H:%M:%S` datefmt
- Root logger level set to DEBUG
- StreamHandler added only when `sys.stderr is not None` (frozen no-console guard)
- StreamHandler always writes to `sys.__stderr__` to avoid Kivy's stderr-proxy infinite recursion

### _setup_excepthook()
- Patches `sys.excepthook` to log full tracebacks via `logging.getLogger('dmccodegui').critical()`
- KeyboardInterrupt passes through to original hook without logging
- All other exceptions: `traceback.format_exception()` result logged before calling original hook

### Call Ordering
Both functions called in the pre-Kivy execution block, before `_detect_preset()`:
```
setup_logging()
_setup_excepthook()
_log = logging.getLogger(__name__)   # must be here, not after Kivy imports
_ACTIVE_PRESET_NAME = _detect_preset(...)
```

### Print Migration
All 7 print() calls in main.py replaced with logger calls:
- `_detect_preset()` (4 calls): `_log.info` / `_log.warning`
- Preload cache (1 call): `_log.info`
- MgReader start/no-addr (2 calls): `_log.info` / `_log.warning`

### Ad-hoc Logger Consolidation
3 `import logging; logging.getLogger(__name__)` call sites replaced with module-level `_log`:
- `build()` machine KV load failure
- `_add_machine_screens()` (removed local `_log = logging.getLogger(__name__)`)
- `do_estop()` e-stop error

### Kivy Logger Suppression
`logging.getLogger('kivy').setLevel(logging.WARNING)` added after Kivy imports to suppress DEBUG noise.

## Test Results

- `pytest tests/test_logging.py`: 8/8 pass (all new)
- `pytest tests/test_display_preset.py`: 10/10 pass (1 test updated: capsys → log capture handler)
- Full suite: 499 pass, 17 pre-existing failures (unchanged from baseline)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] _log used before definition in _detect_preset() call**
- **Found during:** Task 2 (print migration)
- **Issue:** `_detect_preset()` is called at module level (line 248) before the Kivy imports block where `_log` was initially placed (~line 332). This caused `NameError: name '_log' is not defined` during module reload in tests.
- **Fix:** Moved `_log = logging.getLogger(__name__)` to the pre-Kivy execution block, immediately after `_setup_excepthook()` and before `_detect_preset()` call.
- **Files modified:** src/dmccodegui/main.py
- **Commit:** 0f3fb9d

**2. [Rule 1 - Bug] RecursionError: StreamHandler → Kivy stderr proxy → root logger → StreamHandler**
- **Found during:** Task 2 (running tests after Task 1 commit)
- **Issue:** Kivy replaces `sys.stderr` with `KivyLogger._write`, a proxy that routes writes back through Python's logging system. After Kivy imports, `setup_logging()`'s StreamHandler (writing to `sys.stderr`) would trigger Kivy's logger, which propagated to root, which triggered the StreamHandler again — infinite recursion.
- **Fix:** Changed StreamHandler to use `sys.__stderr__` (the original OS stderr) instead of `sys.stderr`. The `sys.stderr is not None` guard is kept for the frozen no-console check; the actual stream used is `getattr(sys, '__stderr__', sys.stderr) or sys.stderr`.
- **Files modified:** src/dmccodegui/main.py
- **Commit:** 0f3fb9d

**3. [Rule 1 - Bug] test_startup_log_line checked stdout (capsys) for print() output**
- **Found during:** Task 2 (print migration)
- **Issue:** `test_startup_log_line` in `test_display_preset.py` asserted `"10inch" in captured.out` — this relied on the `print()` call. After migration to `_log.info()`, the output goes to the log file handler, not stdout.
- **Fix:** Updated test to add a temporary `logging.Handler` to root logger, call `_detect_preset()`, then check captured records for "10inch".
- **Files modified:** tests/test_display_preset.py
- **Commit:** 0f3fb9d

## Self-Check: PASSED

- tests/test_logging.py: FOUND
- src/dmccodegui/main.py: FOUND
- 28-01-SUMMARY.md: FOUND
- Commit 48fd3dc: FOUND
- Commit 0f3fb9d: FOUND
- setup_logging() defined at line 38, called at line 250: CONFIRMED
- RotatingFileHandler at line 52: CONFIRMED
- sys.excepthook patched at line 101: CONFIRMED
