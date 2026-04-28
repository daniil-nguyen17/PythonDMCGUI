#!/usr/bin/env bash
# Binh An HMI — Raspberry Pi OS Bookworm installer
#
# Usage:   sudo bash install.sh
# Target:  Raspberry Pi OS Bookworm (aarch64 / 64-bit)
# Purpose: Transforms a fresh Pi OS SD card into a working HMI workstation.
#
# Step order (locked decision):
#   1.  Force X11 (Kivy has no Wayland support)
#   2.  Disable screen blanking (always-on HMI)
#   3.  Enable SSH
#   4.  apt dependencies (base + aarch64 build toolchain for Kivy source build)
#   5.  Galil gclib system library (offline .deb install — no internet needed)
#   6.  Static IP for controller network (100.100.100.0/24 on eth0)
#   7.  Copy app to /opt/binh-an-hmi/
#   8.  Create Python venv
#   9.  pip install requirements-pi.txt
#   10. Desktop shortcuts (with PYTHONPATH so python -m dmccodegui works)
#   11. Summary and reboot countdown
#
# Idempotent: safe to re-run after partial failure.

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INSTALL_DIR="/opt/binh-an-hmi"
VENV_DIR="$INSTALL_DIR/venv"
LOG_FILE="/var/log/binh-an-hmi-install.log"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTROLLER_SUBNET="100.100.100"
PI_STATIC_IP="${CONTROLLER_SUBNET}.10"

# ---------------------------------------------------------------------------
# Root check
# ---------------------------------------------------------------------------

if [[ "$EUID" -ne 0 ]]; then
    echo "Please run with sudo: sudo bash $0"
    exit 1
fi

# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------

log() {
    echo "==> $*" | tee -a "$LOG_FILE"
}

# Ensure log file is writable
touch "$LOG_FILE" 2>/dev/null || true

log "=========================================="
log "  Binh An HMI — Pi Installer"
log "  $(date)"
log "=========================================="

# ---------------------------------------------------------------------------
# Architecture detection
# ---------------------------------------------------------------------------

ARCH="$(uname -m)"
log "Detected architecture: $ARCH"
if [[ "$ARCH" != "aarch64" ]]; then
    log ""
    log "WARNING: This installer targets aarch64 (64-bit Pi OS)."
    log "WARNING: Detected $ARCH — gclib and build toolchain may not work."
    log "WARNING: Reflash with 64-bit Pi OS Bookworm for best results."
    log ""
fi

# ---------------------------------------------------------------------------
# STEP 1: Force X11 (must be first — Kivy has no Wayland support)
# ---------------------------------------------------------------------------

log "Forcing X11 session (Kivy requires X11, Wayland not supported) ..."
raspi-config nonint do_wayland W1

# ---------------------------------------------------------------------------
# STEP 2: Disable screen blanking (always-on HMI display)
# ---------------------------------------------------------------------------

log "Disabling screen blanking (always-on HMI) ..."
raspi-config nonint do_blanking 1

# ---------------------------------------------------------------------------
# STEP 3: Enable SSH
# ---------------------------------------------------------------------------

log "Ensuring SSH is enabled ..."
systemctl enable ssh
systemctl start ssh

# ---------------------------------------------------------------------------
# STEP 4: apt dependencies
#   Base: python3, pip, venv
#   Build: build-essential, cmake, pkg-config (Kivy compile from source on aarch64)
#   SDL2: required headers for Kivy window backend on Pi
#   OpenGL: Mesa EGL/GLES2 headers (Kivy KivyWindow uses EGL)
#   GStreamer: video/audio backend for Kivy
# ---------------------------------------------------------------------------

log "Installing apt dependencies ..."
apt-get update -qq 2>&1 | tee -a "$LOG_FILE"
apt-get install -y \
    python3 python3-pip python3-venv \
    build-essential cmake pkg-config \
    libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
    libgl1-mesa-dev libgles2-mesa-dev libegl1-mesa-dev \
    libmtdev-dev libxrender-dev \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    libgstreamer1.0-dev \
    2>&1 | tee -a "$LOG_FILE"

