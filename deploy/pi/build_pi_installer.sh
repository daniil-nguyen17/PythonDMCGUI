#!/usr/bin/env bash
# Build a self-extracting Pi installer for Binh An HMI
#
# Usage:   bash deploy/pi/build_pi_installer.sh
# Output:  Output/BinhAnHMI_Pi_Setup.run
#
# Requires: makeself (apt-get install makeself)
#
# The resulting .run file is a single self-extracting archive that a
# technician copies to the Pi (USB or SCP) and runs:
#
#   sudo bash BinhAnHMI_Pi_Setup.run
#
# It extracts to a temp directory, runs install.sh, then cleans up.
# No folder navigation, no manual steps.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="$REPO_ROOT/Output"
STAGING_DIR="$(mktemp -d)"
INSTALLER_NAME="BinhAnHMI_Pi_Setup.run"

# ---------------------------------------------------------------------------
# Check for makeself
# ---------------------------------------------------------------------------

if ! command -v makeself &>/dev/null; then
    echo "ERROR: makeself is not installed."
    echo ""
    echo "Install it:"
    echo "  Ubuntu/Debian/Pi: sudo apt-get install makeself"
    echo "  macOS:            brew install makeself"
    echo ""
    exit 1
fi

# ---------------------------------------------------------------------------
# Stage files (same excludes as install.sh rsync)
# ---------------------------------------------------------------------------

echo "==> Staging project files ..."
rsync -a "$REPO_ROOT/" "$STAGING_DIR/" \
    --exclude='.git' \
    --exclude='dist/' \
    --exclude='build/' \
    --exclude='Output/' \
    --exclude='.planning/' \
    --exclude='tests/' \
    --exclude='__pycache__' \
    --exclude='.claude/' \
    --exclude='.agents/' \
    --exclude='*.xlsx' \
    --exclude='*.dmc'

# ---------------------------------------------------------------------------
# Create wrapper script that runs install.sh from extracted dir
# ---------------------------------------------------------------------------

cat > "$STAGING_DIR/setup.sh" <<'WRAPPER'
#!/usr/bin/env bash
# Auto-generated wrapper — runs install.sh from the extracted archive
set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
    echo "Please run with sudo: sudo bash $0"
    exit 1
fi

EXTRACT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo ""
echo "============================================"
echo "  Binh An HMI — Pi Installer"
echo "  Extracted to: $EXTRACT_DIR"
echo "============================================"
echo ""

bash "$EXTRACT_DIR/deploy/pi/install.sh"
WRAPPER
chmod +x "$STAGING_DIR/setup.sh"

# ---------------------------------------------------------------------------
# Build self-extracting archive
# ---------------------------------------------------------------------------

mkdir -p "$OUTPUT_DIR"

echo "==> Building self-extracting installer ..."
makeself \
    --gzip \
    --needroot \
    "$STAGING_DIR" \
    "$OUTPUT_DIR/$INSTALLER_NAME" \
    "Binh An HMI — Raspberry Pi Installer" \
    ./setup.sh

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

rm -rf "$STAGING_DIR"

SIZE=$(du -h "$OUTPUT_DIR/$INSTALLER_NAME" | cut -f1)
echo ""
echo "============================================"
echo "  Built: Output/$INSTALLER_NAME ($SIZE)"
echo "============================================"
echo ""
echo "Deploy to Pi:"
echo "  1. Copy $INSTALLER_NAME to USB stick"
echo "  2. On the Pi: sudo bash /media/<user>/<usb>/$INSTALLER_NAME"
echo "  3. Done — Pi reboots with app ready"
echo ""
