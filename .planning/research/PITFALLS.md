# Domain Pitfalls: Packaging & Deployment

**Domain:** Python/Kivy industrial HMI — Windows installer + Raspberry Pi kiosk deployment
**Researched:** 2026-04-21
**Confidence:** MEDIUM-HIGH — PyInstaller/Kivy patterns verified via official docs + community sources; gclib
deployment derived from Galil official docs + ctypes deployment patterns; Pi kiosk from RPi forums 2024-2025

---

## Critical Pitfalls

### Pitfall C1: PyInstaller --onefile mode breaks Kivy at runtime

**What goes wrong:**
`--onefile` mode creates a self-extracting executable that decompresses to a temporary `_MEIxxxxxx`
folder at startup. Kivy locates its SDL2 DLLs, GLEW binaries, fonts, and .kv data files via
`sys._MEIPASS` — but the standard `os.path.dirname(__file__)` path resolution in `main.py`
(currently used for `.kv` file loading, font registration, `users.json`, and `settings.json`)
resolves to the temp folder rather than the installed location. On cold boot the temp folder is
created fresh; on repeated launches previous temp folders may persist and collide.

**Why it happens:**
The project's `main.py` uses `os.path.dirname(os.path.abspath(__file__))` consistently — this is
correct in development but points into `_MEIxxxxxx` in `--onefile` mode. Kivy also requires
`sdl2.dep_bins` and `glew.dep_bins` to be present in the final `COLLECT()` output; `--onefile`
strips this structure entirely, so SDL2 is never found.

**Consequences:**
- App crashes on startup with `ImportError: SDL2 not found` or blank window with no rendering.
- Font files (NotoSans) silently missing → Kivy falls back to its internal font or crashes.
- `users.json` and `settings.json` written to the temp folder → deleted on exit → all user
  accounts and machine type lost on every restart.

**Prevention:**
- Use `--onedir` (one-folder) mode, not `--onefile`. This is the Kivy-official recommendation.
  The output is a folder, not a single .exe, but Inno Setup bundles it cleanly regardless.
- For any path that must persist across runs (users.json, settings.json), write to
  `platformdirs.user_data_dir('dmccodegui')` (Windows: `%APPDATA%\dmccodegui`), not relative
  to `__file__`. Add a `_resolve_data_path()` helper that returns the persistent path in both
  dev and frozen contexts:
  ```python
  import sys, os
  def _get_data_dir() -> str:
      if getattr(sys, 'frozen', False):
          import platformdirs
          return platformdirs.user_data_dir('dmccodegui', appauthor=False)
      return os.path.dirname(os.path.abspath(__file__))
  ```
- Read-only assets (fonts, images, .kv files) can stay relative to `sys._MEIPASS` since they
  are bundled and never written.

**Warning signs:**
- Temp folder `_MEIxxxxxx` accumulates on C:\ after each run.
- Users report losing their PIN accounts after each launch.
- App works on developer machine but crashes on clean install target.

**Phase to address:** Windows packaging phase — decide path strategy before writing the .spec file.

---

### Pitfall C2: SDL2 and GLEW binaries not included — Kivy window never opens

**What goes wrong:**
PyInstaller's default analysis does not include SDL2 or GLEW DLLs. The Kivy `.spec` file must
explicitly pull these from the Kivy-installed package using `kivy_deps.sdl2` and `kivy_deps.glew`.
If the spec file omits the `Tree()` additions to `COLLECT()`, the built .exe launches, imports
Python successfully, but the Kivy window never appears — no error message, just an immediate
silent exit or a black window.

**Why it happens:**
SDL2 and GLEW are native binary dependencies resolved at runtime, not Python imports that
PyInstaller's static analysis can trace. The standard build path for other projects
(`pyinstaller main.py`) produces a spec file with no mention of these.

**Consequences:**
- App silently exits on startup with no traceable Python error.
- Build succeeds with no warnings, making the failure non-obvious.

