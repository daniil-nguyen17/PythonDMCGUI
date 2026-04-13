# Phase 23: Controller Communication Optimization - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning (updated with MG-from-DMC approach)

<domain>
## Phase Boundary

Optimize controller communication by leveraging DMC-side MG output as the primary data source for positions and state, with batched MG polling as fallback. Add structured MG state messages for sub-ms state transition detection. Harden all gclib connections with production flags and explicit timeouts. Move the MG reader thread to app-wide scope. No new UI features, no new screens, no changes to the HMI one-shot variable pattern.

</domain>

<decisions>
## Implementation Decisions

### Position and State Reads — MG-from-DMC Primary

**Research outcome:** GRecord/GDataRecord is NOT available in the gclib Python wrapper (confirmed via `dir(gclib.py())`). The C API has data record support but the Python bindings don't expose it. GMessage() IS available.

**Primary approach: DMC program emits positions and state via MG messages.**

The DMC program already emits contextual MG messages at different points in the grind cycle. These are the authoritative formats:

| DMC State | MG Format | Axes/Values |
|-----------|-----------|-------------|
| #MAIN idle loop | `IDLING FOR INPUT  A:{_TDA}  B:{_TDB}  C:{_TDC}  D:{_TDD}` | A, B, C, D (all 4) |
| Pre-LI | `PRE-LI  A:{_TDA}  B:{_TDB}` | A, B |
| Running LI | `RUNNING  A:{_TDA}  B:{_TDB}  C:{_TDC}  LM:{_LM}` | A, B, C + LM |
| End reached | `END REACHED  A:{_TDA}  B:{_TDB}  C:{_TDC}  D:{_TDD}` | A, B, C, D |

- Uses _TD (told/desired position), not _TP (actual) — _TD values are fine for operator display
- MG reader thread parses prefix to determine context, extracts values by splitting on axis labels (A:, B:, C:, D:, LM:)
- State and knife counts should also be emitted from DMC (hmiState, ctSesKni, ctStnKni) — add to the #MAIN idle loop MG output
- This eliminates polling commands entirely when DMC program is running

**Fallback: Batched MG polling when DMC program is NOT running.**
- Before XQ #AUTO or after HX, no MG output from DMC
- Centralized poller falls back to batched MG: `MG _TPA,_TPB,_TPC,_TPD,hmiState,ctSesKni,ctStnKni,_XQ`
- Single mega-batch command (8 values in 1 cmd) — down from 8 separate commands
- Fallback also used during connection verification and initial state reads

### Fallback Behavior
- If MG-from-DMC parse fails or DMC isn't running, poller uses batched MG as fallback
- If batched MG parse fails, count as failure toward DISCONNECT_THRESHOLD (existing reconnect path)
- On any read failure (MG or poll), keep last known values (stale-but-real) — never zero defaults
- Always read 4 axes regardless of machine type (Serration ignores D=0)
- Unify both poll.py and RunScreen._tick_pos to use the same read method
- Poll rates stay as-is: 10 Hz centralized, 5 Hz RunScreen (1 Hz during grind)

### MG State Messages
- MG reader thread moves to app-wide scope (not just RunScreen) — Run, AxesSetup, and Parameters all need it
- DMC program emits structured STATE:N messages at state transitions — supplements polling, doesn't replace it
- MG reader dispatches state messages to handlers immediately (sub-ms detection), poller confirms every tick as ground truth
- Structured state messages (STATE:N and position lines) filtered out of RunScreen controller log panel — only freeform MG messages show in operator log

### Connection Hardening
- Always use --direct flag for production connections (hard-coded, not configurable)
- --direct and explicit timeouts apply to BOTH handles (primary command handle and MG reader handle)
- reset_handle() (E-STOP recovery) also uses --direct and configured timeout
- Timeout values: 1000ms primary, 500ms MG handle (confirmed safe by research — matches existing MG reader GTimeout(500) pattern)
- Timeout errors treated same as other failures — count toward DISCONNECT_THRESHOLD (3 consecutive failures)
- Log connection flags on connect: "[CTRL] Connected to {address} --direct, timeout={ms}ms" for field debugging

### Claude's Discretion
- STATE:N message format design — based on DMC MG command constraints
- Error handling granularity within position message parsing
- MG reader thread architecture (standalone module vs extension of poll.py)
- How to detect DMC-program-running state for MG-vs-poll switching
- GTimeout API usage patterns

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `hmi/poll.py` ControllerPoller: Centralized 10 Hz poller — becomes fallback-only when MG-from-DMC is active
- `screens/base.py` BaseRunScreen: _mg_reader_loop, _mg_thread, _mg_stop_event — duplicated 3x across run screens, extractable to app-wide module
- `utils/jobs.py`: submit() / submit_urgent() priority queue — commands still go through here
- `controller.py` GalilController: cmd(), connect(), reset_handle() — connection hardening targets
- `GMessage()`: Available in Python wrapper — the key API for receiving DMC MG output

### Established Patterns
- Disciplined single-channel: ALL GCommand traffic through JobThread worker
- Two-handle architecture: primary (-MG 0) for commands, MG (--subscribe MG) for unsolicited messages
- Clock.schedule_once for main-thread state writes from background reads
- DMC MG output already uses contextual prefixes (PRE-LI, RUNNING, END REACHED, IDLING FOR INPUT)

### Integration Points
- `poll.py _do_read()`: Refactor to batched MG (fallback mode)
- `controller.py connect()` / `reset_handle()`: Add --direct and timeout
- `base.py _mg_reader_loop()`: Extract to app-wide MgReader module
- `main.py`: MgReader lifecycle (start/stop with app)
- DMC file: Add MG output lines for positions/state in #MAIN and state transitions
- `dmc_vars.py`: Constants for MG prefixes and batch command

</code_context>

<specifics>
## Specific Ideas

- GDataRecord4000 struct exists in C gclib for DMC-4040 (512 bytes, all axis positions + status) but Python wrapper doesn't expose GRecord/data record subscription — confirmed dead end
- DMC program already emits MG with axis labels (A:, B:, C:, D:, LM:) — MG reader can parse these naturally
- _TD (told position) is sufficient for operator display — no need to poll _TP separately
- MG reader should handle variable-format messages (different axes reported at different stages)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 23-controller-communication-optimization*
*Context gathered: 2026-04-13 (updated with MG-from-DMC approach)*
