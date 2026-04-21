---
gsd_state_version: 1.0
milestone: v4.0
milestone_name: Packaging & Deployment
status: unknown
stopped_at: null
last_updated: "2026-04-21"
last_activity: 2026-04-21 — Milestone v4.0 started
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-21)

**Core value:** An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion, zero access to things they shouldn't touch.
**Current focus:** v4.0 — Package the HMI for Windows 11 and Raspberry Pi deployment

## Current Position

```
Milestone : v4.0 Packaging & Deployment
Phase     : Not started (defining requirements)
Plan      : —
Status    : Defining requirements
Progress  : [░░░░░░░░░░] 0%
```

Last activity: 2026-04-21 — Milestone v4.0 started

## v4.0 Phase Map

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| (TBD — roadmap not yet created) | | | |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
v1.0 phase-level decisions archived in `.planning/milestones/v1.0-ROADMAP.md`.
v2.0 phase-level decisions archived in `.planning/milestones/v2.0-ROADMAP.md`.
v3.0 phase-level decisions archived in `.planning/milestones/v3.0-ROADMAP.md` (pending archive).

Decisions affecting current work (v4.0):
- Bundle Python + all deps into Windows installer (size doesn't matter, zero pre-reqs on target)
- gclib must be bundled or installed automatically — user has only used system-wide install
- Pi has internet during setup — can pip install from PyPI
- 3 Pi delivery methods (USB/SCP, SD image, git clone) — all must coexist without interfering
- Kiosk mode on Pi (fullscreen, no desktop access)
- Auto-detect screen resolution with manual override for 7"/10"/15" displays
- Exclude .md, .planning/, tests/ from package; DMC/Excel as optional separate bundle

### Critical Pitfalls (from research)

(Pending research)

### Research Flags (require hardware or customer input)

- gclib installation on Pi (system-wide .so vs venv-compatible wheel)
- gclib bundling in PyInstaller (hidden imports, .dll/.so discovery)
- Kivy on Pi ARM (GPU acceleration, touchscreen driver compatibility)
- matplotlib backend on Pi kiosk (headless vs framebuffer)

### Pending Todos

- Define requirements, create roadmap, then `/gsd:plan-phase [N]`

### Blockers/Concerns

- gclib packaging is the biggest unknown — may need custom build steps per platform
- Pi touchscreen driver compatibility varies by display model
- Kivy GPU acceleration on Pi may require specific Mesa/EGL config

## Session Continuity

Last session: 2026-04-21
Stopped at: null
Resume file: None
Next action: Define requirements → Create roadmap
