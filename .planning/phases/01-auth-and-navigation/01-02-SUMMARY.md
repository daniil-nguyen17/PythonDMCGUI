---
phase: 01-auth-and-navigation
plan: 02
subsystem: ui
tags: [kivy, kv-lang, screenmanager, navigation, dark-theme]

# Dependency graph
requires: []
provides:
  - StatusBar widget (connection status, user/role, banner ticker, E-STOP)
  - TabBar widget with role-based tab set via set_role()
  - Four placeholder screens: RunScreen, AxesSetupScreen, ParametersScreen, DiagnosticsScreen
  - New RootLayout: StatusBar + TabBar + ScreenManager(NoTransition)
  - TabBar wired to ScreenManager via current_tab binding
  - StatusBar wired to app.banner_text and state subscriber
affects:
  - 01-auth-and-navigation plan 03 (auth wiring replaces default admin role)
  - 02-run-screen (fills RunScreen placeholder)
  - 03-axes-setup (fills AxesSetupScreen placeholder)
  - 04-parameters (fills ParametersScreen placeholder)
  - 05-diagnostics (fills DiagnosticsScreen placeholder)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "StatusBar.update_from_state(state) — state subscriber pattern for widget updates"
    - "TabBar.set_role(role) — role-based tab rebuild, no-op if same role"
    - "KV_FILES list in main.py — ordered loading, base.kv always last"
    - "Screen placeholder pattern: Screen subclass + ObjectProperty controller/state"

key-files:
  created:
    - src/dmccodegui/screens/status_bar.py
    - src/dmccodegui/screens/tab_bar.py
    - src/dmccodegui/screens/run.py
    - src/dmccodegui/screens/axes_setup.py
    - src/dmccodegui/screens/parameters.py
    - src/dmccodegui/screens/diagnostics.py
    - src/dmccodegui/ui/status_bar.kv
    - src/dmccodegui/ui/tab_bar.kv
    - src/dmccodegui/ui/run.kv
    - src/dmccodegui/ui/axes_setup.kv
    - src/dmccodegui/ui/parameters.kv
    - src/dmccodegui/ui/diagnostics.kv
    - tests/test_main.py
  modified:
    - src/dmccodegui/ui/base.kv
    - src/dmccodegui/screens/__init__.py
    - src/dmccodegui/main.py

key-decisions:
  - "Old screen files kept on disk but removed from import pipeline — avoids breaking git history for files with uncommitted changes"
  - "TabBar defaults to admin role (all 4 tabs) until Plan 03 wires real auth"
  - "StatusBar.update_from_state uses getattr with defaults — tolerates MachineState without current_user/current_role until Plan 03 adds them"
  - "NoTransition confirmed via static file content test (no Kivy event loop needed)"

patterns-established:
  - "Widget state updates go through update_from_state(state) called via Clock.schedule_once from state subscriber"
  - "Role-gated UI via TabBar.set_role() — call with new role string to rebuild tabs"
  - "Tab navigation: TabBar.current_tab binding drives sm.current via setattr lambda"

requirements-completed:
  - NAV-01
  - NAV-02
  - NAV-03
  - NAV-04
  - NAV-05
  - UI-01
  - UI-02
  - UI-03
  - UI-04

# Metrics
duration: 2min
completed: 2026-04-04
---

# Phase 1 Plan 02: App Shell — StatusBar + TabBar + ScreenManager Summary

**Kivy app shell with StatusBar/TabBar replacing old ActionBar+Spinner, ScreenManager(NoTransition) with 4 placeholder screens, role-based tab visibility, and E-STOP wired to app.e_stop()**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-04T06:24:42Z
- **Completed:** 2026-04-04T06:26:30Z
- **Tasks:** 2
- **Files modified:** 16 (13 created, 3 modified)

## Accomplishments
- StatusBar widget: connection status (colored dot + text), user/role area, banner ticker, always-visible E-STOP
- TabBar widget: role-based set_role() method with ROLE_TABS dict; tab press wired to ScreenManager via Kivy binding
- Four placeholder screens (Run, Axes Setup, Parameters, Diagnostics) each with controller/state ObjectProperties
- base.kv completely rewritten — RootLayout now uses StatusBar + TabBar + ScreenManager(NoTransition)
- main.py KV_FILES updated, old screens removed from pipeline, wiring code added in build()
- NoTransition test passes — static content assertion, no event loop required

## Task Commits

Each task was committed atomically:

1. **Task 1: Create StatusBar, TabBar widgets and placeholder screens** - `3de9c39` (feat)
2. **Task 2: Rewrite base.kv, update main.py, screens/__init__.py, and add NoTransition test** - `3223daa` (feat)

## Files Created/Modified
- `src/dmccodegui/screens/status_bar.py` - StatusBar BoxLayout with update_from_state()
- `src/dmccodegui/screens/tab_bar.py` - TabBar with set_role() and _on_tab_press()
- `src/dmccodegui/screens/run.py` - RunScreen placeholder
- `src/dmccodegui/screens/axes_setup.py` - AxesSetupScreen placeholder
- `src/dmccodegui/screens/parameters.py` - ParametersScreen placeholder
- `src/dmccodegui/screens/diagnostics.py` - DiagnosticsScreen placeholder
- `src/dmccodegui/ui/status_bar.kv` - StatusBar KV rule with E-STOP button
- `src/dmccodegui/ui/tab_bar.kv` - TabBar KV rule (dark panel, dynamically populated)
- `src/dmccodegui/ui/run.kv` - RunScreen KV rule
- `src/dmccodegui/ui/axes_setup.kv` - AxesSetupScreen KV rule
- `src/dmccodegui/ui/parameters.kv` - ParametersScreen KV rule
- `src/dmccodegui/ui/diagnostics.kv` - DiagnosticsScreen KV rule
- `src/dmccodegui/ui/base.kv` - Rewritten: new RootLayout with NoTransition import
- `src/dmccodegui/screens/__init__.py` - Old imports removed, new screens exported
- `src/dmccodegui/main.py` - KV_FILES updated, wiring added in build()
- `tests/test_main.py` - NoTransition static content test (UI-04)

## Decisions Made
- Old screen .py files (rest.py, start.py, etc.) kept on disk but removed from __init__.py imports — avoids breaking git history for files with uncommitted local changes
- TabBar defaults to "admin" role (all 4 tabs) until Plan 03 wires real auth
- StatusBar.update_from_state() uses getattr with defaults to tolerate MachineState lacking current_user/current_role (those added by Plan 03)
- NoTransition verified via static file test — no Kivy event loop, no headless display needed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- App shell is complete and launchable with new navigation structure
- Plan 03 can now wire auth: replace `tab_bar.set_role("admin", "run")` with real user role on login
- Plan 03 can add current_user/current_role to MachineState; StatusBar.update_from_state() already handles them via getattr
- All placeholder screens ready for content injection in phases 2-5

---
*Phase: 01-auth-and-navigation*
*Completed: 2026-04-04*
