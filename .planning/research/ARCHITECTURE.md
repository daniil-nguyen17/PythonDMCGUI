# Architecture Research

**Domain:** HMI-to-controller integration layer — Kivy GUI + Galil DMC state machine (v2.0)
**Researched:** 2026-04-06
**Confidence:** HIGH — based on direct code audit of v1.0 codebase

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         Kivy UI Thread (Main Thread)                      │
│                                                                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │
│  │  RunScreen │  │AxesSetup   │  │ Parameters │  │  SetupScreen       │ │
│  │  (run.py)  │  │Screen      │  │Screen      │  │  (setup.py)        │ │
│  │            │  │            │  │            │  │                    │ │
│  │ 10Hz poll  │  │ 10Hz poll  │  │ read/write │  │ connect/discover   │ │
│  │  clock     │  │  clock     │  │  on enter  │  │                    │ │
│  │ 5Hz plot   │  │            │  │            │  │                    │ │
│  │  clock     │  │            │  │            │  │                    │ │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └────────┬───────────┘ │
│        │               │               │                   │             │
│        └───────────────┴───────────────┴──────────────────┘             │
│                         Clock.schedule_once() ^                          │
│                         (all UI writes from threads go here)             │
└──────────────────────────────────────────────────────────────────────────┘
                                    |
                              jobs.submit()
                                    |
┌──────────────────────────────────────────────────────────────────────────┐
│                    Background Thread Pool (jobs.py)                       │
│                                                                           │
│   JobThread - single FIFO worker thread                                  │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  NEW: HMICommandService -- wraps one-shot variable write pattern│   │
│   │  NEW: DMC state read added to existing RunScreen._do_poll()     │   │
│   │  Existing: array read/write, status poll, PA/BG commands        │   │
│   └────────────────────────────┬────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────────┘
                                    |
                           GalilController.cmd()
                                    |
┌──────────────────────────────────────────────────────────────────────────┐
│                       GalilController (controller.py)                     │
│                                                                           │
│   cmd()  upload_array()  download_array()  connect()  disconnect()        │
│   [NEW] write_hmi_var(name)  -- sends "name=0" to trigger one-shot       │
│   [NEW] read_hmi_var(name)   -- sends "MG name" to verify reset to 1     │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
                                    |
                             gclib GCommand()
                                    |
┌──────────────────────────────────────────────────────────────────────────┐
│                         DMC Controller Hardware                            │
│                                                                           │
│   #AUTO -> #CONFIG -> #PARAMS -> #COMPED -> #HOME -> #MAIN -> #WtAtRt    │
│                                                                           │
│   HMI Variables (default=1, trigger on 0, reset to 1 in block):          │
│     hmiGrnd  -> #GRIND       hmiSetp -> #SETUP     hmiMore -> #MOREGRI  │
│     hmiNewS  -> #NEWSESS     hmiLess -> #LESSGRI   hmiHome -> #HOME     │
│     hmiJog   -> #WheelJg     hmiCalc -> #VARCALC                        │
│                                                                           │
│   State Variable (to be added to DMC): hmiState                          │
│     e.g. 0=idle, 1=main loop, 2=grinding, 3=setup, 4=homing, 5=jogging  │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Status |
|-----------|---------------|--------|
| `GalilController` (controller.py) | All gclib calls; the only class that touches hardware | EXISTS — extend with `write_hmi_var()` and `read_hmi_var()` |
| `HMICommandService` (new) | Wraps the one-shot write pattern; optionally waits for reset confirmation | NEW — thin wrapper, ~40 lines |
| `MachineState` (app_state.py) | Observable dataclass; source of truth for UI state | EXISTS — add `dmc_state: int` and `dmc_loop: str` fields |
| `RunScreen` (screens/run.py) | Operator run page: Start Grind, Go To Rest, Go To Start, More/Less, New Session | EXISTS — add HMI trigger calls to action handlers; extend `_do_poll` for `hmiState` |
| `AxesSetupScreen` (screens/axes_setup.py) | Jog controls, teach points — triggers DMC #SETUP/#HOME/#WheelJg | EXISTS — add HMI trigger calls to jog/home/setup entry buttons |
| `ParametersScreen` (screens/parameters.py) | Reads/writes named vars; triggers #VARCALC after save | EXISTS — add `hmiCalc=0` after batch apply |
| `jobs` (utils/jobs.py) | Single FIFO background thread; all gclib I/O submits here | EXISTS — no changes needed |
| `hmi/dmc_vars.py` (new) | String constants for all HMI variable names and state codes | NEW — zero-risk constants file |

