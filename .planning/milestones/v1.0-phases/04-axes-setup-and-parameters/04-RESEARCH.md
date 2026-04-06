# Phase 4: Axes Setup and Parameters - Research

**Researched:** 2026-04-04
**Domain:** Kivy touchscreen UI — axes jog/teach screen and grouped parameter editor on a Galil DMC controller
**Confidence:** HIGH (all findings from direct codebase inspection, no external lookups needed)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Jog Behavior**
- Live jog using PR (Position Relative) + BG commands per button press — axis moves immediately
- No confirmation dialog before jog moves — Setup user is authenticated and physically at machine
- Three mm-based step toggle buttons: 10mm, 5mm, 1mm (mutually exclusive selection)
- Jog distance = step_mm * cpmX (counts per mm for that axis)
- Example: 10mm step on A axis with cpmA=1200 sends `PRA=12000` then `BGA`
- No slider — arrow buttons + step toggles only
- CPM values can be read from controller (cpmA/B/C/D) or derived from calibration params (ctsRev * ratio / pitch) — Claude's discretion on which is more convenient

**D-Axis Handling**
- D axis appears in the sidebar alongside A/B/C with same jog/teach UI layout
- D axis uses same mm-based step toggles (10mm/5mm/1mm) with cpmD conversion
- D axis accent color: yellow (per established theme)
- D axis has its own DMC variables: `restPtD` and `startPtD` — no array sharing with A/B/C
- D axis label: "Rotation" in sidebar

**Position Display**
- Current position read via TD commands: `_TDA`, `_TDB`, `_TDC`, `_TDD`
- Polling at ~2-5 Hz timer for live position updates (same pattern as RUN page but slower)
- Position cards per axis: Rest Point, Start Point, Current Position (from mockup)

**Teach Buttons**
- Two teach buttons per axis view: "Teach as Rest Point" and "Teach as Start Point"
- One press captures ALL 4 axes at once: `restPtA=_TDA`, `restPtB=_TDB`, `restPtC=_TDC`, `restPtD=_TDD` (and same pattern for start points)
- After teaching, send BV command to burn values to non-volatile memory
- Setup user jogs axes to desired positions first, then teaches to capture

**Quick Action Buttons**
- Include Go to Rest All, Go to Start All, Home All buttons
- These work by setting software variables (mimicking physical button presses) that the DMC program's main loop polls
- Software button variables (Claude names): `swGoSetup`, `swMoreGrind`, `swLessGrind`, `swNewStone` — set to 0 or 1
- "Go Setup" puts controller into setup mode where axes can move freely
- This approach keeps the controller in its normal program flow rather than sending raw PA/BG which could disrupt state

**Parameter Definitions**
- Parameters organized into grouped cards (matching mockup pattern)
- **Calibration group (per axis):**
  - `pitchA`, `pitchB`, `pitchC`, `pitchD` — leadscrew pitch (mm/rev; D is deg/rev)
  - `ratioA`, `ratioB`, `ratioC`, `ratioD` — gear ratio
  - `ctsRevA`, `ctsRevB`, `ctsRevC`, `ctsRevD` — encoder counts per revolution
- **Geometry group:**
  - `knfThk` — knife thickness (mm)
  - `edgeThk` — edge thickness (mm)
  - `backOff` — limit switch back-off distance (mm)
- **Feedrates group (mm/s):**
  - `fdA`, `fdB`, `fdCdn`, `fdCup`, `fdPark`, `fdD`
- Each parameter row shows: human-readable name, DMC variable code, editable input, unit

**Parameter Validation**
- Type check (must be valid number) + basic sanity ranges
- Negatives rejected for feedrates; zero rejected for pitch/ratio/ctsRev
- Claude defines reasonable range defaults per parameter purpose
- Invalid inputs flagged with red border immediately (PARAM-03)
- Modified (unsaved) values highlighted amber with change counter (PARAM-04)

**Apply/Save Workflow (Parameters)**
- Batch apply: user edits multiple fields, presses "Apply to Controller" to send ALL modified values at once
- After apply: automatically read-back all updated values from controller to verify receipt
- Apply button also sends BV command to burn values to non-volatile memory
- "Read from Controller" button refreshes all parameter values from controller

