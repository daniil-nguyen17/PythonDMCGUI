# Feature Landscape

**Domain:** Industrial HMI-controller integration — knife grinding machine, Galil DMC, 4-Axes Flat Grind
**Researched:** 2026-04-06
**Confidence:** HIGH (based on direct DMC program analysis, existing codebase review, gclib documentation,
and established industrial HMI patterns from ISA-101 and CNC industry practice)

> **Scope note:** This document replaces the v1.0 FEATURES.md for the v2.0 milestone.
> v1.0 features (PIN auth, tab navigation, live plot scaffold, axes setup UI, parameter cards,
> CSV profiles, user management) are already built and shipped. This document covers only what is
> needed to wire the existing UI to the real DMC controller state machine.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that make the integration feel like a real machine controller.
Missing any of these means the HMI still feels like a demo with disconnected buttons.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Start Grind button triggers `XQ #GRIND` | Core operator action — "press Start, machine grinds." Without this nothing works. | LOW | `run.py` `on_start_pause_toggle()` already calls `XQ #CYCLE` — needs to be changed to `XQ #GRIND`. The DMC `#GRIND` subroutine calls `#GOSTR` then executes the vector contour loop. |
| Go To Rest button triggers `XQ #GOREST` | Operators expect a safe park button that moves all axes to the rest position. Without it they have no way to safely stop and park. | LOW | `run.py` `on_go_to_rest()` already calls `XQ #REST` — needs to be changed to `XQ #GOREST`. DMC `#GOREST` moves C first, then D, then A, then B in the safe sequenced order. |
| Go To Start button triggers `XQ #GOSTR` | Setup personnel must be able to send the machine to start position without running a full cycle — to verify position before committing. | LOW | No button currently exists in `run.py` for this. New button needed in the run page action bar. DMC `#GOSTR` is already defined and tested. |
| Stop motion sends `ST ABCD` | Any stop action (pause, abort, E-STOP) must immediately halt all axes. An HMI that cannot stop a moving machine is unsafe. | LOW | `run.py` pause path sends `HX`. Must instead (or additionally) send `ST ABCD` to halt axis motion. `HX` stops the DMC program thread; `ST` stops motor motion. Both are needed. |
| Controller state reflected in UI within 1 second | Operators must be able to see whether the machine is running, at rest, or in setup. Without state sync, operators cannot safely interact with the machine. | MEDIUM | Poll a state variable (e.g. `MG hmiState` or dedicated flag variable) at 10 Hz from the background thread already running in `run.py`. Update a status dot/label with values: IDLE / GRINDING / SETUP / AT-REST. |
| Live axis positions connected to real controller | Position labels on the RUN page must show real encoder counts from the controller, not stale or simulated values. Operators use them to verify home and axis travel. | LOW | `run.py` `_do_poll()` already calls `MG _TP{axis}` — the poll loop is started but `_show_disconnected()` overrides it on every `on_pre_enter`. Remove the override; enable the poll path when `controller.is_connected()`. |
| Plot populates from real A/B positions during cycle | The live A/B plot is built and draws from `_plot_buf_x/y`, but buffers only fill when `cycle_running == True`. Setting `cycle_running = True` on grind start is already in `on_start_pause_toggle` — this just needs to be exercised against the real controller. | LOW | No new code needed. Validate that `_TPA` and `_TPB` return numbers at 10 Hz. Confirm plot redraws at 5 Hz. |
| Jog controls move real axes | Jog arrow buttons in the Axes Setup screen must send actual `JG` / `SP` / `BG` commands. Currently `adjust_axis()` only updates UI text fields. | MEDIUM | Depends on which screen the operator is on. `AxisDSetup.adjust_axis()` already sends `pa=` immediately (live jog). `StartScreen` and `RestScreen` only update the text field — they need a separate jog-in-place command or a "Move Now" button wired to `PA / BG`. |
| Save Start/Rest points writes to controller arrays | `StartScreen.save_values()` and `RestScreen.save_values()` already call `download_array`. These must succeed against the real controller and confirm via a status message. Currently they silently succeed or print to console only. | LOW | Add a success toast/banner via `_alert()` on successful array write. Verify array names (`StartPnt` vs `startPt`) match what the DMC program actually uses — DMC uses `startPt[4]` and `restPt[4]`; Python uploads to `StartPnt` and `RestPnt`. This name mismatch must be resolved. |
| Parameters write to controller via `download_array` | Feedrates, CPM values, and geometry parameters edited in the Parameters screen must be written to the controller's variables (e.g. `fdA`, `cpmA`, `knfThk`). | MEDIUM | `parameters.py` currently has no `save` action wired to the controller. Each parameter card needs a "Write to Controller" path using `controller.cmd("fdA=50")` pattern or `download_array`. |
| New Session flow resets knife count and re-homes | The "New Session" button (stone change) must call `XQ #NEWSESS`. This runs homing and resets `ctSesKni = 0`. | LOW | No button currently wired. New button needed in the RUN page — gated to Setup role (stone changes are setup actions, not operator actions). Wire to `XQ #NEWSESS`. |
| More Stone / Less Stone adjusts `startPt[3]` | Compensation buttons must call `XQ #MOREGRI` and `XQ #LESSGRI`. These subroutines add/subtract `cpmC * 0.001` to `startPt[3]` each press. | LOW | `run.py` has `on_adjust_up/down` for `deltaC` array — these are different from More/Less Stone. More/Less Stone buttons need to be separate, dedicated buttons in the RUN page that call `XQ #MOREGRI` / `XQ #LESSGRI`. |
| Homing sequence available from Setup screen | Setup personnel must be able to run the home sequence (`XQ #HOME`) from the HMI. This is a prerequisite before any grind cycle after power-on. | LOW | The physical panel has a Home button (IN25 in `#SETUP`). The HMI needs a "Run Home" button on the Axes Setup screen, gated to Setup role. Wire to `XQ #HOME`. |
| Connection status visible at all times | An operator who walks up to a disconnected machine must immediately see it is not connected. Pressing Start on a disconnected HMI must not silently fail. | LOW | The top bar / status bar widget already has a connection indicator. Verify `controller.is_connected()` is polled and reflected in `state.connected`. All action handlers already guard with `controller.is_connected()` check — confirm this is consistent across all new action handlers. |

