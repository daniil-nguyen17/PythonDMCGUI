# Phase 3: Live Matplotlib Plot — Research

**Researched:** 2026-04-04
**Domain:** matplotlib embedded in Kivy, rolling buffer, live plot update pattern
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Plot Visual Design**
- Continuous line trail tracing A (X-axis) vs B (Y-axis) positions
- Single bright high-contrast color on dark background (Claude picks exact color)
- Plot background matches app theme (BG_PANEL) with tick/label colors matching text_mid
- Minimal axis ticks only — no grid lines, no axis labels beyond numeric tick values
- No current-position dot or marker — just the line

**History Buffer and Trail**
- Rolling buffer of 500-1000 position samples (Claude picks exact size)
- Hard clip when buffer is full — oldest points simply disappear, no fade/alpha
- Trail clears automatically when operator taps Start (cycle begin)
- Plot updates ONLY during active cycles — static/blank when idle (saves Pi resources)

**Viewport Behavior**
- Auto-scale axes to fit all visible trail data with padding
- Equal aspect ratio (1:1 scaling) so grinding path shape is geometrically accurate
- No operator interaction — display only, no zoom, no pan, no tap handlers
- No touch event handlers on the plot widget (avoids interfering with E-STOP or other buttons)

**Performance Strategy**
- Target 5 Hz plot update rate (every 200ms), decoupled from the 10 Hz position polling
- Named constant `PLOT_UPDATE_HZ = 5` at top of file alongside other constants
- All matplotlib rendering on the main Kivy thread (FigureCanvasKivyAgg requirement)
- Position data collected on background thread (existing pattern), only draw call on main thread
- CRITICAL: Polling is read-only for display data (axis positions). Never use polling to send commands to the controller.
- Skip Pi performance validation for now — build for Windows first, validate on Pi during Phase 8
- Document tuning points: Add comments at PLOT_UPDATE_HZ constant and buffer size explaining how to adjust for Pi performance testing
- No FPS counter or debug overlay in production — clean display only
- Pi fallback: If matplotlib proves too slow on Pi, the fallback is switching to Kivy Canvas drawing (like DeltaCBarChart) — drop matplotlib entirely for native GPU acceleration

### Claude's Discretion
- Exact bright trail color choice (something that reads well on BG_PANEL dark background)
- Exact buffer size within the 500-1000 range
- Line width for the trail
- Tick mark density and formatting
- Padding amount for auto-scale viewport
- Whether to use draw_idle() or fig.canvas.draw() for the redraw call
- Exact integration with the existing _do_poll / _apply_ui flow (separate Clock.schedule_interval for plot vs reusing poll cycle)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RUN-07 | Live matplotlib plot shows top-down A/B axis positions in real-time with rolling buffer | MatplotFigure widget from kivy-matplotlib-widget provides the Kivy-compatible canvas; rolling deque buffer + Clock.schedule_interval at 5 Hz drives updates on main thread |
</phase_requirements>

---

## Summary

This phase embeds a live A/B position line-trail plot into the existing RUN page placeholder (left column, full height). The data source is already flowing: `RunScreen._do_poll()` reads A/B positions at 10 Hz and posts them to `_apply_ui()` on the Kivy main thread. The only new work is (1) adding a plot widget to the KV layout, (2) accumulating positions in a rolling deque, and (3) triggering a redraw on a separate 5 Hz clock.

The critical integration discovery from actual environment inspection: `matplotlib.backends.backend_kivyagg` does **not** ship with matplotlib 3.10.8 (the version installed in this project). The correct package is `kivy-matplotlib-widget` (v0.16.0, released 2025-10-17), which provides `MatplotFigure` from `kivy_matplotlib_widget.uix.graph_widget`. This widget accepts `widget.figure = fig` to attach a matplotlib `Figure`, and redraw is triggered by `fig.canvas.draw_idle()`. The package is already installed in the project environment.

Touch interception is the main safety concern: `MatplotFigure` has built-in pan/zoom gesture handling. Since the operator must never accidentally trigger a pan/zoom gesture instead of an E-STOP tap, touch interaction must be fully disabled on this widget by setting `do_pan_x`, `do_pan_y`, `do_scale`, and `touch_mode` properties to their inactive values, or by subclassing to swallow/ignore all touch events.

