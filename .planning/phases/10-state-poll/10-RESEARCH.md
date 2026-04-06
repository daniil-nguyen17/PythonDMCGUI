# Phase 10: State Poll - Research

**Researched:** 2026-04-06
**Domain:** Kivy/Python polling loop, Galil DMC controller reads, MachineState pub-sub, connection recovery
**Confidence:** HIGH — all findings derived from direct codebase inspection, not external sources

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Poll architecture:**
- Single app-wide poller in main.py replaces RunScreen's per-screen _do_poll
- 10 Hz poll tick using Clock.schedule_interval, submits work to background jobs thread
- Python reads _TP (tell position) directly for axis positions — no DMC-side position variables needed
- Python reads hmiState, ctSesKni, ctStnKni via MG commands on named variables
- All data read in one batch per tick: hmiState + _TPA/_TPB/_TPC/_TPD + ctSesKni + ctStnKni

**DMC thread 2 label (new):**
- New DMC label running on thread 2 handles hmiState management and knife counting
- Thread 2 owns hmiState — it observes HMI trigger variables (hmiGrnd, hmiSetp, etc.) and sets hmiState based on which trigger fired (0 = action starting), then watches for reset to 1 (action complete, return to IDLE)
- Thread 2 does NOT write to trigger variables — purely observes them
- Thread 2 loop uses WT (wait) delay between iterations to avoid hogging controller cycles
- stoneKnf counter (ctStnKni) increments alongside ctSesKni at grind cycle completion, resets to 0 in #NEWSESS when hmiNewS fires

**Connection loss & recovery:**
- Disconnect detection: 3 consecutive poll failures marks as disconnected (~300ms at 10 Hz)
- UI on disconnect: freeze last known axis positions + red "DISCONNECTED (Xs)" banner with elapsed time counter
- Poller keeps retrying at full 10 Hz during disconnect — no backoff
- On disconnect: close the gclib handle. On reconnect attempt: try GOpen to reopen
- Auto-reconnect: silent, no operator action needed. When a poll succeeds, clear disconnect banner and resume normal display
- On reconnect: just resume polling, no program-running verification. hmiState=0 (uninitialized) signals if DMC program isn't running

**Knife count display:**
- Two counters visible on the Run page cycle status area: ctSesKni and ctStnKni
- DMC variable name for stone count: `ctStnKni` (matches ct-prefix pattern of ctSesKni)
- stoneKnf variable added to DMC program in THIS phase (not deferred to Phase 12)
  - Declared in #PARAMS
  - Incremented alongside ctSesKni in grind completion block
  - Reset to 0 in #NEWSESS subroutine

**Data flow to MachineState:**
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

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| POLL-01 | HMI polls hmiState from controller at 10 Hz and updates MachineState.dmc_state | Poller module reads `MG hmiState`, writes to `MachineState.dmc_state`, triggers `notify()` |
| POLL-02 | HMI polls axis positions (A, B, C, D) from controller and displays live values on Run page | Batch read `MG _TPA,_TPB,_TPC,_TPD`, RunScreen subscribes to MachineState; replaces _do_poll |
| POLL-03 | HMI detects controller connection loss and displays disconnected status | 3-consecutive-failure counter, GClose/GOpen reconnect cycle, red banner with elapsed time |
| POLL-04 | HMI reads knife count (ctSesKni) from controller and displays on Run page | `MG ctSesKni` + `MG ctStnKni` in batch read; new MachineState fields; Run page KV labels |
</phase_requirements>

---

## Summary

Phase 10 moves controller polling from a per-screen concern to an app-wide concern. Currently, `RunScreen._do_poll` issues individual `MG _TP{axis}` commands at 10 Hz and updates local Kivy properties directly. The new architecture creates a `hmi/poll.py` module with a single poller that submits one batch read per tick through `jobs.submit()`, writes all results to `MachineState`, then lets RunScreen (and future screens) react via the existing `subscribe()` pattern.

The codebase already has all load-bearing infrastructure in place: `MachineState` has `dmc_state`, `pos`, `connected`, and `subscribe()`/`notify()`; `jobs.py` has both `submit()` for one-off work and `schedule()` for periodic callbacks; `GalilController.cmd()` issues arbitrary MG queries; `dmc_vars.py` has `HMI_STATE_VAR` and all state constants. Phase 10 wires these pieces together with a new `hmi/poll.py` module, extends `MachineState` with knife-count fields and a derived `cycle_running` property, and makes RunScreen subscribe rather than poll directly.

