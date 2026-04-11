---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Multi-Machine
status: unknown
stopped_at: Phase 18 context gathered
last_updated: "2026-04-11T11:32:50.011Z"
last_activity: 2026-04-11 — Roadmap defined, 6 phases, 26/26 requirements mapped
progress:
  total_phases: 16
  completed_phases: 9
  total_plans: 17
  completed_plans: 17
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-11)

**Core value:** An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion, zero access to things they shouldn't touch.
**Current focus:** v3.0 — Refactor into per-machine screen sets (Flat Grind, Serration, Convex)

## Current Position

```
Milestone : v3.0 Multi-Machine
Phase     : 18 — Base Class Extraction
Plan      : Not started
Status    : Roadmapped, awaiting plan
Progress  : [··········] 0% (0/6 phases)
```

Last activity: 2026-04-11 — Roadmap defined, 6 phases, 26/26 requirements mapped

## v3.0 Phase Map

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 18 | Base Class Extraction | ARCH-01, ARCH-02, ARCH-03, ARCH-04 | Not started |
| 19 | Flat Grind Rename and KV Split | FLAT-01, FLAT-02, FLAT-03, FLAT-04 | Not started |
| 20 | Screen Registry and Loader | LOAD-01, LOAD-02, LOAD-03, LOAD-04 | Not started |
| 21 | Serration Screen Set | SERR-01, SERR-02, SERR-03, SERR-04 | Not started |
| 22 | Convex Screen Set | CONV-01, CONV-02, CONV-03, CONV-04 | Not started |
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

Last session: 2026-04-11T11:32:49.999Z
Stopped at: Phase 18 context gathered
Resume file: .planning/phases/18-base-class-extraction/18-CONTEXT.md
Next action: `/gsd:plan-phase 18`