**Prevention:**
Spec file must include at the top:
```python
from kivy_deps import sdl2, glew
```
And the `COLLECT()` step must include:
```python
*[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)],
```
Run `pip install kivy_deps.sdl2 kivy_deps.glew` in the build environment.
Verify by running the built .exe from a terminal and checking for SDL2 init messages.

**Warning signs:**
- Built .exe exits immediately with no window.
- Process Manager shows Python process spawn and immediate exit (< 1 second).
- No `_MEIxxxxxx` temp folder created on disk (extraction failed before Kivy init).

**Phase to address:** Windows packaging phase — add SDL2/GLEW spec lines to the phase checklist as
a non-negotiable prerequisite.

---

### Pitfall C3: Kivy hidden imports not captured — screens fail to load at runtime

**What goes wrong:**
Kivy uses `importlib`-based dynamic loading for window, audio, text, input, and video providers.
PyInstaller's static analysis cannot trace these. The project also uses `importlib.import_module()`
in `main.py`'s `_resolve_dotted_path()` for machine screen loading — these dotted paths are
never statically imported. Both sets of imports must be explicitly listed in `hiddenimports`.

**Why it happens:**
The `_resolve_dotted_path()` pattern (e.g., loading `"dmccodegui.screens.flat_grind.FlatGrindRunScreen"`)
constructs import paths as strings at runtime — PyInstaller cannot know to include them. Similarly,
`kivy.core.window.WindowSDL2`, `kivy.core.text.text_sdl2`, and `kivy.input.providers.mouse` are
all loaded dynamically by Kivy internally.

**Consequences:**
- App starts but specific screens are blank or crash with `ModuleNotFoundError`.
- Machine type selection succeeds but the run screen never loads.
- Error only appears when navigating to a specific machine type.

**Prevention:**
Add to the spec's `hiddenimports`:
```python
hiddenimports = [
    # Kivy providers
    'kivy.core.window.window_sdl2',
    'kivy.core.text.text_sdl2',
    'kivy.core.audio.audio_sdl2',
    'kivy.core.image.img_sdl2',
    'kivy.input.providers.mouse',
    'kivy.input.providers.wm_touch',
    'kivy.input.providers.wm_pen',
    # All machine screen modules (dynamic import via _resolve_dotted_path)
    'dmccodegui.screens.flat_grind',
    'dmccodegui.screens.serration',
    'dmccodegui.screens.convex',
    # matplotlib backend (Agg only — no Qt/Tk in kiosk)
    'matplotlib.backends.backend_agg',
    'kivy_matplotlib_widget',
]
```
Use `get_deps_minimal()` from `kivy.tools.packaging.pyinstaller_hooks` as a starting point and
add machine-specific modules manually.

**Warning signs:**
- App runs on developer machine but a specific screen is missing on target.
- `ModuleNotFoundError` in the log after navigating to a machine screen for the first time.

**Phase to address:** Windows packaging phase — build the hiddenimports list incrementally by
running the packed app and checking each navigation path.

---

### Pitfall C4: gclib DLL not found in the frozen build

**What goes wrong:**
`gclib` is a native C library (`gclib.dll` on Windows, `libgclib.so` on Linux). The Python
`gclib` module is a ctypes wrapper that calls `ctypes.cdll.LoadLibrary()` at import time. When
the app is frozen by PyInstaller, the DLL must be physically present in the output directory
alongside the .exe (or on `PATH`). If it is not, the `import gclib` at the top of `controller.py`
raises `OSError: [WinError 126] The specified module could not be found`, caught by the
`try/except ImportError` guard as `GCLIB_AVAILABLE = False` — the app silently starts in
no-controller mode with no visible error.

