# Roadmap: DMC Grinding GUI

## Milestones

- ✅ **v1.0 MVP** — Phases 1-7 (shipped 2026-04-06) | Phase 8 deferred
- ⏸ **v1.1 Deployment** — Phase 8: Pi Kiosk (pending hardware validation)
- ✅ **v2.0 Flat Grind Integration** — Phases 9-17 (shipped 2026-04-07)
- ✅ **v3.0 Multi-Machine** — Phases 18-23 (shipped 2026-04-13)
- 🚧 **v4.0 Packaging & Deployment** — Phases 24-29 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-7) — SHIPPED 2026-04-06</summary>

- [x] **Phase 1: Auth and Navigation** — PIN login, three-tier roles, tab bar (4/4 plans, completed 2026-04-04)
- [x] **Phase 2: RUN Page** — Cycle controls, live axis positions, E-STOP, Knife Grind Adjustment (4/4 plans, completed 2026-04-04)
- [x] **Phase 3: Live Matplotlib Plot** — Embedded A/B position plot at 5 Hz (1/1 plan, completed 2026-04-04)
- [x] **Phase 4: Axes Setup and Parameters** — Unified jog/teach screen and grouped parameter editor (3/3 plans, completed 2026-04-04)
- [x] **Phase 5: CSV Profile System** — Import/export with machine-type validation and diff preview (3/3 plans, completed 2026-04-04)
- [x] **Phase 6: Machine-Type Differentiation** — Flat Grind, Convex Grind, Serration Grind support (3/3 plans, completed 2026-04-04)
- [x] **Phase 7: Admin and User Management** — Admin CRUD screen for users, PINs, and roles (2/2 plans, completed 2026-04-06)

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>⏸ v1.1 Deployment (Phase 8) — DEFERRED</summary>

- [ ] **Phase 8: Pi Kiosk and Deployment** — Kiosk lockout, systemd autostart, SD card packaging

Full context: `.planning/phases/08-CONTEXT.md`

</details>

<details>
<summary>✅ v2.0 Flat Grind Integration (Phases 9-17) — SHIPPED 2026-04-07</summary>

- [x] **Phase 9: DMC Foundation** — HMI trigger variables, dmc_vars.py constants, hmiState at every boundary (completed 2026-04-06)
- [x] **Phase 10: State Poll** — 10 Hz poll wired to real controller for positions, knife count, disconnect detection (completed 2026-04-06)
- [x] **Phase 11: E-STOP Safety** — Priority stop path, motion-gate on all buttons (completed 2026-04-06)
- [x] **Phase 12: Run Page Wiring** — All operator Run page buttons trigger real DMC subroutines (completed 2026-04-06)
- [x] **Phase 13: Setup Loop** — Enter/exit setup, home, jog, teach points, parameter write + recalc (completed 2026-04-06)
- [x] **Phase 14: State-Driven UI** — Button enable/disable, status labels, setup badge, tab gating (completed 2026-04-06)
- [x] **Phase 15: Run Page Missing Controls** — Stone Compensation card layout gap closure (completed 2026-04-06)
- [x] **Phase 16: ProfilesScreen Setup Loop Fix** — Smart-enter guard and exit-setup wiring (completed 2026-04-07)
- [x] **Phase 17: Poll Reset and Cold-Start Fix** — _fail_count reset on reconnect, OFFLINE default (completed 2026-04-07)

Full details: `.planning/milestones/v2.0-ROADMAP.md`

</details>

<details>
<summary>✅ v3.0 Multi-Machine (Phases 18-23) — SHIPPED 2026-04-13</summary>

- [x] **Phase 18: Base Class Extraction** — Extract BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen with shared controller wiring and subscription lifecycle (completed 2026-04-11)
- [x] **Phase 19: Flat Grind Rename and KV Split** — Rename existing screens to FlatGrind* classes with per-machine kv files in ui/flat_grind/ (completed 2026-04-11)
- [x] **Phase 20: Screen Registry and Loader** — machine_config screen_classes mapping, _load_machine_screens() swap function, machine detection on connect (completed 2026-04-11)
- [x] **Phase 21: Serration Screen Set** — SerrationRunScreen, SerrationAxesSetupScreen, SerrationParametersScreen with 3-axis layout and bComp stub (completed 2026-04-13)
- [x] **Phase 22: Convex Screen Set** — ConvexRunScreen, ConvexAxesSetupScreen, ConvexParametersScreen with convex-specific layout (completed 2026-04-13)
- [x] **Phase 23: Controller Communication Optimization** — GRecord poll replacement, MG variable batching, structured state messages, MG reader thread, direct connection flag, explicit timeouts (completed 2026-04-13)

