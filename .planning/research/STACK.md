# Technology Stack: Packaging & Deployment

**Project:** DMC Grinding GUI — v4.0 Packaging & Deployment Milestone
**Researched:** 2026-04-21
**Scope:** Windows .exe installer, Raspberry Pi venv/systemd/kiosk, screen resolution adaptation

---

## Recommended Stack

### Windows Packaging

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PyInstaller | 6.19.0 | Bundle Python + all deps into distributable | Only packager with first-class Kivy hooks (SDL2/GLEW Tree injection); cx_Freeze lacks them; Briefcase doesn't support Kivy well |
| Inno Setup | 6.7.1 | Wrap PyInstaller onedir output into a .exe installer | Declarative Pascal scripting, built-in uninstaller tracking, VS Code uses it, lighter learning curve than NSIS, 200 KB overhead irrelevant at bundle scale |
| kivy-deps.sdl2 | (Kivy-matched) | SDL2 DLLs bundled via spec file Tree injection | Required by spec — `sdl2.dep_bins` Tree; without it the SDL2 window provider fails silently on target machines that have no system Kivy install |
| kivy-deps.glew | (Kivy-matched) | GLEW DLLs bundled via spec file Tree injection | Same reason — `glew.dep_bins` must be in COLLECT; omitting it causes blank window on Windows machines with only integrated graphics |
| screeninfo | 0.8.1 | Pre-startup physical display size detection (runtime dep) | Pure Python, cross-platform (Windows/X11), no display server required at detection time; must be installed on dev machine and listed in requirements |

### Raspberry Pi Deployment

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python venv | 3.11 (Bookworm default) | Isolated runtime on Pi | PiWheels provides Kivy 2.3 pre-compiled ARM wheels for Python 3.11 / Bookworm; avoids 2-hour source builds |
| pip + PiWheels | current | Install all Python deps on Pi | PiWheels is the official wheel index for Raspberry Pi OS; Kivy's own docs cite it as the install path |
| systemd system service | (OS-provided) | Autostart on boot, restart on crash | Modern standard on Bookworm; rc.local is deprecated; LXDE autostart files no longer exist (Wayfire/Wayland replaced LXDE) |
| install.sh script | (custom) | One-command setup on fresh Pi | Encapsulates venv creation, apt deps, gclib .deb install, systemd unit enable — reproducible, no manual steps |
| Raspberry Pi Imager | 1.8+ | Flash base OS to SD card | Official tool; customises hostname/SSH/wifi at flash time |
| dd (Linux) / Win32DiskImager (Windows) | OS-provided | Clone a configured SD to image file for the "deploy from image" workflow | Flash once on a reference unit, clone image for all remaining units |

### Screen Resolution Adaptation

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| screeninfo | 0.8.1 | Query physical display dimensions before Kivy starts | Must run before any Kivy import; screeninfo works without a display server (unlike Tkinter) and without PIL (unlike pyautogui) |
| kivy.config.Config.set | Kivy built-in | Set `graphics.width/height/fullscreen` before Window import | The only supported mechanism; Config is frozen on first Window import, so detection and Config.set must happen in the same pre-Kivy block at the top of main.py |
| KIVY_DPI env var | Kivy built-in | Allow install.sh to pin DPI per display profile | Deploy script sets `KIVY_DPI=160` for 7" displays in the systemd unit; overrides Kivy's autodetect which is unreliable on Pi HDMI-forced framebuffers |

---

## gclib Bundling Strategy

### Windows

