# Feature Landscape

**Domain:** Industrial HMI — per-machine-type screen set refactor (v3.0 Multi-Machine)
**Researched:** 2026-04-11
**Confidence:** HIGH (based on direct codebase analysis of existing machine_config.py, run.py,
axes_setup.py, parameters.py, main.py, and established Kivy ScreenManager/Builder patterns)

> **Scope note:** This document supersedes the v2.0 FEATURES.md for the v3.0 milestone.
> v2.0 features (HMI-to-controller wiring, XQ calls, hmi variable pattern, live polling,
> stone compensation, jog/teach, parameters write path) are already built and validated.
> This document covers only what is needed to refactor into per-machine-type screen sets.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that make the per-machine refactor actually work. Missing any of these means either
the wrong screens load for a machine type, or fine-tuning one machine breaks another.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Per-machine Run screen classes | Each machine type needs independent Run layout without `if is_serration()` branches. Serration has bComp controls; Convex has no D-axis. Sharing one class means any Serration-specific change risks breaking Flat Grind. | MEDIUM | Split `RunScreen` into `FlatGrindRunScreen`, `SerrationRunScreen`, `ConvexRunScreen`. Each inherits a shared `BaseRunScreen` mixin for common poll loop, plot, E-STOP, cycle controls. Machine-specific sections (bComp strip, deltaC bar, axis count) live only in their subclass. |
| Per-machine Axes Setup screen classes | Axis sidebar depends on axis count (A/B/C/D vs A/B/C). D-axis row show/hide is currently done in `_rebuild_axis_rows()` on every `on_pre_enter`. Per-machine subclass eliminates the runtime branch. | MEDIUM | Split `AxesSetupScreen` into `FlatGrindAxesSetupScreen`, `SerrationAxesSetupScreen`, `ConvexAxesSetupScreen`. Serration subclass simply never renders the D row — no runtime `get_axis_list()` query needed. |
| Per-machine Parameters screen classes | Param defs differ by machine type (Serration drops D-axis vars). Currently `ParametersScreen.on_pre_enter()` calls `mc.get_param_defs()` dynamically. Per-machine subclass bakes the correct defs in at class definition. | MEDIUM | Split `ParametersScreen` into `FlatGrindParametersScreen`, `SerrationParametersScreen`, `ConvexParametersScreen`. Each subclass provides a class-level `PARAM_DEFS` constant pointing to the correct `machine_config._*_PARAM_DEFS`. |
| Per-machine .kv files for each screen | Layout independence requires each screen subclass to have its own `.kv` file. Sharing a `.kv` file forces both machines to accept layout compromises from the other. | MEDIUM | Create `ui/flat_grind_run.kv`, `ui/serration_run.kv`, `ui/convex_run.kv` (same for axes_setup and parameters). Main .kv loader list in `main.py:KV_FILES` loads all of them at startup. |
| Machine detection on connect loads correct screen set | When a controller is connected, the HMI must swap to the screen set matching that machine's type. Currently `machine_config.get_active_type()` is read at startup from settings.json, but the ScreenManager always has the same screens regardless. | HIGH | A screen registry/loader replaces the current single-screen approach. On machine type selection (picker or settings.json), `ScreenManager.current` is pointed at `flat_grind_run` / `serration_run` / `convex_run` etc. Tab bar route names update accordingly. |
| Tab bar routes updated per machine type | The tab bar currently hard-codes screen names (`run`, `axes_setup`, `parameters`). With per-machine screens, the run tab must route to `flat_grind_run` or `serration_run` depending on detected type. | MEDIUM | Add a `set_machine_type(mtype)` method on `TabBar` that remaps route names without changing the visible tab labels. The method is called once after machine type is confirmed — same timing as the existing `state.machine_type = mtype` line in `main.py`. |
| Flat Grind screens preserved as-is | Existing Flat Grind behavior is 90% validated on hardware. The refactor must not change any Flat Grind logic — only extract it into named subclasses. | LOW | Rename `RunScreen` → `FlatGrindRunScreen`, `AxesSetupScreen` → `FlatGrindAxesSetupScreen`, `ParametersScreen` → `FlatGrindParametersScreen`. Update `.kv` `<RunScreen>` rule to `<FlatGrindRunScreen>` etc. No functional changes. |
| Shared controller comms layer unchanged | `GalilController`, `JobThread`, `ControllerPoller`, `dmc_vars.py`, `poll.py`, and `app_state.py` must not be touched. All three machine types share the same Galil controller model and communication protocol. | LOW | Enforced by keeping all comms in the base layer. Subclasses call the same `jobs.submit()`, `controller.cmd()`, `state.*` APIs. Only the screen-level Python classes and `.kv` files change. |
| Auth, PIN overlay, tab bar, status bar shared across machines | The role system (Operator/Setup/Admin), PIN overlay, tab visibility gates, and status bar are machine-independent. They must continue to work identically regardless of which screen set is loaded. | LOW | These widgets are already independent of `RunScreen` / `AxesSetupScreen`. No changes needed — confirmed by the fact that `pin_overlay.py`, `tab_bar.py`, and `status_bar.py` contain zero references to machine type. |
| First-launch machine type picker still works | The mandatory picker on first launch (when settings.json has no `machine_type`) must route to the correct screen set after selection. Currently it calls `mc.set_active_type()` then shows the PIN overlay — but does not update the ScreenManager's active screen names. | LOW | After `mc.set_active_type(mtype)`, the startup flow must also call the new screen loader to switch the ScreenManager's current screen to the correct machine's run screen. |

