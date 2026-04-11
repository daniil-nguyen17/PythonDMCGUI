# Phase 18: Base Class Extraction - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Extract BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen with shared controller wiring, poll subscription, and lifecycle hooks. Existing screens inherit from these bases with no behavior change. No rename, no kv split, no new machine screen classes yet.

</domain>

<decisions>
## Implementation Decisions

### Extraction boundary
- **BaseRunScreen**: thin — owns controller/state ObjectProperties, MachineState subscribe/unsubscribe lifecycle, _on_state_change dispatch only. Does NOT own pos_poll, mg_reader, matplotlib, deltaC/bComp, or cycle controls. Machine-specific screens own all of those.
- **BaseAxesSetupScreen**: includes jog infrastructure — owns controller/state properties, on_pre_enter/on_leave lifecycle, jog_axis() with axis_list from machine_config, and the CPM read pattern. Serration/Convex inherit jog for free, only customize axis rows and teach points.
- **BaseParametersScreen**: includes card builder + dirty tracking — owns controller/state properties, lifecycle, build_param_cards(), validate_field(), dirty tracking, apply_to_controller(), read_from_controller(). All of these already use machine_config dynamically.
- Existing RunScreen/AxesSetupScreen/ParametersScreen keep their current names and inherit from the new bases. No rename in this phase (Phase 19 handles FlatGrind* rename). Isolates MRO risk.
- _BaseBarChart and DeltaCBarChart are Flat Grind-specific — move to screens/flat_grind_widgets.py along with DELTA_C_* constants and stone_window_for_index()
- BCompBarChart and BCOMP_* constants are Serration-specific — stay in run.py for now, move to serration in Phase 21
- bComp is NOT a Flat Grind feature — remove from flat_grind_widgets.py, defer to Serration phase

### Setup enter/exit pattern
- Shared SetupScreenMixin class with _enter_setup_if_needed() and _exit_setup_if_needed() methods
- Mixin includes the motion guard (skip hmiSetp if STATE_GRINDING or STATE_HOMING)
- Mixin owns the canonical _SETUP_SCREENS frozenset as a class attribute (currently duplicated in axes_setup.py and parameters.py)
- BaseAxesSetupScreen and BaseParametersScreen both use SetupScreenMixin
- BaseRunScreen does NOT use SetupScreenMixin (Run page doesn't enter setup mode)
- ProfilesScreen NOT wired to mixin in this phase — leave for later

### File organization
- All base classes in a single file: screens/base.py (BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen, SetupScreenMixin)
- Flat Grind-specific widgets and constants in: screens/flat_grind_widgets.py (DeltaCBarChart, _BaseBarChart, DELTA_C_* constants, stone_window_for_index())
- No new directories created in this phase

### Subscription lifecycle
- Base class subscribes to MachineState automatically in on_pre_enter, unsubscribes in on_leave (ARCH-02 compliance)
- Subclasses override _on_state_change(state) to handle their specific needs
- Base wraps subscription callback with Clock.schedule_once so subclasses can safely update Kivy widgets in their handler
- Base on_leave logs a warning if _state_unsub is still set when it shouldn't be (debug safety net for pitfall #4)
- Subscribe regardless of controller connectivity — handles reconnect case
- controller and state ObjectProperties defined on each base class (not a separate mixin)
- No abstract cleanup hooks — standard super() pattern for thread teardown in subclasses

### Claude's Discretion
- Exact method signatures and docstrings on base class methods
- Internal implementation details of SetupScreenMixin
- Whether _on_state_change receives the full MachineState or specific changed fields
- Test structure and approach for verifying no behavior change

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MachineState.subscribe()` / `unsubscribe()` pattern in app_state.py — base class wraps this
- `jobs.submit()` from utils/jobs.py — all background thread work uses this
- `machine_config.get_axis_list()` and `machine_config.get_param_defs()` — already machine-type-aware
- `_SETUP_SCREENS` frozenset — duplicated in axes_setup.py and parameters.py, to be consolidated into mixin

### Established Patterns
- ObjectProperty injection: main.py sets controller/state on screens after ScreenManager build
- Background threading: all controller I/O via jobs.submit(), UI updates via Clock.schedule_once()
- Smart setup enter/exit: check dmc_state before firing hmiSetp, check next_screen before firing hmiExSt
- HMI one-shot variable pattern: set var=0 to trigger, DMC resets to 1

### Integration Points
- screens/__init__.py — may need to export new base classes
- run.py — will import from base.py (BaseRunScreen) and flat_grind_widgets.py (moved widgets)
- axes_setup.py — will import from base.py (BaseAxesSetupScreen, SetupScreenMixin)
- parameters.py — will import from base.py (BaseParametersScreen, SetupScreenMixin)
- main.py — no changes needed (injection pattern unchanged, class names unchanged)

</code_context>

<specifics>
## Specific Ideas

- bComp is Serration-specific, not Flat Grind — ensure clean separation when moving widgets
- Jog infrastructure in BaseAxesSetupScreen should use mc.get_axis_list() so Serration (3-axis) and Convex (4-axis) inherit correct behavior automatically
- Card builder in BaseParametersScreen already reads from mc.get_param_defs() which returns machine-type-specific params — no customization needed per machine type for basic card layout

</specifics>

<deferred>
## Deferred Ideas

- ProfilesScreen wiring to SetupScreenMixin — not in Phase 18 scope
- BCompBarChart move to Serration module — Phase 21
- Base class for ProfilesScreen/UsersScreen — out of scope (already machine-agnostic per REQUIREMENTS.md)

</deferred>

---

*Phase: 18-base-class-extraction*
*Context gathered: 2026-04-11*