### Claude's Discretion
- Whether to read CPM from controller variables or derive from calibration params
- Exact software button variable names (swGoSetup etc. are suggestions)
- Reasonable min/max validation ranges per parameter
- Axis sidebar layout details and position card styling
- Loading/empty states
- Exact parameter grouping card visual design

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AXES-01 | Single unified axes setup screen with sidebar to select between A, B, C, D axes | Kivy ScreenManager already has AxesSetupScreen placeholder; sidebar = ToggleButton group switching active axis view |
| AXES-02 | Each axis view shows Rest Point, Start Point, and Current Position values | TD commands for current pos; restPtX/startPtX DMC variables for taught points |
| AXES-03 | Jog controls with arrow buttons and selectable step size (10mm/5mm/1mm) | HControl/VControl widgets in theme.kv; PR+BG pattern; CPM conversion |
| AXES-04 | Teach buttons to capture current physical position as Rest Point or Start Point | All-4-axis capture via TD commands + BV burn to NV memory |
| AXES-05 | Quick action buttons: Go to Rest All, Go to Start All, Home All | Software variable pattern (swGoSetup etc.) via controller.cmd() |
| AXES-06 | Axes setup only accessible to Setup and Admin roles | TabBar already role-gates this tab; screen can also check state.setup_unlocked |
| PARAM-01 | Parameters organized into grouped cards: Geometry, Feedrates, Calibration, Positions, Safety | CardFrame widget in theme.kv; ScrollView containing group cards |
| PARAM-02 | Each parameter row shows human-readable name, DMC code, editable input, unit | Custom ParamRow widget (4-column BoxLayout); mirrors ParamCell/ParamLabel/ParamInput from parameters_setup.kv |
| PARAM-03 | Invalid inputs flagged with red border immediately on entry | TextInput on_text binding → validate() → set border color |
| PARAM-04 | Modified values shown with amber highlight and change counter | Track _dirty dict; amber border on modified fields; counter Label in bottom bar |
| PARAM-05 | "Apply to Controller" button sends all modified parameters at once | Batch controller.cmd() for each dirty param; then read-back verify; then BV |
| PARAM-06 | "Read from Controller" button refreshes all parameter values | controller.cmd("MG varName") per param; post back to UI via Clock |
| PARAM-07 | Parameters page only editable by Setup/Admin; Operator can view but not modify | Disable TextInput via `disabled` property or `readonly` based on state.setup_unlocked |
</phase_requirements>

---

## Summary

Phase 4 builds two new screens — AxesSetupScreen and ParametersScreen — replacing the existing placeholder stubs. Both screens already exist as registered Python classes and KV placeholders in the codebase; all scaffolding (screen registration in `__init__.py`, KV loading in `KV_FILES`, injection of `controller` and `state` via `main.py`) is in place. The work is purely replacing the placeholder content with real implementations.

The axes screen follows the established pattern from `rest.py` / `axisDSetup.py`: `on_pre_enter` reads from controller, arrow buttons call `controller.cmd()` via `jobs.submit()`, and UI updates post back via `Clock.schedule_once()`. The new requirement is a sidebar for axis selection, live position polling (2-5 Hz Clock interval like `buttons_switches.py`), and PR+BG jog commands with CPM-based mm conversion instead of raw count adjustments.

The parameters screen introduces the "dirty tracking" pattern — a Python dict that records which fields have been modified and not yet applied. On-text-change validation sets border colors immediately (red=invalid, amber=modified), and a bottom bar shows the count of pending changes. Batch apply sends all dirty values via `controller.cmd()`, reads back all params, then sends BV. No new PyPI packages are required.

**Primary recommendation:** Implement AxesSetupScreen in Wave 1, ParametersScreen in Wave 2. Both screens can be developed and tested independently since they are separate KV+py file pairs.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| kivy | (project) | Screen layout, widgets, event loop | Already the app framework |
| kivy.clock | (project) | Polling timer, UI post-back from threads | Established pattern across all screens |
| kivy.properties | (project) | NumericProperty, StringProperty, ListProperty, BooleanProperty | Kivy reactive binding |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| kivy.uix.screenmanager.Screen | (project) | Base class for both new screens | Matches all existing screens |
| kivy.uix.scrollview | (project) | Scrollable parameter list | Parameters screen needs scroll for grouped cards |
| threading (stdlib) | stdlib | Background controller I/O via jobs.submit() | Already used everywhere |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Clock.schedule_interval for polling | jobs.schedule() | schedule_interval runs on main thread which is correct for UI; jobs.schedule runs on worker thread — use schedule_interval for the timer, jobs.submit for the I/O work |
| Separate screen per axis | Single screen with sidebar | Single screen is simpler and matches the AXES-01 requirement explicitly |

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended Project Structure