---

### Differentiators (Competitive Advantage)

Features that make the per-machine refactor more than a rename exercise — enabling real
independent tuning per machine type without coupling risk.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Shared `BaseRunScreen` mixin with machine-specific overrides | A clean base class for the 80% of Run screen behavior that is identical across all three machines (plot, cycle timer, E-STOP, poll, log). Subclasses only override what differs (bComp strip for Serration, deltaC for Flat/Convex). Prevents triplicate bug fixes. | MEDIUM | `BaseRunScreen(Screen)` holds `_start_pos_poll()`, `_stop_pos_poll()`, `_update_plot()`, `on_estop()`, `_cycle_timer_tick()`. `FlatGrindRunScreen(BaseRunScreen)` adds deltaC bar. `SerrationRunScreen(BaseRunScreen)` adds bComp strip. `ConvexRunScreen(BaseRunScreen)` adds convex-specific controls. |
| Lazy screen loading — only load active machine's screens | Loading all three machines' .kv files at startup is safe but loads unused widget trees into memory. Lazy loading reduces startup memory on Pi 4 (2 GB RAM, shared GPU). | MEDIUM | Instead of loading all 9 screen .kv files in `KV_FILES`, detect machine type from settings.json during `build()` and load only the 3 active machine .kv files. Fall back to loading all if unconfigured (first launch). Pi target makes this worth doing — Pi 4 with Kivy + matplotlib + gclib is memory-constrained. |
| Machine type shown in status bar at all times | Setup personnel and service technicians must immediately know which machine type the HMI is configured for — especially on shared test benches where the same Pi might be moved between machines. | LOW | `StatusBar` already has a machine-type tap area in `main.py` (`bind_machine_type_tap`). Confirm the `state.machine_type` string is passed to `StatusBar.update_from_state()` and displayed. Already partially implemented — needs verification that all three machine types display correctly, not just Flat Grind. |
| `has_bcomp` flag drives bComp strip visibility | The Serration machine has a B-axis compensation strip (`has_bcomp=True` in `_REGISTRY`). Rather than hard-coding "if serration, show bComp", use the registry flag. This means if a future 4th machine type needs bComp, it gets it for free. | LOW | `BaseRunScreen._on_state_update()` checks `mc.get_active_type()` → `_REGISTRY[type]["has_bcomp"]`. If True, show bComp strip widget. `FlatGrindRunScreen` and `ConvexRunScreen` never call this path because bComp is not in their layout. |
| Screen set hot-swap without app restart | When a Setup/Admin user changes machine type via the status bar picker mid-session, the ScreenManager swaps screen sets without restarting the app. Useful on shared test benches. | HIGH | This requires `ScreenManager.add_widget()` / `remove_widget()` at runtime, plus re-loading .kv rules for the new machine type. Kivy's `Builder.load_file()` is idempotent for the same file — but removing and re-adding screens while connected is complex. Defer unless customer explicitly requests it; settings.json + restart covers 95% of real-world scenarios. |
| Serration-specific `bComp` write verified against DMC | `has_bcomp=True` machines need to write to the `bComp` array on the controller. The exact array name and index range for the Serration DMC program is TBD (customer to provide). Flag this as needing verification before the Serration screen is considered complete. | LOW | Add a `# TODO: verify bComp array name and size from Serration DMC program` comment at the top of `SerrationRunScreen`. Stub the write path with `controller.cmd(f"bComp[{idx}]={val}")` as a placeholder — same pattern as deltaC writes on Flat Grind. |

