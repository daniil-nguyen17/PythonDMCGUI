# Phase 13: Setup Loop - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire Setup page entry, homing, jog, teach points, parameters write, varcalc trigger, new session, and exit — all from the touchscreen. A Setup/Admin user can perform a complete setup workflow entirely from the HMI without touching physical buttons. The DMC #SULOOP gets new HMI OR conditions for Go To Rest, Go To Start, and exit-setup. Python screens get wired to real controller commands using the established one-shot variable pattern.

</domain>

<decisions>
## Implementation Decisions

### Jog approach
- Python keeps its own PR/BG step jog — does NOT use hmiJog trigger or DMC #WheelJg
- DMC #WheelJg remains exclusively for the physical handwheel
- Jog buttons gated on hmiState=3 (SETUP) — disabled unless controller is in setup mode
- Jog buttons disabled during active motion (while previous jog in progress, _BG{axis} != 0) — prevents queuing multiple moves
- Step sizes remain 1mm, 5mm, 10mm as currently implemented

### Teach points (rest/start)
- Keep Python direct write approach: read _TD{axis}, write restPt/startPt vars, send BV, read back to confirm
- DMC #SETREST/#SETSTR stay exclusively for hardware button saves inside #JogLoop
- No new HMI trigger variables needed for teach

### Quick actions wiring
- Go To Rest and Go To Start: add new HMI trigger variables to DMC (hmiGoRs, hmiGoSt — within 8-char limit)
- Add OR conditions in DMC #SULOOP: `IF (hmiGoRs=0)` → `JS #GOREST`, `IF (hmiGoSt=0)` → `JS #GOSTR`
- Home All: already has hmiHome=0 in #SULOOP — just wire Python to fire it instead of swHomeAll
- Replace swGoRest/swGoStart/swHomeAll software variables with proper HMI triggers in Python
- All three quick actions available only on Axes Setup screen in Setup mode (not on Run page)

### Parameters → varcalc integration
- "Apply to Controller" auto-fires hmiCalc=0 after writing all params — one button does write + recalc + readback
- After firing hmiCalc=0, wait ~500ms for DMC #VARCALC to complete, then read all param values back from controller
- No separate "Recalculate" button needed — Apply handles the full workflow

### New Session (stone change)
- Button lives on Axes Setup screen only — fits setup workflow
- Setup/Admin role required (Operator cannot trigger)
- Single confirmation dialog: "Start new session? This will home all axes and reset knife counts." → Confirm/Cancel
- Fires hmiNewS=0 on confirm — DMC #NEWSESS handles homing, count reset, BV
- Knife count display updates via normal 10 Hz poll tick (no optimistic zero) — consistent with controller-is-truth pattern

### Setup enter/exit
- Entry: fire hmiSetp=0 in on_pre_enter (existing behavior — both AxesSetup and Parameters screens)
- Exit: add new DMC variable hmiExSt (exit setup) with OR condition in #SULOOP alongside @IN[32]
- Python fires hmiExSt=0 in on_leave — but ONLY when navigating to a non-setup screen (Run, Profiles, Users)
- Navigating between Axes Setup ↔ Parameters stays in setup mode — no exit/re-enter cycle
- Similarly, on_pre_enter should NOT fire hmiSetp=0 if already in setup mode (hmiState=3)
- DMC exits #SULOOP on hmiExSt=0, returns to #MAIN, sets hmiState=1 (IDLE)

### Claude's Discretion
- New Session button placement and styling on Axes Setup screen
- Confirmation dialog visual design
- Exact wait time for varcalc completion (within ~500ms range)
- How to detect "already in setup mode" for tab-switch optimization
- Error handling if any trigger fire fails (controller disconnected, etc.)
- Whether to add hmiGoRs/hmiGoSt to #WtAtRt as well or only #SULOOP

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `screens/axes_setup.py`: Full jog (PR/BG + poll _BG), teach (read _TD, write vars, BV, readback), mode toggle — all implemented
- `screens/parameters.py`: Full read/write/validate/apply cycle, dirty tracking, role-based readonly — all implemented
- `hmi/dmc_vars.py`: HMI_SETP, HMI_HOME, HMI_JOG, HMI_CALC, HMI_NEWS constants, all position var constants
- `utils/jobs.py`: submit() for normal operations, submit_urgent() for safety-critical
- `hmi/poll.py`: 10 Hz poller reads hmiState — will reflect SETUP/IDLE transitions
- `app_state.py`: MachineState with dmc_state, subscribe() pattern for UI gating

### Established Patterns
- One-shot trigger: `controller.cmd(f"{VAR}={HMI_TRIGGER_FIRE}")` — write 0 to fire
- UI update from worker: `Clock.schedule_once(lambda *_: ...)` to post results to main thread
- Motion gate: Kivy `disabled` property bound to state conditions
- BV (burn to flash) only on explicit user save actions (teach points, apply params)

### Integration Points
- `4 Axis Stainless grind.dmc` #SULOOP: add OR conditions for hmiGoRs, hmiGoSt, hmiExSt
- `4 Axis Stainless grind.dmc` #PARAMS: declare hmiGoRs, hmiGoSt, hmiExSt with default=1
- `hmi/dmc_vars.py`: add HMI_GO_REST, HMI_GO_START, HMI_EXIT_SETUP constants
- `screens/axes_setup.py`: replace swGoRest/swGoStart/swHomeAll with HMI triggers, add New Session button + dialog, add setup-state gate for jog, add jog-in-progress disable
- `screens/parameters.py`: add hmiCalc=0 after apply_to_controller, add readback after varcalc delay
- Both setup screens: smart enter/exit logic (don't re-enter if already SETUP, don't exit if navigating to other setup screen)

</code_context>

<specifics>
## Specific Ideas

- DMC #SULOOP exit check: `IF (@IN[32]=0) | (hmiExSt=0)` → EN (return from #SETUP to #MAIN)
- DMC resets hmiExSt=1 as first line in the exit block (consistent with one-shot pattern)
- #GOREST and #GOSTR have safe axis ordering built in (B away first for rest, etc.) — Python must NOT replicate this, let DMC handle it
- The swGoRest/swGoStart/swHomeAll software variables can be removed from Python — they were never functional
- Python PR/BG jog and DMC #WheelJg coexist safely because they operate at different times: HMI jog when operator uses touchscreen, handwheel jog when operator uses physical wheel — both only available in SETUP mode

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 13-setup-loop*
*Context gathered: 2026-04-06*
