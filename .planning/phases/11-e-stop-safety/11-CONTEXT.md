# Phase 11: E-STOP Safety - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

The stop path halts motion within 200ms from any screen, is never queued behind normal controller jobs, and all motion-triggering buttons are gated on real controller state. A recovery button restarts the DMC program after E-STOP. Validated on hardware before any motion commands are wired (Phases 12-13).

</domain>

<decisions>
## Implementation Decisions

### Stop delivery path
- Priority queue approach: add `submit_urgent()` to jobs.py that interrupts the in-flight job (not just queue-jump)
- After E-STOP sends ST, close+reopen the gclib handle (GClose then GOpen) to guarantee clean state
- Stay connected after E-STOP — do not disconnect. Handle is reopened and ready for recovery commands
- Single gclib handle maintained — no dual-handle approach (avoids hardware validation risk)

### E-STOP vs Stop/Pause (two buttons)
- **E-STOP** (StatusBar, always visible): sends ST ABCD + HX — kills motor motion AND DMC program thread. Priority path via submit_urgent(), interrupts in-flight jobs
- **Stop** (Run page only): sends ST ABCD only — halts motor motion, DMC program thread stays alive but cycle is cancelled. Only visible/enabled during active motion (GRINDING or HOMING states)
- After either stop type, operator must restart the cycle — no partial-cycle resume
- E-STOP does NOT disconnect from controller (changed from current code behavior)

### Motion gate logic
- Disable motion-triggering buttons (Start Grind, Go To Rest, Go To Start, More Stone, Less Stone) when hmiState is GRINDING (2) or HOMING (4)
- Also disable all motion buttons when controller is disconnected
- SETUP (3) handled separately by existing setup mode logic (not this phase)
- Disabled buttons use standard Kivy dimmed state — no overlay text or reason labels
- Button state updates on next poll tick (~100ms at 10Hz) via MachineState subscription — no immediate-on-send optimistic disable

### Post-stop recovery
- RECOVER button in StatusBar, next to E-STOP — always visible but disabled until needed
- RECOVER enables when DMC program is not running (post E-STOP or post HX)
- Recovery sequence: sends XQ #AUTO to restart DMC program from the top (#CONFIG → #PARAMS → #COMPED → #HOME → #MAIN → waiting loop)
- One-tap confirmation required: tap RECOVER → "Restart machine program?" dialog → sends XQ #AUTO on confirm
- No role restriction on RECOVER — any logged-in user can restart after E-STOP

### Claude's Discretion
- Exact implementation of submit_urgent() interrupt mechanism (threading approach, cancellation signal)
- How to detect "DMC program not running" state for RECOVER button enable/disable
- RECOVER button styling (color, size) — should be distinct from E-STOP but clearly related
- Error handling if XQ #AUTO fails after recovery attempt
- Whether Stop button on Run page also uses submit_urgent() or regular submit()

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `e_stop()` in main.py:432 — existing E-STOP handler, currently sends AB via jobs.submit(). Needs rewrite to use submit_urgent() with ST ABCD + HX
- `StatusBar` (status_bar.py/kv) — already has E-STOP button (always visible, red, 100dp wide). RECOVER button goes next to it
- `MachineState` (app_state.py) — has dmc_state field from 10Hz poller, subscribe() pattern for button gating
- `JobThread` (utils/jobs.py) — single FIFO worker. Needs submit_urgent() with interrupt capability added
- `GalilController` (controller.py) — cmd() method for ST/HX commands, GClose/GOpen for handle reset

### Established Patterns
- All gclib calls off UI thread via jobs worker
- Single gclib handle serialized through FIFO worker
- 10Hz poll clock separate from 5Hz plot clock
- MachineState.subscribe() with lambda callbacks for state change notification
- Kivy disabled property for button gating

### Integration Points
- `utils/jobs.py`: add submit_urgent() method with interrupt-in-flight capability
- `main.py`: rewrite e_stop() to use submit_urgent(), add recover() method with XQ #AUTO
- `screens/status_bar.py` + `ui/status_bar.kv`: add RECOVER button next to E-STOP, wire enable/disable to MachineState
- `screens/run.py` + `ui/run.kv`: add Stop button (visible during motion only), wire motion gate to disable motion buttons
- `app_state.py`: may need "program_running" derived property for RECOVER button gate

</code_context>

<specifics>
## Specific Ideas

- Recovery button should send XQ #AUTO to restart the full DMC program flow — user wants a clean slate, not a shortcut to main loop
- Both knife counts (ctSesKni, ctStnKni) and position data will reset naturally when DMC program restarts via #AUTO
- The RECOVER button should be something operators know about BEFORE an emergency — always visible, just grayed out until needed

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 11-e-stop-safety*
*Context gathered: 2026-04-06*
