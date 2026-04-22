# Phase 26: Pi OS Preparation and Install Script - Research

**Researched:** 2026-04-22
**Domain:** Raspberry Pi OS Bookworm, Bash install scripts, Kivy ARM deployment, Galil gclib Linux packaging
**Confidence:** MEDIUM-HIGH (most findings verified against official sources; gclib Python wheel on Linux ARM confirmed as py3-none-any wrapping a system .so)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Phase 26 installs as a **normal desktop app with icon**, not a locked-down kiosk
- install.sh is **idempotent** (checks before acting), **fail-fast** (`set -e`), **self-elevating** (checks for root)
- Output: step banners + summary; pip/apt output goes to log file
- **Reboot:** auto-reboots with 10-second countdown after install completes (Ctrl+C to cancel)
- gclib .deb installed from vendored file in `deploy/pi/vendor/` via `dpkg -i`
- Screen blanking disabled (DPMS off) — industrial HMI stays always-on
- SSH ensured enabled and running
- **App install path:** `/opt/binh-an-hmi/` owned by root
- **Venv:** inside `/opt/binh-an-hmi/venv/`
- **Mutable data:** `~/.binh-an-hmi/` (users.json, settings.json)
- **Desktop shortcut:** .desktop in `~/Desktop/` AND `/usr/share/applications/`
- `deploy/pi/install.sh`, `deploy/pi/vendor/gclib-arm.deb`, `deploy/pi/binh-an-hmi.png`, `deploy/pi/requirements-pi.txt`
- `_get_data_dir()` in `main.py` needs new Linux branch returning `~/.binh-an-hmi/`
- Use Pi OS Bookworm system Python (3.11) as venv base
- If `kivy_matplotlib_widget` has no ARM wheel, build from source (--no-binary, add build-essential + cmake apt deps)
- Install step order: X11 → apt → gclib → venv → pip

### Claude's Discretion
- Exact install.sh step ordering beyond the established X11 → apt → gclib → venv → pip flow
- .desktop file contents and icon sizing
- Specific apt dependency list for Kivy/matplotlib on ARM
- Screen blanking disable method (xset, lightdm config, or xorg.conf)
- requirements-pi.txt exact version pins (research will inform these)
- Log file location for install.sh output

### Deferred Ideas (OUT OF SCOPE)
- Kiosk lockdown (Openbox shortcut blocking, taskbar suppression, dedicated kiosk user, boot direct to app)
- systemd crash recovery (Restart=on-failure, RestartSec=3, StartLimitBurst=5)
- Hardware watchdog (WatchdogSec=30 with sdnotify heartbeat in Kivy event loop)
- PI-02, PI-03, PI-07 requirements
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PI-01 | install.sh creates a Python venv with all dependencies (Kivy, matplotlib, gclib, kivy_matplotlib_widget) on Pi OS Bookworm | Confirmed: python3.11-venv apt package, piwheels pre-configured, Kivy wheel available on PiWheels for armhf |
| PI-04 | install.sh forces X11 session (disables Wayland) as its first operation — Kivy cannot run on Wayland | Confirmed: `raspi-config nonint do_wayland W1` is the exact noninteractive command |
| PI-05 | A single install.sh script handles all Pi setup: apt deps, Galil .deb, venv creation, pip install, kiosk config (partial — kiosk deferred) | Confirmed: all non-kiosk steps are researched and viable |
</phase_requirements>

---

## Summary

Phase 26 is a bash install script (`install.sh`) that sets up the Binh An HMI as a normal desktop app on a fresh Raspberry Pi OS Bookworm SD card. The three non-deferred requirements (PI-01, PI-04, PI-05) are all technically achievable with well-understood tooling.

The single largest risk is the **32-bit vs 64-bit OS decision**. PiWheels (pre-configured at `/etc/pip.conf` on Pi OS) only serves armhf (32-bit) wheels — it does not build aarch64 wheels. On a 64-bit Pi OS install, `pip install kivy` will fall back to building Kivy from source, which takes 20-40 minutes and requires a full compiler toolchain. The install script should either: (a) target 32-bit Pi OS explicitly, or (b) detect the architecture and print a clear warning when running on 64-bit. Since the CONTEXT.md says "Pi 4 or 5" without specifying bitness, this is a discretion decision the planner should note.

