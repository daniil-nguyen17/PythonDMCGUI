# Requirements: DMC Grinding GUI

**Defined:** 2026-04-06
**Core Value:** An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion, zero access to things they shouldn't touch.

## v2.0 Requirements

Requirements for Flat Grind HMI-controller integration. Each maps to roadmap phases.

### DMC Program

- [x] **DMC-01**: DMC program declares HMI trigger variables (hmiGrnd, hmiSetp, hmiMore, hmiLess, hmiNewS, hmiHome, hmiJog, hmiCalc) with default=1 in #PARAMS
- [x] **DMC-02**: DMC main polling loop (#WtAtRt) OR's each @IN[] check with its corresponding HMI variable
- [x] **DMC-03**: DMC resets each HMI variable to 1 as the first line inside each triggered block (before any motion)
- [x] **DMC-04**: DMC declares hmiState variable and sets it to distinct integer values at each state boundary (IDLE, GRINDING, SETUP, HOMING, etc.)
- [x] **DMC-05**: DMC setup loop (#SULOOP) OR's physical button checks with HMI variables for home, jog, varcalc, and exit
- [x] **DMC-06**: Array names in Python code match DMC declarations (startPt/restPt, not StartPnt/RestPnt)

### State Polling

- [x] **POLL-01**: HMI polls hmiState from controller at 10 Hz and updates MachineState.dmc_state
- [x] **POLL-02**: HMI polls axis positions (A, B, C, D) from controller and displays live values on Run page
- [x] **POLL-03**: HMI detects controller connection loss and displays disconnected status
- [x] **POLL-04**: HMI reads knife count (ctSesKni) from controller and displays on Run page

### Safety

- [x] **SAFE-01**: E-STOP sends ST ABCD immediately via priority path, not queued behind normal jobs
- [x] **SAFE-02**: Stop/Pause sends ST ABCD + HX to halt both motor motion and DMC program thread
- [x] **SAFE-03**: All motion-triggering buttons are disabled when controller reports active motion (gate on hmiState)

### Run Page

- [x] **RUN-01**: User can start a grind cycle by pressing Start Grind button (sends hmiGrnd=0)
- [ ] **RUN-02**: User can send machine to rest position by pressing Go To Rest
- [ ] **RUN-03**: User can send machine to start position by pressing Go To Start
- [x] **RUN-04**: User can stop an active grind cycle via Stop button (ST ABCD + HX)
- [x] **RUN-05**: User can adjust grind stone compensation via More Stone / Less Stone buttons
- [ ] **RUN-06**: User can start a new session (stone change) with two-step confirmation (Setup/Admin role required)
- [x] **RUN-07**: Live A/B position plot fills with real controller data during grind cycle

### Setup Integration

- [x] **SETP-01**: User can enter Setup mode on the controller from the HMI (sends hmiSetp=0)
- [ ] **SETP-02**: User can trigger homing sequence from Axes Setup page (sends hmiHome=0, Setup/Admin role required)
- [ ] **SETP-03**: User can jog axes from Axes Setup page with movement on real controller
- [ ] **SETP-04**: User can teach Rest point — saves current axis positions to restPt[] array on controller
- [ ] **SETP-05**: User can teach Start point — saves current axis positions to startPt[] array on controller
- [x] **SETP-06**: User can write parameter values from Parameters page to controller variables
- [x] **SETP-07**: User can trigger varcalc recalculation from Parameters page (sends hmiCalc=0)
- [x] **SETP-08**: User can exit Setup mode back to main loop from HMI

### State-Driven UI

- [ ] **UI-01**: Buttons enable/disable based on polled controller state (e.g., no Start Grind while already grinding)
- [ ] **UI-02**: Status label displays current controller state (IDLE, GRINDING, SETUP, HOMING, NEW SESSION)
- [ ] **UI-03**: Setup mode badge visible on all screens when controller is in setup state
- [ ] **UI-04**: Run tab disables when controller is in setup mode
- [ ] **UI-05**: Connection status indicator visible at all times

## Future Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Serration Grind (v3.0)

- **SERR-01**: Serration Grind machine wired to controller using same HMI variable pattern
- **SERR-02**: Serration-specific DMC subroutines mapped to HMI buttons

### Convex Grind (v3.0+)

- **CONV-01**: Convex Grind machine wired to controller using same HMI variable pattern
- **CONV-02**: Convex-specific DMC subroutines mapped to HMI buttons

### Deployment (deferred from v1.0)

- **DEPLOY-01**: App runs in kiosk mode on Raspberry Pi
- **DEPLOY-02**: Kiosk mode is operator-locked
- **DEPLOY-03**: SD card based deployment
- **DEPLOY-04**: App runs on Windows 11 as standard desktop application
- **DEPLOY-05**: No external config files required for deployment

### Diagnostics

- **DIAG-01**: Raw controller command terminal for Setup users
- **DIAG-02**: Array viewer showing all tracked DMC arrays
- **DIAG-03**: Command history log with timestamps

### Enhancements

- **ENH-01**: Axis position units display (mm/degrees instead of raw encoder counts)
- **ENH-02**: Profile metadata embedded in CSV
- **ENH-03**: Per-tooth B-axis compensation table with live bar chart (serration-specific)

## Out of Scope

| Feature | Reason |
|---------|--------|
| XQ direct calls to DMC subroutines | Breaks DMC state machine flow — must use HMI variable one-shot pattern only |
| Password hashing / encryption for PINs | In-house use, no network exposure |
| Multi-machine simultaneous control | One controller, one HMI instance at a time |
| Remote/network HMI access | Local touchscreen only |
| Automated testing against real controller | Hardware-in-the-loop testing is manual |
| DMC program upload from HMI | DMC program loaded separately; HMI only reads/writes variables |
| Animated screen transitions | Adds latency on industrial tool |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DMC-01 | Phase 9 | Complete |
| DMC-02 | Phase 9 | Complete |
| DMC-03 | Phase 9 | Complete |
| DMC-04 | Phase 9 | Complete |
| DMC-05 | Phase 9 | Complete |
| DMC-06 | Phase 9 | Complete |
| POLL-01 | Phase 10 | Complete |
| POLL-02 | Phase 10 | Complete |
| POLL-03 | Phase 10 | Complete |
| POLL-04 | Phase 10 | Complete |
| SAFE-01 | Phase 11 | Complete |
| SAFE-02 | Phase 11 | Complete |
| SAFE-03 | Phase 11 | Complete |
| RUN-01 | Phase 12 | Complete |
| RUN-02 | Phase 12 | Pending |
| RUN-03 | Phase 12 | Pending |
| RUN-04 | Phase 12 | Complete |
| RUN-05 | Phase 12 | Complete |
| RUN-06 | Phase 12 | Pending |
| RUN-07 | Phase 12 | Complete |
| SETP-01 | Phase 13 | Complete |
| SETP-02 | Phase 13 | Pending |
| SETP-03 | Phase 13 | Pending |
| SETP-04 | Phase 13 | Pending |
| SETP-05 | Phase 13 | Pending |
| SETP-06 | Phase 13 | Complete |
| SETP-07 | Phase 13 | Complete |
| SETP-08 | Phase 13 | Complete |
| UI-01 | Phase 14 | Pending |
| UI-02 | Phase 14 | Pending |
| UI-03 | Phase 14 | Pending |
| UI-04 | Phase 14 | Pending |
| UI-05 | Phase 14 | Pending |

**Coverage:**
- v2.0 requirements: 33 total
- Mapped to phases: 33
- Unmapped: 0

---
*Requirements defined: 2026-04-06*
*Last updated: 2026-04-06 — traceability filled after roadmap creation*
