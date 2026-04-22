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
#   5.  Galil gclib system library
#   6.  Copy app to /opt/binh-an-hmi/
#   7.  Create Python venv
#   8.  pip install requirements-pi.txt
#   9.  Desktop shortcuts
#   10. Summary and reboot countdown
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
# Architecture detection (informational only — target is aarch64)
# ---------------------------------------------------------------------------

ARCH="$(uname -m)"
log "Detected architecture: $ARCH"
if [[ "$ARCH" == "aarch64" ]]; then
    log ""
    log "INFO: Running on aarch64 (64-bit Pi OS)."
    log "INFO: Kivy has no pre-built wheel on PiWheels for aarch64."
    log "INFO: It will compile from source — this may take 20-40 minutes."
    log "INFO: The SDL2 dev headers and build toolchain will be installed via apt."
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
# STEP 5: Galil gclib system library (idempotent)
# ---------------------------------------------------------------------------

log "Installing Galil gclib system library ..."
if ! dpkg -l gclib 2>/dev/null | grep -q "^ii"; then
    log "  Installing gclib from vendor .deb ..."
    dpkg -i "$SCRIPT_DIR/vendor/galil-release_1_all.deb" 2>&1 | tee -a "$LOG_FILE"
    apt-get update -qq 2>&1 | tee -a "$LOG_FILE"
    apt-get install -y gclib gcapsd 2>&1 | tee -a "$LOG_FILE"
else
    log "  gclib already installed — skipping"
fi

# ---------------------------------------------------------------------------
# STEP 6: Copy app to /opt/binh-an-hmi/
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
# STEP 7: Create Python venv (idempotent)
# ---------------------------------------------------------------------------

if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating Python venv at $VENV_DIR ..."
    python3 -m venv "$VENV_DIR" 2>&1 | tee -a "$LOG_FILE"
else
    log "Venv already exists at $VENV_DIR — skipping creation"
fi

# ---------------------------------------------------------------------------
# STEP 8: pip install requirements-pi.txt
# ---------------------------------------------------------------------------

log "Installing Python dependencies (this may take 20-40 minutes on 64-bit Pi OS) ..."
"$VENV_DIR/bin/pip" install --upgrade pip 2>&1 | tee -a "$LOG_FILE"
"$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/deploy/pi/requirements-pi.txt" \
    2>&1 | tee -a "$LOG_FILE"

# ---------------------------------------------------------------------------
# STEP 9: Desktop shortcuts
# ---------------------------------------------------------------------------

log "Creating desktop shortcuts ..."
cp "$SCRIPT_DIR/binh-an-hmi.png" "$INSTALL_DIR/binh-an-hmi.png"
cp "$SCRIPT_DIR/binh-an-hmi.desktop" /usr/share/applications/binh-an-hmi.desktop

REAL_USER="${SUDO_USER:-pi}"
REAL_HOME="$(getent passwd "$REAL_USER" | cut -d: -f6)"
mkdir -p "$REAL_HOME/Desktop"
cp "$SCRIPT_DIR/binh-an-hmi.desktop" "$REAL_HOME/Desktop/binh-an-hmi.desktop"
chmod +x "$REAL_HOME/Desktop/binh-an-hmi.desktop"
gio set "$REAL_HOME/Desktop/binh-an-hmi.desktop" metadata::trusted true 2>/dev/null || true
chown "$REAL_USER:$REAL_USER" "$REAL_HOME/Desktop/binh-an-hmi.desktop"

# ---------------------------------------------------------------------------
# STEP 10: Summary and reboot countdown
# ---------------------------------------------------------------------------

log ""
log "============================================"
log "  Installation complete!"
log "  App:  $INSTALL_DIR"
log "  Venv: $VENV_DIR"
log "  Data: ~/.binh-an-hmi/ (created on first launch)"
log "  Log:  $LOG_FILE"
log "============================================"
log ""
log "Rebooting in 10 seconds (Ctrl+C to cancel) ..."
for i in $(seq 10 -1 1); do printf "\r  %ds " "$i"; sleep 1; done
echo ""
reboot
