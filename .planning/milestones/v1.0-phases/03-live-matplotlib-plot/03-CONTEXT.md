# Phase 3: Live Matplotlib Plot - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Embed a real-time top-down A/B position plot into the RUN page's existing placeholder area (left column, 60% width). Operators see the grinding path traced live during active cycles. The plot hooks into the existing 10 Hz polling loop for position data. No new screens, no new navigation — this phase adds a single widget to the existing RUN page layout.

</domain>

<decisions>
## Implementation Decisions

### Plot Visual Design
- Continuous line trail tracing A (X-axis) vs B (Y-axis) positions
- Single bright high-contrast color on dark background (Claude picks exact color)
- Plot background matches app theme (BG_PANEL) with tick/label colors matching text_mid
- Minimal axis ticks only — no grid lines, no axis labels beyond numeric tick values
- No current-position dot or marker — just the line

### History Buffer and Trail
- Rolling buffer of 500-1000 position samples (Claude picks exact size)
- Hard clip when buffer is full — oldest points simply disappear, no fade/alpha
- Trail clears automatically when operator taps Start (cycle begin)
- Plot updates ONLY during active cycles — static/blank when idle (saves Pi resources)

### Viewport Behavior
- Auto-scale axes to fit all visible trail data with padding
- Equal aspect ratio (1:1 scaling) so grinding path shape is geometrically accurate
- No operator interaction — display only, no zoom, no pan, no tap handlers
- No touch event handlers on the plot widget (avoids interfering with E-STOP or other buttons)

### Performance Strategy
- Target 5 Hz plot update rate (every 200ms), decoupled from the 10 Hz position polling
- Named constant `PLOT_UPDATE_HZ = 5` at top of file alongside other constants
- All matplotlib rendering on the main Kivy thread (FigureCanvasKivyAgg requirement)
- Position data collected on background thread (existing pattern), only draw call on main thread
- **CRITICAL: Polling is read-only for display data (axis positions). Never use polling to send commands to the controller.**
- Skip Pi performance validation for now — build for Windows first, validate on Pi during Phase 8
- **Document tuning points:** Add comments at PLOT_UPDATE_HZ constant and buffer size explaining how to adjust for Pi performance testing
- No FPS counter or debug overlay in production — clean display only
- **Pi fallback:** If matplotlib proves too slow on Pi, the fallback is switching to Kivy Canvas drawing (like DeltaCBarChart) — drop matplotlib entirely for native GPU acceleration

### Claude's Discretion
- Exact bright trail color choice (something that reads well on BG_PANEL dark background)
- Exact buffer size within the 500-1000 range
- Line width for the trail
- Tick mark density and formatting
- Padding amount for auto-scale viewport
- Whether to use draw_idle() or fig.canvas.draw() for the redraw call
- Exact integration with the existing _do_poll / _apply_ui flow (separate Clock.schedule_interval for plot vs reusing poll cycle)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RunScreen._do_poll()`: Background thread reads A/B positions at 10 Hz — plot data source is already flowing
- `RunScreen._apply_ui()`: Main thread callback updates pos_a/pos_b StringProperties — plot can hook into the same data path
- `DeltaCBarChart`: Existing Kivy Canvas-based widget in run.py — reference pattern if fallback to Kivy drawing is needed
- `theme.kv` / `ThemeManager`: bg_panel, bg_dark, text_mid, border colors — use for plot theming
- `jobs.submit()` + `Clock.schedule_once()`: Established threading pattern

### Established Patterns
- KV files loaded via `KV_FILES` list in main.py
- Screen classes use `ObjectProperty` for controller/state injection
- All gclib calls via `jobs.submit()`, UI updates via `Clock.schedule_once()`
- `on_pre_enter` / `on_leave` lifecycle hooks manage clock events
- `cycle_running` BooleanProperty controls cycle state

### Integration Points
- Plot placeholder in `run.kv` lines 33-56: BoxLayout with Label "Live Position -- A / B Axes" — replace with FigureCanvasKivyAgg widget
- `RunScreen.on_start_pause_toggle()`: Clear trail buffer when cycle starts (btn_state == "down")
- `RunScreen._apply_ui()`: Feed new A/B position to plot buffer after updating pos_a/pos_b
- `RunScreen.on_pre_enter()` / `on_leave()`: Start/stop the plot update clock
- `FigureCanvasKivyAgg` from `kivy.garden.matplotlib` or `matplotlib.backends.backend_kivyagg` — needs import added

</code_context>

<specifics>
## Specific Ideas

- Polling reads position for display only — the plot never triggers any controller commands
- Trail clears on cycle start gives the operator a fresh view for each grinding run
- Equal aspect ratio matters because grinding paths have real geometric meaning — a distorted path would mislead the operator
- The 5 Hz update rate is deliberately half the polling rate to leave CPU headroom for E-STOP responsiveness
- When idle, the plot should show either the last cycle's trail (static) or a blank plot area — not continuously updating

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-live-matplotlib-plot*
*Context gathered: 2026-04-04*