---

### Anti-Features (Commonly Requested, Often Problematic)

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Single screen class with deep `if machine_type == "..."` branching | "Avoids code duplication — one screen, many modes." | Every Serration-specific change risks breaking Flat Grind code paths that share the same `if/else` tree. Testing becomes combinatorial. KV layouts become full of `opacity: 0 if ...` bindings that still consume memory. This is the current v2.0 approach and exactly what v3.0 is designed to escape. | Per-machine subclasses. Each class is independently testable. A bug in `SerrationRunScreen` cannot reach `FlatGrindRunScreen`. |
| Shared single .kv file with `opacity: 0 if not has_bcomp` | "Simpler than three .kv files — just toggle visibility." | Hidden widgets (opacity=0) still exist in the widget tree and consume layout passes, memory, and touch event processing. On Pi 4 this matters. More importantly, layout differences between machines (not just visibility) require different widget hierarchies. | Separate .kv files per machine type. Each .kv file only contains the widgets that machine needs. No dead widgets in the tree. |
| Runtime machine type switching without app restart | "Power user feature — switch machine types on the fly." | `Builder.load_file()` adds rules to the global registry. Removing them cleanly requires `Builder.unload_file()` which is fragile with complex inheritance hierarchies. ScreenManager widget teardown while polling is active risks race conditions with the JobThread. | Write the machine type to settings.json and prompt for restart. Restart is fast (< 5 seconds) and eliminates the entire class of teardown bugs. Industrial machines don't switch types mid-shift. |
| Three separate `main.py` entry points (one per machine) | "Each machine gets its own deployable app." | Triples maintenance burden. Auth, tab bar, status bar, poll loop — all duplicated. Bug fixes need to be applied in three places. SD card images diverge over time. | Single `main.py`, single app. Machine type selection at startup via the existing picker. All three screen sets registered in one ScreenManager. |
| Controller variable read to auto-detect machine type | "Let the DMC program tell the HMI what machine it is." | The three machines all use the same DMC program structure. There is no machine-type variable defined in the current DMC code. Adding one requires DMC program changes. The settings.json approach is already in place, costs zero DMC changes, and works correctly. | Keep settings.json as the source of truth. The first-launch picker forces setup personnel to confirm type once. After that it is automatic. |
| Per-machine-type tab sets (different tabs per machine) | "Serration doesn't need a Convex-specific tab, so hide it." | Tab sets are already role-gated (Operator vs Setup vs Admin), not machine-gated. The three machines use the same five tabs (Run, Axes Setup, Parameters, Profiles, Users). Adding machine-type gating to tabs creates a 3x3 matrix of configurations. | Keep the tab set identical across all machine types. The content of each tab's screen differs — the tab labels and counts do not. |

---

## Feature Dependencies

