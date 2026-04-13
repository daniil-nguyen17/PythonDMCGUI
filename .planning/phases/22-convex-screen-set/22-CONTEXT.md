# Phase 22: Convex Screen Set - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Create ConvexRunScreen, ConvexAxesSetupScreen, ConvexParametersScreen with 4-axis layout (A, B, C, D), a convex-specific adjustment panel placeholder, and independently defined placeholder param_defs. Reachable through the screen loader when machine type is "4-Axes Convex Grind". Satisfies CONV-01, CONV-02, CONV-03, CONV-04.

</domain>

<decisions>
## Implementation Decisions

### Convex adjustment panel
- Same base controls as Flat Grind (DeltaC bar chart, more/less stone with tip/heel labels, startPtC offset) — carried over unchanged
- Additional "Convex Adjustments" panel as a labeled section with placeholder text ("Pending customer specs") — makes it obvious where convex-specific controls will go
- Own widget class `ConvexAdjustPanel` in `screens/convex/widgets.py` — clean separation, easy to swap in real controls later
- Panel content and behavior are TBD pending customer specifications

### Axis roles & labels
- Same roles as Flat Grind: A=cross-travel, B=in-feed, C=stone-advance, D=wheel-dress
- Same accent colors: A=orange, B=purple, C=cyan, D=yellow — consistent across all machine types
- Same teach points (rest point + start point per axis) and same jog workflow

### Run screen layout
- Keeps live A/B matplotlib position plot (toolpath preview + live trace) — same as Flat Grind
- Keeps DeltaC bar chart (segment endpoint offsets) with tip/heel labels and up/down arrows
- Keeps more/less stone panel with startPtC offset logic
- Keeps cycle controls: Start, Stop, session/station counters, progress bar, controller message log
- ConvexAdjustPanel added to layout — position at Claude's discretion based on existing proportions

### Param_defs
- `_CONVEX_PARAM_DEFS` explicitly defined as its own list (NOT a copy of `_FLAT_PARAM_DEFS`) — enables independent editing for future convex-specific parameters
- Same parameter groups as Flat Grind for now: Geometry, Feedrates, Calibration — all 4 axes
- Single top-level placeholder comment: "Placeholder — mirrors Flat Grind, pending customer convex specs"
- Parameters screen behavior identical to Flat Grind (grouped cards, editable fields, read-from-controller)
- No dynamic bridging parameter (like numSerr) for now — may add later pending customer specs

### Screen package structure
- Copy flat_grind package as starting point, then modify — full independence (Phase 21 pattern)
- Package: `screens/convex/` with `__init__.py`, `run.py`, `axes_setup.py`, `parameters.py`, `widgets.py`
- `__init__.py` exports `load_kv()` + all three Convex screen classes (deferred loading pattern from Phase 19)
- KV files in `ui/convex/`: `run.kv`, `axes_setup.kv`, `parameters.kv`
- Update `machine_config._REGISTRY["4-Axes Convex Grind"]` to point to real Convex classes and load_kv

### Testing
- Mirror Flat Grind test patterns: screen instantiation, expected widgets present
- ConvexAdjustPanel renders with placeholder content
- KV rule name collision check: grep for duplicate `<ClassName>:` headers across all .kv files
- Same test coverage approach as Phase 21 (Serration)

### Claude's Discretion
- ConvexAdjustPanel position in run screen layout
- ConvexAdjustPanel placeholder visual design
- Exact KV layout proportions and spacing
- Test file organization
- widgets.py internal structure for ConvexAdjustPanel

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `screens/flat_grind/` package: complete 4-axis reference implementation to copy from (run.py, axes_setup.py, parameters.py, widgets.py, __init__.py)
- `ui/flat_grind/` KV files: layout templates to copy and modify for convex
- `screens/base.py`: BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen, SetupScreenMixin — all Convex classes inherit from these
- `screens/flat_grind/widgets.py`: DeltaC bar chart widget, more/less stone panel — carry over to convex
- `machine_config._CONVEX_PARAM_DEFS`: currently a shallow copy of Flat, will be replaced with explicit own list

### Established Patterns
- Per-machine package: `__init__.py` with deferred `load_kv()` + class exports, called from main.py build()
- Copy-then-modify for full independence (Phase 21 serration pattern)
- One-element array writes: deltaC write pattern in flat_grind/run.py
- ObjectProperty injection: main.py sets controller/state on screens
- Background I/O: all gclib calls via `jobs.submit()`, UI updates via `Clock.schedule_once()`
- module-level `submit` import in base.py: single patch target for tests

### Integration Points
- `machine_config.py._REGISTRY["4-Axes Convex Grind"]`: update screen_classes, load_kv, replace _CONVEX_PARAM_DEFS with explicit list
- `main.py._add_machine_screens()`: already handles dynamic loading from registry — no changes needed
- Tab bar: unchanged — same 5 tabs for all machine types

</code_context>

<specifics>
## Specific Ideas

- Convex is essentially Flat Grind with an extra placeholder panel — the key differentiator is the ConvexAdjustPanel which will hold convex-specific controls once customer specs arrive
- Param_defs must be independently defined (not a copy) so future convex-specific parameters can be added without touching Flat Grind
- The labeled placeholder section should be clearly visible so it's obvious during testing/demo that convex-specific controls are pending

</specifics>

<deferred>
## Deferred Ideas

- Convex-specific adjustment controls — add to ConvexAdjustPanel when customer provides real convex specifications
- Additional convex-specific parameters — add to _CONVEX_PARAM_DEFS when customer provides real DMC variable list
- Dynamic bridging parameter (numSerr equivalent) — add if needed after customer input
- Convex plot visualization customization — if convex toolpath differs from flat grind, update after hardware validation

</deferred>

---

*Phase: 22-convex-screen-set*
*Context gathered: 2026-04-13*