**Why it happens:**
The gclib installer places the DLL in a system PATH location (e.g., `C:\Program Files\Galil\gclib\`).
PyInstaller copies Python-level imports, not DLLs that are loaded via `ctypes.cdll` unless they
are explicitly specified with `--add-binary` or `binaries=` in the spec file.
The `try/except ImportError` guard in `controller.py` swallows the true error (`OSError`),
making it look like gclib is simply not installed rather than failing to load.

**Consequences:**
- App starts with no error message but cannot connect to any controller.
- `GAddresses()` returns empty, all connect attempts silently fail.
- Operator has no way to diagnose the missing DLL.

**Prevention:**
1. Locate the DLL after gclib is installed: `C:\Program Files\Galil\gclib\gclib.dll` (typical path).
2. Add to spec file:
   ```python
   binaries=[('C:/Program Files/Galil/gclib/gclib.dll', '.')]
   ```
3. The `controller.py` guard should catch `OSError` in addition to `ImportError`:
   ```python
   try:
       import gclib
       GCLIB_AVAILABLE = True
   except (ImportError, OSError):
       gclib = None
       GCLIB_AVAILABLE = False
   ```
4. Add a visible startup warning to the UI when `GCLIB_AVAILABLE = False`.
5. On Pi: install gclib via the Galil-provided `.deb` package so `libgclib.so` lands in
   `/usr/lib/`. The venv Python can then find it via the system linker. Do NOT copy it into the
   venv — ctypes resolves via system `LD_LIBRARY_PATH`, not the venv's site-packages.

**Warning signs:**
- App starts but "No controller found" on setup screen with zero addresses listed.
- `ldd` on the .exe shows `gclib.dll` as not found.
- Developer machine works but clean target machine silently fails.

**Phase to address:** Windows packaging phase (DLL bundling); Pi deployment phase (gclib .deb install
in setup script).

---

### Pitfall C5: Raspberry Pi Bookworm defaults to Wayland — Kivy has no Wayland support

**What goes wrong:**
Raspberry Pi OS Bookworm (the current default OS as of 2024) ships with Wayland as the default
compositor (Wayfire or labwc). Kivy 2.x uses SDL2 as its window provider on Pi, and the SDL2
version shipped with Bookworm may not include the `kmsdrm` backend required for console/kiosk
use, and Kivy has no Wayland protocol support. Running `python main.py` under a Wayland session
either produces a black window, an SDL2 error, or the window never gets focus/input events.

**Why it happens:**
Kivy's SDL2 window provider communicates with X11 (via `DISPLAY` environment variable). Under a
Wayland session, `DISPLAY` is not set, so SDL2 falls back to trying direct DRM or fails entirely.
Wayland's security model also prevents arbitrary clients from grabbing input devices without going
through the compositor — Kivy does not implement the Wayland protocol.

**Consequences:**
- App starts on developer machine (Windows/X11) but fails silently on Pi with Bookworm.
- Touchscreen input completely non-functional even if window appears.
- systemd service fails to produce any window — Pi boots to black screen.

**Prevention:**
Force X11 before deployment. In `/boot/firmware/config.txt` (Bookworm path) or via `raspi-config`:
```
# raspi-config → Advanced Options → Wayland → X11
```
Or for a headless/Lite install, set the environment before launching:
```bash
export DISPLAY=:0
export XAUTHORITY=/home/pi/.Xauthority
```
The kiosk systemd service must set `DISPLAY=:0` and `XAUTHORITY=/home/pi/.Xauthority` in its
`[Service]` environment block. Force X11 in `raspi-config` before writing the SD card image.

**Warning signs:**
- `SDL_VIDEODRIVER` not set → SDL tries Wayland first → init fails.
- Log shows `Couldn't connect to display ":0"` or `No available video device`.
- App works with `DISPLAY=:0` in terminal but fails via systemd.

**Phase to address:** Pi kiosk phase — add Wayland→X11 switch as the first step in the Pi setup script.

---

### Pitfall C6: systemd GUI service starts before X11 is ready — DISPLAY not available

**What goes wrong:**
A `[Service]` unit that sets `Environment="DISPLAY=:0"` and `After=graphical.target` still fails
in practice because:
1. `graphical.target` is reached before the X session script in `/etc/X11/xinit/xinitrc.d/`
   imports `DISPLAY` and `XAUTHORITY` into the systemd user session. The timing gap is 2-5 seconds.
2. System-level services (enabled via `systemctl enable`) run as root and cannot write to the
   user's X socket at `/tmp/.X11-unix/X0`.
3. A user-level service (`systemctl --user enable`) does not start automatically on boot unless
   `loginctl enable-linger pi` is set.

**Why it happens:**
The `graphical.target` dependency is not granular enough — it signals that the display manager has
started, not that a user X session is running and accepting connections.

**Consequences:**
- Pi boots, systemd starts the service, app exits immediately with `Couldn't connect to display`.
- Adding `sleep 5` to `ExecStartPre` works on developer Pi but fails on slower SD cards.
- System service runs as root; X11 denies connection from root without explicit `xhost +local:root`.

**Prevention:**
Use the user-service approach with linger:
```ini
# /etc/systemd/system/dmcgui.service
[Unit]
Description=DMC Grinding GUI
After=graphical-session.target
Wants=graphical-session.target

[Service]
User=pi
Group=pi
Environment="DISPLAY=:0"
Environment="XAUTHORITY=/home/pi/.Xauthority"
ExecStartPre=/bin/sleep 5
ExecStart=/home/pi/dmcgui/venv/bin/python -m dmccodegui
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical-session.target
```
Then: `sudo loginctl enable-linger pi`

Alternatively: use the LXDE autostart file (`~/.config/lxsession/LXDE-pi/autostart`) which runs
after the full desktop session is established — simpler and more reliable than systemd for X apps.

**Warning signs:**
- `journalctl -u dmcgui` shows `Couldn't connect to display :0` on every boot.
- App works when launched from terminal or desktop but not via systemd.
- Works after adding `sleep 10` to service — timing-dependent, not a real fix.

**Phase to address:** Pi kiosk phase — choose one of: LXDE autostart (simpler) or user systemd + linger
(more robust). Document the tradeoff in the phase spec. Do not use system service for X apps.

---

### Pitfall C7: Kivy config.ini written to wrong location in frozen/kiosk context

**What goes wrong:**
Kivy writes its config to `~/.kivy/config.ini` by default. In a kiosk deployment where the app
runs as user `pi` via systemd (not a desktop session), the home directory may not have the `.kivy`
folder pre-created. If `~` resolves to `/root` (when running as system service) or to a read-only
path, Kivy raises a `PermissionError` during startup trying to create or read its config.

This is compounded by the existing `Config.set()` calls in `main.py`: these are applied to the
in-memory config before the `.kivy/config.ini` file is written, but only if `Config.set()` is
called before any Kivy import that triggers `Window` creation. In the frozen app, import ordering
may change due to PyInstaller's module pre-loading.

**Why it happens:**
PyInstaller freezes all modules and pre-imports them at a different point in the import graph.
The guarantee that `Config.set()` fires before `Window` is instantiated depends on `main.py`
being the true entry point — which it is in development but may not be if PyInstaller's bootloader
initializes Kivy indirectly.

**Consequences:**
- App boots to wrong resolution or non-fullscreen mode on Pi.
- `PermissionError` on kiosk boot when running as system service.
- `Config.set('graphics', 'fullscreen', ...)` silently ignored → app runs in a window on the Pi desktop.

**Prevention:**
1. Set `KIVY_HOME` to a writable, predictable path before ANY Kivy import, even before `from kivy.config import Config`:
   ```python
   import os
   os.environ['KIVY_HOME'] = '/home/pi/.dmcgui_kivy'  # Pi
   # os.environ['KIVY_HOME'] = os.path.join(os.getenv('APPDATA'), 'dmcgui_kivy')  # Windows
   ```
2. Pre-create the `KIVY_HOME` directory in the setup script.
3. Confirm `Config.set()` ordering in the spec file's runtime hook if needed.

**Warning signs:**
- `PermissionError: [Errno 13] Permission denied: '/root/.kivy'` in journalctl.
- App starts in windowed mode on Pi despite `fullscreen` config.
- Config changes in dev don't match behavior on target Pi.

**Phase to address:** Pi kiosk phase AND Windows packaging phase — set `KIVY_HOME` before Kivy
import in the platform-specific launcher script.

---

## Moderate Pitfalls

### Pitfall M1: matplotlib backend conflict in frozen app

**What goes wrong:**
`kivy_matplotlib_widget` uses the Agg backend (`matplotlib.use('Agg')`). In the frozen build,
matplotlib's backend auto-detection may attempt to import Qt or Tk backends first if they are
present in the bundled environment. If matplotlib finds PyQt5 or tkinter in the bundle (included
as transitive dependencies of something else), it may silently switch to a non-Agg backend that
requires a separate event loop — crashing on first plot operation.

Additionally, PyInstaller includes all matplotlib backends it can statically trace. The font cache
(`~/.matplotlib/fontlist-*.json`) is rebuilt on first run and requires filesystem write access —
which fails if the cache directory is read-only or inside `_MEIPASS`.

**Prevention:**
- Set the backend explicitly before importing matplotlib anywhere:
  ```python
  import matplotlib
  matplotlib.use('Agg')
  ```
- Set `MPLCONFIGDIR` to a writable path in the launcher (same principle as `KIVY_HOME`):
  ```python
  os.environ['MPLCONFIGDIR'] = '/home/pi/.dmcgui_mpl'  # Pi
  ```
- In the spec file's `hiddenimports`, include ONLY `matplotlib.backends.backend_agg`, not
  `matplotlib.backends.backend_qt5agg` or others.
- Do not `pip install PyQt5` in the venv unless needed for other reasons — its presence confuses
  matplotlib backend selection.

**Phase to address:** Windows packaging phase (spec file) + Pi deployment phase (launcher env setup).

---

### Pitfall M2: .kv files and assets not bundled — screens blank in frozen app

**What goes wrong:**
The `ui/` directory (`.kv` files), `assets/fonts/`, and `assets/images/` are data files, not
Python modules. PyInstaller does not include them unless explicitly listed in the `datas=` section
of the spec file. The app loads `.kv` files via `Builder.load_file(os.path.join(..., kv))` using
a path derived from `__file__`. In a frozen build, `__file__` inside `_MEIPASS` is correct only
if the data files were bundled into that location. If `datas=` is missing or uses wrong dest paths,
the files are absent and every screen is blank.

**Prevention:**
Add to spec `datas`:
```python
datas = [
    ('src/dmccodegui/ui', 'dmccodegui/ui'),
    ('src/dmccodegui/assets', 'dmccodegui/assets'),
    ('src/dmccodegui/auth/users.json', 'dmccodegui/auth'),  # only if shipping default users
]
```
Verify the dest paths match what `os.path.join(os.path.dirname(__file__), 'ui')` resolves to
inside `_MEIPASS`. Use a sys._MEIPASS-aware path resolver for asset loading.

**Warning signs:**
- App starts, PIN overlay appears, but all screens are blank (no .kv layout loaded).
- `FileNotFoundError: ui/base.kv` in the log.
- Fonts revert to Kivy default (no Noto Sans) → wrong character rendering on Pi.

**Phase to address:** Windows packaging phase — verify all `Builder.load_file` paths resolve in
the frozen context before considering the build complete.

---

### Pitfall M3: Pi ARM wheel compilation failures in venv

**What goes wrong:**
On Raspberry Pi OS Bookworm (Python 3.11), piwheels provides pre-compiled wheels for Kivy, numpy,
and most common packages. However:
1. `kivy_matplotlib_widget` is not on piwheels — it requires compilation or a local wheel.
2. If the venv was created with `--system-site-packages` (common in tutorials), pip installs
   may silently use system packages instead of venv-local ones.
3. Bookworm's `pip install` with `sudo` is blocked by the OS (`externally managed environment`
   error). The install script must use the venv's pip explicitly.
