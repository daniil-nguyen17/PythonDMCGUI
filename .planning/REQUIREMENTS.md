# Requirements: DMC Grinding GUI

**Defined:** 2026-04-21
**Core Value:** An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion, zero access to things they shouldn't touch.

## v4.1 Requirements

### Codebase Audit

- [ ] **AUDIT-01**: All dead code identified by ruff + vulture is removed (with Kivy `_REGISTRY` allowlist to prevent false positives)
- [ ] **AUDIT-02**: All unused imports removed and import ordering standardized across the codebase
- [ ] **AUDIT-03**: Docstrings updated on all public classes and functions to reflect current behavior
- [ ] **AUDIT-04**: Naming conventions consistent across modules (no mixed `log`/`logger`, no stale variable names)

### Bug Fixes

- [ ] **FIX-03**: Windows app uses ANGLE (DirectX) backend instead of OpenGL to prevent AMD GPU driver crashes during sustained plot redraws
- [ ] **FIX-04**: MG reader handles use `--direct --subscribe MG` on all platforms — controller log receives messages on both Windows and Pi
- [ ] **FIX-05**: Pi install.sh rsync excludes `venv/` directory to prevent destroying existing venv on re-installs

### UI Polish

- [ ] **UI-01**: Touch targets verified at minimum 44dp across all screens on 15" and 7" display presets
- [ ] **UI-02**: Layout consistency pass — alignment, spacing, and card sizing uniform across Run, Setup, Parameters, and Profiles screens

### Per-Machine Parameters

- [ ] **PARAM-01**: `_CONVEX_PARAM_DEFS` completed in machine_config.py with correct parameter names, ranges, and DMC variable mappings
- [ ] **PARAM-02**: Parameter read failures from controller log a warning instead of silently swallowing exceptions

### Licensing

- [ ] **LIC-01**: Hardware fingerprint module collects stable machine ID (Pi CPU serial, Windows BIOS UUID) and produces a SHA-256 hash
- [ ] **LIC-02**: Ed25519 license validator checks signed license file against current hardware fingerprint at startup — before any Kivy import
- [ ] **LIC-03**: Keygen CLI tool generates signed license files from a hardware fingerprint string (developer-only, not deployed)
- [ ] **LIC-04**: Unlicensed machines show a clear error message ("Contact Binh An") and exit — no traceback, no zombie window

### Code Protection

- [ ] **PROT-01**: Pi deployment compiles business-logic modules to `.so` via Cython and removes source `.py` files from installed app
- [ ] **PROT-02**: Windows build optionally obfuscates bytecode via PyArmor before PyInstaller bundling (two-step: obfuscate first, then package)
- [ ] **PROT-03**: `controller.py` is excluded from all compilation/obfuscation targets (gclib ctypes boundary)

## v4.0 Requirements (Shipped)

### Bug Fixes

- [x] **FIX-01**: Grind-end race condition fixed — 2s grace period after on_start_grind prevents false grind-end detection from stale IDLE state in both DR and TCP poll paths (Flat Grind + Serration)
- [x] **FIX-02**: Flat Grind run page validated on real controller — graph draws during grind, buttons gray out during motion, machine state updates in real-time

### Windows Packaging

- [x] **WIN-01**: App launches on a clean Windows 11 machine from a PyInstaller onedir bundle with Python, all dependencies, and gclib DLL included — no pre-installed software required
- [x] **WIN-02**: gclib DLL is vendored in the repo and bundled in the frozen build — app connects to Galil controller without Galil SDK installed on target
- [x] **WIN-03**: Inno Setup installer creates Start Menu and Desktop shortcuts that launch the app
- [x] **WIN-04**: App appears in Windows Add/Remove Programs with a working uninstaller that cleanly removes all installed files
- [x] **WIN-05**: users.json and settings.json are stored in %APPDATA%/DMCGrindingGUI/, not in the frozen temp directory — user accounts persist across app restarts
- [x] **WIN-06**: Installer offers an optional "Launch at Windows startup" checkbox that adds HKCU Run key for auto-start on login
- [x] **WIN-07**: Version number is visible in the EXE file properties and in the installer window title