No new files at the package level. Changes are:
```
src/dmccodegui/
├── screens/
│   ├── axes_setup.py       # Replace placeholder — AxesSetupScreen full implementation
│   └── parameters.py       # Replace placeholder — ParametersScreen full implementation
└── ui/
    ├── axes_setup.kv        # Replace placeholder — full KV layout
    └── parameters.kv        # Replace placeholder — full KV layout
```

### Pattern 1: Axis Sidebar Selection

**What:** A column of 4 ToggleButtons (one per axis A/B/C/D) acts as a tab selector. Pressing a button changes the `_selected_axis` StringProperty, which the KV uses to show/hide (or swap content of) axis-specific panels.

**When to use:** When a single screen must show data for any one of N uniform items.

**Example:**
```python
# axes_setup.py
from kivy.properties import StringProperty, NumericProperty

class AxesSetupScreen(Screen):
    _selected_axis = StringProperty("A")

    def select_axis(self, axis: str) -> None:
        self._selected_axis = axis
```
```kivy
# axes_setup.kv — sidebar toggle group
ToggleButton:
    text: "A  Feed"
    group: "axis_sel"
    state: "down"
    on_release: root.select_axis("A")
ToggleButton:
    text: "B  Lift"
    group: "axis_sel"
    on_release: root.select_axis("B")
```

### Pattern 2: Live Position Polling (2-5 Hz)

**What:** `Clock.schedule_interval` creates a repeating timer. The callback submits a background job via `jobs.submit()`. The background job reads `_TDA` / `_TDB` / `_TDC` / `_TDD` and posts results back via `Clock.schedule_once()`.

**When to use:** Any screen requiring live controller data updates.

**Example:**
```python
# Follows buttons_switches.py exactly
_poll_event = None

def on_pre_enter(self, *args):
    self._load_all_positions()
    if self._poll_event:
        self._poll_event.cancel()
    self._poll_event = Clock.schedule_interval(self._poll_tick, 1 / 3.0)  # 3 Hz

def on_leave(self, *args):
    if self._poll_event:
        self._poll_event.cancel()
        self._poll_event = None

def _poll_tick(self, dt):
    if not self.controller or not self.controller.is_connected():
        return
    def do_poll():
        try:
            results = {}
            for ax in ("A", "B", "C", "D"):
                resp = self.controller.cmd(f"MG _TD{ax}")
                results[ax] = float(resp.strip())
        except Exception:
            return
        Clock.schedule_once(lambda *_, r=results: self._update_positions(r))
    jobs.submit(do_poll)
```

### Pattern 3: PR+BG Live Jog with CPM Conversion

**What:** Each arrow button press converts mm step size to encoder counts using CPM for the selected axis, then sends `PR{axis}={counts}` followed by `BG{axis}`.

**When to use:** Incremental axis jogging during setup.

**Example:**
```python
# AXIS_CPM derived from calibration params: ctsRevX * ratioX / pitchX
# Or read from controller: MG cpmA
AXIS_CPM_DEFAULTS = {
    "A": 1200.0,  # fallback if read fails
    "B": 1200.0,
    "C": 800.0,
    "D": 500.0,
}

def jog_axis(self, axis: str, direction: int) -> None:
    """direction: +1 or -1"""
    step_mm = self._current_step_mm  # 10.0, 5.0, or 1.0
    cpm = self._axis_cpm.get(axis, AXIS_CPM_DEFAULTS[axis])
    counts = int(direction * step_mm * cpm)
    self._send_dmc(f"PR{axis}={counts}")
    self._send_dmc(f"BG{axis}")

def _send_dmc(self, command: str) -> None:
    if not self.controller or not self.controller.is_connected():
        return
    def do_cmd():
        try:
            self.controller.cmd(command)
        except Exception as e:
            Clock.schedule_once(lambda *_: self._alert(str(e)))
    jobs.submit(do_cmd)
```

### Pattern 4: All-Axes Teach (Capture + BV)

**What:** One button tap reads current position from all 4 axes via TD commands and writes to the corresponding DMC scalar variables, then burns with BV.

**When to use:** Teach Rest Point or Teach Start Point.

