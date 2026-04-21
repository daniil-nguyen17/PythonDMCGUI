# Feature Landscape

**Domain:** Industrial Python HMI — Packaging & Deployment (v4.0)
**Researched:** 2026-04-21
**Confidence:** HIGH (Windows installer, Pi systemd patterns) / MEDIUM (update mechanisms, logging)

> **Scope note:** This supersedes the v3.0 FEATURES.md (which covered the multi-machine screen
> refactor). v4.0's goal is getting the working HMI into installable bundles for Windows 11
> and Raspberry Pi. All prior HMI functionality (PIN auth, live plots, per-machine screens,
> controller comms) is already built — this document covers only packaging and deployment features.

---

## Table Stakes

Features that make the deployment usable. Missing any of these means operators cannot
run the machine, support cannot troubleshoot remotely, or the app is stranded when it crashes.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Windows: self-contained .exe bundle | Operators won't have Python installed. Windows must "just work" out of a folder or installer. | MEDIUM | PyInstaller produces a one-folder or one-file bundle. Kivy has official hooks (`kivy.tools.packaging.pyinstaller_hooks`). gclib is a C DLL — must be included via `datas` in the spec file. Matplotlib and kivy_matplotlib_widget require explicit hiddenimports. |
| Windows: Start Menu and Desktop shortcuts | Every Windows app creates shortcuts. Missing shortcuts means "where did it install?" calls. | LOW | Inno Setup handles shortcut creation declaratively. NSIS is an alternative but requires scripted logic. Either wraps the PyInstaller output folder and creates `[Icons]` entries. |
| Windows: Add/Remove Programs entry | Users expect to see the app in "Apps & Features" and be able to uninstall cleanly. | LOW | Inno Setup creates the Uninstall registry entry automatically. This is zero extra work once Inno Setup is chosen. |
| Pi: virtual environment with all deps | Pi OS Bookworm (2023+) REQUIRES pip installs to go into a venv. System-wide pip is blocked. Installing without a venv will fail silently or error. | LOW | `python3 -m venv --system-site-packages ~/dmc_gui_env`. Use `--system-site-packages` to inherit apt-installed packages (e.g., system OpenGL libs needed by Kivy). Install deps via `~/dmc_gui_env/bin/pip install -r requirements.txt`. |
| Pi: systemd service with auto-restart | If the app crashes (which it will in field conditions), operators will not know how to restart it. Restart must be automatic. | LOW | `Restart=on-failure` + `RestartSec=3` in the unit file covers the majority of crash scenarios. `StartLimitIntervalSec=60` + `StartLimitBurst=5` prevents infinite restart loops on fatal errors. |
| Pi: fullscreen kiosk, no desktop access | Operators must not be able to reach the desktop, file manager, or terminal. The app must own the screen. | MEDIUM | Two approaches: (1) autologin user with `.bashrc` launching the app, or (2) systemd user service that starts before the desktop loads. On Pi OS Bookworm (Wayland), a systemd service or XDG autostart file works. The app itself sets `Config.set('graphics', 'fullscreen', 'auto')` before importing Kivy's Window — this is already established in main.py's pattern. |
| Rotating log file | Field deployments cannot tolerate unbounded log growth on a 16 GB SD card or Windows drive. A crashed app leaves no trace without logs. | LOW | Python's `logging.handlers.RotatingFileHandler` — 5 MB per file, keep 3 backups = 15 MB max. Write to `~/.dmc_gui/logs/app.log` (Pi) or `%APPDATA%\DMCGui\logs\app.log` (Windows). |
| Uncaught exception logging | Silent crashes are the worst debugging scenario in field deployments. All unhandled exceptions must be captured to the log. | LOW | `sys.excepthook = _log_uncaught_exception` at the top of main.py. Log the full traceback before exit. Add a Kivy `on_stop` handler to flush log buffers. |
| Exclude dev-only files from package | .planning/, tests/, Excel files, and .dmc files add bulk and expose internal project artifacts to operators. | LOW | PyInstaller spec file `excludes` list or `.spec` `datas` whitelist. Inno Setup `[Files]` section controls what goes into the installer. For Pi, the install.sh script clones only the app directory or uses a stripped archive. |