The gclib Python package (`gclib-1.0.1-py3-none-any.whl`) is a pure-Python ctypes wrapper — the wheel itself has no native code. It loads the system `libgclib.so` that is installed by `sudo apt install gclib`. This means gclib in the venv depends on the system apt package being installed first (which the locked decision already mandates). The vendored `.deb` approach (locked decision) refers to the Galil APT repository release `.deb` (`galil-release_1_all.deb`) which registers Galil's apt repo, followed by `apt install gclib`.

**Primary recommendation:** Target 32-bit Pi OS (armhf) explicitly. Add architecture detection at the top of install.sh and abort with a clear message if running on aarch64, until a 64-bit pip-wheel path is tested.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Kivy | 2.3.1 | GUI framework | Same as Windows; pre-built wheel on PiWheels for armhf/cp311 |
| matplotlib | 3.9.x+ | Plotting | Pre-built on PiWheels for armhf/cp311 |
| kivy-matplotlib-widget | 0.15.0+ | Kivy matplotlib integration | `py3-none-any` wheel — pure Python, no native build needed, available on PiWheels |
| gclib | 1.0.1 | Galil controller API (Python wrapper) | `py3-none-any` wheel from Galil's own URL; wraps system `libgclib.so` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python3.11-venv | system | venv creation capability | Must apt-install on Lite images — not pre-installed |
| python3-pip | system | Bootstrap pip in venv | Must apt-install on Lite images |
| libgl1-mesa-glx | system | OpenGL runtime for Kivy | Required for SDL2 window rendering |
| libgles2-mesa | system | OpenGL ES for Pi GPU | Kivy SDL2 runtime dep |
| libegl1-mesa | system | EGL for SDL2 OpenGL context | Kivy SDL2 runtime dep |
| libmtdev1 | system | Multitouch device input | Kivy input runtime dep |

### Galil gclib System Packages (via Galil's apt repo)
| Package | Purpose |
|---------|---------|
| gclib | Native `libgclib.so` C library + shared objects |
| gcapsd | GCaps daemon — controller discovery service |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Galil apt repo (galil-release.deb → apt install gclib) | Vendored gclib .deb file | Vendoring the galil-release.deb and then running apt is actually what the locked decision means — keeps installer offline-capable |
| 32-bit Pi OS (armhf) | 64-bit Pi OS (aarch64) | 64-bit gets no PiWheels; Kivy must build from source (20-40 min). 32-bit is strongly preferred for this install script. |
| xset -dpms for screen blanking | raspi-config nonint do_blanking 1 | raspi-config method persists across reboots; xset method is session-scoped only |

**Installation (what install.sh will run):**
```bash
# Step 1: X11 (Kivy requires X11, Bookworm defaults to Wayland)
raspi-config nonint do_wayland W1

# Step 2: apt deps
apt-get update
apt-get install -y python3 python3-pip python3.11-venv \
    libgl1-mesa-glx libgles2-mesa libegl1-mesa libmtdev1 \
    libxrender1 libx11-6 libxext6

# Step 3: Galil gclib system library
dpkg -i /path/to/galil-release_1_all.deb
apt-get update
apt-get install -y gclib gcapsd

# Step 4: Venv
python3 -m venv /opt/binh-an-hmi/venv

# Step 5: pip
/opt/binh-an-hmi/venv/bin/pip install --upgrade pip
/opt/binh-an-hmi/venv/bin/pip install -r /opt/binh-an-hmi/requirements-pi.txt
```

---

## Architecture Patterns

### Recommended Project Structure
```
deploy/pi/
├── install.sh            # main install script
├── requirements-pi.txt   # pinned pip versions for ARM
├── binh-an-hmi.png       # 256x256 icon for .desktop file
├── binh-an-hmi.desktop   # template .desktop entry
└── vendor/
    └── galil-release_1_all.deb   # Galil apt repo registration package
```

