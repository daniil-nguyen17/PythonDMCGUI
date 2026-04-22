# Phase 29: Integration Testing and Field Validation - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Validate both platform packages on real hardware with a live Galil controller. Windows installer passes a clean-VM gate. Three Pi deployment methods are confirmed working. Display presets from Phase 27 are validated and tuned on actual touchscreens. Bugs found during testing are fixed inline. A deployment guide is created for technicians.

</domain>

<decisions>
## Implementation Decisions

### Hardware availability
- Galil controller available and connected — can run live Flat Grind cycles (FIX-02)
- Raspberry Pi with touchscreen(s) ready — multiple screen sizes available for preset validation
- Windows: both dev machine (Galil SDK installed) and separate clean factory PC available
- All four success criteria are testable with current hardware

### Test & fix workflow
- Bugs found during validation are fixed inline in Phase 29 — no separate fix phases
- Test results documented as pass/fail checklist in SUMMARY.md with notes per test and log excerpts for failures — no screenshots required
- Phase 27 display preset validation included in scope (beyond FIX-02 and PI-06)
- If KIVY_METRICS_DENSITY values (0.65/0.75/1.0) don't look right on real screens, tune them inline during Phase 29 — iterative adjustment at the hardware

### Pi deployment methods
- **USB/SCP method:** copy full repo to Pi via USB or SCP, then run install.sh (handles exclusions via rsync). Simplest for technicians.
- **SD card image method:** manual process with documented steps (install on Pi, configure, capture with Pi Imager/dd). No automation script — FUTURE-02 in REQUIREMENTS.md covers automation tooling.
- **git clone method:** Pi has internet access, clones from GitHub directly, then runs install.sh. Standard workflow.
- All three methods tested to boot-to-login-screen as the pass/fail gate

### Deployment documentation
- Create a simple `deploy/pi/README.md` with step-by-step instructions for each of the three Pi deployment methods
- Technicians need this to deploy without the developer present
- Also create `deploy/windows/README.md` with Windows installer instructions

### Windows validation
- Test on dev machine first (smoke test), then validate on clean factory PC (true gate)
- Clean-VM test: no Python, no Galil SDK, no dev tools — installer must work standalone
- Windows Defender active (default) — no AV exclusions, no admin overrides

### Claude's Discretion
- Test execution order and grouping
- How to structure the checklist in SUMMARY.md
- Exact steps in deployment READMEs
- Whether to create a formal test matrix or keep it informal
- How to handle Pi image creation documentation format

</decisions>

<specifics>
## Specific Ideas

- The clean Windows PC test is the most important gate — it validates WIN-01 and WIN-02 (PyInstaller bundle works without pre-installed software)
- Multiple Pi touchscreen sizes available means Phase 27 density values can be validated in a single session
- FIX-02 (Flat Grind on real controller) is the ultimate validation that v1.0-v3.0 code works end-to-end through the packaged installer
- install.sh is idempotent — can re-run after fixes without starting over

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `deploy/windows/build_windows.bat`: Builds PyInstaller bundle + Inno Setup installer
- `deploy/windows/BinhAnHMI.spec`: PyInstaller spec with all datas/binaries/excludes
- `deploy/pi/install.sh`: Idempotent Pi setup script (X11, apt, gclib, venv, pip, desktop shortcut)
- `tests/test_installer.py`: Existing Windows installer tests (content inspection)
- `tests/test_install_pi.py`: Existing Pi install script tests (content inspection)
- `tests/test_bundle_exclusions.py`: Bundle content verification tests (Phase 28)

### Established Patterns
- Content-inspection tests: validate spec/install.sh without building (test_installer.py, test_install_pi.py, test_bundle_exclusions.py)
- Phase 27 display presets: `_DISPLAY_PRESETS` dict in main.py with density/fullscreen/borderless per preset
- Phase 28 logging: `setup_logging()` creates app.log in `_get_data_dir()/logs/` — log file presence confirms app ran

### Integration Points
- `deploy/windows/build_windows.bat` → `dist/BinhAnHMI/` → Inno Setup → `DMCGrindingGUI_Setup.exe`
- `deploy/pi/install.sh` → `/opt/binh-an-hmi/` + `~/Desktop/BinhAnHMI.desktop`
- `src/dmccodegui/main.py` `_DISPLAY_PRESETS` → density tuning target
- `%APPDATA%/BinhAnHMI/logs/app.log` and `~/.binh-an-hmi/logs/app.log` → validation evidence

</code_context>

<deferred>
## Deferred Ideas

- **SD card image automation** — FUTURE-02 in REQUIREMENTS.md covers tooling for zero-touch Pi deployment via automated image creation
- **Pi splash screen** — FUTURE-03 in REQUIREMENTS.md (optional branding during startup)

</deferred>

---

*Phase: 29-integration-testing-and-field-validation*
*Context gathered: 2026-04-22*
