# Phase 19: Flat Grind Rename and KV Split - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Rename existing RunScreen, AxesSetupScreen, and ParametersScreen to FlatGrindRunScreen, FlatGrindAxesSetupScreen, and FlatGrindParametersScreen with independent .kv files in ui/flat_grind/. Establishes the reference implementation and naming convention before the screen loader is wired in Phase 20. Zero behavior change from v2.0 Flat Grind functionality.

</domain>

<decisions>
## Implementation Decisions

### Python file structure
- New `screens/flat_grind/` package with `__init__.py`, `run.py`, `axes_setup.py`, `parameters.py`, `widgets.py`
- File names mirror the base pattern (run.py, axes_setup.py, parameters.py) — directory provides namespace
- `flat_grind_widgets.py` moves into the package as `screens/flat_grind/widgets.py`
- `__init__.py` exports all three FlatGrind* screen classes — consumers import from package root: `from screens.flat_grind import FlatGrindRunScreen`
- `machine_config.py` stays centralized — screen_classes mapping added in Phase 20
- `screens/__init__.py` updated to export FlatGrind* classes only (not old names)

### Old file handling
- Old `screens/run.py`, `screens/axes_setup.py`, `screens/parameters.py` become thin re-export wrappers (e.g., `from .flat_grind import FlatGrindRunScreen as RunScreen`) — safety net for anything importing old names
- Re-exports include screen class only — no BCompBarChart or other items re-exported
- Old `.kv` files (`ui/run.kv`, `ui/axes_setup.kv`, `ui/parameters.kv`) left untouched on disk but **not loaded** by Builder — removed from Builder.load_file calls in main.py
- End-of-v3.0-milestone audit: review and clean up all old files that are no longer needed after real-life usage validation

### KV file naming and loading
- KV files in `ui/flat_grind/` use same base names: `run.kv`, `axes_setup.kv`, `parameters.kv`
- Screen layouts only — no machine-specific style overrides (theme stays in `ui/theme.kv`)
- KV content is exact copy from old files with only the rule header renamed (`<RunScreen>:` -> `<FlatGrindRunScreen>:` etc.) — zero layout changes
- `Builder.load_file()` calls placed in `screens/flat_grind/__init__.py` — package is self-contained, importing it loads the kv
- Old `ui/run.kv` still has bComp widget references — noted for cleanup in end-of-milestone audit

### main.py transition wiring
- main.py imports FlatGrind* classes directly from `screens.flat_grind`
- ScreenManager canonical names preserved: `name='run'`, `name='axes_setup'`, `name='parameters'` — all navigation, tab bar, and screen references unchanged
- Controller/state ObjectProperty injection uses canonical screen name lookups (`sm.get_screen('run').controller = ctrl`) — no class-specific references

### Import migration
- All imports across codebase updated to use FlatGrind* class names directly
- All test files updated to import from `screens.flat_grind` with FlatGrind* names
- Log prefixes updated: `[RunScreen]` -> `[FlatGrindRunScreen]` etc. for unambiguous multi-machine debugging

### BCompBarChart removal
- BCompBarChart and BCOMP_* constants removed entirely from old run.py — bComp chart works differently than deltaC chart, will be redesigned from scratch in Phase 21 (Serration)
- `_BaseBarChart` stays in `screens/flat_grind/widgets.py` — DeltaCBarChart still uses it, Phase 21 decides whether to reuse for Serration

### Testing
- Existing test suite must pass with FlatGrind* imports — validates zero behavior change
- New automated test: grep all .kv files for duplicate `<ClassName>:` headers — catches kv rule name collisions (success criterion #3)
- New tests: full screen instantiation for each FlatGrind* class, verifying expected widgets/properties are present

### Claude's Discretion
- KV asset path strategy (relative vs absolute from project root) — match existing patterns
- Builder.load_file path resolution method (pathlib vs Kivy resource path)
- Exact thin re-export wrapper implementation details
- Test file organization for Phase 19-specific tests

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `screens/base.py`: BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen, SetupScreenMixin — all FlatGrind* classes inherit from these
- `screens/flat_grind_widgets.py`: DeltaCBarChart, _BaseBarChart, DELTA_C_* constants, stone_window_for_index() — moves to screens/flat_grind/widgets.py
- `screens/__init__.py`: current exports (RunScreen, AxesSetupScreen, ParametersScreen, base classes) — update to FlatGrind* exports

### Established Patterns
- ObjectProperty injection: main.py sets controller/state on screens via `sm.get_screen(name)`
- KV loading: main.py has KV_FILES list with Builder.load_file calls (lines 70-72 for run/axes_setup/parameters)
- Background threading: all controller I/O via jobs.submit(), UI updates via Clock.schedule_once()
- HMI one-shot variable pattern: set var=0 to trigger, DMC resets to 1

### Integration Points
- `screens/__init__.py` — switch exports from old names to FlatGrind*
- `main.py` KV_FILES list — remove old kv paths, add flat_grind kv loading via package import
- `tests/test_axes_setup.py`, `tests/test_parameters.py`, `tests/test_base_classes.py` — update imports
- `screens/run.py` (old) — BCompBarChart removed, becomes thin re-export wrapper

</code_context>

<specifics>
## Specific Ideas

- bComp bar chart is fundamentally different from deltaC bar chart — don't try to share a base class between them. Phase 21 designs bComp visualization from scratch.
- Serration/Convex packages will follow the exact same structure: screens/{machine_type}/ with __init__.py, run.py, axes_setup.py, parameters.py
- End-of-milestone cleanup audit is critical — old files, old kv, and any orphaned code should be reviewed after real hardware validates the new structure

</specifics>

<deferred>
## Deferred Ideas

- End-of-v3.0-milestone audit: clean up old screen files, old kv files, and any orphaned code after real-life usage confirms the new structure works
- Old ui/run.kv bComp widget references: noted for cleanup during audit
- BCompBarChart redesign: Phase 21 (Serration Screen Set)
- ProfilesScreen re-export or migration: not in scope (already machine-agnostic)

</deferred>

---

*Phase: 19-flat-grind-rename-and-kv-split*
*Context gathered: 2026-04-11*
