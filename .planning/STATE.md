---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in-progress
stopped_at: Completed 01-02-PLAN.md
last_updated: "2026-04-04T06:30:00.000Z"
last_activity: 2026-04-04 — Plan 01-02 complete: app shell StatusBar+TabBar+ScreenManager with NoTransition
progress:
  total_phases: 8
  completed_phases: 0
  total_plans: 4
  completed_plans: 2
  percent: 5
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-04)

**Core value:** An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion, zero access to things they shouldn't touch.
**Current focus:** Phase 1 — Auth and Navigation

## Current Position

Phase: 1 of 8 (Auth and Navigation)
Plan: 2 of 4 in current phase
Status: In progress
Last activity: 2026-04-04 — Plan 01-02 complete: app shell StatusBar+TabBar+ScreenManager with NoTransition

Progress: [█░░░░░░░░░] 5%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01 P01 | 2 | 2 tasks | 8 files |
| Phase 01 P02 | 2 min | 2 tasks | 16 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Init: PIN auth (no hashing per scope) — in-memory dict via AuthManager, not sqlite
- Init: Matplotlib via FigureCanvasKivyAgg — only new PyPI dep; all draws on main thread only
- Init: RestPnt rename to DAxisPnt required before Phase 5 CSV work (hard pre-requisite flagged by research)
- Init: Machine type hard-coded at deployment — no runtime selector in UI
- [Phase 01]: AuthManager uses plain JSON with plain-text PINs (no hashing, no sqlite) per locked project decision
- [Phase 01]: setup_unlocked derived from role in set_auth() at call time, not stored separately
- [Phase 01]: MachineState auth fields use dataclass defaults to preserve backward compatibility
- [Phase 01-02]: Old screen files kept on disk (removed from imports only) to preserve git history for uncommitted changes
- [Phase 01-02]: TabBar defaults to admin role until Plan 03 wires real auth
- [Phase 01-02]: StatusBar.update_from_state uses getattr defaults — tolerates MachineState without current_user/current_role

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 3 (Matplotlib): Pi performance benchmarking required — confirm draw_idle() is sufficient or blit animation needed
- Phase 4 (Axes Setup): RestPnt → DAxisPnt rename may require changes to DMC controller program; confirm scope before starting
- Phase 8 (Kiosk): Pi OS Bookworm Wayland/X11 transition — exact kiosk lockout procedure depends on Pi OS version at deploy time

## Session Continuity

Last session: 2026-04-04T06:30:00.000Z
Stopped at: Completed 01-02-PLAN.md
Resume file: .planning/phases/01-auth-and-navigation/01-02-SUMMARY.md
