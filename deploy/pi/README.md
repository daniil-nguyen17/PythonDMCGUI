# Pi Deployment Guide — Binh An HMI

Technician reference for installing the Binh An HMI application on a
Raspberry Pi. Three methods are provided depending on available connectivity
and whether identical hardware is being replicated.

---

## Prerequisites (all methods)

- Raspberry Pi 4 (or later) running **64-bit Pi OS Bookworm** (desktop)
- At least 4 GB free space on the SD card
- Controller connected via Ethernet before first launch

---

## Method A: USB/SCP Transfer (recommended for most deployments)

**Best for:** Single Pi, no internet required on the Pi itself.

### Step 1 — Copy the project to the Pi

**Option A1 — USB stick:**
1. Copy the entire project folder to a USB stick on your PC.
2. Insert the USB stick into the Pi and mount it (auto-mounts to `/media/pi/<label>`).
3. Copy to the Pi's home directory:
   ```bash
   cp -r /media/pi/<label>/PythonDMCGUI ~/PythonDMCGUI
   ```

**Option A2 — SCP over network:**
```bash
scp -r PythonDMCGUI pi@<pi-ip-address>:~/PythonDMCGUI
```

### Step 2 — Run the install script

SSH into the Pi (or open a terminal on the Pi desktop) and run:

```bash
cd ~/PythonDMCGUI
sudo bash deploy/pi/install.sh
```

The script runs unattended and handles:
- Forcing X11 display server (Kivy has no Wayland support)
- Installing system packages via apt (Python 3, libsdl2, libmtdev, etc.)
- Installing Galil gclib from the bundled .deb package
- Creating a Python virtual environment at `~/.binh-an-hmi/venv`
- Installing Python dependencies from `requirements-pi.txt`
- Deploying application files to `~/.binh-an-hmi/app/` (rsync, excludes .md, tests, .xlsx, .dmc)
- Creating a desktop shortcut (`~/Desktop/BinhAnHMI.desktop`)
- Disabling screen blanking (so the HMI display stays on)
- Enabling SSH for future remote access

The script logs everything to `/var/log/binh-an-hmi-install.log`.

### Step 3 — Verify

1. Double-click the **BinhAnHMI** icon on the Pi desktop.
2. The app opens to the PIN login screen.
3. Log in with the operator PIN and confirm the controller address is reachable.

**Note:** `install.sh` is idempotent — safe to re-run after applying fixes
without starting the process over. It will update application files and
reinstall Python packages if needed.

---

## Method B: SD Card Image (zero-install for identical hardware)

**Best for:** Deploying to multiple Pis with the same hardware model.

Use this method when you have one working Pi set up via Method A or C and
need to clone it to additional Pis of the same hardware revision.

### Step 1 — Capture the SD card image

On the **configured Pi**, shut down cleanly:

```bash
sudo shutdown now
```

Remove the SD card and, **on a separate Linux machine** (or Windows with
Raspberry Pi Imager), capture the image:

```bash
# Linux — replace /dev/mmcblk0 with your SD card device
sudo dd if=/dev/mmcblk0 of=binh-an-hmi.img bs=4M status=progress
```

Or use **Raspberry Pi Imager** on Windows: click "Use custom" and select
the source SD card, then write to an image file.

### Step 2 — Write the image to a new SD card

```bash
# Linux
sudo dd if=binh-an-hmi.img of=/dev/mmcblk0 bs=4M status=progress

# Or use Raspberry Pi Imager on Windows
```

### Step 3 — First-boot steps

1. Insert the SD card and boot the new Pi.
2. If using `dd`, the filesystem may need expanding:
   ```bash
   sudo raspi-config
   # Navigate to: Advanced Options > Expand Filesystem
   sudo reboot
   ```
3. Raspberry Pi Imager handles filesystem expansion automatically.
4. Confirm the HMI desktop shortcut is present and launches correctly.

**Note:** SD card image automation tooling is planned for a future release
(FUTURE-02). The manual `dd` / Imager workflow is the supported approach today.

---

## Method C: git clone (requires internet on the Pi)

**Best for:** Development machines or initial setup when the Pi has internet.

### Step 1 — Clone the repository

On the Pi (or via SSH):

```bash
git clone <repo-url> ~/PythonDMCGUI
```

Replace `<repo-url>` with the actual repository URL (ask your developer).

### Step 2 — Run the install script

```bash
cd ~/PythonDMCGUI
sudo bash deploy/pi/install.sh
```

Same outcome as Method A — the desktop shortcut appears and the app
launches to the PIN login screen.

---

## Troubleshooting

**Long first install (20-40 min):**
`kivy_matplotlib_widget` may compile from source on aarch64 because a
pre-built wheel is not always available on PiWheels. This is normal.
Do not interrupt. Monitor progress in `/var/log/binh-an-hmi-install.log`.

**Wrong screen preset (7inch vs 10inch):**
If the display preset is detected incorrectly, override it manually:

```bash
mkdir -p ~/.binh-an-hmi
cat > ~/.binh-an-hmi/settings.json <<'EOF'
{"display_size": "7inch"}
EOF
```

Valid values: `"7inch"`, `"10inch"`, `"15inch"`.

**App fails to start:**
Check the application log:

```bash
cat ~/.binh-an-hmi/logs/app.log
```

**Install script errors:**
Full install log:

```bash
sudo cat /var/log/binh-an-hmi-install.log
```
