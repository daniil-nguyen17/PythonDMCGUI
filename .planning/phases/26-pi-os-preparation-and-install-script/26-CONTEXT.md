# Phase 26: Pi OS Preparation and Install Script - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

A single install.sh script sets up the Binh An HMI as a **normal desktop application** on a fresh Raspberry Pi OS Bookworm SD card. The script handles X11 forcing (Kivy requirement), venv creation, all pip dependencies, Galil gclib .deb installation, desktop shortcut, and basic OS config (SSH, screen blanking). Kiosk lockdown, systemd crash recovery, and hardware watchdog are explicitly deferred to a future phase after the app is validated on real Pi hardware.

**Revised requirements in scope:** PI-01, PI-04, PI-05 (partially)
**Deferred to kiosk phase:** PI-02 (systemd restart), PI-03 (fullscreen lockdown), PI-07 (watchdog)

</domain>

<decisions>
## Implementation Decisions

### Scope Reduction
- Phase 26 installs as a **normal desktop app with icon**, not a locked-down kiosk
- Kiosk mode (Openbox shortcut blocking, taskbar suppression, boot-to-app) deferred until the app is 100% tested on Pi hardware
- systemd service, crash recovery (Restart=on-failure), and hardware watchdog (WatchdogSec + sdnotify) all deferred to kiosk phase
- This is the first Pi version — install and validate before locking down

### install.sh Behavior
- **Idempotent:** every step checks before acting (skip if venv exists, skip if already installed, etc.) — safe to re-run after partial failure or for updates
- **Fail-fast:** uses `set -e` — stops on first error with clear message about which step failed
- **Self-elevating:** checks for root at top, prints "Please run with sudo" and exits if not root
- **Output:** step banners for each major operation (e.g., "==> Installing apt dependencies...") with summary at end; pip/apt output goes to log file
- **Reboot:** auto-reboots with 10-second countdown after install completes (Ctrl+C to cancel)
- **gclib .deb:** installed from vendored file in deploy/pi/vendor/ (dpkg -i)
- **Screen blanking:** disabled (DPMS off) — industrial HMI stays always-on
- **SSH:** ensured enabled and running — only maintenance access path since kiosk will block local access later

### Pi File Layout
- **App install path:** `/opt/binh-an-hmi/` — standard third-party location, owned by root
- **Venv:** inside `/opt/binh-an-hmi/venv/` (created by install.sh)
- **Mutable data:** `~/.binh-an-hmi/` (users.json, settings.json) — mirrors Windows APPDATA pattern, survives reinstall
- **Desktop shortcut:** .desktop file in `~/Desktop/` AND `/usr/share/applications/` (icon + app menu entry)

### Repo Structure (deploy/pi/)
- `deploy/pi/install.sh` — the main install script
- `deploy/pi/vendor/gclib-arm.deb` — vendored Galil gclib ARM package (sourcing TBD — researcher will investigate availability)
- `deploy/pi/binh-an-hmi.png` — app icon for desktop shortcut
- `deploy/pi/requirements-pi.txt` — pinned pip package versions for reproducible installs

### _get_data_dir() Code Change
- Modify `main.py` `_get_data_dir()` to detect Linux/Pi and return `~/.binh-an-hmi/`
- Current logic: frozen → APPDATA, dev → src/dmccodegui/auth/
- New logic: frozen → APPDATA (Windows), else Linux → ~/.binh-an-hmi/, else dev-Windows → src/dmccodegui/auth/
- This code change is part of Phase 26, not deferred

### Python and Pip Strategy
- Use Pi OS Bookworm system Python (3.11) as venv base
- Pinned versions in `deploy/pi/requirements-pi.txt` for reproducible installs
- If kivy_matplotlib_widget has no ARM wheel on PiWheels, build from source (pip install with --no-binary, install build-essential + cmake as apt deps)

### Claude's Discretion
- Exact install.sh step ordering beyond the established X11 → apt → gclib → venv → pip flow
- .desktop file contents and icon sizing
- Specific apt dependency list for Kivy/matplotlib on ARM
- Screen blanking disable method (xset, lightdm config, or xorg.conf)
- requirements-pi.txt exact version pins (research will inform these)
- Log file location for install.sh output

</decisions>

<specifics>
## Specific Ideas

- Mirrors the Windows deployment pattern: vendored dependencies in deploy/pi/vendor/ just like deploy/windows/vendor/ has gclib DLLs
- _get_data_dir() change extends existing frozen/dev detection pattern from Phase 24
- gclib ARM .deb availability is uncertain — researcher should investigate Galil's download portal and confirm ARM64 support for Bookworm

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `main.py:15-29` (`_get_data_dir()`): existing Windows/dev path logic — extend with Linux detection
- `main.py:4-9`: frozen-mode GCLIB_ROOT setup — pattern for Pi-specific startup config
- `deploy/windows/vendor/`: established pattern of vendoring platform-specific binaries
- `deploy/windows/BinhAnHMI.ico`: existing icon — can derive Pi PNG from same source

### Established Patterns
- Pre-import configuration: Config.set calls before Kivy Window import in main.py (Pi X11 forcing extends this)
- Platform detection: `getattr(sys, 'frozen', False)` and `os.environ.get('APPDATA')` — extend with `sys.platform` check
- Vendored binaries: deploy/windows/vendor/ pattern — deploy/pi/vendor/ follows same convention

### Integration Points
- `main.py` `_get_data_dir()`: needs Linux path branch
- `deploy/pi/install.sh`: new file — copies app source to /opt/binh-an-hmi/
- `deploy/pi/requirements-pi.txt`: new file — pip dependencies for ARM
- `deploy/pi/vendor/`: new directory — gclib ARM .deb
- `deploy/pi/binh-an-hmi.desktop`: new file — desktop entry template

</code_context>

<deferred>
## Deferred Ideas

- **Kiosk lockdown** — Openbox with shortcut blocking, taskbar suppression, dedicated kiosk user, boot direct to app. Deferred to future phase after hardware validation.
- **systemd crash recovery** — Restart=on-failure, RestartSec=3, StartLimitBurst=5. Deferred to kiosk phase.
- **Hardware watchdog** — WatchdogSec=30 with sdnotify heartbeat in Kivy event loop. Deferred to kiosk phase.
- **PI-02, PI-03, PI-07 requirements** — all deferred from Phase 26 to kiosk phase.

</deferred>

---

*Phase: 26-pi-os-preparation-and-install-script*
*Context gathered: 2026-04-22*
