# Project Research Summary

**Project:** DMC Grinding GUI -- v4.0 Packaging and Deployment
**Domain:** Python/Kivy industrial HMI -- Windows installer + Raspberry Pi kiosk deployment
**Researched:** 2026-04-21
**Confidence:** HIGH (overall, with MEDIUM gaps on gclib DLL bundling and screeninfo on Pi)

## Executive Summary

This milestone converts a fully working Python/Kivy industrial HMI into distributable packages for two target platforms: a Windows 11 workstation installer and a Raspberry Pi kiosk. All application functionality is already built; v4.0 is purely a packaging and deployment concern. The recommended approach uses PyInstaller 6.19 (onedir mode) + Inno Setup 6.7 for Windows, and a venv + systemd kiosk via install.sh for Pi. Neither platform requires Python pre-installed by the end user. The build layer lives entirely in a new deploy/ directory at the project root and never modifies src/dmccodegui/.

The highest-risk item on Windows is gclib DLL discovery: PyInstaller cannot auto-detect ctypes-loaded DLLs, so gclib.dll must be vendored into the repo and explicitly listed in the spec binaries= section, with a GCLIB_ROOT environment patch at the top of main.py. The second critical issue is that users.json and settings.json must be redirected from sys._MEIPASS (read-only temp dir) to APPDATA/DMCCodeGUI/ before the frozen app is considered functional, or user accounts vanish on every restart. On Pi the blocking issue is Bookworm default Wayland: Kivy has no Wayland support and the setup script must force X11 via raspi-config before anything else will work.

The overall risk profile is manageable because every pitfall has a known, documented fix. The main execution risk is ordering: several fixes must be in place before the PyInstaller spec file is finalized (path resolution, gclib bundling), and the Pi Galil .deb must be installed before the venv is created. If the build order is followed correctly, the deployment is reproducible and suitable for field use at a single grinding machine site.

---

## Key Findings

### Recommended Stack

The Windows packaging chain is PyInstaller 6.19 in --onedir mode (mandatory: --onefile breaks SDL2 DLL loading and causes silent temp-dir data loss) producing a folder output, then Inno Setup 6.7 wrapping that folder into a .exe installer. Kivy SDL2 and GLEW binaries must be explicitly injected into the PyInstaller COLLECT() via sdl2.dep_bins and glew.dep_bins Tree entries -- without these the Kivy window never opens, with no meaningful error.

For Raspberry Pi, the deployment runtime is Python 3.11 venv on Pi OS Bookworm with PiWheels as the Kivy wheel source (avoids 2-hour source builds). Autostart uses a systemd service with Restart=on-failure targeting graphical-session.target with X11 forced via raspi-config. Screen resolution is handled by screeninfo-based detection in a pre-Kivy block at the top of main.py, consistent with the existing Config.set ordering pattern already in the codebase.

**Core technologies:**
- **PyInstaller 6.19 (onedir):** Windows bundler -- only packager with first-class Kivy SDL2/GLEW hooks
- **Inno Setup 6.7:** Windows installer -- declarative, handles shortcuts + uninstaller, 80% less code than NSIS
- **Python 3.11 venv + PiWheels:** Pi runtime -- PiWheels provides pre-compiled Kivy ARM wheels, eliminating source builds
- **systemd service:** Pi autostart -- modern Bookworm standard; LXDE autostart no longer exists on Bookworm
- **screeninfo 0.8.1:** Display detection -- works without a display server, before any Kivy import
- **kivy-deps.sdl2 / kivy-deps.glew:** Required spec file Tree injections -- Kivy window cannot open without them

### Expected Features

The v4.0 feature scope is delivery infrastructure only -- all HMI screens are already complete.

**Must have (table stakes -- v4.0 MVP):**
- Self-contained Windows onedir bundle with gclib DLL bundled (no Galil pre-install on target)
- Inno Setup installer with Start Menu shortcut, Desktop shortcut, Add/Remove Programs entry
- Pi install.sh: venv creation, PiWheels pip install, systemd unit enable, kiosk fullscreen
- Pi systemd unit with Restart=on-failure and RestartSec=3 + StartLimitBurst=5
- Rotating log file (RotatingFileHandler, 5 MB, 3 backups, platform-correct path)
- sys.excepthook patched for uncaught exception logging before any Kivy import
- Dev artifacts excluded from all packages (.planning/, tests/, .dmc, .xlsx)
- users.json / settings.json redirected to APPDATA on Windows (frozen context fix)