gclib on Windows is a conventional C DLL pair (`gclib.dll`, `gclibo.dll`) installed by the Galil installer to `C:\Program Files (x86)\Galil\gclib\`. The Python wrapper calls `ctypes.cdll.LoadLibrary` with a hardcoded path to that directory.

**Problem:** PyInstaller does not auto-discover DLLs loaded via absolute ctypes path strings — it only bundles DLLs next to the executable or on system PATH at analysis time. The Galil DLLs are not on PATH by default.

**Strategy:**
1. Copy `gclib.dll` and `gclibo.dll` from a Galil installation into `src/dmccodegui/vendor/galil/` and commit them to the repo. These are redistributable runtime files, not the installer itself.
2. In the PyInstaller spec `datas`, add `('src/dmccodegui/vendor/galil/*.dll', '.')` so both DLLs land in the root of the onedir output folder (next to the executable).
3. In `main.py`, in the pre-Kivy block, patch the gclib search path before importing gclib. The gclib Python wrapper exposes `GclibDllPath_` and `GcliboDllPath_` class attributes that can be overridden before the first `GOpen()` call:
   ```python
   if hasattr(sys, '_MEIPASS'):
       import gclib
       gclib.GclibDllPath_  = os.path.join(sys._MEIPASS, 'gclib.dll')
       gclib.GcliboDllPath_ = os.path.join(sys._MEIPASS, 'gclibo.dll')
   ```
4. The Inno Setup script does NOT run the Galil system installer — the DLLs are already in the bundle. This removes the per-machine Galil software prerequisite entirely.

**Confidence:** MEDIUM. The `GclibDllPath_` attribute override is documented in the Galil gclib class reference as the mechanism for non-default DLL locations. Verify the exact attribute names in the installed `gclib/__init__.py` before implementing, as minor version differences may change them.

### Raspberry Pi

gclib on Linux installs as `libgclib.so` via Galil's `.deb` package. Galil explicitly provides ARM builds for Raspberry Pi OS (announced and documented on galil.com).

**Strategy:**
1. Download the Galil gclib `.deb` for ARM and commit it to `deploy/pi/deps/galil-gclib-arm.deb` in the repo.
2. `install.sh` runs `sudo dpkg -i deploy/pi/deps/galil-gclib-arm.deb` followed by `sudo ldconfig`. The `.deb` post-install script registers the `.so` with the system linker.
3. The Python gclib wrapper (pip-installable) finds `libgclib.so` via `ctypes.find_library` through the normal system linker path — no path patching required on Linux.
4. The `.so` is NOT placed inside the venv. It is a system library (root-owned). The venv's Python process resolves it through `LD_LIBRARY_PATH` or `/etc/ld.so.conf.d/` (populated by `ldconfig` after the `.deb` install).
5. Install the Python gclib wrapper into the venv: `/opt/dmcgui/venv/bin/pip install gclib`

**Confidence:** MEDIUM-HIGH. Galil officially documents and supports Raspberry Pi OS deployment, provides ARM `.deb` packages, and published an announcement specifically about Pi support. The pip-installable gclib wrapper is the same one used in the existing dev environment.

---

## Alternatives Considered and Rejected

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Windows bundler | PyInstaller 6.19 | cx_Freeze | No Kivy SDL2/GLEW hooks; manual DLL hunting required; 10x smaller community (12.8k vs 1.5k GitHub stars); GUI app packaging is explicitly called out as more complex |
| Windows bundler | PyInstaller 6.19 | Briefcase (BeeWare) | Mobile/web-first; Kivy support is experimental; not tested for industrial desktop; no community examples for this use case |
| Windows bundler | PyInstaller 6.19 | Nuitka | Compiles to C — build times are 10–30x longer; licensing complexity; no IP protection needed for a closed internal tool; overkill |
| Windows installer | Inno Setup 6.7 | NSIS | More powerful but harder to learn; Inno Setup handles uninstaller, registry, Start Menu, Desktop shortcuts with ~20 lines of declarative script vs NSIS plugin stack |
| Windows installer | Inno Setup 6.7 | WiX / MSI | Enterprise XML toolchain; designed for corporate MSI deployment chains, not a single-site industrial tool |
| PyInstaller mode | onedir | onefile | onefile re-extracts to %TEMP% on every launch, adding 5–30 seconds and triggering AV false positives on locked-down industrial machines. onedir with Inno Setup wrapping is correct: installers were designed for folder trees |
| Pi Python | pip + venv | conda / miniconda | Conda ARM support on Pi is unreliable; heavier than needed; PiWheels makes pip the right choice |
| Pi autostart | systemd service | LXDE autostart file | LXDE autostart no longer exists on Bookworm (replaced by Wayfire compositor); LXDE approach would fail on all current Pi OS installs |
| Pi display backend | X11 + SDL2 | Wayland (direct) | SDL KMSDRM driver has documented display corruption bugs on RPi 5 with Bookworm/Wayland (SDL GitHub issue #8579). Force X11 session until Kivy/SDL2 officially validates Wayland on Pi |
| Screen detection | screeninfo | `tkinter.Tk().winfo_screenwidth()` | Requires Tk display context; creates a visible window flash on some systems; adding tkinter as a dep for a Kivy app is wrong |
| Screen detection | screeninfo | pyautogui.size() | Pulls in PIL and requires an X server connection at call time; too heavy for a detection-only use case |

---

## Installation

### Windows Build Machine (developer)

```bash
# Core packaging tools
pip install pyinstaller==6.19.0

