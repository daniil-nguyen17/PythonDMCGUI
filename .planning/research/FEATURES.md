# Feature Landscape

**Domain:** Industrial machine control GUI — knife grinding machine (CNC-adjacent HMI)
**Researched:** 2026-04-04
**Confidence note:** Based on existing codebase analysis, approved HTML mockups, and established
industrial HMI standards (ISA-101, Siemens/Allen-Bradley HMI conventions, IEC 62443 access
control patterns). No web search was performed; findings reflect well-established domain knowledge
and direct project artifact review.

---

## Table Stakes

Features operators and setup personnel expect as a baseline. Their absence makes the product feel
unfinished or unsafe.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| PIN-based login with role selection | All industrial HMIs protect setup/admin from operators. Touchscreen-friendly (no keyboard needed). PIN is the correct granularity for in-house use. | Med | Numeric keypad overlay widget. Store hashed PINs in a local JSON or SQLite file. Remember last user on startup. |
| Three-tier access: Operator / Setup / Admin | Operators run machines; setup configures them; admin manages users. Tier separation is table stakes for any shop-floor machine. | Med | Operator sees run controls only. Setup unlocks via PIN overlay and relocks on timeout or manual lock. Admin manages the user table. |
| Session lock / auto-lock | Setup unlocks to edit parameters, then the machine is left unattended. Auto-lock after N minutes of inactivity prevents accidental config changes by operators who walk up after. | Low | Clock.schedule_once timeout. Any touch on non-admin screens resets timer. Lock returns to Operator view, not login screen. |
| Big-button RUN page | Operators need Start, Pause, Go to Rest, and E-STOP visible and reachable in one tap from any state. These must be 44dp+ minimum and E-STOP must be visually dominant (red, largest target). | Med | Matches approved run_page.html mockup. E-STOP must always be reachable regardless of scroll position. |
| Live axis position display | Operators and setup personnel need to know where the machine is at all times. Position readback is non-negotiable for a motion control GUI. | Med | Poll `MG _TPA/B/C/D` via background thread. Update labels at ~10 Hz. Already scaffolded in app_state.py and the disabled poll loop in main.py. |
| Cycle status and progress feedback | Operators need to know if the machine is running, paused, faulted, or idle. Without this, they have no feedback loop. | Low | Banner text already exists. Needs a dedicated status indicator (dot + text) on the RUN page as shown in run_page.html. |
| Operation log / event ticker | Every significant action (cycle start, fault, parameter change, E-STOP) must be recorded and visible in a scrollable log. | Low | Already in MachineState.messages (200-message ring buffer). Wire into scrollable Label on RUN page. |
| Axis jog controls | Setup personnel must be able to manually move each axis to teach positions or verify travel. Arrow buttons + step size is the standard pattern. | Med | Scaffold exists in axisDSetup.py (adjust_axis method). Unify into AxesSetupScreen covering all four axes with sidebar selection. |
| Teach point capture | Setup personnel must be able to record the current physical position as Rest or Start so the DMC program knows where to go. | Low | Already implemented in setup.py's teach_point(). Needs to be surfaced on the unified AxesSetupScreen. |
| Grouped parameter editing | Parameters must be organized by function (Geometry, Feedrates, Calibration, Positions, Safety). Flat lists of DMC variable names are unusable for operators. | Med | Mockup in params_setup.html shows card layout. Existing parameters_setup.py is partial. |
| Controller connection management | The app must handle connect/disconnect, show status, and recover gracefully from lost connections. | Low | Already implemented in SetupScreen. The pattern is solid; needs to be surfaced in the top bar of the main layout per the mockup. |
| E-STOP at all times | E-STOP must be reachable from every screen, not just the RUN page. It is a safety requirement, not a convenience feature. | Low | app.e_stop() already sends AB command and disconnects. Needs to be wired into a persistent button in the top bar or tab footer. |
| Per-machine-type screen sets | Three machine types (4-Axes Flat, 4-Axes Convex, 3-Axes Serration) have different axis counts and workflows. A single screen set would require confusing conditional logic throughout. | High | Serration screen already exists (serration_knife.py). Flat and Convex need their own RUN + Axes Setup screens. Machine type selected at connection time or hard-coded per deployment. |
| Consistent dark theme with axis accent colors | Dark themes reduce eye strain on the shop floor. Axis color coding (A=orange, B=purple, C=cyan, D=yellow) prevents axis confusion during jog operations and plot reading. | Low | theme.kv already establishes this. Maintain across all new screens. |
| Touch-friendly targets throughout | Pi touchscreen requires minimum 44dp interactive targets. Anything smaller is unusable with gloves or at arm's reach. | Low | Ongoing discipline, not a single feature. Must be enforced in KV review. |

---

## Differentiators