4. gclib Python wrapper is not on PyPI — it requires running Galil's `setup.py install` manually
   inside the venv, which installs `gclib.py` into venv site-packages but does NOT install the
   native `libgclib.so` (that requires the separate `.deb` package).

**Prevention:**
- Use isolated venv: `python3 -m venv --without-pip /home/pi/dmcgui/venv`, then
  `venv/bin/pip install --extra-index-url https://www.piwheels.org/simple/ kivy`.
- Install gclib native library first via Galil's `.deb`, then install the Python wrapper
  separately inside the venv: `venv/bin/python /usr/share/doc/gclib/src/setup.py install`.
- Build `kivy_matplotlib_widget` from source or ship a pre-compiled wheel built on an identical
  Pi OS version and architecture.
- Add `--extra-index-url https://www.piwheels.org/simple/` to all Pi `pip install` commands.

**Warning signs:**
- `pip install kivy` takes 45+ minutes (building from source, not using piwheels wheel).
- `import gclib` succeeds in venv but `gclib.py()` raises `OSError` for `libgclib.so`.
- `externally managed environment` error when running pip without venv activation.

**Phase to address:** Pi deployment phase — write the install.sh script with explicit piwheels
index and separate gclib native/Python install steps.

---

### Pitfall M4: Users.json and settings.json path breaks between dev and deployed contexts