**Primary recommendation:** Use `MatplotFigure` (kivy-matplotlib-widget 0.16.0) with `touch_mode='none'`, attach the figure via `widget.figure = fig` in `on_kv_post`, feed data through `_apply_ui`, and call `fig.canvas.draw_idle()` on a separate `Clock.schedule_interval` at 5 Hz.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| matplotlib | 3.10.8 (installed) | Figure/Axes/line2D — the actual plot | Already installed; only charting library with a Kivy-compatible canvas widget |
| kivy-matplotlib-widget | 0.16.0 (installed) | `MatplotFigure` — Kivy widget that renders a matplotlib Figure | `matplotlib.backends.backend_kivyagg` is absent from matplotlib 3.10.8; this is the maintained replacement; confirmed importable in this environment |
| kivy.clock (Clock) | bundled with Kivy 2.3.1 | `Clock.schedule_interval` — drives 5 Hz redraw separate from 10 Hz poll | Already used throughout the codebase for all periodic callbacks |
| collections.deque | stdlib | Fixed-capacity rolling buffer for position history | O(1) appendleft/pop; `maxlen` parameter gives free hard-clip at buffer capacity |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| matplotlib.figure.Figure | 3.10.8 | Direct Figure construction (no pyplot) | Use `Figure()` not `plt.subplots()` — avoids pyplot global state and thread-safety issues when the figure is created before Kivy's event loop starts |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| kivy-matplotlib-widget MatplotFigure | matplotlib.backends.backend_kivyagg.FigureCanvasKivyAgg | backend_kivyagg is NOT present in matplotlib 3.10.8 on this system — confirmed ModuleNotFoundError at import; cannot use |
| kivy-matplotlib-widget MatplotFigure | Kivy Canvas drawing (DeltaCBarChart pattern) | No matplotlib dep; lower rendering overhead on Pi; but requires hand-rolling line drawing, axis ticks, auto-scale — significant extra code. Documented as the Phase 8 Pi fallback if matplotlib proves too slow |
| kivy-matplotlib-widget MatplotFigure | kivy.garden.matplotlib | garden.matplotlib has 30 open unresolved issues, no active PRs; consider unmaintained |
| collections.deque | plain Python list with slice | deque(maxlen=N) auto-discards oldest items; list requires manual slicing every update |

**Installation (already installed):**
```bash
# Both are already present — no install step needed
pip install "matplotlib>=3.10" "kivy-matplotlib-widget>=0.16.0"
```

Add to pyproject.toml dependencies:
```toml
dependencies = [
  "kivy>=2.2.0",
  "matplotlib>=3.8",
  "kivy-matplotlib-widget>=0.16.0",
]
```

---

## Architecture Patterns

### Recommended Project Structure

No new files needed. All changes are within existing files:

```
src/dmccodegui/
├── screens/run.py          # Add: PLOT_UPDATE_HZ constant, _plot_buf_x/y deques,
│                           #       _plot_clock_event, _init_plot(), _tick_plot(),
│                           #       clear trail in on_start_pause_toggle()
├── ui/run.kv               # Replace: plot placeholder Label with MatplotFigure widget
└── (pyproject.toml)        # Add: matplotlib and kivy-matplotlib-widget deps
```

### Pattern 1: Widget Initialization in on_kv_post

**What:** Create the matplotlib Figure and Axes, configure visual style, assign to MatplotFigure widget.
**When to use:** Only once, after KV ids are available. `on_kv_post` fires after KV binding, before `on_pre_enter`.

```python
# Source: kivy_matplotlib_widget.uix.graph_widget.MatplotFigure (inspected 2026-04-04)
# Import at module top — lazy import avoids premature Kivy context issues
from matplotlib.figure import Figure
from kivy_matplotlib_widget.uix.graph_widget import MatplotFigure  # noqa: F401  (also registers KV Factory)
import kivy_matplotlib_widget  # registers MatplotFigure in Kivy Factory

# In run.py constants section:
PLOT_UPDATE_HZ = 5  # Hz — tuning point: lower to 2-3 if Pi CPU load is too high
PLOT_BUFFER_SIZE = 750  # points — tuning point: reduce to 300 if Pi memory is constrained

# In RunScreen.on_kv_post():
def on_kv_post(self, base_widget) -> None:
    # ... existing delta_c_chart binding ...

    plot_wgt = self.ids.get("ab_plot")
    if plot_wgt is not None:
        self._fig = Figure(figsize=(4, 3), facecolor=BG_PANEL_HEX)
        self._ax = self._fig.add_subplot(111)
        self._configure_axes()
        self._plot_line, = self._ax.plot([], [], color="#7DF9FF", linewidth=1.2)
        plot_wgt.figure = self._fig
        # Disable all touch interaction — preserves E-STOP responsiveness
        plot_wgt.do_pan_x = False
        plot_wgt.do_pan_y = False
        plot_wgt.do_scale = False
        plot_wgt.touch_mode = 'none'
        plot_wgt.disable_mouse_scrolling = True
```