---

## Differentiators

Features that raise the deployment quality above "it runs on the target machine" to
"service technicians can maintain it in the field."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Windows: optional auto-start on login | Dedicated grinding workstations should boot straight to the HMI. Making this a checkbox during install is cleaner than manual configuration. | LOW | Inno Setup can write `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` or create a shortcut in the user's Startup folder. Use HKCU (current user) so admin rights are not required at runtime. Offer as an optional "Launch at Windows startup" checkbox in the installer. |
| Windows: version number in installer title and executable | Technicians need to confirm which build is deployed. Version in the installer title and in File Properties prevents "which version is this?" confusion. | LOW | Embed `version.txt` or bake version string into `main.py`. PyInstaller reads `--version-file` for Windows EXE version resources. Inno Setup reads `AppVersion` from the same source. |
| Pi: three deployment paths | Different field scenarios have different constraints. A customer with a fresh Pi needs a different method than one updating an existing install. | MEDIUM | (1) `install.sh` via USB/SCP — git clone + venv setup + systemd unit install; (2) SD card image — pre-built image with app + deps; (3) git clone + script for developers. The script path is the foundation; the image path uses `rpi-imager` or `dd`. |
| Pi: systemd hardware watchdog (WatchdogSec) | Software `Restart=on-failure` handles crashes. Hardware watchdog handles hangs — a frozen app that appears alive but stops updating the display. Critical for unattended kiosk use. | MEDIUM | Set `WatchdogSec=30` in the unit file. App must call `sd_notify(WATCHDOG=1)` periodically — use the `sdnotify` Python package. Add a periodic Clock-scheduled callback in main.py at 10s intervals. If the Kivy event loop dies, the watchdog fires and systemd restarts. |
| Screen resolution auto-detection with override | Pi touchscreens come in 7" (800x480), 10" (1024x600), and 15" (1280x800). Windows target is 1920x1080. The same app binary must display correctly on all. | MEDIUM | `Config.set('graphics', 'fullscreen', 'auto')` is already established. For Pi, read display resolution via `subprocess.check_output(['xrandr'])` or check `Window.system_size` post-init. Write a `settings.json` override key `"display_override": "800x480"` — startup code reads this before calling Config.set. |
| DMC/Excel files as optional separate bundle | First-time controller setup needs the DMC program and Excel parameter sheets. These are not part of the runtime and should not clutter the install, but must be available. | LOW | Ship as a separate ZIP file or installer. Include a README.txt with controller setup instructions. Keep this separate from the main installer — its audience is setup engineers, not operators. |
| Log viewer accessible from Admin tab | In-field debugging currently requires SSH access or pulling the SD card. An Admin-only "View Logs" button that opens the last 200 lines of app.log eliminates most on-site debugging trips. | MEDIUM | New `LogViewerScreen` or a modal popup with a `ScrollView` + `Label`. Read `app.log` via Python's `logging` file path. Restrict to Admin role. This is a v4.x addition, not strictly required for initial deployment. |
| Install directory configurable in Windows installer | Some industrial IT environments require software to install to D:\ or a specific network share. | LOW | Inno Setup `DefaultDirName` can be overridden at install time. No code changes to the app itself. |

---

## Anti-Features