The DMC program also needs one addition: a Thread 2 label (`#THRD2`) that manages `hmiState` transitions and increments both knife counters, plus a `ctStnKni` variable declared in `#PARAMS` and reset in `#NEWSESS`. Without Thread 2, `hmiState` updates would only occur inside the subroutines themselves — with Thread 2, the state machine is continuously maintained regardless of which subroutine the main thread is running.

**Primary recommendation:** Create `hmi/poll.py` as a self-contained poller class; keep `MachineState` pure-Python; wire RunScreen to subscribe rather than poll; add Thread 2 and ctStnKni to the DMC program.

---

## Standard Stack

### Core
| Component | Version/Location | Purpose | Why Standard |
|-----------|-----------------|---------|--------------|
| `kivy.clock.Clock.schedule_interval` | Kivy ≥2.2 | 10 Hz tick on Kivy main thread | Only correct way to drive periodic work on Kivy's main thread |
| `utils/jobs.py JobThread.submit()` | Project — `src/dmccodegui/utils/jobs.py` | Off-thread gclib calls | Single FIFO worker; serializes all gclib access |
| `GalilController.cmd()` | Project — `src/dmccodegui/controller.py` | MG queries to controller | Handles gclib errors, logging, is_connected guard |
| `MachineState.subscribe()` / `notify()` | Project — `src/dmccodegui/app_state.py` | Screen-to-state pub-sub | Already used by StatusBar; extend to RunScreen |

### Supporting
| Component | Location | Purpose | When to Use |
|-----------|---------|---------|-------------|
| `Clock.schedule_once` | Kivy | Post results back to main thread | Every time a background job needs to update UI |
| `GalilController.disconnect()` / `connect()` | controller.py | Close + reopen gclib handle on reconnect | Called by poller when consecutive failures hit threshold |
| `dmc_vars.py` constants | `hmi/dmc_vars.py` | Variable name strings | All MG command strings must use constants, never raw strings |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single batch MG read per tick | One MG per variable | Fewer round-trips; preferred unless batch parsing proves unreliable |
| jobs.submit per tick | jobs.schedule at module level | submit-per-tick gives Clock control over when work is queued; schedule runs on its own thread separate from main clock |

**Installation:** No new dependencies. All required libraries already in the project.

---

## Architecture Patterns

### Recommended Project Structure
```
src/dmccodegui/
├── hmi/
│   ├── __init__.py
│   ├── dmc_vars.py          # constants — EXTEND with CT_SES_KNI, CT_STN_KNI
│   └── poll.py              # NEW: ControllerPoller class
├── app_state.py             # EXTEND: session_knife_count, stone_knife_count, cycle_running property
├── main.py                  # WIRE: start/stop poller on connect/disconnect
└── screens/
    └── run.py               # REPLACE _do_poll with MachineState subscription
```

### Pattern 1: Centralized Poller Module (hmi/poll.py)

**What:** A class that owns the Clock event and failure counter, submits batch reads to jobs, posts results to MachineState.
**When to use:** This is the only correct pattern — no per-screen polling.