```
machine_config.py (_REGISTRY, get_active_type, get_param_defs, get_axis_list)
  └── already built, used by all three screen sets
  └── required by: per-machine param defs, bComp flag, axis count

Flat Grind screens (rename-only refactor)
  ├── FlatGrindRunScreen ← rename RunScreen, no logic change
  ├── FlatGrindAxesSetupScreen ← rename AxesSetupScreen, remove _rebuild_axis_rows() D-hide
  └── FlatGrindParametersScreen ← rename ParametersScreen, bake FLAT_PARAM_DEFS as class constant
  └── required before: Serration and Convex screens (they fork from Flat Grind as base)

Per-machine .kv files
  ├── ui/flat_grind_run.kv ← rename/copy from ui/run.kv
  ├── ui/serration_run.kv ← fork from flat_grind_run.kv, add bComp strip, remove D-axis refs
  ├── ui/convex_run.kv ← fork from flat_grind_run.kv, convex-specific controls
  └── same pattern for axes_setup and parameters
  └── required before: screen registry can route to correct class

Screen registry / loader (new in v3.0)
  ├── maps machine type string → (run_screen_name, axes_screen_name, params_screen_name)
  ├── called by: startup flow after mc.get_active_type() returns valid type
  ├── called by: first-launch picker on_selected callback
  └── required by: tab bar route update, sm.current navigation

Tab bar route update (set_machine_type method)
  └── requires: screen registry to know the correct screen names per type
  └── called after: screen registry loader completes

BaseRunScreen mixin
  ├── extracts: _start_pos_poll, _stop_pos_poll, _update_plot, _cycle_timer_tick, on_estop
  └── required before: FlatGrindRunScreen, SerrationRunScreen, ConvexRunScreen can inherit it

SerrationRunScreen
  ├── requires: BaseRunScreen mixin
  ├── requires: ui/serration_run.kv loaded
  ├── requires: bComp array name verified from Serration DMC program (customer to provide)
  └── forked from: FlatGrindRunScreen, adds bComp write path

ConvexRunScreen
  ├── requires: BaseRunScreen mixin
  ├── requires: ui/convex_run.kv loaded
  └── forked from: FlatGrindRunScreen, adapted for Convex geometry controls

Shared layer (unchanged)
  ├── GalilController, JobThread, ControllerPoller — no changes
  ├── app_state.MachineState — no changes (machine_type field already exists)
  ├── auth/AuthManager — no changes
  ├── pin_overlay.py, tab_bar.py, status_bar.py — no changes (already machine-agnostic)
  └── profiles.py, users.py, diagnostics.py — no changes
```

### Dependency Notes

- **Flat Grind first, then Serration, then Convex:** This is the established machine order from project memory (`project_v2_machine_order.md`). Flat Grind is the reference implementation. Serration and Convex fork from it and tune independently. Do not start Serration or Convex screens until Flat Grind rename-refactor is complete and verified.

- **Rename is the first and safest step:** The Flat Grind refactor is a pure rename — `RunScreen` → `FlatGrindRunScreen`, matching `.kv` rule rename, matching imports in `main.py`. Zero functional change. This gives a working baseline before any new screen subclasses are added.

- **KV_FILES list in main.py is the load manifest:** The `KV_FILES` list controls what gets registered with Kivy's `Builder`. Adding per-machine .kv files to this list is the mechanism for making new screen classes available. Order matters — `theme.kv` must remain first, `base.kv` must remain last.

- **ScreenManager screen names must be stable:** Tab bar and `sm.current` assignments use string names (`"run"`, `"axes_setup"`). If those names change to `"flat_grind_run"`, every `sm.current = "run"` assignment in `main.py`, `axes_setup.py`, `parameters.py`, and `tab_bar.py` must be updated. Plan for a controlled search-and-replace pass, not ad-hoc edits.

- **`_SETUP_SCREENS` frozensets need updating:** Both `axes_setup.py` and `parameters.py` maintain a `_SETUP_SCREENS` frozenset used to decide whether navigating away should send the exit-setup HMI command. When screen names change, these frozensets must be updated to include the new machine-specific screen names (e.g., `"flat_grind_axes_setup"` instead of `"axes_setup"`).

- **Serration bComp array name is TBD:** The Serration DMC program has not been provided. `has_bcomp=True` in the registry, but the actual array name, size, and write protocol are unknown. Serration screen must stub the bComp path and flag it for customer verification before production use.

---

## MVP Definition

