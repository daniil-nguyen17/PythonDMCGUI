# Phase 2: RUN Page - Research

**Researched:** 2026-04-04
**Domain:** Kivy UI — live polling, toggle buttons, progress bar, custom bar-chart widget, KV layout
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Action Buttons**
- Start button: no confirmation dialog — one tap begins cycle immediately
- Start and Pause are a **single toggle button**: shows "Start" when idle, becomes "Pause" when running
- Go to Rest: always enabled; at rest position the machine waits for next command
- No E-STOP on the bottom action bar — the persistent status bar E-STOP (Phase 1) is sufficient
- Bottom bar has 3 buttons: Start/Pause (toggle), Go to Rest, and the freed space from removing E-STOP

**Cycle Status Data Source**
- All cycle status values polled from controller arrays/variables on a background thread at ~10 Hz (same rate as axis positions, single polling loop)
- **3-axis serration machines**: show current tooth, pass, depth (serration-specific fields)
- **4-axis flat/convex machines**: do NOT show tooth, pass, depth (not applicable)
- Speed removed from cycle status panel entirely
- Elapsed time and ETA: GUI-calculated from elapsed time + completion percentage
- Progress bar: shows overall cycle completion percentage
- When idle: show last values from previous cycle, greyed out

**Knife Grind Adjustment (replaces Operation Log)**
- Replaces the operation log from the mockup — no timestamped event log on the RUN page
- Operator inputs a section count (1-10) dividing the 100-element `deltaC` controller array into N equal segments
- Vertical bars laid out horizontally, each representing one section's accumulated offset from zero
- Operator taps a bar to select it, then uses up/down arrow buttons to adjust ±50 counts per press
- Apply button sends all adjusted values to the controller at once (batch update)
- IMPORTANT: deltaC array has protected indices — writable index range TBD and must be parameterized
- Reset button: TBD (depends on which indices are writable)

**Axis Position Display**
- All axes show raw encoder counts only (no unit conversion in display)
- Each axis row includes a conversion note derived from controller CPM variables (e.g., "1000 cts = 1mm"), read from cpmA, cpmB, cpmC, cpmD
- No direction arrows
- When disconnected: show "---" for all position values
- No flash/pulse on value change — smooth update at ~10 Hz
- Axis accent colors: A=orange, B=purple, C=cyan, D=yellow

### Claude's Discretion
- Exact layout proportions within the mockup grid structure
- Toggle button visual treatment (color change, icon swap for Start vs Pause state)
- Greyed-out styling for idle cycle status values
- Bar chart visual design for Knife Grind Adjustment (bar width, colors, selection highlight)
- Section count input widget style (spinner, text input, etc.)
- Polling implementation details (single loop vs separate schedulers)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RUN-01 | RUN page displays big touchscreen buttons for Start, Pause, Go to Rest, and E-STOP (all 44dp+ minimum) | Bottom bar with 3 buttons at 64dp+ height; E-STOP already in StatusBar from Phase 1 |
| RUN-02 | E-STOP button is visually dominant (red, largest target) and isolated from other controls | E-STOP lives in StatusBar (Phase 1 complete); satisfies isolation requirement by physical separation |
| RUN-03 | Live axis positions (A, B, C, D) update at ~10 Hz with color-coded labels | Clock.schedule_interval at 1/10.0; MG _TPA/B/C/D pattern from controller.py; accent colors from theme_manager |
| RUN-04 | Cycle status panel shows current tooth, pass, depth, speed, elapsed time, and ETA | Polled from controller variables; machine-type-gated display; elapsed/ETA computed in Python |
| RUN-05 | Progress bar shows overall cycle completion percentage | Kivy built-in ProgressBar widget or manual canvas fill; bound to NumericProperty |
| RUN-06 | Operation log displays timestamped events in a scrollable view | REPLACED by Knife Grind Adjustment panel per CONTEXT.md decisions |
</phase_requirements>

---

## Summary

Phase 2 builds out `RunScreen` from its current placeholder into the fully functional operator RUN page. The screen is structured as a two-column layout (left: plot placeholder + Knife Grind Adjustment; right: cycle status + axis positions) with a three-button action bar at the bottom. The `mockups/run_page.html` is the approved reference layout; `run.kv` is currently a trivial placeholder and will be fully replaced.