**Example:**
```python
def teach_rest_point(self) -> None:
    def do_teach():
        try:
            vals = {}
            for ax in ("A", "B", "C", "D"):
                resp = self.controller.cmd(f"MG _TD{ax}")
                vals[ax] = float(resp.strip())
            # Write scalar DMC variables (not arrays)
            self.controller.cmd(
                f"restPtA={vals['A']};restPtB={vals['B']};"
                f"restPtC={vals['C']};restPtD={vals['D']}"
            )
            self.controller.cmd("BV")  # Burn to non-volatile memory
        except Exception as e:
            Clock.schedule_once(lambda *_: self._alert(f"Teach failed: {e}"))
    jobs.submit(do_teach)
```

**Note:** The old screens (rest.py, axisDSetup.py) used DMC arrays (`RestPnt[0..2]`, `download_array()`). Phase 4 uses individual scalar DMC variables (`restPtA`, `restPtB`, etc.) — this is the new locked design. The old screens are NOT replaced; they remain for backward compatibility.

### Pattern 5: Dirty-Tracking Parameter Editor

**What:** A dict maps DMC variable name to its current (controller-read) value and a separate dict tracks user-edited (pending) values. On every TextInput change, validation runs, border color updates, and the change counter increments.

**When to use:** Any batched-edit form where unsaved state must be visible.

**Example:**
```python
from kivy.properties import NumericProperty, DictProperty

class ParametersScreen(Screen):
    pending_count = NumericProperty(0)  # KV binds bottom-bar counter to this

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # {var_name: {"label": str, "value": float, "unit": str, "group": str, "min": float, "max": float}}
        self._param_defs: dict = {}
        # {var_name: float}  — last known controller values
        self._controller_vals: dict = {}
        # {var_name: str}  — user-edited strings not yet applied
        self._dirty: dict = {}

    def on_field_text_change(self, var_name: str, text: str) -> None:
        """Called from KV on_text binding for each parameter input."""
        widget = self._field_widgets[var_name]
        try:
            val = float(text)
            p = self._param_defs[var_name]
            if val < p["min"] or val > p["max"]:
                raise ValueError(f"Out of range [{p['min']}, {p['max']}]")
            # Valid and changed — amber
            current = self._controller_vals.get(var_name)
            if current is not None and abs(val - current) > 1e-9:
                self._dirty[var_name] = text
                self._set_border_amber(widget)
            else:
                self._dirty.pop(var_name, None)
                self._set_border_normal(widget)
        except (ValueError, KeyError):
            self._dirty.pop(var_name, None)
            self._set_border_red(widget)
        self.pending_count = len(self._dirty)
```

### Pattern 6: Batch Apply + Read-Back Verify

**What:** "Apply to Controller" sends all dirty values in one background job, then reads all params back to confirm receipt, then sends BV.

**Example:**
```python
def apply_to_controller(self) -> None:
    if not self._dirty:
        return
    to_send = dict(self._dirty)  # snapshot
    def do_apply():
        try:
            # Send all modified values
            for var_name, text_val in to_send.items():
                self.controller.cmd(f"{var_name}={text_val}")
            # Read back all params to verify
            readback = {}
            for var_name in self._param_defs:
                resp = self.controller.cmd(f"MG {var_name}")
                readback[var_name] = float(resp.strip())
            # Burn to NV memory
            self.controller.cmd("BV")
            Clock.schedule_once(lambda *_, rb=readback: self._on_apply_complete(rb))
        except Exception as e:
            Clock.schedule_once(lambda *_: self._alert(f"Apply failed: {e}"))
    jobs.submit(do_apply)

def _on_apply_complete(self, readback: dict) -> None:
    self._controller_vals.update(readback)
    self._dirty.clear()
    self.pending_count = 0
    # Reset all field borders to normal
    for var_name in self._param_defs:
        if var_name in self._field_widgets:
            self._set_border_normal(self._field_widgets[var_name])
```

### Pattern 7: Role-Based Read-Only Mode (PARAM-07)

**What:** On `on_pre_enter`, check `state.setup_unlocked`. If False (Operator), set all TextInput widgets to `readonly = True` and hide the Apply button.

**Example:**
```python
def on_pre_enter(self, *args):
    is_editable = self.state and self.state.setup_unlocked
    for widget in self._field_widgets.values():
        widget.readonly = not is_editable
    # Show/hide apply button
    self.ids.apply_btn.opacity = 1 if is_editable else 0
    self.ids.apply_btn.disabled = not is_editable
    self._read_from_controller()
```

### Anti-Patterns to Avoid

