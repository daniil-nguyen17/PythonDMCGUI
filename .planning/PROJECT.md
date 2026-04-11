# DMC Grinding GUI

## What This Is

A touchscreen-first control application for Galil DMC-based knife grinding machines. Operators log in with a PIN, run grinding cycles while watching a live A/B position plot, and manage knife profiles — all from a locked-down industrial interface. Setup personnel get full machine configuration access (axes, parameters, profiles) behind a PIN overlay. Admin users manage accounts. Supports three machine types: 4-Axes Flat Grind, 4-Axes Convex Grind, and 3-Axes Serration Grind. Deployed on Raspberry Pi (kiosk mode, pending) and Windows.

## Core Value

An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion, zero access to things they shouldn't touch.

## Requirements

### Validated

- ✓ PIN-based user authentication with remember-last-user on startup — v1.0
- ✓ Three user roles: Operator, Setup, Admin with tiered access — v1.0
- ✓ Operator role: run cycles, monitor live plot — v1.0
- ✓ Setup role: full machine config (parameters, axes, calibration, profiles) — unlocks via PIN overlay, re-locks when done — v1.0
- ✓ Admin role: user management (create/delete users, assign PINs and roles) — v1.0
- ✓ Per-machine-type UI: screens adapt for Flat Grind, Convex Grind, and Serration Grind — v1.0
- ✓ Clean RUN page: live matplotlib A/B plot, cycle status, progress bar, operation log, big touchscreen action buttons — v1.0
- ✓ Unified Axes Setup page: sidebar axis selection, jog controls, teach rest/start points, quick actions — v1.0
- ✓ Grouped Parameters Setup page: cards for Geometry, Feedrates, Calibration with units and DMC codes — v1.0
- ✓ CSV profile import/export with machine-type validation and diff preview — v1.0
- ✓ Consistent dark theme with axis accent colors (A=orange, B=purple, C=cyan, D=yellow), 44dp+ touch targets — v1.0
- ✓ Matplotlib live position plot showing top-down A/B positions in real-time at 5 Hz — v1.0
- ✓ Navigation via tab bar (Run, Axes Setup, Parameters, Profiles, Users) replacing ActionBar + Spinner — v1.0

### Active

- [ ] Refactor screens into per-machine-type classes (Flat Grind, Serration, Convex) each with own .kv file
- [ ] Shared controller communication layer preserved (gclib, JobThread, poll, dmc_vars)
- [ ] Each machine type gets dedicated Run, Axes Setup, and Parameters screens
- [ ] Machine detection on connect (controller variable + local config) loads correct screen set
- [ ] Same tab bar, navigation behavior, and auth flow across all machine types
- [ ] Existing Flat Grind functionality preserved as-is (90% complete, fine-tuning only)
- [ ] Serration Grind screens created from Flat Grind base, tuned independently
- [ ] Convex Grind screens created from Flat Grind base, tuned independently

### Future

- [ ] Raspberry Pi kiosk mode (deferred from v1.0, pending hardware validation)
- [ ] Windows deployment support alongside Pi
- [ ] Easy SD card deployment

### Out of Scope

- Top-tier security (PIN is sufficient, no encryption/hashing required for in-house use)
- External JSON config files for deployment (hard-coding machine config is acceptable since machines are stable once production starts)
- Remote/network updates (updates are manual SD card swaps)
- Multi-language UI (Vietnamese labels replaced with English)
- Mobile/tablet app (Pi touchscreen and Windows desktop only)
- Undo/redo for parameter edits (controller is source of truth; "Read from Controller" is the real undo)
- Animated screen transitions (adds latency on industrial tool)

## Current Milestone: v3.0 Multi-Machine

**Goal:** Refactor the HMI into per-machine-type screen sets so each machine (Flat Grind, Serration, Convex) has its own dedicated Run, Axes Setup, and Parameters screens with independent .kv files — enabling independent fine-tuning per machine without breaking the others.