```python
# hmi/poll.py — illustrative skeleton
from kivy.clock import Clock
from ..utils import jobs
from ..hmi.dmc_vars import HMI_STATE_VAR, CT_SES_KNI, CT_STN_KNI

class ControllerPoller:
    POLL_HZ = 10
    DISCONNECT_THRESHOLD = 3  # consecutive failures before marking disconnected

    def __init__(self, controller, state):
        self._controller = controller
        self._state = state
        self._clock_event = None
        self._fail_count = 0
        self._disconnect_start: float | None = None

    def start(self) -> None:
        if self._clock_event is None:
            self._clock_event = Clock.schedule_interval(
                self._on_tick, 1.0 / self.POLL_HZ
            )

    def stop(self) -> None:
        if self._clock_event:
            self._clock_event.cancel()
            self._clock_event = None

    def _on_tick(self, dt: float) -> None:
        """Main thread: submit background read every tick."""
        jobs.submit(self._do_read)

    def _do_read(self) -> None:
        """Background thread: batch read all polled variables."""
        try:
            # Batch: hmiState + 4 positions + 2 knife counts
            state_val = int(float(self._controller.cmd(f"MG {HMI_STATE_VAR}").strip()))
            pos_a = float(self._controller.cmd("MG _TPA").strip())
            pos_b = float(self._controller.cmd("MG _TPB").strip())
            pos_c = float(self._controller.cmd("MG _TPC").strip())
            pos_d = float(self._controller.cmd("MG _TPD").strip())
            ses_kni = int(float(self._controller.cmd(f"MG {CT_SES_KNI}").strip()))
            stn_kni = int(float(self._controller.cmd(f"MG {CT_STN_KNI}").strip()))

            # Success — reset failure counter
            self._fail_count = 0
            Clock.schedule_once(lambda *_: self._apply(
                state_val, pos_a, pos_b, pos_c, pos_d, ses_kni, stn_kni
            ))
        except Exception:
            self._fail_count += 1
            if self._fail_count >= self.DISCONNECT_THRESHOLD:
                Clock.schedule_once(lambda *_: self._on_disconnect())

    def _apply(self, dmc_state, a, b, c, d, ses_kni, stn_kni) -> None:
        """Main thread: write results to MachineState."""
        s = self._state
        if not s.connected:
            s.connected = True
            self._disconnect_start = None
        s.dmc_state = dmc_state
        s.pos.update({"A": a, "B": b, "C": c, "D": d})
        s.session_knife_count = ses_kni
        s.stone_knife_count = stn_kni
        s.notify()

    def _on_disconnect(self) -> None:
        """Main thread: mark disconnected, close gclib handle."""
        import time
        if self._disconnect_start is None:
            self._disconnect_start = time.monotonic()
        self._state.connected = False
        self._state.notify()
        # Close handle so reconnect attempt gets a fresh GOpen
        jobs.submit(self._controller.disconnect)
```

### Pattern 2: MachineState Extension

**What:** Add two new integer fields and convert `cycle_running` from a stored bool to a derived `@property`.
**When to use:** Exactly as specified — state authority is the controller, not Python.

```python
# app_state.py additions
from dataclasses import dataclass, field
from .hmi.dmc_vars import STATE_GRINDING

@dataclass
class MachineState:
    # ... existing fields ...
    dmc_state: int = 0
    session_knife_count: int = 0
    stone_knife_count: int = 0

    # Remove stored cycle_running bool — replace with derived property:
    @property
    def cycle_running(self) -> bool:
        return self.dmc_state == STATE_GRINDING
```

**Important:** The existing `test_machine_state_cycle.py` tests assert `cycle_running == False` on a fresh state. With `dmc_state=0` (STATE_UNINITIALIZED != STATE_GRINDING), this property returns `False` by default — tests pass without modification.

### Pattern 3: RunScreen Subscription Replacement

**What:** Remove `_update_clock_event`, `_do_poll`, and `_apply_ui` from RunScreen. Subscribe to MachineState in `on_pre_enter`, unsubscribe in `on_leave`.
**When to use:** This is the target state — RunScreen becomes a pure view.

```python
# screens/run.py — on_pre_enter replacement
def on_pre_enter(self, *args) -> None:
    self._apply_machine_type_widgets()
    # Subscribe to MachineState — called on every poll tick (10 Hz)
    self._state_unsub = self.state.subscribe(
        lambda s: Clock.schedule_once(lambda *_: self._apply_state(s))
    )
    # ... existing plot clock ...
    self._plot_clock_event = Clock.schedule_interval(self._tick_plot, 1.0 / PLOT_UPDATE_HZ)

def on_leave(self, *args) -> None:
    if hasattr(self, '_state_unsub') and self._state_unsub:
        self._state_unsub()
        self._state_unsub = None
    if self._plot_clock_event:
        self._plot_clock_event.cancel()
        self._plot_clock_event = None

def _apply_state(self, s: MachineState) -> None:
    """Apply MachineState fields to RunScreen Kivy properties."""
    if s.connected:
        for axis, prop in (("A","pos_a"), ("B","pos_b"), ("C","pos_c"), ("D","pos_d")):
            val = s.pos.get(axis)
            self._set_pos(prop, val)
    else:
        self._show_disconnected()
    # Knife counts
    self.session_knife_count = str(s.session_knife_count)
    self.stone_knife_count = str(s.stone_knife_count)
```