### Pattern 2: Rolling Buffer + _apply_ui Integration

**What:** Collect A/B raw float values from the poll result into a fixed-capacity deque; redraw happens on a separate clock, not every poll cycle.
**When to use:** Inside `_apply_ui()` which already runs on the Kivy main thread.

```python
# In RunScreen.__init__ or class body:
from collections import deque
_plot_buf_x: deque  # initialized in on_kv_post or __init__
_plot_buf_y: deque

# Initialized:
self._plot_buf_x = deque(maxlen=PLOT_BUFFER_SIZE)
self._plot_buf_y = deque(maxlen=PLOT_BUFFER_SIZE)

# In _apply_ui(), after updating pos_a/pos_b strings:
if self.cycle_running:
    raw_a = pos.get("A")
    raw_b = pos.get("B")
    if raw_a is not None and raw_b is not None:
        self._plot_buf_x.append(float(raw_a))
        self._plot_buf_y.append(float(raw_b))
```

### Pattern 3: Separate 5 Hz Plot Clock

**What:** A second `Clock.schedule_interval` fires at 5 Hz to do the actual matplotlib redraw. This decouples the expensive draw call from the 10 Hz poll, leaving every other poll cycle free for E-STOP responsiveness.
**When to use:** Started in `on_pre_enter`, cancelled in `on_leave` alongside `_update_clock_event`.

```python
# Source: Kivy Clock documentation pattern + project convention (on_pre_enter/on_leave pattern)
def on_pre_enter(self, *args) -> None:
    self._show_disconnected()
    # Start 10 Hz position poll
    self._update_clock_event = Clock.schedule_interval(self._update_clock, 1.0 / POLL_HZ)
    # Start 5 Hz plot redraw (separate from poll to protect E-STOP latency)
    self._plot_clock_event = Clock.schedule_interval(self._tick_plot, 1.0 / PLOT_UPDATE_HZ)

def on_leave(self, *args) -> None:
    if self._update_clock_event:
        self._update_clock_event.cancel()
        self._update_clock_event = None
    if self._plot_clock_event:
        self._plot_clock_event.cancel()
        self._plot_clock_event = None

def _tick_plot(self, dt: float) -> None:
    """5 Hz Kivy clock: redraw the A/B position trail. Main thread only."""
    if not self.cycle_running:
        return  # No update when idle — saves Pi CPU
    xs = list(self._plot_buf_x)
    ys = list(self._plot_buf_y)
    if len(xs) < 2:
        return
    self._plot_line.set_data(xs, ys)
    self._ax.relim()
    self._ax.autoscale_view()
    self._fig.canvas.draw_idle()
```

### Pattern 4: Trail Clear on Cycle Start

**What:** When operator taps Start, clear the deques and reset the axes.
**When to use:** Inside existing `on_start_pause_toggle()` where `btn_state == "down"`.

```python
# Inside on_start_pause_toggle(), btn_state == "down" branch:
self._plot_buf_x.clear()
self._plot_buf_y.clear()
if hasattr(self, '_plot_line') and self._plot_line is not None:
    self._plot_line.set_data([], [])
    self._fig.canvas.draw_idle()
```

### Pattern 5: Axes Styling to Match App Theme

**What:** Set axes background, tick colors, and spine colors to match the BG_PANEL / text_mid theme. No grid, no labels, minimal ticks.

Theme values (from `theme_manager.py`, confirmed):
- `bg_panel` = `[0.051, 0.071, 0.102, 1]` → hex `#0D1219`
- `text_mid` = `[0.580, 0.631, 0.710, 1]` → hex `#94A1B5`

