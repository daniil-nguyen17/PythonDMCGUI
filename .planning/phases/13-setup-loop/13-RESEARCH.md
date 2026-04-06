# Phase 13: Setup Loop - Research

**Researched:** 2026-04-06
**Domain:** DMC one-shot trigger wiring, Kivy screen lifecycle, Python-side jog and teach logic
**Confidence:** HIGH

## Summary

Phase 13 is an integration and wiring phase, not an exploratory one. The decisions are fully locked in CONTEXT.md and all the core mechanisms already exist. The primary work is:

1. **DMC program**: add three new variables (`hmiGoRs`, `hmiGoSt`, `hmiExSt`) in `#PARAMS` and wire `IF` conditions for them in `#SULOOP`.
2. **`dmc_vars.py`**: add three new constants for the new triggers, add a `HMI_NEW_SESSION` (already `HMI_NEWS`) alias check.
3. **`screens/axes_setup.py`**: replace dead `swGoRest`/`swGoStart`/`swHomeAll` software-variable commands with proper HMI trigger fires; add New Session button + confirmation dialog; add setup-mode gate (fire `hmiSetp=0` only if not already in STATE_SETUP); add in-progress motion gate on jog buttons.
4. **`screens/parameters.py`**: fire `hmiCalc=0` after writing params, wait ~500 ms, read back all params to confirm; smart enter/exit (skip re-enter if already SETUP, skip exit if navigating to sibling setup screen).

The test suite style is established: mock controller, patch `jobs.submit`, call the background function synchronously, assert `ctrl.cmd` call sequence. All 239 existing tests pass. New tests follow the same pattern.

**Primary recommendation:** Wire the three new DMC triggers first (DMC + `dmc_vars.py`), then update Python screen logic, then write tests covering each discrete behavior change.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Jog approach**
- Python keeps its own PR/BG step jog — does NOT use hmiJog trigger or DMC #WheelJg
- DMC #WheelJg remains exclusively for the physical handwheel
- Jog buttons gated on hmiState=3 (SETUP) — disabled unless controller is in setup mode
- Jog buttons disabled during active motion (while previous jog in progress, _BG{axis} != 0) — prevents queuing multiple moves
- Step sizes remain 1mm, 5mm, 10mm as currently implemented

**Teach points (rest/start)**
- Keep Python direct write approach: read _TD{axis}, write restPt/startPt vars, send BV, read back to confirm
- DMC #SETREST/#SETSTR stay exclusively for hardware button saves inside #JogLoop
- No new HMI trigger variables needed for teach

**Quick actions wiring**
- Go To Rest and Go To Start: add new HMI trigger variables to DMC (hmiGoRs, hmiGoSt — within 8-char limit)
- Add OR conditions in DMC #SULOOP: `IF (hmiGoRs=0)` → `JS #GOREST`, `IF (hmiGoSt=0)` → `JS #GOSTR`
- Home All: already has hmiHome=0 in #SULOOP — just wire Python to fire it instead of swHomeAll
- Replace swGoRest/swGoStart/swHomeAll software variables with proper HMI triggers in Python
- All three quick actions available only on Axes Setup screen in Setup mode (not on Run page)

**Parameters → varcalc integration**
- "Apply to Controller" auto-fires hmiCalc=0 after writing all params — one button does write + recalc + readback
- After firing hmiCalc=0, wait ~500ms for DMC #VARCALC to complete, then read all param values back from controller
- No separate "Recalculate" button needed — Apply handles the full workflow

**New Session (stone change)**
- Button lives on Axes Setup screen only — fits setup workflow
- Setup/Admin role required (Operator cannot trigger)
- Single confirmation dialog: "Start new session? This will home all axes and reset knife counts." → Confirm/Cancel
- Fires hmiNewS=0 on confirm — DMC #NEWSESS handles homing, count reset, BV
- Knife count display updates via normal 10 Hz poll tick (no optimistic zero) — consistent with controller-is-truth pattern

