# Project Research Summary

**Project:** DMC Grinding GUI — v3.0 Multi-Machine HMI Refactor
**Domain:** Industrial Kivy HMI — per-machine-type screen architecture
**Researched:** 2026-04-11
**Confidence:** HIGH

## Executive Summary

This is a refactor of an industrial Raspberry Pi HMI (Python/Kivy/gclib) that controls a Galil motion controller for precision knife grinding. The v3.0 milestone splits the current single-screen-set architecture into per-machine-type screen sets for three machine types: 4-Axes Flat Grind (existing, hardware-validated), 3-Axes Serration Grind, and 4-Axes Convex Grind.

The recommended approach is static kv load at startup with Python-side type routing: all nine machine-specific kv files loaded once at build time, distinct Python class names per machine type (FlatGrindRunScreen, SerrationRunScreen, ConvexRunScreen), and a screen-set swap mechanism that removes the old machine's screens and adds the new machine's screens under canonical names ("run", "axes_setup", "parameters"). This eliminates the current `if machine_type == ...` branching without the fragility of runtime kv unload/reload.

The primary risk is Flat Grind regression during base class extraction. The existing screens are 90% hardware-validated — inserting a base class changes Python MRO. Mitigation: strict phase ordering (extract base, validate Flat Grind, then fork for other machines). Secondary risk: Serration bComp array name is unknown (DMC program not yet provided).

## Key Findings

### Recommended Stack

No new packages required. The refactor uses only existing Kivy 2.2+ ScreenManager API and Python inheritance. `Builder.unload_file()` was evaluated and rejected — Kivy docs state it does not affect already-instantiated widgets. The correct swap mechanism is `sm.add_widget()` / `sm.remove_widget()`.