```python
BG_PANEL_HEX = "#0D1219"   # matches theme.bg_panel
TICK_COLOR = "#94A1B5"     # matches theme.text_mid
TRAIL_COLOR = "#7DF9FF"    # electric cyan — high contrast on dark navy; distinct from axis accent colors

def _configure_axes(self) -> None:
    ax = self._ax
    self._fig.patch.set_facecolor(BG_PANEL_HEX)
    ax.set_facecolor(BG_PANEL_HEX)
    ax.set_aspect("equal", adjustable="datalim")
    ax.tick_params(colors=TICK_COLOR, labelsize=7, length=3, width=0.5)
    for spine in ax.spines.values():
        spine.set_edgecolor(TICK_COLOR)
        spine.set_linewidth(0.5)
    ax.xaxis.set_major_locator(plt.MaxNLocator(nbins=4, integer=True))
    ax.yaxis.set_major_locator(plt.MaxNLocator(nbins=4, integer=True))
    ax.grid(False)
    self._fig.tight_layout(pad=0.4)
```

### KV Layout Change

Replace the plot placeholder in `run.kv` lines 33-56 (the BoxLayout with Label "Live Position — A / B Axes"):

```kv
#:import kivy_matplotlib_widget kivy_matplotlib_widget  # triggers Factory registration

# In LEFT COLUMN, replace the plot placeholder BoxLayout with:
MatplotFigure:
    id: ab_plot
    size_hint_y: 1
    do_pan_x: False
    do_pan_y: False
    do_scale: False
    touch_mode: 'none'
```

Note: The `#:import kivy_matplotlib_widget kivy_matplotlib_widget` line at the top of run.kv, combined with `import kivy_matplotlib_widget` in run.py, ensures the `MatplotFigure` class is registered in the Kivy Factory before the KV builder processes the `MatplotFigure:` rule.

### Anti-Patterns to Avoid

- **Calling `fig.canvas.draw()` (blocking) instead of `draw_idle()` (async):** `draw()` blocks the Kivy event loop synchronously; `draw_idle()` queues the redraw and returns immediately. Always use `draw_idle()`.
- **Doing matplotlib work in `_do_poll()` background thread:** `_do_poll` runs in a `jobs.submit()` thread. Any matplotlib call there — including `ax.set_data()` — is a threading violation. Position data appends to the deque in `_apply_ui()` (main thread), and drawing happens in `_tick_plot()` (main thread clock).
- **Using `plt.subplots()`:** `plt.subplots()` touches matplotlib's global pyplot state. Use `Figure()` + `fig.add_subplot(111)` directly to avoid pyplot's internal thread state and show/close machinery.
- **Updating the plot when `cycle_running is False`:** The clock fires even when idle; the `_tick_plot` guard `if not self.cycle_running: return` prevents wasted redraws when the machine is stopped.
- **Forgetting to cancel `_plot_clock_event` in `on_leave`:** The plot clock must be cancelled alongside `_update_clock_event` — a dangling clock referencing a screen that is no longer active causes KeyErrors and potential crashes.
- **Equal aspect ratio with very small or empty buffer:** `ax.set_aspect("equal")` with no data can emit a matplotlib warning and occasionally produce a degenerate axis range. Guard `_tick_plot` with `if len(xs) < 2: return`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rendering a line plot inside a Kivy widget | Custom Kivy Canvas line-drawing with manual scale calculation | matplotlib `Figure` + `MatplotFigure` | Auto-scale, equal aspect, proper floating-point coordinate mapping; the hand-rolled canvas version (DeltaCBarChart) would need ~300 lines of coordinate math to match |
| Fixed-capacity sliding window for position history | Plain list with `list = list[-N:]` on every append | `collections.deque(maxlen=N)` | O(1) auto-eviction; no copy on every tick; thread-safe for single-writer patterns |
| Kivy-compatible matplotlib canvas widget | Re-implementing FigureCanvasKivyAgg | `kivy-matplotlib-widget.MatplotFigure` | `matplotlib.backends.backend_kivyagg` does not exist in matplotlib 3.10.8 — confirmed ImportError in this environment |

**Key insight:** The only non-trivial custom work in this phase is the _data plumbing_ (hooking `_apply_ui` → deque → `_tick_plot`). The rendering, scaling, and canvas management are handled entirely by existing libraries.

---

## Common Pitfalls