Features commonly requested for software deployment that are wrong for this application.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Over-the-air / network auto-update | This app runs in industrial facilities that may have no internet, air-gapped networks, or strict change management controls. An auto-updater that calls home would fail silently or be blocked by IT. | Manual update via USB stick (Pi) or re-running the installer (Windows). The existing git-based install.sh supports `git pull` for the SD-connected scenario. |
| Crash reporting to external service (Sentry, Bugsnag) | Same network constraints. Also, crash data may include machine parameters that are proprietary to the customer. | Local rotating log file only. Admin can view logs in-app or copy them to USB for support. |
| Single-file PyInstaller executable (--onefile) | --onefile extracts to a temp directory on every launch, which is slow on Pi and fails if the temp partition is small. Also breaks gclib DLL loading via absolute path. | Use --onedir (the default). The folder is the deployable artifact. Inno Setup wraps the folder into a proper installer without needing --onefile. |
| Python virtualenv inside the Windows installer | On Windows, PyInstaller bundles the interpreter and all deps into the output folder. A venv inside the installer adds complexity without benefit. | PyInstaller output folder IS the isolation layer on Windows. Venv is only needed on Pi where system Python is the runtime. |
| Updater .exe / in-app "Check for Updates" button | Industrial app updates require validation and sign-off before reaching the floor. Silent or user-initiated updates bypass the change management process. | Deliver updates as a new installer (.exe for Windows, new install.sh run for Pi). Change management is manual by design. |
| Desktop wallpaper / splash screen branding | Nice for consumer apps. Adds build complexity and is irrelevant on a grinding machine HMI that runs fullscreen from boot. | The Kivy dark theme already provides a professional appearance. No splash screen needed. |
| NSIS instead of Inno Setup | NSIS is fully scripted (think low-level assembler). Inno Setup is INI-based with optional Pascal scripting. For this app's needs (shortcuts, registry key for autostart, uninstaller), Inno Setup is 80% less code. | Use Inno Setup 6.x. Only switch to NSIS if a specific requirement cannot be expressed in Inno Setup's scripting model. |
| Automatic Pi OS upgrade during install | `sudo apt upgrade` during the install script risks breaking system packages that gclib or Kivy depend on. Pi OS upgrades are not atomic and can leave the system in a broken state if interrupted. | Document required Pi OS version (Bookworm 64-bit recommended). install.sh installs only the Python packages needed. Do not run apt upgrade. |
| Multi-user Windows profiles | The HMI's auth is handled internally (PIN system). Windows user accounts add a layer of authentication that operators will not expect and support staff cannot manage. | Install for the current Windows user (HKCU) or machine-wide (HKLM). The app's PIN system handles role-based access. |

---

## Feature Dependencies

```
PyInstaller spec file (.spec)
  ├── requires: working main.py (already done)
  ├── requires: gclib DLL path known and added to datas
  ├── requires: Kivy hooks (kivy.tools.packaging.pyinstaller_hooks.get_deps_all())
  ├── requires: kivy_matplotlib_widget in hiddenimports
  └── produces: dist/DMCGui/ folder (one-dir mode)

Inno Setup script (.iss)
  ├── requires: PyInstaller dist/DMCGui/ folder (complete and tested)
  ├── provides: Start Menu shortcut
  ├── provides: Desktop shortcut
  ├── provides: Add/Remove Programs entry
  ├── provides: optional HKCU Run key for auto-start
  └── produces: DMCGui_Setup_v4.0.exe

Pi install.sh
  ├── requires: Pi OS Bookworm (Bookworm mandates venv for pip)
  ├── step 1: sudo apt install python3-venv python3-pip python3-dev libgl1
  ├── step 2: python3 -m venv --system-site-packages ~/dmc_gui_env
  ├── step 3: ~/dmc_gui_env/bin/pip install -r requirements.txt
  ├── step 4: copy systemd unit file to /etc/systemd/system/
  ├── step 5: systemctl enable --now dmc_gui.service
  └── produces: working kiosk on boot

systemd unit file (dmc_gui.service)
  ├── requires: venv Python binary path (~/dmc_gui_env/bin/python)
  ├── requires: main.py absolute path
  ├── Restart=on-failure
  ├── RestartSec=3
  ├── StartLimitIntervalSec=60
  ├── StartLimitBurst=5
  └── WatchdogSec=30 (differentiator — requires sdnotify heartbeat in app)

Rotating log setup (in main.py before app.run())
  ├── requires: platform detection to set log path correctly
  ├── requires: sys.excepthook patched before any Kivy import
  └── feeds: Admin log viewer (differentiator, v4.x)

Screen resolution handling
  ├── requires: existing Config.set('graphics', 'fullscreen', 'auto') pattern (already in place)
  ├── extend: read settings.json for display_override key before Config.set
  └── no Inno Setup / systemd dependencies
```

### Dependency Ordering Notes