**What goes wrong:**
`DMCApp.__init__` resolves `users_path` and `settings_path` relative to `__file__` inside the
installed package. On Pi deployment from a git clone, `__file__` is
`/home/pi/dmcgui/src/dmccodegui/auth/users.json` — correct. On Windows with PyInstaller, `__file__`
inside `_MEIPASS` points to a temp directory that is wiped on exit.

If users.json is bundled into the frozen app (read-only), all user creation by AuthManager fails
silently — the JSON write goes to the temp directory and is lost on next launch. The operator's
PIN accounts vanish after every restart.

**Prevention:**
Define a persistent data directory at the top of `main.py` (before `DMCApp.__init__`) and pass
it to `AuthManager` and `mc.init()`. See Pitfall C1 for the `_get_data_dir()` helper pattern.
The setup script (Pi) and Inno Setup installer (Windows) must create this directory with correct
permissions before first launch.

**Warning signs:**
- User accounts created in-app disappear after app restart.
- Admin PIN stops working after reboot.
- `settings.json` machine type resets to unset on every launch.

**Phase to address:** Windows packaging phase (resolve frozen path before writing spec file);
Pi deployment phase (install script creates data dir).

---

### Pitfall M5: Touchscreen input device not recognized on Pi after OS upgrade

**What goes wrong:**
Kivy uses `mtdev` or `evdev` for touchscreen input on Linux. The input device path (e.g.,
`/dev/input/event0`) may change between Bookworm versions, kernel updates, or different Pi
display hardware. In a kiosk where the keyboard is absent, a misconfigured input device leaves
the operator with a completely frozen-looking screen (app running, no response to touch).

