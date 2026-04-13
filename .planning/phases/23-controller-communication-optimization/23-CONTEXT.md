# Phase 23: Controller Communication Optimization - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Optimize the controller poll loop to minimize per-tick gclib command count, add structured MG state messages for sub-ms state transition detection, and harden all gclib connections with production flags and explicit timeouts. The poll loop, RunScreen position poll, and MG reader thread are in scope. No new UI features, no new screens, no changes to the HMI one-shot variable pattern.

</domain>

<decisions>
## Implementation Decisions

### Position Read Batching
- Research QR (query record), DR (data record), and RP (report position) as alternatives to individual MG commands before committing to an approach
- Verify each alternative fits the disciplined single-channel architecture and won't bottleneck communication
- Batched MG (MG _TPA,_TPB,_TPC,_TPD) is the safe fallback if alternatives don't pan out
- Best-fit approach wins — researcher picks based on bandwidth/latency tradeoff analysis
- If batched MG parse fails, count as failure toward DISCONNECT_THRESHOLD (existing reconnect path)
- Always read 4 axes regardless of machine type (Serration ignores D=0) — poller stays generic
- Unify both poll.py (centralized poller) and RunScreen._tick_pos to use the same read method
- Poll rates stay as-is: 10 Hz centralized, 5 Hz RunScreen (1 Hz during grind)
- On position read failure, keep last known values (stale-but-real) until disconnect threshold fires

### Variable Batching
- Batch hmiState, ctSesKni, ctStnKni, and _XQ into a single MG command
- Combine with position batch into a single mega-batch: MG _TPA,_TPB,_TPC,_TPD,hmiState,ctSesKni,ctStnKni,_XQ — one command reads all 8 values per tick (down from 8 separate commands)
- On variable batch failure, keep last known values (not zero defaults) to prevent state mismatch
- Apply same batching to RunScreen._tick_pos — both poller and RunScreen use identical batched reads
- Note: mega-batch approach applies if research confirms batched MG is the best method. If QR/DR/RP is chosen for positions, variables may still use batched MG separately

### MG State Messages
- MG reader thread moves to app-wide scope (not just RunScreen) — both Run and AxesSetup need live state, Parameters reads some variables
- DMC program emits structured MG messages at state transitions — format is Claude's discretion
- MG state messages supplement polling, not replace it — MG gives sub-ms detection, poller confirms every tick as ground truth
- Structured state messages filtered out of RunScreen controller log panel — only freeform MG messages show in operator log

### Connection Hardening
- Always use --direct flag for production connections (hard-coded, not configurable)
- --direct and explicit timeouts apply to BOTH handles (primary command handle and MG reader handle)
- reset_handle() (E-STOP recovery) also uses --direct and configured timeout
- Timeout values: let researcher determine safe values by checking gclib docs and controller response times
- Timeout errors treated same as other failures — count toward DISCONNECT_THRESHOLD (3 consecutive failures)
- Log connection flags on connect: "[CTRL] Connected to {address} --direct, timeout={ms}ms" for field debugging

### Claude's Discretion
- MG message format design (KEY:VALUE, tagged, etc.) — based on DMC MG command constraints
- Error handling granularity within the mega-batch parse
- MG reader thread architecture (standalone module vs extension of poll.py)
- GTimeout API usage patterns

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `hmi/poll.py` ControllerPoller: Centralized 10 Hz poller with Clock.schedule_interval, jobs.submit pattern, disconnect threshold logic
- `screens/base.py` BaseRunScreen: Subscribe-on-enter / unsubscribe-on-leave lifecycle, _mg_reader_loop, _mg_thread, _mg_stop_event
- `utils/transport.py` GalilTransport: Retry/backoff wrapper around GCommand, could be extended for batched reads
- `utils/jobs.py`: submit() / submit_urgent() priority queue system — all controller I/O routed through here
- `controller.py` GalilController: cmd() wrapper with logging suppression for status commands, connect/disconnect/reset_handle lifecycle

### Established Patterns
- Disciplined single-channel: ALL GCommand traffic through JobThread worker (no rogue threads)
- HMI one-shot variable pattern: send var=0 to trigger, DMC resets to 1
- Two-handle architecture: primary (-MG 0) for commands, MG (--subscribe MG) for unsolicited messages
- Status command suppression in cmd() logging (is_status_command check)
- Clock.schedule_once for main-thread state writes from background reads

### Integration Points
- `poll.py _do_read()` lines 121-159: Main optimization target — 8 individual reads become 1
- `controller.py connect()` line 119: GOpen call where --direct flag needs to be added
- `controller.py reset_handle()` line 169: GOpen call that also needs --direct
- `base.py _mg_reader_loop()`: MG thread that needs to move to app-wide scope
- `main.py`: MG reader lifecycle management if it becomes app-wide
- `dmc_vars.py`: Constants for variable names used in batched MG commands

</code_context>

<specifics>
## Specific Ideas

- GRecord/GRecord() is NOT available in gclib Python wrapper — documented in project memory. Research QR, DR, RP as alternatives
- The operator's concern about state mismatch: if variable reads fail and defaults are used, buttons could be momentarily enabled incorrectly. Solution: keep last known values on failure
- AxesSetupScreen updates positions during jog moves — MG reader or state detection must be available beyond RunScreen
- Parameters screen reads some variables — app-wide approach ensures coverage

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 23-controller-communication-optimization*
*Context gathered: 2026-04-13*