**Setup enter/exit**
- Entry: fire hmiSetp=0 in on_pre_enter (existing behavior — both AxesSetup and Parameters screens)
- Exit: add new DMC variable hmiExSt (exit setup) with OR condition in #SULOOP alongside @IN[32]
- Python fires hmiExSt=0 in on_leave — but ONLY when navigating to a non-setup screen (Run, Profiles, Users)
- Navigating between Axes Setup ↔ Parameters stays in setup mode — no exit/re-enter cycle
- Similarly, on_pre_enter should NOT fire hmiSetp=0 if already in setup mode (hmiState=3)
- DMC exits #SULOOP on hmiExSt=0, returns to #MAIN, sets hmiState=1 (IDLE)

### Claude's Discretion
- New Session button placement and styling on Axes Setup screen
- Confirmation dialog visual design
- Exact wait time for varcalc completion (within ~500ms range)
- How to detect "already in setup mode" for tab-switch optimization
- Error handling if any trigger fire fails (controller disconnected, etc.)
- Whether to add hmiGoRs/hmiGoSt to #WtAtRt as well or only #SULOOP

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SETP-01 | User can enter Setup mode on the controller from the HMI (sends hmiSetp=0) | `axes_setup.py` `_enter_setup_and_read()` already fires `hmiSetp=0`; extend with state guard (skip if dmc_state==STATE_SETUP) |
| SETP-02 | User can trigger homing sequence from Axes Setup page (sends hmiHome=0, Setup/Admin role required) | `home_all()` method exists but fires dead `swHomeAll=1`; replace with `hmiHome=0` fire via `HMI_HOME` constant |
| SETP-03 | User can jog axes from Axes Setup page with movement on real controller | `jog_axis()` PR/BG logic already implemented; add `dmc_state==STATE_SETUP` gate and in-progress `_BG{axis}!=0` block |
| SETP-04 | User can teach Rest point — saves current axis positions to restPt[] array on controller | `teach_rest_point()` fully implemented; needs test update for new trigger guards only |
| SETP-05 | User can teach Start point — saves current axis positions to startPt[] array on controller | `teach_start_point()` fully implemented; same as SETP-04 |
| SETP-06 | User can write parameter values from Parameters page to controller variables | `apply_to_controller()` fully implemented; extend to fire `hmiCalc=0` post-write and read back |
| SETP-07 | User can trigger varcalc recalculation from Parameters page (sends hmiCalc=0) | No separate button; fold into `apply_to_controller()` — fire `hmiCalc=0`, sleep 500ms, read back |
| SETP-08 | User can exit Setup mode back to main loop from HMI | DMC currently only has `@IN[32]` as exit; add `hmiExSt` variable + OR condition; Python fires on `on_leave` to non-setup screens |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| gclib (via `GalilController.cmd()`) | project fixture | Send raw DMC commands to controller | Project's single communication channel |
| Kivy `Screen` + `Clock` | project fixture | Screen lifecycle, background→UI thread bridge | Established throughout phases 9-12 |
| `utils/jobs.submit()` | project fixture | Serialised background worker for controller I/O | Single gclib handle, no concurrent access |
| `hmi/dmc_vars.py` | project fixture | Single source of truth for DMC variable name strings | Phase 9 decision: never use raw string literals |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `unittest.mock.MagicMock` + `patch` | stdlib | Mock controller and Clock in tests | All new unit tests |
| `time.sleep` (on worker thread only) | stdlib | Wait for varcalc completion before readback | Inside `apply_to_controller` background job only |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `time.sleep(0.5)` in background job | `Clock.schedule_once` with delay | sleep is simpler on the worker thread; schedule_once would need a callback chain on the main thread |
| Separate "Recalculate" button | Fold into Apply | User decided: Apply does write+recalc+readback in one action |

**Installation:** No new packages required.

---

## Architecture Patterns

