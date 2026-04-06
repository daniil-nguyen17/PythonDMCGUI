---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Flat Grind Integration
status: planning
stopped_at: Phase 11 context gathered
last_updated: "2026-04-06T05:27:52.444Z"
last_activity: 2026-04-06 — Roadmap created
progress:
  total_phases: 7
  completed_phases: 2
  total_plans: 6
  completed_plans: 6
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-06)

**Core value:** An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion, zero access to things they shouldn't touch.
**Current focus:** v2.0 — Wire HMI to DMC controller for 4-Axes Flat Grind machine

## Current Position

Milestone: v2.0 Flat Grind Integration
Phase: 9 — DMC Foundation (not started)
Plan: None (roadmap just created)
Status: Ready to plan Phase 9
Last activity: 2026-04-06 — Roadmap created

Progress (v2.0): [░░░░░░░░░░] 0% (0/6 phases)

## Milestone Summary

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 9 | DMC Foundation | DMC-01..DMC-06 | Not started |
| 10 | State Poll | POLL-01..POLL-04 | Not started |
| 11 | E-STOP Safety | SAFE-01..SAFE-03 | Not started |
| 12 | Run Page Wiring | RUN-01..RUN-07 | Not started |
| 13 | Setup Loop | SETP-01..SETP-08 | Not started |
| 14 | State-Driven UI | UI-01..UI-05 | Not started |

## Performance Metrics

**Velocity (v2.0):**
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
| Phase 09-dmc-foundation P01 | 22 | 2 tasks | 4 files |
| Phase 09 P02 | 2 | 2 tasks | 1 files |
| Phase 09-dmc-foundation P03 | 12 | 2 tasks | 6 files |
| Phase 10-state-poll P01 | 18 | 2 tasks | 5 files |
| Phase 10-state-poll P02 | 16 | 2 tasks | 5 files |
| Phase 10-state-poll P03 | 8 | 2 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
v1.0 phase-level decisions archived in `.planning/milestones/v1.0-ROADMAP.md`.

Decisions affecting current work (v2.0):
- HMI one-shot variable pattern: named vars with `hmi` prefix (8-char DMC limit), default=1, send 0 to trigger, DMC resets to 1 as first line inside triggered block
- No XQ direct calls — all triggers through HMI variable pattern only
- Flat Grind first, then Serration, then Convex
- Phase 8 (Pi kiosk) deferred until after v2.0 hardware validation
- DMC program modification is a hard prerequisite for all button wiring (Phase 9 before all others)
- E-STOP must use submit_urgent() — never queue behind normal jobs, never implement as HMI trigger variable
- State authority is hmiState from controller — Python-side cycle_running is derived, not authoritative
- Single gclib handle serialized through jobs FIFO worker — no concurrent handle access regardless of 2.4.x thread-safety claim
- BV (variable save to flash) only on explicit user save — never in poll loops, never automatic
- [Phase 09-dmc-foundation]: dmc_vars.py is the single source of truth for DMC variable names — screen files must import from here, never use raw string literals
- [Phase 09-dmc-foundation]: xfail marker on stale-string test keeps suite green until plan 09-03 migrates screen files
- [Phase 09]: hmiState set in #HOME subroutine at entry (=4) and before EN (=1); SULOOP overrides after return to restore hmiState=3
- [Phase 09]: Exit-setup button (@IN[32]) gets no HMI variable — deferred to Phase 13 SETP-08
- [Phase 09-dmc-foundation]: Absolute imports used for dmc_vars in screen files to satisfy plan artifact check
- [Phase 10-state-poll]: cycle_running is a @property on MachineState derived from dmc_state == STATE_GRINDING — never stored, controller is the single source of truth
- [Phase 10-state-poll]: DMC knife counting inline at grind completion (#DONE block) rather than Thread 2 observer — simpler and avoids inter-thread race conditions
- [Phase 10-state-poll]: Thread 2 (#THRD2) is a passive WT 100 observer placeholder — main thread subroutines retain ownership of all hmiState transitions
- [Phase 10-state-poll]: TYPE_CHECKING guard in poll.py avoids circular import: hmi/__init__.py does not eagerly import poll
- [Phase 10-state-poll]: 7 separate MG commands per poll cycle (not batch) — safe individual reads per RESEARCH.md recommendation
- [Phase 10-state-poll]: test_plot_buffer_only_during_cycle updated to use _apply_state with MachineState API instead of deleted _apply_ui

### Research Flags (require hardware validation)

- Phase 11 (E-STOP): If dual-handle approach chosen over priority queue, verify Galil firmware supports two concurrent GOpen TCP connections — MEDIUM confidence
- Phase 13 (Jog): hmiJog=0 vs direct PR/BG with _XQ==0 gate — cannot be determined from code alone, requires hardware validation
- Phase 9 (array names): startPt/restPt case sensitivity on this specific controller firmware version — verify on real hardware before committing rename approach

### Pending Todos

- Plan Phase 9: DMC Foundation

### Blockers/Concerns

- Real DMC controller hardware required to fully test integration (all phases)
- DMC variable names limited to 8 characters — constants in hmi/dmc_vars.py prevent typos

## Session Continuity

Last session: 2026-04-06T05:27:52.442Z
Stopped at: Phase 11 context gathered
Resume file: .planning/phases/11-e-stop-safety/11-CONTEXT.md
Next action: `/gsd:plan-phase 9`