### Pattern 4: Disconnect Banner with Elapsed Time

**What:** A Kivy StringProperty on the app or RunScreen that formats "DISCONNECTED (Xs)". Updated by a separate 1 Hz Clock event that starts on disconnect, stops on reconnect.
**When to use:** Triggered by MachineState.connected transitioning False.

```python
# Disconnect elapsed timer — in RunScreen or as app-level widget
def _on_state_connected_changed(self, s: MachineState) -> None:
    if not s.connected:
        if self._disconnect_clock is None:
            self._disconnect_t0 = time.monotonic()
            self._disconnect_clock = Clock.schedule_interval(
                self._tick_disconnect_banner, 1.0
            )
    else:
        if self._disconnect_clock:
            self._disconnect_clock.cancel()
            self._disconnect_clock = None
        self.banner_text = ""  # clear banner on reconnect

def _tick_disconnect_banner(self, dt: float) -> None:
    elapsed = int(time.monotonic() - self._disconnect_t0)
    self.banner_text = f"DISCONNECTED ({elapsed}s)"
```

### Pattern 5: DMC Thread 2 Label

**What:** A new `#THRD2` label runs on Galil thread 2. It observes trigger variable values and hmiState to manage state transitions and knife counting.
**When to use:** Thread 2 is the correct DMC pattern for background monitoring that doesn't block the main program loop.

```dmc
' ============================================================
'  THREAD 2 - hmiState observer and knife counter
'  Start with XQ #THRD2,1 from #AUTO
' ============================================================
#THRD2
#T2LOOP
WT 50                     ' yield ~50ms between iterations

' --- Knife count: watch for grind completion ---
' hmiState transitions 2->1 signals grind done
IF (hmiState = 1) & (lastSt = 2)
  ctSesKni = ctSesKni + 1
  ctStnKni = ctStnKni + 1
ENDIF
lastSt = hmiState

JP #T2LOOP
EN
```

**Note:** `lastSt` must be declared in `#PARAMS`. The WT value is Claude's discretion — 50ms is a reasonable starting point (20 Hz on thread 2, ample for state observation).

**Alternative counting location:** Instead of Thread 2 tracking state transitions, the grind completion increment can be placed directly in `#GRIND` after `JS #GOREST`. This is simpler and avoids needing Thread 2 at all for knife counting. Thread 2 would then only be needed if a future requirement needs background state monitoring. The CONTEXT.md specifies Thread 2 for hmiState management — both counters can increment there.

### Anti-Patterns to Avoid

- **Per-screen polling:** RunScreen must not have its own Clock.schedule_interval for controller reads after Phase 10.
- **Queuing disconnect on the jobs FIFO:** The failure counter must be checked and acted on via Clock.schedule_once to the main thread, not from within the background worker.
- **Calling `GalilController.disconnect()` from the main thread:** Always submit to jobs so it runs off-thread.
- **Writing cycle_running as a stored field:** It is a derived property from dmc_state — never assign it directly.
- **BV in poll loop:** Confirmed out of scope — never call BV from within the poller.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Periodic background tick | Custom threading.Timer loop | `Clock.schedule_interval` + `jobs.submit` | Clock runs on Kivy main thread, ensuring safe Kivy property access; jobs serializes gclib |
| Pub-sub notifications | List of callbacks managed manually | `MachineState.subscribe()` / `notify()` | Already exists, already handles exceptions in listeners, already tested |
| Reconnect delay | `time.sleep()` in background thread | Poller keeps ticking at 10 Hz — GOpen attempt is just another `jobs.submit` | Sleep blocks the jobs worker; the poller's tick rate already provides the retry cadence |
| gclib thread safety | Lock/mutex around cmd() calls | Single FIFO jobs worker (already serializes all access) | Established project decision — do not introduce concurrent gclib access |

**Key insight:** The project already has the correct primitives. Phase 10 is wiring, not inventing.

---

## Common Pitfalls