---

## Recommended Project Structure

```
src/dmccodegui/
├── controller.py           # MODIFY: add write_hmi_var(), read_hmi_var()
├── app_state.py            # MODIFY: add dmc_state, dmc_loop fields
├── hmi/                    # NEW package
│   ├── __init__.py
│   ├── commands.py         # HMICommandService -- one-shot write + optional ack
│   └── dmc_vars.py         # Constants: HMI var names, state codes
├── screens/
│   ├── run.py              # MODIFY: wire action buttons to HMI vars; extend _do_poll
│   ├── axes_setup.py       # MODIFY: jog/home/setup buttons -> HMI vars
│   └── parameters.py       # MODIFY: apply -> trigger hmiCalc
└── utils/
    └── jobs.py             # NO CHANGE
```

### Structure Rationale

- **hmi/ package:** Isolates all HMI-specific logic. `commands.py` is testable with a mock `GalilController`. The `dmc_vars.py` constants file prevents 8-character var name typos across screens.
- **Modifying controller.py:** `write_hmi_var()` and `read_hmi_var()` are thin wrappers over `cmd()`. They belong on `GalilController` because all gclib calls live there — the threading rule is enforced at one point.
- **No new threads:** The existing `jobs.submit()` FIFO handles all new gclib writes. The existing 10Hz `_update_clock` in `RunScreen` handles the polling extension. No new thread primitives needed.

---

## Architectural Patterns

### Pattern 1: One-Shot HMI Variable Trigger

**What:** The HMI sends `var=0` to activate a block in the DMC program. The DMC resets the variable to `1` when entering that block. Default value is `1` (inactive). This creates a one-shot edge-triggered activation.

**When to use:** Every button that maps to a named `#LABEL` in the DMC program.

**Trade-offs:** Simple and robust. No ACK needed for normal buttons — the state change poll confirms it worked. The risk is if the HMI sends `var=0` while the DMC is not in the right loop to service it; the variable stays `0` until the DMC evaluates that branch. Acceptable for single-operator use.

**Example — HMICommandService:**

```python
# hmi/commands.py
import time
from ..controller import GalilController


class HMICommandService:
    def __init__(self, controller: GalilController) -> None:
        self._ctrl = controller

    def trigger(self, var_name: str) -> None:
        """Send var_name=0 to activate the one-shot trigger in the DMC program.

        Called from a background thread (via jobs.submit).
        Raises RuntimeError if not connected.
        """
        self._ctrl.cmd(f"{var_name}=0")

    def trigger_and_wait(self, var_name: str, timeout_s: float = 2.0) -> bool:
        """Trigger and poll until DMC resets var back to 1 (confirms entry).

        Returns True if DMC acknowledged within timeout.
        Only use for blocking modal flows (e.g. initial homing). See Anti-Pattern 4.
        """
        self._ctrl.cmd(f"{var_name}=0")
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            raw = self._ctrl.cmd(f"MG {var_name}").strip()
            try:
                if float(raw) == 1.0:
                    return True
            except ValueError:
                pass
            time.sleep(0.05)
        return False
```

