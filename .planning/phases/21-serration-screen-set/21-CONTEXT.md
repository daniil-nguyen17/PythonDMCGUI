# Phase 21: Serration Screen Set - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Create SerrationRunScreen, SerrationAxesSetupScreen, SerrationParametersScreen with 3-axis layout (A, B, C only), D-axis removed, live bComp panel for per-serration compensation entry, and placeholder plot stub. Reachable through the screen loader when machine type is "3-Axes Serration Grind". Satisfies SERR-01, SERR-02, SERR-03, SERR-04.

</domain>

<decisions>
## Implementation Decisions

### bComp panel
- Live functional panel (not a stub) — scrollable list/table of editable input fields, one row per serration
- Array sized by `numSerr` variable read from controller — displayed as "Serrations: N" in panel header
- Read/write DMC `bComp[]` array: auto-read on screen enter + manual "Read bComp" refresh button
- Save writes one element at a time (matches existing deltaC individual element assignment pattern for reliable writes)
- Values in mm with min/max validation (Claude picks reasonable defaults)
- Editable when machine is idle — no setup mode required
- All entries visible at once in a scrollable list (no pagination)
- New BCompPanel widget built from scratch — do NOT reuse _BaseBarChart (list UI is fundamentally different from bar chart)
- Lives in `screens/serration/widgets.py` — mirrors flat_grind package structure

### Run screen layout
- No DeltaC bar chart — that is Flat Grind only
- No D-axis position labels or status anywhere — stripped completely, clean 3-axis layout
- Plot area: placeholder/stub — decide visualization after seeing real machine data
- bComp panel positioned below the plot stub area, full width
- Cycle controls: Start, Stop, session/station counters, progress bar, controller message log — same as Flat Grind
- More/less stone panel: up/down arrows (no tip/heel labels), same startPtC offset logic and DMC variables as Flat Grind, shows current startPtC value alongside arrows
- `numSerr` displayed near bComp panel header as read-only

### Axes Setup 3-axis layout
- Same as Flat Grind minus D axis — [A, B, C] with identical roles, same accent colors (A=orange, B=purple, C=cyan)
- Same teach points: rest point and start point per axis
- Standard jog workflow: jog controls, teach, CPM read — no extra Serration-specific actions
- BaseAxesSetupScreen with mc.get_axis_list() handles the 3-axis constraint automatically

### Parameters grouping
- Same groups as Flat Grind (Geometry, Feedrates, Calibration) minus D-axis parameters
- `_SERRATION_PARAM_DEFS` already defined in machine_config.py (Flat minus fdD, pitchD, ratioD, ctsRevD)
- `numSerr` is an editable parameter on the Parameters screen — operator sets it in setup
- When numSerr changes, bComp list on Run screen auto-resizes on next screen enter (re-reads numSerr)
- Room to add more Serration-specific params later — param_defs is a placeholder subset for now

### Screen package structure
- Copy flat_grind package as starting point, then modify — full independence for future tuning
- Package: `screens/serration/` with `__init__.py`, `run.py`, `axes_setup.py`, `parameters.py`, `widgets.py`
- `__init__.py` exports `load_kv()` + all three Serration screen classes (same pattern as flat_grind)
- KV files in `ui/serration/`: `run.kv`, `axes_setup.kv`, `parameters.kv`
- Update `machine_config._REGISTRY["3-Axes Serration Grind"]` to point to real Serration classes and load_kv

### Testing
- Mirror Flat Grind test patterns: screen instantiation, expected widgets present, D-axis widgets absent
- bComp panel renders with dummy data — verify list sizing from numSerr
- bComp read/write I/O testing deferred to hardware validation — no mocked controller tests for bComp
- KV rule name collision check: grep for duplicate `<ClassName>:` headers across all .kv files

### Claude's Discretion
- Exact bComp min/max validation range
- Plot stub visual design (empty axes, placeholder text, etc.)
- BCompPanel internal implementation (Kivy RecycleView, BoxLayout rows, etc.)
- numSerr parameter definition details (group, min, max)
- Exact KV layout proportions and spacing
- Test file organization

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `screens/flat_grind/` package: complete reference implementation to copy from (run.py, axes_setup.py, parameters.py, widgets.py, __init__.py)
- `ui/flat_grind/` KV files: layout templates to copy and modify
- `screens/base.py`: BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen, SetupScreenMixin — all Serration classes inherit from these
- `machine_config._SERRATION_PARAM_DEFS`: already defined, D-axis vars stripped
- `machine_config.is_serration()`: utility function for machine type checks
- `machine_config._REGISTRY["3-Axes Serration Grind"]`: has_bcomp=True, axes=[A,B,C] — just needs screen_classes/load_kv updated

### Established Patterns
- Per-machine package: `__init__.py` with `load_kv()` + class exports, called from main.py build()
- One-element array writes: deltaC write pattern in flat_grind/run.py uses individual element assignments for reliability
- ObjectProperty injection: main.py sets controller/state on screens via `sm.get_screen(canonical_name)`
- Background I/O: all gclib calls via `jobs.submit()`, UI updates via `Clock.schedule_once()`
- module-level `submit` import in base.py: single patch target for all screen I/O in tests

### Integration Points
- `machine_config.py._REGISTRY`: update "3-Axes Serration Grind" screen_classes and load_kv paths
- `main.py._add_machine_screens()`: already handles dynamic loading from registry — no changes needed
- `screens/__init__.py`: may need to export Serration classes
- Tab bar: unchanged — same 5 tabs for all machine types

</code_context>

<specifics>
## Specific Ideas

- bComp is a simple editable list, not a chart — operator enters mm values per serration index, saves one at a time
- More/less stone panel is simpler than Flat Grind: same arrows and startPtC logic but no tip/heel labels
- Plot visualization is deliberately deferred — stub now, design after seeing real Serration machine data
- numSerr bridges Parameters and Run: editable on Parameters, displayed read-only on Run, drives bComp list sizing

</specifics>

<deferred>
## Deferred Ideas

- Serration plot visualization design — decide after hardware validation with real machine data
- Additional Serration-specific parameters — add to _SERRATION_PARAM_DEFS when customer provides real DMC variable list
- bComp controller I/O testing — deferred to hardware validation phase
- Serration bComp write path tied to DMC program (SERR-04 partially addressed: panel functional, but DMC program integration pending customer)

</deferred>

---

*Phase: 21-serration-screen-set*
*Context gathered: 2026-04-11*