**Target features:**
- Per-machine screen classes: FlatGrindRunScreen, SerrationRunScreen, ConvexRunScreen (+ Axes Setup, Parameters for each)
- Per-machine .kv files for full layout independence
- Shared base layer: controller comms (gclib, JobThread, poll), auth, tab bar, navigation
- Machine detection on connect: reads controller variable or local config, loads correct screen set
- Screen registry/loader that swaps screen set based on detected machine type
- Existing Flat Grind screens preserved as-is — becomes the reference implementation
- Serration and Convex screens created from Flat Grind base, tuned independently

## Context

- **Current state:** v3.0 started — v2.0 shipped (Flat Grind integration complete), now refactoring into per-machine screen sets
- **DMC code:** `4 Axis Stainless grind.dmc` — state machine: #AUTO → #CONFIG → #PARAMS → #COMPED → #HOME → #MAIN → polling loop. Physical buttons on @IN[] pins, adding HMI variables as OR conditions
- **HMI variable pattern:** Named vars with `hmi` prefix (8-char DMC limit), default=1, HMI sends var=0 to trigger, DMC resets to 1 after entering the block
- **Tech stack:** Python 3.10+, Kivy 2.2+, gclib, matplotlib, kivy_matplotlib_widget
- **Controller:** All three machine types use the same Galil controller model, communicating via gclib. DMC programs run on the controller; the GUI sets arrays/variables and issues PA/BG commands
- **Threading model:** Background thread pool for all controller I/O, results posted back to UI thread via Clock.schedule_once. Plot redraws on separate 5 Hz clock from 10 Hz poll clock
- **Profile system:** CSV-based import/export with machine-type validation, diff preview, and cycle safety interlock
- **Machine config:** Registry pattern in machine_config.py — keyed by type string with plug-in param_defs per type
- **Auth:** AuthManager with JSON storage, plain-text PINs (per scope), 30-minute idle auto-lock
- **Pending:** Hardware validation on real DMC controller, then Pi kiosk deployment (Phase 8)

## Constraints

- **Platform:** Must run on Raspberry Pi 4/5 (touchscreen, kiosk) and Windows 11
- **Tech stack:** Python, Kivy (existing), gclib (existing), matplotlib + kivy_matplotlib_widget
- **Touch targets:** Minimum 44dp for all interactive elements (Pi touchscreen)
- **Controller I/O:** All gclib calls must remain off the UI thread (existing pattern)
- **Deployment:** Single SD card image for Pi; simple install for Windows
- **Screen resolution:** 1920x1080 primary target, must work on typical Pi touchscreen resolutions (800x480, 1024x600, 1280x800)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| PIN auth, not password | In-house use, security not top priority, touchscreen-friendly | ✓ Good — plain JSON, numpad overlay works well on touchscreen |
| Per-machine-type screens, not per-platform | Machines have different axis counts and workflows; Pi and Windows run same UI | ✓ Good — machine_config registry cleanly drives all screen adaptation |
| CSV for profiles, not database | Simple, portable, operators understand CSV files, matches DMC array format | ✓ Good — diff preview and machine-type validation work well |
| Matplotlib for live plot | Already a Python ecosystem tool, integrates with Kivy via kivy_matplotlib_widget | ✓ Good — 5 Hz redraw with draw_idle(), touch disabled for E-STOP safety |
| Tab navigation replacing ActionBar + Spinner | Cleaner, more touchscreen-friendly, matches mockup direction | ✓ Good — role-gated tabs update instantly on auth change |
| Kiosk mode on Pi | Operators should not access desktop, browser, or file explorer | — Deferred to after v2.0 |
| HMI one-shot variable pattern | OR physical @IN[] with hmi vars (default=1, send 0 to trigger, reset to 1) | — Pending |
| Flat Grind first, then Serration, then Convex | Build and validate one machine type end-to-end before moving to next | — Pending |
| Hard-coded machine config | Machines don't change once production starts; eliminates config file management | ✓ Good — settings.json stores type, first-launch picker for initial selection |
| Separate plot clock from poll clock | Decouples 5 Hz redraws from 10 Hz controller polling to protect E-STOP latency | ✓ Good — established in Phase 3 |
| Config.set before all Kivy imports | Kivy config is frozen on first Window import; kiosk fullscreen must be set in main.py top block | ✓ Good — pattern established, Pi kiosk config will extend it |

---
*Last updated: 2026-04-11 after v3.0 milestone start*