---

### Differentiators (Competitive Advantage)

Features beyond the minimum that make this HMI more valuable than a raw DMC terminal or a bare
operator panel. These are worth building once table stakes are done.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| HMI one-shot trigger variable pattern (hmiGrnd etc.) | Allows HMI buttons and physical panel buttons to act as OR conditions — pressing Start on the screen has the same effect as pressing the physical button, without duplicating DMC logic. Supports hybrid human/HMI operation. | MEDIUM | DMC program must be modified: add `hmiGrnd=1` default, add `IF (@IN[29]=0) OR (hmiGrnd=0)` before the `JS #GRIND` call, reset `hmiGrnd=1` inside the block. GUI sends `hmiGrnd=0` to trigger. 8-char DMC name limit applies: `hmiGrnd`, `hmiSetp`, `hmiMore`, `hmiLess`, `hmiNewS`, `hmiHome`, `hmiJog`, `hmiCalc`. |
| DMC state variable polled by HMI | The HMI shows a named state (IDLE / GRINDING / AT-REST / SETUP / HOMING) instead of just a connected/disconnected dot. Operators have confidence about what the machine is doing even when off-screen. | MEDIUM | Add `hmiState` variable to DMC `#PARAMS` (default = 0). Set it at entry/exit of each major subroutine: `hmiState=1` entering `#GRIND`, `hmiState=2` entering `#GOREST` final position, etc. HMI polls `MG hmiState` at 10 Hz. This variable approach is LOW latency because it only needs one `MG` call. |
| Knife count display from controller | Show `ctSesKni` (knives ground this session) and `knfSess` on the RUN page. Operators use this to pace production and know when to ask for a stone change. | LOW | Poll `MG ctSesKni` and `MG knfSess` in the background poll. Add two labels to the RUN page status column. No DMC program changes needed — variables already exist. |
| Position readout in engineering units (mm/degrees) | Showing "12,450 counts" is meaningless to an operator. Converting to "12.45 mm" using CPM values makes the display comprehensible. | LOW | CPM values (`cpmA`, `cpmB`, `cpmC`, `cpmD`) are already polled by `run.py._read_cpm_values()`. Divide raw position by CPM. Format as `f"{mm:.2f} mm"` or `f"{deg:.1f} deg"` for D axis. Toggle between counts and units via a tap. |
| Varcalc / recalculate trigger from HMI | After a knife type change, `#VARCALC` recalculates CPM, thickness counts, and derived values. Setup personnel currently have to press a physical button (IN26). HMI trigger eliminates the need to walk to the physical panel. | LOW | Wire to `XQ #VARCALC` from a "Recalculate" button in Parameters screen, gated to Setup role. This is the parameter recalc that saves to EEPROM via `BV`. |
| Setup mode visual indicator on all screens | When `hmiState == SETUP`, the tab bar or status bar shows a yellow "SETUP MODE" badge. Prevents operators from accidentally navigating to Run and starting a cycle while setup personnel are jogging axes. | LOW | React to the polled `hmiState` value in `MachineState`. Add a `setup_mode_active` BooleanProperty. KV binding in the tab bar changes Run tab color or disables it when `setup_mode_active` is True. |
| Graceful controller reconnection | If the USB/Ethernet connection drops mid-cycle, the HMI shows a "Controller disconnected" overlay and retries connection in the background. When reconnected, it resumes polling without requiring a restart. | MEDIUM | The existing `GalilController.is_connected()` pattern supports this. Add a reconnect loop in the background thread: on connection failure, try `GOpen()` every 5 seconds. Post `state.set_connected(False)` immediately on error. Overlay triggered by `state.connected == False`. |
| Array name validation on upload/download | The Python code uses `StartPnt` / `RestPnt` as array names; the DMC program uses `startPt` / `restPt`. This mismatch will cause silent failures on the real controller. Validation catches this before an operator saves corrupted data. | LOW | The real fix is to make the names consistent. Either rename in DMC (`DM StartPnt[4]`) or rename in Python (`upload_array("startPt", ...)`). Add a validation helper that checks the array exists on the controller before writing. |