### Pitfall 1: Calling matplotlib draw from the background job thread
**What goes wrong:** App crashes with SIGABRT (on Pi) or produces a blank canvas (on Windows) — often no useful traceback.
**Why it happens:** `_do_poll()` runs in `jobs.submit()` worker thread. Developers are tempted to update the plot there because it feels like a data operation. It is also a GL/rendering operation.
**How to avoid:** Data flows: background thread appends nothing to deque — only `_apply_ui()` (confirmed main thread via `Clock.schedule_once`) appends. Drawing flows: only `_tick_plot()` (confirmed main thread via `Clock.schedule_interval`) calls matplotlib.
**Warning signs:** If you see `ax.set_data` or `canvas.draw` inside `_do_poll` or any function called from `jobs.submit`, it is wrong.

### Pitfall 2: MatplotFigure passes touch events to pan/zoom handlers by default
**What goes wrong:** Operator taps in the plot area and triggers a pan/zoom gesture instead of tapping through to E-STOP or other buttons underneath.
**Why it happens:** `MatplotFigure` inherits touch handling from a Scatter-based widget with pan/zoom built in. Default `touch_mode` is not 'none'.
**How to avoid:** In `on_kv_post` immediately after assigning `widget.figure = fig`, set `do_pan_x = False`, `do_pan_y = False`, `do_scale = False`, `touch_mode = 'none'`. Repeat in KV as defaults.
**Warning signs:** Touch on the plot area produces movement of the axes view, or E-STOP button appears unresponsive when touched near the plot boundary.

### Pitfall 3: backend_kivyagg import fails silently / wrong import path
**What goes wrong:** `from matplotlib.backends.backend_kivyagg import FigureCanvasKivyAgg` raises `ModuleNotFoundError` — confirmed in this environment with matplotlib 3.10.8.
**Why it happens:** This backend was present in older matplotlib versions but is absent from 3.10.8. Prior research documents (STACK.md, ARCHITECTURE.md) reference this path as the standard approach — they are outdated.
**How to avoid:** Use `from kivy_matplotlib_widget.uix.graph_widget import MatplotFigure` and assign `widget.figure = fig`. Do not attempt the backend_kivyagg import.
**Warning signs:** Any import line containing `backend_kivyagg` will fail in this environment.

### Pitfall 4: MatplotFigure not recognized in KV file
**What goes wrong:** `FactoryException: Unknown class <MatplotFigure>` at app startup.
**Why it happens:** Kivy's KV builder processes class rules before screen modules are imported if the import order is wrong, or if `kivy_matplotlib_widget` is never imported before `Builder.load_file()`.
**How to avoid:** Add `import kivy_matplotlib_widget` (not just `from ... import MatplotFigure`) at the top of `run.py`. This side-effects line registers all widgets in the Kivy Factory. Also add `#:import kivy_matplotlib_widget kivy_matplotlib_widget` in `run.kv` as a belt-and-suspenders guard.
**Warning signs:** App starts with a blank left column or FactoryException in the log.

### Pitfall 5: equal aspect ratio with empty or single-point buffer produces degenerate axes
**What goes wrong:** matplotlib warning `"Axes limits cannot be set"` or the plot axis range collapses to a single point.
**Why it happens:** `ax.set_aspect("equal")` + `autoscale_view()` with zero or one data point produces an ill-defined view.
**How to avoid:** Guard `_tick_plot` with `if len(xs) < 2: return`. On trail clear, call `ax.set_xlim(0, 1); ax.set_ylim(0, 1)` as a safe blank state.
**Warning signs:** Console warning containing "axes limits" when first entering the RUN page.

### Pitfall 6: Figure size mismatch vs widget size
**What goes wrong:** Plot renders at matplotlib's default figure DPI/size, not at the actual widget pixel size. On 800x480 Pi screen, this appears clipped or tiny.
**Why it happens:** `Figure(figsize=(4, 3))` sets DPI-based inches. `MatplotFigure` resizes via its `on_size` callback, but only after the figure is assigned.
**How to avoid:** Use `tight_layout(pad=0.4)` and `size_hint_y: 1` in KV so the widget fills available space. `MatplotFigure` handles the texture resize. Do not hard-code `figsize` dimensions in absolute pixels.
**Warning signs:** On Pi touchscreen, plot area appears zoomed-in or shows only a corner of the axes.

---

## Code Examples

### Minimal MatplotFigure Wiring (verified against installed package)

