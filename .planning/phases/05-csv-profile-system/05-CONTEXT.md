# Phase 5: CSV Profile System - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Setup personnel can save the current knife setup to a CSV and reload it later without re-entering values. Covers import, export, machine-type validation, and cycle-running safety interlock. Machine-type differentiation (adapting UI per machine type) is Phase 6. Admin user management is Phase 7.

</domain>

<decisions>
## Implementation Decisions

### CSV Format & Scope
- One CSV format containing everything: all scalar parameters (PARAM_DEFS) plus all DMC arrays
- Array-as-columns layout: scalars as name/value rows, arrays as one row per array with values across columns
- Metadata header rows at top: machine type, export date, profile name
- Controller only updates values for recognized array/variable names — extra data in CSV is harmless
- Primary use case: full setup profile (first-time), but most common use is just the delta arrays (deltaA-D) when changing knives

### UI Placement & Flow
- New dedicated Profiles tab/screen added to tab bar (role-gated to Setup/Admin)
- Screen has two big buttons: Import and Export — minimal layout, no file listing
- Import opens a Kivy FileChooser modal overlay (full-screen) — works on both Pi kiosk and Windows
- Export shows a text input popup for user to enter a profile name, then saves
- File chooser filters to .csv files only

### Import Confirmation Diff
- After selecting a CSV, show a diff dialog with changed values only (not all values)
- Table format: Name, Current Value, New Value — only rows where values differ
- User confirms to apply — values sent to controller + BV burn immediately (one-step import)
- If any value fails validation (out of range, wrong type, unrecognized name), block the entire import with clear error messages listing all failures
- Machine-type mismatch blocks import with clear error before diff is even shown

### File Storage
- Default storage: app-relative `/profiles/` directory (created if missing)
- File chooser starts at /profiles/ but allows browsing other locations (USB drives, Downloads, etc.)
- Export: if file with same name exists, show "Overwrite existing profile?" confirmation dialog
- CSV files are human-readable and Excel-compatible

### Safety Interlocks
- Import button disabled (greyed out) while `state.cycle_running == True`
- Import/Export only accessible to Setup and Admin roles (Operator cannot see Profiles tab)

### Claude's Discretion
- Exact Kivy FileChooser configuration (list vs icon view, filters)
- Diff dialog visual design and scrolling behavior
- Text input popup styling for export naming
- How to discover which arrays exist on the controller for full export
- Error message wording and layout
- Loading indicators during import/export operations

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ParametersScreen.PARAM_DEFS`: 21 scalar parameter definitions with var names, units, min/max ranges
- `ParametersScreen.validate_field()`: Validation logic (numeric, range, zero-reject, negative-reject) — reuse for CSV import validation
- `GalilController.cmd()`: Read/write scalar variables (e.g., `MG knfThk`, `knfThk=25.5`)
- `GalilController.upload_array()` / `download_array()`: Read/write DMC arrays
- `GalilController.upload_array_auto()`: Upload entire array without knowing size in advance
- `jobs.submit()` + `Clock.schedule_once()`: Background threading pattern for controller I/O
- `PINOverlay` (ModalView subclass): Pattern for full-screen modal overlays with callbacks
- `theme.kv`: Dark palette, CardFrame widget, 44dp+ touch targets
- `MachineState.cycle_running`: Safety interlock flag
- `MachineState.setup_unlocked`: Role-gating flag

### Established Patterns
- KV files loaded via `KV_FILES` list in main.py — new profiles.kv will be added
- `controller` and `state` injected into screens via ObjectProperty
- `on_pre_enter` for initial data load, `on_leave` for cleanup
- Background thread pool for all controller I/O, results posted to UI via Clock
- Role-based `_apply_role_mode(setup_unlocked)` pattern for access control

### Integration Points
- TabBar: add "Profiles" tab (role-gated to Setup/Admin)
- ScreenManager: register ProfilesScreen
- MachineState: subscribe for cycle_running changes to enable/disable import button
- ParametersScreen.PARAM_DEFS: shared parameter definitions for validation

</code_context>

<specifics>
## Specific Ideas

- "First time setup can have everything for the controller... if they just change the knife then just the 4 arrays deltaA-D. Mostly just the delta arrays."
- Controller only updates values for known array names and variables — CSV can contain everything safely
- BV burn after successful import to persist values through power cycles

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-csv-profile-system*
*Context gathered: 2026-04-04*