### Pattern 1: Idempotent Bash Install Script with set -e
**What:** Each operation is guarded by a check before executing. The whole script uses `set -e` so any unguarded failure stops execution with a clear traceback.
**When to use:** Always — makes the script safe to re-run after partial failure or upgrade.
**Example:**
```bash
#!/usr/bin/env bash
set -euo pipefail

# Self-elevating root check
if [[ $EUID -ne 0 ]]; then
    echo "Please run with sudo: sudo bash install.sh" >&2
    exit 1
fi

INSTALL_DIR="/opt/binh-an-hmi"
VENV_DIR="$INSTALL_DIR/venv"
LOG_FILE="/var/log/binh-an-hmi-install.log"

log() { echo "==> $*" | tee -a "$LOG_FILE"; }

# Idempotent venv creation
if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating Python venv at $VENV_DIR ..."
    python3 -m venv "$VENV_DIR" 2>&1 | tee -a "$LOG_FILE"
else
    log "Venv already exists — skipping creation"
fi
```

### Pattern 2: gclib Dependency Chain
**What:** gclib Python wheel is a ctypes wrapper that dlopen()s `libgclib.so` at runtime. The .so is installed by `apt install gclib`. The Python pip install must happen AFTER the apt step, or the venv will import but immediately fail on first controller call.
**When to use:** Always in this install sequence.
**Order:** `dpkg -i galil-release_1_all.deb` → `apt install gclib gcapsd` → `pip install gclib wheel URL`

### Pattern 3: raspi-config nonint for X11 Switch
**What:** raspi-config supports a noninteractive mode for scripting. The Wayland/X11 switch is handled by `do_wayland` with argument `W1` (X11/Openbox) or `W2` (Labwc/Wayland).
**When to use:** First operation in install.sh per locked decision.
**Example:**
```bash
log "Forcing X11 session (Kivy requires X11, Bookworm defaults to Wayland) ..."
raspi-config nonint do_wayland W1
```
Note: A reboot is required before the X11 setting takes effect. Since install.sh ends with a reboot, the first-boot after install will be in X11 mode.

### Pattern 4: Permanent Screen Blanking Disable
**What:** For permanent (reboot-persistent) screen blanking disable on Bookworm X11, use `raspi-config nonint do_blanking 1` (argument `1` = disable blanking). Session-scoped `xset` commands are not sufficient — they require a running X session and don't survive reboot.
**When to use:** During install.sh to configure always-on HMI.
**Example:**
```bash
log "Disabling screen blanking (always-on HMI) ..."
raspi-config nonint do_blanking 1
```

### Pattern 5: SSH Enable (Bookworm)
**What:** On Bookworm, enable SSH via systemctl (not the legacy `/boot/ssh` file trick which no longer works).
**Example:**
```bash
log "Ensuring SSH is enabled ..."
systemctl enable ssh
systemctl start ssh
```

### Pattern 6: Freedesktop .desktop Entry
**What:** Standard XDG desktop entry file for application menu and desktop shortcut.
**When to use:** Two copies — `~/Desktop/binh-an-hmi.desktop` and `/usr/share/applications/binh-an-hmi.desktop`.
**Example:**
```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=Binh An HMI
Comment=Binh An grinding controller HMI
Exec=/opt/binh-an-hmi/venv/bin/python -m dmccodegui
Icon=/opt/binh-an-hmi/binh-an-hmi.png
Terminal=false
Categories=Utility;
StartupNotify=false
```
Note: Icon recommended size is 256x256 PNG. For LXDE-pi desktop (used in X11 mode), `.desktop` files in `~/Desktop/` must be trusted before they'll launch — double-click → "Execute" or right-click → "Allow Launching". `/usr/share/applications/` entries appear in the app menu automatically.

### Pattern 7: _get_data_dir() Linux Branch
**What:** Extend the existing frozen/dev detection with a `sys.platform == 'linux'` check.
**When to use:** In `main.py`, extends the existing pattern from Phase 24.
**Example:**
```python
def _get_data_dir() -> str:
    if getattr(sys, 'frozen', False):
        # Windows frozen (PyInstaller)
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        data_dir = os.path.join(appdata, 'BinhAnHMI')
    elif sys.platform == 'linux':
        # Raspberry Pi / Linux desktop
        data_dir = os.path.join(os.path.expanduser('~'), '.binh-an-hmi')
    else:
        # Dev mode (Windows, non-frozen)
        data_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'auth'
        )
    os.makedirs(data_dir, exist_ok=True)
    return data_dir
```

