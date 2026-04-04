# Roadmap: DMC Grinding GUI

## Overview

Starting from a partially-built Kivy application with existing screens for setup, rest, axes, parameters, and serration — this roadmap delivers a production-ready industrial HMI. The journey: lock down access with PIN auth and role-aware navigation first, then build the operator-facing RUN page and live position plot, then give Setup personnel unified axes and parameter tools, then add CSV profiles, then support all three machine types, then add admin user management, and finally package for Pi kiosk deployment. Every feature has a home before it is built.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Auth and Navigation** - PIN login, three-tier roles, tab bar replacing ActionBar+Spinner
- [x] **Phase 2: RUN Page** - Cycle controls, live axis positions, cycle status, Knife Grind Adjustment, E-STOP everywhere (completed 2026-04-04)
- [x] **Phase 3: Live Matplotlib Plot** - Embedded A/B position plot with Pi performance validation (completed 2026-04-04)
- [x] **Phase 4: Axes Setup and Parameters** - Unified jog/teach screen and grouped parameter editor for Setup role (completed 2026-04-04)
- [ ] **Phase 5: CSV Profile System** - Safe import/export of knife profiles with machine-type validation
- [ ] **Phase 6: Machine-Type Differentiation** - Full support for Flat Grind, Convex Grind, and Serration Grind variants
- [ ] **Phase 7: Admin and User Management** - Admin screen for user CRUD and PIN assignment
- [ ] **Phase 8: Pi Kiosk and Deployment** - Kiosk lockout, systemd autostart, SD card packaging

## Phase Details

### Phase 1: Auth and Navigation
**Goal**: Operators and Setup personnel can identify themselves with a PIN and the UI shows only what they are allowed to touch
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, NAV-01, NAV-02, NAV-03, NAV-04, NAV-05, UI-01, UI-02, UI-03, UI-04
**Success Criteria** (what must be TRUE):
  1. User can tap a PIN on a touchscreen numpad overlay to log in — no physical keyboard required
  2. App pre-selects the last logged-in user on startup so returning operators skip user selection
  3. Operator sees only the Run tab; Setup sees Run, Axes Setup, and Parameters; tab bar updates immediately on role change
  4. Setup user can tap a PIN overlay on any restricted tab to unlock access, and access re-locks automatically after the configured inactivity timeout
  5. E-STOP button, connection status, and current user/role are visible on every screen at all times
**Plans:** 3/4 plans executed

Plans:
- [x] 01-01-PLAN.md — AuthManager + MachineState auth extension (pure Python + tests)
- [x] 01-02-PLAN.md — New app shell: StatusBar + TabBar + placeholder screens
- [x] 01-03-PLAN.md — PIN overlay, auth flow wiring, role-gated tabs, auto-lock
- [ ] 01-04-PLAN.md — Visual/functional verification checkpoint

### Phase 2: RUN Page
**Goal**: Operators can start and monitor a grinding cycle from a single screen with zero ambiguity about machine state
**Depends on**: Phase 1
**Requirements**: RUN-01, RUN-02, RUN-03, RUN-04, RUN-05, RUN-06
**Success Criteria** (what must be TRUE):
  1. Operator can tap Start, Pause, Go to Rest, and E-STOP — all buttons are 44dp+ and E-STOP is visually dominant and isolated
  2. Live axis position labels for A, B, C, D update at approximately 10 Hz with their assigned accent colors
  3. Cycle status panel shows current tooth, pass, depth, speed, elapsed time, and ETA during an active cycle
  4. Progress bar fills continuously from 0% to 100% as the cycle runs
  5. Operation log shows timestamped entries for cycle start, faults, parameter changes, and E-STOP in a scrollable view
**Plans:** 4/4 plans complete

Plans:
- [ ] 02-00-PLAN.md — Wave 0 test scaffolds (test_run_screen, test_delta_c_bar_chart, test_machine_state_cycle)
- [ ] 02-01-PLAN.md — MachineState cycle fields + RunScreen layout + polling + action buttons
- [ ] 02-02-PLAN.md — Knife Grind Adjustment panel (DeltaCBarChart widget)
- [ ] 02-03-PLAN.md — Visual/functional verification checkpoint

### Phase 3: Live Matplotlib Plot
**Goal**: Operators can see the grinding path in real time as a top-down A/B position plot embedded in the RUN page
**Depends on**: Phase 2
**Requirements**: RUN-07
**Success Criteria** (what must be TRUE):
  1. A/B axis positions trace a live path on the RUN page at 5-10 Hz with a rolling history buffer
  2. E-STOP button remains immediately responsive while the plot is actively updating (no frozen touch)
  3. Plot renders correctly at both 1920x1080 and typical Pi touchscreen resolutions (800x480, 1024x600)
**Plans:** 1/1 plans complete

Plans:
- [ ] 03-01-PLAN.md — MatplotFigure widget, rolling buffer, 5 Hz redraw clock + tests

