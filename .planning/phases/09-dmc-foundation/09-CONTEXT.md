# Phase 9: DMC Foundation - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

The DMC program and Python codebase share a correct, named contract. HMI trigger variables exist in the controller with default=1, OR conditions are live in both the main polling loop (#WtAtRt) and setup loop (#SULOOP), hmiState is set at every state boundary, and Python constants in hmi/dmc_vars.py prevent 8-char name typos. All existing Python screen files are migrated from hardcoded StartPnt/RestPnt strings to the new constants.

</domain>

<decisions>
## Implementation Decisions

### Array name alignment
- Replace startPt[4] and restPt[4] arrays with individual named variables: startPtA, startPtB, startPtC, startPtD, restPtA, restPtB, restPtC, restPtD
- All 4 axes declared for all machine types (unused axes hold 0)
- Remove the unused hmiBtn[40] array from the DMC file
- Computed sequence arrays (deltaD[], deltaC[], bComp[]) remain as indexed arrays — only position points get individual variables
- Python constants use exact DMC names (e.g., constant value is 'startPtA', not a human-friendly alias)
- Phase 9 updates ALL existing Python screen files to use constants from dmc_vars.py — no stale StartPnt/RestPnt strings left behind

### hmiState encoding
- Keep hmiState as a dedicated DMC variable (not derived from trigger variables) — authoritative source for machine state including physical-button-initiated actions
- 4 core states only: IDLE=1, GRINDING=2, SETUP=3, HOMING=4
- hmiState=0 means uninitialized/error (all valid states are nonzero)
- No sub-states for GOING_TO_REST, GOING_TO_START, etc. — those are brief motions under core states
- State transitions tied to trigger variable lifecycle: hmiGrnd=0 triggers GRINDING state, reset to 1 returns to IDLE

### DMC backward compatibility
- OR logic for all triggers: `IF (@IN[29]=0) | (hmiGrnd=0)` — physical buttons AND HMI variables both work
- Simultaneous physical button + HMI trigger is an acceptable race condition (subroutine runs once regardless)
- All OR conditions added in Phase 9 — both #WtAtRt (main loop) and #SULOOP (setup loop) modified in a single pass
- DMC file tracked in repo (already at repo root as '4 Axis Stainless grind.dmc')
- Keep original filename '4 Axis Stainless grind.dmc' — do not rename
- Leave existing DMC header comments as-is — only modify functional code

### Python constants scope
- New file: src/dmccodegui/hmi/dmc_vars.py (new hmi/ package)
- Contains: HMI trigger variable names, hmiState integer constants, position variable names, default values — full integration contract in one file
- Flat Grind only for now — Serration/Convex constants added later when those DMC files arrive
- Parameter variable names (knfThk, fdA, etc.) stay in machine_config.py — they differ per machine type and are already there

### Claude's Discretion
- Exact structure/grouping within dmc_vars.py
- How to organize the hmi/ package __init__.py
- Which screen files need what level of refactoring to use new constants
- DMC OR condition syntax details

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GalilController` (controller.py): existing cmd/upload_array/download_array methods — position variable reads will switch from array ops to individual MG queries
- `GalilTransport` (utils/transport.py): retry/backoff wrapper around gclib — used for all controller I/O
- `MachineState` (app_state.py): needs new `dmc_state` field for hmiState values — currently has `cycle_running` bool which becomes derived
- `axes_setup.py`: already uses `restPtA`/`startPtA` individual variable pattern for writes — ahead of the DMC file

### Established Patterns
- All gclib calls off UI thread via background worker
- Machine config registry in machine_config.py — keyed by type string
- Screen files import controller and call cmd/upload_array/download_array directly

### Integration Points
- `4 Axis Stainless grind.dmc`: add hmi* variable declarations in #PARAMS, OR conditions in #WtAtRt and #SULOOP, hmiState assignments at state boundaries, replace startPt[]/restPt[] arrays with individual vars
- `src/dmccodegui/hmi/dmc_vars.py`: new constants module imported by all screen files
- ~15 screen files referencing StartPnt/RestPnt: migrate to dmc_vars constants
- `app_state.py`: add dmc_state field to MachineState dataclass

</code_context>

<specifics>
## Specific Ideas

- This .dmc file IS the Flat Grind program (despite "SERRATED" in the header). Serration and Convex DMC files will be provided later as separate files.
- The hmi/ package will eventually hold poll.py, commands.py alongside dmc_vars.py — foundation for Phases 10-14.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 09-dmc-foundation*
*Context gathered: 2026-04-06*
