---
phase: 27-screen-resolution-detection
plan: 01
subsystem: ui
tags: [screeninfo, kivy, resolution, display, preset, window-config]

# Dependency graph
requires:
  - phase: 26-pi-os-preparation-and-install-script
    provides: deploy/pi/ skeleton and requirements-pi.txt

provides:
  - "_classify_resolution(w, h) pure function — short-dimension threshold classification"
  - "_detect_preset(settings_path) — settings override > screeninfo auto-detect > 15inch fallback"
  - "_DISPLAY_PRESETS dict — three presets (7inch/10inch/15inch) with density, fullscreen, size"
  - "_early_settings_path() — pre-Kivy bootstrap settings.json path resolver"
  - "Preset-driven Kivy Config.set block replacing hardcoded values"
  - "screeninfo==0.8.1 in deploy/pi/requirements-pi.txt"

affects: [28-logging-infrastructure, 29-integration-testing-and-field-validation]

# Tech tracking
tech-stack:
  added: [screeninfo==0.8.1]
  patterns:
    - "Pre-Kivy lazy import pattern: screeninfo imported inside _detect_preset() body to avoid module-level side effects"
    - "Settings override with hard-stop on invalid: invalid display_size returns 15inch immediately (no auto-detect fallback)"
    - "Short-dimension threshold classification: min(w,h) <= 480 → 7inch, <= 600 → 10inch, else 15inch"

key-files:
  created:
    - tests/test_display_preset.py
    - .planning/phases/27-screen-resolution-detection/deferred-items.md
  modified:
    - src/dmccodegui/main.py
    - deploy/pi/requirements-pi.txt

key-decisions:
  - "screeninfo imported lazily inside _detect_preset() — prevents ImportError from blocking module load when screeninfo not installed"
  - "Invalid display_size in settings.json returns 15inch immediately without consulting screeninfo — per locked plan decision"
  - "_early_settings_path() intentionally duplicates _get_data_dir() path logic — no makedirs side effect needed at detection time"
  - "Pi uses fullscreen='auto', Windows uses borderless='1' — each preset's fullscreen_mode encodes the platform strategy"
  - "Density values (0.65/0.75/1.0) are initial estimates — kept as named constants in _DISPLAY_PRESETS for easy hardware tuning"

patterns-established:
  - "Pre-Kivy bootstrap read: settings.json read before any Kivy import using stdlib json only"
  - "Module-level preset detection: _detect_preset() called at module level, result stored as _ACTIVE_PRESET_NAME before Kivy imports"

requirements-completed: [APP-04]

# Metrics
duration: 4min
completed: 2026-04-22
---

# Phase 27 Plan 01: Screen Resolution Detection Summary

**Screeninfo-based display preset detection with settings.json override, three presets (7/10/15-inch) driving Kivy Config.set density and fullscreen mode**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-22T02:02:56Z
- **Completed:** 2026-04-22T02:06:26Z
- **Tasks:** 2 (TDD task + verification)
- **Files modified:** 4 (main.py, requirements-pi.txt, test_display_preset.py, deferred-items.md)

## Accomplishments

- Implemented `_classify_resolution(w, h)` — pure function using short-dimension thresholds for 7"/10"/15" display classification
- Implemented `_detect_preset(settings_path)` — three-level priority: settings.json override, screeninfo auto-detect, 15inch fallback
- Added `_DISPLAY_PRESETS` dict with density, width, height, fullscreen_mode, borderless, maximized, resizable per preset
- Replaced hardcoded `Config.set` block and deleted `Window.size = (1920, 1080)` — window config now fully preset-driven
- All 10 unit tests pass; no regressions introduced (17 pre-existing failures confirmed unchanged)

## Task Commits

Each task was committed atomically:

1. **TDD RED - Failing tests** - `e843a2e` (test)
2. **TDD GREEN - Implementation** - `ad87b85` (feat)
3. **Task 2: Full suite verification** - `a02734d` (chore)

**Plan metadata:** (final docs commit follows)

_Note: TDD task had RED (e843a2e) and GREEN (ad87b85) commits._

## Files Created/Modified

- `src/dmccodegui/main.py` - Added _DISPLAY_PRESETS, _classify_resolution, _early_settings_path, _detect_preset; replaced static Config.set block; removed Window.size hardcode
- `tests/test_display_preset.py` - 10 unit tests covering all APP-04 behaviors
- `deploy/pi/requirements-pi.txt` - Added screeninfo==0.8.1
- `.planning/phases/27-screen-resolution-detection/deferred-items.md` - Logged 17 pre-existing test failures

## Decisions Made

- screeninfo imported lazily inside `_detect_preset()` body — prevents `ImportError` from breaking module load when screeninfo not installed in test/dev environments
- Invalid `display_size` in settings.json returns `"15inch"` immediately — does NOT fall through to screeninfo auto-detect (per locked plan decision)
- `_early_settings_path()` intentionally duplicates `_get_data_dir()` path logic — it must not call `makedirs` at detection time (bootstrap, pre-Kivy)
- Pi 7"/10" presets use `fullscreen_mode="auto"` (Pi framebuffer fills screen natively); Windows 15" uses `borderless="1"` (manages its own size)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

17 pre-existing test failures were present in the test suite before phase 27-01 changes. Confirmed via `git stash` + re-run. Logged to `deferred-items.md`. Our 10 new tests all pass, and `test_data_dir.py` (6 tests) remains unaffected.

## User Setup Required

None - no external service configuration required. screeninfo is a pure Python library (no system dependencies on Windows/Pi).

## Next Phase Readiness

- Phase 27-01 complete: display preset detection integrated into pre-Kivy startup block
- Phase 28 (Logging Infrastructure) can proceed; no blocking dependencies
- Hardware validation on real Pi 7" display remains a research flag (in STATE.md) — density values may need tuning after field testing

---
*Phase: 27-screen-resolution-detection*
*Completed: 2026-04-22*