Full details: `.planning/milestones/v3.0-ROADMAP.md`

</details>

### v4.0 Packaging & Deployment (Phases 24-29)

**Milestone Goal:** Package the working HMI into installable bundles for Windows 11 and Raspberry Pi — zero pre-installed software required on target machines.

- [ ] **Phase 24: Windows PyInstaller Bundle** — PyInstaller spec, gclib DLL vendoring, frozen path fixes (WIN-01, WIN-02, WIN-05, WIN-07)
- [x] **Phase 25: Windows Inno Setup Installer** — .exe installer, Start Menu/Desktop shortcuts, Add/Remove Programs, optional auto-start (WIN-03, WIN-04, WIN-06) (completed 2026-04-22)
- [ ] **Phase 26: Pi OS Preparation and Install Script** — X11 switch, Galil .deb, venv, desktop app install (PI-01, PI-04, PI-05)
- [ ] **Phase 27: Screen Resolution Detection** — Auto-detect at startup, display profile presets, manual override in settings.json (APP-04)
- [ ] **Phase 28: Logging Infrastructure** — Rotating log file, uncaught exception hook, dev artifact exclusion (APP-01, APP-02, APP-03)
- [ ] **Phase 29: Integration Testing and Field Validation** — Clean-VM Windows gate, Pi hardware gate, real controller validation (FIX-02, PI-06)

---

## Phase Details

### Phase 8: Pi Kiosk and Deployment
**Goal**: The app boots automatically on a Raspberry Pi into a locked-down kiosk with no path for operators to reach the desktop, and installs from an SD card
**Depends on**: Phase 6 (complete)
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04, DEPLOY-05
**Status**: Deferred — awaiting hardware validation of Phases 1-7 on real DMC controller
**Success Criteria** (what must be TRUE):
  1. Raspberry Pi boots directly into the app with no desktop, browser, or file manager accessible to the operator
  2. There is no keyboard shortcut, swipe, or tap sequence that exits the app without Setup or Admin credentials
  3. App restarts automatically if it crashes (systemd Restart=always)
  4. A technician can deploy the app to a new Pi by writing an SD card image and inserting it — no pip install or internet connection required
  5. The same codebase runs as a standard window on Windows 11 with no kiosk behavior
**Plans**: TBD (context captured in `08-CONTEXT.md`)

### Phase 9: DMC Foundation
**Goal**: The DMC program and Python codebase share a correct, named contract — HMI trigger variables exist in the controller with default=1, OR conditions are live in the polling loop, hmiState is set at every state boundary, and Python constants prevent 8-char name typos.
**Depends on**: Nothing (first v2.0 phase)
**Requirements**: DMC-01, DMC-02, DMC-03, DMC-04, DMC-05, DMC-06
**Success Criteria** (what must be TRUE):
  1. Uploading the modified .dmc file and issuing XQ #AUTO causes hmiGrnd, hmiSetp, hmiMore, hmiLess, hmiNewS, hmiHome, hmiJog, hmiCalc to each return 1 when queried via gclib
  2. Setting any HMI trigger variable to 0 from gclib causes the corresponding DMC block to execute — it resets the variable to 1 as its first action before any motion
  3. Querying hmiState from the controller returns a distinct nonzero integer at each named state boundary (IDLE, GRINDING, SETUP, HOMING) — not a constant or undefined
  4. Python code references all DMC array names (startPt, restPt) and variable names through constants in hmi/dmc_vars.py — no raw 8-char string literals in screen files
  5. App closes cleanly without leaving a dangling gclib handle — verified by successfully opening a new connection immediately after a forced close
**Plans:** 3/3 plans complete
Plans:
- [x] 09-01-PLAN.md — Create hmi/dmc_vars.py constants module and MachineState.dmc_state field
- [x] 09-02-PLAN.md — Modify DMC program: HMI variables, OR conditions, hmiState, array-to-scalar conversion
- [x] 09-03-PLAN.md — Migrate 4 Python screen files from stale array ops to dmc_vars constants

