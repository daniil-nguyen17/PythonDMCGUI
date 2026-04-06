# Roadmap: DMC Grinding GUI

## Milestones

- ✅ **v1.0 MVP** — Phases 1-7 (shipped 2026-04-06) | Phase 8 deferred
- ⏸ **v1.1 Deployment** — Phase 8: Pi Kiosk (pending hardware validation)
- 🚧 **v2.0 Flat Grind Integration** — Phases 9-14 (in progress)

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

### 🚧 v2.0 Flat Grind Integration (Phases 9-17)

- [x] **Phase 9: DMC Foundation** — Modify DMC program and add Python HMI constants/state fields — hard prerequisite for all wiring (completed 2026-04-06)
- [x] **Phase 10: State Poll** — Wire 10 Hz poll to read hmiState and axis positions from real controller (completed 2026-04-06)
- [x] **Phase 11: E-STOP Safety** — Validate priority stop path and motion-state gate before any motion commands are wired (completed 2026-04-06)
- [x] **Phase 12: Run Page Wiring** — Wire all operator Run page buttons to real DMC subroutines (completed 2026-04-06)
- [x] **Phase 13: Setup Loop** — Wire Setup page entry, homing, jog, teach points, parameters write, and exit (completed 2026-04-06)
- [x] **Phase 14: State-Driven UI** — Button enable/disable, status labels, setup badge, and live plot validation
- [ ] **Phase 15: Run Page Missing Controls** — Restructure Run page layout: Stone Compensation card with persistent startPtC readback (layout gap closure)
- [ ] **Phase 16: ProfilesScreen Setup Loop Fix** — Fix smart-enter guard and exit-setup wiring in ProfilesScreen (gap closure)
- [ ] **Phase 17: Poll Reset and Cold-Start Fix** — Reset _fail_count on reconnect and fix cold-start E-STOP label (gap closure)
 (completed 2026-04-06)

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
- [ ] 10-01-PLAN.md — Extend dmc_vars.py, MachineState, and DMC program with knife count + Thread 2
- [ ] 10-02-PLAN.md — Create ControllerPoller module and wire into app lifecycle
- [ ] 10-03-PLAN.md — Migrate RunScreen to MachineState subscription, add knife count and disconnect UI

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
- [ ] 11-01-PLAN.md — Priority job infrastructure (submit_urgent, reset_handle, program_running poll)
- [ ] 11-02-PLAN.md — Wire E-STOP, Stop, RECOVER buttons and motion gate on RunScreen

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
**Plans**: TBD

### Phase 13: Setup Loop
**Goal**: A Setup user can enter controller setup mode from the HMI, home the machine, jog all axes, teach rest and start points, write parameter values to the controller, trigger recalculation, and return to main loop — entirely from the touchscreen.
**Depends on**: Phase 9, Phase 10, Phase 11
**Requirements**: SETP-01, SETP-02, SETP-03, SETP-04, SETP-05, SETP-06, SETP-07, SETP-08
**Success Criteria** (what must be TRUE):
  1. Tapping Enter Setup on the HMI sends hmiSetp=0 and the controller enters its #SETUP loop — hmiState reflects SETUP state within one poll tick
  2. Tapping Home (Setup/Admin only) sends hmiHome=0 and all axes move to their home positions — confirmed on real hardware
  3. Tapping jog +/- on any axis causes that axis to move the configured step distance on the real controller — no conflict with the DMC #WheelJg loop observed
  4. Tapping Teach Rest Point writes current axis positions to restPt[] on the controller; Teach Start Point writes to startPt[] — values confirmed by reading back from controller terminal
  5. Editing a parameter value and saving writes the new value to the controller variable and triggers hmiCalc=0 — the controller recalculates derived values (verified by reading back a derived variable)
  6. Tapping Exit Setup returns the controller to the #MAIN loop — hmiState returns to IDLE within one poll tick
**Plans**: TBD

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
- [ ] 14-01-PLAN.md — StatusBar state label, setup badge, and tab gating
- [ ] 14-02-PLAN.md — Cross-screen button gating (Profiles import, Parameters apply)

---

### Phase 15: Run Page Missing Controls
**Goal**: The Run page Stone Compensation controls move from the bottom action bar into a dedicated card in the right column with a persistent startPtC readback label, and requirements RUN-02, RUN-03, RUN-06 are re-mapped to Phase 13 where they are already implemented.
**Depends on**: Phase 12
**Requirements**: RUN-02, RUN-03, RUN-06 (re-mapped to Phase 13 — layout only)
**Gap Closure**: Closes gaps from v2.0 audit
**Success Criteria** (what must be TRUE):
  1. More Stone and Less Stone buttons appear in a Stone Compensation card in the right column, not in the bottom action bar
  2. A persistent startPtC label in the card shows the current stone position
  3. RUN-02, RUN-03, RUN-06 traceability updated to Phase 13 (complete)
**Plans:** 1 plan
Plans:
- [ ] 15-01-PLAN.md — Stone Compensation card layout and traceability re-mapping

### Phase 16: ProfilesScreen Setup Loop Fix
**Goal**: ProfilesScreen correctly enters and exits controller setup mode using the same smart-enter/exit pattern as AxesSetupScreen and ParametersScreen.
**Depends on**: Phase 13
**Requirements**: SETP-01, SETP-08
**Gap Closure**: Closes gaps from v2.0 audit
**Success Criteria** (what must be TRUE):
  1. Navigating to ProfilesScreen while already in STATE_SETUP does not re-send hmiSetp=0
  2. Leaving ProfilesScreen sends hmiExSt=0 (not hmiSetp=1) to correctly exit setup mode

### Phase 17: Poll Reset and Cold-Start Fix
**Goal**: Controller poller resets cleanly between disconnect/reconnect cycles and the status bar shows OFFLINE (not E-STOP) before the first successful connection.
**Depends on**: Phase 10, Phase 14
**Requirements**: POLL-03, UI-02
**Gap Closure**: Closes gaps from v2.0 audit
**Success Criteria** (what must be TRUE):
  1. After disconnect_and_refresh(), _fail_count is reset to 0 so reconnection starts with a clean slate
  2. Before the first successful poll, the status bar shows OFFLINE instead of E-STOP

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
| 11. E-STOP Safety | 2/2 | Complete   | 2026-04-06 | - |
| 12. Run Page Wiring | 1/1 | Complete    | 2026-04-06 | - |
| 13. Setup Loop | 3/3 | Complete   | 2026-04-06 | - |
| 14. State-Driven UI | 2/2 | Complete    | 2026-04-06 | - |
| 15. Run Page Missing Controls | v2.0 | 0/1 | Pending | - |
| 16. ProfilesScreen Setup Loop Fix | v2.0 | 0/TBD | Pending | - |
| 17. Poll Reset and Cold-Start Fix | v2.0 | 0/TBD | Pending | - |

---

*Roadmap created: 2026-04-06*
*v2.0 phases added: 2026-04-06*