# Kivy SDL2/GLEW packages needed for spec file DLL Trees
pip install kivy-deps.sdl2 kivy-deps.glew

# Screen detection (runtime dep — also add to requirements.txt)
pip install screeninfo==0.8.1

# Build the distributable (onedir mode)
pyinstaller dmcgui.spec

# Create the .exe installer
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

### PyInstaller spec file (key additions for Kivy)

```python
# dmcgui.spec — key sections

import kivy_deps.sdl2 as sdl2
import kivy_deps.glew as glew

a = Analysis(
    ['src/dmccodegui/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # All KV files
        ('src/dmccodegui/ui/**/*.kv',        'dmccodegui/ui'),
        # Vendor DLLs for gclib
        ('src/dmccodegui/vendor/galil/*.dll', '.'),
        # kivy_matplotlib_widget KV assets
        ('path/to/kivy_matplotlib_widget/**/*.kv', 'kivy_matplotlib_widget'),
        # Profile CSVs (if shipped with installer)
        ('profiles/',                          'profiles'),
    ],
    hiddenimports=['kivy.core.window.window_sdl2', 'kivy.core.renderer.renderer_sdl2'],
    hookspath=[],
    excludes=['tkinter', '_tkinter', 'matplotlib.backends.backend_tkagg'],
    ...
)

exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='DMCGrindingGUI', ...)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    # SDL2 and GLEW DLL trees — required for Kivy window provider
    *[Tree(p) for p in sdl2.dep_bins],
    *[Tree(p) for p in glew.dep_bins],
    strip=False,
    upx=False,
    name='DMCGrindingGUI',
)
```

### Raspberry Pi Target Machine

```bash
# install.sh (committed to deploy/pi/)
# Run as: sudo ./install.sh

# 1. System dependencies for Kivy + SDL2
apt-get install -y libgl1-mesa-glx libgles2-mesa libegl1-mesa libmtdev1 \
                   libsdl2-2.0-0 libsdl2-image-2.0-0 libsdl2-mixer-2.0-0

# 2. Install gclib system library
dpkg -i /opt/dmcgui/deploy/pi/deps/galil-gclib-arm.deb
ldconfig

# 3. Create Python venv
python3.11 -m venv /opt/dmcgui/venv

# 4. Install Python dependencies (PiWheels speeds up Kivy dramatically)
/opt/dmcgui/venv/bin/pip install --extra-index-url https://www.piwheels.org/simple \
    kivy==2.3.1 matplotlib kivy_matplotlib_widget gclib screeninfo

# 5. Install systemd service
cp /opt/dmcgui/deploy/pi/dmcgui.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable dmcgui
systemctl start dmcgui
```

### Pi systemd service unit

```ini
# /etc/systemd/system/dmcgui.service

[Unit]
Description=DMC Grinding GUI
After=graphical.target
Wants=graphical.target

[Service]
User=pi
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
Environment=KIVY_WINDOW=sdl2
Environment=KIVY_GL_BACKEND=sdl2
Environment=SDL_VIDEODRIVER=x11
Environment=DMC_KIOSK=1
ExecStart=/opt/dmcgui/venv/bin/python /opt/dmcgui/src/dmccodegui/main.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical.target
```