One confirmed Kivy bug: `on_pre_enter` and `on_enter` defined in kv files silently do not fire for the first screen added to a ScreenManager (GitHub issue #2565, unresolved through Kivy 2.3.1). All lifecycle hooks must be in Python base classes.

**Core technologies:**
- `ScreenManager.add_widget/remove_widget` — runtime screen swap under canonical names
- Python base class inheritance — `BaseRunScreen`, `BaseAxesSetupScreen`, `BaseParametersScreen` for shared controller wiring
- `Builder.load_file()` at startup — all nine machine kv files loaded once; ~100-200ms on Pi 4

### Expected Features

**Must have (table stakes):**
- Per-machine Run/AxesSetup/Parameters screen classes (3 x 3 = 9 classes)
- Per-machine kv files (9 total) for layout independence
- Screen registry/loader mapping machine type to screen set
- Flat Grind behavior preserved unchanged
- Tab bar and auth unchanged (already machine-agnostic)

**Should have (differentiators):**
- `BaseRunScreen` mixin preventing triplicate bug fixes
- `screen_classes` key in `machine_config._REGISTRY`
- Subscription lifecycle enforced in base class (subscribe-on-enter, unsubscribe-on-leave)

**Defer to v3.x+:**
- Lazy kv loading (Pi memory optimization)
- Serration bComp write path (blocked on customer DMC program)
- Hot-swap machine type without restart (settings.json + restart covers 95% of use)

### Architecture Approach

Layered separation: shared chrome (TabBar, StatusBar, PINOverlay) above a ScreenManager holding shared screens plus the active machine's screen set. Base classes provide the 80% behavior identical across machine types. Machine-specific sub-packages provide only variant behavior. The shared HMI and state layers are unchanged.

**Major components:**
1. `screens/base/run_base.py` — poll subscription, plot setup/teardown, state subscription, HMI trigger helpers
2. `screens/base/axes_setup_base.py` — jog mechanics, teach logic; `_rebuild_axis_rows()` already data-driven
3. `screens/base/parameters_base.py` — dirty tracking, validation, apply, role gate; already data-driven
4. `main.py:_load_machine_screens()` — swap function: stop threads, remove old screens, instantiate new, navigate
5. `machine_config._REGISTRY["screen_classes"]` — maps canonical name to Python class per machine type

### Critical Pitfalls

1. **KV rule name collision** — if two kv files define `<ClassName>:` for the same class, the second silently shadows the first. Each machine screen needs a unique Python class name.
2. **Flat Grind regression from base class extraction** — inserting `BaseRunScreen` changes MRO. Mitigation: extract base first, validate on hardware, then rename in separate commit.
3. **Background thread leak on screen removal** — Kivy does not fire `on_pre_leave` on programmatic `remove_widget`. The swap function must explicitly call `_stop_pos_poll()` and `_stop_mg_reader()`.
4. **State subscription accumulation** — screens that subscribe but never unsubscribe leave dead listeners. Base class must enforce subscribe-in-enter / unsubscribe-in-leave.
5. **matplotlib figure not destroyed on screen swap** — `plt.close(fig)` must be called on outgoing run screen.

## Implications for Roadmap

### Phase 1: Base Class Extraction
**Rationale:** Riskiest phase — refactors working hardware-validated code. Doing it first isolates MRO risk before machine variants exist.
**Delivers:** `BaseRunScreen`, `BaseAxesSetupScreen`, `BaseParametersScreen` in `screens/base/`; subscription lifecycle enforced; existing screens inherit with zero functional change.
**Avoids:** Pitfall 2 (MRO regression), Pitfall 4 (subscription leak)

### Phase 2: Flat Grind Rename + KV Split
**Rationale:** Pure mechanical rename, no logic change. Establishes naming convention and reference implementation.
**Delivers:** `FlatGrindRunScreen`, `FlatGrindAxesSetupScreen`, `FlatGrindParametersScreen`; `ui/flat_grind/*.kv`; hardware validation confirms no regression.
**Avoids:** Pitfall 1 (kv rule collision)

### Phase 3: Screen Registry + Loader + main.py Wiring
**Rationale:** Integration point — resolves canonical names, removes static screen declarations from base.kv, makes app route correctly.
**Delivers:** `_load_machine_screens()` in main.py; `screen_classes` in machine_config; base.kv static entries removed; matplotlib teardown on swap.
**Avoids:** Pitfall 3 (thread leak), Pitfall 5 (figure leak)

### Phase 4: Serration Screen Set
**Rationale:** Second machine type per project machine order (Flat Grind -> Serration -> Convex).
**Delivers:** `SerrationRunScreen`, `SerrationAxesSetupScreen`, `SerrationParametersScreen`; `ui/serration/*.kv`; D-axis removed; bComp panel stubbed.

### Phase 5: Convex Screen Set
**Rationale:** Third machine type, last per machine order. 4-axis like Flat Grind.
**Delivers:** `ConvexRunScreen`, `ConvexAxesSetupScreen`, `ConvexParametersScreen`; `ui/convex/*.kv`; placeholder param_defs noted.

### Phase 6: Cleanup + Old File Deletion
**Rationale:** Delete legacy single-machine files only after all three machine types validated.
**Delivers:** Clean repository; old `screens/run.py`, `ui/run.kv` etc. deleted; test suite green.

### Phase Ordering Rationale

- Base class before rename: MRO changes are highest-risk; must be isolated
- Rename before loader: loader needs final class names to be stable
- Loader before Serration/Convex: those screens must be reachable through swap mechanism
- Serration before Convex: project machine order is non-negotiable
- Cleanup last: reference implementation must exist during all fork validation

### Research Flags

Standard patterns (skip research-phase):
- **Phase 1:** Standard Python inheritance
- **Phase 2:** Mechanical rename
- **Phase 3:** `sm.add_widget`/`remove_widget` fully documented

Needs customer input during execution:
- **Phase 4:** Serration bComp array name — customer must provide Serration DMC program
- **Phase 5:** Convex param_defs — customer must provide real specifications

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Kivy 2.2+ API verified from docs and builder source; GitHub #2565 confirmed |
| Features | HIGH | Direct codebase analysis of all screen classes and machine_config |
| Architecture | HIGH | All component boundaries verified against actual code |
| Pitfalls | HIGH | All pitfalls derived from existing codebase structure |

**Overall confidence:** HIGH

### Gaps to Address

- **Serration bComp array name:** Customer must provide Serration DMC program before Phase 4 bComp write path. Stub and flag.
- **Convex param_defs:** Placeholder copy of Flat Grind in machine_config. Phase 5 ships with placeholder; production needs real specs.
- **matplotlib figure teardown:** Must be added to Phase 3 swap function.

## Sources

### Primary (HIGH confidence)
- Kivy ScreenManager API 2.3.1 — add_widget, remove_widget, lifecycle events
- Kivy Builder source 2.3.1 — match_rule_name additive behavior, unload_file limitation
- GitHub Issue #2565 — on_pre_enter not fired for kv-declared first screen
- Direct codebase inspection: main.py, screens/*.py, ui/*.kv, machine_config.py, app_state.py

---
*Research completed: 2026-04-11*
*Ready for roadmap: yes*