Features that go beyond what operators expect. Not required for the product to feel complete, but
add real value for the shop and differentiate from a bare-bones DMC terminal.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Live matplotlib A/B position plot (top-down) | Operators can see where the knife is relative to the grind path without looking at the machine. Catches drift or missed home immediately. | High | matplotlib FigureCanvasKivyAgg integration. Poll at ~10 Hz, rolling buffer of N points. Axis color coding (A=orange, B=purple). Already planned and scaffolded (poll disabled in main.py). |
| CSV profile import/export | Operators can save the current knife setup to a file and reload it for the next batch. Eliminates re-entering parameters for repeat jobs. The CSV format matches DMC array naming conventions, making it transparent and portable. | Med | Read/write CSV with DMC array name as column header and value rows. Export = read all tracked variables from controller, write to file. Import = parse, validate, download to controller. |
| Profile name / metadata in CSV | A profile filename alone is not enough context. Embedding the machine type, date, and operator name in CSV header rows lets the shop find and verify profiles without opening them. | Low | Add comment rows at top of CSV. Metadata: machine_type, created_by, created_at, notes. |
| Per-tooth B-axis compensation table | Serration grinding requires individual tooth-by-tooth B-axis offset corrections to account for blade irregularities. The bComp array already exists on the controller. A visual table with live bar chart gives setup personnel direct insight into compensation distribution. | High | Already implemented in serration_knife.py. Represents the most sophisticated feature in the existing codebase. |
| Tab navigation replacing ActionBar + Spinner | A persistent tab bar (Run / Axes Setup / Parameters / Diagnostics) is faster to navigate than a spinner and makes screen structure obvious at a glance. Touch targets are larger and the active tab is always visible. | Med | Approved direction per mockup. The base.kv RootLayout needs to be refactored from Spinner-based navigation to a persistent tab bar. |
| Diagnostics tab | A dedicated screen showing raw controller responses, recent command history, and current array values gives setup personnel a debugging tool without needing a separate DMC terminal. | Med | Surface MachineState.messages in a scrollable terminal-style widget. Add a raw command entry field (Setup role only). Read and display all tracked arrays on demand. |
| Kiosk mode (Raspberry Pi) | Operators cannot accidentally close the app, switch to the desktop, or open a browser. Locks down the Pi to a single-purpose machine. | Med | systemd service + openbox/matchbox WM autostart with no taskbar. Kivy Config fullscreen=auto. Separate from the app itself — a deployment configuration. |
| SD card deployment | Technicians can deploy a new software version by swapping an SD card rather than connecting a keyboard and running pip install. Eliminates deployment friction in a shop environment. | Med | Raspberry Pi Imager creates a base image. A startup script pulls the app from a known path. systemd unit handles autostart. Document once, reuse forever. |
| Remember last user on startup | The most recently logged-in operator is pre-selected on the PIN entry screen. Eliminates scrolling through a user list for the common case where the same person runs the machine daily. | Low | Persist last_user to a local JSON file. Load on startup, pre-select in the PIN keypad widget. |
| Input validation with inline feedback | Invalid numeric inputs (out of range, wrong type) should highlight red immediately rather than failing silently or crashing on the controller side. | Low | Already partially implemented in axisDSetup.py (red background_color on parse failure). Standardize this pattern across all numeric inputs. |
| Axis position units display | Showing encoder counts to operators is meaningless. Converting to mm or degrees with the correct scale factor makes setup comprehensible. | Low | Add unit labels next to all position readbacks. The conversion factor is a parameter; do not hard-code it in the UI. |

---

## Anti-Features

Things to deliberately NOT build. Building these would add complexity, maintenance burden, or
security theater without meaningful benefit for the use case.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Password hashing / encryption for PINs | The machines are in a closed shop with no network exposure. Adding bcrypt or AES adds 2 dependencies and complexity for zero real security gain given the threat model. | Store PINs in plaintext in a local JSON file. Documented as a known limitation in PROJECT.md. |
| External JSON/YAML config files for machine parameters | Machines do not change once production starts. Config file management adds deployment surface area (wrong file = broken machine) with no benefit. | Hard-code machine configs in Python. If a parameter ever needs to change, it's a software update. |
| Remote/network software updates | OTA update infrastructure is out of scope and adds significant attack surface. | Manual SD card swap for Pi; manual pip install for Windows. Document the procedure once. |
| Multi-language UI | The codebase currently has Vietnamese labels which are being replaced with English. Adding an i18n framework now would add 1-2 days of work for a feature with no stated demand. | English only. If translation is needed later, the KV string pattern makes it straightforward to add. |
| Database for profiles | SQLite or Postgres adds a dependency, schema migration concerns, and makes profiles opaque to operators. CSV files can be opened in Excel, emailed, and understood without software. | CSV files in a known directory. One file per profile. Filename is the profile name. |
| Cloud sync / backup | No network infrastructure exists for these machines. Adding cloud sync creates a dependency that fails in offline environments. | Manual file copy for backup. Profiles are just CSV files. |
| Web dashboard or REST API | These are standalone machine controllers, not networked production systems. A web interface adds Flask/FastAPI, port management, and a second UI surface to maintain. | Kivy GUI only. If remote monitoring is needed in the future, it is a separate project. |
| User permission granularity beyond three roles | Fine-grained permissions (e.g., "can edit feedrates but not geometry") add a permission management screen, more conditional UI logic, and user confusion. | Operator / Setup / Admin is sufficient. Setup has full parameter access; that is acceptable for in-house shop use. |
| Undo/redo for parameter edits | Controller state is the source of truth. An undo stack in the GUI that diverges from controller state creates confusion about what the machine will actually do. | Load from controller (re-read array) to restore. That is the real undo. |
| Animated transitions between screens | Motion effects add latency and cognitive noise on a functional industrial tool. Operators find them distracting. | Instant screen switches. No slide/fade transitions. |