**Should have (differentiators -- v4.x, after hardware validation):**
- Windows optional auto-start on login (Inno Setup HKCU Run key checkbox)
- Version number embedded in Windows EXE resources and installer title
- Pi hardware watchdog (WatchdogSec=30 + sdnotify heartbeat in main.py)
- SD card image for zero-touch Pi deployment
- Screen resolution override via settings.json display_size key
- Admin log viewer (last 200 lines, in-app modal, Admin role only)

**Defer to v5.0 or drop:**
- Network/OTA updates (incompatible with industrial change management and air-gapped networks)
- External crash reporting services (network constraints, IP concerns)
- In-app Check for Updates flow

### Architecture Approach

The packaging layer is strictly a build-time and runtime-setup concern that sits in a new deploy/ directory at the project root. It never imports from or modifies src/dmccodegui/. The application source requires exactly three targeted changes: (1) GCLIB_ROOT env patch at the top of main.py for frozen context, (2) _get_data_dir() helper to redirect mutable JSON files to APPDATA, and (3) _load_display_config() function to read settings.json display preset before any Kivy Window import. All three are additions to the existing pre-Kivy block in main.py -- the ordering pattern is already established in the codebase.

**Major components:**
1. **deploy/windows/dmccodegui.spec** -- PyInstaller spec: entry point, KV/asset datas, gclib.dll binary, SDL2/GLEW Trees, hiddenimports for all machine screens and Kivy providers
2. **deploy/windows/installer.iss** -- Inno Setup: wraps build/windows/dist/ folder, creates shortcuts, Add/Remove entry, optional HKCU Run key, netsh firewall rule for DR UDP port
3. **deploy/windows/build_windows.bat** -- Single developer command: runs PyInstaller then Inno Setup in sequence
4. **deploy/pi/install.sh** -- Pi setup: apt deps, Galil .deb (before venv), venv creation, PiWheels pip install, systemd unit enable
5. **deploy/pi/dmccodegui.service** -- systemd unit: X11 environment, Restart=on-failure, After=graphical-session.target, User=pi
6. **src/dmccodegui/main.py (additions only)** -- GCLIB_ROOT patch, _get_data_dir(), _load_display_config() all in existing pre-Kivy block

### Critical Pitfalls

1. **PyInstaller --onefile mode (C1)** -- Use --onedir exclusively. --onefile silently deletes users.json on every launch and breaks SDL2 DLL loading. Inno Setup handles the folder output cleanly.
2. **SDL2/GLEW DLLs missing from spec (C2)** -- Kivy window silently fails to open. Spec must include Tree injections from sdl2.dep_bins + glew.dep_bins in COLLECT(). Must be in the initial spec.
3. **gclib DLL not bundled (C4)** -- App starts but silently falls into no-controller mode. Vendor gclib.dll into repo, add to spec binaries=, set GCLIB_ROOT=sys._MEIPASS. Widen except (ImportError, OSError) in controller.py.
4. **Bookworm Wayland blocks Kivy (C5)** -- Pi boots to black screen. raspi-config X11 switch is the first step of the Pi setup script. Set SDL_VIDEODRIVER=x11 in the systemd unit.
5. **systemd service starts before X11 is ready (C6)** -- Use After=graphical-session.target plus User=pi (not root), set DISPLAY=:0 and XAUTHORITY in the unit, enable loginctl enable-linger pi.

Additional watch items: users.json/settings.json in _MEIPASS (C1/M4 -- APPDATA redirect required), KIVY_HOME permission failure on Pi kiosk (C7 -- pre-create in install.sh), hidden imports for machine screens (C3 -- all dotted paths from _resolve_dotted_path must be in hiddenimports), AV false positives (M6 -- upx=False, test on clean Windows 11 VM).

---

## Implications for Roadmap

Based on the dependency chain from ARCHITECTURE.md and the pitfall ordering from PITFALLS.md, the natural phase structure is two parallel tracks that merge at integration testing.

