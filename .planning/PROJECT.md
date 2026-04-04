# DMC Grinding GUI

## What This Is

A touchscreen-first control application for Galil DMC-based knife grinding machines. It provides operators with a simple, locked-down interface to run grinding cycles, monitor live axis positions, and adjust runtime parameters — while giving setup personnel full machine configuration access behind a PIN. Targets three machine types: 4-Axes Flat Grind, 4-Axes Convex Grind, and 3-Axes Serration Grind. Deployed on Raspberry Pi (kiosk mode) and Windows.

## Core Value

An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion, zero access to things they shouldn't touch.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] PIN-based user authentication with remember-last-user on startup
- [ ] Three user roles: Operator, Setup, Admin with tiered access
- [ ] Operator role: run cycles, monitor live plot, adjust basic runtime values (speed override, etc.)
- [ ] Setup role: full machine config (parameters, axes, calibration, profiles) — unlocks via PIN overlay, re-locks when done
- [ ] Admin role: user management (create/delete users, assign PINs and roles)
- [ ] Per-machine-type UI: separate screen sets for Flat Grind, Convex Grind, and Serration Grind
- [ ] Clean RUN page: live matplotlib A/B top-down position plot, cycle status, progress bar, operation log, big touchscreen action buttons (Start, Pause, Go to Rest, E-STOP)
- [ ] Unified Axes Setup page: sidebar for axis selection, jog controls (arrows + slider + step size), teach rest/start points, quick actions (Go to Rest All, Go to Start All, Home All)
- [ ] Grouped Parameters Setup page: cards for Geometry, Feedrates, Calibration, Positions, Safety with units and DMC variable codes visible
- [ ] CSV profile import/export: load a CSV with DMC array names and values, export current values for reuse across knife profiles
- [ ] Raspberry Pi kiosk mode: boot straight into app, full-screen, no desktop/browser/file explorer access for operators
- [ ] Windows deployment support alongside Pi
- [ ] Easy SD card deployment: install program on SD card, insert into Pi, runs on startup
- [ ] Consistent dark theme with accent colors per axis (A=orange, B=purple, C=cyan, D=yellow), touch-friendly 44dp+ targets
- [ ] Matplotlib live position plot showing top-down A/B axis positions in real-time
- [ ] Navigation via tab bar (Run, Axes Setup, Parameters, Diagnostics) replacing current ActionBar + Spinner pattern

### Out of Scope

- Top-tier security (PIN is sufficient, no encryption/hashing required for in-house use)
- External JSON config files for deployment (hard-coding machine config is acceptable since machines are stable once production starts)
- Remote/network updates (updates are manual SD card swaps)
- Multi-language UI (Vietnamese labels will be replaced with English)
- Mobile/tablet app (Pi touchscreen and Windows desktop only)

## Context

- **Existing codebase:** Python + Kivy app with gclib for Galil motion controller communication. Current screens: Setup (connection), Rest Point, Start Point, Axis D Setup, Parameters Setup, Buttons & Switches, Serration Knife (partial). Dark theme already established.
- **Controller:** All three machine types use the same Galil controller model, communicating via gclib. DMC programs run on the controller; the GUI sets arrays/variables and issues PA (Position Absolute) + BG (Begin) commands.
- **Operator workflow:** Operator loads a knife, selects profile (or uses current params), hits Start, watches the grind cycle, adjusts if needed based on results, repeats. Setup person comes in occasionally to tweak parameters or teach new positions.
- **Profile system:** No formal profiles yet. Parameters are individual variables/arrays. Loading a profile = uploading a CSV with DMC array names and values. Exporting = saving current state to CSV for later reuse.
- **Threading model:** Background thread pool for all controller I/O, results posted back to UI thread via Clock.schedule_once. This pattern should be preserved.
- **UI mockups:** HTML mockups created in `/mockups/` directory for RUN page, Axes Setup, and Parameters Setup — approved as design direction.

## Constraints

- **Platform:** Must run on Raspberry Pi 4/5 (touchscreen, kiosk) and Windows 11
- **Tech stack:** Python, Kivy (existing), gclib (existing), matplotlib (new for live plot)
- **Touch targets:** Minimum 44dp for all interactive elements (Pi touchscreen)
- **Controller I/O:** All gclib calls must remain off the UI thread (existing pattern)
- **Deployment:** Single SD card image for Pi; simple install for Windows
- **Screen resolution:** 1920x1080 primary target, must work on typical Pi touchscreen resolutions (800x480, 1024x600, 1280x800)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| PIN auth, not password | In-house use, security not top priority, touchscreen-friendly | — Pending |
| Per-machine-type screens, not per-platform | Machines have different axis counts and workflows; Pi and Windows run same UI | — Pending |
| CSV for profiles, not database | Simple, portable, operators understand CSV files, matches DMC array format | — Pending |
| Matplotlib for live plot | Already a Python ecosystem tool, integrates with Kivy via FigureCanvasKivyAgg | — Pending |
| Tab navigation replacing ActionBar + Spinner | Cleaner, more touchscreen-friendly, matches mockup direction | — Pending |
| Kiosk mode on Pi | Operators should not access desktop, browser, or file explorer | — Pending |
| Hard-coded machine config | Machines don't change once production starts; eliminates config file management | — Pending |

---
*Last updated: 2026-04-04 after initialization*