The project already has a mature polling pattern: `Clock.schedule_interval(fn, 1/10.0)` on `on_pre_enter`, cancelled in `on_leave` — exactly as used by `ButtonsSwitchesScreen`. All controller I/O runs on `jobs.submit()` (background thread), and UI mutations are always posted back via `Clock.schedule_once()`. This pattern must be replicated faithfully for the 10 Hz position + cycle status loop.

The Knife Grind Adjustment panel is the novel widget in this phase. It replaces the "Operation Log" from the HTML mockup and requires a custom bar-chart row where each bar represents a deltaC segment. The widget is drawn via Kivy canvas instructions — no third-party charting library is needed or appropriate. The writable index range of the `deltaC` array must be treated as a configurable constant (a module-level variable or class attribute, not a magic number) so it can be adjusted without touching logic code.

**Primary recommendation:** Reuse the `ButtonsSwitchesScreen` polling structure verbatim; build the bar chart as a custom `Widget` subclass with canvas drawing; keep all controller reads in background threads, all Label/ProgressBar updates on the main thread.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Kivy | Installed (project-wide) | Screen layout, widgets, event loop | Already the app framework |
| kivy.clock.Clock | — | `schedule_interval` for 10 Hz polling, `schedule_once` for thread-safe UI update | Established pattern in project |
| kivy.uix.progressbar.ProgressBar | — | Cycle completion percentage bar | Built-in; no custom drawing needed |
| kivy.uix.boxlayout.BoxLayout | — | Column and row layouts throughout | Standard Kivy layout |
| kivy.uix.gridlayout.GridLayout | — | Cycle status 2-column grid | Used in existing screens |
| kivy.uix.widget.Widget | — | Base for custom bar chart canvas drawing | Lightest Kivy base for custom paint |
| kivy.properties (NumericProperty, StringProperty, ListProperty, BooleanProperty) | — | Reactive data binding for live values | Established project pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| kivy.uix.togglebutton.ToggleButton | — | Start/Pause single-button toggle | Correct widget for two-state button |
| kivy.uix.scrollview.ScrollView | — | Not used this phase (no log) | Would be used if log were needed |
| kivy.graphics (Rectangle, Color, Line) | — | Custom bar chart canvas drawing | Any widget needing non-standard paint |
| jobs.submit / jobs.schedule | — | Background controller I/O | Already in use project-wide |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Canvas-drawn bar chart | matplotlib FigureCanvasKivyAgg | Matplotlib is Phase 3; overkill for static bars; adds Phase 3 dependency risk |
| ToggleButton | Two separate Button widgets with manual state | ToggleButton's `state` property ('normal'/'down') maps cleanly to idle/running |
| Clock.schedule_interval | jobs.schedule + Clock.schedule_once | Both work; schedule_interval is simpler for main-thread-safe poll triggers |

**Installation:** No new dependencies for this phase. All required widgets and utilities are already installed.

---

## Architecture Patterns

### Recommended Project Structure
```
src/dmccodegui/
├── screens/
│   └── run.py              # RunScreen class — expand from placeholder
├── ui/
│   └── run.kv              # Full RUN page KV layout — replace placeholder
```

No new files are strictly required. The single-screen approach (one `.py`, one `.kv`) matches every other screen in the project.

### Pattern 1: 10 Hz Polling Loop (established project pattern)
**What:** `Clock.schedule_interval` fires every 100ms, submits controller read to background thread, posts UI update back via `Clock.schedule_once`.
**When to use:** Any live data on this screen — axis positions AND cycle status share one loop.
**Example:**
```python
# From screens/buttons_switches.py — replicate this exactly
def on_pre_enter(self, *args):
    self._update_clock_event = Clock.schedule_interval(self._update_clock, 1 / 10.0)

def on_leave(self, *args):
    if self._update_clock_event:
        self._update_clock_event.cancel()
        self._update_clock_event = None

def _update_clock(self, dt):
    if not self.controller or not self.controller.is_connected():
        return
    def do_read():
        try:
            pos = {}
            for axis in ['A', 'B', 'C', 'D']:
                resp = self.controller.cmd(f"MG _TP{axis}")
                pos[axis] = float(resp.strip())
            cycle = self._read_cycle_status()
            Clock.schedule_once(lambda *_: self._apply_ui(pos, cycle))
        except Exception as e:
            Clock.schedule_once(lambda *_: self._show_disconnected())
    jobs.submit(do_read)
```