**Note on X11 vs Wayland:** Bookworm defaults to Wayfire (Wayland) but ships a compatible X11 session. Force X11 login via `raspi-config` → Advanced Options → Wayland → X11 on the target machine. The SDL KMSDRM driver has a documented garbage-display bug on RPi 5 with Wayland; `SDL_VIDEODRIVER=x11` in the unit file is a belt-and-suspenders guard.

---

## Screen Resolution Adaptation

### Strategy

Kivy freezes its display configuration on first `Window` import. Resolution detection and `Config.set()` calls must happen in a pre-Kivy block at the very top of `main.py`, before any other Kivy import. This is consistent with the existing project pattern (`Config.set before all Kivy imports` — already established in `main.py` per PROJECT.md key decisions).

```python
# TOP OF main.py — before ANY kivy imports

import os
import sys

def _configure_display():
    """Detect screen size and set Kivy window config before Window import."""
    try:
        from screeninfo import get_monitors
        monitors = get_monitors()
        primary = monitors[0] if monitors else None
    except Exception:
        primary = None

    # Manual override from settings.json takes priority over auto-detect
    # (checked here before settings module imports Kivy)
    try:
        import json
        with open('settings.json') as f:
            override = json.load(f).get('display_resolution')
        if override:
            w, h = override['width'], override['height']
            primary = type('M', (), {'width': w, 'height': h})()
    except Exception:
        pass

    from kivy.config import Config  # safe — doesn't import Window

    if primary:
        Config.set('graphics', 'width',  str(primary.width))
        Config.set('graphics', 'height', str(primary.height))

    # Kiosk fullscreen on Pi
    if os.environ.get('DMC_KIOSK') == '1':
        Config.set('graphics', 'fullscreen', 'auto')

    # Keyboard dock mode for small touchscreens
    if primary and primary.width <= 800:
        Config.set('kivy', 'keyboard_mode', 'systemanddock')

_configure_display()

# NOW safe to import kivy
from kivy.app import App
# ... rest of imports
```

### Display Profiles

| Profile | Resolution | Use case |
|---------|-----------|----------|
| 7 inch | 800×480 | Pi official touchscreen (small) |
| 10 inch | 1024×600 or 1280×800 | Pi touchscreen (medium) |
| 15 inch | 1920×1080 | Windows workstation or large Pi display |

The existing `dp`/`sp` layout (44dp touch targets already in use) scales correctly once window geometry is set. No widget-level changes are needed for resolution adaptation — only the pre-Kivy window size config.

---

## Key Kivy Packaging Gotchas

### KV Files Are Not Auto-Discovered

PyInstaller does not find `.kv` files through static analysis. Every `.kv` file must be in the `datas` list of the spec. Missing KV files produce a **blank screen with no error** — the worst kind of failure.

Use a glob in the spec: `('src/dmccodegui/ui/**/*.kv', 'dmccodegui/ui')`

### `_MEIPASS` Resource Path

The project already has this pattern (noted in PROJECT.md). Ensure `resource_add_path(sys._MEIPASS)` is called early in `main.py` when `hasattr(sys, '_MEIPASS')`, so Kivy's resource finder locates bundled KV files, fonts, and images.

### SDL2 DLL Load Order Bug (onefile only)

PyInstaller issue #3795: SDL2 DLLs extracted to `%TEMP%` can be found after system SDL2 if any system SDL2 exists, causing version conflicts. This is the primary reason to use **onedir, not onefile** for this project.

### Matplotlib Backend

Exclude Tkinter backends to avoid bundling Tkinter unnecessarily. Add to the Analysis `excludes` list:
```python
excludes=['tkinter', '_tkinter', 'matplotlib.backends.backend_tkagg', 'matplotlib.backends.backend_tk']
```

The app already uses the Kivy matplotlib widget which renders via Agg — no Tk backend is needed.