# ---------------------------------------------------------------------------
# STEP 5: Galil gclib system library (offline install from vendor .debs)
#
# The vendor/ directory should contain pre-downloaded .deb files:
#   - galil-release_1_all.deb  (apt repo bootstrap)
#   - gclib_*.deb              (the actual library)
#   - gcapsd_*.deb             (discovery service)
#
# If vendor .debs for gclib/gcapsd exist, install directly (no internet needed).
# Otherwise fall back to the apt repo method with [trusted=yes] to work around
# Galil's SHA1 GPG key rejection on modern Pi OS.
# ---------------------------------------------------------------------------

log "Installing Galil gclib system library ..."
if dpkg -l gclib 2>/dev/null | grep -q "^ii"; then
    log "  gclib already installed — skipping"
else
    GCLIB_DEB=$(find "$SCRIPT_DIR/vendor" -maxdepth 1 -name 'gclib_*.deb' 2>/dev/null | head -1)
    GCAPSD_DEB=$(find "$SCRIPT_DIR/vendor" -maxdepth 1 -name 'gcapsd_*.deb' 2>/dev/null | head -1)

    if [[ -n "$GCLIB_DEB" && -n "$GCAPSD_DEB" ]]; then
        log "  Installing gclib from vendor .deb files (offline) ..."
        dpkg -i "$GCLIB_DEB" 2>&1 | tee -a "$LOG_FILE"
        dpkg -i "$GCAPSD_DEB" 2>&1 | tee -a "$LOG_FILE"
        apt-get install -f -y 2>&1 | tee -a "$LOG_FILE"
    else
        log "  Vendor .deb files not found — falling back to Galil apt repo ..."
        if [[ -f "$SCRIPT_DIR/vendor/galil-release_1_all.deb" ]]; then
            dpkg -i "$SCRIPT_DIR/vendor/galil-release_1_all.deb" 2>&1 | tee -a "$LOG_FILE"
        else
            log "  Downloading Galil apt repo bootstrap ..."
            wget -q https://www.galil.com/sw/pub/apt/all/galil-release_1_all.deb \
                -O /tmp/galil-release_1_all.deb 2>&1 | tee -a "$LOG_FILE"
            dpkg -i /tmp/galil-release_1_all.deb 2>&1 | tee -a "$LOG_FILE"
        fi
        # Fix Galil apt source: add arm64 arch and trusted=yes (their GPG key
        # uses SHA1 which modern Pi OS rejects)
        for f in /etc/apt/sources.list.d/galil*.list /etc/apt/sources.list.d/galil*.sources; do
            [[ -f "$f" ]] && rm -f "$f"
        done
        echo 'deb [arch=arm64 trusted=yes] https://www.galil.com/sw/pub/apt / ' \
            > /etc/apt/sources.list.d/galil.list
        apt-get update -qq 2>&1 | tee -a "$LOG_FILE"
        apt-get install -y gclib gcapsd 2>&1 | tee -a "$LOG_FILE"
    fi
fi

# ---------------------------------------------------------------------------
# STEP 6: Static IP for controller network
#
# The Galil controller lives at 100.100.100.2. The Pi needs a static IP on
# the same subnet on eth0. This persists across reboots via NetworkManager
# connection profile.
# ---------------------------------------------------------------------------

log "Configuring static IP ${PI_STATIC_IP}/24 on eth0 for controller network ..."

CONN_NAME="galil-controller"
if nmcli -t -f NAME connection show 2>/dev/null | grep -q "^${CONN_NAME}$"; then
    log "  NetworkManager profile '${CONN_NAME}' already exists — updating ..."
    nmcli connection modify "$CONN_NAME" \
        ipv4.addresses "${PI_STATIC_IP}/24" \
        ipv4.method manual \
        connection.autoconnect yes \
        2>&1 | tee -a "$LOG_FILE"
else
    log "  Creating NetworkManager profile '${CONN_NAME}' ..."
    nmcli connection add \
        type ethernet \
        con-name "$CONN_NAME" \
        ifname eth0 \
        ipv4.addresses "${PI_STATIC_IP}/24" \
        ipv4.method manual \
        connection.autoconnect yes \
        2>&1 | tee -a "$LOG_FILE"
fi
nmcli connection up "$CONN_NAME" 2>&1 | tee -a "$LOG_FILE" || true