```python
# Source: kivy_matplotlib_widget.uix.graph_widget — inspected 2026-04-04; v0.16.0
import kivy_matplotlib_widget  # side-effect: registers MatplotFigure in Kivy Factory
from kivy_matplotlib_widget.uix.graph_widget import MatplotFigure  # type annotation only
from matplotlib.figure import Figure

fig = Figure(facecolor="#0D1219")
ax = fig.add_subplot(111)
line, = ax.plot([], [], color="#7DF9FF", linewidth=1.2)

# Assign to widget
plot_wgt.figure = fig  # triggers MatplotFigure.on_figure() → creates internal canvas

# Redraw (must be on main thread)
line.set_data(xs, ys)
ax.relim()
ax.autoscale_view()
fig.canvas.draw_idle()
```

### Clock Integration Pattern (matching existing project style)

```python
# Source: project convention established in run.py on_pre_enter / on_leave
PLOT_UPDATE_HZ = 5  # Hz — tuning point for Pi; reduce if CPU load is excessive

_plot_clock_event = None  # class-level sentinel

def on_pre_enter(self, *args) -> None:
    self._show_disconnected()
    # Existing poll clock
    self._update_clock_event = Clock.schedule_interval(self._update_clock, 1.0 / 10)
    # New plot redraw clock — separate from poll to protect E-STOP latency
    self._plot_clock_event = Clock.schedule_interval(self._tick_plot, 1.0 / PLOT_UPDATE_HZ)

def on_leave(self, *args) -> None:
    for attr in ("_update_clock_event", "_plot_clock_event"):
        ev = getattr(self, attr, None)
        if ev:
            ev.cancel()
            setattr(self, attr, None)
```

### KV Snippet (replacing placeholder)

```kv
#:import kivy_matplotlib_widget kivy_matplotlib_widget

# Replace the existing plot placeholder BoxLayout (lines 33-56 in run.kv):
MatplotFigure:
    id: ab_plot
    size_hint_y: 1
    do_pan_x: False
    do_pan_y: False
    do_scale: False
    touch_mode: 'none'
    disable_mouse_scrolling: True
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `matplotlib.backends.backend_kivyagg.FigureCanvasKivyAgg` | `kivy_matplotlib_widget.uix.graph_widget.MatplotFigure` | Removed from matplotlib 3.x (absent in 3.10.8, confirmed) | **Must update all prior research docs and code scaffolds that reference backend_kivyagg** |
| `kivy.garden.matplotlib` garden extension | `kivy-matplotlib-widget` PyPI package | garden.matplotlib stale (30 open issues, no active PRs) | No `garden install` step needed — standard `pip install` |
| `plt.subplots()` for figure creation | `Figure()` + `fig.add_subplot()` | Best practice; not version-specific | Avoids pyplot global state contamination |

**Deprecated / outdated references in this project:**
- `.planning/research/ARCHITECTURE.md` line 196: `from kivy_garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg` — this import fails in the current environment.
- `.planning/research/STACK.md` line 32: states `FigureCanvasKivyAgg ships with matplotlib's Kivy backend` — incorrect for matplotlib 3.10.8.
- `.planning/research/SUMMARY.md` line 25 and elsewhere: references `FigureCanvasKivyAgg` and `canvas.draw_idle()` on that object — the draw_idle pattern is correct but the import path is wrong.

These references should be treated as superseded by the findings in this document.

---

## Open Questions

1. **Re-enabling the 10 Hz poll clock in `on_pre_enter`**
   - What we know: `on_pre_enter` currently calls `_show_disconnected()` only — polling was explicitly disabled per Phase 2 decision ("no program loaded yet").
   - What's unclear: The decision comment says "no program loaded yet" — this implies polling should eventually be enabled when a controller is connected. Phase 3 needs the poll clock running to have data for the plot.
   - Recommendation: Re-enable polling in `on_pre_enter` (restore `Clock.schedule_interval(self._update_clock, 1.0/10)`) guarded by `if self.controller and self.controller.is_connected()`. This is consistent with the existing `_update_clock` logic which already checks `is_connected()` and skips gracefully when disconnected.

2. **`_do_poll` currently does not read raw float A/B values for buffer**
   - What we know: `_apply_ui(pos, cycle)` receives `pos["A"]` and `pos["B"]` as raw floats — the data is already in the right format.
   - What's unclear: `_apply_ui` formats them as `f"{int(val):,}"` strings for display. The plot buffer needs raw floats, not formatted strings.
   - Recommendation: In `_apply_ui`, read `pos.get("A")` and `pos.get("B")` **before** the int conversion, and append to `_plot_buf_x`/`_plot_buf_y` only if `cycle_running` and both values are not None.

