# Phase 4: Axes Setup and Parameters - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Unified axes jog/teach screen and grouped parameter editor, both restricted to Setup role. Setup personnel can jog any axis, teach rest and start points, and edit all machine parameters from clean unified screens. CSV import/export is Phase 5. Machine-type differentiation is Phase 6.

</domain>

<decisions>
## Implementation Decisions

### Jog Behavior
- Live jog using PR (Position Relative) + BG commands per button press — axis moves immediately
- No confirmation dialog before jog moves — Setup user is authenticated and physically at machine
- Three mm-based step toggle buttons: 10mm, 5mm, 1mm (mutually exclusive selection)
- Jog distance = step_mm * cpmX (counts per mm for that axis)
- Example: 10mm step on A axis with cpmA=1200 sends `PRA=12000` then `BGA`
- No slider — arrow buttons + step toggles only
- CPM values can be read from controller (cpmA/B/C/D) or derived from calibration params (ctsRev * ratio / pitch) — Claude's discretion on which is more convenient

### D-Axis Handling
- D axis appears in the sidebar alongside A/B/C with same jog/teach UI layout
- D axis uses same mm-based step toggles (10mm/5mm/1mm) with cpmD conversion
- D axis accent color: yellow (per established theme)
- D axis has its own DMC variables: `restPtD` and `startPtD` — no array sharing with A/B/C
- D axis label: "Rotation" in sidebar

### Position Display
- Current position read via TD commands: `_TDA`, `_TDB`, `_TDC`, `_TDD`
- Polling at ~2-5 Hz timer for live position updates (same pattern as RUN page but slower)
- Position cards per axis: Rest Point, Start Point, Current Position (from mockup)

### Teach Buttons
- Two teach buttons per axis view: "Teach as Rest Point" and "Teach as Start Point"
- One press captures ALL 4 axes at once: `restPtA=_TDA`, `restPtB=_TDB`, `restPtC=_TDC`, `restPtD=_TDD` (and same pattern for start points)
- After teaching, send BV command to burn values to non-volatile memory
- Setup user jogs axes to desired positions first, then teaches to capture

### Quick Action Buttons
- Include Go to Rest All, Go to Start All, Home All buttons
- These work by setting software variables (mimicking physical button presses) that the DMC program's main loop polls
- Software button variables (Claude names): `swGoSetup`, `swMoreGrind`, `swLessGrind`, `swNewStone` — set to 0 or 1
- "Go Setup" puts controller into setup mode where axes can move freely
- This approach keeps the controller in its normal program flow rather than sending raw PA/BG which could disrupt state

### Parameter Definitions
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
- This is the starting list; more parameters may be added later
- Each parameter row shows: human-readable name, DMC variable code, editable input, unit

### Parameter Validation
- Type check (must be valid number) + basic sanity ranges
- Negatives rejected for feedrates; zero rejected for pitch/ratio/ctsRev
- Claude defines reasonable range defaults per parameter purpose
- Invalid inputs flagged with red border immediately (PARAM-03)
- Modified (unsaved) values highlighted amber with change counter (PARAM-04)

### Apply/Save Workflow (Parameters)
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

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `theme.kv`: Dark palette (BG_DARK, BG_PANEL, BG_ROW, BORDER), axis accent colors, CardFrame widget
- `VControl`/`HControl` widgets in theme.kv: composite arrow+input controls (used by old screens)
- `GalilController.upload_array()` / `download_array()`: read/write DMC arrays
- `GalilController.cmd()`: send raw DMC commands (PR, BG, BV, TD, etc.)
- `jobs.submit()` + `Clock.schedule_once()`: established threading pattern for controller I/O
- `MachineState` dataclass: subscribe/notify pattern, taught_points dict, axis_positions
- StatusBar + TabBar from Phase 1: persistent top bar with E-STOP, connection status, user badge

### Established Patterns
- KV files loaded in order via `KV_FILES` list in main.py
- `controller` and `state` injected into screens via ObjectProperty
- `on_pre_enter` for initial data load, `on_leave` for cleanup
- Background thread pool for all controller I/O, results posted to UI via Clock
- Old screens (rest.py, start.py, axisDSetup.py) demonstrate read/adjust/save patterns

### Integration Points
- TabBar already has "Axes Setup" and "Parameters" tabs (from Phase 1)
- Screens will be registered in ScreenManager and wired in main.py
- E-STOP accessible from StatusBar — no special handling needed per screen
- Role gating already handled by TabBar visibility (Setup role required)

</code_context>

<specifics>
## Specific Ideas

- Jog uses PR+BG (relative positioning) not PA+BG — easier to control for incremental moves
- Software button pattern (swGoSetup etc.) mimics physical button presses to keep controller in its normal DMC program flow — avoids disrupting controller state machine
- Teach captures all 4 axes simultaneously with one button press — Setup user positions axes first, then teaches
- BV (burn variables) after both teach operations and parameter apply — values persist through controller power cycles
- Apply to Controller includes automatic read-back verification to confirm values were received

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-axes-setup-and-parameters*
*Context gathered: 2026-04-04*