### Established Project Structure (relevant files)
```
src/dmccodegui/
├── hmi/
│   └── dmc_vars.py          # Add HMI_GO_REST, HMI_GO_START, HMI_EXIT_SETUP
├── screens/
│   ├── axes_setup.py        # Quick actions, jog gate, New Session, smart enter/exit
│   └── parameters.py        # hmiCalc=0 post-apply, 500ms wait, readback; smart enter/exit
└── app_state.py             # No changes needed

tests/
├── test_axes_setup.py       # Extend with new trigger/gate tests
├── test_parameters.py       # Extend with varcalc-after-apply tests
└── test_dmc_vars.py         # Extend with new constant tests

"4 Axis Stainless grind.dmc"  # DMC: add hmiGoRs, hmiGoSt, hmiExSt
```

### Pattern 1: One-Shot HMI Trigger Fire
**What:** Write 0 to a named DMC variable to fire a trigger; DMC resets to 1 immediately on entry.
**When to use:** All HMI-initiated controller actions.
**Example:**
```python
# Source: dmc_vars.py + established pattern from axes_setup.py/_enter_setup_and_read
from ..hmi.dmc_vars import HMI_HOME, HMI_TRIGGER_FIRE

def home_all(self) -> None:
    if not self.controller or not self.controller.is_connected():
        return
    ctrl = self.controller
    def do_home():
        try:
            ctrl.cmd(f"{HMI_HOME}={HMI_TRIGGER_FIRE}")
        except Exception as e:
            print(f"[AxesSetup] home_all failed: {e}")
    jobs.submit(do_home)
```

### Pattern 2: Setup-State Guard Before Any Motion
**What:** Check `state.dmc_state == STATE_SETUP` before allowing jog or quick action.
**When to use:** Any button that requires setup mode.
**Example:**
```python
# Source: established pattern; STATE_SETUP = 3 from dmc_vars.py
from ..hmi.dmc_vars import STATE_SETUP

def jog_axis(self, axis: str, direction: int) -> None:
    if self.state and self.state.dmc_state != STATE_SETUP:
        return   # not in setup mode
    ...
```

### Pattern 3: In-Progress Motion Gate (jog only)
**What:** Read `_BG{axis}` before submitting a new PR/BG; if nonzero, silently skip.
**When to use:** Jog buttons only — prevents queuing multiple relative moves.
**Example:**
```python
# Check in the background job before issuing PR/BG
raw = ctrl.cmd(f"MG _BG{axis}").strip()
if float(raw) != 0:
    return  # previous jog still running
ctrl.cmd(f"PR{axis}={counts}")
ctrl.cmd(f"BG{axis}")
```

### Pattern 4: Smart Setup Enter (skip re-enter if already SETUP)
**What:** In `on_pre_enter`, read `state.dmc_state` — if already `STATE_SETUP` (3), skip `hmiSetp=0`.
**When to use:** Both `AxesSetupScreen` and `ParametersScreen` `on_pre_enter`.
**Example:**
```python
from ..hmi.dmc_vars import STATE_SETUP

def on_pre_enter(self, *args):
    already_in_setup = (
        self.state is not None and self.state.dmc_state == STATE_SETUP
    )
    if not already_in_setup and self.controller and self.controller.is_connected():
        jobs.submit(self._enter_setup_and_read)
    elif self.controller and self.controller.is_connected():
        jobs.submit(self._read_initial_values)  # skip hmiSetp=0, just refresh
```

### Pattern 5: Smart Setup Exit (only if leaving to non-setup screen)
**What:** In `on_leave`, determine destination screen; fire `hmiExSt=0` only when destination is NOT another setup screen.
**When to use:** Both `AxesSetupScreen` and `ParametersScreen` `on_leave`.
**Example:**
```python
SETUP_SCREENS = {"axes_setup", "parameters"}

def on_leave(self, *args):
    sm = self.manager
    next_screen = sm.current if sm else ""
    if next_screen not in SETUP_SCREENS:
        if self.controller and self.controller.is_connected():
            try:
                self.controller.cmd(f"{HMI_EXIT_SETUP}={HMI_TRIGGER_FIRE}")
            except Exception:
                pass
```