### Pattern 2: ToggleButton for Start/Pause
**What:** `ToggleButton` with `state` property — `'normal'` = idle (shows "Start"), `'down'` = running (shows "Pause").
**When to use:** The single Start/Pause button in the bottom action bar.
**Example:**
```python
# KV binding — text and color change reactively from state
ToggleButton:
    id: start_pause_btn
    text: 'PAUSE' if self.state == 'down' else 'START'
    background_color: (0.47, 0.25, 0.06, 1) if self.state == 'down' else (0.09, 0.40, 0.20, 1)
    size_hint_y: None
    height: '64dp'
    on_release: root.on_start_pause_toggle(self.state)
```
**Python handler:**
```python
def on_start_pause_toggle(self, new_state):
    if new_state == 'down':  # just went to 'down' = Start was pressed
        self._start_cycle()
    else:                    # just went to 'normal' = Pause was pressed
        self._pause_cycle()
```

### Pattern 3: Custom Bar Chart Widget (canvas instructions)
**What:** A `Widget` subclass that draws horizontal bars using `Rectangle` canvas instructions; redraws on property change.
**When to use:** Knife Grind Adjustment panel.
**Example:**
```python
from kivy.uix.widget import Widget
from kivy.properties import ListProperty, NumericProperty
from kivy.graphics import Color, Rectangle

class DeltaCBarChart(Widget):
    """Draws N vertical bars representing deltaC offsets."""
    offsets = ListProperty([])       # list of float offsets, one per section
    selected_index = NumericProperty(-1)  # -1 = none selected
    MAX_OFFSET = NumericProperty(500)

    def on_offsets(self, *args):
        self.draw()

    def on_selected_index(self, *args):
        self.draw()

    def on_size(self, *args):
        self.draw()

    def draw(self):
        self.canvas.clear()
        if not self.offsets:
            return
        n = len(self.offsets)
        bar_w = self.width / n
        mid_y = self.height / 2
        with self.canvas:
            for i, offset in enumerate(self.offsets):
                # bar height proportional to offset
                bar_h = abs(offset) / self.MAX_OFFSET * (self.height / 2)
                bar_h = max(bar_h, 2)
                color = (1.0, 0.65, 0.0, 1) if i == self.selected_index else (0.23, 0.51, 0.96, 1)
                Color(*color)
                if offset >= 0:
                    Rectangle(pos=(self.x + i * bar_w + 2, mid_y),
                               size=(bar_w - 4, bar_h))
                else:
                    Rectangle(pos=(self.x + i * bar_w + 2, mid_y - bar_h),
                               size=(bar_w - 4, bar_h))
```

### Pattern 4: Greyed-out Idle Values
**What:** When no cycle is running (`running == False`), apply reduced opacity to cycle status labels.
**When to use:** All cycle status fields (tooth, pass, depth, elapsed, ETA, progress bar).
**Example:**
```python
# In KV — opacity bound to RunScreen property
Label:
    id: lbl_tooth
    text: root.cycle_tooth
    opacity: 1.0 if root.cycle_running else 0.4
    color: 0.235, 0.639, 0.996, 1  # highlight blue
```

### Pattern 5: CPM Conversion Note
**What:** Read `cpmA`, `cpmB`, `cpmC`, `cpmD` from the controller once on `on_pre_enter`, display as a sub-label below each axis position.
**When to use:** Axis position rows in the right column.
**Example:**
```python
def _read_cpm_values(self):
    """Read counts-per-mm/degree for each axis. Called once on enter."""
    cpm = {}
    for axis in ['A', 'B', 'C', 'D']:
        try:
            resp = self.controller.cmd(f"MG cpm{axis}")
            cpm[axis] = float(resp.strip())
        except Exception:
            cpm[axis] = None
    return cpm

def _format_cpm_note(self, axis, cpm_val):
    if cpm_val is None or cpm_val == 0:
        return ""
    return f"{int(cpm_val)} cts = 1 unit"
```