### Phase 4: Axes Setup and Parameters
**Goal**: Setup personnel can jog any axis, teach rest and start points, and edit all machine parameters from clean unified screens
**Depends on**: Phase 1
**Requirements**: AXES-01, AXES-02, AXES-03, AXES-04, AXES-05, AXES-06, PARAM-01, PARAM-02, PARAM-03, PARAM-04, PARAM-05, PARAM-06, PARAM-07
**Success Criteria** (what must be TRUE):
  1. Setup user can select any axis from a sidebar and jog it with arrow buttons, a slider, or a step size selector (x1, x10, x100) — all from one screen
  2. Setup user can tap a Teach button to capture the current physical position as the Rest Point or Start Point for the selected axis
  3. Quick action buttons (Go to Rest All, Go to Start All, Home All) move all axes with a single tap
  4. Parameters page shows all values grouped into Geometry, Feedrates, Calibration, Positions, and Safety cards — each row shows human-readable name, DMC code, editable field, and unit
  5. Invalid parameter inputs are flagged with a red border immediately on entry; unsaved changes are highlighted amber with a change counter
**Plans:** 3/3 plans complete

Plans:
- [ ] 04-01-PLAN.md — AxesSetupScreen: sidebar, jog, teach, quick actions, live polling + tests
- [ ] 04-02-PLAN.md — ParametersScreen: grouped cards, dirty tracking, validation, apply/read + tests
- [ ] 04-03-PLAN.md — Visual/functional verification checkpoint

### Phase 5: CSV Profile System
**Goal**: Setup personnel can save the current knife setup to a CSV and reload it later without re-entering values
**Depends on**: Phase 4
**Requirements**: CSV-01, CSV-02, CSV-03, CSV-04, CSV-05
**Success Criteria** (what must be TRUE):
  1. Setup user can export all current parameter values to a CSV file that is human-readable and Excel-compatible
  2. Setup user can import a CSV to load a knife profile — a confirmation dialog showing a diff of changes appears before anything is sent to the controller
  3. Import is blocked and shows a clear error when the CSV's machine type header does not match the current machine
  4. Import button is disabled (greyed out) while a grinding cycle is actively running
**Plans:** 1/3 plans executed

Plans:
- [ ] 05-01-PLAN.md — Pure Python CSV engine: export, parse, diff, validate (TDD)
- [ ] 05-02-PLAN.md — ProfilesScreen UI + tab bar integration + controller wiring
- [ ] 05-03-PLAN.md — Visual/functional verification checkpoint

### Phase 6: Machine-Type Differentiation
**Goal**: The app correctly adapts its RUN page, axes controls, and parameter groups to whichever of the three machine types it is deployed on
**Depends on**: Phase 4
**Requirements**: MACH-01, MACH-02, MACH-03
**Success Criteria** (what must be TRUE):
  1. On a 4-Axes Flat Grind deployment, the RUN page and Axes Setup show all four axes with Flat Grind parameter groups
  2. On a 4-Axes Convex Grind deployment, the RUN page and Axes Setup show all four axes with Convex Grind parameter groups
  3. On a 3-Axes Serration Grind deployment, the RUN page and Axes Setup show only the three relevant axes with Serration parameter groups
  4. Machine type is fixed at deployment (hard-coded) — no runtime machine-type selector appears in the UI
**Plans**: TBD

### Phase 7: Admin and User Management
**Goal**: Admin users can create, delete, and update user accounts and PINs without touching files or code
**Depends on**: Phase 1
**Requirements**: AUTH-07, AUTH-08
**Success Criteria** (what must be TRUE):
  1. Admin user can open a dedicated user management screen (behind Admin PIN) to view all existing users
  2. Admin user can create a new user by entering a name, PIN, and role assignment
  3. Admin user can delete a user or change their PIN and role from the management screen
**Plans**: TBD

### Phase 8: Pi Kiosk and Deployment
**Goal**: The app boots automatically on a Raspberry Pi into a locked-down kiosk with no path for operators to reach the desktop, and installs from an SD card
**Depends on**: Phase 6
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04, DEPLOY-05
**Success Criteria** (what must be TRUE):
  1. Raspberry Pi boots directly into the app with no desktop, browser, or file manager accessible to the operator
  2. There is no keyboard shortcut, swipe, or tap sequence that exits the app without Setup or Admin credentials
  3. App restarts automatically if it crashes (systemd Restart=always)
  4. A technician can deploy the app to a new Pi by writing an SD card image and inserting it — no pip install or internet connection required
  5. The same codebase runs as a standard window on Windows 11 with no kiosk behavior
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

Note: Phase 3 depends on Phase 2; Phase 4 depends on Phase 1 (not Phase 2/3 — can start in parallel with Phase 3 if desired). Phase 5, 6, 7 all depend on Phase 4/1. Phase 8 depends on Phase 6.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Auth and Navigation | 3/4 | In Progress|  |
| 2. RUN Page | 4/4 | Complete   | 2026-04-04 |
| 3. Live Matplotlib Plot | 1/1 | Complete   | 2026-04-04 |
| 4. Axes Setup and Parameters | 3/3 | Complete   | 2026-04-04 |
| 5. CSV Profile System | 1/3 | In Progress|  |
| 6. Machine-Type Differentiation | 0/TBD | Not started | - |
| 7. Admin and User Management | 0/TBD | Not started | - |
| 8. Pi Kiosk and Deployment | 0/TBD | Not started | - |