### Anti-Patterns to Avoid
- **`pip install` as root outside venv:** Bookworm enforces PEP 668 — `pip install` system-wide is blocked. Always use `/opt/binh-an-hmi/venv/bin/pip`.
- **`sudo pip` for venv packages:** After creating the venv as root (during sudo install.sh), use `$VENV_DIR/bin/pip install` directly — no sudo needed since root created the venv.
- **xset for permanent blanking disable:** xset is session-scoped only. Use `raspi-config nonint do_blanking 1` during install.
- **Assuming 64-bit Pi OS:** PiWheels does not serve aarch64 wheels. Kivy on 64-bit requires compiling from source. Always check architecture in install.sh.
- **Omitting `python3.11-venv` from apt list:** The Lite image does not include it. `python3 -m venv` fails silently or with a confusing error without it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Noninteractive X11 switching | Editing `/etc/lightdm/lightdm.conf` manually with sed | `raspi-config nonint do_wayland W1` | raspi-config handles all Pi model variants, LightDM config variants, and AccountsService updates atomically |
| Noninteractive blanking disable | xset commands in ~/.bashrc | `raspi-config nonint do_blanking 1` | Persists across reboots; raspi-config writes the correct config file location |
| Galil Python bindings | Custom ctypes wrapper | `pip install https://www.galil.com/sw/pub/python/gclib-1.0.1-py3-none-any.whl` | Official Galil-maintained wrapper; py3-none-any works on any arch |
| SSH enable | Editing /etc/ssh/sshd_config | `systemctl enable ssh && systemctl start ssh` | Correct for Bookworm; legacy `/boot/ssh` file method no longer works |
| .desktop file trust | Custom autorun script | Standard LXDE "Allow Launching" mechanism | LXDE-pi handles this via GUI; install.sh can copy the file, user trusts on first launch |

**Key insight:** raspi-config's noninteractive mode handles the two hardest scripting problems (Wayland switch and blanking) atomically and correctly across Pi model variants. Never manually edit the underlying config files — raspi-config knows which files to update per model.

---

## Common Pitfalls

### Pitfall 1: Wrong Architecture — 64-bit Pi OS
**What goes wrong:** `pip install kivy` on aarch64 Bookworm finds no PiWheels wheel, attempts to compile SDL2 from source, takes 30+ minutes, and may fail if build deps are missing.
**Why it happens:** PiWheels only serves armhf (32-bit) wheels. 64-bit Pi OS is the default recommended by the Pi imager for Pi 4/5.
**How to avoid:** Add an architecture check at the top of install.sh:
```bash
ARCH=$(uname -m)
if [[ "$ARCH" != "armv7l" && "$ARCH" != "armv6l" ]]; then
    echo "ERROR: This installer requires 32-bit Raspberry Pi OS (armhf)." >&2
    echo "Detected: $ARCH. Please flash a 32-bit image." >&2
    exit 1
fi
```
**Warning signs:** `pip install kivy` output shows "Building wheel for kivy" with CMake/C compilation output.

### Pitfall 2: Wayland Active at App Launch
**What goes wrong:** App is launched (from desktop shortcut or terminal) while Wayland is still the active session. Kivy/SDL2 cannot connect to Wayland and exits silently or with `SDL_Error: Couldn't connect to display`.
**Why it happens:** `raspi-config nonint do_wayland W1` requires a reboot to take effect. If the user launches the app before rebooting, Wayland is still active.
**How to avoid:** install.sh must reboot after completion. The 10-second countdown reboot (locked decision) handles this.
**Warning signs:** App exits immediately after launch with no error dialog.

### Pitfall 3: python3.11-venv Missing
**What goes wrong:** `python3 -m venv /opt/binh-an-hmi/venv` fails with: `Error: ensurepip is not available. python3-venv is not installed.`
**Why it happens:** Raspberry Pi OS Lite does not include `python3.11-venv` by default.
**How to avoid:** Include `python3.11-venv` in the apt dependencies list.
**Warning signs:** `python3 -m venv` command fails even though python3 is installed.

### Pitfall 4: gclib .so Not Found at Runtime
**What goes wrong:** App imports `gclib` from the venv without error, but the first `g.GOpen()` call fails with a ctypes `OSError: libgclib.so.X: cannot open shared object file`.
**Why it happens:** The gclib pip wheel is `py3-none-any` (pure Python ctypes wrapper). It dlopen()s the system `.so` at runtime. If the apt step was skipped or failed, the `.so` is absent.
**How to avoid:** install.sh must run `apt install gclib` before the `pip install` step. The dpkg step only registers the apt repo; the actual library comes from `apt install gclib`.
**Warning signs:** App starts but controller connection immediately fails.