### Phase 1: Windows -- PyInstaller Spec + Frozen Path Fixes
**Rationale:** The spec file is the foundation of the entire Windows track. Path fixes (APPDATA redirect, GCLIB_ROOT patch) must be implemented before the spec is written -- retrofitting them into an existing spec is harder and resets testing.
**Delivers:** A working dist/DMCGrindingGUI/ folder that launches on a clean Windows VM without Python or Galil installed.
**Addresses:** Self-contained bundle, gclib bundled, mutable data paths fixed, Kivy providers working.
**Avoids:** C1 (onedir), C2 (SDL2/GLEW Trees), C3 (hiddenimports), C4 (gclib DLL), M4 (APPDATA redirect).

### Phase 2: Windows -- Inno Setup Installer
**Rationale:** Inno Setup wraps the Phase 1 output. Cannot start until Phase 1 produces a working frozen build that has passed the clean-VM gate.
**Delivers:** DMCGrindingGUI_v4.0_Setup.exe with Start Menu shortcut, Desktop shortcut, Add/Remove Programs entry, netsh firewall rule for DR UDP.
**Uses:** Inno Setup 6.7, the dist/ folder from Phase 1.
**Avoids:** m1 (HKCU Run key in admin context), m2 (DR UDP firewall rule in installer script).

### Phase 3: Pi -- OS Preparation + Install Script
**Rationale:** Pi track is independent of Windows and can proceed in parallel with Phases 1-2. Wayland fix must be the first operation.
**Delivers:** install.sh and dmccodegui.service that produce a working kiosk on a fresh Bookworm SD card.
**Addresses:** Pi venv, systemd autostart, kiosk fullscreen, gclib .deb install.
**Avoids:** C5 (Wayland), C6 (systemd X11 timing), C7 (KIVY_HOME pre-created), M3 (Galil .deb before venv), m3 (gpu_mem in config.txt), m4 (Kivy log rotation).

### Phase 4: Screen Resolution + Display Profiles
**Rationale:** Depends on Phase 1 (stable settings.json APPDATA path) and Phase 3 (install.sh structure). Resolution detection fits after both platforms have stable data paths.
**Delivers:** _load_display_config() in main.py, preset map (7inch/10inch/15inch/kiosk), install.sh pre-write.
**Uses:** screeninfo 0.8.1, KIVY_DPI env var in systemd unit.
**Avoids:** C7 (Config.set inside frozen context -- must stay in pre-Kivy block).

### Phase 5: Logging Infrastructure
**Rationale:** Platform-correct log paths depend on Phase 1 _get_data_dir() pattern. Log infrastructure is a prerequisite for meaningful field debugging.
**Delivers:** RotatingFileHandler (5 MB, 3 backups), sys.excepthook patch, MPLCONFIGDIR env set, KIVY_LOG_LEVEL=warning in systemd unit.
**Avoids:** M1 (matplotlib Agg backend forced), m4 (Kivy log disk fill).

### Phase 6: Integration Testing + Field Validation
**Rationale:** Both platform tracks must be complete before hardware validation.
**Delivers:** Signed-off installer on Windows 11 VM, signed-off kiosk on Pi 4 or Pi 5 with Galil controller connected.
**Gate criteria:** Controller connection succeeds, user accounts persist across restarts, all machine screens load, touchscreen responds, DR streaming produces position data.
**Avoids:** M5 (touchscreen validation on actual hardware), M6 (AV quarantine test on clean Windows).

### Phase Ordering Rationale

- Phases 1-2 are strictly sequential (Inno Setup requires completed PyInstaller dist/).
- Phase 3 is independent and can run in parallel with Phases 1-2.
- Phase 4 depends on both Phase 1 (APPDATA path stability) and Phase 3 (install.sh structure).
- Phase 5 can be done in parallel with Phase 4 once _get_data_dir() is settled (end of Phase 1).
- Phase 6 must follow all prior phases.
- The gclib path fix and _get_data_dir() helper are Phase 1 prerequisites -- implement before writing the spec file.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** gclib attribute names must be confirmed against the installed gclib/__init__.py before spec work. MEDIUM confidence -- exact attribute names may vary by gclib version.
- **Phase 3:** kivy_matplotlib_widget ARM wheel availability on Bookworm unconfirmed. Confirm build procedure before writing install.sh.
- **Phase 4:** screeninfo behavior on Pi with HDMI-forced resolution needs validation on real hardware.

