# Phase 6: Machine-Type Differentiation - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

The app correctly adapts its RUN page, axes controls, and parameter groups to whichever of the three machine types it is deployed on: 4-Axes Flat Grind, 4-Axes Convex Grind, and 3-Axes Serration Grind. Machine type is selected at runtime by Setup/Admin, persisted, and hot-swappable. Admin user management is Phase 7. Kiosk deployment is Phase 8.

</domain>

<decisions>
## Implementation Decisions

### Parameter groups per machine type
- Each machine type has its own parameter groups — not just different variables inside the same groups
- Convex Grind is mostly the same as Flat Grind with some additional Convex-specific parameters
- Serration Grind shares some groups with Flat/Convex (e.g., Feedrates) but has many serration-specific variables
- Validation rules (min/max ranges) vary per machine type, even for shared variable names
- Specific DMC variable lists will be provided later — design the config structure to be plug-in friendly
- Group color scheme is consistent by group name across all machine types (orange=Geometry, cyan=Feedrates, purple=Calibration). New groups get new colors.

### Axis configuration per machine type
- Serration uses A/B/C only — same roles as Flat (A=Knife Length, B=Knife Curve, C=Grinder Up/Down)
- Convex uses all 4 axes identically to Flat (A=Knife Length, B=Knife Curve, C=Grinder Up/Down, D=Knife Angle)
- CPM defaults are the same across all machine types (A=1200, B=1200, C=800, D=500)
- On Serration, the D axis is hidden completely from the Axes Setup sidebar — not greyed out, removed

### RUN page adaptation
- Delta-C bar chart (Knife Grind Adjustment) is shown on Flat and Convex only — hidden on Serration
- Serration replaces Delta-C with a bComp (B-axis compensation) bar chart:
  - Same widget pattern as DeltaCBarChart (tap-to-select bar, up/down buttons, zero baseline)
  - Array size driven by `numSerr` (number of serrations per knife, set in parameters)
  - Each bar adjusts the B-axis compensation for that tooth — adds/removes grind depth
  - `bComp` is the DMC array name; `numSerr` is the DMC variable for array size
- Live A/B position plot works identically on all three machine types
- Action buttons (Start, Pause, Go to Rest, E-STOP) are identical across all types
- Cycle status: Serration shows tooth/pass/depth fields; Flat/Convex do not (decided in Phase 2)

### Machine type selection and persistence
- Machine type is selected at runtime by Setup/Admin — NOT hard-coded (changes earlier project decision)
- Operator cannot change machine type
- Persisted to disk — survives restarts
- Hot-swap: changing machine type immediately reloads parameter groups, axes sidebar, RUN page widgets without restart
- Status bar displays current machine type name — tapping it (Setup/Admin only) opens a picker popup
- Picker popup shows 3 big buttons: "4-Axes Flat Grind", "4-Axes Convex Grind", "3-Axes Serration Grind"
- On first launch (no machine type set), the app forces the mandatory machine-type picker before anything else — cannot dismiss without selecting

### Claude's Discretion
- Storage location for persisted machine type (separate config file vs users.json vs new settings file)
- Internal config module architecture (one dict per type, registry pattern, etc.)
- bComp bar chart step size (can match Delta-C step or differ)
- How hot-swap triggers screen rebuilds (Kivy property binding, screen recreation, etc.)

</decisions>

<specifics>
## Specific Ideas

- bComp chart is the Serration equivalent of Delta-C — "each value put in will add or take away the grind for that tooth"
- `numSerr` DMC variable controls how many bars the bComp chart shows (matches number of serrations per knife)
- Setup/Admin should be able to change machine type "on the go" — scenario: taking a Pi from one machine to another
- First-launch experience should be clean: mandatory machine type selection before login

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DeltaCBarChart` (run.py): Existing bar chart widget — nearly identical pattern needed for bComp. Can be generalized into a shared base widget.
- `PARAM_DEFS` list (parameters.py): Current parameter definitions for Flat Grind — needs to become per-machine-type.
- `AXIS_LABELS`, `AXIS_COLORS`, `AXIS_CPM_DEFAULTS` dicts (axes_setup.py): Currently 4-axis only — need to be filtered by machine type.
- `MACHINE_TYPE` constant in run.py and `MACHINE_TYPE` in profiles.py — both need to read from the new central config.
- `IS_SERRATION` flag in run.py — already gates serration-specific cycle status fields.

### Established Patterns
- Background thread I/O via `jobs.submit()` with `Clock.schedule_once()` for UI updates — preserved
- Kivy properties for reactive UI binding — hot-swap should leverage property changes to trigger rebuilds
- `_poll_tick` pattern for periodic controller reads — axes and parameters screens use this
- `StatusBar` already shows connection info — machine type display fits naturally here

### Integration Points
- `StatusBar` (status_bar.py / status_bar.kv): Add machine type label + tap-to-pick for Setup/Admin
- `AxesSetupScreen` sidebar: Filter axis buttons by machine type's axis list
- `ParametersScreen` PARAM_DEFS: Replace with per-machine-type parameter definitions
- `RunScreen` Delta-C section: Conditionally show Delta-C or bComp based on machine type
- `profiles.py` MACHINE_TYPE: Read from central config for CSV export/import validation
- `PINOverlay` / auth flow: Machine type picker needs to show on first launch before login

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-machine-type-differentiation*
*Context gathered: 2026-04-04*