- **Sending BG without axis letter after PR:** `PR{axis}={counts}; BG{axis}` is safer than bare `BG` which starts all axes. Use `BGA`, `BGB`, etc.
- **Using download_array() for scalar taught points:** The new design stores `restPtA`/`startPtA` as scalar DMC variables, not array indices. Use `controller.cmd("restPtA=value")` not `download_array("RestPnt", ...)`.
- **Running controller.cmd() on the Kivy main thread:** Always via `jobs.submit()`. The existing screens all demonstrate this pattern correctly.
- **On_text firing during programmatic text assignment:** When populating fields from controller read-back, temporarily disable the on_text handler or check `_loading` flag to avoid spurious dirty marking.
- **Forgetting on_leave cleanup:** All screens using Clock.schedule_interval MUST cancel in on_leave, or the poll continues after navigation.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Thread-safe background jobs | Custom thread pool | `jobs.submit()` (already exists) | Handles queue, worker lifecycle, exception swallowing |
| Periodic polling | Custom threading.Timer | `Clock.schedule_interval()` | Runs on Kivy main thread, auto-cancelled on app stop |
| Post-thread UI updates | threading.Event + polling | `Clock.schedule_once(lambda *_: ...)` | Established pattern; safe with Kivy's single-threaded GL |
| Step toggle mutual exclusion | Manual button state management | Kivy `ToggleButton` with `group=` | Built-in radio behavior at zero cost |
| Axis accent colors | Hardcoded RGB tuples per axis | Use established constants: A=orange `(0.980, 0.569, 0.043)`, B=purple `(0.659, 0.333, 0.965)`, C=cyan `(0.024, 0.714, 0.831)`, D=yellow `(0.980, 0.749, 0.043)` | Theme consistency across all screens |
| Card widgets | Custom canvas drawing | `CardFrame` from theme.kv | Already defined; handles background and border |
| Dividers between panels | Manual canvas | `VDivider` from theme.kv | Consistent visual separation |

---

## Common Pitfalls

