# Requirements: DMC Grinding GUI v4.0 Packaging & Deployment

**Defined:** 2026-04-21
**Core Value:** An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion, zero access to things they shouldn't touch.

## v4.0 Requirements

### Bug Fixes

- [x] **FIX-01**: Grind-end race condition fixed — 2s grace period after on_start_grind prevents false grind-end detection from stale IDLE state in both DR and TCP poll paths (Flat Grind + Serration)
- [ ] **FIX-02**: Flat Grind run page validated on real controller — graph draws during grind, buttons gray out during motion, machine state updates in real-time

### Windows Packaging

- [ ] **WIN-01**: App launches on a clean Windows 11 machine from a PyInstaller onedir bundle with Python, all dependencies, and gclib DLL included — no pre-installed software required
- [ ] **WIN-02**: gclib DLL is vendored in the repo and bundled in the frozen build — app connects to Galil controller without Galil SDK installed on target
- [x] **WIN-03**: Inno Setup installer creates Start Menu and Desktop shortcuts that launch the app
- [x] **WIN-04**: App appears in Windows Add/Remove Programs with a working uninstaller that cleanly removes all installed files
- [x] **WIN-05**: users.json and settings.json are stored in %APPDATA%/DMCGrindingGUI/, not in the frozen temp directory — user accounts persist across app restarts
- [x] **WIN-06**: Installer offers an optional "Launch at Windows startup" checkbox that adds HKCU Run key for auto-start on login
- [x] **WIN-07**: Version number is visible in the EXE file properties and in the installer window title

### Pi Deployment

- [x] **PI-01**: install.sh creates a Python venv with all dependencies (Kivy, matplotlib, gclib, kivy_matplotlib_widget) on Pi OS Bookworm
- [ ] **PI-02**: systemd service auto-restarts the app on crash (Restart=on-failure, RestartSec=3, StartLimitBurst=5)
- [ ] **PI-03**: App runs fullscreen on Pi with no path for operators to reach the desktop, file manager, or terminal
- [x] **PI-04**: install.sh forces X11 session (disables Wayland) as its first operation — Kivy cannot run on Wayland
- [ ] **PI-05**: A single install.sh script handles all Pi setup: apt deps, Galil .deb, venv creation, pip install, systemd enable, kiosk config
- [ ] **PI-06**: Three deployment methods documented and tested: USB/SCP folder transfer, SD card image, git clone + install.sh
- [ ] **PI-07**: systemd hardware watchdog (WatchdogSec=30) with sdnotify heartbeat in the app detects frozen-but-alive states and restarts

### App Infrastructure

- [ ] **APP-01**: Rotating log file writes to platform-correct location (APPDATA on Windows, ~/.dmc_gui/logs/ on Pi) with 5 MB limit and 3 backups
- [ ] **APP-02**: All uncaught exceptions are logged with full traceback before the app exits (sys.excepthook patched before Kivy import)
- [ ] **APP-03**: Packages exclude non-runtime files: .md, .planning/, tests/, .xlsx, .dmc from installed bundle
- [ ] **APP-04**: App auto-detects screen resolution at startup with manual override option in settings.json for 7"/10"/15" displays

## Future Requirements

### v4.x (After Hardware Validation)

- **FUTURE-01**: Admin log viewer — in-app modal showing last 200 lines of app.log, restricted to Admin role
- **FUTURE-02**: SD card image automation tooling for zero-touch Pi deployment
- **FUTURE-03**: Pi splash screen during app startup (optional)

## Out of Scope

| Feature | Reason |
|---------|--------|
| OTA/network updates | Industrial change management, air-gapped networks |
| External crash reporting (Sentry) | Network constraints, IP concerns |
| --onefile PyInstaller | Breaks SDL2 DLL loading, temp dir data loss |
| Splash screen / branding | Irrelevant for kiosk HMI that runs fullscreen from boot |
| NSIS installer | Inno Setup is simpler for this use case |
| Auto Pi OS upgrade in install.sh | Risk of breaking gclib/Kivy system deps |
| In-app Check for Updates | Industrial change management process is manual by design |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIX-01 | Pre-milestone | Complete |
| FIX-02 | Phase 29 | Pending |
| WIN-01 | Phase 24 | Pending |
| WIN-02 | Phase 24 | Pending |
| WIN-03 | Phase 25 | Complete |
| WIN-04 | Phase 25 | Complete |
| WIN-05 | Phase 24 | Complete |
| WIN-06 | Phase 25 | Complete |
| WIN-07 | Phase 24 | Complete |
| PI-01 | Phase 26 | Complete |
| PI-02 | Phase 26 | Pending |
| PI-03 | Phase 26 | Pending |
| PI-04 | Phase 26 | Complete |
| PI-05 | Phase 26 | Pending |
| PI-06 | Phase 29 | Pending |
| PI-07 | Phase 26 | Pending |
| APP-01 | Phase 28 | Pending |
| APP-02 | Phase 28 | Pending |
| APP-03 | Phase 28 | Pending |
| APP-04 | Phase 27 | Pending |

**Coverage:**
- v4.0 requirements: 20 total
- Mapped to phases: 20/20
- Unmapped: 0

---
*Requirements defined: 2026-04-21*
*Last updated: 2026-04-21 — traceability updated after v4.0 roadmap creation (Phases 24-29)*