### Pattern 6: MachineState Extension for Cycle Data
**What:** Add cycle-specific fields to `MachineState` with dataclass defaults.
**When to use:** Planner must decide which new fields to add.
**Required new fields (serration-specific, shown only on 3-axis):**
- `cycle_tooth: int = 0`
- `cycle_pass: int = 0`
- `cycle_depth: float = 0.0`
- `cycle_elapsed_s: float = 0.0`  (seconds, float for ETA calculation)
- `cycle_completion_pct: float = 0.0`  (0.0 to 100.0, for progress bar)
- `cycle_running: bool = False`

All new fields use dataclass `field(default=...)` to preserve backward compatibility (as established in Phase 1 decisions).

### Recommended Project Structure (KV layout)
```
RunScreen (BoxLayout vertical, fills ScreenManager)
└── BoxLayout (horizontal, flex=1)          ← main content area
    ├── BoxLayout (vertical, size_hint_x: 0.6)   ← left column
    │   ├── CardFrame (flex=1)                    ← plot placeholder
    │   └── CardFrame (size_hint_y: None, height: ~240dp)  ← Knife Grind Adjustment
    └── BoxLayout (vertical, size_hint_x: 0.4)   ← right column
        ├── CardFrame (size_hint_y: None)         ← Cycle Status + ProgressBar
        └── CardFrame (flex=1)                    ← Axis Positions
└── BoxLayout (horizontal, size_hint_y: None, height: '72dp')  ← bottom action bar
    ├── ToggleButton (flex=1)                     ← Start / Pause
    └── Button (flex: 0.6)                        ← Go to Rest
```

### Anti-Patterns to Avoid
- **Calling controller.cmd() on the main thread inside _update_clock:** Always wrap in `jobs.submit()`. The main thread handles Kivy events only.
- **Using `Clock.schedule_interval` and forgetting `on_leave` cancel:** Leaves a zombie loop that polls forever. Every `schedule_interval` must have a paired cancel.
- **Hard-coding the deltaC writable index range:** Use a module-level constant (e.g., `DELTA_C_WRITABLE_START = 0; DELTA_C_WRITABLE_END = 99`) so it can be changed without touching logic.
- **Starting the poll loop when disconnected:** Guard every `_update_clock` callback with `if not self.controller or not self.controller.is_connected(): return`.
- **Using `download_array` with all 100 indices on every Apply press:** Only write the writable range, not indices 0..99 blindly — protected indices must not be touched.
- **Using `ToggleButton` group property for Start/Pause:** Do not assign a group; the button is standalone state, not part of a radio group.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Two-state button | Manual bool flag + two Button swap | `ToggleButton` with `state` property | Built-in Kivy; KV text binding is reactive automatically |
| Progress bar fill | Manual canvas Rectangle scaled to width | `kivy.uix.progressbar.ProgressBar` | Built-in; handles boundary, accessibility, theming |
| Background thread for controller I/O | `threading.Thread` inline | `jobs.submit()` from `utils/jobs.py` | Project-standard pool; already handles errors |
| Periodic timer | `threading.Timer` | `Clock.schedule_interval` | Main-thread-safe; cancellable; already used everywhere |
| Scrollable list | Manual widget stack | `ScrollView` wrapping a `GridLayout` | Built-in; handles touch fling and overscroll |

**Key insight:** The controller I/O and UI update threading contract is already fully established in this codebase. Following it exactly is more important than any individual widget choice.

---

## Common Pitfalls

### Pitfall 1: ToggleButton State Direction
**What goes wrong:** `on_release` fires after state has already flipped. Checking `self.state` inside `on_release` gives the NEW state, not the old state. This is the expected Kivy behavior but surprises developers.
**Why it happens:** Kivy flips `ToggleButton.state` before firing `on_release`.
**How to avoid:** In the `on_release` handler, read `self.state` — it reflects the state the button just flipped TO. `'down'` = user just pressed Start. `'normal'` = user just pressed Pause.
**Warning signs:** Start and Pause logic are inverted in behavior.

### Pitfall 2: Clock Event Not Cancelled on Leave
**What goes wrong:** Navigating away from RunScreen does not stop the 10 Hz loop. Controller gets polled forever; if controller disconnects, errors flood the console.
**Why it happens:** `Clock.schedule_interval` returns a `ClockEvent` that persists until explicitly cancelled.
**How to avoid:** Always store the event in `self._poll_event` and cancel it in `on_leave`. Check `ButtonsSwitchesScreen` for the exact pattern.
**Warning signs:** Errors appearing in console when on a different screen; CPU usage not dropping after navigation.