### Pitfall 5: Desktop Shortcut Not Executable (Trust Issue)
**What goes wrong:** Operator double-clicks the `.desktop` file on the LXDE-pi desktop and sees a dialog "This file does not have execute permission" or the file opens in a text editor.
**Why it happens:** LXDE-pi marks `.desktop` files as untrusted until the user explicitly allows launching.
**How to avoid:** install.sh can set the trusted bit on the .desktop file using `gio set` or `chmod +x`. Alternatively, document that the user must right-click → "Allow Launching" on first use. For the `/usr/share/applications/` entry, this is not an issue — it appears in the app menu directly.
```bash
# Set the desktop file as trusted/executable
chmod +x ~/Desktop/binh-an-hmi.desktop
gio set ~/Desktop/binh-an-hmi.desktop metadata::trusted true 2>/dev/null || true
```

### Pitfall 6: Screen Blanking Disable via xset Only
**What goes wrong:** install.sh runs `xset -dpms; xset s off` and the screen still blanks after reboot.
**Why it happens:** `xset` modifies the current X session's settings only. These settings are not persisted across reboots or session restarts.
**How to avoid:** Use `raspi-config nonint do_blanking 1` which writes to the Pi's persistent configuration.

### Pitfall 7: deploy/pi/vendor/ .deb Is the Wrong File
**What goes wrong:** The vendored `.deb` contains the gclib C library itself, but the Galil distribution model uses a "release" `.deb` that only configures the apt repo — the actual gclib packages are then `apt install`ed.
**Why it happens:** Galil's distribution model is a two-step: (1) register apt repo, (2) `apt install gclib`. The vendored file should be `galil-release_1_all.deb`, not a gclib binary `.deb`.
**How to avoid:** Vendor `galil-release_1_all.deb` (the repo registration package from `https://www.galil.com/sw/pub/apt/all/galil-release_1_all.deb`). After `dpkg -i galil-release_1_all.deb`, run `apt update && apt install gclib gcapsd`.
**Note:** This requires an internet connection during install for the `apt install gclib` step. If fully offline install is needed, the individual gclib `.deb` packages from Galil's apt mirror would need to be vendored separately — this is an open question flagged below.

---

## Code Examples

