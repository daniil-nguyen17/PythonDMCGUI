---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Multi-Machine
status: unknown
stopped_at: Completed 22-02-PLAN.md
last_updated: "2026-04-13T02:10:40.327Z"
last_activity: 2026-04-13 — Phase 22 Plan 02 complete; ConvexRunScreen full implementation, run.kv with MatplotFigure/DeltaC/ConvexAdjustPanel/D-axis rows, 19 tests passing
progress:
  total_phases: 16
  completed_phases: 14
  total_plans: 27
  completed_plans: 27
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-11)

**Core value:** An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion, zero access to things they shouldn't touch.
**Current focus:** v3.0 — Refactor into per-machine screen sets (Flat Grind, Serration, Convex)

## Current Position

```
Milestone : v3.0 Multi-Machine
Phase     : 22 — Convex Screen Set
Plan      : 02/02 complete
Status    : Phase 22 Complete — ConvexRunScreen full implementation, run.kv, 19 tests passing
Progress  : [██████████] 100% (27/27 plans)
```

Last activity: 2026-04-13 — Phase 22 Plan 02 complete; ConvexRunScreen full implementation, run.kv with MatplotFigure/DeltaC/ConvexAdjustPanel/D-axis rows, 19 tests passing

## v3.0 Phase Map

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 18 | Base Class Extraction | ARCH-01, ARCH-02, ARCH-03, ARCH-04 | Complete (2/2 plans) |
| 19 | Flat Grind Rename and KV Split | FLAT-01, FLAT-02, FLAT-03, FLAT-04 | Complete (2/2 plans) |
| 20 | Screen Registry and Loader | LOAD-01, LOAD-02, LOAD-03, LOAD-04 | Complete (2/2 plans) |
| 21 | Serration Screen Set | SERR-01, SERR-02, SERR-03, SERR-04 | Complete (2/2 plans) |
| 22 | Convex Screen Set | CONV-01, CONV-02, CONV-03, CONV-04 | Complete (2/2 plans) |
| 23 | Controller Communication Optimization | COMM-01, COMM-02, COMM-03, COMM-04, COMM-05, COMM-06 | Not started |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
v1.0 phase-level decisions archived in `.planning/milestones/v1.0-ROADMAP.md`.
v2.0 phase-level decisions archived in `.planning/milestones/v2.0-ROADMAP.md`.