---

### Anti-Features (Commonly Requested, Often Problematic)

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Confirmation dialogs on every button press | "Make sure the operator means it before moving motors." | Adds a tap to every action. On a grinding machine, operators run cycles repeatedly. Dialog fatigue causes operators to dismiss dialogs without reading them. Latency between decision and action increases error risk. | Confirm only on destructive/irreversible actions: New Session (resets knife count + re-homes), and Reset to Defaults. All other motion commands (Start, Rest, Jog) execute immediately. |
| HMI-side E-STOP via software | "Give the operator a big red button on screen." | ISO 13850 requires E-STOP to be hardwired at PL=c or higher. A software E-STOP that sends `ST ABCD` via gclib has network/USB latency, Python GIL delays, and Kivy event loop delays. It CANNOT substitute for the physical E-STOP. The physical E-STOP circuit is already in place. | Show a clear "GO TO REST" button on the run page as the normal "stop grinding" action. Document that the physical E-STOP remains the safety-critical stop. The HMI `ST ABCD` command is an operational stop, not a safety stop. |
| Speed control slider on the RUN page | "Let operators adjust speed during a cycle." | Feedrate changes mid-vector-contour (`LM` mode) can cause the interpolator to lose synchronization, producing geometry errors in the grind path. Speed is a parameter set before cycles, not during. | Expose speed parameters on the Parameters screen (Setup role only). They take effect on the next cycle start. |
| Real-time parameter editing during a cycle | "Operators want to tweak while the machine runs." | Mid-cycle parameter writes to DMC arrays can corrupt the values the currently-running subroutine is reading. The DMC interpreter does not lock arrays during reads. | Disable the Parameters screen save button while `cycle_running == True`. Show a "Stop cycle to edit parameters" message. |
| Axis position sliders for coarse jog | The `buttons_switches.py` slider sends `PA{axis}=N` + `BG` on slider release. The slider range is -1000 to 1000 counts — about 1 mm travel. | Sliders are imprecise on a touchscreen. Accidental touch during a cycle could send an unintended PA command. The existing jog arrow buttons with X1/X10/X100 step are safer and more precise. | Keep the axis status indicators (limit, home, motor-off checkboxes). Remove or disable the position sliders. Use the existing step-jog arrow buttons from AxesSetupScreen exclusively. |
| Polling `MG` commands at faster than 10 Hz for all variables | "More data = better display." | gclib round-trip over USB is ~2-5 ms. At 10 Hz with 4 axes + state variables, each poll sends 5+ `MG` commands = ~25 ms serial I/O per cycle. Polling faster than 10 Hz risks starving the Kivy main thread and increasing E-STOP latency. | Keep poll at 10 Hz. Use the `DR` (Data Record) command for high-speed position capture if ring buffer data is needed. Plot runs at 5 Hz from buffered data — do not drive plot directly from poll. |
| Separate screen for each setup sub-function | "Each function deserves its own dedicated screen." | More screens = more navigation taps. Setup personnel are already context-switched between the physical machine and the HMI. Each extra screen is a tap they may miss or forget. | Group setup functions logically on fewer screens: AxesSetup (jog + teach + home), Parameters (all parameter groups in cards), Run (all cycle controls). The v1.0 tab bar already enforces this structure. |

