# Architecture Patterns: Packaging & Deployment

**Domain:** Python/Kivy industrial HMI — packaging and deployment layer
**Researched:** 2026-04-21
**Confidence:** HIGH for directory structure and integration points (derived from actual codebase). MEDIUM for gclib DLL specifics (WebSearch verified against Galil docs). HIGH for Kivy PyInstaller spec structure (official Kivy docs confirmed).

---

## Recommended Architecture

The packaging/deployment layer is a build-time and runtime-setup concern that sits entirely outside the Python package at `src/dmccodegui/`. It never modifies the application source. It consists of three silos:

```
PythonDMCGUI/                    ← project root
  src/dmccodegui/                ← APPLICATION (do not modify for packaging)
  build/                         ← NEW: build artifacts (gitignored)
    windows/
      dist/                      ← PyInstaller output
    pi/
  deploy/                        ← NEW: build scripts and installer sources
    windows/
      dmccodegui.spec            ← PyInstaller spec
      installer.iss              ← Inno Setup script
      build_windows.bat          ← one-shot build driver
    pi/
      install.sh                 ← venv setup + systemd install
      dmccodegui.service         ← systemd unit file
      build_sdcard.sh            ← optional: rpi-imager customization hook
  profiles/                      ← existing: CSV profiles (bundled separately)
  .planning/                     ← never packaged
  tests/                         ← never packaged
  *.dmc  *.xlsx  *.csv           ← never packaged (optional separate bundle)
```

