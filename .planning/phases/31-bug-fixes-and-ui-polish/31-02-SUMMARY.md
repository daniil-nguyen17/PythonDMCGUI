---
phase: 31-bug-fixes-and-ui-polish
plan: 02
subsystem: ui
tags: [kivy, display-presets, spacing-tokens, kv-files]

# Dependency graph
requires:
  - phase: 30-codebase-audit
    provides: Clean codebase with consistent naming and docstrings
provides:
  - Single 15inch display preset (dead 7inch/10inch removed)
  - Token-standardized spacing (4/8/12/16/24dp) in all shared KV files
affects: [32-per-machine-parameters, 33-licensing-core]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "4/8/12/16/24dp spacing token scale for all shared KV padding/spacing"
    - "Single display preset pattern (always 15inch)"

key-files:
  created: []
  modified:
    - src/dmccodegui/main.py
    - tests/test_display_preset.py
    - src/dmccodegui/ui/theme.kv
    - src/dmccodegui/ui/tab_bar.kv
    - src/dmccodegui/ui/status_bar.kv
    - src/dmccodegui/ui/profiles.kv
    - src/dmccodegui/ui/users.kv

key-decisions:
  - "Kept _classify_resolution() function signature for API stability even though it always returns '15inch'"
  - "10dp mapped to 12dp (closer to original) per RESEARCH.md recommendation"
  - "40dp profiles padding mapped to 24dp (maximum token) per user decision in CONTEXT.md"

patterns-established:
  - "Spacing token scale: all padding/spacing in shared KV files must use 4/8/12/16/24dp only"
  - "Display preset: single '15inch' preset, _classify_resolution always returns '15inch'"

requirements-completed: [UI-01, UI-02]

# Metrics
duration: 3min
completed: 2026-05-04
---

# Phase 31 Plan 02: Display Preset Cleanup and Spacing Token Standardization Summary

**Removed dead 7-inch/10-inch display presets and standardized all shared KV padding/spacing to locked 4/8/12/16/24dp token scale**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-04T05:51:40Z
- **Completed:** 2026-05-04T05:55:39Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Removed 7inch and 10inch entries from _DISPLAY_PRESETS, simplified _classify_resolution to always return "15inch"
- Updated all 10 test cases to reflect single-preset behavior (TDD: RED then GREEN)
- Standardized padding/spacing across 5 shared KV files (theme, tab_bar, status_bar, profiles, users) to token scale
- Verified zero non-token padding/spacing values remain in any shared KV file

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove 7"/10" presets and update tests (TDD RED)** - `e543d67` (test)
2. **Task 1: Remove 7"/10" presets and update tests (TDD GREEN)** - `e0bac48` (feat)
3. **Task 2: Standardize spacing tokens in shared KV files** - `027cc5d` (feat)

## Files Created/Modified
- `src/dmccodegui/main.py` - Removed 7inch/10inch presets, simplified _classify_resolution
- `tests/test_display_preset.py` - Updated tests for single-preset behavior
- `src/dmccodegui/ui/theme.kv` - CardFrame 10dp->12dp, ActionButton 6dp->8dp, controls 3dp->4dp
- `src/dmccodegui/ui/tab_bar.kv` - spacing/padding 2dp->4dp
- `src/dmccodegui/ui/status_bar.kv` - padding 6dp,2dp->8dp,4dp, spacing 6dp->8dp, padding_x 14dp->16dp
- `src/dmccodegui/ui/profiles.kv` - Main content padding 40dp->24dp, spacing 20dp->24dp
- `src/dmccodegui/ui/users.kv` - UserEditOverlay spacing 14dp->16dp

## Decisions Made
- Kept _classify_resolution() function signature (width, height params) for API stability even though always returns "15inch"
- Mapped 10dp to 12dp (closer to original intent) per RESEARCH.md guidance
- Mapped 40dp profiles padding down to 24dp (maximum token) per user decision
- base.kv, setup.kv, parameters.kv, pin_overlay.kv, diagnostics.kv had no non-token spacing values -- no changes needed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

3 pre-existing test failures in test_delta_c_bar_chart.py (flat_grind files) -- not caused by this plan's changes and out of scope per flat_grind protection rule.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Display preset code simplified and tested, ready for any future display work
- Shared KV token scale established as a pattern for future UI work
- Plan 03 (wave 2) can proceed independently

---
*Phase: 31-bug-fixes-and-ui-polish*
*Completed: 2026-05-04*
