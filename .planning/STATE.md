---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Multi-Machine
status: planning
stopped_at: Defining requirements
last_updated: "2026-04-11"
last_activity: 2026-04-11 — Milestone v3.0 started
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-11)

**Core value:** An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion, zero access to things they shouldn't touch.
**Current focus:** v3.0 — Refactor into per-machine screen sets (Flat Grind, Serration, Convex)

## Current Position

Milestone: v3.0 Multi-Machine
Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-11 — Milestone v3.0 started

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
v1.0 phase-level decisions archived in `.planning/milestones/v1.0-ROADMAP.md`.
v2.0 phase-level decisions archived in `.planning/milestones/v2.0-ROADMAP.md`.

Decisions affecting current work (v3.0):
- Per-machine screen classes with own .kv files — full layout independence for fine-tuning
- Shared controller communication layer (gclib, JobThread, poll, dmc_vars) preserved
- Existing Flat Grind screens become reference implementation — no changes to working code
- Serration and Convex screens created from Flat Grind base
- One Pi per machine, one app instance per machine
- Machine detection via controller variable + local config

### Research Flags (require hardware validation)

- Carried from v2.0: dual-handle approach, hmiJog pattern, array name case sensitivity
- v3.0: Serration and Convex DMC programs may differ from Flat Grind — variable names and state machine need validation per machine type

### Pending Todos

(None yet)

### Blockers/Concerns

- Real DMC controller hardware required for Serration and Convex validation
- DMC programs for Serration and Convex machines may need modifications similar to v2.0 Phase 9

## Session Continuity

Last session: 2026-04-11
Stopped at: Defining requirements
Resume file: None
Next action: Define requirements and create roadmap