### Pattern 6: Post-Apply varcalc
**What:** After writing all params in `apply_to_controller`, fire `hmiCalc=0`, sleep 500ms, read back.
**When to use:** `ParametersScreen.apply_to_controller()` only.
**Example:**
```python
# All on worker thread inside _job():
ctrl.cmd(f"{HMI_CALC}={HMI_TRIGGER_FIRE}")
import time
time.sleep(0.5)         # wait for #VARCALC to complete
# then read back all params as already done in read_from_controller
```

### Pattern 7: New Session Confirmation Dialog
**What:** On button tap, show a Kivy `Popup` with message + Confirm/Cancel buttons; fire `hmiNewS=0` only on Confirm.
**When to use:** New Session button on Axes Setup screen.
**Example (structural):**
```python
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

def on_new_session(self) -> None:
    if self.state and not self.state.setup_unlocked:
        return  # operator role — silently ignore
    content = BoxLayout(orientation='vertical', spacing=8)
    content.add_widget(Label(
        text="Start new session?\nThis will home all axes and reset knife counts."
    ))
    btns = BoxLayout(size_hint_y=None, height=48, spacing=8)
    popup = Popup(title="Confirm", content=content, size_hint=(0.6, 0.4))
    def confirm(*_):
        popup.dismiss()
        self._fire_new_session()
    btns.add_widget(Button(text="Confirm", on_release=confirm))
    btns.add_widget(Button(text="Cancel", on_release=popup.dismiss))
    content.add_widget(btns)
    popup.open()

def _fire_new_session(self) -> None:
    if not self.controller or not self.controller.is_connected():
        return
    ctrl = self.controller
    def do_fire():
        try:
            ctrl.cmd(f"{HMI_NEWS}={HMI_TRIGGER_FIRE}")
        except Exception as e:
            print(f"[AxesSetup] New session failed: {e}")
    jobs.submit(do_fire)
```

### DMC Changes Required

**In `#PARAMS` block — add three new variables:**
```
hmiGoRs = 1;   ' HMI trigger: go to rest position (in setup)
hmiGoSt = 1;   ' HMI trigger: go to start position (in setup)
hmiExSt = 1;   ' HMI trigger: exit setup, return to #MAIN
```

**In `#SULOOP` — add three new IF blocks:**
```
' --- HMI: GO TO REST ---
IF (hmiGoRs = 0)
  hmiGoRs = 1
  MG "HMI: GOING TO REST"
  JS #GOREST
  JS #W_REL
ENDIF

' --- HMI: GO TO START ---
IF (hmiGoSt = 0)
  hmiGoSt = 1
  MG "HMI: GOING TO START"
  JS #GOSTR
  JS #W_REL
ENDIF

' --- BUTTON 32 OR HMI EXIT SETUP ---
IF (@IN[32] = 0) | (hmiExSt = 0)
  hmiExSt = 1
  MG "RETURNING TO MAIN MENU"
  JS #W_REL
  EN
ENDIF
```

**Note:** The existing `IF (@IN[32] = 0)` block must be replaced (not duplicated) with the combined OR version.