```python
# hmi/dmc_vars.py -- constant definitions prevent typos and document the DMC interface
HMI_GRIND       = "hmiGrnd"   # Main loop: enter #GRIND
HMI_SETUP       = "hmiSetp"   # Main loop: enter #SETUP
HMI_MORE        = "hmiMore"   # Main loop: enter #MOREGRI (more stone)
HMI_LESS        = "hmiLess"   # Main loop: enter #LESSGRI (less stone)
HMI_NEW_SESSION = "hmiNewS"   # Main loop: enter #NEWSESS (stone change)
HMI_HOME        = "hmiHome"   # Setup loop: enter #HOME
HMI_JOG         = "hmiJog"    # Setup loop: enter #WheelJg
HMI_CALC        = "hmiCalc"   # Setup loop: enter #VARCALC

# State variable written by DMC to report current loop
HMI_STATE_VAR = "hmiState"

# State codes (must match values set in DMC program)
STATE_IDLE      = 0
STATE_MAIN      = 1
STATE_GRINDING  = 2
STATE_SETUP     = 3
STATE_HOMING    = 4
STATE_JOGGING   = 5
STATE_NEWSESS   = 6

STATE_LABELS = {
    STATE_IDLE:     "Idle",
    STATE_MAIN:     "Main Loop",
    STATE_GRINDING: "Grinding",
    STATE_SETUP:    "Setup",
    STATE_HOMING:   "Homing",
    STATE_JOGGING:  "Jogging",
    STATE_NEWSESS:  "New Session",
}
```


### Pattern 2: Extend the Existing 10Hz Poll for State Reading

**What:** `RunScreen._do_poll()` already runs at 10Hz in a background thread. Extend it to also read `hmiState` in the same background call. The result is posted to `MachineState` via the existing `Clock.schedule_once` return path.

**When to use:** Any DMC variable that drives UI state (current loop, cycle progress). Piggybacking on the existing poll avoids adding a second clock.

**Trade-offs:** Adds one `MG hmiState` call per 10Hz tick (~10ms round-trip). Tight coupling between RunScreen and DMC state is already the design. The poll only runs when RunScreen is visible — acceptable because all main loop buttons live on RunScreen.

**Example:**

```python
# Extend RunScreen._do_poll() -- new lines marked # NEW
def _do_poll(self) -> None:
    try:
        pos = {}
        for axis in ("A", "B", "C", "D"):
            raw = self.controller.cmd(f"MG _TP{axis}")
            pos[axis] = float(raw.strip())

        # NEW: read DMC state variable
        dmc_state = 0
        try:
            raw_state = self.controller.cmd("MG hmiState")
            dmc_state = int(float(raw_state.strip()))
        except Exception:
            pass

        # NEW: pass dmc_state through to _apply_ui
        Clock.schedule_once(lambda *_: self._apply_ui(pos, {}, dmc_state))
    except Exception as e:
        print(f"[RunScreen] Poll error: {e}")

# _apply_ui receives dmc_state and writes to MachineState
def _apply_ui(self, pos: dict, cycle: dict, dmc_state: int = 0) -> None:
    # ... existing pos updates (unchanged) ...
    if self.state:
        self.state.dmc_state = dmc_state  # NEW
        self.state.notify()               # NEW (or call existing notify path)
```


### Pattern 3: Button Press -> jobs.submit -> controller.cmd -> Clock.schedule_once

**What:** All HMI trigger button presses follow the same three-step path: (1) UI calls `jobs.submit(fn)` on the main thread, (2) the background thread calls `controller.cmd("var=0")` (or `HMICommandService.trigger(var)`), (3) errors are posted back via `Clock.schedule_once`. This is the pattern already in `ButtonsSwitchesScreen`, `StartScreen`, and `RunScreen`.

**When to use:** Every button that sets an HMI variable. HMI triggers are a new category of command using the established pattern.

**Trade-offs:** No new abstractions needed for basic triggers. `HMICommandService` is optional — screens can call `self.controller.cmd("hmiGrnd=0")` via the existing `dmcCommand()` helper. The service class pays off when `trigger_and_wait()` is needed.

