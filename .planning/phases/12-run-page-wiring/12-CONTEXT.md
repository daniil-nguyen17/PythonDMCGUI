# Phase 12: Run Page Wiring - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire all operator Run page buttons to real DMC subroutines via the HMI one-shot variable pattern. The Run page has four action buttons: Start Grind, Stop, More Stone, Less Stone. Go To Rest, Go To Start, and New Session are NOT on the Run page (removed/deferred).

</domain>

<decisions>
## Implementation Decisions

### Button inventory (reduced from original scope)
- Run page buttons: Start Grind, Stop, More Stone, Less Stone — that's it
- Go To Rest and Go To Start REMOVED — these are either inside the grind label or part of setup mode, not standalone Run page actions
- New Session (stone change) MOVED to Axes Setup page — belongs with setup workflow (Phase 13)
- Stop button already wired in Phase 11 (ST ABCD via submit_urgent)

### Start Grind
- Sends `hmiGrnd=0` via one-shot pattern — no XQ command, just set the trigger variable
- DMC polling loop (#WtAtRt) detects the trigger, runs the grind cycle, ZS clears stack at end
- DMC resets hmiGrnd to 1 as first action inside the triggered block
- START/PAUSE toggle replaced with a simple Start Grind button — no pause concept
- Plot buffer clears on Start Grind press (fresh trace per cycle)
- Button does NOT optimistically disable — waits for poll tick to confirm hmiState=GRINDING (Phase 11 decision: no optimistic disable)
- All roles can press Start Grind (Operator, Setup, Admin)

### More Stone / Less Stone
- Sends `hmiMore=0` or `hmiLess=0` via one-shot pattern
- DMC subroutine modifies startPtC: `startPtC = startPtC + (cpmC * 0.001)` for More, `startPtC = startPtC - (cpmC * 0.001)` for Less
- BV (burn variables) runs inside the DMC subroutine — each press persists to flash immediately (exception to general "no automatic BV" guideline — operator expects persistence)
- Feedback: read startPtC BEFORE firing trigger, wait ~300-500ms fixed delay (subroutine is short: SB, math, MG, WT 200, BV, EN), read startPtC AFTER — display old and new value to operator
- Buttons disabled during active motion (GRINDING or HOMING) — follows existing motion gate from Phase 11
- All roles can press More/Less Stone (Operator, Setup, Admin)

### Live A/B plot
- Plot feeds from poller data (10 Hz) during cycle_running (dmc_state == STATE_GRINDING)
- Plot redraws at 5 Hz on separate clock (existing pattern)
- Buffer clears when Start Grind is pressed
- No changes needed to plot infrastructure — it already reads real axis positions from MachineState

### Claude's Discretion
- Start Grind button styling (replaces the START/PAUSE toggle)
- Exact delay value for More/Less Stone readback (300-500ms range)
- How to display the startPtC before/after feedback (toast, label update, log entry)
- Error handling if trigger fire fails (controller disconnected, etc.)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `dmc_vars.py` (hmi/dmc_vars.py): HMI_GRND, HMI_MORE, HMI_LESS constants with HMI_TRIGGER_FIRE=0 and HMI_TRIGGER_DEFAULT=1
- `jobs.submit()` (utils/jobs.py): normal queue for Start Grind and More/Less Stone triggers
- `jobs.submit_urgent()`: already used by Stop button (Phase 11)
- `MachineState.motion_active` property: gates buttons via Kivy binding
- `GalilController.cmd()`: sends `f"{HMI_GRND}={HMI_TRIGGER_FIRE}"` pattern
- `STARTPT_C` constant in dmc_vars.py: for reading back startPtC value

### Established Patterns
- One-shot trigger: `controller.cmd(f"{VAR}={HMI_TRIGGER_FIRE}")` — write 0 to fire
- UI update from worker: `Clock.schedule_once(lambda *_: ...)` to post results to main thread
- Motion gate: Kivy `disabled` property bound to `motion_active` BooleanProperty
- Button callbacks define inner function, submit to jobs worker

### Integration Points
- `screens/run.py`: replace XQ #CYCLE with hmiGrnd=0, replace START/PAUSE toggle with simple Start button, add More/Less Stone one-shot wiring with readback
- `ui/run.kv`: remove Go To Rest, Go To Start buttons; remove PAUSE toggle state; update button layout
- `screens/run.py` on_start_pause_toggle: refactor to simple on_start_grind callback
- More/Less Stone callbacks: currently modify in-memory offsets — replace with hmiMore/hmiLess trigger + startPtC readback

</code_context>

<specifics>
## Specific Ideas

- The DMC #MOREGRI subroutine structure: SB 3 (set bit), startPtC math, MG message, WT 200, BV, EN — total ~200-300ms
- #LESSGRI is the mirror: startPtC = startPtC - (cpmC * 0.001)
- The grind cycle runs fully autonomously once triggered — ZS clears stack at end, hmiState returns to IDLE
- No mid-cycle pause/resume — Stop halts, operator must restart the full cycle

</specifics>

<deferred>
## Deferred Ideas

- **New Session (stone change) on Axes Setup page** — Phase 13. Controller waits ~30 minutes for stone change, resets ctStnKni count, resets startPtC to fresh stone position. Two-step confirmation, Setup/Admin role required. Uses hmiNewS=0 trigger.
- **Go To Rest / Go To Start** — Not standalone HMI actions. Part of grind label or setup mode. No dedicated HMI buttons needed.

</deferred>

---

*Phase: 12-run-page-wiring*
*Context gathered: 2026-04-06*