### Anti-Patterns to Avoid
- **XQ direct calls:** All triggers through HMI variable one-shot pattern only. `XQ #AUTO` in `recover()` is the sole authorised XQ call (Phase 11 decision).
- **Firing `hmiSetp=0` on every tab switch:** Smart enter checks `dmc_state == STATE_SETUP` first.
- **Firing `hmiExSt=0` when navigating between setup screens:** Smart exit checks destination screen name.
- **Multiple simultaneous jog moves:** Check `_BG{axis}` before issuing PR/BG; if nonzero, return.
- **BV outside explicit user saves:** Never in poll loops; only in teach and apply-params flows.
- **Optimistic knife count reset:** Let the 10 Hz poller carry the updated count from the controller; no local zero.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Go To Rest / Go To Start safe axis ordering | Custom Python multi-axis sequencing | `hmiGoRs=0` / `hmiGoSt=0` triggers into DMC `#GOREST` / `#GOSTR` | DMC routines have B-first (rest) and correct order built in; Python cannot know safe ordering |
| NV memory burn | Custom write-verify loop | `ctrl.cmd("BV")` then readback | BV is the Galil-native persist command |
| Thread safety for UI updates from worker | Direct widget mutation on worker thread | `Clock.schedule_once(lambda *_: ...)` | Kivy canvas operations must run on main thread |
| Confirmation dialog | Custom overlay widget | Kivy `Popup` | Standard Kivy pattern; minimal code |

---

## Common Pitfalls

### Pitfall 1: Double-Firing hmiSetp=0 on Tab Switch
**What goes wrong:** User taps Axes Setup → Parameters → Axes Setup; each `on_pre_enter` fires `hmiSetp=0`, causing a spurious state transition.
**Why it happens:** No guard against already-in-SETUP state.
**How to avoid:** Check `self.state.dmc_state == STATE_SETUP` in `on_pre_enter`; if true, skip the fire, only call `_read_initial_values()`.
**Warning signs:** hmiState flickers 3→3 in controller terminal output on every tab switch.

### Pitfall 2: Firing hmiExSt=0 When Navigating Between Setup Screens
**What goes wrong:** Navigating Axes Setup → Parameters triggers `on_leave` on AxesSetup which fires `hmiExSt=0`, causing controller to exit `#SULOOP` back to `#MAIN`. Then Parameters fires `hmiSetp=0` to try to re-enter.
**Why it happens:** `on_leave` fires unconditionally.
**How to avoid:** In `on_leave`, inspect `self.manager.current` — only fire `hmiExSt=0` when next screen is NOT in `{"axes_setup", "parameters"}`.
**Warning signs:** hmiState shows 1 (IDLE) briefly between tab switches; second tab entry takes an extra ~100ms poll tick to reach state 3.

### Pitfall 3: Stale Jog While Another Is In Progress
**What goes wrong:** Rapid button taps queue multiple PR/BG jobs; axes overshoot by accumulated counts.
**Why it happens:** `jobs.submit()` is FIFO — each tap enqueues another relative move.
**How to avoid:** Read `_BG{axis}` at the start of the background job; if nonzero, return immediately without sending PR/BG.
**Warning signs:** Axis travels further than one step distance on a single button press.