**Example (minimal, no new service needed for most buttons):**

```python
# In RunScreen -- wiring the "Start Grind" button
def on_grind_button(self) -> None:
    """Trigger #GRIND in DMC main loop via hmiGrnd one-shot variable."""
    if not self.controller or not self.controller.is_connected():
        self._alert("No controller connected")
        return

    def _trigger():
        try:
            self.controller.cmd("hmiGrnd=0")
        except Exception as e:
            Clock.schedule_once(lambda *_: self._alert(f"Grind trigger failed: {e}"))

    jobs.submit(_trigger)
```

---

## Data Flow

### Button Press -> Controller -> State Change -> UI Update

```
[Operator taps "Start Grind" on RunScreen]
        |
        v
[RunScreen.on_grind_button()]  -- Kivy main thread
        |
        v  jobs.submit(_trigger)
        |
[Background thread: _trigger()]
        |
        v  self.controller.cmd("hmiGrnd=0")
        |
[GalilController.cmd()]  -- gclib.GCommand("hmiGrnd=0")
        |
        v  (network/USB to controller hardware)
[DMC Program: #WtAtRt polling loop sees hmiGrnd=0]
        |  jumps to #GRIND, resets hmiGrnd=1, sets hmiState=2
        v
[10Hz poll picks up hmiState=2 on next tick]
        |
[Background thread: RunScreen._do_poll()]
        |
        v  Clock.schedule_once(_apply_ui)
        |
[RunScreen._apply_ui()]  -- Kivy main thread
        |  MachineState.dmc_state = 2 -> notify()
        v
[UI updates: button highlight, status label, cycle_running=True]
```

### Parameter Save -> Controller -> #VARCALC Trigger

```
[Operator taps "Apply All" on ParametersScreen]
        |
        v
[ParametersScreen._apply_all()]  -- main thread
        |
        v  jobs.submit(_do_apply)
        |
[Background thread: _do_apply()]
  for each dirty param:
      controller.cmd("varName=value")
  controller.cmd("BV")           -- burn to NV
  controller.cmd("hmiCalc=0")   -- NEW: trigger #VARCALC in setup loop
        |
        v  Clock.schedule_once(_on_apply_done)
        |
[ParametersScreen._on_apply_done()]  -- main thread
  show "Parameters saved + recalculated" banner
```

### Jog Button -> Setup Loop Integration

```
[Operator taps "Jog Wheel" on AxesSetupScreen]
        |
        v  jobs.submit
[Background: controller.cmd("hmiJog=0")]
        |
[DMC: #SETUP loop sees hmiJog=0, jumps to #WheelJg]
        |  (physical jog runs; exits #WheelJg via @IN[32] or hmi exit var)
        v
[10Hz poll reads updated axis positions on AxesSetupScreen]
        v
[AxesSetupScreen displays live positions]
```

### Key Data Flows Summary

1. **Button trigger:** UI thread -> `jobs.submit` -> `controller.cmd("hmiVar=0")` -> DMC acts -> next 10Hz poll confirms via `hmiState`
2. **State poll:** 10Hz clock -> `jobs.submit(_do_poll)` -> `controller.cmd("MG hmiState")` + axis positions -> `Clock.schedule_once` -> `MachineState.dmc_state = N` -> `state.notify()` -> subscribed UI updates
3. **Parameter apply:** ParametersScreen dirty flush -> write vars -> `BV` -> `hmiCalc=0` — no ACK needed; next poll confirms DMC is still running
4. **Connection lost:** Any `controller.cmd()` raises `RuntimeError` -> `_alert()` via `Clock.schedule_once` -> banner shows -> poll clock guard (`if not self.controller.is_connected(): return`) silences further errors

---

## Integration Points with Existing Code

### What to Modify