Phases with standard patterns (research can be skipped):
- **Phase 2:** Inno Setup scripting is well-documented; shortcut + registry patterns are boilerplate.
- **Phase 5:** Python logging.handlers.RotatingFileHandler is stdlib with zero ambiguity.
- **Phase 6:** Testing checklist -- no research needed, just hardware access.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | PyInstaller/Kivy packaging: official docs confirmed. PiWheels for Bookworm: official Kivy docs cite it. Inno Setup 6.7.1: confirmed on official downloads page. |
| Features | HIGH | Table stakes are straightforward packaging deliverables. Differentiators are optional v4.x additions. |
| Architecture | HIGH | Directory structure derived from actual codebase. Build flow cross-referenced against Kivy packaging guide and Galil docs. |
| Pitfalls | MEDIUM-HIGH | Critical pitfalls C1-C5 verified via official docs, SDL GitHub issues, RPi forums. gclib attribute name (C4) needs version verification. |

**Overall confidence:** HIGH for the build approach; MEDIUM for two specific details (gclib attribute names, kivy_matplotlib_widget on Pi ARM).

### Gaps to Address

- **gclib DLL attribute names on Windows:** Confirm GclibDllPath_ attribute names in the installed gclib/__init__.py before Phase 1. Wrong names produce a silent no-controller failure.
- **kivy_matplotlib_widget on Pi ARM:** Confirm whether a PiWheels wheel exists or source compilation on Bookworm 3.11 is required. Most likely install.sh failure point.
- **screeninfo on Pi HDMI-forced framebuffer:** Official 7-inch Pi touchscreen may report resolution unusually at 800x480. Validate on real hardware. KIVY_DPI env var is the fallback.
- **Antivirus on target Windows machines:** Must be validated on a representative factory floor machine with default Defender before declaring the installer production-ready.

---

## Sources

### Primary (HIGH confidence)
- Kivy Windows packaging guide 2.3.1 -- https://kivy.org/doc/stable/guide/packaging-windows.html
- Kivy RPi installation guide 2.3.1 -- https://kivy.org/doc/stable/installation/installation-rpi.html
- PyInstaller 6.19.0 spec files docs -- https://pyinstaller.org/en/stable/spec-files.html
- PyInstaller runtime information (sys._MEIPASS) -- https://pyinstaller.org/en/stable/runtime-information.html
- Inno Setup 6.7.1 official downloads -- https://jrsoftware.org/isdl.php
- Galil gclib Raspberry Pi OS install docs -- https://www.galil.com/sw/pub/all/doc/global/install/linux/rpios/
- Galil gclib Python wrapper class reference -- https://www.galil.com/sw/pub/all/doc/gclib/html/classgclib.html
- SDL KMSDRM RPi 5 display bug (confirmed open) -- https://github.com/libsdl-org/SDL/issues/8579
- PiWheels Bookworm/Pi 5 availability -- https://blog.piwheels.org/2023/11/debian-bookworm-and-raspberry-pi-5/
- Python stdlib logging.handlers.RotatingFileHandler -- Python 3.11 docs

### Secondary (MEDIUM confidence)
- RPi Forums Bookworm Wayland kiosk (2024-2025) -- systemd X11 timing patterns
- RPi Forums Bookworm venv autostart (February 2025) -- systemd user service + linger pattern
- PyInstaller AV false positives GitHub issue 6754 -- upx=False mitigation confirmed
- Inno Setup admin vs. user context pitfall -- w3tutorials.net
- systemd WatchdogSec + sdnotify -- oneuptime.com blog (2026-03)
- Industrial HMI USB update patterns -- delta-ia-tips.com (pattern confirmed by multiple vendors)

### Tertiary (needs validation on hardware)
- screeninfo 0.8.1 on Pi HDMI-forced 800x480 -- PyPI page only; behavior on Pi touchscreen unconfirmed
- kivy_matplotlib_widget ARM wheel on Bookworm -- GitHub mp-007/kivy_matplotlib_widget; PiWheels availability unconfirmed

---
*Research completed: 2026-04-21*
*Ready for roadmap: yes*