- **PyInstaller spec must come before Inno Setup:** The installer wraps the PyInstaller output. Build and test the PyInstaller bundle on a clean Windows machine before writing the Inno Setup script.
- **Pi venv must come before systemd unit:** The unit file references the venv's Python binary by absolute path. Writing the unit file before confirming the venv path causes a silent failure on boot.
- **Rotating log setup must be in main.py before any Kivy import:** The existing `Config.set` pattern in main.py confirms this ordering constraint is understood. Logging setup follows the same rule — initialize before `from kivy.app import App`.
- **gclib DLL path is the highest-risk unknown on Windows:** gclib is a proprietary Galil library. PyInstaller will not detect it automatically via import analysis. The exact DLL filename and whether it is in PATH or installed to a fixed directory must be confirmed before the spec file is finalized.

---

## MVP Definition

### Ship for v4.0 (Minimum Deployable Package)

These are required before any real hardware testing can begin on target machines.

- [ ] PyInstaller spec file that builds a working one-dir bundle on Windows 11 (includes gclib DLL, Kivy providers, matplotlib, kivy_matplotlib_widget)
- [ ] Inno Setup script that wraps the bundle into a .exe installer with Start Menu shortcut, Desktop shortcut, and Add/Remove Programs entry
- [ ] Rotating log file initialized in main.py (`RotatingFileHandler`, 5 MB limit, 3 backups, platform-correct path)
- [ ] `sys.excepthook` patched to log uncaught exceptions before any Kivy import
- [ ] Pi `install.sh` that creates a venv, installs requirements.txt, installs systemd unit, enables kiosk mode
- [ ] Pi systemd unit file with `Restart=on-failure`, `RestartSec=3`, `StartLimitBurst=5`
- [ ] Pi fullscreen kiosk (systemd service + `Config.set fullscreen auto` already in place)
- [ ] Dev-only files excluded from all package types (.planning/, tests/, .dmc, .xlsx)

### Add in v4.x (After Initial Hardware Validation)

- [ ] Windows optional auto-start on login (Inno Setup checkbox writing HKCU Run key)
- [ ] Version number embedded in Windows EXE resources and Inno Setup title
- [ ] Pi hardware watchdog (WatchdogSec=30 + sdnotify heartbeat in main.py)
- [ ] SD card image for zero-touch Pi deployment
- [ ] Screen resolution override via settings.json display_override key
- [ ] Admin log viewer (last 200 lines of app.log, in-app modal)

### Defer to v5.0 or Drop

- [ ] Network/OTA updates (incompatible with industrial change management)
- [ ] External crash reporting (network constraints, IP concerns)
- [ ] In-app "Check for Updates" flow

---

## Sources

- PyInstaller + Kivy official packaging docs: https://kivy.org/doc/stable/guide/packaging-windows.html (HIGH confidence)
- Kivy PyInstaller hooks API: https://kivy.org/doc/stable/api-kivy.tools.packaging.pyinstaller_hooks.html (HIGH confidence)
- Inno Setup feature set: https://jrsoftware.org/isinfo.php (HIGH confidence)
- Pi OS Bookworm venv requirement: https://www.raspberrypi.com/news/using-python-with-virtual-environments-the-magpi-148/ (HIGH confidence)
- Pi OS Bookworm venv details: https://pimoroni.github.io/venv-python/ (HIGH confidence)
- systemd Restart policies + WatchdogSec: https://oneuptime.com/blog/post/2026-03-02-configure-systemd-restartsec-watchdogsec-ubuntu/view (MEDIUM confidence)
- systemd service restart on Pi: https://forums.raspberrypi.com/viewtopic.php?t=324417 (MEDIUM confidence)
- Python rotating log handler: Python stdlib `logging.handlers.RotatingFileHandler` docs (HIGH confidence)
- Windows startup registry keys: https://learn.microsoft.com/en-us/windows/win32/setupapi/run-and-runonce-registry-keys (HIGH confidence)
- Industrial HMI USB update patterns: https://delta-ia-tips.com/2023/07/31/hmi-firmware-update-using-usb-stick/ (MEDIUM confidence — pattern confirmed by multiple vendors)
- Kivy fullscreen/auto resolution: https://kivy.org/doc/stable/api-kivy.core.window.html (HIGH confidence)

---

*Feature research for: v4.0 Packaging & Deployment milestone*
*Researched: 2026-04-21*