### install.sh Skeleton
```bash
#!/usr/bin/env bash
# deploy/pi/install.sh — Binh An HMI installer for Raspberry Pi OS Bookworm
set -euo pipefail

# --- Constants ---
INSTALL_DIR="/opt/binh-an-hmi"
VENV_DIR="$INSTALL_DIR/venv"
DATA_DIR_TEMPLATE="~/.binh-an-hmi"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/binh-an-hmi-install.log"

# --- Root check ---
if [[ $EUID -ne 0 ]]; then
    echo "Please run with sudo: sudo bash $0" >&2
    exit 1
fi

# --- Architecture check ---
ARCH=$(uname -m)
if [[ "$ARCH" != "armv7l" && "$ARCH" != "armv6l" ]]; then
    echo "ERROR: 32-bit Raspberry Pi OS required. Detected: $ARCH" >&2
    exit 1
fi

log() { echo "==> $*" | tee -a "$LOG_FILE"; }

# --- Step 1: Force X11 (Kivy requirement) ---
log "Configuring X11 session (replaces Wayland default) ..."
raspi-config nonint do_wayland W1

# --- Step 2: Disable screen blanking ---
log "Disabling screen blanking ..."
raspi-config nonint do_blanking 1

# --- Step 3: Enable SSH ---
log "Ensuring SSH is enabled ..."
systemctl enable ssh
systemctl start ssh

# --- Step 4: apt dependencies ---
log "Installing apt dependencies ..."
apt-get update -qq 2>&1 | tee -a "$LOG_FILE"
apt-get install -y \
    python3 python3-pip python3.11-venv \
    libgl1-mesa-glx libgles2-mesa libegl1-mesa libmtdev1 \
    libxrender1 \
    2>&1 | tee -a "$LOG_FILE"

# --- Step 5: Galil gclib system library ---
log "Installing Galil gclib ..."
if ! dpkg -l gclib &>/dev/null; then
    dpkg -i "$SCRIPT_DIR/vendor/galil-release_1_all.deb" 2>&1 | tee -a "$LOG_FILE"
    apt-get update -qq 2>&1 | tee -a "$LOG_FILE"
    apt-get install -y gclib gcapsd 2>&1 | tee -a "$LOG_FILE"
else
    log "gclib already installed — skipping"
fi

# --- Step 6: Copy app to /opt ---
log "Installing app to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"
rsync -a --delete "$SCRIPT_DIR/../../" "$INSTALL_DIR/" \
    --exclude='.git' --exclude='deploy/' --exclude='dist/' --exclude='build/' \
    --exclude='.planning/' --exclude='tests/' \
    2>&1 | tee -a "$LOG_FILE"

# --- Step 7: Create venv ---
if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating Python venv ..."
    python3 -m venv "$VENV_DIR" 2>&1 | tee -a "$LOG_FILE"
else
    log "Venv exists — skipping creation"
fi

# --- Step 8: pip install ---
log "Installing Python dependencies ..."
"$VENV_DIR/bin/pip" install --upgrade pip 2>&1 | tee -a "$LOG_FILE"
"$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/deploy/pi/requirements-pi.txt" \
    2>&1 | tee -a "$LOG_FILE"

# --- Step 9: Desktop shortcuts ---
log "Creating desktop shortcuts ..."
cp "$SCRIPT_DIR/binh-an-hmi.desktop" /usr/share/applications/binh-an-hmi.desktop
cp "$SCRIPT_DIR/binh-an-hmi.png" "$INSTALL_DIR/binh-an-hmi.png"
REAL_USER="${SUDO_USER:-pi}"
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
cp "$SCRIPT_DIR/binh-an-hmi.desktop" "$REAL_HOME/Desktop/binh-an-hmi.desktop"
chmod +x "$REAL_HOME/Desktop/binh-an-hmi.desktop"
gio set "$REAL_HOME/Desktop/binh-an-hmi.desktop" metadata::trusted true 2>/dev/null || true
chown "$REAL_USER:$REAL_USER" "$REAL_HOME/Desktop/binh-an-hmi.desktop"

# --- Reboot countdown ---
log "Installation complete! Rebooting in 10 seconds (Ctrl+C to cancel) ..."
for i in $(seq 10 -1 1); do printf "\r  %ds " "$i"; sleep 1; done
echo ""
reboot
```

### requirements-pi.txt (Pinned Versions — Suggested Starting Point)
```text
# Source: https://pypi.org/project/kivy/ and https://www.piwheels.org/
# Pin to versions confirmed available on PiWheels for cp311-armhf-linux
kivy==2.3.1
matplotlib==3.9.4
kivy-matplotlib-widget==0.15.0
# Galil gclib Python wrapper — wraps system libgclib.so installed by apt
# Note: must install gclib apt package first
gclib @ https://www.galil.com/sw/pub/python/gclib-1.0.1-py3-none-any.whl
```

### binh-an-hmi.desktop
```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=Binh An HMI
Comment=Binh An grinding controller HMI
Exec=/opt/binh-an-hmi/venv/bin/python -m dmccodegui
Icon=/opt/binh-an-hmi/binh-an-hmi.png
Terminal=false
Categories=Utility;
StartupNotify=false
```

