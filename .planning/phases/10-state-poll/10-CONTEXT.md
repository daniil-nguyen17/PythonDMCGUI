# Phase 10: State Poll - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

The HMI reads authoritative state from the controller on every poll tick — axis positions display real values, connection loss is detected within 2 seconds, knife counts reflect controller data, and auto-reconnect resumes polling without app restart. All verified against the real controller before any write commands are sent (Phases 11-13).

</domain>

<decisions>
## Implementation Decisions

### Poll architecture
- Single app-wide poller in main.py replaces RunScreen's per-screen _do_poll
- 10 Hz poll tick using Clock.schedule_interval, submits work to background jobs thread
- Python reads _TP (tell position) directly for axis positions — no DMC-side position variables needed
- Python reads hmiState, ctSesKni, ctStnKni via MG commands on named variables
- All data read in one batch per tick: hmiState + _TPA/_TPB/_TPC/_TPD + ctSesKni + ctStnKni

### DMC thread 2 label (new)
- New DMC label running on thread 2 handles hmiState management and knife counting
- Thread 2 owns hmiState — it observes HMI trigger variables (hmiGrnd, hmiSetp, etc.) and sets hmiState based on which trigger fired (0 = action starting), then watches for reset to 1 (action complete, return to IDLE)
- Thread 2 does NOT write to trigger variables — purely observes them
- Thread 2 loop uses WT (wait) delay between iterations to avoid hogging controller cycles
- stoneKnf counter (ctStnKni) increments alongside ctSesKni at grind cycle completion, resets to 0 in #NEWSESS when hmiNewS fires

### Connection loss & recovery
- Disconnect detection: 3 consecutive poll failures marks as disconnected (~300ms at 10 Hz)
- UI on disconnect: freeze last known axis positions + red "DISCONNECTED (Xs)" banner with elapsed time counter
- Poller keeps retrying at full 10 Hz during disconnect — no backoff
- On disconnect: close the gclib handle. On reconnect attempt: try GOpen to reopen
- Auto-reconnect: silent, no operator action needed. When a poll succeeds, clear disconnect banner and resume normal display
- On reconnect: just resume polling, no program-running verification. hmiState=0 (uninitialized) signals if DMC program isn't running

### Knife count display
- Two counters visible on the Run page cycle status area:
  - ctSesKni — session knife count (resets on power off)
  - ctStnKni — stone knife count (resets on stone change via hmiNewS)
- Both visible so operator and passersby can see productivity
- DMC variable name for stone count: `ctStnKni` (matches ct-prefix pattern of ctSesKni)
- stoneKnf variable added to DMC program in THIS phase (not deferred to Phase 12)
  - Declared in #PARAMS
  - Incremented alongside ctSesKni in grind completion block
  - Reset to 0 in #NEWSESS subroutine

### Data flow to MachineState
- MachineState is the central hub: poller writes all data to MachineState fields, screens subscribe
- Replace cycle_running bool with a @property derived from dmc_state == STATE_GRINDING
- New flat integer fields on MachineState: session_knife_count (int = 0), stone_knife_count (int = 0)
- Notify subscribers on every poll tick (10 Hz) — no change detection, screens filter as needed
- RunScreen's existing _do_poll/_apply_ui gets replaced by MachineState subscription

### Claude's Discretion
- Exact DMC thread 2 label structure and WT delay value
- How to structure the poller module (hmi/poll.py or similar)
- MachineState subscription mechanism details (keep existing or enhance)
- Disconnect elapsed time counter implementation
- How to handle the transition from RunScreen's old poll to new centralized poll

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MachineState` (app_state.py): already has dmc_state field, pos dict, connected bool, subscribe() pattern — extend with knife count fields and derived cycle_running
- `jobs.submit()` / `jobs.schedule()` (utils/jobs.py): background thread work queue, single FIFO worker — poller will submit through this
- `GalilController` (controller.py): cmd() method for MG queries, is_connected() check, wait_for_ready() for reconnect
- `dmc_vars.py` (hmi/dmc_vars.py): HMI_STATE_VAR, state constants, trigger variable names — poller reads these
- RunScreen `_update_clock` / `_do_poll` / `_apply_ui` pattern: reference for the new centralized poller, will be replaced

### Established Patterns
- All gclib calls off UI thread via jobs.submit(), results posted to main thread via Clock.schedule_once
- Single gclib handle serialized through FIFO worker — no concurrent access
- 10 Hz poll clock separate from 5 Hz plot clock (Phase 3 decision)
- MachineState.subscribe() with lambda callbacks for state change notification

### Integration Points
- `main.py`: uncomment/replace _poll_controller with new centralized poller (currently commented out)
- `app_state.py`: add session_knife_count, stone_knife_count fields; replace cycle_running with derived property
- `dmc_vars.py`: add ctSesKni, ctStnKni constant names
- `screens/run.py`: remove _do_poll/_apply_ui, subscribe to MachineState instead
- `4 Axis Stainless grind.dmc`: add thread 2 label for hmiState management, add ctStnKni variable declaration and increment/reset logic
- `ui/run.kv`: add knife count labels to cycle status area

</code_context>

<specifics>
## Specific Ideas

- Thread 2 in the DMC program observes HMI trigger variables to determine state — this is a passive observer pattern that avoids interfering with the main program thread
- ctStnKni follows the ct-prefix naming pattern established by ctSesKni
- The disconnect banner should show elapsed time (e.g., "DISCONNECTED (5s)") to help operators gauge severity
- Both knife counts should be visible to anyone walking by the machine — prominent placement in cycle status

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-state-poll*
*Context gathered: 2026-04-06*