### Pitfall 1: MachineState.notify() on background thread
**What goes wrong:** Calling `state.notify()` from inside `_do_read()` (background thread) fires listener callbacks on a non-Kivy thread. Kivy property mutations from non-main threads cause silent corruption or crashes.
**Why it happens:** It's easy to call `notify()` right after writing fields.
**How to avoid:** Always `Clock.schedule_once(lambda *_: self._apply(...))` from the background thread. The `_apply` method runs on the main thread and calls `notify()`.
**Warning signs:** Intermittent AttributeError or "must be called from main thread" Kivy assertions.

### Pitfall 2: cycle_running property breaks existing tests
**What goes wrong:** `test_machine_state_cycle.py::test_machine_state_has_cycle_running` checks `s.cycle_running == False`. A `@property` replaces the dataclass field — but `dataclasses.fields()` will no longer include `cycle_running`. If any code does `dataclasses.asdict(state)` or iterates fields, `cycle_running` will be missing.
**Why it happens:** `@property` and `@dataclass` fields are separate. A property replaces the stored field but is not tracked by `dataclasses.fields()`.
**How to avoid:** Keep `cycle_running` as a `@property`, remove the stored field from the dataclass. Verify all tests still pass. The existing test only checks `s.cycle_running == False` — the property returns `self.dmc_state == STATE_GRINDING` which is `0 == 2` = `False` on a fresh state. Test passes.
**Warning signs:** `TypeError: non-default argument 'cycle_running' follows default argument` at import time if both a default field and a property with the same name coexist.

### Pitfall 3: Consecutive failure counter races
**What goes wrong:** The `_fail_count` attribute is written from the background thread and read/written by the same background thread — this is safe since jobs FIFO is single-worker. But if `_on_disconnect()` is scheduled once via `Clock.schedule_once`, it could fire multiple times if multiple ticks fail before the first scheduled callback runs.
**Why it happens:** Clock.schedule_once calls are queued; the background thread keeps posting `_on_disconnect` every tick after threshold.
**How to avoid:** Guard with `if not s.connected: return` at the top of `_on_disconnect`. Once state is marked disconnected, further `_on_disconnect` calls are no-ops.

### Pitfall 4: GOpen after GClose without creating new handle
**What goes wrong:** `GalilController.disconnect()` calls `GClose()` but leaves `self._driver` pointing to the existing (now closed) gclib handle. Subsequent `GOpen()` on the same handle object may fail or behave unexpectedly.
**Why it happens:** gclib.py() handle objects may not support reopen after close on all firmware versions.
**How to avoid:** On reconnect, set `self._driver = None` in `disconnect()` so that `connect()` creates a fresh `gclib.py()` instance. Verify with the existing `connect()` flow — it already creates a new driver if `self._driver is None`.
**Confidence:** MEDIUM — behavior depends on firmware version, requires hardware validation.

### Pitfall 5: ctStnKni not declared before polling begins
**What goes wrong:** If Phase 10 is deployed and the DMC program does not yet include `ctStnKni` in `#PARAMS`, `MG ctStnKni` returns `?` and the poll fails every tick.
**Why it happens:** The DMC program modification (adding ctStnKni) is a prerequisite for the Python poller to work.
**How to avoid:** Plan the DMC program changes as Wave 1 (before the Python poller is enabled) within Phase 10. Poller should gracefully handle `?` responses by defaulting to 0 rather than raising.

### Pitfall 6: RunScreen._update_clock still running
**What goes wrong:** If `RunScreen._update_clock_event` is not cancelled when the new centralized poller starts, two separate polling loops contend for the single jobs FIFO, doubling gclib traffic at 10 Hz each.
**Why it happens:** The old poll event is started in `on_pre_enter` and cancelled in `on_leave`. If the centralized poller also starts at app launch, both run when RunScreen is active.
**How to avoid:** As part of the RunScreen migration, remove `_update_clock_event` setup from `on_pre_enter` entirely. The subscription callback takes its place.

---

## Code Examples

Verified patterns from project source:

### Issuing MG queries (confirmed from controller.py)
```python
# controller.py cmd() — already handles errors and logging
raw = self.controller.cmd("MG _TPA")
value = float(raw.strip())
```

### Subscribing to MachineState (confirmed from main.py)
```python
# From main.py line 120 — the subscribe + Clock.schedule_once pattern
self.state.subscribe(lambda s: Clock.schedule_once(lambda *_: status_bar.update_from_state(s)))
```