---

## Feature Dependencies

```
Controller connection (controller.is_connected())
  └── required by ALL action handlers below

DMC array name consistency fix (startPt vs StartPnt)
  └── required before: Save Start Point, Save Rest Point

Start Grind (XQ #GRIND)
  ├── requires: controller connected
  ├── requires: machine at rest or at start position (operator responsibility)
  └── enables: live plot buffer fill, cycle timer start, state → GRINDING

Go To Rest (XQ #GOREST)
  ├── requires: controller connected
  └── enables: state → AT-REST, cycle_running = False

Go To Start (XQ #GOSTR)
  └── requires: controller connected

Stop Motion (ST ABCD)
  └── requires: controller connected
  └── called by: Pause, Go To Rest before moving, any abort path

HMI one-shot variable pattern (DMC code change)
  ├── requires: DMC program modified to add hmi* variables and OR conditions
  ├── enables: Start Grind via hmiGrnd=0 (instead of XQ #GRIND direct)
  ├── enables: More/Less Stone via hmiMore=0 / hmiLess=0
  └── enables: physical buttons and HMI to co-exist safely

Controller state variable (hmiState)
  ├── requires: DMC program modified to set hmiState at subroutine boundaries
  ├── enables: Setup mode indicator badge on all screens
  ├── enables: Disable Run tab during setup mode
  └── enables: State-driven UI (correct button states on reconnect)

More Stone / Less Stone (XQ #MOREGRI / #LESSGRI)
  ├── requires: machine in IDLE state (not mid-cycle)
  └── note: these modify startPt[3], which affects the NEXT cycle's start position

New Session (XQ #NEWSESS)
  ├── requires: Setup role (stone change is a setup action)
  ├── requires: machine not currently grinding
  └── requires: operator physically present (machine will home = move all axes)

Homing (XQ #HOME)
  ├── requires: Setup role
  └── note: runs after power-on and after New Session automatically — HMI button is for manual re-home only

Varcalc / Recalculate (XQ #VARCALC)
  ├── requires: Setup role
  ├── requires: knife parameters already set in Parameters screen
  └── saves to EEPROM via BV — survives power cycle

Live position display (MG _TPA/B/C/D at 10 Hz)
  ├── requires: poll loop enabled (remove _show_disconnected() override in on_pre_enter)
  └── enables: live A/B plot buffer fill during cycle

Knife count display (MG ctSesKni at 10 Hz)
  └── requires: live position poll already running (batch MG queries in same poll)

Position in engineering units (mm/degrees)
  └── requires: CPM values already polled by _read_cpm_values()
```

### Dependency Notes

- **Array name mismatch must be resolved first:** Python code calls `upload_array("StartPnt", ...)` but the DMC program declares `DM startPt[4]`. These are different array names. Galil array names are case-insensitive in some firmware versions but not all. Verify against the actual controller before any save operations.

- **XQ vs hmi variable pattern:** Direct `XQ #GRIND` works immediately without DMC changes. The HMI one-shot variable pattern requires DMC code modification. Start with direct `XQ` calls to validate wiring, then migrate to the hmi variable pattern for proper OR-with-physical-buttons behavior.

- **ST vs HX:** `HX` halts the DMC program execution thread (no more DMC instructions run). `ST ABCD` stops axis motion. Both are needed on pause/abort: `HX` first to stop program from issuing new moves, `ST ABCD` next to decelerate and stop current motion.

- **Jog during Setup mode:** The DMC `#WheelJg` loop handles physical handwheel jog. HMI jog (step buttons) sends direct `JG` / `PA` / `BG` commands from the host — it does NOT require `XQ #WheelJg`. Direct commands work any time the controller is in IDLE or SETUP state. Do not call `XQ #WheelJg` from the HMI — that would hand control to the DMC jog loop, which waits for physical buttons to exit.

---

## Operator Workflow Sequences

These sequences define the expected interaction flow. Each step maps to a specific feature and its dependency chain.

### Sequence 1: Normal Grind Cycle (Operator)

