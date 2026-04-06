---
phase: 09-dmc-foundation
plan: 02
subsystem: controller
tags: [galil, dmc, hmi, motion-control]

# Dependency graph
requires: []
provides:
  - DMC program with 8 HMI trigger variables (hmiGrnd..hmiCalc) declared in #PARAMS
  - DMC program with hmiState variable tracking machine state (IDLE=1, GRINDING=2, SETUP=3, HOMING=4)
  - OR conditions in #WtAtRt (5 blocks) and #SULOOP (3 blocks) enabling Python-triggered actions
  - All position array references replaced with scalar variables (startPtA-D, restPtA-D)
affects:
  - 10-state-poll
  - 11-estop-safety
  - 12-run-page-wiring
  - 13-setup-loop

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "HMI one-shot variable pattern: named vars with hmi prefix, default=1, send 0 to trigger, DMC resets to 1 as first line inside triggered block"
    - "hmiState authority: DMC variable is authoritative source of machine state, Python polls it"
    - "OR condition syntax: IF (@IN[N] = 0) | (hmiVar = 0) enables both physical and HMI triggers"

key-files:
  created: []
  modified:
    - "4 Axis Stainless grind.dmc"

key-decisions:
  - "hmiState set in #HOME subroutine itself (hmiState=4 at entry, hmiState=1 before EN) — SULOOP overrides after JS #HOME returns to restore hmiState=3"
  - "Exit-setup button (@IN[32]) gets NO HMI variable — deferred to Phase 13 SETP-08 per CONTEXT.md"
  - "NEWSESS block does not set hmiState (stays IDLE=1) — it's a parameter reset, not a motion state"

patterns-established:
  - "Pattern: HMI trigger variable lifecycle — DMC resets to 1 as the absolute first line inside the triggered IF block, before any SB/JS/motion command"
  - "Pattern: hmiState transitions tied to trigger variable lifecycle at every state boundary"

requirements-completed: [DMC-02, DMC-03, DMC-04, DMC-05]

# Metrics
duration: 2min
completed: 2026-04-06
---

# Phase 09 Plan 02: DMC HMI Integration Summary

**Galil DMC program modified with 8 HMI trigger variables, hmiState machine-state tracking, OR conditions on all physical button checks, and position arrays converted to individual scalar variables**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-06T03:38:19Z
- **Completed:** 2026-04-06T03:40:34Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Removed DM startPt[4], DM restPt[4], DM hmiBtn[40] array declarations and replaced with 9 scalar variable declarations (8 HMI triggers + hmiState) and 8 position scalars in #PARAMS
- Added OR conditions to all 5 #WtAtRt IF blocks and all 3 #SULOOP IF blocks (jog, home, varcalc), enabling Python to trigger any machine action by writing 0 to the corresponding variable
- Replaced all startPt[n] and restPt[n] indexed array references with scalar names across #SETREST, #SETSTR, #GOREST, #GOSTR, #MOREGRI, #LESSGRI subroutines

## Task Commits

Each task was committed atomically:

1. **Task 1: Modify #PARAMS — declare HMI variables and convert arrays to scalars** - `ba7c102` (feat)
2. **Task 2: Modify #WtAtRt, #SULOOP, subroutines — add OR conditions, hmiState, and scalar refs** - `7bd3de9` (feat)

**Plan metadata:** `(pending)` (docs: complete plan)

## Files Created/Modified
- `4 Axis Stainless grind.dmc` - Added HMI trigger variable declarations, hmiState tracking, OR conditions on all button check IF blocks, and scalar variable replacements throughout subroutines

## Decisions Made
- hmiState is set in #HOME subroutine at entry (hmiState=4) and before EN (hmiState=1). The #SULOOP call overrides the end-of-HOME reset by setting hmiState=3 after JS #HOME returns. This covers both standalone #HOME calls from #AUTO and setup-context calls from #SULOOP.
- NEWSESS block keeps hmiState=1 (IDLE) throughout — a new-session reset is not a motion state.
- Exit-setup button (@IN[32]) gets no HMI variable per plan specification (deferred to Phase 13).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DMC program is now the hard prerequisite foundation for all HMI wiring phases
- Phase 10 (State Poll) can implement Python polling of hmiState using the STATE_* constants from dmc_vars.py
- Phase 12 (Run Page Wiring) can wire HMI buttons using the one-shot variable pattern
- Phase 13 (Setup Loop) can wire jog/home/varcalc buttons using the same pattern
- Hardware validation required: upload modified DMC file to real controller to confirm OR condition syntax, hmiState reads, and scalar variable names are accepted

## Self-Check: PASSED

- `4 Axis Stainless grind.dmc` — FOUND
- `09-02-SUMMARY.md` — FOUND
- Task 1 commit `ba7c102` — FOUND
- Task 2 commit `7bd3de9` — FOUND

---
*Phase: 09-dmc-foundation*
*Completed: 2026-04-06*