| File | What Changes | Why |
|------|-------------|-----|
| `controller.py` | Add `write_hmi_var(name)` and `read_hmi_var(name)` convenience methods | Thin wrappers over `cmd()` that document the one-shot pattern; optional but useful for clarity |
| `app_state.py` | Add `dmc_state: int = 0` and `dmc_loop: str = ""` fields | Screens need reactive properties for DMC loop status to drive button enable/disable |
| `screens/run.py` | Wire `on_start_pause_toggle`, `on_go_to_rest`, More/Less, New Session to HMI vars; extend `_do_poll` to read `hmiState` | The current `on_start_pause_toggle` sends `XQ #CYCLE` / `HX` directly, which bypasses the DMC state machine; must change to `hmiGrnd=0` |
| `screens/axes_setup.py` | Add HMI trigger calls to jog, home, and setup entry buttons | Setup loop requires `hmiSetp=0` to enter #SETUP, `hmiJog=0` for wheel jog, `hmiHome=0` for homing |
| `screens/parameters.py` | After batch apply, send `hmiCalc=0` to trigger #VARCALC | Ensures DMC recalculates derived parameters after NV write; existing apply flow already goes through `jobs.submit` |

### What to Add (New Components)

| File | Purpose | Size | Dependencies |
|------|---------|------|-------------|
| `hmi/__init__.py` | Package marker | 1 line | none |
| `hmi/dmc_vars.py` | String constants for all HMI variable names and state codes | ~30 lines | none |
| `hmi/commands.py` | `HMICommandService` with `trigger()` and `trigger_and_wait()` | ~40 lines | `GalilController` |

### What to Leave Unchanged

| Component | Reason |
|-----------|--------|
| `utils/jobs.py` | The FIFO single-worker model already handles serial gclib access correctly |
| `machine_config.py` | HMI vars are not machine-type-specific for Flat Grind; same `hmiGrnd` etc. used throughout |
| `auth/` | No auth changes needed for v2.0 HMI integration |
| `utils/transport.py` | Transport layer is already solid; no changes needed |
| KV files (structural layout) | Layouts established in v1.0; only add/modify button `on_release` bindings |

### Existing Pattern Already in Codebase

The `dmcCommand()` helper method on `ButtonsSwitchesScreen` and `StartScreen` shows the established pattern. For HMI variable triggers, use the same shape:

```python
# This pattern already exists in start.py and buttons_switches.py
# HMI triggers follow the same three lines
def dmcCommand(self, command: str) -> None:
    if not self.controller or not self.controller.is_connected():
        self._alert("No controller connected")
        return

    def do_command():
        try:
            self.controller.cmd(command)
        except Exception as e:
            Clock.schedule_once(lambda *_: self._alert(f"Command failed: {e}"))

    jobs.submit(do_command)
```

HMI variable writes (`"hmiGrnd=0"`) go through this same helper — they are just a specific class of DMC command.

---

## Anti-Patterns

### Anti-Pattern 1: Calling gclib from the Main Thread

**What people do:** Call `self.controller.cmd(...)` directly inside a button `on_release` handler or a `Clock.schedule_interval` callback.

**Why it's wrong:** gclib blocks on network/USB I/O — typically 5-50ms per call. On 60Hz Kivy, this causes visible frame drops and delays E-STOP processing. On Pi, it can freeze the UI for hundreds of milliseconds.

**Do this instead:** Always `jobs.submit(fn)` where `fn` contains all `controller.cmd()` calls. The existing codebase is 100% consistent on this rule — all new HMI trigger code must maintain it.


### Anti-Pattern 2: Adding a Dedicated HMI State Poll Clock

**What people do:** Add a new `Clock.schedule_interval` specifically for HMI state polling, independent of the existing 10Hz poll.

**Why it's wrong:** Two clocks both submitting to `jobs.submit` means two poll jobs can queue per tick. Under load, queue depth grows and poll latency increases. Both clocks enqueue jobs even when the controller is slow — queue backs up.