Decisions affecting current work (v3.0):
- Per-machine screen classes with own .kv files — full layout independence for fine-tuning
- Shared controller communication layer (gclib, JobThread, poll, dmc_vars) preserved unchanged
- Existing Flat Grind screens become reference implementation — Phase 18 extracts base, Phase 19 renames, Phase 20 wires loader
- Serration before Convex — project machine order is non-negotiable
- COMM phase (23) depends on Phase 18 only, not on Serration/Convex — can proceed once base classes stabilize
- Machine detection via controller variable + local config; switching requires restart (hot-swap deferred to v3.x)
- All lifecycle hooks in Python base classes only — never in .kv files (Kivy GitHub #2565: on_pre_enter silently skips for first screen added via kv)
- Builder.unload_file() rejected — does not affect instantiated widgets; swap uses sm.add_widget/remove_widget
- [Phase 18-base-class-extraction]: BaseRunScreen thin: no jog, no matplotlib, no setup mode. SetupScreenMixin has no __init__ to preserve cooperative MRO.
- [Phase 18-base-class-extraction]: BCompBarChart stays in run.py — Serration-specific, deferred to Phase 21.
- [Phase 18-02]: base.py uses module-level submit import so all jobs.submit() calls are patchable at dmccodegui.screens.base.submit — single patch target for all screen I/O in tests.
- [Phase 19-01]: Per-machine screen package pattern: screens/{machine}/__init__.py loads KV via Builder.load_file() before class imports, exports all screen classes.
- [Phase 19-01]: BCompBarChart and bComp methods removed from FlatGrindRunScreen — Serration-specific, deferred to Phase 21.
- [Phase 19-02]: Deferred KV loading: flat_grind/__init__.py exposes load_kv() instead of eager Builder.load_file() at import time. Called from main.py build() before Factory instantiation.
- [Phase 19-02]: Added STATE_SETUP gate to BaseAxesSetupScreen.jog_axis — documented in docstring but was missing from implementation.
- [Phase 20-screen-registry-and-loader]: cleanup() non-blocking thread stop: set _mg_stop_event, clear _mg_thread=None, no join — on_leave _stop_mg_reader keeps join for normal navigation
- [Phase 20-screen-registry-and-loader]: Convex and Serration use flat_grind placeholder screen_classes with Phase 21/22 TODO comments — importlib resolution verified immediately
- [Phase 20-screen-registry-and-loader]: _MACH_TYPE_MAP maps controller machType int (1/2/3) to type strings — verify on hardware
- [Phase 20-screen-registry-and-loader]: machType query failures and unknown values silently ignored — graceful degradation locked decision
- [Phase 20-screen-registry-and-loader]: _add_machine_screens called after Factory.RootLayout(); load_kv called before KV_FILES loop for correct KV registration order
- [Phase 21-serration-screen-set]: Copied flat_grind code into serration classes (no import from flat_grind) for full independence
- [Phase 21-serration-screen-set]: D-axis absent from serration/axes_setup.kv entirely — axis_row_d not created, ids.get() returns None gracefully
- [Phase 21]: BCompPanel is a scrollable BoxLayout list (not bar chart); D-axis absent from SerrationRunScreen; no matplotlib in serration run screen
- [Phase 22-convex-screen-set]: Convex package fully independent (no flat_grind imports); _CONVEX_PARAM_DEFS explicit list literal with placeholder comment; registry updated to real Convex class paths
- [Phase 22-convex-screen-set]: Convex run.kv adds D-axis position display rows not in flat_grind/run.kv — required for pos_d KV binding and pos_d_row serration visibility toggle

### Critical Pitfalls (from research)

1. KV rule name collision — two kv files with same `<ClassName>:` header, second silently shadows first. Each machine screen must have a unique Python class name.
2. Flat Grind regression from base class extraction — MRO change. Mitigation: extract base, validate on hardware, then rename in separate commit (Phase 19).
3. Background thread leak on screen removal — Kivy does not fire on_pre_leave on programmatic remove_widget. Swap function must explicitly call _stop_pos_poll() and _stop_mg_reader().
4. State subscription accumulation — dead listeners if screens subscribe but never unsubscribe. Base class enforces subscribe-in-enter / unsubscribe-in-leave.
5. Matplotlib figure not destroyed on screen swap — plt.close(fig) must be called on outgoing run screen in Phase 20 swap function.

### Research Flags (require hardware or customer input)

- Carried from v2.0: dual-handle approach, hmiJog pattern, array name case sensitivity
- Phase 21: Serration bComp array name — customer must provide Serration DMC program before bComp write path; stub and flag
- Phase 22: Convex param_defs — placeholder copy of Flat Grind in machine_config; production needs real customer specs
- Phase 23: GRecord wrapper — verify GRecord exists in gclib wrapper and audit existing screen usage before editing poll.py

### Pending Todos

- Start with `/gsd:plan-phase 18` — Base Class Extraction is the prerequisite for all other v3.0 phases

### Blockers/Concerns

- Real DMC controller hardware required for Serration and Convex validation (Phases 21, 22)
- Serration bComp array name unknown — customer has not yet provided Serration DMC program
- Convex param_defs are placeholders — production sign-off requires real customer specifications

## Session Continuity

Last session: 2026-04-13T02:09:37.488Z
Stopped at: Completed 22-02-PLAN.md
Resume file: None
Next action: Plan Phase 20 — Screen Registry and Loader