3. **`matplotlib.ticker.MaxNLocator` import for tick density**
   - What we know: Matplotlib's `MaxNLocator` controls max tick count; `plt.MaxNLocator` would require importing pyplot.
   - Recommendation: Import directly: `from matplotlib.ticker import MaxNLocator` — avoids pyplot global state.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml (`[tool.pytest.ini_options]`) |
| Quick run command | `python -m pytest tests/test_run_screen.py -x -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RUN-07 | `RunScreen` exposes `_plot_buf_x`, `_plot_buf_y` as deques | unit | `python -m pytest tests/test_run_screen.py::test_plot_buffer_properties -x` | ❌ Wave 0 |
| RUN-07 | Trail buffer clears when `on_start_pause_toggle("down")` is called | unit | `python -m pytest tests/test_run_screen.py::test_trail_clears_on_start -x` | ❌ Wave 0 |
| RUN-07 | `PLOT_UPDATE_HZ` constant exists in `run.py` | unit | `python -m pytest tests/test_run_screen.py::test_plot_hz_constant_exists -x` | ❌ Wave 0 |
| RUN-07 | Buffer appends only when `cycle_running` is True (idle static) | unit | `python -m pytest tests/test_run_screen.py::test_plot_buffer_only_during_cycle -x` | ❌ Wave 0 |
| RUN-07 | Rolling buffer respects `PLOT_BUFFER_SIZE` maxlen | unit | `python -m pytest tests/test_run_screen.py::test_plot_buffer_maxlen -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_run_screen.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Five new test functions in `tests/test_run_screen.py` covering RUN-07 behaviors listed above
- [ ] No new test files needed — all RUN-07 tests belong in the existing `test_run_screen.py`
- [ ] No new fixtures needed — existing Kivy-deferred import pattern in `test_run_screen.py` is sufficient

---

## Sources

### Primary (HIGH confidence)
- `kivy_matplotlib_widget.uix.graph_widget.MatplotFigure` — inspected source 2026-04-04; v0.16.0; confirmed `figure` ObjectProperty, `do_pan_x`, `do_pan_y`, `do_scale`, `touch_mode` properties; `fig.canvas.draw_idle()` as redraw mechanism
- `src/dmccodegui/screens/run.py` — codebase inspection 2026-04-04; confirmed `_do_poll`, `_apply_ui`, `on_start_pause_toggle`, `on_pre_enter`, `on_leave` signatures and threading model
- `src/dmccodegui/ui/run.kv` — codebase inspection 2026-04-04; confirmed plot placeholder at lines 33-56 as BoxLayout with Label
- `src/dmccodegui/theme_manager.py` — codebase inspection 2026-04-04; confirmed `bg_panel = [0.051, 0.071, 0.102, 1]`, `text_mid = [0.580, 0.631, 0.710, 1]`
- Shell verification 2026-04-04: `python -c "from matplotlib.backends.backend_kivyagg import FigureCanvasKivyAgg"` → `ModuleNotFoundError` confirmed on matplotlib 3.10.8

### Secondary (MEDIUM confidence)
- [kivy-matplotlib-widget PyPI](https://pypi.org/project/kivy-matplotlib-widget/) — v0.16.0, released 2025-10-17; confirmed active maintenance; `MatplotFigure` is primary widget; no additional backend deps
- [kivy-garden/garden.matplotlib GitHub](https://github.com/kivy-garden/garden.matplotlib/blob/master/backend_kivyagg.py) — confirmed 30 open issues, no active PRs; not recommended

### Tertiary (LOW confidence)
- `.planning/research/ARCHITECTURE.md`, `STACK.md`, `PITFALLS.md` — prior project research; useful for threading patterns and pitfall descriptions but contain outdated import paths that contradict current environment findings

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `MatplotFigure` import confirmed working in this Python environment; `backend_kivyagg` absence confirmed by actual ImportError
- Architecture: HIGH — integration points are direct codebase reads; threading model follows established project patterns
- Pitfalls: HIGH (threading/touch) / MEDIUM (Pi performance) — threading pitfalls are Kivy fundamentals; Pi performance deferred to Phase 8 per locked decision

**Research date:** 2026-04-04
**Valid until:** 2026-07-04 (kivy-matplotlib-widget tracks matplotlib; check for breaking changes on upgrade)