### Unsubscribing (confirmed from app_state.py)
```python
# subscribe() returns a callable cancel function
unsub = state.subscribe(my_listener)
# Later:
unsub()
```

### Submitting background work (confirmed from main.py)
```python
# Pattern for all off-thread controller calls
def do_work():
    result = self.controller.cmd("MG hmiState")
    Clock.schedule_once(lambda *_: apply_result(result))
jobs.submit(do_work)
```

### DMC batch variable read — multiple MG in one command
```dmc
' DMC: read multiple variables in one MG command (semicolon-separated)
MG hmiState, _TPA, _TPB, _TPC, _TPD, ctSesKni, ctStnKni
' Returns: space-separated floats on one line
```

**Note on batch MG:** The Galil MG command supports multiple variables separated by commas in a single command. The response is space-separated values. This reduces round-trips from 7 to 1 per tick. However, parsing multi-value MG responses has not been tested against this specific controller — confidence is MEDIUM. The safe fallback is 7 individual cmd() calls (each confirmed working). The planner should choose: implement as 7 individual calls (HIGH confidence), or single batch MG with fallback parsing (MEDIUM confidence, better performance).

### DMC Thread 2 start in #AUTO
```dmc
' In #AUTO, after JS #PARAMS, add:
XQ #THRD2, 1    ' start thread 2 label
```

---

## State of the Art

| Old Approach | Current Approach | Reason for Change | Impact |
|--------------|-----------------|-------------------|--------|
| RunScreen._do_poll per-screen | hmi/poll.py app-wide poller | Multiple screens would need duplicate poll code | Single truth for controller state |
| cycle_running stored bool (Phase 2 decision) | cycle_running @property derived from dmc_state | State authority is controller, not Python | Eliminates race where Python and controller disagree |
| No knife count in HMI | ctSesKni + ctStnKni both displayed | Phase 10 requirement | Operator sees productivity metrics |
| hmiState updated only inside subroutines | Thread 2 observes transitions | Continuous state accuracy between subroutine calls | Accurate state reporting at all times |

**Deprecated/outdated after Phase 10:**
- `RunScreen._update_clock_event`: replaced by MachineState subscription
- `RunScreen._do_poll()`: replaced by `ControllerPoller._do_read()`
- `RunScreen._apply_ui()`: replaced by `RunScreen._apply_state(s: MachineState)`
- `MachineState.cycle_running` as stored dataclass field: becomes a `@property`

---

## Open Questions

1. **Batch MG parsing reliability**
   - What we know: Galil MG supports comma-separated variable list; returns space-separated floats
   - What's unclear: Whether all 7 variables in one MG response parse cleanly on this firmware version; whether `?` for one variable aborts the whole response
   - Recommendation: Implement as 7 individual cmd() calls for Wave 1 (safe, confirmed working); refactor to batch MG in a follow-up if desired

2. **GOpen reuse vs. new handle after GClose**
   - What we know: `controller.connect()` already creates a new `gclib.py()` if `self._driver is None`; `disconnect()` sets `self._connected = False` but does NOT set `self._driver = None`
   - What's unclear: Whether calling `GOpen()` on an existing closed handle succeeds, or whether `self._driver = None` must be set in disconnect() to force a fresh handle
   - Recommendation: Set `self._driver = None` at the end of `disconnect()` to guarantee a clean reconnect path; hardware validation required

3. **Thread 2 WT delay value**
   - What we know: CONTEXT.md marks this as Claude's Discretion; WT 50 (50ms = 20Hz on thread 2) is a reasonable starting point
   - What's unclear: Whether 50ms is fast enough to catch all hmiState transitions, or causes excessive controller load
   - Recommendation: Start with WT 100 (10Hz — half the Python poll rate); the Python side already polls at 10Hz so a slightly slower thread 2 is acceptable

4. **ctStnKni increment location — Thread 2 vs. #GRIND inline**
   - What we know: CONTEXT.md specifies Thread 2 observes transitions; increment can also go inline at end of #GRIND
   - What's unclear: Thread 2 observing hmiState 2->1 transition is correct but requires the `lastSt` variable and adds DMC complexity
   - Recommendation: Put ctSesKni and ctStnKni increment inline at the end of #GRIND (after `JS #GOREST`) as the simplest reliable approach; Thread 2 then only needs to observe state for future requirements. This is within Claude's Discretion.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (from pyproject.toml `[tool.pytest.ini_options]`) |