**Rule:** The `deploy/` tree is pure scaffolding — shell scripts, spec files, ini files. It imports nothing from `src/`. It references the built artifacts in `build/`. It is committed to git but never included in any installer payload.

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `deploy/windows/dmccodegui.spec` | Describes what PyInstaller bundles: entry point, datas (kv files, assets, fonts), binaries (gclib.dll), hidden imports (kivy hooks), excludes | PyInstaller tool at build time |
| `deploy/windows/installer.iss` | Inno Setup script: copies `build/windows/dist/` to `C:\Program Files\`, creates Start Menu + Desktop shortcuts, optionally adds Run key for auto-start | Inno Setup compiler at packaging time |
| `deploy/windows/build_windows.bat` | Runs PyInstaller then Inno Setup in sequence. Single command a developer runs. | Calls PyInstaller, calls ISCC.exe |
| `deploy/pi/install.sh` | Creates `/opt/dmccodegui/` directory, creates venv, pip-installs all dependencies including gclib .whl, copies systemd unit, enables and starts the service | Bash + pip + systemctl on target Pi |
| `deploy/pi/dmccodegui.service` | systemd unit that launches the Kivy app fullscreen on boot. Sets DISPLAY, XAUTHORITY, handles restart. | systemd on target Pi |
| `src/dmccodegui/main.py` | Existing entry point. Gets a new startup hook: read `settings.json` for `display_size` key, call `Config.set('graphics', 'width')` / `height` before `Window` import if override is set. | Kivy Config (must precede Window import) |

---

## Build Flow: Source to Package to Install to Run

### Windows Path

```
1. Developer machine (Windows 11)
   └── python -m PyInstaller deploy/windows/dmccodegui.spec
       ├── Collects: src/dmccodegui/** (all .py)
       ├── Datas:    ui/**/*.kv → ui/
       │             assets/fonts/** → assets/fonts/
       │             assets/images/** → assets/images/
       │             auth/users.json → auth/
       │             auth/settings.json → auth/
       ├── Binaries: gclib.dll (from %GCLIB_ROOT%\dll\x64\) → .
       │             gcaps.exe (gclib connection broker) → .
       ├── Hidden imports: kivy, kivy.core.window, kivy.core.text
       │             kivy._event, kivy.graphics, etc.
       └── Output: build/windows/dist/dmccodegui/

2. Developer machine
   └── ISCC.exe deploy/windows/installer.iss
       ├── Source: build/windows/dist/dmccodegui/
       ├── Output: build/windows/DMCCodeGUI_v4.0_Setup.exe
       └── Creates: Start Menu shortcut, optional Desktop shortcut,
                    optional HKCU Run key for auto-start on login

3. Target Windows machine
   └── Run DMCCodeGUI_v4.0_Setup.exe
       ├── Installs to: C:\Program Files\DMCCodeGUI\
       ├── No Python required on target
       ├── No Galil gclib installer required on target (DLL is bundled)
       └── gcaps.exe bundled — no separate gcaps installation needed
```

### Raspberry Pi Path

```
1. Delivery method A: git clone
   git clone <repo> /opt/dmccodegui
   cd /opt/dmccodegui
   bash deploy/pi/install.sh

2. Delivery method B: USB/SCP folder
   scp -r PythonDMCGUI/ pi@<ip>:/opt/dmccodegui/
   ssh pi@<ip> "bash /opt/dmccodegui/deploy/pi/install.sh"

3. Delivery method C: SD card image
   Build once with method A, then dd the card or use rpi-imager

install.sh steps (in order):
   a. sudo apt-get install -y python3-venv python3-dev libsdl2-dev libgl1-mesa-dev
   b. Install Galil .deb package (libgalil) BEFORE creating venv
         — libgalil.so.2.0 installs to /usr/lib; ldconfig creates symlinks
   c. python3 -m venv /opt/dmccodegui/.venv
   d. .venv/bin/pip install kivy matplotlib kivy_matplotlib_widget
   e. .venv/bin/pip install https://www.galil.com/sw/pub/python/gclib-1.0.1-py3-none-any.whl
   f. cp deploy/pi/dmccodegui.service /etc/systemd/system/
   g. systemctl daemon-reload
   h. systemctl enable dmccodegui
   i. systemctl start dmccodegui
```

---

## Integration Points With Existing App

### 1. gclib .dll Discovery on Windows (PyInstaller)

gclib's Python wrapper loads the underlying C library via `ctypes.CDLL`. The wrapper resolves the path from:
- The `GCLIB_ROOT` environment variable (modern builds): `%GCLIB_ROOT%\dll\x64\gclib.dll`
- Fallback hardcoded path: `C:\Program Files (x86)\Galil\gclib\dll\x64\gclib.dll`

When PyInstaller bundles the app, neither of these paths exists on the target machine. The spec file must copy `gclib.dll` and `gcaps.exe` into the bundle root (`.`), and `main.py` must set `os.environ["GCLIB_ROOT"]` to `sys._MEIPASS` before the gclib import resolves.

**Integration point in `main.py` — must be the very first lines, before any import:**

```python
import sys, os
if getattr(sys, 'frozen', False):          # running as PyInstaller bundle
    os.environ["GCLIB_ROOT"] = sys._MEIPASS
```

This is safe because `controller.py` already guards gclib import with `try/except ImportError` — no behavior change in dev mode.

### 2. gclib .so Discovery on Raspberry Pi (venv)

On Pi, the Galil installer copies `libgalil.so.2.0` to `/usr/lib` and creates symlinks (`libgalil.so.2`, `libgalil.so`) via ldconfig. The gclib Python pip package wrapper resolves the .so from the system library path — the venv's Python will find it via ldconfig as long as the Galil package was installed system-wide before creating the venv.

**install.sh must install the Galil .deb package before creating the venv**, not after. The order in install.sh is: `apt-get install libgalil` (or equivalent) first, then `python3 -m venv`, then `pip install gclib`.

No application code changes needed for Pi. The `try/except ImportError` guard in `controller.py` already handles the absence of gclib gracefully.

### 3. KV and Asset Path Resolution (PyInstaller)

`main.py` already uses `os.path.dirname(os.path.abspath(__file__))` to build all asset paths. Under PyInstaller, `__file__` inside a frozen module resolves to `sys._MEIPASS/<module_path>`, so relative paths from `__file__` work without modification.

The `resource_add_path` call in `build()` resolves correctly under PyInstaller because `assets/images/` is copied into the bundle by the spec file's `datas` list. No change required to that call.

### 4. users.json and settings.json (Mutable Runtime Data)

Both `auth/users.json` and `auth/settings.json` are inside the package tree and opened at absolute paths derived from `__file__`. Under PyInstaller, `sys._MEIPASS` is a read-only temp directory extracted fresh on each launch. Any writes to that directory are silently discarded.

**Required change:** `DMCApp.__init__` in `main.py` must redirect these paths to a writable location when frozen:

```python
if getattr(sys, 'frozen', False):
    _data_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')),
                             'DMCCodeGUI')
else:
    _data_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(_data_dir, 'auth'), exist_ok=True)
users_path = os.path.join(_data_dir, 'auth', 'users.json')
settings_path = os.path.join(_data_dir, 'auth', 'settings.json')
```

The installer (Inno Setup) must also copy the seed `users.json` and `settings.json` from the bundle to `{userappdata}\DMCCodeGUI\auth\` on first install, so defaults exist before first launch.

On Pi (non-frozen), paths stay as-is under `/opt/dmccodegui/src/dmccodegui/auth/` which is writable.

### 5. Screen Resolution Detection

Kivy's resolution system is finalized at `Window` import time. The sequence in `main.py` is already correct — Config.set calls come before the Window import (lines 9–16 of current main.py). The resolution detection hook must fit into the same module-level block.

**Data flow:**

```
app start
  → _load_display_config() reads settings.json with stdlib json (no Kivy yet)
  → if settings.json has "display_size" key:
       map preset string to width/height
       Config.set('graphics', 'width', w)
       Config.set('graphics', 'height', h)
       if "kiosk": Config.set('graphics', 'fullscreen', 'auto')
  → else:
       keep existing defaults (1920x1080 on Windows, manual override for Pi)
  → from kivy.core.window import Window  ← geometry now frozen
  → DMCApp.build() → normal flow
  → first-run: if no display_size in settings.json, show picker in setup screen,
                write choice to settings.json, inform user to restart
```

**Where in startup flow:** A `_load_display_config()` function is called at module level in `main.py` after the `os.environ` block but before `from kivy.config import Config`. It reads only `settings.json["display_size"]` using stdlib `json`. It returns a `(w, h, fullscreen)` tuple that drives `Config.set` calls. On Pi in kiosk mode, the install.sh should pre-write `"display_size": "kiosk"` into `settings.json` so the app boots fullscreen from first launch.

**Supported presets:**

| Display | Resolution | settings.json value |
|---------|-----------|---------------------|
| Windows default | 1920x1080 | (key absent) |
| 7" Pi touchscreen | 800x480 | `"7inch"` |
| 10" Pi touchscreen | 1024x600 | `"10inch"` |
| 15" Pi touchscreen | 1280x800 | `"15inch"` |
| Pi kiosk (any size) | fullscreen=auto | `"kiosk"` |
| Custom | WxH | `"1280x720"` (parsed directly) |

---

## File Exclusion Strategy

### What Gets Bundled vs What Doesn't

| Path | Windows bundle | Pi deployment | Notes |
|------|---------------|---------------|-------|
| `src/dmccodegui/**/*.py` | YES | YES | All application code |
| `src/dmccodegui/ui/**/*.kv` | YES (datas) | YES | All KV layout files |
| `src/dmccodegui/assets/` | YES (datas) | YES | Fonts, images |
| `src/dmccodegui/auth/users.json` | YES (seed, to APPDATA) | YES | Writable at runtime |
| `src/dmccodegui/auth/settings.json` | YES (seed, to APPDATA) | YES | Writable at runtime |
| `profiles/` | YES | YES | CSV profiles, operator data |
| `deploy/` | NO | NO (already present on Pi) | Build scripts only |
| `tests/` | NO | NO | Dev artifacts |
| `.planning/` | NO | NO | Dev artifacts |
| `docs/` | NO | NO | Dev documentation |
| `*.dmc` | NO | NO | Separate optional setup bundle |
| `*.xlsx`, `*.csv` (root) | NO | NO | Separate optional setup bundle |
| `README.md`, `*.md` | NO | NO | Not end-user content |
| `pyproject.toml`, `environment.yml` | NO | NO | Dev tooling |

### PyInstaller spec excludes (reduces bundle size ~50%)

```python
excludes=['pytest', 'unittest', 'doctest', 'pdb', 'pydoc',
          'tkinter', 'IPython', 'notebook', 'email', 'http',
          'xmlrpc', 'ftplib', 'imaplib', 'poplib']