### Pitfall 3: Canvas Not Redrawn on Widget Resize
**What goes wrong:** The custom bar chart looks correct at first render but does not redraw when the window is resized or when the screen is first entered after another screen hid it.
**Why it happens:** Kivy canvas instructions are not automatically re-executed when widget size changes unless explicitly bound.
**How to avoid:** Bind `on_size` (and `on_pos` if needed) to the draw method. Also bind to the data property (`on_offsets`).
**Warning signs:** Bars disappear or remain stale after resize or screen switch.

### Pitfall 4: deltaC Apply Overwrites Protected Indices
**What goes wrong:** Writing the full 100-element array reconstructed from UI bars corrupts protected controller array slots.
**Why it happens:** The writable range is not yet defined (TBD in CONTEXT.md). If the planner writes all 100 indices assuming all are writable, it will overwrite protected values on the controller.
**How to avoid:** The `DELTA_C_WRITABLE_START` / `DELTA_C_WRITABLE_END` constants must be used to slice the write. The Apply button only writes `deltaC[WRITABLE_START..WRITABLE_END]`. Leave these as named constants so they can be changed when the real range is confirmed.
**Warning signs:** Machine behaves unexpectedly after Knife Grind Adjustment apply; controller program errors.

### Pitfall 5: ETA Calculation Division by Zero
**What goes wrong:** If `cycle_completion_pct` is 0.0 and elapsed time is nonzero, dividing elapsed by percentage to estimate ETA causes ZeroDivisionError or infinite ETA.
**Why it happens:** Cycle has just started; completion is 0 but time has already elapsed.
**How to avoid:** Guard ETA calculation: `if pct > 1.0: eta = elapsed / pct * (100 - pct)` else show `"--:--"`.
**Warning signs:** Crash or "inf" displayed in ETA field at cycle start.

### Pitfall 6: CPM Read Fails Silently for Unused Axes
**What goes wrong:** On a 3-axis machine, reading `cpmD` throws because D axis variable does not exist on the controller.
**Why it happens:** Machine type is not yet enforced in this phase (Phase 6). CPM variables may only be defined for axes that exist on the controller program.
**How to avoid:** Wrap each CPM read in try/except; fall back to `cpm[axis] = None` and show no conversion note for that axis.
**Warning signs:** On-enter error toast for a specific axis on certain machines.

---

## Code Examples

Verified patterns from existing project code:

### Axis Position Read (from controller.py read_status)
```python
# Source: src/dmccodegui/controller.py read_status()
for axis in ['A', 'B', 'C', 'D']:
    try:
        resp = self.cmd(f"MG _TP{axis}")
        pos[axis] = float(resp.strip())
    except Exception:
        pos[axis] = 0.0
```

### 10 Hz Poll Start/Stop (from buttons_switches.py)
```python
# Source: src/dmccodegui/screens/buttons_switches.py
_update_clock_event = None

def on_pre_enter(self, *args):
    if self._update_clock_event:
        self._update_clock_event.cancel()
    self._update_clock_event = Clock.schedule_interval(self._update_clock, 1 / 10.0)

def on_leave(self, *args):
    if self._update_clock_event:
        self._update_clock_event.cancel()
        self._update_clock_event = None

def _update_clock(self, dt):
    if not self.controller or not self.controller.is_connected():
        return
    jobs.submit(self._do_poll)
```

### Background Read + UI Update (established pattern)
```python
# Source: all existing screens — controller I/O in jobs.submit, UI in Clock.schedule_once
def _do_poll(self):
    try:
        value = self.controller.cmd("MG some_var")
        Clock.schedule_once(lambda *_: self._apply_value(float(value)))
    except Exception as e:
        Clock.schedule_once(lambda *_: self._show_error(str(e)))
```

### Array Write (batch, from controller.py download_array)
```python
# Source: src/dmccodegui/controller.py download_array()
# Write writable slice of deltaC to controller
def _apply_delta_c(self, offsets, writable_start, writable_end):
    def do_write():
        try:
            values = self._offsets_to_delta_c(offsets, writable_start, writable_end)
            self.controller.download_array("deltaC", writable_start, values)
        except Exception as e:
            Clock.schedule_once(lambda *_: self._alert(str(e)))
    jobs.submit(do_write)
```