# ---------------------------------------------------------------------------
# STEP 7: Copy app to /opt/binh-an-hmi/
# ---------------------------------------------------------------------------

log "Installing app to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"
rsync -a --delete "$SCRIPT_DIR/../../" "$INSTALL_DIR/" \
    --exclude='.git' \
    --exclude='deploy/' \
    --exclude='dist/' \
    --exclude='build/' \
    --exclude='.planning/' \
    --exclude='tests/' \
    --exclude='__pycache__' \
    --exclude='.claude/' \
    --exclude='*.md' \
    --exclude='*.xlsx' \
    --exclude='*.dmc' \
    --exclude='pyproject.toml' \
    2>&1 | tee -a "$LOG_FILE"

# Copy deploy/pi assets that the app needs at runtime
mkdir -p "$INSTALL_DIR/deploy/pi"
cp -r "$SCRIPT_DIR/"* "$INSTALL_DIR/deploy/pi/"

# ---------------------------------------------------------------------------
# STEP 8: Create Python venv (idempotent)
# ---------------------------------------------------------------------------

if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating Python venv at $VENV_DIR ..."
    python3 -m venv "$VENV_DIR" 2>&1 | tee -a "$LOG_FILE"
else
    log "Venv already exists at $VENV_DIR — skipping creation"
fi

# ---------------------------------------------------------------------------
# STEP 9: pip install requirements-pi.txt
# ---------------------------------------------------------------------------

log "Installing Python dependencies (this may take 20-40 minutes on 64-bit Pi OS) ..."
"$VENV_DIR/bin/pip" install --upgrade pip 2>&1 | tee -a "$LOG_FILE"
"$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/deploy/pi/requirements-pi.txt" \
    2>&1 | tee -a "$LOG_FILE"

# ---------------------------------------------------------------------------
# STEP 10: Desktop shortcuts
# ---------------------------------------------------------------------------

log "Creating desktop shortcuts ..."
cp "$SCRIPT_DIR/binh-an-hmi.png" "$INSTALL_DIR/binh-an-hmi.png"

# Generate desktop file with correct PYTHONPATH
cat > /tmp/binh-an-hmi.desktop <<'DESKTOP'
[Desktop Entry]
Version=1.0
Type=Application
Name=Binh An HMI
Comment=Binh An grinding controller HMI
Exec=env PYTHONPATH=/opt/binh-an-hmi/src /opt/binh-an-hmi/venv/bin/python3 -m dmccodegui
Icon=/opt/binh-an-hmi/binh-an-hmi.png
Terminal=false
Categories=Utility;
StartupNotify=false
DESKTOP

cp /tmp/binh-an-hmi.desktop /usr/share/applications/binh-an-hmi.desktop

REAL_USER="${SUDO_USER:-pi}"
REAL_HOME="$(getent passwd "$REAL_USER" | cut -d: -f6)"
mkdir -p "$REAL_HOME/Desktop"
cp /tmp/binh-an-hmi.desktop "$REAL_HOME/Desktop/binh-an-hmi.desktop"
chmod +x "$REAL_HOME/Desktop/binh-an-hmi.desktop"
gio set "$REAL_HOME/Desktop/binh-an-hmi.desktop" metadata::trusted true 2>/dev/null || true
chown "$REAL_USER:$REAL_USER" "$REAL_HOME/Desktop/binh-an-hmi.desktop"

rm -f /tmp/binh-an-hmi.desktop

# ---------------------------------------------------------------------------
# STEP 11: Summary and reboot countdown
# ---------------------------------------------------------------------------

log ""
log "============================================"
log "  Installation complete!"
log "  App:        $INSTALL_DIR"
log "  Venv:       $VENV_DIR"
log "  Data:       ~/.binh-an-hmi/ (created on first launch)"
log "  Log:        $LOG_FILE"
log "  Static IP:  ${PI_STATIC_IP} on eth0"
log "  Controller: ${CONTROLLER_SUBNET}.2 (expected)"
log "============================================"
log ""
log "Rebooting in 10 seconds (Ctrl+C to cancel) ..."
for i in $(seq 10 -1 1); do printf "\r  %ds " "$i"; sleep 1; done
echo ""
reboot