```

---

## Suggested Build Order (Dependencies)

```
Phase A: PyInstaller spec (Windows)
  Depends on: working PyInstaller + Kivy install on dev machine
  Output: spec file that produces a working frozen exe
  Gate: launch frozen exe on clean Windows VM without Python installed

Phase B: gclib.dll discovery fix in main.py
  Depends on: Phase A (need frozen exe to test against)
  Output: sys._MEIPASS / GCLIB_ROOT env var set at top of main.py
  Gate: frozen exe opens a Galil connection successfully

Phase C: mutable data path fix (APPDATA redirect)
  Depends on: Phase A (need frozen context to test path logic)
  Output: users.json / settings.json redirected to APPDATA when frozen
  Gate: user accounts persist across launches of the frozen exe

Phase D: Inno Setup installer script
  Depends on: Phase A + B + C (need a working frozen dist/ tree)
  Output: DMCCodeGUI_vX.X_Setup.exe
  Gate: clean-install on Windows 11 VM, app launches, connects to controller

Phase E: Screen resolution detection
  Depends on: Phase C (settings.json path must be stable before adding new keys)
  Output: _load_display_config() in main.py, picker UI in setup screen or first-run modal
  Gate: "7inch" in settings.json produces 800x480 window at launch

Phase F: Pi install.sh + systemd unit
  Depends on: nothing on Windows side (parallel track)
  Output: install.sh, dmccodegui.service
  Gate: fresh Pi boots directly into fullscreen app, no desktop visible