Additionally, the Kivy `config.ini` input section must list the correct provider:
```ini
[input]
%(name)s = probesysfs,provider=hidinput
```
If the config is stale (from a Bullseye migration) or set to `mtdev` when the device needs
`hidinput`, touch events are silently dropped.

**Prevention:**
- Run `python -c "import evdev; [print(d) for d in evdev.list_devices()]"` on the target Pi to
  identify the correct device before writing the config.
- Use the `probesysfs` provider in `config.ini` which auto-detects touchscreens at runtime.
- Add a touchscreen smoke test to the Pi deployment checklist: launch app, confirm a tap registers.

**Warning signs:**
- App renders correctly but no touch response.
- `kivy.input.providers` shows no devices detected in the log.
- Works with mouse (`KIVY_MOUSE=mouse`) but not touch.

**Phase to address:** Pi kiosk phase — touchscreen calibration is a hardware validation step, not
a code step. Include in acceptance criteria.

---

### Pitfall M6: Antivirus false positive on PyInstaller-built .exe blocks installation on Windows

**What goes wrong:**
PyInstaller builds are routinely flagged by Windows Defender, Kaspersky, Avast, and others as
suspicious. This is a known issue caused by the bootloader's self-extraction behavior (resembles
malware patterns) and UPX compression. On a factory floor Windows machine with managed security
policy, the installer may be quarantined before it executes — with no obvious error shown to
the operator.