**Do this instead:** Extend the existing `RunScreen._do_poll()` background function to also read `hmiState` in the same background call. One round-trip to the controller per tick, one Clock driving it.


### Anti-Pattern 3: Inline String Literals for HMI Variable Names

**What people do:** Write `self.controller.cmd("hmiGrnd=0")` directly in 5 different places.

**Why it's wrong:** The DMC program has an 8-character variable name limit and names are case-sensitive at the gclib level. A single typo silently does nothing — the controller ignores unknown variable assignments with no error message.

**Do this instead:** Define all HMI variable names as constants in `hmi/dmc_vars.py`. Reference only the constants in screen code. This also makes it trivial to audit which DMC variables the GUI touches.


### Anti-Pattern 4: Using trigger_and_wait() on Every Button

**What people do:** Use `trigger_and_wait()` on every button press to guarantee the DMC acknowledged before the UI continues.

**Why it's wrong:** `trigger_and_wait()` blocks the `jobs` FIFO worker for up to `timeout_s` per button press. During that time, no other background jobs can run — position polling stalls, the UI appears frozen, and the E-STOP command (which also goes through `jobs.submit`) would be delayed.

**Do this instead:** Use `trigger()` (fire-and-forget) for all normal operation buttons. Reserve `trigger_and_wait()` only for modal blocking flows where the UI explicitly shows a "Please wait..." state and the operator cannot press anything else. In those cases, disable the UI before submitting, and re-enable it in the `Clock.schedule_once` completion callback.


### Anti-Pattern 5: Replacing XQ #CYCLE with HMI Vars Without Updating the DMC Program

**What people do:** Change `run.py` to send `hmiGrnd=0` but forget to update the `.dmc` file to OR the HMI variable condition alongside the physical `@IN[]` input.

**Why it's wrong:** If the DMC program only checks `@IN[30]` and not `hmiGrnd`, sending `hmiGrnd=0` has no effect. The GUI silently does nothing.

**Do this instead:** The DMC code change is a prerequisite for all HMI var wiring. The pattern in the DMC program should be:

```
' Before: IF (@IN[30]=0)
' After:  IF ((@IN[30]=0)||(hmiGrnd=0))
hmiGrnd=1  ' reset the variable
JP #GRIND
```

Confirm DMC code is updated and tested on hardware before wiring the GUI buttons.

---

## Suggested Build Order

The build order is driven by three dependency chains:

1. **Foundation first:** `MachineState` fields and `GalilController` methods must exist before any screen can use them.
2. **Read before write:** The state poller (passive read) should be validated before wiring active button triggers.
3. **Main loop before setup loop:** RunScreen buttons are the critical path for operator use; setup loop integration (AxesSetup, Parameters) comes after.

