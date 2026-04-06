# Phase 2: RUN Page - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Operator-facing RUN page with cycle controls (Start/Pause toggle, Go to Rest), live axis positions, cycle status panel, progress bar, and Knife Grind Adjustment panel. Layout follows the approved HTML mockup at `mockups/run_page.html` — left column (plot area placeholder + adjustment panel), right column (cycle status + axis positions), bottom action bar. The live matplotlib plot is Phase 3; this phase creates the plot placeholder area. E-STOP is NOT on the RUN page bottom bar — it lives in the persistent status bar (Phase 1).

</domain>

<decisions>
## Implementation Decisions

### Action Buttons
- Start button: no confirmation dialog — one tap begins cycle immediately
- Start and Pause are a **single toggle button**: shows "Start" when idle, becomes "Pause" when running
- Go to Rest: always enabled, used after stopping mid-cycle so operator can inspect machine/knife. At rest position the machine waits for next command
- No E-STOP on the bottom action bar — the persistent status bar E-STOP (from Phase 1) is sufficient
- Bottom bar has 3 buttons: Start/Pause (toggle), Go to Rest, and space freed from removing E-STOP

### Cycle Status Data Source
- All cycle status values polled from controller arrays/variables on a background thread at ~10 Hz (same rate as axis positions, single polling loop)
- **3-axis serration machines**: show current tooth, pass, depth (serration-specific fields)
- **4-axis flat/convex machines**: do NOT show tooth, pass, depth (not applicable)
- **Speed removed** from cycle status panel entirely
- Elapsed time and ETA: GUI-calculated from elapsed time + completion percentage
- Progress bar: shows overall cycle completion percentage
- When idle (no cycle running): show last values from previous cycle, greyed out

### Knife Grind Adjustment (replaces Operation Log)
- **Replaces the operation log** from the mockup — no timestamped event log on the RUN page
- Operator inputs a section count (1-10) specifying how many segments to divide the knife into
- If N sections entered: the 100-element `deltaC` controller array is divided into N equal segments (e.g., 10 sections = indices 0-9, 10-19, 20-29, ...)
- Vertical bars laid out horizontally, each representing one section's offset value
- Bars show accumulated offset from zero (+50, +100, -50, etc.) — not absolute deltaC values
- Operator taps a bar to select it, then uses up/down arrow buttons to adjust ±50 counts per press
- **Apply button** sends all adjusted values to the controller at once (batch update, not immediate per-press)
- **IMPORTANT NOTE for planning:** deltaC array has protected indices that these bars must NOT touch. The writable index range (from which index to which index) will be determined later — planner should parameterize this range so it can be configured without code changes
- Reset button: TBD — depends on knowing which indices are writable vs protected

### Axis Position Display
- All axes show raw encoder counts only (no mm/degrees conversion in the display)
- Each axis row includes a conversion note derived from controller CPM variables (e.g., "1000 cts = 1mm" for axis A) — read cpmA, cpmB, cpmC, cpmD from controller
- No direction arrows next to positions (removed from mockup design)
- When disconnected: show "---" for all position values
- No flash/pulse on value change — smooth update at ~10 Hz
- Axis accent colors maintained: A=orange, B=purple, C=cyan, D=yellow

### Claude's Discretion
- Exact layout proportions within the mockup grid structure
- Toggle button visual treatment (color change, icon swap for Start vs Pause state)
- Greyed-out styling for idle cycle status values
- Bar chart visual design for Knife Grind Adjustment (bar width, colors, selection highlight)
- Section count input widget style (spinner, text input, etc.)
- Polling implementation details (single loop vs separate schedulers)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RunScreen`: empty placeholder in `screens/run.py` — ready to build on, already has controller/state ObjectProperty injection
- `MachineState`: has `pos` dict, `running` bool, `speed` float, `messages` list, subscribe/notify pattern — core data for live updates
- `MachineState.update_status()`: updates pos, interlocks_ok, speed in one call with notify — use for position polling
- `MachineState.log()`: messages list with 200-entry cap — could be repurposed or extended
- `jobs.submit()` + `Clock.schedule_once()`: established threading pattern for controller I/O — use for polling loop
- `DMCApp.e_stop()` in `main.py:302`: E-STOP logic already sends `ST` + `AB` to controller
- `theme.kv`: dark palette (BG_DARK, BG_PANEL, BG_ROW, BORDER) — all RUN page cards use these
- `CardFrame` widget: rounded card with border — use for cycle status and axis position panels
- HTML mockup at `mockups/run_page.html`: approved layout with grid structure (left col: plot + log, right col: cycle status + axes, bottom: actions)

### Established Patterns
- KV files loaded in order via `KV_FILES` list in `main.py`, `base.kv` always last
- Screen classes use `ObjectProperty` for controller/state injection via `DMCApp.build()`
- All gclib calls via `jobs.submit()` on background thread, UI updates posted back via `Clock.schedule_once()`
- `on_kv_post`, `on_pre_enter`, `on_leave` lifecycle hooks used in screens
- Existing screens read controller variables with `self.controller.GCommand("MG varname")`

### Integration Points
- `RunScreen` class in `screens/run.py` — build out from placeholder
- `run.kv` (needs creation) — KV layout file for the RUN screen
- `MachineState` — may need new fields for cycle status (current_tooth, current_pass, depth, elapsed, etc.)
- `DMCApp.build()` — RunScreen already injected with controller/state
- Controller polling: need a `Clock.schedule_interval()` for ~10 Hz position + cycle status reads
- `deltaC` array: 100-element array on controller, accessed via gclib array read/write commands

</code_context>

<specifics>
## Specific Ideas

- Knife Grind Adjustment is a key operator tool: operators inspect the knife after a cycle, see where it needs more or less grinding, and adjust the deltaC offsets per section before running again
- 3-axis serration is the only machine type with tooth/pass/depth cycle data — 4-axis machines have simpler cycle status
- The conversion note (e.g., "1000 cts = 1mm") is read from the controller's CPM variables (cpmA, cpmB, cpmC, cpmD) — not hard-coded
- Go to Rest is a post-stop convenience: operator stops mid-cycle, sends axes to rest, inspects the machine/knife, then decides next action

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-run-page*
*Context gathered: 2026-04-04*