**Prevention:**
- Disable UPX compression: add `upx=False` to the spec file's `EXE()` call.
- Use `--onedir` (not `--onefile`) — directory-mode builds are less likely to trigger heuristics.
- Rebuild PyInstaller's bootloader locally from source to produce a unique binary hash.
- For production: sign the .exe with a code signing certificate. Windows SmartScreen and most AV
  tools reduce false positives significantly for signed binaries.
- If signing is not feasible: document that the installer must be added to Windows Defender
  exclusions, and include this in the deployment instructions.

**Warning signs:**
- Installer downloaded/copied to target machine but never runs.
- Windows Defender notification: "This app has been blocked for your protection."
- .exe file disappears from the download folder (quarantined).

**Phase to address:** Windows packaging phase — test on a clean Windows 11 VM with default
Defender settings before declaring the installer complete.

---

## Minor Pitfalls

### Pitfall m1: Inno Setup admin context vs. user registry for auto-start

**What goes wrong:**
Inno Setup installers run as Administrator by default. Registry writes to
`HKCU\Software\Microsoft\Windows\CurrentVersion\Run` (user auto-start) from an elevated installer
write to the Administrator's profile, not the logged-in user. The auto-start entry is never
visible to the actual user, so the app never launches on login despite a "successful" install.

**Prevention:**
In the Inno Setup script, use `[Registry]` entries with `Root: HKCU` and include
`Flags: uninsdeletevalue`. The script must also check `PrivilegesRequired = admin` — if admin
is needed for the install dir but user-level registry writes are needed for auto-start, use
`[Run]` with `Flags: runasoriginaluser` to run the auto-start registration under the original
(non-elevated) user context.

**Phase to address:** Windows packaging phase — test auto-start on a non-admin user account.

---

### Pitfall m2: DataRecordListener UDP socket fails behind a Windows firewall

**What goes wrong:**
`DataRecordListener` opens a UDP socket to receive Data Record packets from the Galil controller
on port `DR_UDP_PORT`. Windows Firewall blocks inbound UDP on new ports by default and may prompt
the user with a security dialog. In a kiosk-style deployment where the user doesn't have admin
rights, the dialog is suppressed and the UDP socket silently receives nothing. The app works on
the developer machine (which approved the exception) but the Pi streaming produces no position data.

**Prevention:**
- The Windows installer (Inno Setup) must add a firewall exception for `dmccodegui.exe` or for
  the specific UDP port:
  ```
  [Run]
  Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""DMC GUI"" dir=in action=allow protocol=UDP localport=36000"; Flags: runhidden
  ```
- Test DR streaming on a clean Windows machine with default firewall enabled before release.

**Phase to address:** Windows packaging phase — firewall exception in the Inno Setup script.

---

### Pitfall m3: Raspberry Pi GPU memory allocation insufficient for Kivy/OpenGL

**What goes wrong:**
On Pi 4 and Pi 5 with a small GPU memory allocation (default 64MB), Kivy's OpenGL renderer may
fail or produce corrupted graphics when the live matplotlib plot is active. The HDMI output may
show rendering artifacts, or the screen may go black after the first plot update.

**Prevention:**
Add to `/boot/firmware/config.txt`:
```
gpu_mem=128
```
For 7" official Pi display (1024x600), 128MB is sufficient. For 15" (1920x1080), use 256MB.

**Warning signs:**
- Screen goes black or artifacts appear only when the matplotlib widget renders.
- `dmesg` shows DRM/GPU memory allocation failures.
- Works on Pi 5 but fails on Pi 4 (which has less video memory bandwidth).

**Phase to address:** Pi kiosk phase — include `gpu_mem` in the SD card image `config.txt`.

---

### Pitfall m4: Kivy log file fills disk in headless kiosk

**What goes wrong:**
By default Kivy writes a verbose log to `~/.kivy/logs/kivy_YYYY-MM-DD_NN.txt`. On an industrial Pi
running 24/7, these logs accumulate and eventually fill the SD card, causing writes to fail and
settings/users.json corruption.

