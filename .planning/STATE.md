---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Completed 04-03-PLAN.md — Phase 4 complete
last_updated: "2026-04-04T11:30:40.421Z"
last_activity: "2026-04-04 — Plan 01-03 complete: PIN overlay auth flow, role-gated tabs, idle auto-lock"
progress:
  total_phases: 8
  completed_phases: 4
  total_plans: 12
  completed_plans: 12
  percent: 8
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-04)

**Core value:** An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion, zero access to things they shouldn't touch.
**Current focus:** Phase 1 — Auth and Navigation

## Current Position

Phase: 1 of 8 (Auth and Navigation)
Plan: 3 of 4 in current phase
Status: In progress
Last activity: 2026-04-04 — Plan 01-03 complete: PIN overlay auth flow, role-gated tabs, idle auto-lock

Progress: [█░░░░░░░░░] 8%

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
| Phase 01 P03 | 4 min | 2 tasks | 8 files |
| Phase 02-run-page P00 | 2 | 2 tasks | 3 files |
| Phase 02-run-page P01 | 5 | 2 tasks | 3 files |
| Phase 02-run-page P02 | 159 | 2 tasks | 2 files |
| Phase 02-run-page P03 | 0 | 1 tasks | 2 files |
| Phase 03-live-matplotlib-plot P01 | 3 | 2 tasks | 3 files |
| Phase 04-axes-setup-and-parameters P01 | 20 | 2 tasks | 3 files |
| Phase 04 P02 | 244 | 2 tasks | 3 files |
| Phase 04-axes-setup-and-parameters P03 | 30 | 2 tasks | 6 files |

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
- [Phase 01-03]: PINOverlay user list uses opacity/disabled swap — avoids removing/re-adding widgets which can lose KV id bindings
- [Phase 01-03]: TabBar now defaults to operator role (real auth replaces temporary admin default from Plan 02)
- [Phase 01-03]: _tabs_for_role is a staticmethod for pure-Python testability without Kivy event loop
- [Phase 02-run-page]: Wave 0 scaffolds use direct imports inside test functions — defers Kivy initialization, avoids headless import failures
- [Phase 02-run-page]: test_machine_state_cycle.py kept Kivy-free — pure dataclass tests run in any CI environment without display
- [Phase 02-01]: DELTA_C constants and DeltaCBarChart stub added in Plan 02-01 to satisfy pre-written tests; full implementation deferred to Plan 02-02
- [Phase 02-01]: delta_c_offsets kept as plain list (not Kivy ListProperty) since Plan 02-02 owns the full widget binding
- [Phase 02-run-page]: DELTA_C_STEP updated from placeholder 10.0 to plan-specified 50 (int)
- [Phase 02-run-page]: delta_c_offsets promoted to ListProperty so KV bindings and canvas redraws fire correctly
- [Phase 02-run-page]: theme.text_muted does not exist on ThemeManager — correct attribute is theme.text_mid
- [Phase 02-run-page]: CYCLE_VAR_COMPLETION / MG pctDone removed — DMC controller lacks this variable
- [Phase 02-run-page]: Controller polling disabled in on_pre_enter — deferred until a cycle is actually running
- [Phase 03-live-matplotlib-plot]: kivy_matplotlib_widget 0.16.0 MatplotFigure used for live plot — Figure/Axes direct, no pyplot, draw_idle async redraws
- [Phase 03-live-matplotlib-plot]: 5 Hz plot clock separate from 10 Hz poll clock — decouples redraws from controller polling to protect E-STOP latency
- [Phase 03-live-matplotlib-plot]: Touch interaction fully disabled on MatplotFigure (touch_mode='none') — preserves E-STOP button responsiveness
- [Phase 04]: jog_axis uses PR+BG (position relative) per axis, never PA — locked decision
- [Phase 04]: Teach writes scalar DMC vars restPtA/B/C/D + BV burn; no download_array
- [Phase 04]: AXIS_CPM_DEFAULTS A=1200,B=1200,C=800,D=500; read live from controller, fall back to defaults
- [Phase 04-02]: backOff placed in Safety group only -- it is fundamentally a safety parameter (axis retreat from limit), not a geometry parameter
- [Phase 04-02]: Background job applies state changes directly without Clock.schedule_once -- Kivy property value assignments are thread-safe and this enables clean synchronous testing
- [Phase Phase 04-03]: Axis labels renamed from Feed/Lift/Cross/Rotation to Knife Length/Knife Curve/Grinder Up/Down/Knife Angle — matches actual machine motion purpose
- [Phase Phase 04-03]: Positions and Safety parameter groups removed — rest/start points set via Teach buttons in AxesSetupScreen, not typed manually
- [Phase Phase 04-03]: GROUP_COLORS dict applied to parameter cards: orange=Geometry, cyan=Feedrates, purple=Calibration — left-edge stripe + header + dim var label

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 3 (Matplotlib): Pi performance benchmarking required — confirm draw_idle() is sufficient or blit animation needed
- Phase 4 (Axes Setup): RestPnt → DAxisPnt rename may require changes to DMC controller program; confirm scope before starting
- Phase 8 (Kiosk): Pi OS Bookworm Wayland/X11 transition — exact kiosk lockout procedure depends on Pi OS version at deploy time

## Session Continuity

Last session: 2026-04-04T11:29:14.173Z
Stopped at: Completed 04-03-PLAN.md — Phase 4 complete
Resume file: None