### Phase 10: State Poll
**Goal**: The HMI reads authoritative state from the controller on every poll tick — axis positions display real values, connection loss is detected, and knife count reflects controller data — all verified against the real controller before any write commands are sent.
**Depends on**: Phase 9
**Requirements**: POLL-01, POLL-02, POLL-03, POLL-04
**Success Criteria** (what must be TRUE):
  1. Moving axes by hand (or jogging from DMC terminal) causes the Run page position labels to update within 200 ms — values match the controller query directly
  2. Disconnecting the controller network cable causes a visible disconnected status on the HMI within 2 seconds — no crash, no freeze
  3. Reconnecting the cable (or restarting the controller) causes the HMI to resume polling without an app restart
  4. The knife count label on the Run page shows the same value as ctSesKni queried directly from the DMC terminal
**Plans:** 3/3 plans complete
Plans:
- [x] 10-01-PLAN.md — Extend dmc_vars.py, MachineState, and DMC program with knife count + Thread 2
- [x] 10-02-PLAN.md — Create ControllerPoller module and wire into app lifecycle
- [x] 10-03-PLAN.md — Migrate RunScreen to MachineState subscription, add knife count and disconnect UI

### Phase 11: E-STOP Safety
**Goal**: The stop path halts motion within 200 ms from any screen, is never queued behind normal controller jobs, and all motion-triggering buttons are gated on real controller state — validated on hardware before any motion commands are wired.
**Depends on**: Phase 9, Phase 10
**Requirements**: SAFE-01, SAFE-02, SAFE-03
**Success Criteria** (what must be TRUE):
  1. Pressing E-STOP while a large array operation is in-flight halts axis motion within 200 ms — confirmed by observing the controller's axis stop response, not just checking a flag
  2. Pressing Stop from the Run page sends both ST ABCD and HX — the DMC program thread stops, not just the motors
  3. Start Grind, Go To Rest, Go To Start, More Stone, and Less Stone buttons are visually disabled when hmiState reports active motion — they cannot be tapped until the controller reports idle
  4. E-STOP is accessible from the Run page without navigating away from any active screen
**Plans:** 2/2 plans complete
Plans:
- [x] 11-01-PLAN.md — Priority job infrastructure (submit_urgent, reset_handle, program_running poll)
- [x] 11-02-PLAN.md — Wire E-STOP, Stop, RECOVER buttons and motion gate on RunScreen

### Phase 12: Run Page Wiring
**Goal**: An operator can run a complete grind cycle from the touchscreen — start, stop, navigate to rest and start positions, adjust stone compensation, and begin a new session — all triggering real DMC subroutines via the HMI one-shot variable pattern.
**Depends on**: Phase 9, Phase 10, Phase 11
**Requirements**: RUN-01, RUN-02, RUN-03, RUN-04, RUN-05, RUN-06, RUN-07
**Success Criteria** (what must be TRUE):
  1. Pressing Start Grind sends hmiGrnd=0 and the DMC controller begins the grind cycle — confirmed by observing axis motion and hmiState changing to GRINDING
  2. Pressing Go To Rest and Go To Start each cause the machine to move to the respective taught position — confirmed against physical axis motion, not simulated
  3. Pressing Stop during an active grind cycle halts all axis motion and ends the DMC program thread within one stop-command round trip
  4. Pressing More Stone or Less Stone while the machine is idle triggers the corresponding DMC compensation routine — buttons are disabled during active motion
  5. Pressing New Session requires a two-step confirmation, is blocked for Operator role, and triggers the DMC #NEWSESS routine on confirmation
  6. The A/B live plot fills with real axis position data during an active grind cycle — trace is not synthetic, flat, or static
**Plans**: 1/1 plans complete

### Phase 13: Setup Loop
**Goal**: A Setup user can enter controller setup mode from the HMI, home the machine, jog all axes, teach rest and start points, write parameter values to the controller, trigger recalculation, and return to main loop — entirely from the touchscreen.
**Depends on**: Phase 9, Phase 10, Phase 11
**Requirements**: SETP-01, SETP-02, SETP-03, SETP-04, SETP-05, SETP-06, SETP-07, SETP-08, RUN-02, RUN-03, RUN-06
**Success Criteria** (what must be TRUE):
  1. Tapping Enter Setup on the HMI sends hmiSetp=0 and the controller enters its #SETUP loop — hmiState reflects SETUP state within one poll tick
  2. Tapping Home (Setup/Admin only) sends hmiHome=0 and all axes move to their home positions — confirmed on real hardware
  3. Tapping jog +/- on any axis causes that axis to move the configured step distance on the real controller — no conflict with the DMC #WheelJg loop observed
  4. Tapping Teach Rest Point writes current axis positions to restPt[] on the controller; Teach Start Point writes to startPt[] — values confirmed by reading back from controller terminal
  5. Editing a parameter value and saving writes the new value to the controller variable and triggers hmiCalc=0 — the controller recalculates derived values (verified by reading back a derived variable)
  6. Tapping Exit Setup returns the controller to the #MAIN loop — hmiState returns to IDLE within one poll tick