```
1. Operator taps PIN → enters Operator session
2. RUN page shown — status indicator reads IDLE or AT-REST
3. Operator verifies axis positions match expected start positions
4. Operator taps "Go To Start" → XQ #GOSTR → machine moves to start position
5. Status indicator changes to MOVING, then AT-START when motion complete
6. Operator taps "Start Grind" → XQ #GRIND (or hmiGrnd=0)
7. cycle_running = True → plot trail begins drawing
8. Status indicator reads GRINDING
9. Operator watches plot and position labels during cycle
10. Cycle completes → DMC calls #GOREST → axes park
11. Status indicator reads AT-REST
12. cycle_running = False → plot pauses, timer stops
13. ctSesKni increments — knife count display updates
14. Operator taps "Start Grind" again for next knife
```

### Sequence 2: Stone Compensation Adjustment (Operator)

```
1. Operator notices grind is too light (not enough material removal)
2. Operator taps "More Stone" button (visible on RUN page)
3. HMI sends XQ #MOREGRI (or hmiMore=0)
4. DMC executes: startPt[3] = startPt[3] + (cpmC * 0.001)
5. Banner message: "MORE STONE ADDED"
6. Operator runs next cycle — new startPt[3] value is used in #GOSTR
7. Repeat as needed; each tap adds 0.001mm to B-axis start offset
```

### Sequence 3: Setup Mode — Jog and Teach (Setup Role)

```
1. Setup personnel unlocks Setup via PIN overlay
2. Navigates to Axes Setup tab
3. Setup mode indicator badge appears (if hmiState polling is implemented)
4. Setup personnel selects axis from sidebar (A, B, C, D)
5. Taps step-jog arrows with X1/X10/X100 multiplier
   → Each tap sends JG command (or PA relative move + BG)
6. Positions axis at desired rest/start position
7. Taps "Teach Rest" or "Teach Start" button
   → HMI sends XQ #SETREST or XQ #SETSTR
   → DMC captures current _TDA/_TDB/_TDC/_TDD into restPt[] or startPt[]
   → Arrays saved to EEPROM via BV
8. Optionally: navigate to Parameters tab, edit feedrates, tap "Write to Controller"
9. Tap "Recalculate" → XQ #VARCALC → derived values recomputed and saved to EEPROM
10. Setup personnel taps "Lock Setup" → PIN overlay re-locks, reverts to Operator view
```

### Sequence 4: New Session / Stone Change (Setup Role)

```
1. Setup personnel unlocks Setup via PIN overlay
2. Navigates to RUN page (or dedicated button location)
3. Taps "New Session" button (gated: Setup role only)
4. HMI sends XQ #NEWSESS (or hmiNewS=0)
5. DMC executes: XQ #HOME (all axes home), ctSesKni = 0
6. Machine homes — status indicator reads HOMING
7. When homing complete, status returns to IDLE
8. Physical stone change: operator replaces grind stone
9. Setup personnel runs a test cycle to verify new stone contact
10. Adjusts More/Less Stone as needed
```

### Sequence 5: Power-On / Reconnect

```
1. Machine powers on — DMC #AUTO runs: CONFIG → PARAMS → COMPED → HOME → MAIN
2. HMI app starts — controller.is_connected() = False, all position labels show "---"
3. HMI connects to controller via gclib (GOpen)
4. Poll loop starts: reads _TPA/_TPB/_TDC/_TDD at 10 Hz
5. Position labels populate with real encoder values
6. HMI reads hmiState (if implemented) — should read IDLE after #AUTO completes
7. Operator is now ready to run
```

---

## MVP Definition

### Launch With (v2.0 — Flat Grind Integration)

The minimum that makes the HMI a functional machine controller for the 4-Axes Flat Grind:

- [ ] Array name mismatch resolved (`StartPnt` vs `startPt`, `RestPnt` vs `restPt`)
- [ ] Start Grind button wired to `XQ #GRIND` — with `cycle_running = True`
- [ ] Go To Rest button wired to `XQ #GOREST` — with `cycle_running = False`
- [ ] Go To Start button added and wired to `XQ #GOSTR`
- [ ] Pause/Stop wired to `ST ABCD` + `HX` (both commands)
- [ ] Live position labels connected to real controller (remove `_show_disconnected()` override)
- [ ] More Stone / Less Stone buttons added to RUN page, wired to `XQ #MOREGRI` / `XQ #LESSGRI`
- [ ] New Session button added to RUN page (Setup role gate), wired to `XQ #NEWSESS`
- [ ] Homing button on Axes Setup page (Setup role gate), wired to `XQ #HOME`
- [ ] Parameters screen write path wired to controller (`controller.cmd("fdA=50")` pattern)
- [ ] Jog step buttons in Axes Setup confirmed to move real axes (PA relative + BG)
- [ ] Save Start / Rest point arrays confirmed to write to controller correctly

