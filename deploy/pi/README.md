# Pi Deployment Guide — Binh An HMI

Technician reference for installing the Binh An HMI application on a
Raspberry Pi. Three methods are provided depending on available connectivity
and whether identical hardware is being replicated.

---

## Prerequisites (all methods)

- Raspberry Pi 4, Pi 5, or Pi 500 running **64-bit Pi OS Bookworm** (desktop)
- **Must be 64-bit** — 32-bit Pi OS is not supported (gclib and build toolchain require aarch64)
- At least 4 GB free space on the SD card
- Controller connected via Ethernet (the installer configures a static IP automatically)

### Offline installation (recommended)

For fastest deployment without internet on the Pi, pre-load the `deploy/pi/vendor/`
directory with gclib .deb files. See `deploy/pi/vendor/README.md` for instructions.

---

## Method A: USB/SCP Transfer (recommended for most deployments)

**Best for:** Single Pi, no internet required on the Pi itself.

### Step 1 — Copy the project to the Pi

**Option A1 — USB stick:**
1. Copy the entire project folder to a USB stick on your PC.
2. Insert the USB stick into the Pi (auto-mounts to `/media/<user>/<label>`).

**Option A2 — SCP over network:**
```bash
scp -r PythonDMCGUI pi@<pi-ip-address>:~/PythonDMCGUI
```

### Step 2 — Run the install script

Open a terminal on the Pi and run:

```bash
cd /media/<user>/<label>/PythonDMCGUI
sudo bash deploy/pi/install.sh
```

Or if you copied to the home directory:

```bash
cd ~/PythonDMCGUI
sudo bash deploy/pi/install.sh
```

The script runs unattended and handles everything:
- Forcing X11 display server (Kivy has no Wayland support)
- Installing system packages via apt (Python 3, libsdl2, libmtdev, etc.)
- Installing Galil gclib (from vendor .debs if available, or via apt repo)
- Configuring static IP (100.100.100.10/24) on eth0 for controller network
- Copying application files to `/opt/binh-an-hmi/`
- Creating a Python virtual environment
- Installing Python dependencies from `requirements-pi.txt`
- Creating a desktop shortcut
- Disabling screen blanking (so the HMI display stays on)
- Enabling SSH for future remote access
- Rebooting automatically when done

The script logs everything to `/var/log/binh-an-hmi-install.log`.

**Note:** You can run the script directly from the USB stick — you do NOT need
to copy the project to the Pi's SD card first. The installer copies what it needs
to `/opt/binh-an-hmi/`.

### Step 3 — Verify

After the Pi reboots:
1. Double-click the **Binh An HMI** icon on the Pi desktop.
2. The app opens to the PIN login screen.
3. Enter `100.100.100.2` as the controller address and connect.

**Note:** `install.sh` is idempotent — safe to re-run after applying fixes
without starting the process over.

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
launches to the PIN login screen after reboot.

---

## Network Configuration

The installer automatically configures a static IP on the Pi's Ethernet port:

| Setting | Value |
|---------|-------|
| Pi IP | 100.100.100.10 |
| Subnet | /24 (255.255.255.0) |
| Controller IP | 100.100.100.2 |
| Interface | eth0 |

This is created as a NetworkManager connection profile (`galil-controller`)
that persists across reboots. The Pi's WiFi connection is not affected.

**To change the static IP** (if deploying multiple Pis on the same network):

```bash
sudo nmcli connection modify galil-controller ipv4.addresses 100.100.100.11/24
sudo nmcli connection up galil-controller
```

---

## Troubleshooting

**Long first install (20-40 min):**
`kivy_matplotlib_widget` may compile from source on aarch64 because a
pre-built wheel is not always available on PiWheels. This is normal.
Do not interrupt. Monitor progress in `/var/log/binh-an-hmi-install.log`.

**Desktop shortcut shows text instead of launching:**
Right-click the shortcut and select "Allow Launching" or "Trust this executable".
Or from terminal: `chmod +x ~/Desktop/binh-an-hmi.desktop`

**Controller shows "unknown options: M, G":**
This is fixed in the current version. If you see this on an older install,
the gclib flags need updating — re-run the install script to get the latest code.

**Controller won't connect (timeout):**
Verify the static IP is configured:
```bash
ip addr show eth0 | grep inet
```
Should show `100.100.100.10/24`. If missing:
```bash
sudo nmcli connection up galil-controller
```

Test connectivity:
```bash
ping 100.100.100.2 -c 3
```

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