```

Phases A through E are sequential. Phase F is independent and can proceed in parallel.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Shipping gclib installer as prerequisite on target Windows machine
**What goes wrong:** End-user must install Galil software before running the HMI. On a locked-down industrial machine this may require IT intervention or may be impossible.
**Instead:** Bundle gclib.dll and gcaps.exe directly in the PyInstaller `binaries=` list. The DLL is redistributable per Galil's license terms.

### Anti-Pattern 2: Shipping users.json inside sys._MEIPASS without APPDATA redirect
**What goes wrong:** PyInstaller extracts `_MEIPASS` to a temp directory on each launch. Any user accounts created at runtime are silently discarded on exit.
**Instead:** Copy the seed `users.json` to `APPDATA/DMCCodeGUI/auth/` on first run (if not present). All runtime reads/writes go to APPDATA, never to `_MEIPASS`.

### Anti-Pattern 3: Setting Config.set inside DMCApp.build() for window geometry
**What goes wrong:** Kivy freezes window geometry on first `Window` import, which happens long before `build()` is called. Any `Config.set('graphics', ...)` calls inside `build()` are silently ignored.
**Instead:** Resolution config must happen at module level in `main.py`, before `from kivy.core.window import Window` — exactly where the existing `Config.set` calls already live (lines 9–16 of current main.py).

### Anti-Pattern 4: Pi systemd service targeting graphical.target without DISPLAY set
**What goes wrong:** `graphical.target` does not guarantee X11 is running. The Kivy SDL2 backend cannot open a display without `DISPLAY=:0` in the environment.
**Instead:** Set `Environment=DISPLAY=:0` and `Environment=XAUTHORITY=/home/pi/.Xauthority` in the unit file. Use `After=display-manager.service` rather than `graphical.target`.

### Anti-Pattern 5: Installing Galil .deb after creating the venv on Pi
**What goes wrong:** The gclib Python pip package uses ctypes to find `libgalil.so` via ldconfig at pip-install time. If the shared library is not on the system path when pip runs, the wrapper silently falls back to no-op or fails to bind — resulting in `GCLIB_AVAILABLE = False` at runtime even though the library is later installed.
**Instead:** Galil .deb installation is step (b) in `install.sh`, before `python3 -m venv` at step (c).

### Anti-Pattern 6: Placing deploy/ scripts inside src/dmccodegui/
**What goes wrong:** PyInstaller's auto-collect will pick up .sh and .iss files as datas and bundle them. They add no runtime value and inflate bundle size.
**Instead:** Keep `deploy/` at the project root, never inside `src/`.

---

## Scalability Considerations

This is a single-machine kiosk deployment. Scaling concerns are operational:

| Concern | Approach |
|---------|----------|
| New Pi machine | Run `install.sh` on it. Machine type auto-detects from controller on first boot. |
| App update on Pi | `git pull && systemctl restart dmccodegui`. No reinstall. |
| App update on Windows | Re-run installer. Inno Setup upgrades in-place. APPDATA data preserved. |
| SD card duplication | Image one configured Pi, dd to new cards. Machine type auto-detects on each new controller. |

---

## Sources

- Galil gclib Python wrapper (ctypes CDLL path pattern): [gclib source](https://www.galil.com/sw/pub/all/doc/gclib/html/gclib_8py_source.html)
- Galil Raspberry Pi OS installation (libgalil.so to /usr/lib): [Galil RPi OS Install](https://www.galil.com/sw/pub/all/doc/global/install/linux/rpios/)
- Galil gclib pip wheel URL: `py -m pip install https://www.galil.com/sw/pub/python/gclib-1.0.1-py3-none-any.whl` (from [gclib Downloads](https://www.galil.com/sw/pub/all/rn/gclib.html))
- Kivy Windows packaging (spec file structure, sdl2.dep_bins, Tree): [Kivy Packaging Windows](https://kivy.org/doc/stable/guide/packaging-windows.html)
- Kivy metrics and DPI/density system: [Kivy Metrics](https://kivy.org/doc/stable/api-kivy.metrics.html)
- Kivy Window API (system_size, size): [Kivy Window](https://kivy.org/doc/stable/api-kivy.core.window.html)
- PyInstaller spec file binaries= and datas= format: [PyInstaller Spec Files](https://pyinstaller.org/en/stable/spec-files.html)
- Inno Setup shortcut + Start Menu structure: [Inno Setup](https://jrsoftware.org/isinfo.php)
- Kivy RPi installation: [Kivy RPi docs](https://kivy.org/doc/stable/installation/installation-rpi.html)