### Pitfall 4: varcalc Readback Too Early
**What goes wrong:** `apply_to_controller` reads params back immediately after writing — before `#VARCALC` completes — and displays stale derived values.
**Why it happens:** `ctrl.cmd("hmiCalc=0")` returns immediately; `#VARCALC` runs async on the controller.
**How to avoid:** `time.sleep(0.5)` on the worker thread between firing `hmiCalc=0` and reading back params. 500ms is the agreed target (Claude's discretion: exact value).
**Warning signs:** `cpmA`/`cpmB`/`cpmC`/`cpmD` shown in Parameters UI don't change after editing pitch/ratio.

### Pitfall 5: New Session Fired Without Role Check
**What goes wrong:** An Operator (who cannot use Setup functions) accidentally triggers New Session.
**Why it happens:** Role guard missing from `on_new_session()`.
**How to avoid:** Check `self.state.setup_unlocked` before opening the dialog. Return silently if False.
**Warning signs:** New Session button visible but not disabled when logged in as Operator.

### Pitfall 6: Eight-Character DMC Variable Name Limit
**What goes wrong:** New variable names exceed 8 chars and the controller silently truncates, creating a different variable.
**Why it happens:** Galil firmware hard limit.
**How to avoid:** `hmiGoRs` (7), `hmiGoSt` (7), `hmiExSt` (7) — all within limit. Verify in `test_dmc_vars.py` with `len(name) <= 8` assertion.
**Warning signs:** `MG hmiGoRs` returns an error or always 0.

---

## Code Examples

### New dmc_vars.py Constants
```python
# Source: project pattern from existing constants
HMI_GO_REST: str   = "hmiGoRs"   # Trigger: go to rest position (in setup)
HMI_GO_START: str  = "hmiGoSt"   # Trigger: go to start position (in setup)
HMI_EXIT_SETUP: str = "hmiExSt"  # Trigger: exit setup, return to #MAIN
```

All three are 7 characters — within the 8-char DMC limit.

### Updated on_leave With Smart Exit
```python
_SETUP_SCREENS = frozenset({"axes_setup", "parameters"})

def on_leave(self, *args):
    """Fire hmiExSt=0 only when navigating away from all setup screens."""
    next_screen = ""
    if self.manager:
        next_screen = self.manager.current
    if next_screen not in _SETUP_SCREENS:
        if self.controller and self.controller.is_connected():
            try:
                self.controller.cmd(f"{HMI_EXIT_SETUP}={HMI_TRIGGER_FIRE}")
            except Exception:
                pass
```

### Updated jog_axis With Motion Gate + State Gate
```python
def jog_axis(self, axis: str, direction: int) -> None:
    if not self.controller or not self.controller.is_connected():
        return
    if not self._cpm_ready:
        return
    if self.state and self.state.dmc_state != STATE_SETUP:
        return  # not in setup mode
    cpm = self._axis_cpm.get(axis, 0.0)
    if cpm <= 0:
        return
    counts = int(direction * self._current_step_mm * cpm)
    ctrl = self.controller

    def do_jog():
        # In-progress motion gate
        try:
            raw = ctrl.cmd(f"MG _BG{axis}").strip()
            if float(raw) != 0:
                return  # previous jog still in progress
        except Exception:
            return
        try:
            ctrl.cmd(f"PR{axis}={counts}")
            ctrl.cmd(f"BG{axis}")
            import time
            for _ in range(60):
                time.sleep(0.1)
                try:
                    raw = ctrl.cmd(f"MG _TD{axis}").strip()
                    _push_pos(f"{float(raw):.1f}")
                except Exception:
                    pass
                try:
                    bg_raw = ctrl.cmd(f"MG _BG{axis}").strip()
                    if float(bg_raw) == 0:
                        break
                except Exception:
                    break
            raw = ctrl.cmd(f"MG _TD{axis}").strip()
            _push_pos(f"{float(raw):.1f}")
        except Exception as e:
            print(f"[AxesSetup] Jog {axis} failed: {e}")

    jobs.submit(do_jog)
```

### Updated apply_to_controller With varcalc
```python
def apply_to_controller(self) -> None:
    # ... (existing guards unchanged) ...
    dirty_snapshot = dict(self._dirty)
    param_defs_snapshot = mc.get_param_defs()

    def _job():
        import time
        ctrl = self.controller
        if ctrl is None:
            return
        for var_name, text in dirty_snapshot.items():
            try:
                ctrl.cmd(f"{var_name}={text}")
            except Exception:
                pass
        # Fire varcalc then wait for completion
        try:
            ctrl.cmd(f"{HMI_CALC}={HMI_TRIGGER_FIRE}")
        except Exception:
            pass
        time.sleep(0.5)   # wait for #VARCALC to complete
        # Read back all params
        new_vals: Dict[str, float] = {}
        for p in param_defs_snapshot:
            var = p['var']
            try:
                raw = ctrl.cmd(f"MG {var}")
                new_vals[var] = float(raw.strip())
            except Exception:
                pass
        try:
            ctrl.cmd("BV")
        except Exception:
            pass
        # Update UI state (existing pattern)
        self._controller_vals.update(new_vals)
        self._dirty.clear()
        self.pending_count = 0
        for var_name, widget in self._field_widgets.items():
            self._set_field_state(widget, 'valid')

    submit(_job)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `swGoRest=1`, `swGoStart=1`, `swHomeAll=1` (software vars) | `hmiGoRs=0`, `hmiGoSt=0`, `hmiHome=0` (one-shot triggers) | Phase 13 | Dead code removed; controller state machine handles safe axis ordering |
| `@IN[32] = 0` only for exit-setup | `@IN[32] = 0 \| hmiExSt = 0` | Phase 13 | HMI can now exit setup without physical button press |
| No OR for `hmiGoRs`/`hmiGoSt` in `#SULOOP` | New IF blocks added | Phase 13 | HMI can drive Go To Rest/Start from touchscreen inside setup mode |
| `on_leave` always resets `hmiSetp=1` | Smart exit fires `hmiExSt=0` to non-setup screens only | Phase 13 | No spurious exit/re-enter cycle on Axes Setup ↔ Parameters navigation |

**Deprecated/outdated:**
- `_send_sw_var()` method in `axes_setup.py`: was used for `swGoRest`/`swGoStart`/`swHomeAll` — becomes dead code after migration; can be removed or left as internal helper.
- `swGoRest`, `swGoStart`, `swHomeAll` in DMC #PARAMS: no longer set from Python; safe to leave declared but inert.

---

## Open Questions

1. **Confirmation dialog when controller disconnects mid-flow**
   - What we know: `jobs.submit` swallows exceptions; the trigger fire silently fails.
   - What's unclear: Should the user see a banner/toast on failure?
   - Recommendation: Log to `_alert()` on exception (existing helper); treat as Claude's discretion per CONTEXT.md.

2. **hmiGoRs/hmiGoSt in #WtAtRt as well?**
   - What we know: CONTEXT.md marks this as Claude's discretion.
   - What's unclear: Are there use cases for triggering Go To Rest/Start from idle state outside setup?
   - Recommendation: Add only to `#SULOOP` for this phase — simpler, avoids state-machine ambiguity. `#GOREST` is also called at grind completion, so adding it to `#WtAtRt` would need extra hmiState guards.

3. **Exact wait time for varcalc**
   - What we know: CONTEXT.md says "within ~500ms range"; `#VARCALC` runs serially on the controller.
   - What's unclear: Actual completion time under load — requires hardware validation.
   - Recommendation: Use 500ms; flag as a hardware validation item.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (inferred from project) |
| Quick run command | `python -m pytest tests/test_axes_setup.py tests/test_parameters.py tests/test_dmc_vars.py -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| SETP-01 | `on_pre_enter` fires `hmiSetp=0` when not already in SETUP | unit | `pytest tests/test_axes_setup.py -k "enter_setup" -x` | Wave 0 gap |
| SETP-01 | `on_pre_enter` skips `hmiSetp=0` when `dmc_state==STATE_SETUP` | unit | `pytest tests/test_axes_setup.py -k "skip_reenter" -x` | Wave 0 gap |
| SETP-02 | `home_all()` fires `hmiHome=0` (not `swHomeAll=1`) | unit | `pytest tests/test_axes_setup.py -k "home_all_fires_hmi" -x` | Wave 0 gap |
| SETP-03 | `jog_axis()` blocked when `dmc_state != STATE_SETUP` | unit | `pytest tests/test_axes_setup.py -k "jog_blocked_not_setup" -x` | Wave 0 gap |
| SETP-03 | `jog_axis()` blocked when `_BG{axis} != 0` (in-progress) | unit | `pytest tests/test_axes_setup.py -k "jog_blocked_in_progress" -x` | Wave 0 gap |
| SETP-04 | `teach_rest_point()` reads TD, writes restPt vars, sends BV, reads back | unit | `pytest tests/test_axes_setup.py::test_teach_rest_burns_nv -x` | ✅ (existing) |
| SETP-05 | `teach_start_point()` reads TD, writes startPt vars, sends BV, reads back | unit | `pytest tests/test_axes_setup.py::test_teach_start_burns_nv -x` | ✅ (existing) |
| SETP-06 | `apply_to_controller()` writes each dirty param to controller | unit | `pytest tests/test_parameters.py -k "apply" -x` | ✅ (existing) |
| SETP-07 | `apply_to_controller()` fires `hmiCalc=0` after writing params | unit | `pytest tests/test_parameters.py -k "apply_fires_calc" -x` | Wave 0 gap |
| SETP-07 | `apply_to_controller()` reads back params after 500ms delay | unit | `pytest tests/test_parameters.py -k "apply_readback" -x` | Wave 0 gap |
| SETP-08 | `on_leave` fires `hmiExSt=0` when navigating to non-setup screen | unit | `pytest tests/test_axes_setup.py -k "exit_setup_fires" -x` | Wave 0 gap |
| SETP-08 | `on_leave` does NOT fire `hmiExSt=0` when navigating to sibling setup screen | unit | `pytest tests/test_axes_setup.py -k "no_exit_sibling" -x` | Wave 0 gap |
| SETP-08 | New DMC constants have correct values and ≤8 chars | unit | `pytest tests/test_dmc_vars.py -k "go_rest or go_start or exit_setup" -x` | Wave 0 gap |

**Note:** SETP-02 through SETP-05 hardware validation (real axis movement) is manual-only per REQUIREMENTS.md out-of-scope decision ("Automated testing against real controller").

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_axes_setup.py tests/test_parameters.py tests/test_dmc_vars.py -q`
- **Per wave merge:** `python -m pytest tests/ -q`
- **Phase gate:** Full suite (239 + new tests) green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_axes_setup.py` — add tests for: smart enter (SETP-01 guard), `home_all` HMI trigger (SETP-02), jog not-in-setup gate (SETP-03), jog in-progress gate (SETP-03), smart exit (SETP-08 fires / SETP-08 no-fire)
- [ ] `tests/test_parameters.py` — add tests for: `apply_to_controller` fires `hmiCalc=0` (SETP-07), readback after delay (SETP-07 readback)
- [ ] `tests/test_dmc_vars.py` — add tests for three new constants: `HMI_GO_REST`, `HMI_GO_START`, `HMI_EXIT_SETUP` (name values, ≤8 chars, presence in any ALL_ list if added)

*(No new test files needed — all tests extend existing files.)*

---

## Sources

### Primary (HIGH confidence)
- Direct source read: `src/dmccodegui/hmi/dmc_vars.py` — all constant names and values verified
- Direct source read: `src/dmccodegui/screens/axes_setup.py` — full method inventory and jog/teach logic
- Direct source read: `src/dmccodegui/screens/parameters.py` — full apply/read/varcalc lifecycle
- Direct source read: `4 Axis Stainless grind.dmc` — exact `#PARAMS`, `#SULOOP`, `#GOREST`, `#GOSTR` structure
- Direct source read: `.planning/phases/13-setup-loop/13-CONTEXT.md` — all locked decisions

### Secondary (MEDIUM confidence)
- `tests/test_axes_setup.py` — test patterns for mocking controller and asserting `cmd()` call sequences
- `src/dmccodegui/hmi/poll.py` — confirmed `dmc_state` is polled at 10 Hz; state transitions visible within one tick

### Tertiary (LOW confidence)
- 500ms varcalc wait time — based on CONTEXT.md decision; actual completion time hardware-dependent

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are project fixtures, no new dependencies
- Architecture: HIGH — patterns established in phases 9-12; this phase wires existing pieces
- Pitfalls: HIGH — derived from reading actual code and CONTEXT.md decision log
- DMC changes: HIGH — exact current `#SULOOP` and `#PARAMS` read from source file; new vars fit 8-char limit

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable domain; only invalidated by controller firmware changes)
