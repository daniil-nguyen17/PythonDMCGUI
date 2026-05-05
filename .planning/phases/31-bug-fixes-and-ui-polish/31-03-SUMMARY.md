---
phase: 31-bug-fixes-and-ui-polish
plan: 03
subsystem: ui
tags: [kivy, kv, spacing-tokens, touch-targets, layout-consistency]

# Dependency graph
requires:
  - phase: 31-02
    provides: "Shared KV spacing token scale (4/8/12/16/24dp), display preset cleanup"
provides:
  - "All machine-specific KV files standardized to token-scale spacing"
  - "All interactive elements meet 44dp minimum touch target"
  - "Visual consistency across all tabs verified on 15.6-inch 1920x1080"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: ["4/8/12/16/24dp token scale applied project-wide in all KV files"]

key-files:
  created: []
  modified:
    - "src/dmccodegui/ui/run.kv"
    - "src/dmccodegui/ui/flat_grind/run.kv"
    - "src/dmccodegui/ui/serration/run.kv"
    - "src/dmccodegui/ui/convex/run.kv"
    - "src/dmccodegui/ui/axes_setup.kv"
    - "src/dmccodegui/ui/flat_grind/axes_setup.kv"
    - "src/dmccodegui/ui/serration/axes_setup.kv"
    - "src/dmccodegui/ui/convex/axes_setup.kv"

key-decisions:
  - "Delta-C buttons increased to 44dp height, panel resized to accommodate"
  - "bComp +/- buttons verified compliant via parent width context (0.2 * ~300dp = 60dp)"

patterns-established:
  - "Token-scale enforcement: every padding/spacing in the project uses only 4/8/12/16/24dp"
  - "Touch target minimum: all interactive elements >= 44dp on primary axis"

requirements-completed: [UI-01, UI-02]

# Metrics
duration: 12min
completed: 2026-05-04
---

# Phase 31 Plan 03: Machine-Specific KV Spacing + Touch Targets Summary

**All 8 machine-specific KV files standardized to 4/8/12/16/24dp spacing tokens with sub-44dp interactive elements remediated and visually verified on 15.6-inch display**

## Performance

- **Duration:** 12 min
- **Started:** 2026-05-04T06:00:00Z
- **Completed:** 2026-05-04T06:12:00Z
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 8

## Accomplishments
- Remapped all non-token padding/spacing values in 4 run.kv files and 4 axes_setup.kv files to the standardized 4/8/12/16/24dp scale
- Fixed all sub-44dp interactive elements: Delta-C arrow buttons (28dp to 44dp), section count buttons (24dp to 44dp), stone comp buttons (40dp to 44dp), CardFrame control rows (30dp to 44dp)
- Human visual verification confirmed no layout regressions on 15.6-inch 1920x1080 target display

## Task Commits

Each task was committed atomically:

1. **Task 1: Spacing tokens + touch targets in run screens** - `4526ac2` (feat)
2. **Task 2: Spacing tokens in axes_setup screens + final audit** - `ad612c1` (feat)
3. **Task 3: Visual verification checkpoint** - approved by user (no commit needed)

## Files Created/Modified
- `src/dmccodegui/ui/run.kv` - Base run screen: token spacing + 44dp touch targets
- `src/dmccodegui/ui/flat_grind/run.kv` - Flat grind run: token spacing + 44dp Delta-C buttons
- `src/dmccodegui/ui/serration/run.kv` - Serration run: token spacing, bComp buttons verified compliant
- `src/dmccodegui/ui/convex/run.kv` - Convex run: token spacing + 44dp Delta-C/stone comp buttons
- `src/dmccodegui/ui/axes_setup.kv` - Base axes setup: spacing 10dp remapped to 12dp
- `src/dmccodegui/ui/flat_grind/axes_setup.kv` - Flat grind axes setup: spacing standardized
- `src/dmccodegui/ui/serration/axes_setup.kv` - Serration axes setup: spacing standardized
- `src/dmccodegui/ui/convex/axes_setup.kv` - Convex axes setup: spacing standardized

## Decisions Made
- Delta-C panel height increased from 185dp to accommodate 44dp buttons (no flexible layout needed -- fixed height sufficient)
- bComp +/- buttons in serration/run.kv kept at size_hint_x: 0.2 -- parent card width context ensures >44dp computed width
- Spacing token scale locked at 4/8/12/16/24dp (matching Plan 02 decision)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 31 is now complete (3/3 plans done)
- UI-01 and UI-02 requirements fully satisfied
- Ready to proceed to Phase 32 (Per-Machine Parameters) pending convex param specs from customer

## Self-Check: PASSED

- All 8 modified files exist on disk
- Commit 4526ac2 (Task 1) verified in git log
- Commit ad612c1 (Task 2) verified in git log

---
*Phase: 31-bug-fixes-and-ui-polish*
*Completed: 2026-05-04*