| Config file | `pyproject.toml` — `testpaths = ["tests"]` |
| Quick run command | `pytest tests/test_app_state.py tests/test_dmc_vars.py tests/test_machine_state_cycle.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| POLL-01 | MachineState.dmc_state updated by poller | unit | `pytest tests/test_poll.py::test_poller_writes_dmc_state -x` | Wave 0 |
| POLL-01 | cycle_running property returns True when dmc_state==STATE_GRINDING | unit | `pytest tests/test_app_state.py::test_cycle_running_derived_from_dmc_state -x` | Wave 0 |
| POLL-02 | MachineState.pos updated by poller | unit | `pytest tests/test_poll.py::test_poller_writes_positions -x` | Wave 0 |
| POLL-03 | 3 consecutive failures mark state.connected=False | unit | `pytest tests/test_poll.py::test_disconnect_after_three_failures -x` | Wave 0 |
| POLL-03 | Poller reconnects when poll succeeds after disconnect | unit | `pytest tests/test_poll.py::test_reconnect_clears_disconnect -x` | Wave 0 |
| POLL-04 | MachineState.session_knife_count and stone_knife_count fields exist | unit | `pytest tests/test_app_state.py::test_knife_count_fields -x` | Wave 0 |
| POLL-04 | Poller writes knife counts from controller | unit | `pytest tests/test_poll.py::test_poller_writes_knife_counts -x` | Wave 0 |
| POLL-02 | dmc_vars.py has CT_SES_KNI and CT_STN_KNI constants | unit | `pytest tests/test_dmc_vars.py::TestKnifeCountConstants -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_app_state.py tests/test_dmc_vars.py tests/test_machine_state_cycle.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_poll.py` — covers POLL-01, POLL-02, POLL-03, POLL-04 poller behavior with mock controller
- [ ] `tests/test_app_state.py` needs new test methods: `test_cycle_running_derived_from_dmc_state`, `test_knife_count_fields`
- [ ] `tests/test_dmc_vars.py` needs new test class: `TestKnifeCountConstants` (CT_SES_KNI, CT_STN_KNI)

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `src/dmccodegui/app_state.py` — MachineState fields, subscribe/notify pattern
- Direct codebase inspection: `src/dmccodegui/utils/jobs.py` — JobThread.submit(), schedule(), single FIFO worker
- Direct codebase inspection: `src/dmccodegui/controller.py` — cmd(), connect(), disconnect(), is_connected()
- Direct codebase inspection: `src/dmccodegui/hmi/dmc_vars.py` — HMI_STATE_VAR, STATE_GRINDING, all trigger var names
- Direct codebase inspection: `src/dmccodegui/main.py` — existing commented-out poll, Clock patterns, jobs usage
- Direct codebase inspection: `src/dmccodegui/screens/run.py` — _do_poll, _apply_ui, subscribe pattern gap
- Direct codebase inspection: `4 Axis Stainless grind.dmc` — current DMC program, #PARAMS, #NEWSESS, ctSesKni location
- Direct codebase inspection: `tests/` — pytest infrastructure, existing test patterns

### Secondary (MEDIUM confidence)
- Kivy Clock.schedule_interval/schedule_once threading model: Kivy documentation (Clock runs on main thread)
- Galil MG multi-variable syntax: Galil documentation convention (comma-separated variable list)

### Tertiary (LOW confidence)
- GOpen reuse after GClose behavior: requires hardware validation against specific controller firmware

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components are existing project code inspected directly
- Architecture: HIGH — patterns derived from existing working code in same project
- Pitfalls: HIGH for threading model pitfalls (observable from code); MEDIUM for GOpen/GClose behavior (firmware-dependent)
- DMC Thread 2: MEDIUM — DMC syntax confirmed from existing program; WT value and exact transition logic require hardware validation

**Research date:** 2026-04-06
**Valid until:** Stable (no external dependencies changing); DMC firmware behavior flags require hardware validation before implementation
