# Phase 11: E-STOP Safety - Research

**Researched:** 2026-04-06
**Domain:** Python threading (priority queue), Galil DMC command set, Kivy button gating
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Stop delivery path**
- Priority queue approach: add `submit_urgent()` to jobs.py that interrupts the in-flight job (not just queue-jump)
- After E-STOP sends ST, close+reopen the gclib handle (GClose then GOpen) to guarantee clean state
- Stay connected after E-STOP — do not disconnect. Handle is reopened and ready for recovery commands
- Single gclib handle maintained — no dual-handle approach (avoids hardware validation risk)

**E-STOP vs Stop/Pause (two buttons)**
- **E-STOP** (StatusBar, always visible): sends ST ABCD + HX — kills motor motion AND DMC program thread. Priority path via submit_urgent(), interrupts in-flight jobs
- **Stop** (Run page only): sends ST ABCD only — halts motor motion, DMC program thread stays alive but cycle is cancelled. Only visible/enabled during active motion (GRINDING or HOMING states)
- After either stop type, operator must restart the cycle — no partial-cycle resume
- E-STOP does NOT disconnect from controller (changed from current code behavior)

**Motion gate logic**
- Disable motion-triggering buttons (Start Grind, Go To Rest, Go To Start, More Stone, Less Stone) when hmiState is GRINDING (2) or HOMING (4)
- Also disable all motion buttons when controller is disconnected
- SETUP (3) handled separately by existing setup mode logic (not this phase)
- Disabled buttons use standard Kivy disabled property — no overlay text or reason labels
- Button state updates on next poll tick (~100ms at 10Hz) via MachineState subscription — no immediate-on-send optimistic disable

**Post-stop recovery**
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

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SAFE-01 | E-STOP sends ST ABCD immediately via priority path, not queued behind normal jobs | submit_urgent() design; interrupt-in-flight threading pattern |
| SAFE-02 | Stop/Pause sends ST ABCD + HX to halt both motor motion and DMC program thread | Galil ST/HX semantics; confirmed ST ABCD stops all axes, HX kills executing thread |
| SAFE-03 | All motion-triggering buttons are disabled when controller reports active motion (gate on hmiState) | MachineState.subscribe() pattern; Kivy disabled property; STATE_GRINDING (2) and STATE_HOMING (4) constants |
</phase_requirements>

---

## Summary

Phase 11 is a pure safety-hardening phase that touches four integration points: `jobs.py` (add priority path), `main.py` (rewrite `e_stop()`, add `recover()`), `status_bar` (add RECOVER button), and `run.py` + `run.kv` (add Stop button, wire motion gate). No new dependencies are required. The codebase already has all the building blocks — a FIFO `JobThread`, a `GalilController` with `cmd()`, and a `MachineState.subscribe()` pattern established in Phase 10.

The hardest design decision is `submit_urgent()`. The existing `JobThread` uses a standard `queue.Queue` which gives no way to interrupt a running job from outside. The chosen approach (a cancellation event plus a priority queue) requires careful threading: the worker must check the cancel event frequently, and the urgent slot must drain before normal jobs resume. This is achievable in pure Python without additional libraries.

`_XQ` is the correct Galil variable to read for "DMC program running" detection (returns -1 when no program is executing, 0+ when a thread is active). This drives RECOVER button enable/disable without adding a new polled field.

**Primary recommendation:** Implement `submit_urgent()` as a single-slot preemption flag plus a high-priority `Queue` checked before the normal queue, with a threading `Event` that the current job can poll via an injected cancellation token. The jobs worker checks the urgent slot after every normal-job completion and also at the head of each loop iteration.

---

## Standard Stack

### Core (no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `queue.Queue` (stdlib) | 3.10+ | Normal job FIFO | Already in jobs.py |
| `threading.Event` (stdlib) | 3.10+ | Cancel signal for in-flight jobs | Zero-cost synchronization primitive |
| `kivy.uix.modalview.ModalView` | 2.2+ | RECOVER confirmation dialog | Already used in main.py for machine picker |
| `kivy.properties.BooleanProperty` | 2.2+ | Button disabled gating in KV | Already used in RunScreen |