### _get_data_dir() Extended for Linux
```python
# Source: main.py (extend existing function at line 15)
def _get_data_dir() -> str:
    """Return writable directory for mutable data files.

    Frozen (PyInstaller onedir, Windows): %APPDATA%\\BinhAnHMI\\
    Linux (Pi, dev on Linux):             ~/.binh-an-hmi/
    Dev (Windows, non-frozen):            src/dmccodegui/auth/
    """
    if getattr(sys, 'frozen', False):
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        data_dir = os.path.join(appdata, 'BinhAnHMI')
    elif sys.platform == 'linux':
        data_dir = os.path.join(os.path.expanduser('~'), '.binh-an-hmi')
    else:
        data_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'auth'
        )
    os.makedirs(data_dir, exist_ok=True)
    return data_dir
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `/boot/ssh` file for headless SSH enable | `systemctl enable ssh` | Bookworm (2023) | Legacy method silently ignored |
| `pip install` system-wide | Must use venv (PEP 668) | Python 3.11 + Bookworm | `pip install` outside venv is blocked by externally-managed-environment error |
| egl_rpi window provider for Kivy | SDL2 window provider | Kivy 2.x on Bookworm | egl_rpi only on Buster 32-bit; Bookworm uses SDL2 backend |
| X11 default | Wayland default (labwc) | Bookworm (Oct 2023) | All Kivy/SDL2 apps must force X11 until Wayland support lands in Kivy |
| PiWheels 32-bit only | PiWheels 32-bit only (unchanged) | Not yet changed | 64-bit Pi OS users cannot use PiWheels; Kivy must compile from source |

**Deprecated/outdated:**
- egl_rpi Kivy provider: Only works on Buster 32-bit, removed/unsupported on Bookworm
- `/boot/ssh` headless SSH file: No longer works in Bookworm
- `pip install --break-system-packages`: Works but wrong — use venv instead

---

## Open Questions

1. **Online vs Offline gclib Install**
   - What we know: Galil's distribution model uses `galil-release_1_all.deb` to register their apt repo, then `apt install gclib` pulls from the internet.
   - What's unclear: Can the individual gclib `.deb` binary packages be downloaded and vendored for a fully offline install? The install script currently requires internet access for the `apt install gclib` step.
   - Recommendation: Accept online install for now (SSH is available for maintenance anyway). If offline install becomes a requirement, download the gclib binary `.deb` from Galil's apt mirror during build and vendor it alongside `galil-release_1_all.deb`.

2. **32-bit vs 64-bit Pi OS Targeting**
   - What we know: PiWheels only serves armhf (32-bit) wheels. Kivy 2.3.1 has a pre-built wheel for cp311-armhf-linux on PiWheels. On 64-bit (aarch64), Kivy must compile from source.
   - What's unclear: The user has not specified which bitness to target. Pi 4 and Pi 5 can run either. The Pi Imager now defaults to 64-bit for Pi 4/5.
   - Recommendation: The planner should ask the user to confirm 32-bit Pi OS, OR the architecture check in install.sh should be a warning (not abort) with a note that install will take longer.

3. **gclib Version in requirements-pi.txt**
   - What we know: The environment.yml uses `gclib-1.0.0-py3-none-any.whl` (the URL in the project). Galil's docs show `gclib-1.0.1-py3-none-any.whl` as the current version.
   - What's unclear: Whether 1.0.0 and 1.0.1 have API differences. 1.0.0 is what the Windows version uses.
   - Recommendation: Use the same version as Windows (`gclib-1.0.0-py3-none-any.whl`) for consistency. The exact URL to confirm is `https://www.galil.com/sw/pub/python/gclib-1.0.0-py3-none-any.whl`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (from pyproject.toml dev dependencies) |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` testpaths = ["tests"] |