### Pi Deployment

- [x] **PI-01**: install.sh creates a Python venv with all dependencies (Kivy, matplotlib, gclib, kivy_matplotlib_widget) on Pi OS Bookworm
- [x] **PI-04**: install.sh forces X11 session (disables Wayland) as its first operation — Kivy cannot run on Wayland
- [x] **PI-05**: A single install.sh script handles all Pi setup: apt deps, Galil .deb, venv creation, pip install, systemd enable, kiosk config
- [x] **PI-06**: Three deployment methods documented and tested: USB/SCP folder transfer, SD card image, git clone + install.sh

### App Infrastructure

- [x] **APP-01**: Rotating log file writes to platform-correct location (APPDATA on Windows, ~/.binh-an-hmi/logs/ on Pi) with 5 MB limit and 3 backups
- [x] **APP-02**: All uncaught exceptions are logged with full traceback before the app exits (sys.excepthook patched before Kivy import)
- [x] **APP-03**: Packages exclude non-runtime files: .md, .planning/, tests/, .xlsx, .dmc from installed bundle
- [x] **APP-04**: App auto-detects screen resolution at startup with manual override option in settings.json for 7"/10"/15" displays

## Future Requirements

- **PI-02**: systemd service auto-restarts the app on crash (Restart=on-failure, RestartSec=3, StartLimitBurst=5)
- **PI-03**: App runs fullscreen on Pi with no path for operators to reach the desktop, file manager, or terminal
- **PI-07**: systemd hardware watchdog (WatchdogSec=30) with sdnotify heartbeat in the app detects frozen-but-alive states and restarts
- **FUTURE-01**: Admin log viewer — in-app modal showing last 200 lines of app.log, restricted to Admin role
- **FUTURE-02**: SD card image automation tooling for zero-touch Pi deployment
- **FUTURE-03**: Pi splash screen during app startup (optional)

## Out of Scope

| Feature | Reason |
|---------|--------|
| OTA/network updates | Industrial change management, air-gapped networks |
| External crash reporting (Sentry) | Network constraints, IP concerns |
| --onefile PyInstaller | Breaks SDL2 DLL loading, temp dir data loss |
| NSIS installer | Inno Setup is simpler for this use case |
| Auto Pi OS upgrade in install.sh | Risk of breaking gclib/Kivy system deps |
| In-app Check for Updates | Industrial change management process is manual by design |
| Online activation / revocation server | Air-gapped factory, <100 deployments — offline licensing sufficient |
| Cross-compilation of Cython from Windows | ARM toolchain fragility; compile natively on Pi |
| Full mypy strict mode | Kivy stubs incomplete; only practical on non-Kivy modules |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUDIT-01 | Pending | Pending |
| AUDIT-02 | Pending | Pending |
| AUDIT-03 | Pending | Pending |
| AUDIT-04 | Pending | Pending |
| FIX-03 | Pending | Pending |
| FIX-04 | Pending | Pending |
| FIX-05 | Pending | Pending |
| UI-01 | Pending | Pending |
| UI-02 | Pending | Pending |
| PARAM-01 | Pending | Pending |
| PARAM-02 | Pending | Pending |
| LIC-01 | Pending | Pending |
| LIC-02 | Pending | Pending |
| LIC-03 | Pending | Pending |
| LIC-04 | Pending | Pending |
| PROT-01 | Pending | Pending |
| PROT-02 | Pending | Pending |
| PROT-03 | Pending | Pending |

**Coverage:**
- v4.1 requirements: 18 total
- Mapped to phases: 0
- Unmapped: 18 ⚠️

---
*Requirements defined: 2026-04-21*
*Last updated: 2026-04-28 after v4.1 milestone start*
