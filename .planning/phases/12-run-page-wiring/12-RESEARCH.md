# Phase 12: Run Page Wiring - Research

**Researched:** 2026-04-06
**Domain:** Kivy screen wiring, HMI one-shot trigger pattern, startPtC readback, plot buffer lifecycle
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Button inventory (reduced from original scope)**
- Run page buttons: Start Grind, Stop, More Stone, Less Stone — that is it
- Go To Rest and Go To Start REMOVED — these are either inside the grind label or part of setup mode, not standalone Run page actions
- New Session (stone change) MOVED to Axes Setup page — belongs with setup workflow (Phase 13)
- Stop button already wired in Phase 11 (ST ABCD via submit_urgent)

**Start Grind**
- Sends `hmiGrnd=0` via one-shot pattern — no XQ command, just set the trigger variable
- DMC polling loop (#WtAtRt) detects the trigger, runs the grind cycle, ZS clears stack at end
- DMC resets hmiGrnd to 1 as first action inside the triggered block
- START/PAUSE toggle replaced with a simple Start Grind button — no pause concept
- Plot buffer clears on Start Grind press (fresh trace per cycle)
- Button does NOT optimistically disable — waits for poll tick to confirm hmiState=GRINDING
- All roles can press Start Grind (Operator, Setup, Admin)

**More Stone / Less Stone**
- Sends `hmiMore=0` or `hmiLess=0` via one-shot pattern
- DMC subroutine modifies startPtC: `startPtC = startPtC + (cpmC * 0.001)` for More, `startPtC = startPtC - (cpmC * 0.001)` for Less
- BV (burn variables) runs inside the DMC subroutine — each press persists to flash immediately
- Feedback: read startPtC BEFORE firing trigger, wait ~300-500ms fixed delay, read startPtC AFTER — display old and new value to operator
- Buttons disabled during active motion (GRINDING or HOMING)
- All roles can press More/Less Stone

**Live A/B plot**
- Plot feeds from poller data (10 Hz) during cycle_running (dmc_state == STATE_GRINDING)
- Plot redraws at 5 Hz on separate clock (existing pattern)
- Buffer clears when Start Grind is pressed
- No changes needed to plot infrastructure

### Claude's Discretion
- Start Grind button styling (replaces the START/PAUSE toggle)
- Exact delay value for More/Less Stone readback (300-500ms range)
- How to display the startPtC before/after feedback (toast, label update, log entry)
- Error handling if trigger fire fails (controller disconnected, etc.)

### Deferred Ideas (OUT OF SCOPE)
- New Session (stone change) on Axes Setup page — Phase 13
- Go To Rest / Go To Start — not standalone HMI actions
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RUN-01 | User can start a grind cycle by pressing Start Grind button (sends hmiGrnd=0) | HMI_GRND constant exists in dmc_vars.py; on_start_pause_toggle currently sends XQ #CYCLE — must be replaced with controller.cmd(f"{HMI_GRND}={HMI_TRIGGER_FIRE}") via jobs.submit |
| RUN-02 | User can send machine to rest position by pressing Go To Rest | REMOVED per CONTEXT.md — button exists in run.kv but is being eliminated from action bar; this requirement is satisfied by noting Go To Rest is deferred/relocated |
| RUN-03 | User can send machine to start position by pressing Go To Start | REMOVED per CONTEXT.md — no standalone button; deferred to Phase 13 or grind label |
| RUN-04 | User can stop an active grind cycle via Stop button (ST ABCD + HX) | Already wired in Phase 11: on_stop() sends ST ABCD via submit_urgent — no new work, only KV layout cleanup |
| RUN-05 | User can adjust grind stone compensation via More Stone / Less Stone buttons | HMI_MORE/HMI_LESS exist in dmc_vars.py; callbacks currently modify in-memory offsets — must be replaced with one-shot trigger + startPtC readback; STARTPT_C constant available |
| RUN-06 | User can start a new session with two-step confirmation (Setup/Admin role required) | MOVED to Phase 13 per CONTEXT.md — excluded from this phase's scope |
| RUN-07 | Live A/B position plot fills with real controller data during grind cycle | Already implemented: _apply_state feeds _plot_buf_x/_plot_buf_y when s.cycle_running and s.connected; _tick_plot redraws at 5 Hz; buffer must be cleared on new Start Grind |
</phase_requirements>

---

## Summary

Phase 12 is a targeted refactor and completion pass on `screens/run.py` and `ui/run.kv`. The core infrastructure — poller, MachineState, jobs worker, motion gate, plot buffer, and Stop button — is fully built and passing 18 tests. What remains is three surgical changes: (1) replace the XQ #CYCLE call in `on_start_pause_toggle` with a `hmiGrnd=0` one-shot trigger and convert the ToggleButton to a plain Button, (2) implement `on_more_stone` / `on_less_stone` callbacks using the `hmiMore=0` / `hmiLess=0` one-shot pattern with a startPtC before/after readback, (3) remove the `go_to_rest_btn` from the KV layout and add More Stone / Less Stone buttons in its place.

The live A/B plot (RUN-07) requires only the buffer-clear on Start Grind, which is already implemented in `on_start_pause_toggle("down")` — the refactor must preserve that clearing behaviour in the new `on_start_grind` callback. RUN-02, RUN-03, and RUN-06 are explicitly out of scope per CONTEXT.md decisions (removed, deferred to Phase 13).

The most complexity in this phase is the More/Less Stone readback sequence: read startPtC, fire trigger, sleep fixed delay, read startPtC again, post result to main thread — all inside a single jobs.submit closure. The delay must be long enough for the DMC subroutine (~200-300ms execution) plus controller round-trip overhead — 400ms is a safe default that the discretion area allows.

**Primary recommendation:** One plan, two tasks — Task 1: Python callback changes in run.py (Start Grind + More/Less Stone); Task 2: KV layout changes in run.kv (remove Go To Rest, ToggleButton to Button, add More/Less Stone buttons). Tests can be added to the same plan alongside the implementation tasks.

---

## Standard Stack

### Core (already in place — no new installs)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Kivy | existing | Button, BooleanProperty, Clock, Screen | Project-wide UI framework |
| kivy.clock.Clock | existing | schedule_once for main-thread UI callbacks from worker | Established pattern in all screens |
| dmccodegui.utils.jobs | existing | submit() for queued trigger commands | Single serialized gclib handle |
| dmccodegui.hmi.dmc_vars | existing | HMI_GRND, HMI_MORE, HMI_LESS, STARTPT_C, HMI_TRIGGER_FIRE | Single source of truth for var names |

### No new dependencies required
All libraries and patterns needed are already used in the project. No `pip install` step needed.

---

## Architecture Patterns

### Established: One-Shot Trigger Pattern
All HMI button presses use this exact sequence. Never XQ. Never raw string literals.

```python
# Source: dmc_vars.py + existing on_stop() pattern
from ..hmi.dmc_vars import HMI_GRND, HMI_TRIGGER_FIRE
from ..utils import jobs

def on_start_grind(self) -> None:
    if not self.controller or not self.controller.is_connected():
        return
    # Clear plot trail for fresh cycle view
    self._plot_buf_x.clear()
    self._plot_buf_y.clear()
    if self._plot_line is not None:
        self._plot_line.set_data([], [])
        if self._fig and self._fig.canvas:
            self._fig.canvas.draw_idle()

    def _fire():
        try:
            self.controller.cmd(f"{HMI_GRND}={HMI_TRIGGER_FIRE}")
        except Exception as e:
            Clock.schedule_once(lambda *_: self._alert(f"Start failed: {e}"))

    jobs.submit(_fire)
```

### Established: Read-Fire-Read (startPtC Readback)
Used for More Stone / Less Stone. Read before, fire trigger, wait fixed delay, read after — all in one worker closure. Post result to main thread via Clock.

```python
# Source: CONTEXT.md specifics + pattern from poll.py and existing callbacks
import time as _time
from ..hmi.dmc_vars import HMI_MORE, HMI_TRIGGER_FIRE, STARTPT_C

def on_more_stone(self) -> None:
    if not self.controller or not self.controller.is_connected():
        return

    ctrl = self.controller

    def _fire():
        try:
            before_raw = ctrl.cmd(f"MG {STARTPT_C}").strip()
            before = float(before_raw)
        except Exception:
            before = None
        try:
            ctrl.cmd(f"{HMI_MORE}={HMI_TRIGGER_FIRE}")
        except Exception as e:
            Clock.schedule_once(lambda *_: self._alert(f"More stone failed: {e}"))
            return
        _time.sleep(0.4)   # DMC #MOREGRI subroutine: ~200-300ms + round-trip headroom
        try:
            after_raw = ctrl.cmd(f"MG {STARTPT_C}").strip()
            after = float(after_raw)
        except Exception:
            after = None

        def _post(*_):
            if before is not None and after is not None:
                self._alert(
                    f"Stone +: startPtC {int(before):,} -> {int(after):,}"
                )
        Clock.schedule_once(_post)

    jobs.submit(_fire)
```

### Established: KV Button Binding
Replace ToggleButton with plain Button. Wire to `on_start_grind`. Disable when motion_active.

```kv
# Start Grind (replaces ToggleButton)
Button:
    id: start_grind_btn
    text: 'START GRIND'
    font_size: '16sp'
    bold: True
    size_hint_x: 1
    background_normal: ''
    background_color: 0.09, 0.40, 0.20, 1
    color: 0.733, 0.969, 0.827, 1
    disabled: root.motion_active
    on_release: root.on_start_grind()

# More Stone button
Button:
    id: more_stone_btn
    text: 'MORE STONE'
    font_size: '14sp'
    bold: True
    size_hint_x: 0.7
    background_normal: ''
    background_color: 0.118, 0.227, 0.373, 1
    color: 0.576, 0.773, 0.992, 1
    disabled: root.motion_active
    on_release: root.on_more_stone()

# Less Stone button
Button:
    id: less_stone_btn
    text: 'LESS STONE'
    font_size: '14sp'
    bold: True
    size_hint_x: 0.7
    background_normal: ''
    background_color: 0.118, 0.100, 0.200, 1
    color: 0.780, 0.650, 0.990, 1
    disabled: root.motion_active
    on_release: root.on_less_stone()
```

### Anti-Patterns to Avoid
- **XQ #CYCLE or XQ #MOREGRI direct calls:** Project-wide decision — breaks DMC state machine flow. Always use hmi variable one-shot.
- **Optimistic disable of Start Grind:** Decision from Phase 11 — button state waits for poll tick; no `self.motion_active = True` before the trigger fires.
- **Storing cycle_running on RunScreen as a writable field:** `MachineState.cycle_running` is a `@property` derived from `dmc_state`. `RunScreen.cycle_running` is a Kivy BooleanProperty bridged by `_apply_state`. Do not reset it manually in the new `on_start_grind`.
- **sleep() on main thread:** The readback sleep for More/Less Stone must happen inside the `jobs.submit(_fire)` closure — not on the main thread.
- **Raw DMC variable string literals in screen files:** Always import from `dmc_vars.py`. The `STARTPT_C` constant is already defined there.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Thread-safe UI update | Manual threading.Lock | `Clock.schedule_once(lambda *_: ...)` | Kivy main-thread safety established pattern across all existing callbacks |
| Serialized controller access | Second controller handle | `jobs.submit()` (single FIFO queue) | Single gclib handle decision — concurrent handle access prohibited |
| Motion gating | Per-button state tracking | `root.motion_active` BooleanProperty bound in KV | Already wired via `_apply_state`; binding covers all motion buttons automatically |
| startPtC variable name | Hardcoded string "startPtC" | `STARTPT_C` from `dmc_vars.py` | Single source of truth for 8-char DMC var names |

---

## Common Pitfalls

### Pitfall 1: ToggleButton state leak after refactor
**What goes wrong:** The existing KV references `start_pause_btn` by ID in `on_go_to_rest()` which resets its state. After removing the ToggleButton, any code that still references `self.ids.get("start_pause_btn")` will silently return `None` — no error, but the reset is a no-op.
**Why it happens:** Old Go To Rest handler tried to reset ToggleButton state on XQ call.
**How to avoid:** Remove `on_go_to_rest()` entirely from run.py along with the button from run.kv. The function only existed to reset the ToggleButton and call XQ #REST. Both are gone.
**Warning signs:** Test references to `start_pause_btn` id still existing after refactor.

### Pitfall 2: test_trail_clears_on_start fails after rename
**What goes wrong:** Existing test calls `r.on_start_pause_toggle("down")` directly. After renaming to `on_start_grind`, that test will break with AttributeError.
**Why it happens:** The test exercises the plot buffer clearing behaviour that must be preserved.
**How to avoid:** Either rename the test to call `on_start_grind()` or keep `on_start_pause_toggle` as a thin shim that calls `on_start_grind()`. The cleaner path is to update the test. The buffer-clear code block from `on_start_pause_toggle("down")` must move wholesale into `on_start_grind`.
**Warning signs:** `test_trail_clears_on_start` fails after refactor.

### Pitfall 3: STARTPT_C already defined but easy to miss
**What goes wrong:** Developer writes `ctrl.cmd("MG startPtC")` as a raw string literal instead of using the constant.
**Why it happens:** dmc_vars.py has `STARTPT_A/B/C/D` in the startPt section, not adjacent to HMI trigger vars.
**How to avoid:** Import `STARTPT_C` from `dmc_vars` at the top of run.py alongside the existing imports. Flag in code review any raw `"startPtC"` string.

### Pitfall 4: sleep delay too short — readback shows no change
**What goes wrong:** If `_time.sleep(0.4)` is reduced to 0.1s, the after-read races with the DMC subroutine still executing, and before==after, misleading the operator.
**Why it happens:** DMC #MOREGRI subroutine runs: SB 3, math, MG message, WT 200 (200ms), BV, EN — the WT 200 alone is 200ms. Add round-trip for the MG read.
**How to avoid:** Use 400ms as the default. Document the DMC subroutine timing in the callback docstring so future maintainers understand why the delay exists.

### Pitfall 5: Go To Rest button removal breaks KV id references
**What goes wrong:** run.kv still has `go_to_rest_btn` id. Removing the widget without removing `on_go_to_rest` in run.py leaves a dead handler. If a test checks for the absence of this button, it will catch regressions.
**Why it happens:** Incremental removal without coordinated code/KV/test cleanup.
**How to avoid:** Remove `on_go_to_rest()` from run.py, the button from run.kv, and verify no remaining test references `go_to_rest_btn`.

---

## Code Examples

### Verified: Existing motion_active wiring in _apply_state
```python
# Source: screens/run.py _apply_state() — already correct
self.motion_active = s.dmc_state in (STATE_GRINDING, STATE_HOMING)
```
More Stone and Less Stone buttons will be disabled automatically by KV binding `disabled: root.motion_active` — no additional guard needed in the callback beyond the `is_connected()` check.

### Verified: STARTPT_C constant location
```python
# Source: hmi/dmc_vars.py lines 93-103
STARTPT_C: str = "startPtC"  # Start/grind position for C axis
```
Import alongside existing dmc_vars imports: `from ..hmi.dmc_vars import STATE_GRINDING, STATE_HOMING, HMI_GRND, HMI_MORE, HMI_LESS, HMI_TRIGGER_FIRE, STARTPT_C`

### Verified: jobs.submit signature
```python
# Source: utils/jobs.py
def submit(fn: JobFn, *args: Any, **kwargs: Any) -> None:
    get_jobs().submit(fn, *args, **kwargs)
```
Pass a zero-argument inner function — the pattern used in all existing callbacks.

### Verified: _alert method for operator feedback
```python
# Source: screens/run.py _alert()
def _alert(self, message: str) -> None:
    # Pushes to app-wide banner ticker
```
Use `self._alert(f"Stone +: startPtC {int(before):,} -> {int(after):,}")` inside `Clock.schedule_once` for the readback display.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| XQ #CYCLE via controller.cmd | hmiGrnd=0 one-shot trigger | Phase 9 decision | Phase 12 must complete the migration — on_start_pause_toggle still uses XQ |
| ToggleButton (START/PAUSE) | Plain Button (START GRIND) | Phase 12 decision | Removes pause concept — simpler operator workflow |
| In-memory offset modification for More/Less | hmiMore/hmiLess trigger + startPtC readback | Phase 12 decision | Persistence handled by DMC BV in subroutine |
| Go To Rest as standalone action | Removed from Run page | Phase 12 decision | Part of grind label or setup mode, not a Run page button |

**Deprecated/outdated in current run.py:**
- `on_start_pause_toggle`: XQ #CYCLE call and optimistic `self.cycle_running = True` — both must be removed
- `on_go_to_rest`: XQ #REST call and ToggleButton reset — entire method to be removed
- `start_pause_btn` ToggleButton in run.kv — replaced with plain Button
- `go_to_rest_btn` in run.kv — removed entirely

---

## Existing Tests: What Passes, What Needs Updating

All 18 tests in `tests/test_run_screen.py` pass in the current state. After Phase 12 changes:

| Test | After Phase 12 | Action |
|------|---------------|--------|
| `test_trail_clears_on_start` | Breaks — calls `on_start_pause_toggle("down")` | Update to call `on_start_grind()` |
| `test_stop_sends_st_only` | Still passes — on_stop unchanged | No change |
| All motion gate tests | Still pass — _apply_state unchanged | No change |
| All plot buffer tests | Still pass — buffer logic unchanged | No change |

New tests needed for Phase 12:
- `test_start_grind_sends_hmi_trigger` — verifies `hmiGrnd=0` sent via jobs.submit (not XQ)
- `test_more_stone_sends_hmi_trigger` — verifies `hmiMore=0` sent via jobs.submit
- `test_less_stone_sends_hmi_trigger` — verifies `hmiLess=0` sent via jobs.submit
- `test_more_stone_reads_startptc_before_and_after` — verifies readback sequence
- `test_start_grind_clears_plot_buffers` — replaces `test_trail_clears_on_start` after rename

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (version from existing suite) |
| Config file | none — discovered by default |
| Quick run command | `python -m pytest tests/test_run_screen.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RUN-01 | on_start_grind sends hmiGrnd=0 via jobs.submit | unit | `python -m pytest tests/test_run_screen.py::test_start_grind_sends_hmi_trigger -x` | Wave 0 |
| RUN-01 | on_start_grind clears plot buffers | unit | `python -m pytest tests/test_run_screen.py::test_start_grind_clears_plot_buffers -x` | Wave 0 (rename existing) |
| RUN-04 | on_stop sends ST ABCD only via submit_urgent | unit | `python -m pytest tests/test_run_screen.py::test_stop_sends_st_only -x` | Exists |
| RUN-05 | on_more_stone sends hmiMore=0 via jobs.submit | unit | `python -m pytest tests/test_run_screen.py::test_more_stone_sends_hmi_trigger -x` | Wave 0 |
| RUN-05 | on_less_stone sends hmiLess=0 via jobs.submit | unit | `python -m pytest tests/test_run_screen.py::test_less_stone_sends_hmi_trigger -x` | Wave 0 |
| RUN-05 | readback reads startPtC before and after trigger | unit | `python -m pytest tests/test_run_screen.py::test_more_stone_reads_startptc_before_and_after -x` | Wave 0 |
| RUN-07 | plot buffer fills only during cycle_running + connected | unit | `python -m pytest tests/test_run_screen.py::test_plot_buffer_only_during_cycle -x` | Exists |
| RUN-02/03/06 | removed/deferred — no test needed | manual-only | N/A — out of scope per CONTEXT.md | N/A |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_run_screen.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_run_screen.py` — add 5 new test functions (start_grind trigger, more/less stone trigger x2, startPtC readback, rename trail_clears test)
- [ ] Update `test_trail_clears_on_start` to call `on_start_grind()` instead of `on_start_pause_toggle("down")`

---

## Open Questions

1. **startPtC readback: what to display when before/after read fails?**
   - What we know: controller.cmd() can raise if disconnected; the jobs worker swallows exceptions unless the callback handles them
   - What is unclear: should a failed before-read abort the trigger, or fire and skip feedback?
   - Recommendation: fire the trigger regardless; only show readback if both reads succeed; on failure, show a generic "Stone compensation applied" message via _alert

2. **KV layout for More/Less Stone: bottom bar or left column?**
   - What we know: bottom action bar currently has Start Grind (wide), Stop (0.6x), Go To Rest (0.7x). Go To Rest is being removed.
   - What is unclear: whether the freed space fits two buttons comfortably at 72dp bar height
   - Recommendation: place More Stone and Less Stone in the bottom action bar at size_hint_x: 0.6 each, replacing Go To Rest — bar already has spacing and works for 3 buttons

3. **RUN-02 and RUN-03 requirement status**
   - What we know: CONTEXT.md explicitly removes Go To Rest and Go To Start from the Run page; REQUIREMENTS.md marks these as Pending under Phase 12
   - What is unclear: whether the planner should mark RUN-02 and RUN-03 as "addressed by removal" or leave them Pending for a future phase
   - Recommendation: mark RUN-02 and RUN-03 as "addressed — removed from scope per Phase 12 context decision"; they will not be wired in any phase since they are part of the grind label/setup mode, not standalone HMI buttons

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `screens/run.py` (all action handlers, threading model, motion gate)
- Direct code inspection: `hmi/dmc_vars.py` (all HMI trigger constants, STARTPT_C)
- Direct code inspection: `utils/jobs.py` (submit, submit_urgent, scheduling model)
- Direct code inspection: `hmi/poll.py` (poller threading model, _apply pattern)
- Direct code inspection: `ui/run.kv` (current button layout, ToggleButton, go_to_rest_btn)
- Direct code inspection: `tests/test_run_screen.py` (18 passing tests, what exists vs what needs updating)
- Direct test execution: `python -m pytest tests/test_run_screen.py` — all 18 pass

### Secondary (MEDIUM confidence)
- CONTEXT.md: all locked decisions are authoritative (gathered 2026-04-06 from user discussion)

### Tertiary (LOW confidence)
- None — all findings are directly from code inspection and CONTEXT.md

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, inspected directly
- Architecture patterns: HIGH — inspected from working Phase 11 implementations
- Pitfalls: HIGH — found by reading old XQ-based code that Phase 12 replaces
- Test gaps: HIGH — 18 tests run and inspected directly, gaps identified by comparing to requirements

**Research date:** 2026-04-06
**Valid until:** Stable — this codebase is not a moving external dependency; valid until run.py or dmc_vars.py changes
