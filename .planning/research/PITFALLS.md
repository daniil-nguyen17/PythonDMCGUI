# Pitfalls Research

**Domain:** HMI-controller integration — adding gclib/DMC communication to existing Kivy GUI for industrial grinding machine
**Researched:** 2026-04-06
**Confidence:** HIGH for gclib/threading pitfalls (from official Galil docs + direct codebase analysis); MEDIUM for timing-specific scenarios (from industrial HMI domain knowledge + code pattern analysis)

---

## Critical Pitfalls

Mistakes that cause safety incidents, machine damage, or require full rewrites.

---

### Pitfall 1: Sending HMI Trigger While Physical Button Already Queued in DMC — Double Action

**What goes wrong:**
The DMC polling loop at `#WtAtRt` checks both `@IN[29]` (physical Go Grind button) and `hmiGrnd` (HMI variable) as separate OR conditions. If the operator presses the physical button at the same moment the HMI submits `hmiGrnd=0`, the DMC program enters `#GRIND` once for the physical button on the current polling cycle, then jumps back to `#WtAtRt`, then immediately enters `#GRIND` again on the very next cycle because `hmiGrnd` is still 0 (the HMI hasn't reset it yet). The machine attempts to start a second grind cycle while still in — or just returning from — the first.

**Why it happens:**
The DMC program is a tight `WT 100` polling loop. The HMI sets `hmiGrnd=0` via a background `jobs.submit()` call. There is a window of ~100–300 ms between when the GUI submits the command and when the DMC program resets `hmiGrnd=1` after entering the triggered subroutine. A physical button press landing in that window fires the action twice.

**Concrete scenario:**
1. Operator taps "Start Grind" on HMI — GUI posts `jobs.submit` → queued in jobs FIFO
2. Operator's colleague also presses the physical Go Grind button 50 ms later
3. DMC sees physical button, enters `#GRIND` (long operation), returns to `#WtAtRt`
4. `hmiGrnd` is still 0 because GUI's `GCommand("hmiGrnd=0")` arrived and DMC reset it to 1, BUT the HMI hasn't confirmed the reset and may re-send 0 on the next status poll cycle
5. Machine enters `#GRIND` from a non-rest position — tooling or knife damage

**How to avoid:**
- HMI trigger variables must be fire-and-forget, not level-held. Send `hmiGrnd=0` exactly once per user tap. Never send it again until the operator presses the button again.
- Implement an optimistic motion lock in the GUI: when Start Grind is tapped, immediately set a `_hmi_command_pending` flag in Python and disable the button. Do NOT re-enable it until the status poll confirms the controller is back in `#MAIN` (not in `#GRIND`).
- On the DMC side, the OR condition pattern must be: `IF (@IN[29]=0) OR (hmiGrnd=0)` then immediately `hmiGrnd=1` as the very first statement in the triggered block — before any motion begins. This is the one-shot reset. Never let the HMI variable stay at 0 for more than one polling cycle.

**Warning signs:**
- GUI button sends `hmiGrnd=0` from a scheduled/polling callback rather than directly from a tap handler
- HMI tap handler is not debounced and can fire multiple times for one touch
- GUI does not disable the Start button immediately after sending the trigger
- The DMC program resets `hmiGrnd=1` after a long motion sequence rather than at the start of the triggered block

**Phase to address:**
DMC program modification phase (modifying `4 Axis Stainless grind.dmc`) — the one-shot reset placement is a DMC change, not a Python change. The Python optimistic lock is an HMI phase change.

---

### Pitfall 2: Sending Motion Commands During Active Grind Cycle — Controller State Corruption

**What goes wrong:**
The RunScreen currently calls `self.controller.cmd("XQ #CYCLE")` when Start is pressed (existing stub) and `self.controller.cmd("XQ #REST")` when Go to Rest is pressed — without checking whether the controller is currently running a motion subroutine. The DMC program does not have queuing — a `XQ` issued while the controller is already executing a thread corrupts the program counter or is silently dropped.

Additionally, the `on_go_to_rest` handler resets `cycle_running = False` on the Python side but the controller may still be mid-grind. Any `hmiGrnd=0` or jog command sent in the window between the Python state change and the actual physical stop completes causes unexpected motion.

**Why it happens:**
`MachineState.cycle_running` in Python is the GUI's guess about what the controller is doing. It is not authoritative. The controller's actual execution state is only readable by polling `MG _XQ` (execution status) or a dedicated DMC status variable. Any command sent in the gap between GUI state and controller state can fire at the wrong time.

**Concrete scenario:**
1. Operator starts a grind cycle — `cycle_running = True` on GUI
2. Network glitch delays the poll for 500 ms — GUI still shows "running"
3. Operator taps "Go To Rest" — GUI sets `cycle_running = False`, submits `hmiHome=0`
4. DMC is still mid-vector in `#GRIND` — the hmiHome trigger fires during vector motion
5. Controller tries to execute `#GOREST` subroutine while vector is running — `ST ABCD` interrupts mid-vector, axes stop at arbitrary positions

**How to avoid:**
- Expose a dedicated DMC status variable: `hmiState` (0=idle/main, 1=grinding, 2=setup, etc.). The HMI polls this variable at every cycle instead of guessing from `cycle_running`.
- Gate ALL HMI trigger sends behind: `if hmi_state == HMI_STATE_IDLE` or `if hmi_state == HMI_STATE_GRINDING_COMPLETE` (depending on the command). Never rely solely on the Python `cycle_running` flag.
- "Go To Rest" from the HMI should only be sent when `hmiState` confirms the grind cycle is complete or when the operator has explicitly confirmed E-STOP first.
- The existing `on_start_pause_toggle` that sends `HX` for pause is correct for HMI pause (HX halts execution cleanly). Do not replace it with a trigger variable — `HX` via `GCommand` is immediate; trigger variables have a polling delay.

**Warning signs:**
- Python code gates HMI sends only on `self.cycle_running` (Python-side flag), not on a polled controller state variable
- `XQ #REST` sent without a preceding check of `_XQ` or a controller-side state variable
- "Go To Rest" button is enabled while the grind cycle is actively running
- E-STOP is implemented as an HMI trigger variable instead of a direct `AB` command

**Phase to address:**
HMI trigger wiring phase — requires defining and polling `hmiState` as part of the DMC modifications.

---

### Pitfall 3: E-STOP Implemented as a Trigger Variable or Queued Job — Unacceptable Response Time

**What goes wrong:**
If E-STOP is sent via `jobs.submit(lambda: controller.cmd("hmiEStop=0"))`, the command sits in the FIFO queue behind any currently-running job. A position poll job, a parameter read, or an array download that started before the E-STOP will complete first. On a busy queue this can delay E-STOP by 200–1000 ms. The machine continues moving during that window.

The existing `controller.cmd("AB")` path in the app is correct — `AB` is a direct abort command — but if the E-STOP button's handler goes through `jobs.submit()` rather than calling `controller.cmd()` directly from the main thread, the latency is unacceptable.

**Why it happens:**
The rule "all gclib calls must stay off the UI thread" is correct for normal operation. Developers apply it universally including to E-STOP, not realizing that E-STOP is the one case where queuing behind normal operations is dangerous.

**Concrete scenario:**
1. Operator jog triggers an upload_array call for 250 elements (300–500 ms job)
2. Knife position drifts — operator presses E-STOP
3. E-STOP is posted to `jobs.submit()` — joins queue behind the array upload
4. Array upload completes 400 ms later — E-STOP fires
5. Machine has moved 400 ms worth of grind motion since the tap

**How to avoid:**
- E-STOP must call `controller.cmd("AB")` directly from the Kivy main thread, NOT via `jobs.submit()`. This is the one exception to the "gclib off the main thread" rule.
- The `_connected` guard is sufficient: if connected, call `GCommand("AB")` inline. The UI thread blocks for ~5–10 ms for the AB command to acknowledge — acceptable.
- Alternatively, give E-STOP its own dedicated `gclib.py()` connection handle used only for abort. This handle never has a queue, so it is always immediately available. (MEDIUM confidence — requires opening two GOpen connections to the same controller; verify this is supported by the Galil firmware.)
- Cancel all pending `jobs` after the AB by flushing or restarting the `JobThread`. The existing `jobs.shutdown()` / `jobs.get_jobs()` pattern supports this.
- Never implement E-STOP as a DMC trigger variable. `AB` is the correct command — it is immediate, atomic, and halts all motion.

**Warning signs:**
- E-STOP handler calls `jobs.submit()` or `dmcCommand()`
- E-STOP test: press E-STOP immediately after starting a large array download — does the machine stop within 100 ms?
- `jobs` queue depth is not monitored; a backed-up queue delays all subsequent commands including safety ones
- E-STOP is only wired to one screen (RUN page) rather than the persistent global tab bar

**Phase to address:**
E-STOP integration phase — must be the very first thing tested on hardware, before any other HMI wiring is done.

---

### Pitfall 4: gclib `py()` Handle Called from Multiple Threads — Corrupted Responses or Silent Connection Drop

**What goes wrong:**
The official gclib documentation states: "It is not safe to call GCommand() in multiple threads to the same physical connection — if such operation is required, it is the user's responsibility to use a mutual exclusion (mutex) or other mechanism."

The current architecture uses a single `jobs.JobThread` (FIFO, single worker) which correctly serializes all gclib calls. The risk arises when new code bypasses `jobs.submit()`. Specifically:
- If E-STOP calls `controller.cmd("AB")` directly from the Kivy main thread (which is correct for latency), AND the jobs thread is simultaneously executing a `controller.cmd()` call, TWO threads are calling `GCommand` on the same `py()` handle at the same time.
- The result is unpredictable: corrupted response strings, `?` error codes treated as valid data, or a silent connection drop requiring a GClose/GOpen cycle.

**Why it happens:**
The E-STOP direct-call fix (Pitfall 3 solution) creates a new threading hazard. The fix to one safety issue creates another if not handled carefully.

**How to avoid:**
- Option A (recommended): Keep E-STOP through `jobs.submit()` BUT give the E-STOP job a priority queue slot. Implement `jobs.submit_urgent()` that prepends to the queue rather than appending. The FIFO dequeue in `JobThread._run()` would drain the urgent item first.
- Option B: Open a second `gclib.py()` connection (second `GOpen` to same address) exclusively for E-STOP. Galil controllers support multiple concurrent TCP connections. This completely eliminates the shared-handle problem.
- Option C: Use a threading `Lock` around all `GCommand` calls in `GalilController.cmd()`. Any caller that holds the lock (including the main thread E-STOP) blocks the background thread. This is the simplest fix but introduces potential deadlock if the background thread holds the lock when E-STOP fires.
- Recommendation: Option A (priority queue slot) is the cleanest: preserves single-handle constraint, gives E-STOP < 1 polling cycle of latency (100 ms max), requires minimal code change.

**Warning signs:**
- E-STOP handler calls `self.controller.cmd()` directly from a Kivy button callback (main thread) while polling jobs are running
- Intermittent `?` response strings to normal MG commands that appear only when E-STOP has been recently triggered
- Controller connection drops after E-STOP, requiring manual reconnect

**Phase to address:**
E-STOP wiring phase (same phase as Pitfall 3). Decide the approach (priority queue vs. second connection) before writing any E-STOP code.

---

### Pitfall 5: HMI State Shows "Running" After Physical E-STOP or Limit Switch — State Desynchronization

**What goes wrong:**
The `MachineState.cycle_running` flag on the Python side is set to `True` when the HMI starts a cycle and `False` when the HMI sends Stop/Rest. If the physical E-STOP button is pressed (wired directly to the controller, bypassing the HMI entirely), the controller halts all motion but `cycle_running` on the Python side remains `True`. The HMI continues showing "RUNNING" with a spinning progress indicator, the plot continues buffering, and the operator cannot restart the machine until they navigate away and back (which resets the stale state).

The same scenario occurs when a hardware limit switch trips during a grind cycle — the controller halts cleanly but the HMI does not know and keeps showing the cycle as active.

**Why it happens:**
`cycle_running` is write-only from the Python side. There is no read-back from the controller that informs Python when the cycle ends outside of an HMI action. The only signal path is the HMI itself, creating a one-way dependency.

**Concrete scenario:**
1. HMI starts grind — `cycle_running = True`
2. Operator hits physical E-STOP — controller stops instantly
3. HMI shows "GRINDING" forever
4. Operator taps Start again — `hmiGrnd=0` is sent
5. Controller is in a faulted/stopped state; trigger is silently ignored or causes an unexpected motion command to execute when the fault is cleared

**How to avoid:**
- The `hmiState` variable (see Pitfall 2) is the solution. Poll it at every status cycle. When `hmiState` returns to 0 (idle/main), set `cycle_running = False` on the Python side regardless of how the cycle ended.
- Add a controller-execution status read: `MG _XQ` returns the executing thread ID. If it returns 0 (no thread running), the cycle has ended. Gate `cycle_running = True` only while `_XQ != 0`.
- The status poll in `_do_poll()` (RunScreen) should read `hmiState` and `_XQ` in addition to axis positions. If `_XQ == 0` and `cycle_running == True`, automatically transition to stopped state and surface a banner message: "Cycle ended (not from HMI)."

**Warning signs:**
- `cycle_running` is set to `False` only in HMI button handlers, never from a poll-based controller read
- No test for "physical E-STOP pressed while HMI shows running"
- Plot keeps buffering indefinitely after a hardware stop event

**Phase to address:**
State synchronization phase — implement `hmiState` polling as a dedicated sub-task of the HMI trigger wiring phase.

---

### Pitfall 6: Jogging While in DMC `#SETUP` Mode — Competing Motion Commands

**What goes wrong:**
The DMC `#SETUP` polling loop (`#SULOOP`) runs its own handwheel jog via `#WheelJg`. When the HMI enters Setup mode and the operator uses the `AxesSetupScreen` jog buttons, the HMI sends `PR{axis}={counts}; BG{axis}` commands. If the DMC program is simultaneously in `#WheelJg` and also detecting a `hmiJog=0` trigger, two independent motion commands are active on the same axis simultaneously. The result is axis runaway or erratic motion.

**Why it happens:**
The `AxesSetupScreen.jog_axis()` method sends direct `PR/BG` commands rather than going through the HMI variable trigger system. These commands are not gated by the DMC's current execution state. The DMC `#SETUP` loop has its own jog mode (`#WheelJg`) which also takes control of axis motion.

**How to avoid:**
- HMI jog commands must be sent only when the DMC is in a state that accepts external motion commands — specifically, when it is NOT running `#WheelJg`.
- Define a jog protocol: either (a) the HMI sends jog via the trigger variable (`hmiJog=0`) and the DMC handles it inside its own `#SETUP` loop, OR (b) the HMI sends direct `PR/BG` commands only when the DMC is in an explicitly HMI-controlled idle state (not in any DMC subroutine).
- The safest approach for the Flat Grind machine: HMI jog uses `hmiJog=0` with axis/direction parameters loaded into DMC variables before triggering. The DMC `#SETUP` loop handles the actual motion. This way the DMC controls axis access and no race condition is possible.
- If direct `PR/BG` from HMI is used, poll `MG _XQ` first; only send if no DMC thread is running (`_XQ == 0`).

**Warning signs:**
- `AxesSetupScreen.jog_axis()` sends `PR{axis}` without checking `_XQ`
- Axes jerk or move erratically when using HMI jog immediately after entering Setup mode
- HMI jog buttons enabled while `hmiState` indicates DMC is in `#WheelJg` or `#HOME`

**Phase to address:**
Setup page integration phase — jog protocol must be defined before any jog code is written.

---

### Pitfall 7: Sending Parameters to Controller While DMC is Mid-Cycle — Array Write During Active Motion

**What goes wrong:**
`download_array` for `deltaC`, `deltaA`, or `startPt` arrays writes to DMC arrays that are actively read during `#GRIND`. The DMC motion loop reads `deltaA[n]`, `deltaB[n]`, etc., in a tight inner loop. If the HMI writes new values to `deltaC` while the grind vector is executing, the controller reads a mix of old and new values within the same grind pass. This produces an incorrect grind profile on the knife and may cause unexpected axis acceleration.

**Why it happens:**
The DMC controller does not lock arrays during program execution. `download_array` writes take effect immediately and are not deferred until the current motion completes. The temptation to "apply a compensation adjustment while grinding" (More/Less Stone buttons) seems safe because those are small +/-1mm adjustments, but the pattern is already training developers to write to motion parameters during active motion.

**How to avoid:**
- Any `download_array` call that targets motion-path arrays (`deltaA`, `deltaB`, `deltaC`, `deltaD`, `startPt`, `restPt`) must be gated behind `hmiState == 0` (idle) or a DMC-level write-lock flag.
- The `on_apply_delta_c()` method in RunScreen must check controller state, not just Python `cycle_running`.
- "More Stone" / "Less Stone" are compensations to `startPt[3]` — these are single-variable writes (not array downloads) and are relatively safe during motion because the DMC program reads `startPt[3]` only at the start of `#MOREGRI/#LESSGRI`, not mid-vector. However, document this clearly; future developers should not generalize the pattern.
- For `deltaC` and motion path arrays: only apply between grind passes, never during. Add a confirmation: "This will take effect on the next cycle."

**Warning signs:**
- `on_apply_delta_c()` does not check controller state before calling `download_array`
- "More Stone" / "Less Stone" is enabled when `cycle_running == True` without understanding the DMC timing
- `download_array` calls are not logged with a timestamp to help debug unexpected grind profile changes

**Phase to address:**
More/Less Stone and deltaC integration phase.

---

## Moderate Pitfalls

---

### Pitfall 8: gclib Connection Not Closed on App Exit or Crash — Controller Left in Inconsistent State

**What goes wrong:**
If the Python process exits without calling `GClose()`, the Galil controller may be left with an open TCP connection handle. On subsequent reconnection, `GOpen()` may fail with a "resource busy" error or succeed but receive stale data from the previous session. More critically, if the Python process crashes mid-`download_array`, the controller may have received a partial array write — some elements updated, some old.

**Why it happens:**
The existing `disconnect()` method calls `GClose()` correctly in the happy path. What is missing is a `try/finally` or `atexit` handler that ensures `GClose()` is called even if Kivy crashes, the window is force-closed, or the Python process receives SIGTERM (as it will on Pi shutdown via `systemctl stop`).

**How to avoid:**
- Register an `atexit` handler in `main.py`: `atexit.register(controller.disconnect)`.
- Handle `SIGTERM` explicitly: `signal.signal(signal.SIGTERM, lambda *_: controller.disconnect())`.
- Add a `__del__` method to `GalilController` that calls `disconnect()` as a last-resort fallback.
- The Galil controller also has a TCP watchdog (`GOpen` with `-d` flag option) that closes the connection after a timeout if the host goes silent — enable this for the Pi deployment where process crashes are more likely.

**Warning signs:**
- `GOpen()` fails on app restart with a connection error when the controller has been "connected" from the previous crash
- Reconnecting requires power-cycling the controller
- No `atexit` or signal handler in `main.py`

**Phase to address:**
gclib connection management phase — include as part of the initial controller wiring.

---

### Pitfall 9: Polling the Controller at Different Rates from Multiple Clock Events — Queue Saturation

**What goes wrong:**
The current architecture has two clocks on the RunScreen: `_update_clock_event` at 10 Hz (polls axis positions) and `_plot_clock_event` at 5 Hz (redraws plot). If Setup mode is also active, `AxesSetupScreen._poll_event` runs at 3 Hz. These all submit jobs via `jobs.submit()` — the same single FIFO worker thread.

At 10 Hz from RunScreen + 3 Hz from AxesSetup, the jobs queue receives 13 submissions per second. Each poll reads 4 axes (4 `GCommand` calls at ~2–5 ms each) = 8–20 ms per poll job. At 13 polls/second, the queue is receiving ~100–260 ms of work per second. The single worker cannot keep up and the queue backs up — commands arrive late, E-STOP latency grows, and the UI feels sluggish.

**Why it happens:**
Each screen starts its own polling clock without coordination. The total gclib load is not tracked globally.

**How to avoid:**
- Have a single global poll loop in `DMCApp` (or `MachineState`) rather than per-screen polling. All screens subscribe to `MachineState` for updates. When the RunScreen is visible, the global poll reads A/B/C/D position + `hmiState`. When AxesSetup is visible, it reads the same positions. No duplicate reads.
- The existing `ARCHITECTURE.md` recommendation ("Pattern 3: Polling Loop for Live Plot") establishes this correctly — use `jobs.schedule()` in `DMCApp` instead of per-screen `Clock.schedule_interval`.
- Total jobs per second target: keep total gclib work under 60 ms/s on the Pi (leaves 40 ms/s headroom for command submissions). At ~5 ms per GCommand, this is 12 GCommand calls per second maximum under normal polling.

**Warning signs:**
- Multiple `Clock.schedule_interval` calls active simultaneously from different screens
- `jobs` queue depth grows over time (diagnose by adding a queue size log)
- Status poll responses arrive with timestamps older than 200 ms (confirm by logging response timestamp vs. submission time)

**Phase to address:**
Refactor polling to global app-level job in the first integration phase, before adding more screens.

---

### Pitfall 10: Reading `hmiState` Variable Before DMC Program Has Defined It — "?" Response Treated as State

**What goes wrong:**
When HMI variables (`hmiGrnd`, `hmiState`, `hmiSetp`, etc.) are added to the DMC program, they are assigned initial values in `#CONFIG` or `#AUTO`. If the controller is powered on and the Python GUI connects before the DMC program has finished running `#AUTO` (which takes several seconds including homing), a `MG hmiGrnd` command returns `?` (undefined variable). If the Python code parses `?` as a float, it gets a `ParseError`. If it silently skips the error and assumes the variable is 1 (default), it misses the case where `hmiGrnd` is actually mid-initialization.

**Why it happens:**
The `wait_for_ready()` method currently only checks `MG _TPA` (axis position) — a built-in variable that always exists. It does not verify that user-defined DMC variables are initialized.

**How to avoid:**
- Extend `wait_for_ready()` or add a separate `verify_hmi_vars()` method that polls `hmiGrnd`, `hmiState`, and other key HMI variables. Wait until they all return valid floats (not `?`) before enabling any HMI buttons.
- Add a controller readiness indicator to the GUI: "Waiting for controller program..." displayed until all HMI variables are confirmed initialized.
- Add error-specific handling for `?` responses in the HMI variable poll: do not treat `?` as 0 or 1 — treat it as "not ready" and retry.

**Warning signs:**
- HMI Start button is enabled immediately on connection before DMC `#AUTO` completes
- `ParseError` exceptions in logs during initial connection
- Sending `hmiGrnd=0` before `hmiGrnd` is defined on the DMC side causes a "Bad label" error (TC code 37)

**Phase to address:**
HMI variable initialization phase — the first DMC program modification task.

---

### Pitfall 11: New Session Flow Sends `hmiNewS=0` Without Stone-Changed Confirmation — Accidental Home Cycle

**What goes wrong:**
The DMC `#NEWSESS` subroutine calls `JS #HOME` as its first action (homing all four axes). If the operator taps "New Session" on the HMI by mistake (thinking it means something else), all four axes immediately start homing. The knife mounted on the machine must be removed before homing in many machines — triggering home with a knife in place is a tooling collision risk.

**Why it happens:**
`#NEWSESS` is a destructive operation (resets knife count, triggers homing) but the HMI button is treated the same as "Start Grind" — a single tap sends the trigger.

**How to avoid:**
- "New Session" must require explicit two-step confirmation: show a modal dialog ("Remove the knife before continuing. Confirm new session?") with a deliberate confirmation tap before `hmiNewS=0` is sent.
- Consider a keypress count: require the operator to tap "New Session" three times within 3 seconds, or hold the button for 2 seconds.
- The HMI should show the current stone session info (knife count, stone serial) so the operator can verify they intend to start a new session before confirming.

**Warning signs:**
- "New Session" button sends trigger on first tap without any modal confirmation
- Button is accessible to Operator role (should be Setup or Admin only)
- No test covering "accidental New Session tap during setup"

**Phase to address:**
New Session integration phase.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using Python `cycle_running` as the only cycle state indicator | Simple to implement, no DMC changes needed | State desync after physical E-STOP or limit switch trips; stale UI | Never — add `hmiState` polling from the start |
| Gating sends on `is_connected()` alone | Fast to code | Does not detect controller in fault state, mid-cycle, or mid-homing | Never for motion commands; acceptable for status reads |
| Sending all gclib calls through `jobs.submit()` including E-STOP | Consistent threading model | E-STOP can be delayed by queue depth | Never for E-STOP — use priority queue or direct call with care |
| Using `HX` (halt execution) instead of `AB` (abort) for emergency stop | HX is cleaner (allows restart without re-init) | HX is not immediate on all DMC firmware — `AB` is the safety standard | Use `AB` for E-STOP, `HX` for user-initiated pause/stop |
| Polling `_XQ` to determine if a cycle is running | Works | `_XQ` returns the thread ID, not a semantic state; program structure changes break this | Acceptable as a secondary check alongside `hmiState` |
| Single-element array assignment (`bComp[i]=val`) instead of bulk `download_array` | Simpler loop, easy to understand | 100 individual GCommands for a 100-element array = 100 roundtrips at 2–5 ms each = 200–500 ms | Acceptable only for small arrays (< 10 elements) |

---

## Integration Gotchas

Common mistakes when connecting the HMI to the DMC state machine.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| HMI trigger variables | Sending `hmiGrnd=0` at 10 Hz "to ensure it triggers" | Send exactly once per user action; never re-send until user re-taps |
| HMI trigger variables | Checking that the variable was received by reading it back | The DMC resets it to 1 immediately; a read-back will show 1, not confirmation of receipt. Confirm via `hmiState` transition instead |
| DMC `#SETUP` mode | Entering `#SETUP` from HMI by sending `XQ #SETUP` | Use `hmiSetp=0` trigger variable so the DMC transitions via its own polling loop, maintaining program integrity |
| gclib connection | Opening connection in `on_pre_enter` of a screen | Open once at app startup in `main.py`; screens use the injected controller object |
| gclib connection | Not calling `GClose()` before `GOpen()` on reconnect | Always `disconnect()` before `connect()` — `GOpen()` on an already-open handle throws an error or leaks resources |
| Controller array names | Using 9-character variable names for HMI variables | DMC variable names are limited to 8 characters. `hmiGrnd` (7 chars) is fine; `hmiGrind` (8 chars) is at the limit; anything longer silently truncates to 8 chars and creates a name collision |
| `BV` (burn variables) | Calling `BV` after every parameter write | `BV` writes to non-volatile flash. Excessive `BV` calls during rapid parameter editing wears out flash and causes 2–5 second pauses during the write. Call `BV` only on explicit "Save to Controller" user action, never automatically |
| `#GOREST` motion order | Sending `hmiGrnd=0` when axes are not at rest position | `#GRIND` calls `#GOSTR` which moves all axes. If axes are at random positions, the simultaneous move to start can cause a collision. Always home or rest before starting a new grind |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Uploading 250-element arrays on every screen enter | 3–8 second freeze on RunScreen enter | Only upload arrays when operator explicitly requests a read; not on navigation | Every navigation to affected screen |
| Polling all 4 axes separately with individual `MG _TP{axis}` calls | 4 roundtrips × 2–5 ms = 8–20 ms per poll cycle | Use a single `MG _TPA, _TPB, _TPC, _TPD` command returning all 4 values in one response | Noticeable at 10 Hz on Pi 4 under load |
| Using `time.sleep()` in the jobs thread between array element reads | 250 elements × 10 ms sleep = 2.5 seconds for full array | The existing `upload_array` has a 10 ms sleep — acceptable for one-time reads, unacceptable for polling | Any array upload in a polling loop |
| Running `discover_length()` (probes all 250 array slots) on every poll cycle | Jobs thread saturated; poll latency grows to seconds | `discover_length()` is a one-time initialization tool; cache the result | First use is fine; repeated use is not |
| Matplotlib `draw_idle()` called from `Clock.schedule_once` at 10 Hz | Plot redraws eat Pi CPU, E-STOP latency grows | Keep plot clock at 5 Hz; decouple from poll clock (already done in existing code) | Pi 4 under full load at 10 Hz plot |

---

## Safety Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| E-STOP wired to a single screen (RunScreen only) | Operator on AxesSetup or Parameters screen cannot stop a runaway axis | E-STOP must be in the persistent global tab bar or status bar, visible from every screen at all times |
| Jog controls accessible to Operator role | Operator can move axes to unexpected positions, causing tooling damage | Jog is Setup-role-only. Disable jog buttons when `state.current_role == "operator"` |
| "More Stone" / "Less Stone" accessible without motion check | Calling `#MOREGRI` while mid-grind overwrites `startPt[3]` during active motion | Gate More/Less Stone behind DMC state verification, not just Python `cycle_running` |
| Parameter write (`download_array`) from Operator role | Operator accidentally changes grind parameters mid-job | All `download_array` calls for motion parameters gated behind Setup role |
| No motion interlock on CSV profile load | Profile load while grinding overwrites motion arrays mid-vector | Profile load gated behind: (1) Setup role AND (2) `hmiState == 0` (confirmed idle), not just Python `cycle_running` |
| Jog command with no speed limit | Rapid axis movement at full speed during setup damages knife or tooling | Set axis speed before any jog: `SP{axis}={safe_speed}` before every `PR/BG` pair |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| HMI button responds to tap but machine does not move for 100–300 ms (trigger variable latency) | Operator taps again, thinking the first tap did not register — double trigger | Immediately disable the button on first tap (optimistic lock); show "Sending..." state; re-enable when `hmiState` confirms the action was received |
| "Cycle running" indicator stays on after physical E-STOP | Operator confused — machine is stopped but HMI says running | Poll `hmiState` from controller to drive cycle_running, not just HMI button handlers |
| No visual feedback for E-STOP event | Operator does not know if E-STOP was acknowledged by the controller | After `AB` command, show a prominent red banner: "E-STOP ACTIVE — motion halted" |
| "New Session" button next to "More Stone" / "Less Stone" | Accidental new session during compensation adjustment triggers homing | Spatially separate New Session from routine adjustment buttons; add confirmation dialog |
| Grind cycle progress at 0% until `hmiState` is polled for the first time | Operator sees no feedback for the first poll interval | Show "Starting..." state immediately on Start tap, before first controller confirmation |

---

## "Looks Done But Isn't" Checklist

- [ ] **HMI triggers:** Confirm each trigger variable is reset to 1 by DMC as the FIRST line inside the triggered block, not after the motion completes.
- [ ] **E-STOP:** Test with a large array operation in the jobs queue — confirm E-STOP halts motion within 200 ms regardless of queue depth.
- [ ] **Physical + HMI double-trigger:** Press physical Start button at the same time as HMI Start — confirm only one grind cycle starts.
- [ ] **State desync after physical E-STOP:** Press physical E-STOP while HMI shows "RUNNING" — confirm HMI detects the stop via `hmiState` poll within 2 polling cycles.
- [ ] **Jog in Setup mode:** Enter Setup, start handwheel jog via physical controls, then tap HMI jog — confirm axes do not fight each other.
- [ ] **Reconnection:** Kill the app (force-close) while a grind cycle is running — confirm `GClose()` is called via atexit; confirm controller does not remain in a half-open TCP state.
- [ ] **HMI variable initialization:** Connect immediately after powering the controller — confirm HMI buttons are disabled until `#AUTO` completes and HMI variables return valid values.
- [ ] **Parameter apply during cycle:** Try to apply `deltaC` changes while a grind cycle is running — confirm the UI blocks this action.
- [ ] **New Session confirmation:** Tap "New Session" once — confirm a modal dialog appears before any homing begins.
- [ ] **BV call frequency:** Confirm `BV` is not called more than once per "Save" user action — never automatically after every variable write.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Double grind trigger caused physical damage | HIGH | Stop machine. Assess tooling and knife. Re-home all axes. Check `startPt`/`restPt` arrays have not been corrupted. Do not restart grind until Setup validates positions. |
| Controller left in inconsistent state after app crash | LOW | Power-cycle the controller. On reconnect, run `#HOME` before any motion commands. Verify `hmiState` returns to 0. |
| State desync — GUI shows running, controller is idle | LOW | Navigate away from RunScreen and back (triggers `on_pre_enter` which re-polls). Or add a "Sync" button that explicitly reads `hmiState` and resets GUI flags. |
| Jobs queue backed up — E-STOP delayed | MEDIUM | Restart the app. Implement `jobs.submit_urgent()` for the next build so this never recurs. |
| Array partially written (app crash during `download_array`) | MEDIUM | Read back all affected arrays from controller. Compare against last known-good values (from most recent CSV export). Re-download full arrays if any mismatch. |
| HMI variables undefined at connect time | LOW | Wait for DMC `#AUTO` to complete (observable via `MG _XQ` returning 0 or `hmiState` returning a valid value). Retry initialization after 5-second delay. |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Double-action: physical + HMI trigger race (Pitfall 1) | DMC program modification phase | Test: simultaneous physical + HMI press; confirm single action |
| Motion command during active cycle (Pitfall 2) | HMI trigger wiring phase | Test: send HMI Rest while grind cycle running; confirm rejection |
| E-STOP queued behind normal jobs (Pitfall 3) | E-STOP wiring phase — FIRST hardware test | Test: E-STOP during array upload; confirm < 200 ms halt |
| gclib concurrent access from E-STOP path (Pitfall 4) | E-STOP wiring phase | Inspect code: confirm single-handle access pattern holds |
| State desync after physical E-STOP / limit switch (Pitfall 5) | State synchronization phase | Test: physical E-STOP while HMI shows running; confirm HMI syncs within 2 poll cycles |
| Jog during DMC `#SETUP` mode collision (Pitfall 6) | Setup page integration phase | Test: HMI jog while handwheel is active; confirm no axis fighting |
| Array write during active motion (Pitfall 7) | More/Less Stone + deltaC phase | Test: apply deltaC while grinding; confirm UI blocks the action |
| GClose not called on crash (Pitfall 8) | Connection management phase | Test: kill -9 the app; confirm controller reconnects cleanly next launch |
| Queue saturation from multiple poll clocks (Pitfall 9) | First integration phase | Measure: log queue depth at 10 Hz; confirm < 5 jobs queued at any time |
| `hmiState` read before DMC program initializes (Pitfall 10) | HMI variable init phase | Test: connect 2 seconds after controller power-on; confirm HMI buttons disabled until vars ready |
| Accidental New Session (Pitfall 11) | New Session integration phase | Test: single-tap New Session; confirm modal dialog appears |
| Matplotlib thread-safety (carry-over from v1.0) | RUN page polish | Verify: no matplotlib calls in any `jobs.submit()` closure |
| E-STOP not globally accessible (safety) | E-STOP wiring phase | Verify: E-STOP button visible from AxesSetup, Parameters, and Users screens |

---

## Sources

- Codebase analysis: `src/dmccodegui/controller.py`, `utils/jobs.py`, `screens/run.py`, `screens/axes_setup.py`, `screens/buttons_switches.py` — direct code inspection (HIGH confidence)
- DMC program analysis: `4 Axis Stainless grind.dmc` — direct inspection of #MAIN, #GRIND, #SETUP, #GOREST, #NEWSESS polling loops (HIGH confidence)
- gclib thread safety: Galil official gclib documentation — "It is not safe to call GCommand() in multiple threads to the same physical connection" — [gclib Threading](https://www.galil.com/sw/pub/all/doc/gclib/html/threading.html) (HIGH confidence)
- HMI polling delay causes: [Infoneva — Delay in PLC Response to HMI Button Presses](https://infoneva.com/en/knowledge/delay-in-plc-response-to-hmi-button-presses) (MEDIUM confidence — PLC pattern, not DMC-specific, but timing principles are identical)
- gclib connection API: [Galil gclib py class reference](https://www.galil.com/sw/pub/all/doc/gclib/html/classgclib_1_1py.html) (HIGH confidence — official docs)
- Industrial HMI E-STOP response time standard: 100–200 ms maximum acceptable latency for safety-critical stops — training knowledge from IEC 62061 / ISO 13849 patterns (MEDIUM confidence — verify against actual regulatory requirements for this machine category)
- DMC variable name length limit (8 chars): Galil DMC Command Reference — training knowledge (HIGH confidence — well-documented constraint, confirmed in project context `hmiGrnd` naming)

---
*Pitfalls research for: HMI-controller integration, Galil DMC + gclib + Kivy, knife grinding machine*
*Researched: 2026-04-06*