---

## Feature Dependencies

```
PIN auth widget
  └── Role model (Operator / Setup / Admin)
        ├── Admin role → User management screen
        ├── Setup role → Parameter editing enabled / Axes jog enabled
        └── Operator role → RUN page only (read-only params visible)

Controller connection (SetupScreen)
  └── All other screens (cannot operate disconnected)
        ├── Live axis poll → Live position labels → Live matplotlib plot
        ├── Axes Setup → Teach point → CSV profile export uses taught points
        └── Parameters Setup → CSV profile import/export

CSV profile import
  └── Parameter groups defined (must know which DMC arrays to write)

Live matplotlib plot
  └── Live axis poll at ~10 Hz (disabled in main.py — must be enabled)
  └── MachineState.pos updated reliably

Per-machine-type screens
  └── Machine type selection (at connection time or deployment config)
        ├── 4-Axes Flat → own RUN + AxesSetup screens
        ├── 4-Axes Convex → own RUN + AxesSetup screens
        └── 3-Axes Serration → existing serration_knife.py

Tab navigation
  └── base.kv RootLayout refactor (current ActionBar + Spinner → tab bar)
        └── All existing screens re-registered under new navigation

Kiosk mode
  └── systemd unit + WM autostart (independent of Python app)
  └── Kivy fullscreen config
```

---

## What Already Exists vs What Needs Building

Based on the current codebase, this distinction matters for roadmap phase ordering.

### Already Working
- Controller connection / discovery / disconnect (SetupScreen + GalilController)
- Background threading pattern (jobs.submit + Clock.schedule_once) — solid, preserve it
- MachineState subscriber pattern (pub/sub via state.subscribe)
- Axis D jog with immediate position command (axisDSetup.py)
- Teach point capture and storage in MachineState
- Dark theme and axis color constants (theme.kv)
- Serration knife screen with parameters, bComp table, run control, subroutine reference
- Banner text for log messages (app.banner_text StringProperty)
- upload_array / download_array with GArrayUpload/GArrayDownload and fallback to chunked MG

### Partially Implemented / Broken
- Poll loop exists in main.py but is commented out — live position updates are disabled
- parameters_setup.py is actually RestPnt editing, not a general parameter editor — naming mismatch
- AxisDSetup shares RestPnt array with RestScreen — documented as a known conflict
- No PIN auth, no role model, no user management — zero scaffolding exists

### Not Yet Started
- Live matplotlib plot
- CSV profile import/export
- Tab navigation (current ActionBar + Spinner)
- Unified AxesSetupScreen (jog + teach for all 4 axes with sidebar)
- RUN page (proper cycle control, progress bar, status dot)
- Admin user management screen
- Diagnostics tab
- Kiosk mode systemd config

---

## MVP Recommendation

The minimum viable product that delivers the stated core value ("operator walks up, taps PIN, runs
parts, goes home"):

**Phase 1 — Foundation:** Tab navigation + PIN auth + role model. Everything else depends on this.

**Phase 2 — Run Loop:** RUN page with live position labels, cycle controls (Start/Pause/Rest/E-STOP),
and the existing operation log. Enable the poll loop. This is what makes the machine usable.

**Phase 3 — Live Plot:** Matplotlib A/B position plot. High visual value, confirms the machine is
doing what it should. Requires the poll loop from Phase 2.

**Phase 4 — Setup Tools:** Unified AxesSetupScreen (jog + teach all axes) and proper grouped
Parameters Setup page.

**Phase 5 — Profiles:** CSV import/export. Operators can start saving and reloading knife setups.

**Phase 6 — Admin + Polish:** User management screen, diagnostics tab, kiosk mode deployment.

**Defer indefinitely:** undo/redo, cloud sync, network API, multi-language.

---

## Sources

- Direct codebase analysis: `src/dmccodegui/` (main.py, app_state.py, controller.py, all screens)
- Approved HTML mockups: `mockups/run_page.html`, `mockups/axes_setup.html`, `mockups/params_setup.html`
- Project context: `.planning/PROJECT.md`
- ISA-101 HMI design standard (well-established domain knowledge, training data confidence: HIGH)
- Industrial HMI access control conventions — Siemens TIA Portal, Allen-Bradley FactoryTalk patterns
  (well-established domain knowledge for PIN/role tiering, training data confidence: HIGH)
- Galil DMC gclib API conventions (training data + codebase evidence, confidence: HIGH)