### Disconnected Placeholder Display (pattern to use for "---")
```python
# Pattern: check state.connected before displaying; show "---" when False
def _apply_positions(self, pos):
    if not self.state.connected:
        for axis in ['A', 'B', 'C', 'D']:
            label = self.ids.get(f"pos_{axis.lower()}")
            if label:
                label.text = "---"
        return
    for axis, val in pos.items():
        label = self.ids.get(f"pos_{axis.lower()}")
        if label:
            label.text = f"{int(val):,}"
```

### ProgressBar in KV
```python
# Kivy built-in ProgressBar
ProgressBar:
    id: cycle_progress
    min: 0
    max: 100
    value: root.cycle_completion_pct
    size_hint_y: None
    height: '8dp'
```

### CardFrame Usage (from theme.kv)
```kv
# Source: src/dmccodegui/ui/theme.kv
CardFrame:
    orientation: 'vertical'
    padding: '10dp'
    spacing: '10dp'
    # CardFrame draws bg_panel background + rounded border automatically
    Label:
        text: 'Card Header'
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Old screens (rest.py, start.py) do controller reads synchronously on pre-enter | Phase 1+ screens use jobs.submit for all I/O | Phase 1 | RunScreen must follow jobs.submit pattern |
| ButtonsSwitchesScreen has separate refresh+poll loops | Single combined poll loop is preferred | Phase 2 target | RUN page should use one loop for both positions and cycle status |
| MachineState had no auth fields | Phase 1 added current_user, current_role, setup_unlocked with defaults | Phase 1 complete | Any new MachineState fields must also use dataclass defaults |

**Deprecated/outdated:**
- Synchronous controller reads in `on_pre_enter` (rest.py/start.py pattern): do not replicate for the poll loop. On-enter one-shot reads (e.g., CPM values) can still be synchronous if they are brief and non-recurring.

---

## Open Questions

1. **deltaC Writable Index Range**
   - What we know: The 100-element `deltaC` array has protected indices; the exact writable range is TBD
   - What's unclear: Which indices are safe to write; whether there are read-only sentinel values at specific positions
   - Recommendation: Use named constants `DELTA_C_WRITABLE_START = 0` and `DELTA_C_WRITABLE_END = 99` as placeholders; document them prominently in the code for easy configuration when the real range is confirmed

2. **Cycle Status Controller Variables (serration)**
   - What we know: Tooth, pass, depth are polled from controller; exact variable/array names not specified
   - What's unclear: Are these individual variables (e.g., `MG tooth`, `MG pass`) or elements of a status array?
   - Recommendation: Implement as `controller.cmd("MG <varname>")` with configurable variable name constants; use the same try/except/fallback pattern as position reads

3. **Cycle Completion Percentage Source**
   - What we know: Progress bar shows overall cycle completion; ETA is GUI-calculated from elapsed + completion %
   - What's unclear: Is completion percentage a controller variable or GUI-computed from tooth/total-teeth ratio?
   - Recommendation: If controller provides a variable, read it; otherwise compute as `(current_tooth / total_teeth) * 100` where total teeth is also read from controller

4. **Machine Type Detection (Phase 6 pending)**
   - What we know: 3-axis serration machines show tooth/pass/depth; 4-axis machines do not; machine type is hard-coded at deployment
   - What's unclear: How will RunScreen know its machine type before Phase 6 (Machine Types)?
   - Recommendation: Add a module-level constant `MACHINE_TYPE = "4axis_flat"` (or read from a config constant) that RunScreen checks when deciding which cycle status fields to show; Phase 6 will replace this constant

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing — tests/ directory with conftest.py) |
| Config file | none — runs with `pytest` from project root |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RUN-01 | Bottom bar has Start/Pause toggle + Go to Rest, both 44dp+ | manual-only — Kivy widget size requires running UI | N/A | N/A |
| RUN-02 | E-STOP is in StatusBar (Phase 1), not on RunScreen bottom bar | unit — verify RunScreen has no `e_stop` button in KV | `pytest tests/test_run_screen.py::test_no_estop_in_run_bar -x` | ❌ Wave 0 |
| RUN-03 | Axis positions update every ~100ms; "---" when disconnected | unit — mock controller, tick Clock | `pytest tests/test_run_screen.py::test_axis_positions_disconnected -x` | ❌ Wave 0 |
| RUN-04 | Cycle status fields present; serration fields hidden on 4-axis | unit — check MachineState fields and visibility logic | `pytest tests/test_run_screen.py::test_cycle_status_machine_type -x` | ❌ Wave 0 |
| RUN-05 | ProgressBar value tracks cycle_completion_pct; ETA guarded vs div-by-zero | unit — set pct=0 and pct=50, check ETA output | `pytest tests/test_run_screen.py::test_progress_and_eta -x` | ❌ Wave 0 |
| RUN-06 (replaced) | Knife Grind Adjustment: sections 1-10; bar taps; ±50 per press; Apply batch-writes | unit — DeltaCBarChart logic; Apply with mock controller | `pytest tests/test_run_screen.py::test_delta_c_adjustment -x` | ❌ Wave 0 |

**Manual-only justifications:**
- RUN-01: Pixel/dp dimensions require a live Kivy window; cannot be verified in headless pytest without additional test harness
- Full layout fidelity: All widget sizing and visual styling is verified by operator review against `mockups/run_page.html`

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_run_screen.py` — covers RUN-02, RUN-03, RUN-04, RUN-05, RUN-06 (Knife Grind)
- [ ] `tests/test_delta_c_bar_chart.py` — unit tests for `DeltaCBarChart` widget logic (offset math, section division, writable range)
- [ ] `tests/test_machine_state_cycle.py` — covers new cycle fields on MachineState (cycle_tooth, cycle_running, cycle_completion_pct, ETA calculation)