### Pitfall 1: BV Command Scope
**What goes wrong:** Sending `BV` burns ALL non-volatile variables to flash. If sent while a cycle is running, it may corrupt mid-cycle variables.
**Why it happens:** BV is a global operation on the Galil controller.
**How to avoid:** Only send BV when `state.cycle_running` is False. The screen is Setup-only (cycle won't start on axes setup screen), but add a guard check.
**Warning signs:** Controller behaving erratically after power cycle following an in-cycle BV.

### Pitfall 2: PR vs PA Commands for Jog
**What goes wrong:** Using PA (Position Absolute) for jog moves requires knowing the current absolute position; sending the wrong PA value can cause large unexpected moves.
**Why it happens:** Old code (axisDSetup.py) used `pa=` — this is risky because the position must be computed relative to current position.
**How to avoid:** Use PR (Position Relative) for jog as specified: `PRA={counts}` then `BGA`. The controller handles the relative math.
**Warning signs:** Axis jumping to unexpected absolute positions when step toggle is pressed.

### Pitfall 3: on_text Firing During Read-Back Population
**What goes wrong:** When `_on_apply_complete` sets `widget.text = str(readback_val)`, the on_text callback fires and marks the field as dirty again (since the controller value hasn't been updated yet in `_controller_vals`).
**Why it happens:** Kivy's on_text is synchronous and fires immediately on assignment.
**How to avoid:** Set a `_loading = True` flag before programmatic text assignments, check it in on_text handler, reset after all assignments are done.
**Warning signs:** `pending_count` jumps to N after "Apply to Controller" completes successfully.

### Pitfall 4: KV Lambda Step Size Evaluation
**What goes wrong:** The existing KV pattern `lambda: root.adjust_axis('A', -(step1.state=='down' and 1 or ...))` evaluates ToggleButton state at press time. This works correctly. But if the lambda is constructed during build time (not at press time), stale state is captured.
**Why it happens:** Python lambda captures variable references, but KV lambdas re-evaluate each time the on_press fires.
**How to avoid:** Keep step evaluation inside the Python method (`self._current_step_mm`), not in the KV lambda. This is cleaner for the new screen since step sizes are mm values, not raw counts.
**Warning signs:** All button presses use the same step regardless of toggle state.

### Pitfall 5: CPM Value of Zero
**What goes wrong:** If CPM for an axis is zero or not yet read, `counts = int(direction * step_mm * cpm)` sends `PR{axis}=0` followed by `BG{axis}` — axis twitches or faults.
**Why it happens:** Controller might not have `cpmA` defined if the DMC program doesn't use that variable name, or the read fails.
**How to avoid:** Use `AXIS_CPM_DEFAULTS` as fallback; validate CPM > 0 before sending jog command; log warning if CPM read returns 0.
**Warning signs:** Axis doesn't move when arrow buttons are pressed even though jog commands are sent.

### Pitfall 6: Teach Overwrites All 4 Axes Simultaneously
**What goes wrong:** The teach pattern captures all 4 axes at once. If only axis A is in position and the operator accidentally taps Teach, axes B/C/D rest points get set to their current (possibly wrong) positions.
**Why it happens:** The locked design teaches all axes at once to keep them synchronized.
**How to avoid:** This is an intentional design decision (CONTEXT.md). The screen should display current position clearly so the operator can verify all axes are in position before teaching. Add a note in the UI: "Ensure all axes are in position before teaching."
**Warning signs:** Operator teaches with only one axis positioned; other axes get new rest points.

### Pitfall 7: Parameter Validation Range — Zero-Division Risk
**What goes wrong:** CPM is derived as `ctsRevX * ratioX / pitchX`. If `pitchX = 0`, division by zero occurs.
**Why it happens:** Fresh controller setup, or user clears pitch field.
**How to avoid:** Reject zero for pitch, ratio, ctsRev at validation time (already specified in CONTEXT.md). Also reject negative values for these params.
**Warning signs:** App crashes or shows NaN in position calculations.

---

## Code Examples

Verified patterns from existing codebase:

### Reading Live Axis Position (TD command)
```python
# Source: controller.py cmd() + buttons_switches.py pattern
def _poll_tick(self, dt):
    if not self.controller or not self.controller.is_connected():
        return
    def do_poll():
        try:
            pos = {}
            for ax in ("A", "B", "C", "D"):
                resp = self.controller.cmd(f"MG _TD{ax}")
                pos[ax] = float(resp.strip())
        except Exception:
            return
        Clock.schedule_once(lambda *_, p=pos: self._update_pos_labels(p))
    jobs.submit(do_poll)
```

### Reading a Scalar DMC Variable
```python
# Source: controller.py cmd()
# For reading taught points or parameters back from controller:
resp = self.controller.cmd("MG restPtA")
value = float(resp.strip())
```

### Writing a Scalar DMC Variable
```python
# Source: controller.py cmd()
# Write single value:
self.controller.cmd("restPtA=12000.0")
# Write multiple in one command (semicolon-separated):
self.controller.cmd("restPtA=12000.0;restPtB=8500.0;restPtC=3200.0;restPtD=0.0")
```

### PR+BG Relative Jog
```python
# Source: CONTEXT.md specification — consistent with controller.py cmd()
counts = int(direction * step_mm * cpm_for_axis)
self.controller.cmd(f"PRA={counts}")  # Position Relative on A axis
self.controller.cmd("BGA")            # Begin motion on A axis only
```

### Burn Variables to NV Memory
```python
# Source: CONTEXT.md — after teach or parameter apply
self.controller.cmd("BV")
```

### Setting a Software Button Variable
```python
# Source: CONTEXT.md — quick action buttons
self.controller.cmd("swGoSetup=1")  # Signal DMC program's main loop
```

### Step Toggle Reading in Python (preferred over KV lambdas)
```python
# Source: Derived from axisDSetup.kv pattern — cleaner to centralise in Python
@property
def _current_step_mm(self) -> float:
    if self.ids.step_10mm.state == "down":
        return 10.0
    if self.ids.step_5mm.state == "down":
        return 5.0
    return 1.0
```

### Amber Border for Modified Field
```python
# Source: Derived from rest.py's red-border pattern (background_color = red)
# Amber for modified, red for invalid, normal for clean:
BORDER_NORMAL = [0.118, 0.145, 0.188, 1]   # theme.border
BORDER_AMBER  = [0.980, 0.749, 0.043, 0.9]  # amber highlight
BORDER_RED    = [0.900, 0.200, 0.200, 0.9]  # error red

def _set_field_state(self, widget, state: str) -> None:
    # widget is the outer BoxLayout container, not the TextInput
    # Update canvas border color via a Kivy property binding or canvas instruction
    pass  # Implementation depends on KV widget structure
```

### Screen Registration (already done — no changes needed)
```python
# Source: screens/__init__.py — AxesSetupScreen and ParametersScreen already exported
# Source: main.py KV_FILES — axes_setup.kv and parameters.kv already loaded
# Source: main.py build() — controller/state already injected into all screens
# No changes to __init__.py or main.py needed for registration
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate screens per axis (rest.py, start.py, axisDSetup.py) | Single unified AxesSetupScreen with sidebar | Phase 4 | Cleaner UX; simpler codebase |
| DMC arrays for taught points (RestPnt[0..2], StartPnt[0..3]) | Individual scalar DMC variables (restPtA, restPtB, etc.) | Phase 4 | Clearer semantics; no index mapping; D-axis is first-class |
| Vietnamese labels (Luu Diem Rest, Truc A) | English labels | Phase 4 complete replacement | Per project direction |
| Step toggles X1/X10/X100 (raw counts) | Step toggles 10mm/5mm/1mm (physical mm) | Phase 4 | More intuitive for setup personnel |
| Raw count jog (adjust_axis adds raw counts) | CPM-converted mm jog (PR+BG with counts per mm) | Phase 4 | Consistent physical unit across axis types |

**Deprecated/outdated:**
- `rest.py`, `start.py`, `axisDSetup.py`: Old screens remain in codebase for git history but are no longer imported. Phase 4 does NOT modify or delete them — they are dead code preserved per `STATE.md` decision: "Old screen files kept on disk (removed from imports only) to preserve git history".
- `RestPnt` and `StartPnt` array usage for taught points: Replaced by individual scalar variables in the new design.

---

## Open Questions

1. **CPM Variable Names on Controller**
   - What we know: CONTEXT.md mentions `cpmA/B/C/D` as readable from controller. `buttons_switches.py` uses `_RP{axis}` for position — format is consistent.
   - What's unclear: Whether the DMC program actually defines variables named `cpmA`, `cpmB`, `cpmC`, `cpmD`, or whether they must be derived from `ctsRevX * ratioX / pitchX`.
   - Recommendation: On `on_pre_enter`, attempt `MG cpmA` first. If it returns `?` or fails, derive from calibration params. Cache the CPM values. Log which path was taken.

2. **Software Button Variable Names**
   - What we know: CONTEXT.md suggests `swGoSetup`, `swMoreGrind`, `swLessGrind`, `swNewStone`.
   - What's unclear: The actual DMC program variable names — `swGoSetup` is a suggestion.
   - Recommendation: Use the suggested names as-is. If the DMC program doesn't respond, the failure will be visible in the error log. These can be adjusted at integration time without changing the GUI architecture.

3. **Home All Axes — DMC Command vs Software Variable**
   - What we know: "Go to Rest All" and "Go to Start All" use software variables per CONTEXT.md. "Home All Axes" is also listed as a quick action button.
   - What's unclear: Whether Home All should also use a software variable (e.g., `swHomeAll=1`) or whether it should send a raw DMC `HM ABCD; BG ABCD` command.
   - Recommendation: Use a software variable pattern for consistency with Go to Rest/Start. Name it `swHomeAll`. This keeps all motion decisions inside the DMC program's state machine.

4. **D-Axis Units — mm vs degrees**
   - What we know: CONTEXT.md says D axis pitch is deg/rev (not mm/rev), but still uses the same mm step toggle buttons with cpmD conversion.
   - What's unclear: Whether the step label should say "10mm" or "10deg" for the D axis, or a generic "Step" label.
   - Recommendation: Use a generic step size label (e.g., "10 / 5 / 1") with a unit label that changes per axis ("mm" for A/B/C, "deg" for D). Claude's discretion per CONTEXT.md.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | none detected — run from project root |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AXES-01 | AxesSetupScreen has `_selected_axis` property | unit | `pytest tests/test_axes_setup.py::test_selected_axis_property -x` | ❌ Wave 0 |
| AXES-01 | select_axis() updates `_selected_axis` | unit | `pytest tests/test_axes_setup.py::test_select_axis -x` | ❌ Wave 0 |
| AXES-02 | Position display labels exist per axis | unit | `pytest tests/test_axes_setup.py::test_position_properties -x` | ❌ Wave 0 |
| AXES-03 | jog_axis() computes correct counts from mm | unit | `pytest tests/test_axes_setup.py::test_jog_counts_calculation -x` | ❌ Wave 0 |
| AXES-03 | step_mm property returns 10/5/1 | unit | `pytest tests/test_axes_setup.py::test_step_mm -x` | ❌ Wave 0 |
| AXES-04 | teach_rest_point() calls BV after writing vars | unit (mock controller) | `pytest tests/test_axes_setup.py::test_teach_rest_burns_nv -x` | ❌ Wave 0 |
| AXES-06 | AxesSetupScreen is in Setup/Admin role tabs | integration | manual-only (requires Kivy display) | n/a |
| PARAM-01 | ParametersScreen has all required group sections | unit | `pytest tests/test_parameters.py::test_param_groups_defined -x` | ❌ Wave 0 |
| PARAM-03 | Invalid input sets field state to 'error' | unit | `pytest tests/test_parameters.py::test_invalid_input_flags_red -x` | ❌ Wave 0 |
| PARAM-04 | Modified field increments pending_count | unit | `pytest tests/test_parameters.py::test_dirty_tracking -x` | ❌ Wave 0 |
| PARAM-05 | apply_to_controller() sends all dirty values | unit (mock controller) | `pytest tests/test_parameters.py::test_apply_sends_dirty -x` | ❌ Wave 0 |
| PARAM-05 | BV is sent after apply | unit (mock controller) | `pytest tests/test_parameters.py::test_apply_burns_nv -x` | ❌ Wave 0 |
| PARAM-06 | read_from_controller() clears dirty state | unit (mock controller) | `pytest tests/test_parameters.py::test_read_clears_dirty -x` | ❌ Wave 0 |
| PARAM-07 | Operator role sets all fields to readonly | unit | `pytest tests/test_parameters.py::test_operator_readonly -x` | ❌ Wave 0 |

**Manual-only items:** AXES-06 role-gating (requires Kivy display loop); AXES-05 quick action button DMC responses (requires live controller).

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_axes_setup.py` — covers AXES-01, AXES-02, AXES-03, AXES-04
- [ ] `tests/test_parameters.py` — covers PARAM-01, PARAM-03, PARAM-04, PARAM-05, PARAM-06, PARAM-07
- [ ] Both test files follow the established pattern: `import` inside test function with `KIVY_NO_ENV_CONFIG=1` and `KIVY_LOG_LEVEL=critical` to defer Kivy initialization

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `src/dmccodegui/screens/axes_setup.py` — current placeholder
- Direct codebase inspection: `src/dmccodegui/screens/parameters.py` — current placeholder
- Direct codebase inspection: `src/dmccodegui/screens/rest.py` — established read/save pattern
- Direct codebase inspection: `src/dmccodegui/screens/start.py` — established read/save/move pattern
- Direct codebase inspection: `src/dmccodegui/screens/axisDSetup.py` — established live-jog and array pattern
- Direct codebase inspection: `src/dmccodegui/screens/buttons_switches.py` — established 10Hz polling + on_leave cancel pattern
- Direct codebase inspection: `src/dmccodegui/controller.py` — GalilController.cmd(), upload_array(), download_array() signatures
- Direct codebase inspection: `src/dmccodegui/ui/theme.kv` — CardFrame, VControl, HControl, VDivider widget definitions
- Direct codebase inspection: `src/dmccodegui/ui/axes_setup.kv` — placeholder to be replaced
- Direct codebase inspection: `src/dmccodegui/ui/parameters.kv` — placeholder to be replaced
- Direct codebase inspection: `src/dmccodegui/main.py` — KV_FILES load order, screen injection pattern
- Direct codebase inspection: `src/dmccodegui/app_state.py` — MachineState fields, setup_unlocked flag
- Direct codebase inspection: `src/dmccodegui/utils/jobs.py` — submit() and schedule() signatures
- Direct codebase inspection: `src/dmccodegui/theme_manager.py` — theme color constants
- Direct codebase inspection: `tests/` — existing test patterns (deferred Kivy init, mock controller usage)
- `.planning/phases/04-axes-setup-and-parameters/04-CONTEXT.md` — all locked decisions

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — requirements AXES-01 through AXES-06, PARAM-01 through PARAM-07
- `.planning/STATE.md` — accumulated decisions, known concerns about RestPnt → DAxisPnt rename

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all tools already in use
- Architecture: HIGH — patterns copied directly from working production screens
- Controller commands: HIGH for TD/PR/BG/BV (confirmed via existing code and CONTEXT.md); MEDIUM for software button variables (names are suggestions, not verified against DMC program source)
- Pitfalls: HIGH for on_text/loading, PR vs PA, BV scope (direct code analysis); MEDIUM for CPM variable names (depends on DMC program)

**Research date:** 2026-04-04
**Valid until:** 2026-07-04 (stable framework; 90 days before re-verification needed)