### Launch With (v3.0 — Multi-Machine Refactor)

Minimum that makes each machine type independently tunable without cross-machine risk:

- [ ] `FlatGrindRunScreen`, `FlatGrindAxesSetupScreen`, `FlatGrindParametersScreen` extracted from existing classes — pure rename, zero functional change
- [ ] `ui/flat_grind_run.kv`, `ui/flat_grind_axes_setup.kv`, `ui/flat_grind_parameters.kv` created from existing .kv files — rule names updated to match new class names
- [ ] `main.py:KV_FILES` updated to load flat grind .kv files, screen names updated throughout
- [ ] `_SETUP_SCREENS` frozensets in `axes_setup.py` and `parameters.py` updated to new screen names
- [ ] Tab bar route names updated to match new Flat Grind screen names
- [ ] Existing Flat Grind behavior confirmed unchanged on hardware (regression test)
- [ ] `SerrationRunScreen`, `SerrationAxesSetupScreen`, `SerrationParametersScreen` created — forked from Flat Grind base, D-axis removed, bComp strip stubbed
- [ ] `ui/serration_*.kv` files created — D-axis row absent, bComp strip placeholder present
- [ ] `ConvexRunScreen`, `ConvexAxesSetupScreen`, `ConvexParametersScreen` created — forked from Flat Grind base
- [ ] `ui/convex_*.kv` files created
- [ ] Screen registry maps each `machine_config.MACHINE_TYPES` string to correct screen name triple
- [ ] Startup flow routes to correct screen set based on `mc.get_active_type()`
- [ ] First-launch picker routes to correct screen set after type selection

### Add After Screen Set Validation (v3.x)

- [ ] `BaseRunScreen` mixin extracted — once all three subclasses exist and common logic is visible
- [ ] Lazy .kv loading for active machine type only — after basic routing is proven correct
- [ ] Serration bComp write path — after customer provides Serration DMC program and array name

### Future Consideration (v4.0+)

- [ ] Hot-swap machine type without app restart — only if customer explicitly requires it
- [ ] Fourth machine type — registry pattern in `machine_config.py` already supports it

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Flat Grind rename-refactor (no logic change) | HIGH | LOW | P1 — foundation for everything else |
| Per-machine .kv files (Flat Grind first) | HIGH | LOW | P1 — enables independent tuning |
| Screen name updates in main.py, tab bar, frozensets | HIGH | LOW | P1 — app breaks without this |
| Screen registry / loader | HIGH | MEDIUM | P1 — required for routing to correct screens |
| Serration screen set (fork from Flat Grind) | HIGH | MEDIUM | P1 — second machine type, ordered by machine_order memory |
| Convex screen set (fork from Flat Grind) | HIGH | MEDIUM | P1 — third machine type |
| BaseRunScreen mixin extraction | MEDIUM | MEDIUM | P2 — reduces bug-fix duplication |
| Lazy .kv loading | LOW | MEDIUM | P3 — Pi memory optimization, not blocking |
| Hot-swap machine type | LOW | HIGH | P3 — defer unless explicitly required |

---

## Sources

- Direct codebase analysis: `machine_config.py` (registry, param_defs, axis lists, has_bcomp flag)
- Direct codebase analysis: `main.py` (KV_FILES load order, startup flow, machine type picker, screen injection)
- Direct codebase analysis: `screens/run.py`, `screens/axes_setup.py`, `screens/parameters.py` (existing adaptation patterns)
- Direct codebase analysis: `screens/tab_bar.py` (route names, _SETUP_SCREENS references)
- Project context: `.planning/PROJECT.md` — v3.0 milestone target features, machine order, key decisions
- Project memory: `project_v2_machine_order.md` — Flat Grind first, Serration second, Convex third
- Kivy ScreenManager documentation: Builder.load_file(), ScreenManager.add_widget() patterns (HIGH confidence — established Kivy patterns)
- ISA-101 HMI standards: per-mode screen organization patterns (MEDIUM confidence)

---

*Feature research for: per-machine-type screen set refactor, v3.0 Multi-Machine milestone*
*Researched: 2026-04-11*