**Prevention:**
In the launcher or `KIVY_HOME` config.ini, set:
```ini
[kivy]
log_enable = 1
log_maxfiles = 5
log_level = warning
```
Or set `KIVY_NO_CONSOLELOG=1` and `KIVY_LOG_LEVEL=warning` in the systemd service environment.

**Phase to address:** Pi kiosk phase — add log rotation config to the setup script.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| PyInstaller spec file creation | SDL2/GLEW missing (C2), hidden imports (C3) | Build spec from Kivy docs template, not `pyinstaller main.py --onedir` default |
| gclib bundling (Windows) | DLL silently missing (C4), `OSError` swallowed | Add `binaries=` to spec; widen `except` to `(ImportError, OSError)` in controller.py |
| Frozen path resolution | users.json and settings.json lost on restart (C1, M4) | Implement `_get_data_dir()` before writing spec file |
| Pi OS selection | Wayland blocks Kivy (C5) | Force X11 via raspi-config in setup script; document in phase checklist |
| Pi systemd service | DISPLAY missing, service starts too early (C6) | Use LXDE autostart or user service + linger; never use system service for X apps |
| Pi kiosk first boot | KIVY_HOME permission failure (C7) | Create KIVY_HOME dir in install.sh before first launch |
| Pi venv setup | gclib .so not found (M3) | Install gclib .deb first; then Python wrapper inside venv |
| Windows installer | AV quarantine (M6), auto-start in wrong user context (m1) | upx=False; sign or document AV exclusion; test on non-admin user |
| Touchscreen validation | Input device not detected (M5) | Run probesysfs; add touch smoke test to acceptance criteria |
| matplotlib in frozen app | Wrong backend auto-selected (M1) | Set `MPLCONFIGDIR` and `matplotlib.use('Agg')` before any matplotlib import |
| Windows Firewall + DR | UDP port blocked silently (m2) | Add netsh exception in Inno Setup script |

---

## Sources

- Kivy official docs: [Packaging for Windows (Kivy 2.3.1)](https://kivy.org/doc/stable/guide/packaging-windows.html)
- Kivy PyInstaller hooks API: [kivy.tools.packaging.pyinstaller_hooks](https://kivy.org/doc/stable/api-kivy.tools.packaging.pyinstaller_hooks.html)
- PyInstaller runtime information: [sys._MEIPASS, sys.frozen](https://pyinstaller.org/en/stable/runtime-information.html)
- Galil gclib: [Installation and Python wrapper](https://www.galil.com/sw/pub/all/doc/gclib/html/)
- Galil Raspberry Pi: [gclib Now Supports Raspberry Pi](https://www.galil.com/news/servotrends/gclib-now-supports-raspberry-pi)
- RPi Forums (2024-2025): [Bookworm Wayland kiosk mode challenges](https://forums.raspberrypi.com/viewtopic.php?t=380416)
- RPi Forums: [Kiosk mode on RPi 5 with Bookworm Lite (2025)](https://forums.raspberrypi.com/viewtopic.php?t=389880)
- piwheels: [Debian Bookworm and Raspberry Pi 5 wheel availability](https://blog.piwheels.org/2023/11/debian-bookworm-and-raspberry-pi-5/)
- PyInstaller AV false positives: [GitHub issue #6754](https://github.com/pyinstaller/pyinstaller/issues/6754)
- Inno Setup admin context pitfall: [w3tutorials admin-vs-user context](https://www.w3tutorials.net/blog/installing-application-for-currently-logged-in-user-from-inno-setup-installer-running-as-administrator/)
- kivy_matplotlib_widget: [GitHub mp-007/kivy_matplotlib_widget](https://github.com/mp-007/kivy_matplotlib_widget)
- Existing codebase: `controller.py` (gclib import guard pattern, GCLIB_AVAILABLE flag)
- Existing codebase: `main.py` (Config.set ordering, __file__-based path resolution, DataRecordListener UDP)
- Existing codebase: `hmi/data_record.py` (DR_UDP_PORT usage)

---

*Pitfalls research for: PythonDMCGUI v4.0 Packaging & Deployment*
*Researched: 2026-04-21*
