---
phase: 24-windows-pyinstaller-bundle
plan: "01"
subsystem: infra
tags: [pyinstaller, frozen, appdata, gclib, kivy, versioning]

# Dependency graph
requires: []
provides:
  - "__version__ = '4.0.0' importable from dmccodegui"
  - "_get_data_dir() routing APPDATA/BinhAnHMI/ (frozen) vs auth/ (dev)"
  - "GCLIB_ROOT env var set before any gclib import in frozen mode"
  - "DMCApp.title = 'Binh An HMI v4.0.0'"
  - "DiagnosticsScreen excluded from production import chain"
affects:
  - "24-02 PyInstaller spec — depends on frozen-mode patches in main.py"
  - "Phase 25 installer — depends on APPDATA redirect working correctly"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Frozen-mode guard: getattr(sys, 'frozen', False) pattern for PyInstaller detection"
    - "Module-level GCLIB_ROOT patch before Kivy import chain to avoid DLL miss"
    - "Data dir routing: APPDATA in frozen, __file__-relative in dev"
    - "Class-level f-string title using __version__ for window branding"

key-files:
  created:
    - tests/test_data_dir.py
    - tests/test_version.py
  modified:
    - src/dmccodegui/__init__.py
    - src/dmccodegui/main.py
    - src/dmccodegui/screens/__init__.py

key-decisions:
  - "GCLIB_ROOT patch uses getattr(sys, '_MEIPASS', '') guard so monkeypatched tests don't crash on missing _MEIPASS"
  - "diagnostics.kv removed from KV_FILES — DiagnosticsScreen is dev-only, excluded from production bundle"
  - "idle timeout nav gate removes 'diagnostics' screen name since it no longer exists in production"

patterns-established:
  - "Frozen detection: always use getattr(sys, 'frozen', False) — never direct sys.frozen attribute access"
  - "Module reload in tests: importlib.reload(m) after monkeypatching sys.frozen to pick up frozen-mode branches"

requirements-completed: [WIN-05, WIN-07]

# Metrics
duration: 14min
completed: 2026-04-21
---

# Phase 24 Plan 01: Frozen-Mode App Patches Summary

**PyInstaller-ready main.py with GCLIB_ROOT env patch, APPDATA data dir routing, version branding, and dev-only diagnostics exclusion — validated by 6 new TDD tests**

## Performance

- **Duration:** 14 min
- **Started:** 2026-04-21T11:46:00Z
- **Completed:** 2026-04-21T12:00:00Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 5

## Accomplishments
- Frozen GCLIB_ROOT env var patch placed at absolute top of main.py, before any gclib import chain
- `_get_data_dir()` correctly routes to `%APPDATA%/BinhAnHMI/` in PyInstaller frozen mode and `src/dmccodegui/auth/` in dev mode, with automatic directory creation
- `DMCApp.__init__` now uses `_get_data_dir()` for both `users.json` and `settings.json` — user data survives restarts in frozen builds
- `DMCApp.title = 'Binh An HMI v4.0.0'` set as class attribute using `__version__` from `__init__.py`
- DiagnosticsScreen fully removed from production import chain: excluded from `screens/__init__.py`, `diagnostics.kv` removed from `KV_FILES`, `"diagnostics"` removed from idle timeout nav gate
- 6 new TDD tests cover all frozen/dev/fallback branches for `_get_data_dir()` plus version and title assertions

## Task Commits

1. **Task 1: Add __version__, _get_data_dir(), frozen startup block, window title, and diagnostics exclusion** - `da0669a` (feat)

**Plan metadata:** _(follows this summary commit)_

## Files Created/Modified
- `src/dmccodegui/__init__.py` - Added `__version__ = '4.0.0'` before `__all__`
- `src/dmccodegui/main.py` - Added sys import + frozen GCLIB_ROOT patch, `_get_data_dir()`, `__version__` import, `DMCApp.title`, data dir wiring, diagnostics exclusions
- `src/dmccodegui/screens/__init__.py` - Removed DiagnosticsScreen import and from `__all__`
- `tests/test_data_dir.py` - 4 tests: frozen mode, directory creation, dev mode, APPDATA fallback
- `tests/test_version.py` - 2 tests: package __version__, DMCApp.title class attribute

## Decisions Made
- Used `getattr(sys, '_MEIPASS', '')` guard in the frozen block so unit tests that monkeypatch `sys.frozen = True` without also providing `_MEIPASS` don't crash at module import time
- `__version__` imported inside the try/except block (both branches) to avoid a separate top-level import that could complicate the frozen import ordering

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Frozen block crashed when _MEIPASS not present during tests**
- **Found during:** Task 1, Step 3 (GREEN run)
- **Issue:** Plan's frozen block used `sys._MEIPASS` directly; when tests monkeypatched `sys.frozen = True` without providing `_MEIPASS`, `importlib.reload(m)` raised `AttributeError: module 'sys' has no attribute '_MEIPASS'`
- **Fix:** Wrapped the GCLIB_ROOT assignment with `_meipass = getattr(sys, '_MEIPASS', '')` guard — only sets env var when actually running inside PyInstaller
- **Files modified:** `src/dmccodegui/main.py`
- **Verification:** All 6 new tests pass; GCLIB_ROOT guard is logically equivalent in production (sys._MEIPASS is always set when sys.frozen is True in a real PyInstaller bundle)
- **Committed in:** da0669a (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in plan's frozen block code)
**Impact on plan:** Single line guard fix, zero scope change. GCLIB_ROOT is still set correctly in production frozen builds.

## Issues Encountered
- 17 pre-existing test failures exist in the test suite (test_screen_loader, test_status_bar, test_axes_setup, etc.) — confirmed pre-existing via `git stash` verification. Not caused by this plan's changes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All frozen-mode app patches are in place — Plan 02 (PyInstaller spec) can proceed
- `_get_data_dir()` and `__version__` are importable and tested
- DiagnosticsScreen exclusion is complete — spec file does not need to bundle diagnostics.kv or its assets

---
*Phase: 24-windows-pyinstaller-bundle*
*Completed: 2026-04-21*