| Quick run command | `pytest tests/test_data_dir.py tests/test_install_pi.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PI-01 | venv created with all deps (verified via file existence) | unit | `pytest tests/test_install_pi.py::test_requirements_pi_txt_exists -x` | ❌ Wave 0 |
| PI-01 | requirements-pi.txt contains required packages | unit | `pytest tests/test_install_pi.py::test_requirements_pi_txt_contains_kivy -x` | ❌ Wave 0 |
| PI-04 | install.sh contains `do_wayland W1` as first non-comment operation | unit | `pytest tests/test_install_pi.py::test_install_sh_x11_first -x` | ❌ Wave 0 |
| PI-05 | install.sh exists and is executable | unit | `pytest tests/test_install_pi.py::test_install_sh_exists -x` | ❌ Wave 0 |
| PI-05 | install.sh contains all required sections (apt, gclib, venv, pip, desktop) | unit | `pytest tests/test_install_pi.py::test_install_sh_sections -x` | ❌ Wave 0 |
| PI-05 | install.sh contains idempotency guards (venv existence check) | unit | `pytest tests/test_install_pi.py::test_install_sh_idempotent -x` | ❌ Wave 0 |
| _get_data_dir() | Linux branch returns ~/.binh-an-hmi/ | unit | `pytest tests/test_data_dir.py::test_linux_mode_returns_home_dir -x` | ❌ Wave 0 (add to existing file) |
| deploy/pi files | binh-an-hmi.desktop exists and has required fields | unit | `pytest tests/test_install_pi.py::test_desktop_file_fields -x` | ❌ Wave 0 |

Note: The test pattern mirrors `tests/test_installer.py` (Phase 25 Windows installer tests) — content inspection of text files. No Pi hardware needed.

### Sampling Rate
- **Per task commit:** `pytest tests/test_data_dir.py tests/test_install_pi.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_install_pi.py` — covers PI-01, PI-04, PI-05 (new file, mirrors test_installer.py pattern)
- [ ] Add `test_linux_mode_returns_home_dir` to `tests/test_data_dir.py` — covers `_get_data_dir()` Linux branch

*(Framework and conftest.py already exist — no infrastructure gaps)*

---

## Sources

### Primary (HIGH confidence)
- [Galil Raspberry Pi OS Install Docs](https://www.galil.com/sw/pub/all/doc/global/install/linux/rpios/) — exact gclib apt installation steps
- [Galil gclib HTML docs](https://www.galil.com/sw/pub/all/doc/gclib/html/) — Python wheel URL `gclib-1.0.1-py3-none-any.whl`
- [Kivy 2.3.1 RPi Installation](https://kivy.org/doc/stable/installation/installation-rpi.html) — apt dependencies, PiWheels reference
- [Kivy 2.3.1 Installation Guide](https://kivy.org/doc/stable/gettingstarted/installation.html) — `pip install "kivy[base]"` command
- [PiWheels — kivy-matplotlib-widget](https://www.piwheels.org/project/kivy-matplotlib-widget/) — confirmed py3-none-any wheel, all Bookworm/cp311 builds green
- [PiWheels — matplotlib](https://www.piwheels.org/project/matplotlib/) — confirmed cp311-armhf wheels for Bookworm
- [RPi-Distro/raspi-config bookworm source](https://raw.githubusercontent.com/RPi-Distro/raspi-config/bookworm/raspi-config) — `do_wayland W1` noninteractive syntax, `do_blanking 1` syntax
- [raspi-config bookworm GitHub](https://github.com/RPi-Distro/raspi-config/blob/bookworm/raspi-config) — source of truth for noninteractive commands
- Existing `pyproject.toml` and `tests/` directory — pytest framework confirmed present

### Secondary (MEDIUM confidence)
- [PiWheels ARM64 blog](https://blog.piwheels.org/raspberry-pi-os-64-bit-aarch64/) — confirms PiWheels armhf-only, no aarch64 support
- [Bookworm feedback issue #90](https://github.com/raspberrypi/Raspberry-Pi-OS-64bit/issues/46) — confirms python3.11-venv not on Lite images
- [pimylifeup screen blanking](https://pimylifeup.com/raspberry-pi-disable-screen-blanking/) — raspi-config Display Options method for permanent blanking disable
- [gclib release notes](https://www.galil.com/sw/pub/all/rn/gclib.html) — version 2.4.1 current, Python pip packaging confirmed since 2.0.10

### Tertiary (LOW confidence — needs hardware validation)
- Architecture check syntax (`uname -m` returning `armv7l` on 32-bit Pi) — standard Linux but unverified on physical Pi
- gio set metadata::trusted behavior on current LXDE-pi — works on Bullseye, may differ on Bookworm
- Exact libgl1-mesa-glx package name on Bookworm (may be libgl1-mesa-dri or libgl1 on newer Debian)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Kivy, matplotlib, kivy-matplotlib-widget all confirmed on PiWheels for cp311/armhf; gclib pip wheel confirmed as py3-none-any from official Galil URL
- Architecture: HIGH — install.sh skeleton based on verified commands; patterns follow established project conventions
- Pitfalls: MEDIUM-HIGH — major pitfalls (64-bit, venv package, wayland timing, gclib .so chain) are well-documented; desktop trust issue is MEDIUM (forum-sourced)
- raspi-config noninteractive commands: HIGH — verified from raspi-config bookworm source code

**Research date:** 2026-04-22
**Valid until:** 2026-07-22 (90 days — Bookworm is stable; PiWheels wheel status could change)
