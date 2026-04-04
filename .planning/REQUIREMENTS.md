# Requirements: DMC Grinding GUI

**Defined:** 2026-04-04
**Core Value:** An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Authentication

- [x] **AUTH-01**: User can log in by entering a 4-6 digit PIN on a touchscreen numeric keypad overlay
- [x] **AUTH-02**: App remembers last logged-in user and pre-selects them on startup
- [x] **AUTH-03**: Three user roles exist: Operator, Setup, Admin — each with different access levels
- [x] **AUTH-04**: Operator can only access RUN page and view (not edit) parameters
- [x] **AUTH-05**: Setup user can unlock via PIN overlay to access axes setup, parameters, and machine config, then re-lock when done
- [x] **AUTH-06**: Setup session auto-locks after configurable inactivity timeout, returning to Operator view
- [ ] **AUTH-07**: Admin can create, delete, and modify users (assign PINs and roles)
- [ ] **AUTH-08**: Admin user management is accessible from a dedicated screen behind Admin PIN

### Navigation

- [x] **NAV-01**: App uses a persistent tab bar (Run, Axes Setup, Parameters, Diagnostics) replacing the ActionBar + Spinner pattern
- [x] **NAV-02**: E-STOP button is accessible from every screen via a persistent top bar or footer element
- [x] **NAV-03**: Tab visibility is role-aware — Operator sees Run tab only; Setup sees Run + Axes + Parameters; Admin sees all
- [x] **NAV-04**: Connection status (connected/disconnected + machine name) is always visible in the top bar
- [x] **NAV-05**: Current user name and role are always visible in the top bar with a switch-user button

### RUN Page

- [x] **RUN-01**: RUN page displays big touchscreen buttons for Start, Pause, Go to Rest, and E-STOP (all 44dp+ minimum)
- [x] **RUN-02**: E-STOP button is visually dominant (red, largest target) and isolated from other buttons to prevent accidental taps
- [x] **RUN-03**: Live axis positions (A, B, C, D) update at ~10 Hz with color-coded axis labels (A=orange, B=purple, C=cyan, D=yellow)
- [x] **RUN-04**: Cycle status panel shows current tooth, pass, depth, speed, elapsed time, and ETA
- [x] **RUN-05**: Progress bar shows overall cycle completion percentage
- [x] **RUN-06**: Operation log displays timestamped events (cycle start, faults, parameter changes, E-STOP) in a scrollable view
- [x] **RUN-07**: Live matplotlib plot shows top-down A/B axis positions in real-time with rolling buffer

### Axes Setup

- [x] **AXES-01**: Single unified axes setup screen with sidebar to select between A, B, C, D axes
- [x] **AXES-02**: Each axis view shows Rest Point, Start Point, and Current Position values
- [x] **AXES-03**: Jog controls with arrow buttons, slider, and selectable step size (x1, x10, x100)
- [x] **AXES-04**: Teach buttons to capture current physical position as Rest Point or Start Point
- [x] **AXES-05**: Quick action buttons: Go to Rest (all axes), Go to Start (all axes), Home All Axes
- [x] **AXES-06**: Axes setup is only accessible to Setup and Admin roles

### Parameters

- [x] **PARAM-01**: Parameters are organized into grouped cards: Geometry, Feedrates, Calibration, Positions, Safety
- [x] **PARAM-02**: Each parameter row shows human-readable name, DMC variable code, editable input field, and unit
- [x] **PARAM-03**: Invalid inputs (out of range, wrong type) are highlighted inline with red border immediately on entry
- [x] **PARAM-04**: Modified (unsaved) values are visually indicated with amber highlight and a change counter in the bottom bar
- [x] **PARAM-05**: "Apply to Controller" button sends all modified parameters to the controller at once
- [x] **PARAM-06**: "Read from Controller" button refreshes all parameter values from the controller
- [x] **PARAM-07**: Parameters page is only editable by Setup and Admin roles; Operator can view but not modify

### CSV Profiles

- [x] **CSV-01**: User can export all current parameter values and array data to a CSV file
- [x] **CSV-02**: User can import a CSV file to load a knife profile (DMC array names as headers, values as rows)
- [x] **CSV-03**: CSV import validates machine type compatibility before applying
- [x] **CSV-04**: CSV import is blocked during an active grinding cycle (safety interlock)
- [x] **CSV-05**: CSV profiles are only importable/exportable by Setup and Admin roles

### Machine Types

- [x] **MACH-01**: App supports three machine types: 4-Axes Flat Grind, 4-Axes Convex Grind, 3-Axes Serration Grind
- [ ] **MACH-02**: Each machine type has its own RUN page layout and parameter groups appropriate to its axis count and workflow
- [x] **MACH-03**: Machine type is determined at deployment time (hard-coded per installation, not runtime-selectable)

### Theme & Touch