Note: Kivy-free pure-logic tests (MachineState, DeltaCBarChart math) can run headless. Screen/widget integration tests that require Kivy event loop will need `KIVY_NO_ENV_CONFIG=1` and appropriate mocking or should be marked as manual.

---

## Sources

### Primary (HIGH confidence)
- `src/dmccodegui/screens/buttons_switches.py` — definitive 10 Hz poll pattern: `Clock.schedule_interval`, `jobs.submit`, `on_leave` cancel
- `src/dmccodegui/controller.py` — `cmd()`, `upload_array()`, `download_array()` API surface; `MG _TP{axis}` position read pattern
- `src/dmccodegui/app_state.py` — `MachineState` dataclass; `update_status()`, `subscribe/notify` pattern; Phase 1 auth field extension pattern
- `src/dmccodegui/ui/theme.kv` — `CardFrame`, `VControl`, `HControl`, all shared composite widgets; accent colors
- `src/dmccodegui/main.py` — screen injection pattern; `Clock.schedule_once` for UI updates; `e_stop()` is on `DMCApp`, not screens
- `src/dmccodegui/ui/status_bar.kv` — E-STOP button is in StatusBar (satisfies RUN-02 isolation)
- `mockups/run_page.html` — approved two-column + bottom-bar grid layout reference
- `src/dmccodegui/theme_manager.py` — exact RGBA values for all theme colors; axis accent colors are per-CONTEXT (not in ThemeManager, applied inline)

### Secondary (MEDIUM confidence)
- Kivy official docs on `ToggleButton.state` property: 'normal'/'down' semantics and when `on_release` fires relative to state flip — consistent with observed project usage
- Kivy official docs on `ProgressBar`: `min`, `max`, `value` properties; no animation needed (value binding drives smooth update at 10 Hz)
- Kivy canvas instructions (`Rectangle`, `Color`, `Line` in `with self.canvas`) for custom `Widget` drawing: verified by existing project use of canvas in `CardFrame` and `StatusBar` dot

### Tertiary (LOW confidence)
- None — all findings are grounded in project source or established Kivy APIs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are already installed and used in the project
- Architecture: HIGH — patterns copied directly from existing screen implementations; no novel patterns introduced
- Pitfalls: HIGH — ToggleButton state direction and Clock cancel are verified Kivy behaviors; deltaC protection pitfall documented from CONTEXT.md warning
- Validation: MEDIUM — test file paths are projections (files don't exist yet); Wave 0 work required before implementation

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable Kivy APIs; only re-research if Kivy version is upgraded)