### kivy_matplotlib_widget KV Assets

This library ships its own `.kv` files. They are not in the main `src/` tree. Locate the installed package path and add a glob datas entry pointing to it, or the plot widget renders as an empty box.

### Fonts

If the app registers custom fonts via `LabelBase.register()` (already done for Roboto per project pattern), the font files must be in datas. Missing fonts cause silent fallback to a system font that may not exist on the target machine, resulting in invisible text.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| PyInstaller as bundler | HIGH | Official Kivy 2.3.1 docs, PyPI (version 6.19.0 confirmed current as of 2026-03) |
| Inno Setup as installer | HIGH | Version 6.7.1 confirmed on official downloads page; VS Code uses it |
| PyInstaller SDL2/GLEW Tree injection | HIGH | Documented in Kivy official packaging guide; consistent across Kivy 2.x |
| gclib DLL bundling — Windows | MEDIUM | ctypes path override via `GclibDllPath_` is documented; exact attribute names need verification against installed gclib version |
| gclib .deb on Pi | MEDIUM-HIGH | Galil officially documents Pi support and provides ARM packages; pip wrapper confirmed functional on Pi by Galil announcement |
| Pi systemd + X11 | MEDIUM-HIGH | Bookworm-specific pattern confirmed in Pi forums (February 2025 threads); Wayland avoidance confirmed by SDL GitHub issue |
| Wayland avoidance on Pi 5 | HIGH | SDL KMSDRM display corruption is an open confirmed bug on SDL GitHub (issue #8579), not speculation |
| PiWheels for Kivy on Bookworm | HIGH | Official Kivy docs explicitly cite PiWheels for Python 3.11 / Bookworm |
| screeninfo resolution detection | MEDIUM | Works on Windows and X11; behavior on Pi with HDMI-forced resolution (common for official Pi touchscreen at 800×480) needs validation on real hardware |
| onedir recommendation | HIGH | Multiple sources (PyInstaller docs, community) and the SDL2 DLL load order bug confirm onedir is correct for Kivy on Windows |

---

## Sources

- Kivy Windows packaging guide (2.3.1): https://kivy.org/doc/stable/guide/packaging-windows.html
- Kivy RPi installation guide (2.3.1): https://kivy.org/doc/stable/installation/installation-rpi.html
- Kivy environment variables: https://kivy.org/doc/stable/guide/environment.html
- Kivy Metrics / KIVY_DPI docs (2.3.1): https://kivy.org/doc/stable/api-kivy.metrics.html
- PyInstaller 6.19.0 install docs: https://pyinstaller.org/en/stable/installation.html
- PyInstaller changelog (version confirmed current): https://pyinstaller.org/en/stable/CHANGES.html
- PyInstaller DLL load order issue #3795: https://github.com/pyinstaller/pyinstaller/issues/3795
- Inno Setup downloads (6.7.1 confirmed): https://jrsoftware.org/isdl.php
- Galil gclib Raspberry Pi OS install docs: https://www.galil.com/sw/pub/all/doc/global/install/linux/rpios/
- Galil gclib DLL path documentation: https://www.galil.com/sw/pub/all/doc/gclib/html/classgclib.html
- SDL KMSDRM RPi 5 display bug (confirms Wayland avoidance): https://github.com/libsdl-org/SDL/issues/8579
- Raspberry Pi autostart / systemd Bookworm: https://raspberry.tips/en/raspberrypi-einsteiger/raspberry-pi-autostart-setup
- Pi Bookworm venv autostart forum (February 2025): https://forums.raspberrypi.com/viewtopic.php?t=384121
- screeninfo PyPI: https://pypi.org/project/screeninfo/
- PyInstaller vs cx_Freeze comparison: https://ahmedsyntax.com/cx-freeze-vs-pyinstaller/
- Kivy School PyInstaller instructions: https://kivyschool.com/pyinstaller-instructions/

---

*Stack research for: DMC Grinding GUI — v4.0 Packaging & Deployment*
*Researched: 2026-04-21*