- [x] **UI-01**: Consistent dark theme across all screens (BG_DARK navy palette from existing theme.kv)
- [x] **UI-02**: Axis accent color coding maintained throughout: A=orange, B=purple, C=cyan, D=yellow
- [x] **UI-03**: All interactive elements meet minimum 44dp touch target size
- [x] **UI-04**: No animated transitions between screens — instant switches only

### Deployment

- [ ] **DEPLOY-01**: App runs in kiosk mode on Raspberry Pi — boots straight into the app with no desktop, browser, or file explorer access
- [ ] **DEPLOY-02**: Kiosk mode is operator-locked — no way to exit the app without Setup/Admin credentials
- [ ] **DEPLOY-03**: Deployment is SD card based — install program on SD card, insert into Pi, app runs on boot
- [ ] **DEPLOY-04**: App also runs on Windows 11 as a standard desktop application
- [ ] **DEPLOY-05**: No external JSON/YAML config files required for deployment — machine config is embedded in the application

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Diagnostics

- **DIAG-01**: Raw controller command terminal for Setup users (send commands, see responses)
- **DIAG-02**: Array viewer showing all tracked DMC arrays and their current values
- **DIAG-03**: Command history log with timestamps

### Enhancements

- **ENH-01**: Axis position units display (mm/degrees instead of raw encoder counts)
- **ENH-02**: Profile metadata embedded in CSV (machine type, date, operator name, notes)
- **ENH-03**: Per-tooth B-axis compensation table with live bar chart (serration-specific)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Password hashing / encryption for PINs | In-house use, no network exposure, adds unnecessary dependencies |
| External JSON/YAML config files | Machines are stable once production starts; hard-coding is acceptable |
| Remote/network software updates | No network infrastructure; manual SD card swap is sufficient |
| Multi-language UI | English only; Vietnamese labels being replaced |
| Database for profiles | CSV is transparent, portable, and Excel-compatible |
| Cloud sync / backup | No network infrastructure on these machines |
| Web dashboard / REST API | Standalone controllers, not networked production systems |
| Fine-grained permissions | 3-tier roles (Operator/Setup/Admin) is sufficient for in-house use |
| Undo/redo for parameter edits | Controller is source of truth; "Read from Controller" is the real undo |
| Animated screen transitions | Adds latency and distraction on industrial tool |
| Mobile/tablet app | Pi touchscreen and Windows desktop only |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 1 | Complete |
| AUTH-02 | Phase 1 | Complete |
| AUTH-03 | Phase 1 | Complete |
| AUTH-04 | Phase 1 | Complete |
| AUTH-05 | Phase 1 | Complete |
| AUTH-06 | Phase 1 | Complete |
| AUTH-07 | Phase 7 | Pending |
| AUTH-08 | Phase 7 | Pending |
| NAV-01 | Phase 1 | Pending |
| NAV-02 | Phase 1 | Pending |
| NAV-03 | Phase 1 | Pending |
| NAV-04 | Phase 1 | Pending |
| NAV-05 | Phase 1 | Pending |
| RUN-01 | Phase 2 | Complete |
| RUN-02 | Phase 2 | Complete |
| RUN-03 | Phase 2 | Complete |
| RUN-04 | Phase 2 | Complete |
| RUN-05 | Phase 2 | Complete |
| RUN-06 | Phase 2 | Complete |
| RUN-07 | Phase 3 | Complete |
| AXES-01 | Phase 4 | Complete |
| AXES-02 | Phase 4 | Complete |
| AXES-03 | Phase 4 | Complete |
| AXES-04 | Phase 4 | Complete |
| AXES-05 | Phase 4 | Complete |
| AXES-06 | Phase 4 | Complete |
| PARAM-01 | Phase 4 | Complete |
| PARAM-02 | Phase 4 | Complete |
| PARAM-03 | Phase 4 | Complete |
| PARAM-04 | Phase 4 | Complete |
| PARAM-05 | Phase 4 | Complete |
| PARAM-06 | Phase 4 | Complete |
| PARAM-07 | Phase 4 | Complete |
| CSV-01 | Phase 5 | Complete |
| CSV-02 | Phase 5 | Complete |
| CSV-03 | Phase 5 | Complete |
| CSV-04 | Phase 5 | Complete |
| CSV-05 | Phase 5 | Complete |
| MACH-01 | Phase 6 | Complete |
| MACH-02 | Phase 6 | Pending |
| MACH-03 | Phase 6 | Complete |
| UI-01 | Phase 1 | Pending |
| UI-02 | Phase 1 | Pending |
| UI-03 | Phase 1 | Pending |
| UI-04 | Phase 1 | Pending |
| DEPLOY-01 | Phase 8 | Pending |
| DEPLOY-02 | Phase 8 | Pending |
| DEPLOY-03 | Phase 8 | Pending |
| DEPLOY-04 | Phase 8 | Pending |
| DEPLOY-05 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 50 total
- Mapped to phases: 50
- Unmapped: 0

---
*Requirements defined: 2026-04-04*
*Last updated: 2026-04-04 after roadmap creation — all 50 requirements mapped*