**Plans**: 3/3 plans complete

### Phase 14: State-Driven UI
**Goal**: Every interactive element reflects real controller state — buttons enable and disable correctly on controller-reported state, status labels name the current machine state, setup mode is visible across all screens, and the Run tab blocks correctly during setup.
**Depends on**: Phase 10, Phase 12
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05
**Success Criteria** (what must be TRUE):
  1. Starting a grind cycle from the controller's physical panel (not the HMI) causes the HMI Run page buttons to disable within one poll tick — Python-side cycle_running is not the gate
  2. The status label on the Run page displays IDLE, GRINDING, SETUP, or HOMING matching actual controller state at all times during normal operation
  3. Navigating to any screen while the controller is in setup mode shows the setup mode badge — it is not limited to the Axes Setup screen
  4. The Run tab is visually disabled and cannot be tapped when the controller reports it is in setup mode
  5. The connection status indicator is visible on every screen and reflects connected or disconnected without requiring any page navigation
**Plans:** 2/2 plans complete
Plans:
- [x] 14-01-PLAN.md — StatusBar state label, setup badge, and tab gating
- [x] 14-02-PLAN.md — Cross-screen button gating (Profiles import, Parameters apply)

### Phase 15: Run Page Missing Controls
**Goal**: The Run page Stone Compensation controls move from the bottom action bar into a dedicated card in the right column with a persistent startPtC readback label.
**Depends on**: Phase 12
**Requirements**: (layout only — RUN-02, RUN-03, RUN-06 re-mapped to Phase 13)
**Gap Closure**: Closes gaps from v2.0 audit
**Success Criteria** (what must be TRUE):
  1. More Stone and Less Stone buttons appear in a Stone Compensation card in the right column, not in the bottom action bar
  2. A persistent startPtC label in the card shows the current stone position
  3. RUN-02, RUN-03, RUN-06 traceability updated to Phase 13 (complete)
**Plans:** 1/1 plans complete
Plans:
- [x] 15-01-PLAN.md — Stone Compensation card layout and traceability re-mapping

### Phase 16: ProfilesScreen Setup Loop Fix
**Goal**: ProfilesScreen correctly enters and exits controller setup mode using the same smart-enter/exit pattern as AxesSetupScreen and ParametersScreen.
**Depends on**: Phase 13
**Requirements**: SETP-01, SETP-08
**Gap Closure**: Closes gaps from v2.0 audit
**Success Criteria** (what must be TRUE):
  1. Navigating to ProfilesScreen while already in STATE_SETUP does not re-send hmiSetp=0
  2. Leaving ProfilesScreen sends hmiExSt=0 (not hmiSetp=1) to correctly exit setup mode
**Plans:** 1/1 plans complete
Plans:
- [x] 16-01-PLAN.md — Fix smart-enter guard and exit command in ProfilesScreen

### Phase 17: Poll Reset and Cold-Start Fix
**Goal**: Controller poller resets cleanly between disconnect/reconnect cycles and the status bar shows OFFLINE (not E-STOP) before the first successful connection.
**Depends on**: Phase 10, Phase 14
**Requirements**: POLL-03, UI-02
**Gap Closure**: Closes gaps from v2.0 audit
**Success Criteria** (what must be TRUE):
  1. After disconnect_and_refresh(), _fail_count is reset to 0 so reconnection starts with a clean slate
  2. Before the first successful poll, the status bar shows OFFLINE instead of E-STOP
**Plans:** 1/1 plans complete
Plans:
- [x] 17-01-PLAN.md — Reset _fail_count on stop() and fix program_running cold-start default

---