### No New Packages Required

This phase requires no `pip install` changes. All needed tools are in stdlib (`threading`, `queue`) and already-imported Kivy.

---

## Architecture Patterns

### Pattern 1: submit_urgent() — Priority Preemption

**What:** A second `Queue` (capacity 1) that the worker drains before pulling from the normal queue. A `threading.Event` is passed to in-flight normal jobs (via a wrapper) so they can cooperate by checking it and aborting early.

**When to use:** E-STOP button press; any path that must bypass queued work.

**Design constraints from CONTEXT.md:**
- Single gclib handle — no concurrent access
- interrupt-in-flight, not just queue-jump

**Concrete mechanism (Claude's discretion area):**

```python
# Source: pure Python stdlib threading patterns
import threading
from queue import Queue, Empty

class JobThread:
    def __init__(self) -> None:
        self._queue: Queue = Queue()
        self._urgent_queue: Queue = Queue(maxsize=1)   # at most one urgent job pending
        self._cancel_event = threading.Event()          # signals current normal job to abort
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._stop_event = threading.Event()
        self._thread.start()

    def submit_urgent(self, fn, *args, **kwargs) -> None:
        """Preempt current normal job and run fn next, ahead of queue."""
        # Signal in-flight normal job to stop (cooperative cancel)
        self._cancel_event.set()
        # Drop any stale urgent job (replace with new one)
        try:
            self._urgent_queue.get_nowait()
        except Empty:
            pass
        self._urgent_queue.put((fn, args, kwargs))

    def _run(self) -> None:
        while not self._stop_event.is_set():
            # Drain urgent queue first
            try:
                fn, args, kwargs = self._urgent_queue.get_nowait()
                self._cancel_event.clear()   # reset for next normal job
                try:
                    fn(*args, **kwargs)
                except Exception:
                    pass
                continue
            except Empty:
                pass

            # Normal queue
            try:
                fn, args, kwargs = self._queue.get(timeout=0.05)
            except Empty:
                continue
            self._cancel_event.clear()
            try:
                fn(*args, **kwargs)
            except Exception:
                pass
```

**Key property:** After `submit_urgent()` sets `_cancel_event`, the next time the worker finishes its current job (or the job yields), it checks `_urgent_queue` first. The urgent job runs before any queued normal job.

**Note on "interrupt in-flight":** True preemption of a blocking gclib call is not possible from Python. The pattern above is cooperative: the `_cancel_event` is available for well-behaved normal jobs to poll (e.g., `upload_array`'s loop), but an in-progress `GCommand` call will complete first. For E-STOP this is acceptable — the gclib call takes <1ms; the 200ms budget is for the ST ABCD command to reach the controller, not for the Python thread to switch.

### Pattern 2: E-STOP handler in main.py

**What:** Rewrite `e_stop()` to use `submit_urgent()` with `ST ABCD` then `HX`, followed by GClose+GOpen handle reset.

```python
# Source: Galil command reference; existing controller.cmd() pattern
def e_stop(self) -> None:
    def do_estop():
        try:
            if self.controller.is_connected():
                self.controller.cmd("ST ABCD")   # stop all axes immediately
                self.controller.cmd("HX")         # kill DMC program thread
                # GClose + GOpen: flush any partial response, reset handle state
                self.controller._driver.GClose()
                self.controller._driver.GOpen(self.state.connected_address)
                self.controller._connected = True
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("e_stop error: %s", e)
        # Stay connected — no disconnect() call
        def on_ui():
            # Banner only; no navigation change
            try:
                app = self
                app._log_message("E-STOP — motion halted")
            except Exception:
                pass
        Clock.schedule_once(lambda *_: on_ui())
    jobs.submit_urgent(do_estop)
```

**Note on GClose/GOpen:** `controller.py` exposes `self._driver.GClose()` and `self._driver.GOpen(addr)` directly. The `_driver` attribute is the gclib handle. After GClose+GOpen, `self._connected` must be explicitly set to `True` because `connect()` is not being called (which would also create a new handle). Alternatively, a new `reset_handle()` method on `GalilController` could wrap this cleanly.

### Pattern 3: Stop button on Run page

**What:** A separate button (visible only during GRINDING or HOMING state) that sends `ST ABCD` only. Does not kill the DMC program thread.

**Decision point (Claude's discretion):** Whether Stop uses `submit_urgent()` or `jobs.submit()`. Since Stop is only tappable while the machine is active, queued normal jobs during grinding are likely minimal (poll jobs). Using `submit_urgent()` is safer and consistent — it guarantees the stop command reaches the controller before any pending jobs execute.

**Recommendation:** Use `submit_urgent()` for the Run page Stop button as well, for consistency and safety margin.

```python
# In RunScreen
def on_stop(self) -> None:
    """Send ST ABCD via priority path (halts axes, DMC thread stays alive)."""
    if not self.controller or not self.controller.is_connected():
        return
    def do_stop():
        try:
            self.controller.cmd("ST ABCD")
        except Exception as e:
            Clock.schedule_once(lambda *_: self._alert(f"Stop failed: {e}"))
    from ..utils.jobs import submit_urgent
    submit_urgent(do_stop)
```

### Pattern 4: RECOVER button in StatusBar

**What:** Always-visible button next to E-STOP. Disabled when `program_running` is True; enabled when False.

**Detecting "DMC program not running":**
- Galil `_XQ` system variable: `-1` when no program is running, `0+` when a thread is executing
- Read via `MG _XQ` in the 10Hz poll loop, or as a one-off check on button press
- **Recommended approach:** Add `program_running: bool` to `MachineState`, derived from `_XQ` value in `ControllerPoller._do_read()` — consistent with Phase 10's pattern of deriving all state from poll

```python
# In ControllerPoller._do_read() — add one more MG read:
xq_raw = int(float(ctrl.cmd("MG _XQ").strip()))
program_running = (xq_raw >= 0)  # -1 = no program; 0+ = program running on thread N

# In MachineState:
program_running: bool = False  # True when _XQ >= 0 (DMC program executing)
```

**Alternative (simpler, no extra poll):** RECOVER button is enabled whenever `dmc_state == STATE_IDLE` AND `not program_running`. Since `STATE_IDLE (1)` is set by the DMC program itself when it reaches the waiting loop, if `hmiState == 1` then by definition a program is running. After HX, `hmiState` stays at whatever it was last set to (the DMC program no longer updates it). So `hmiState` alone cannot distinguish "IDLE with program" from "IDLE without program" — `_XQ` read is required for correct RECOVER gating.

**RECOVER sequence:**
```python
def recover(self) -> None:
    """Show confirmation dialog, then send XQ #AUTO on confirm."""
    from kivy.uix.modalview import ModalView
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.label import Label

    modal = ModalView(auto_dismiss=True, size_hint=(0.45, 0.35))
    layout = BoxLayout(orientation='vertical', padding='20dp', spacing='16dp')
    layout.add_widget(Label(text='Restart machine program?', font_size='22sp'))

    def _confirm(*_):
        modal.dismiss()
        def do_recover():
            try:
                self.controller.cmd("XQ #AUTO")
            except Exception as e:
                Clock.schedule_once(
                    lambda *_: self._log_message(f"Recovery failed: {e}")
                )
        jobs.submit(do_recover)   # Normal submit — recovery is not urgent

    btn_row = BoxLayout(size_hint_y=None, height='56dp', spacing='12dp')
    btn_confirm = Button(text='RESTART', background_color=(0.1, 0.4, 0.2, 1))
    btn_cancel = Button(text='CANCEL', background_color=(0.2, 0.2, 0.2, 1))
    btn_confirm.bind(on_release=_confirm)
    btn_cancel.bind(on_release=lambda *_: modal.dismiss())
    btn_row.add_widget(btn_confirm)
    btn_row.add_widget(btn_cancel)
    layout.add_widget(btn_row)
    modal.add_widget(layout)
    modal.open()
```

**Note on XQ #AUTO:** This is a direct XQ call, which is normally prohibited (MEMORY.md: no XQ commands). However, RECOVER is explicitly an exception — it is the startup sequence re-entry path, not a subroutine trigger that breaks DMC state machine flow. XQ #AUTO restarts the entire program from the top, not a mid-program subroutine jump. This is the single authorized XQ call in the codebase.

### Pattern 5: Motion gate on RunScreen buttons

**What:** Subscribe to MachineState in RunScreen (already done in Phase 10). In `_apply_state()`, set `disabled` on motion buttons based on `dmc_state`.

**States that disable motion buttons:** `STATE_GRINDING (2)` or `STATE_HOMING (4)`, or `not connected`.

```python
# In RunScreen._apply_state()
in_motion = s.dmc_state in (STATE_GRINDING, STATE_HOMING) or not s.connected
for btn_id in ("start_grind_btn", "go_to_rest_btn", "go_to_start_btn",
               "more_stone_btn", "less_stone_btn"):
    btn = self.ids.get(btn_id)
    if btn is not None:
        btn.disabled = in_motion
```

**KV: Stop button visibility** (only during active motion):
```kivy
# In run.kv bottom action bar
Button:
    id: stop_btn
    text: 'STOP'
    opacity: 1.0 if root.cycle_running else 0.0
    disabled: not root.cycle_running
    on_release: root.on_stop()
    background_color: 0.88, 0.06, 0.06, 1
    color: 1, 1, 1, 1
    bold: True
```

**Note:** `cycle_running` in `RunScreen` is a `BooleanProperty` mirroring `dmc_state == STATE_GRINDING`. The Stop button should also be visible during HOMING. Consider using a separate `BooleanProperty motion_active` that maps to `dmc_state in (STATE_GRINDING, STATE_HOMING)` rather than reusing `cycle_running`.

### Recommended Project Structure Changes

```
src/dmccodegui/
├── utils/
│   └── jobs.py            # ADD: submit_urgent(), _urgent_queue, _cancel_event
├── controller.py          # ADD: reset_handle() method (GClose+GOpen)
├── app_state.py           # ADD: program_running bool field
├── main.py                # REWRITE: e_stop(); ADD: recover()
├── hmi/
│   └── poll.py            # ADD: MG _XQ read → program_running
├── screens/
│   ├── status_bar.py      # ADD: RECOVER button enable/disable logic
│   └── run.py             # ADD: on_stop(); update _apply_state() for motion gate
└── ui/
    ├── status_bar.kv      # ADD: RECOVER button next to E-STOP
    └── run.kv             # ADD: STOP button; motion gate disabled binding
```

### Anti-Patterns to Avoid

- **Optimistic disable on button press:** Context says no. Wait for next poll tick. Premature state mutation breaks the "controller is authoritative" invariant.
- **jobs.submit() for E-STOP:** Using the normal queue means E-STOP waits behind any in-flight `upload_array` or `download_array` call — violates SAFE-01.
- **Disconnecting on E-STOP:** The old `e_stop()` calls `self.controller.disconnect()`. The new version must NOT — stay connected per locked decision.
- **XQ calls for anything other than #AUTO in recover():** All other machine triggers must use HMI variable one-shot pattern (MEMORY.md, REQUIREMENTS.md out-of-scope table).
- **Reading _XQ in UI thread:** Must be submitted to jobs worker, like all gclib calls.
- **Setting `program_running` from the UI thread directly:** All controller state comes from the poll loop → MachineState → subscribe callbacks.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Thread-safe priority delivery | Custom pipe/socket | `queue.Queue(maxsize=1)` + `threading.Event` | stdlib, zero deps, correct semantics |
| Confirmation dialog | Custom popup widget class | `kivy.uix.modalview.ModalView` inline | Already used in main.py, no new class needed |
| Button disabled gating | Opacity tricks, overlay labels | Kivy `disabled` property | Kivy natively grays out and blocks touch |
| "Program running" detection | Polling hmiState alone | `MG _XQ` (-1 = none, >=0 = running) | hmiState is ambiguous post-HX; _XQ is authoritative |

---

## Common Pitfalls

### Pitfall 1: GClose+GOpen Leaves _connected in Wrong State

**What goes wrong:** After GClose+GOpen, `controller._connected` is still True (it never got set to False), but if GOpen fails for any reason, subsequent `cmd()` calls may raise confusing errors.

**Why it happens:** The existing `connect()` method manages `_connected`. A raw GClose+GOpen bypass skips that bookkeeping.

**How to avoid:** Add a `reset_handle(address: str) -> bool` method to `GalilController` that wraps GClose+GOpen and updates `_connected` correctly on success/failure.

**Warning signs:** `cmd()` calls succeed but return garbled data after E-STOP.

### Pitfall 2: _XQ Returns Float String, Not Int

**What goes wrong:** `ctrl.cmd("MG _XQ")` returns `" -1.0000\r\n"`. Directly comparing to `-1` as string or int without parsing fails.

**Why it happens:** Galil MG always returns float-formatted strings.

**How to avoid:** `int(float(ctrl.cmd("MG _XQ").strip()))` — same pattern as `dmc_state` parsing in `poll.py`.

### Pitfall 3: submit_urgent() Called from UI Thread Race

**What goes wrong:** `_cancel_event.set()` and `_urgent_queue.put()` happen from the UI thread while the worker thread is mid-job. If the worker reads `_urgent_queue` between the set and put, it sees no urgent job and continues the normal queue.

**Why it happens:** Two separate operations that should be atomic.

**How to avoid:** The sequence `_cancel_event.set()` then `_urgent_queue.put()` is safe because the worker checks urgent queue on _every loop iteration_, not only when `_cancel_event` is set. The cancel event signals the in-flight job to yield; the urgent queue ensures the urgent job runs at the top of the next iteration regardless of ordering.

### Pitfall 4: Poll Adding _XQ Raises Disconnect Threshold Unexpectedly

**What goes wrong:** Adding `MG _XQ` as an 8th polled command means one more failure point per tick. If the controller is slow to respond on `_XQ`, fail_count reaches `DISCONNECT_THRESHOLD` faster.

**Why it happens:** `DISCONNECT_THRESHOLD = 3` consecutive full-read failures.

**How to avoid:** The `_XQ` read should be wrapped in its own `try/except` within `_do_read()`. If it fails alone, treat `program_running` as `True` (conservative — don't enable RECOVER if uncertain). Only increment `_fail_count` on the critical 7-variable block that was there before.

### Pitfall 5: Stop Button Visible When Disconnected

**What goes wrong:** `cycle_running` Kivy property is True from the last poll before disconnect. The Stop button remains visible but is useless (controller disconnected).

**Why it happens:** `_apply_state()` only clears `cycle_running` when `s.connected` is True. If disconnected, the old True value remains.

**How to avoid:** In `_apply_state()`, when `not s.connected`, also set `self.cycle_running = False` (and `motion_active = False`).

---

## Code Examples

### Current e_stop() — what will be replaced

```python
# Source: src/dmccodegui/main.py:432 (current, incorrect behavior)
def e_stop(self) -> None:
    def do_estop():
        try:
            if self.controller.is_connected():
                self.controller.cmd('AB')  # wrong command
        finally:
            self.controller.disconnect()   # wrong — must not disconnect
        def on_ui():
            self.state.set_connected(False)
            try:
                self.root.ids.sm.current = 'setup'
            except Exception:
                pass
        Clock.schedule_once(lambda *_: on_ui())
    jobs.submit(do_estop)  # wrong — uses normal queue
```

### Galil Command Reference (verified against Galil Command Reference manual)

| Command | Effect | Use Case |
|---------|--------|----------|
| `ST ABCD` | Stop motion on axes A, B, C, D — decelerates to stop | E-STOP and Stop button |
| `HX` | Halt program execution on all threads | E-STOP only |
| `XQ #AUTO` | Execute program starting at label #AUTO | RECOVER only |
| `MG _XQ` | Read execution status: -1=no program, 0=thread 0 running, etc. | RECOVER button gate |

**Confidence:** HIGH — ST, HX, XQ, MG _XQ are standard Galil commands present in all DMC firmware.

### MachineState.program_running addition

```python
# Source: app_state.py pattern — new field to add
program_running: bool = False  # True when _XQ >= 0 (DMC thread active)
# Note: NOT a @property — polled from controller, not derived from dmc_state
```

### KV RECOVER button pattern

```kivy
# Source: status_bar.kv existing E-STOP button pattern — RECOVER goes next to it
Button:
    id: recover_btn
    text: 'RECOVER'
    size_hint_x: None
    width: '110dp'
    size_hint_y: None
    height: '56dp'
    pos_hint: {'center_y': 0.5}
    background_normal: ''
    background_down: ''
    background_color: (0.15, 0.50, 0.20, 1) if not self.disabled else (0.1, 0.15, 0.1, 1)
    color: 1, 1, 1, 1
    font_size: '18sp'
    bold: True
    disabled: not root.recover_enabled
    on_release: app.recover()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `e_stop()` sends `AB` via `jobs.submit()` then disconnects | `e_stop()` sends `ST ABCD + HX` via `submit_urgent()`, stays connected | Phase 11 | Correct command, correct queue path, correct post-stop state |
| No motion gating | Buttons disabled when dmc_state == GRINDING or HOMING | Phase 11 | Prevents double-trigger, operator feedback |
| No recovery path | RECOVER button with XQ #AUTO | Phase 11 | Operator can restart without navigating to setup |

**Deprecated behavior:**
- `AB` command in e_stop: AB is "abort motion" without deceleration on some Galil models. `ST ABCD` is the correct deceleration stop. Using `AB` is a legacy artifact.
- `controller.disconnect()` in e_stop: Was there to "ensure clean state." Handle reset (GClose+GOpen) achieves clean state without losing the connection.

---

## Open Questions

1. **XQ #AUTO label availability**
   - What we know: CONTEXT.md states recovery sends `XQ #AUTO` to restart from `#AUTO` label
   - What's unclear: The DMC program must have a label `#AUTO` at the top of the program flow. This needs hardware verification that the label exists and the restart sequence is correct.
   - Recommendation: Add a comment in the recover() implementation noting this dependency, and flag for hardware validation.

2. **GClose+GOpen handle reset — connection address**
   - What we know: `GOpen` requires the address string (e.g., "192.168.0.2")
   - What's unclear: `state.connected_address` may be empty if connected via auto-detect
   - Recommendation: Store the address used at connect time in `controller._address` attribute so reset_handle() can use it without depending on MachineState.

3. **_XQ vs hmiState for RECOVER gate**
   - What we know: After HX, the DMC program stops updating hmiState. _XQ returns -1.
   - What's unclear: After E-STOP (ST ABCD + HX), does the controller's _XQ return -1 immediately or after a short delay?
   - Recommendation: Add a small guard in the RECOVER button — it is disabled for 500ms after E-STOP fires (implemented via a Clock.schedule_once that re-enables polling of _XQ), ensuring the flag has propagated before RECOVER is active.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (installed in dev extras) |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options] testpaths = ["tests"]` |
| Quick run command | `pytest tests/test_jobs.py tests/test_app_state.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SAFE-01 | `submit_urgent()` runs before queued normal jobs | unit | `pytest tests/test_jobs.py::test_submit_urgent_runs_before_normal -x` | Wave 0 |
| SAFE-01 | `submit_urgent()` sets cancel_event before queuing urgent job | unit | `pytest tests/test_jobs.py::test_submit_urgent_sets_cancel_event -x` | Wave 0 |
| SAFE-01 | `e_stop()` calls `submit_urgent` not `submit` | unit | `pytest tests/test_main_estop.py::test_estop_uses_submit_urgent -x` | Wave 0 |
| SAFE-01 | `e_stop()` sends `ST ABCD` then `HX` | unit | `pytest tests/test_main_estop.py::test_estop_commands -x` | Wave 0 |
| SAFE-01 | `e_stop()` does NOT call `controller.disconnect()` | unit | `pytest tests/test_main_estop.py::test_estop_stays_connected -x` | Wave 0 |
| SAFE-02 | Run page Stop button sends only `ST ABCD` (no HX) | unit | `pytest tests/test_run_screen.py::test_stop_sends_st_only -x` | ❌ new test in existing file |
| SAFE-03 | Motion buttons disabled when dmc_state == GRINDING | unit | `pytest tests/test_run_screen.py::test_motion_gate_grinding -x` | ❌ new test in existing file |
| SAFE-03 | Motion buttons disabled when dmc_state == HOMING | unit | `pytest tests/test_run_screen.py::test_motion_gate_homing -x` | ❌ new test in existing file |
| SAFE-03 | Motion buttons disabled when disconnected | unit | `pytest tests/test_run_screen.py::test_motion_gate_disconnected -x` | ❌ new test in existing file |
| SAFE-03 | Motion buttons enabled when dmc_state == IDLE and connected | unit | `pytest tests/test_run_screen.py::test_motion_gate_idle -x` | ❌ new test in existing file |

### Sampling Rate
- **Per task commit:** `pytest tests/test_jobs.py tests/test_app_state.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_jobs.py` — covers SAFE-01 submit_urgent behavior (new file)
- [ ] `tests/test_main_estop.py` — covers SAFE-01 e_stop() behavior (new file)
- [ ] `tests/test_run_screen.py` — add SAFE-02 and SAFE-03 tests to existing file

*(Existing `test_app_state.py` and `test_poll.py` cover Phase 10 and need no changes for Phase 11.)*

---

## Sources

### Primary (HIGH confidence)
- `src/dmccodegui/utils/jobs.py` — complete JobThread implementation; confirmed FIFO Queue, no priority mechanism exists
- `src/dmccodegui/controller.py` — GalilController, cmd(), connect(), disconnect(); confirmed `_driver.GClose()` and `_driver.GOpen()` are directly accessible
- `src/dmccodegui/app_state.py` — MachineState fields, subscribe() pattern, dmc_state field
- `src/dmccodegui/hmi/poll.py` — ControllerPoller threading model; 7 separate MG commands per tick
- `src/dmccodegui/main.py:432` — existing e_stop() implementation confirmed; uses AB command, disconnects, uses jobs.submit()
- `src/dmccodegui/screens/status_bar.py` + `ui/status_bar.kv` — E-STOP button exists; no RECOVER button
- `src/dmccodegui/screens/run.py` + `ui/run.kv` — RunScreen action bar; no Stop button; no motion gating
- `src/dmccodegui/hmi/dmc_vars.py` — STATE_GRINDING=2, STATE_HOMING=4 confirmed
- `.planning/phases/11-e-stop-safety/11-CONTEXT.md` — all locked decisions, discretion areas
- Galil Command Reference (general knowledge, HIGH confidence for ST/HX/XQ/_XQ — these are standard across all Galil DMC firmware)

### Secondary (MEDIUM confidence)
- `_XQ == -1` when no program running: standard Galil _XQ behavior; needs hardware confirmation that this holds after HX on this specific controller

### Tertiary (LOW confidence)
- 200ms E-STOP budget achievable with submit_urgent() cooperative approach: the actual timing depends on what job is in-flight when E-STOP fires. If `upload_array` is mid-loop (can run for seconds), the cooperative cancel only signals — the gclib call itself must complete first. Hardware validation required for the 200ms claim.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all tools confirmed in existing code
- Architecture (submit_urgent): HIGH — pure stdlib threading, well-understood pattern
- Architecture (GClose+GOpen): MEDIUM — pattern is correct but behavior after reset needs hardware validation
- Architecture (_XQ for program_running): MEDIUM — standard Galil variable, hardware validation for timing
- Pitfalls: HIGH — derived from reading actual code, not hypothesis
- 200ms budget claim: LOW — hardware timing not verifiable from code alone

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable domain — stdlib threading + Galil commands do not change)