```
Phase 1 -- Foundation (no UI changes, testable with mock controller)
  1a. Add hmi/dmc_vars.py (constants only -- zero risk, zero tests needed)
  1b. Add write_hmi_var() / read_hmi_var() to GalilController
  1c. Add dmc_state, dmc_loop to MachineState dataclass
  1d. Update DMC .dmc file: add hmiState variable + OR conditions on all buttons
      (This is a HARD PREREQUISITE -- nothing else works without it)

Phase 2 -- State Poll (RunScreen read path)
  2a. Extend RunScreen._do_poll() to read hmiState
  2b. Extend RunScreen._apply_ui() to write MachineState.dmc_state
  2c. Validate on real controller: confirm poll updates state correctly at 10Hz

Phase 3 -- Main Loop Button Triggers (RunScreen write path)
  3a. Wire "Start Grind" button -> hmiGrnd=0
      (replace existing XQ #CYCLE call)
  3b. Wire "Go To Rest" button -> hmi var for #GOREST
      (existing XQ #REST may be kept if DMC doesn't use a var for it)
  3c. Wire "Go To Start" button -> hmi var for #GOSTR (if applicable)
  3d. Wire "More Stone" -> hmiMore=0
  3e. Wire "Less Stone" -> hmiLess=0
  3f. Wire "New Session" -> hmiNewS=0
  3g. Validate each button on real controller in sequence

Phase 4 -- Setup Loop Button Triggers
  4a. Wire "Enter Setup" (AxesSetupScreen entry) -> hmiSetp=0
  4b. Wire "Jog Wheel" -> hmiJog=0
  4c. Wire "Home" -> hmiHome=0
  4d. Wire "Apply Parameters" -> flush dirty vars + BV + hmiCalc=0
  4e. Validate setup loop round-trip on real controller

Phase 5 -- Live Position Plot Connection
  5a. Confirm RunScreen position poll reads real axis positions (A, B, C, D)
  5b. Confirm plot buffer fills during active #GRIND cycle
  5c. Tune PLOT_UPDATE_HZ and PLOT_BUFFER_SIZE for Pi CPU load
      (currently 5Hz / 750 points -- adjust based on observed Pi load)

Phase 6 -- State-Driven UI Feedback
  6a. Disable/enable buttons based on dmc_state
      (e.g. "Start Grind" disabled unless dmc_state == STATE_MAIN)
  6b. Show status label text derived from dmc_state
      ("Grinding...", "In Setup", "Homing...", etc.)
  6c. Consider: prevent navigating away from RunScreen while grinding
      (soft interlock -- operator must be warned, not hard-blocked)
```

**Dependencies that enforce this order:**
- Phase 1d (DMC code) must precede Phases 3 and 4 -- you cannot test HMI vars without them in the DMC program.
- Phase 2 (read) must precede Phase 6 (state-driven UI) -- cannot gate buttons on state you are not reading.
- Phase 3 and 4 are independent of each other after Phase 1. Phase 3 first because RunScreen is the operator's primary screen.
- Phase 5 can run in parallel with Phase 4 -- only needs the existing position poll from Phase 2.
- Phase 6 can start in parallel with Phase 4/5 after Phase 2 is validated.

---

## Scaling Considerations

This is a single-machine, single-operator industrial HMI. Scaling is not a concern. The relevant sizing questions are Pi 4/5 CPU budget and gclib round-trip latency.

| Concern | Current State | With HMI Integration | Mitigation |
|---------|--------------|---------------------|------------|
| gclib calls per 10Hz tick | ~4 (axis positions) | ~5 (+1 for hmiState) | Negligible; one extra MG per tick |
| UI thread frame time | Less than 16ms | Less than 16ms | All gclib off main thread; unchanged |
| jobs queue depth under load | 1-2 items | 1-2 items | Same FIFO, same rate |
| Pi 4 CPU load (plot) | ~15% (5Hz redraw) | ~15% | Plot clock unchanged |
| Parameter apply (batch) | N/A in v1.0 | 20+ cmd() calls in one submit | One-shot operation, non-periodic; UI shows loading indicator |

The only load risk is during parameter apply (batch var writes) -- 20+ sequential `cmd()` calls from one `jobs.submit`. This blocks the FIFO worker for up to 200-500ms. This is acceptable as long as the UI shows a loading indicator during this window and the apply button is disabled until the job completes.

---

## Sources

- Direct code audit: `controller.py`, `app_state.py`, `main.py`, `screens/run.py`, `screens/setup.py`, `screens/start.py`, `screens/buttons_switches.py`, `screens/parameters.py`, `utils/jobs.py`, `machine_config.py` (2026-04-06)
- `.planning/PROJECT.md` -- v2.0 milestone context, HMI variable names, DMC state machine flow (2026-04-06)
- HMI one-shot variable pattern documented in PROJECT.md: default=1, trigger on 0, DMC resets to 1 on block entry

---

*Architecture research for: HMI-controller integration layer, v2.0 Flat Grind Integration milestone*
*Researched: 2026-04-06*