### Phase 18: Base Class Extraction
**Goal**: Shared controller wiring, poll subscription, and lifecycle behavior exist in three base classes that all future machine screens inherit — isolating the riskiest refactor before any machine-specific code is created
**Depends on**: Phase 17 (v2.0 complete)
**Requirements**: ARCH-01, ARCH-02, ARCH-03, ARCH-04
**Success Criteria** (what must be TRUE):
  1. Existing RunScreen, AxesSetupScreen, and ParametersScreen inherit from their respective base classes and the application runs identically to v2.0 — no behavior change observable by the user
  2. Navigating away from any screen unsubscribes all state listeners; navigating back re-subscribes — verified by adding a log line that shows zero duplicate callbacks after two enter/leave cycles
  3. All lifecycle hooks (on_pre_enter, on_enter, on_leave) are defined only in Python base class files, not in any .kv file
  4. A new machine screen subclass that calls super() on all lifecycle hooks inherits poll subscription and controller wiring with no additional code
**Plans:** 2/2 plans complete
Plans:
- [x] 18-01-PLAN.md — Create base classes (BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen, SetupScreenMixin) and extract Flat Grind widgets
- [x] 18-02-PLAN.md — Wire existing screens to inherit from base classes, full regression verification

### Phase 19: Flat Grind Rename and KV Split
**Goal**: The existing screens are renamed to FlatGrindRunScreen, FlatGrindAxesSetupScreen, and FlatGrindParametersScreen with independent .kv files in ui/flat_grind/ — establishing the reference implementation and naming convention before the screen loader is wired
**Depends on**: Phase 18
**Requirements**: FLAT-01, FLAT-02, FLAT-03, FLAT-04
**Success Criteria** (what must be TRUE):
  1. The application runs with FlatGrind* class names and ui/flat_grind/*.kv files loaded — all v2.0 Flat Grind functionality works without a single behavior change
  2. Each Flat Grind screen has its own .kv file that contains only that screen's layout — no shared kv file references Flat Grind layout rules
  3. No kv rule name collision exists: grep for duplicate `<ClassName>:` headers across all kv files returns zero matches
  4. A hardware-equivalent smoke test (simulated or real controller) confirms the Run page cycle, jog, teach, and parameter write all function correctly under the new class names
**Plans:** 2/2 plans complete
Plans:
- [x] 19-01-PLAN.md — Create screens/flat_grind/ package and ui/flat_grind/ KV files with FlatGrind* classes
- [x] 19-02-PLAN.md — Wire app to FlatGrind* classes: re-export wrappers, main.py, base.kv, test imports

### Phase 20: Screen Registry and Loader
**Goal**: The application detects the connected machine type and loads the correct screen set under canonical names — machine switching is a restart-and-reconnect, not a hot-swap, and the swap function tears down threads and figures cleanly
**Depends on**: Phase 19
**Requirements**: LOAD-01, LOAD-02, LOAD-03, LOAD-04
**Success Criteria** (what must be TRUE):
  1. machine_config._REGISTRY for each machine type includes a screen_classes key mapping "run", "axes_setup", "parameters" to the correct Python class
  2. Connecting to a controller that reports machine type "flat_grind" causes the app to load FlatGrind* screens; connecting to "serration" loads Serration* screens — verified by inspecting the ScreenManager widget tree
  3. Calling _load_machine_screens() stops the position poll thread and closes the matplotlib figure before removing the outgoing screens — no background thread or figure handle leak after the swap
  4. After a machine type switch and restart, navigating to Run, Axes Setup, and Parameters each shows the correct screen for the active machine type
**Plans:** 2/2 plans complete
Plans:
- [x] 20-01-PLAN.md — Extend _REGISTRY with screen_classes/load_kv and add cleanup() to base classes
- [x] 20-02-PLAN.md — Wire _load_machine_screens() loader, update build()/on_stop()/base.kv, add machType mismatch detection

### Phase 21: Serration Screen Set
**Goal**: The Serration Grind machine has its own Run, Axes Setup, and Parameters screens reachable through the screen loader — 3-axis layout with D-axis removed and bComp panel stubbed pending customer DMC program
**Depends on**: Phase 20
**Requirements**: SERR-01, SERR-02, SERR-03, SERR-04
**Success Criteria** (what must be TRUE):
  1. Connecting with machine type "serration" loads SerrationRunScreen, SerrationAxesSetupScreen, SerrationParametersScreen — no FlatGrind* class is used for any Serration screen
  2. The Serration Axes Setup screen shows only A, B, and C axis controls — D-axis jog buttons and position labels are absent from the layout
  3. The Serration Run page contains a bComp panel area that is clearly marked as pending customer DMC program — it does not crash or error when rendered
  4. Editing a Serration-specific parameter and saving it writes only Serration param_defs values — no Flat Grind parameter keys are written
**Plans:** 2/2 plans complete
Plans:
- [x] 21-01-PLAN.md — Serration package skeleton, thin subclasses (AxesSetup, Parameters), KV files, registry update, test scaffold
- [x] 21-02-PLAN.md — SerrationRunScreen with BCompPanel widget, run.kv, full test coverage

### Phase 22: Convex Screen Set
**Goal**: The Convex Grind machine has its own Run, Axes Setup, and Parameters screens reachable through the screen loader — 4-axis layout with convex-specific controls, placeholder param_defs noted for future customer sign-off
**Depends on**: Phase 20
**Requirements**: CONV-01, CONV-02, CONV-03, CONV-04
**Success Criteria** (what must be TRUE):
  1. Connecting with machine type "convex" loads ConvexRunScreen, ConvexAxesSetupScreen, ConvexParametersScreen — no FlatGrind* or Serration* class is used for any Convex screen
  2. The Convex Run page includes a convex-specific adjustment panel not present on the Flat Grind or Serration run screens
  3. The Convex Axes Setup screen shows all four axes (A, B, C, D) with correct labels for convex machine axis roles
  4. Convex param_defs are clearly marked as placeholder in machine_config comments — a code comment identifies which values need customer production specs before sign-off
**Plans:** 2/2 plans complete
Plans:
- [x] 22-01-PLAN.md — Convex package skeleton, thin subclasses, KV files, registry update, explicit _CONVEX_PARAM_DEFS, test scaffold
- [x] 22-02-PLAN.md — ConvexRunScreen with ConvexAdjustPanel, full run.kv, complete test coverage

### Phase 23: Controller Communication Optimization
**Goal**: The controller poll loop uses a single batched MG command for all position and state reads (GRecord confirmed absent from gclib Python wrapper), state transitions are detected via structured MG messages on an app-wide reader thread, and all gclib handles have explicit timeouts and use the direct connection flag
**Depends on**: Phase 18
**Requirements**: COMM-01, COMM-02, COMM-03, COMM-04, COMM-05, COMM-06
**Success Criteria** (what must be TRUE):
  1. The poll loop issues a single batched MG command per tick instead of 7-8 individual MG commands for positions and state — verified by confirming ctrl.cmd call_count drops to 1 per tick
  2. hmiState, ctSesKni, ctStnKni, and _XQ are read in the same single MG command as positions — no individual MG commands for these variables remain in poll.py
  3. The DMC program emits a structured MG message (e.g. "STATE:3") at each state transition and the app-wide MG reader thread dispatches to registered handlers within one message receipt
  4. Connecting with the --direct flag bypasses gcaps middleware and establishes a production-speed connection — confirmed by observing connection log output
  5. A gclib timeout error on the primary handle produces a timeout exception within 1000 ms; on the MG handle within 500 ms — not a hang
**Plans:** 3/3 plans complete
Plans:
- [x] 23-01-PLAN.md — Batch read function (read_all_state), connection hardening (--direct, --timeout), updated tests
- [x] 23-02-PLAN.md — App-wide MgReader module with position/state/log message parsing, tests
- [x] 23-03-PLAN.md — Wire read_all_state into RunScreen._tick_pos, wire MgReader into main.py, remove per-screen MG code

---

### Phase 24: Windows PyInstaller Bundle
**Goal**: The application runs on a clean Windows 11 machine from a self-contained onedir folder — Python, all dependencies, and the gclib DLL are included, mutable user data persists across restarts, and the frozen build passes a clean-VM smoke test
**Depends on**: Phase 23 (v3.0 complete)
**Requirements**: WIN-01, WIN-02, WIN-05, WIN-07
**Success Criteria** (what must be TRUE):
  1. Running BinhAnHMI.exe on a Windows 11 VM with no Python, no Galil SDK, and no prior app install opens the Kivy window and reaches the PIN login screen
  2. Connecting to a Galil controller from the frozen app succeeds — the controller connection log shows the same response as the dev environment, confirming the gclib DLL loaded from the bundle
  3. Logging in, creating a user, and restarting the app shows the user still exists — users.json persisted to %APPDATA%/BinhAnHMI/, not wiped from _MEIPASS on restart
  4. Right-clicking BinhAnHMI.exe and viewing Properties shows the correct version number in the Details tab
**Plans:** 1/2 plans executed
Plans:
- [ ] 24-01-PLAN.md — Frozen-mode code: __version__, _get_data_dir(), GCLIB_ROOT patch, window title, diagnostics exclusion, tests
- [ ] 24-02-PLAN.md — Deploy infrastructure: vendor DLLs, PyInstaller spec, version file, icon, build script, bundle build + human verify

### Phase 25: Windows Inno Setup Installer
**Goal**: A single .exe installer delivers the app to Windows 11 with Start Menu and Desktop shortcuts, an Add/Remove Programs entry with working uninstaller, optional auto-start on login, and a firewall rule for DR UDP — no manual steps required after running the installer
**Depends on**: Phase 24
**Requirements**: WIN-03, WIN-04, WIN-06
**Success Criteria** (what must be TRUE):
  1. Running BinhAn_HMI_v4.0.0_Setup.exe installs the app and creates Start Menu and Desktop shortcuts that launch it — confirmed on a machine that has never had the app installed
  2. The app appears in Windows Settings > Apps > Installed apps and uninstalling it via that interface removes all installed files with no leftovers in Program Files — APPDATA preserved
  3. Checking the optional "Launch at Windows startup" box during install causes the app to launch automatically on the next login — unchecking it removes the Run key
**Plans:** 2/2 plans complete
Plans:
- [ ] 25-01-PLAN.md — Test scaffold, Inno Setup .iss script, build script ISCC integration
- [ ] 25-02-PLAN.md — Build installer and human verification (shortcuts, Add/Remove, auto-start, firewall, uninstall)

### Phase 26: Pi OS Preparation and Install Script
**Goal**: A single install.sh script sets up the Binh An HMI as a normal desktop application on a fresh Raspberry Pi 4/5 running 64-bit Pi OS Bookworm — X11 forcing, apt dependencies (including aarch64 Kivy build toolchain), Galil gclib, venv, pip install, desktop shortcut, screen blanking disable, and SSH enable. Kiosk lockdown deferred to a future phase.
**Depends on**: Phase 23 (v3.0 complete — parallel track, independent of Phase 24)
**Requirements**: PI-01, PI-04, PI-05
**Success Criteria** (what must be TRUE):
  1. Running install.sh on a fresh 64-bit Bookworm SD card completes without manual intervention — venv is created, all pip installs succeed (Kivy compiles from source on aarch64), desktop shortcut works
  2. After reboot, the app launches from the desktop shortcut and reaches the PIN login screen under X11
  3. _get_data_dir() on Linux returns ~/.binh-an-hmi/ and creates the directory on first launch
**Plans:** 2 plans
Plans:
- [ ] 26-01-PLAN.md — _get_data_dir() Linux branch, deploy/pi/ skeleton files (requirements-pi.txt, .desktop, icon)
- [ ] 26-02-PLAN.md — install.sh script and content-inspection test suite

### Phase 27: Screen Resolution Detection
**Goal**: The app reads the display geometry before any Kivy Window import and applies the correct layout preset — operators on 7", 10", and 15" displays all get a usable interface, and a settings.json override allows a technician to force a preset without editing code
**Depends on**: Phase 24 (APPDATA path stability), Phase 26 (install.sh structure for KIVY_DPI env)
**Requirements**: APP-04
**Success Criteria** (what must be TRUE):
  1. Launching the app on a 7-inch Pi touchscreen (800x480) applies the 7inch preset — font sizes and touch targets are legible and tappable without zooming
  2. Setting display_size: "10inch" in settings.json and restarting forces the 10-inch preset regardless of what screeninfo detects — the override is confirmed by a log line at startup
  3. Launching on a 1920x1080 Windows monitor applies the 15inch/desktop preset with no manual configuration
**Plans**: TBD

### Phase 28: Logging Infrastructure
**Goal**: Every app run produces a rotating log file in the platform-correct location, uncaught exceptions are captured with full traceback before the app exits, and installed packages contain only runtime files
**Depends on**: Phase 24 (_get_data_dir() pattern established)
**Requirements**: APP-01, APP-02, APP-03
**Success Criteria** (what must be TRUE):
  1. After a normal app session on Windows, app.log exists in %APPDATA%/DMCGrindingGUI/logs/ and contains timestamped entries — on Pi it exists in ~/.dmc_gui/logs/
  2. Triggering an unhandled exception (e.g., passing bad data to a controller call) causes the full traceback to appear in app.log before the app exits — the exception is not silently swallowed
  3. The installed Windows bundle and Pi deployment directory contain no .md files, no .planning/ directory, no test files, no .xlsx files, and no .dmc files
**Plans**: TBD

### Phase 29: Integration Testing and Field Validation
**Goal**: Both platform packages pass a hardware gate — the Windows installer is validated on a real factory-floor machine and the Pi kiosk is validated with a live Galil controller connected — and three Pi deployment methods are confirmed working
**Depends on**: Phase 25, Phase 26, Phase 27, Phase 28
**Requirements**: FIX-02, PI-06
**Success Criteria** (what must be TRUE):
  1. Installing DMCGrindingGUI_Setup.exe on the target factory Windows machine (with default Defender active) launches successfully — no AV quarantine, no missing DLL error
  2. Running a Flat Grind cycle on the real Galil controller through the Windows installer shows the live A/B plot updating, buttons graying out during motion, and machine state updating in real-time
  3. All three Pi deployment methods produce a working kiosk: (a) USB/SCP folder transfer + install.sh, (b) SD card image write, (c) git clone + install.sh — each confirmed by a full boot-to-login-screen test
  4. The Pi kiosk with controller connected successfully runs a Flat Grind cycle — DR streaming produces live position data on the run screen
**Plans**: TBD

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Auth and Navigation | v1.0 | 4/4 | Complete | 2026-04-04 |
| 2. RUN Page | v1.0 | 4/4 | Complete | 2026-04-04 |
| 3. Live Matplotlib Plot | v1.0 | 1/1 | Complete | 2026-04-04 |
| 4. Axes Setup and Parameters | v1.0 | 3/3 | Complete | 2026-04-04 |
| 5. CSV Profile System | v1.0 | 3/3 | Complete | 2026-04-04 |
| 6. Machine-Type Differentiation | v1.0 | 3/3 | Complete | 2026-04-04 |
| 7. Admin and User Management | v1.0 | 2/2 | Complete | 2026-04-06 |
| 8. Pi Kiosk and Deployment | v1.1 | 0/TBD | Deferred | - |
| 9. DMC Foundation | v2.0 | 3/3 | Complete | 2026-04-06 |
| 10. State Poll | v2.0 | 3/3 | Complete | 2026-04-06 |
| 11. E-STOP Safety | v2.0 | 2/2 | Complete | 2026-04-06 |
| 12. Run Page Wiring | v2.0 | 1/1 | Complete | 2026-04-06 |
| 13. Setup Loop | v2.0 | 3/3 | Complete | 2026-04-06 |
| 14. State-Driven UI | v2.0 | 2/2 | Complete | 2026-04-06 |
| 15. Run Page Missing Controls | v2.0 | 1/1 | Complete | 2026-04-06 |
| 16. ProfilesScreen Setup Loop Fix | v2.0 | 1/1 | Complete | 2026-04-07 |
| 17. Poll Reset and Cold-Start Fix | v2.0 | 1/1 | Complete | 2026-04-07 |
| 18. Base Class Extraction | v3.0 | 2/2 | Complete | 2026-04-11 |
| 19. Flat Grind Rename and KV Split | v3.0 | 2/2 | Complete | 2026-04-11 |
| 20. Screen Registry and Loader | v3.0 | 2/2 | Complete | 2026-04-11 |
| 21. Serration Screen Set | v3.0 | 2/2 | Complete | 2026-04-13 |
| 22. Convex Screen Set | v3.0 | 2/2 | Complete | 2026-04-13 |
| 23. Controller Communication Optimization | v3.0 | 3/3 | Complete | 2026-04-13 |
| 24. Windows PyInstaller Bundle | v4.0 | 2/2 | Complete | 2026-04-21 |
| 25. Windows Inno Setup Installer | v4.0 | 2/2 | Complete | 2026-04-22 |
| 26. Pi OS Preparation and Install Script | v4.0 | 0/2 | Not started | - |
| 27. Screen Resolution Detection | v4.0 | 0/TBD | Not started | - |
| 28. Logging Infrastructure | v4.0 | 0/TBD | Not started | - |
| 29. Integration Testing and Field Validation | v4.0 | 0/TBD | Not started | - |

---

*Roadmap created: 2026-04-06*
*v2.0 phases added: 2026-04-06*
*v3.0 phases added: 2026-04-11*
*v4.0 phases added: 2026-04-21*