### Add After Flat Grind Validation (v2.x)

- [ ] HMI one-shot variable pattern in DMC code (hmiGrnd, hmiSetp, etc.) — add after XQ wiring validated
- [ ] `hmiState` variable in DMC + state polling in HMI — add once basic wiring works
- [ ] Setup mode badge / Run tab disable when setup active
- [ ] Knife count display (`ctSesKni`, `knfSess`) on RUN page
- [ ] Position readout in engineering units (mm/degrees) with CPM conversion
- [ ] Graceful reconnect loop in background thread
- [ ] Varcalc / Recalculate button on Parameters screen

### Future Consideration (v3.0+)

- [ ] Serration Grind integration — same pattern, different subroutine names
- [ ] Convex Grind integration — same pattern, convex-specific subroutines
- [ ] Array name validation helper before every upload/download

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Array name mismatch fix | HIGH | LOW | P1 — blocker for all save operations |
| Start Grind → XQ #GRIND | HIGH | LOW | P1 — core operator action |
| Go To Rest → XQ #GOREST | HIGH | LOW | P1 — core safety action |
| Live position labels from controller | HIGH | LOW | P1 — feedback loop |
| Stop motion (ST ABCD + HX) | HIGH | LOW | P1 — safety |
| Go To Start → XQ #GOSTR | HIGH | LOW | P1 — pre-cycle verification |
| More/Less Stone buttons | HIGH | LOW | P1 — daily operator workflow |
| Parameters write to controller | HIGH | MEDIUM | P1 — setup workflow |
| Jog confirmed on real axes | HIGH | LOW | P1 — setup workflow |
| New Session → XQ #NEWSESS | MEDIUM | LOW | P1 — stone change workflow |
| Homing button → XQ #HOME | MEDIUM | LOW | P1 — post power-on workflow |
| hmiState variable + polling | HIGH | MEDIUM | P2 — add after XQ wiring stable |
| HMI one-shot variable pattern | MEDIUM | MEDIUM | P2 — nice architecture, not MVP |
| Knife count display | MEDIUM | LOW | P2 — useful production metric |
| Position in engineering units | MEDIUM | LOW | P2 — operator comprehension |
| Setup mode badge / tab disable | MEDIUM | LOW | P2 — safety UX improvement |
| Varcalc trigger from HMI | LOW | LOW | P2 — reduces physical panel dependency |
| Graceful reconnect loop | LOW | MEDIUM | P3 — resilience feature |
| Array name validation helper | LOW | LOW | P3 — defensive coding |

---

## Sources

- Direct DMC program analysis: `4 Axis Stainless grind.dmc` — subroutines, state machine, physical I/O mapping
- Direct codebase analysis: `run.py`, `start.py`, `rest.py`, `axisDSetup.py`, `buttons_switches.py`, `app_state.py`
- Galil gclib documentation: [gclib API](https://www.galil.com/sw/pub/all/doc/gclib/html/) — XQ, MG, ST, HX, JG commands (HIGH confidence)
- Galil Raspberry Pi HMI integration: [Raspberry Pi + Galil](https://www.galil.com/news/whats-new-galil/raspberry-pi-interface-galil-controllers) — Python gclib pattern confirmed (MEDIUM confidence)
- gclib Examples: [gclib Examples](https://www.galil.com/sw/pub/all/doc/gclib/html/examples.html) — XQ syntax, variable polling (HIGH confidence)
- CNC HMI operator workflow patterns: [CNC Control Panel Guide](https://radonix.com/cnc-control-panel-functions-a-step-by-step-breakdown/) — start/stop cycle, mode indicators (MEDIUM confidence)
- CNC cycle stop patterns: [4 Ways to Stop a Cycle](https://www.mmsonline.com/articles/4-ways-to-stop-a-cycle-to-allow-operator-intervention) — ST vs HX distinction (MEDIUM confidence)
- Industrial HMI safety: [Manual Reset via HMI](https://machinerysafety101.com/2021/06/02/manual-reset-using-an-hmi/) — E-STOP hardware requirement (HIGH confidence, ISA-101 aligned)
- HMI design best practices: [HMI Design Guide](https://plcprogramming.io/blog/hmi-design-best-practices-complete-guide) — confirmation dialog anti-pattern, state indicators (MEDIUM confidence)
- Project context: `.planning/PROJECT.md` — v2.0 milestone target features, HMI variable naming

---

*Feature research for: HMI-controller integration, 4-Axes Flat Grind, Galil DMC*
*Researched: 2026-04-06*
