# Phase 24: Windows PyInstaller Bundle - Research

**Researched:** 2026-04-21
**Domain:** PyInstaller onedir packaging, Kivy 2.3.1 Windows bundling, gclib DLL vendoring, APPDATA persistence
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**App Identity & Naming**
- Canonical app name: Binh An HMI
- EXE filename: `BinhAnHMI.exe`
- APPDATA folder: `%APPDATA%/BinhAnHMI/`
- Window title: `Binh An HMI v4.0.0` (version included in title)
- Version source of truth: `__version__ = '4.0.0'` in `src/dmccodegui/__init__.py`
- Version appears in EXE file properties (WIN-07) and window title
- Custom placeholder icon generated during this phase (gear/grinder motif .ico)
- Window title change happens in Phase 24 (both frozen and dev builds show it)

**Data Persistence**
- Frozen builds: users.json and settings.json stored in `%APPDATA%/BinhAnHMI/`
- Dev mode (python -m dmccodegui): files stay local in `src/dmccodegui/auth/` as today
- Detection: standard `getattr(sys, 'frozen', False)` check
- First launch: auto-create default users (Admin/0000, Operator/1234, Setup/5678)
- settings.json: keep current first-launch machine type picker behavior
- Corrupt/missing files: auto-recreate defaults silently (no error dialog)
- Profile CSVs: remain import/export only, not stored in APPDATA

**gclib DLL Sourcing**
- 4 DLLs required: `gclib.dll`, `gclibo.dll`, `libcrypto-1_1-x64.dll`, `libssl-1_1-x64.dll`
- Source: `C:\Program Files (x86)\Galil\gclib\dll\x64\` (confirmed on dev machine)
- Vendor to: `deploy/windows/vendor/` in the repo (committed to git)
- Frozen startup: set `os.environ['GCLIB_ROOT']` to EXE directory before gclib import
- gclib.py: let PyInstaller collect from site-packages (not vendored)
- Build machine does NOT need Galil SDK installed (vendored DLLs are self-contained)

**Bundle Content Boundaries**
- Include: all 21 .kv files, 7 image assets (arrows + knife_demo.png), only 4 Noto Sans fonts (Regular, Bold, Italic, BoldItalic)
- Exclude: ~76 unused Noto Sans font variants, diagnostics screen (diagnostics.py + diagnostics.kv), .dmc files, .xlsx files, profile CSVs, .planning/, tests/, .md files
- Diagnostics screen is dev-only, strip from production build

### Claude's Discretion
- PyInstaller spec structure and hook configuration
- Hidden imports list for Kivy
- SDL2/GLEW tree collection approach
- Exact placeholder icon design
- `_get_data_dir()` function implementation details
- Build script (build_windows.bat) internals

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WIN-01 | App launches on a clean Windows 11 machine from PyInstaller onedir bundle — no pre-installed software required | PyInstaller 6.19 onedir spec, Kivy hookspath + SDL2/GLEW trees, hidden imports via get_deps_minimal() |
| WIN-02 | gclib DLL vendored in repo and bundled — app connects to Galil controller without Galil SDK on target | binaries= tuples in spec, GCLIB_ROOT env var set before gclib import, `deploy/windows/vendor/` dir |
| WIN-05 | users.json and settings.json stored in %APPDATA%/BinhAnHMI/, not in frozen temp — persists across restarts | `_get_data_dir()` helper with `getattr(sys, 'frozen', False)` check, os.makedirs exist_ok=True |
| WIN-07 | Version number visible in EXE file properties Details tab | version_file= in EXE() spec, VSVersionInfo Python file with filevers + StringStruct fields |
</phase_requirements>

---

## Summary

Packaging this Kivy 2.3.1 application with PyInstaller 6.19.0 on Windows requires three interlocking concerns that must be addressed in the correct order. First, the gclib DLL load chain in `gclib.py` uses `os.environ["GCLIB_ROOT"]` — this environment variable must be set to `sys._MEIPASS` (the `_internal/` folder in PyInstaller 6 onedir) before `gclib` is imported; the 4 DLLs must be in `_internal/dll/x64/` at runtime. Second, Kivy's SDL2 and GLEW dependency trees must be explicitly collected via `*[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)]` in the COLLECT step — omitting this causes a silent black window on launch. Third, mutable data files (users.json, settings.json) must redirect to `%APPDATA%/BinhAnHMI/` via `_get_data_dir()` before the App class initializes, because `sys._MEIPASS` is read-only temp storage.

PyInstaller 6.0 introduced a breaking structural change: all onedir support files now live in `_internal/` alongside the EXE (not in the same flat directory as in 5.x). `sys._MEIPASS` points to `_internal/`, NOT `os.path.dirname(sys.executable)`. The spec's `contents_directory='.'` parameter can revert to the old flat layout, but using `sys._MEIPASS` correctly is cleaner and more portable. The GCLIB_ROOT must be set to `sys._MEIPASS` (not `os.path.dirname(sys.executable)`) and the DLL binaries must land at `_internal/dll/x64/*.dll`.

The icon (WIN-07 covers .ico file properties, not just the icon graphic) requires a `version_file.txt` in VSVersionInfo format passed to PyInstaller's `EXE(version='...')` parameter. Pillow can generate the `.ico` file from a programmatically-drawn image using `img.save('BinhAnHMI.ico', format='ICO', sizes=[(16,16),(32,32),(48,48),(256,256)])`.

**Primary recommendation:** Use PyInstaller 6.19.0, `contents_directory` defaulting to `_internal`, set `GCLIB_ROOT = sys._MEIPASS` in frozen startup block, vendor all 4 DLLs under `deploy/windows/vendor/dll/x64/`, and use Kivy's `get_deps_minimal(window='sdl2')` for clean hidden imports.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pyinstaller | 6.19.0 (latest stable) | Bundle Python app to onedir EXE | De facto standard; Kivy docs target this |
| pyinstaller-hooks-contrib | latest (install together) | Community hooks for 3rd-party libs | Must stay in sync with pyinstaller version |
| kivy_deps.sdl2 | 0.8.0 (already installed) | SDL2 DLL binaries for Kivy window | Kivy's official Windows binary dep |
| kivy_deps.glew | 0.3.1 (already installed) | GLEW DLL binaries for OpenGL | Kivy's official Windows binary dep |
| Pillow | any (already in env) | Generate placeholder .ico from Python | No external tools needed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pyinstaller-versionfile | optional | YAML-to-VSVersionInfo generator | If version.txt hand-authoring is too brittle |
| kivy_deps.angle | 0.4.0 (already installed) | ANGLE OpenGL-on-D3D backend | Include in COLLECT Trees for fallback |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pyinstaller onedir | cx_Freeze | PyInstaller has native Kivy hooks; cx_Freeze needs manual config |
| pyinstaller onedir | Nuitka | Nuitka compiles to C; much slower build, no Kivy hook ecosystem |
| Pillow ico generation | Online converter / Photoshop | Programmatic generation is reproducible and repo-committable |
| version_file.txt | pyi-grab_version from cmd.exe | Hand-authoring is simpler for a known version string |

**Installation (on dev machine):**
```bash
pip install pyinstaller pyinstaller-hooks-contrib
```

---

## Architecture Patterns

### Recommended Project Structure

```
PythonDMCGUI/
├── deploy/
│   └── windows/
│       ├── vendor/
│       │   └── dll/
│       │       └── x64/
│       │           ├── gclib.dll
│       │           ├── gclibo.dll
│       │           ├── libcrypto-1_1-x64.dll
│       │           └── libssl-1_1-x64.dll
│       ├── BinhAnHMI.spec          # PyInstaller spec (Claude's discretion)
│       ├── version_file.txt        # VSVersionInfo for EXE properties (WIN-07)
│       ├── BinhAnHMI.ico           # Generated placeholder icon
│       ├── build_windows.bat       # Build script (Claude's discretion)
│       └── gen_icon.py             # One-shot script to generate .ico
└── src/
    └── dmccodegui/
        └── __init__.py             # Gains __version__ = '4.0.0'
```

### Pattern 1: Frozen-mode detection and APPDATA redirect

**What:** `_get_data_dir()` helper in `main.py` returns `%APPDATA%/BinhAnHMI/` when frozen, local `auth/` dir when running in dev. Must execute before `AuthManager` and `machine_config.init()` are called.

**When to use:** Called in `DMCApp.__init__` to derive users_path and settings_path.

**Implementation:**
```python
# Source: PyInstaller 6.19 runtime-information docs
import sys, os

def _get_data_dir() -> str:
    """Return writable data dir: APPDATA in frozen mode, local auth/ in dev."""
    if getattr(sys, 'frozen', False):
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        data_dir = os.path.join(appdata, 'BinhAnHMI')
    else:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auth')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir
```

### Pattern 2: GCLIB_ROOT pre-import patch

**What:** Set `os.environ['GCLIB_ROOT']` before `import gclib` is triggered. In frozen mode, `sys._MEIPASS` is the `_internal/` folder where the DLLs land. The DLLs must be stored at `_internal/dll/x64/*.dll` to match gclib.py's hardcoded path `GCLIB_ROOT + '/dll/x64/...'`.

**When to use:** At the very top of `main.py`, before any other import that could transitively import gclib.

**Implementation:**
```python
# Source: gclib.py source (confirmed line 29-32) + PyInstaller runtime docs
import sys, os

if getattr(sys, 'frozen', False):
    # sys._MEIPASS == the _internal/ folder in onedir mode (PyInstaller 6.x)
    os.environ['GCLIB_ROOT'] = sys._MEIPASS
# (In dev mode, GCLIB_ROOT is already set by Galil SDK installer)
```

**Critical detail:** The vendored DLLs must be placed at `deploy/windows/vendor/dll/x64/*.dll`. The spec binaries= entry must use destination `'dll/x64'` so they land at `_internal/dll/x64/` in the bundle, matching gclib.py's `GCLIB_ROOT + '/dll/x64/...'` path.

### Pattern 3: PyInstaller spec file for Kivy onedir

**What:** The `.spec` file for PyInstaller must explicitly collect SDL2 and GLEW Trees, use Kivy's hookspath, and list the 4 gclib DLLs in binaries=.

**Canonical spec structure (Claude's discretion for internals, but this is the mandatory shape):**
```python
# Source: Kivy 2.3.1 official packaging docs + PyInstaller 6.x spec docs
from kivy_deps import sdl2, glew, angle
from kivy.tools.packaging.pyinstaller_hooks import hookspath, runtime_hooks, get_deps_minimal

VENDOR_DIR = 'deploy/windows/vendor'

a = Analysis(
    ['src/dmccodegui/__main__.py'],
    pathex=['src'],
    binaries=[
        (f'{VENDOR_DIR}/dll/x64/gclib.dll',      'dll/x64'),
        (f'{VENDOR_DIR}/dll/x64/gclibo.dll',     'dll/x64'),
        (f'{VENDOR_DIR}/dll/x64/libcrypto-1_1-x64.dll', 'dll/x64'),
        (f'{VENDOR_DIR}/dll/x64/libssl-1_1-x64.dll',    'dll/x64'),
    ],
    datas=[
        ('src/dmccodegui/ui/*.kv',              'dmccodegui/ui'),
        ('src/dmccodegui/ui/flat_grind/*.kv',   'dmccodegui/ui/flat_grind'),
        ('src/dmccodegui/ui/serration/*.kv',    'dmccodegui/ui/serration'),
        ('src/dmccodegui/ui/convex/*.kv',       'dmccodegui/ui/convex'),
        ('src/dmccodegui/assets/images/*',      'dmccodegui/assets/images'),
        ('src/dmccodegui/assets/fonts/Noto_Sans/static/NotoSans-Regular.ttf',    'dmccodegui/assets/fonts/Noto_Sans/static'),
        ('src/dmccodegui/assets/fonts/Noto_Sans/static/NotoSans-Bold.ttf',       'dmccodegui/assets/fonts/Noto_Sans/static'),
        ('src/dmccodegui/assets/fonts/Noto_Sans/static/NotoSans-Italic.ttf',     'dmccodegui/assets/fonts/Noto_Sans/static'),
        ('src/dmccodegui/assets/fonts/Noto_Sans/static/NotoSans-BoldItalic.ttf', 'dmccodegui/assets/fonts/Noto_Sans/static'),
    ],
    hiddenimports=[
        'win32timezone',                     # kivy FileChooser dep
        'pkg_resources.py2_compat',
        'dmccodegui.screens.flat_grind',
        'dmccodegui.screens.serration',
        'dmccodegui.screens.convex',
    ],
    hookspath=hookspath(),
    runtime_hooks=runtime_hooks(),
    excludes=['dmccodegui.screens.diagnostics'],
    **get_deps_minimal(window='sdl2'),
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BinhAnHMI',
    icon='deploy/windows/BinhAnHMI.ico',
    version='deploy/windows/version_file.txt',
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)],
    strip=False,
    upx=False,
    name='BinhAnHMI',
)
```

**Note on `get_deps_minimal(window='sdl2')`:** Selects only the SDL2 window provider rather than all providers. This avoids bundling unused GStreamer/video/audio deps. The `audio=None, video=None` options further slim the bundle if needed.

### Pattern 4: Windows version_file.txt for EXE properties (WIN-07)

**What:** VSVersionInfo file in Python syntax passed to `EXE(version='...')`. Populates the Details tab in Windows Explorer Properties.

```python
# deploy/windows/version_file.txt
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(4, 0, 0, 0),
    prodvers=(4, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', 'Binh An'),
         StringStruct('FileDescription', 'Binh An HMI - Grinding Machine Controller'),
         StringStruct('FileVersion', '4.0.0.0'),
         StringStruct('InternalName', 'BinhAnHMI'),
         StringStruct('LegalCopyright', 'Copyright 2026 Binh An'),
         StringStruct('OriginalFilename', 'BinhAnHMI.exe'),
         StringStruct('ProductName', 'Binh An HMI'),
         StringStruct('ProductVersion', '4.0.0.0')])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
```

### Pattern 5: ICO generation with Pillow

**What:** One-shot Python script draws a placeholder gear motif and saves multi-resolution .ico.

```python
# deploy/windows/gen_icon.py
from PIL import Image, ImageDraw

def make_icon(path: str) -> None:
    sizes = [16, 32, 48, 256]
    images = []
    for s in sizes:
        img = Image.new('RGBA', (s, s), (30, 80, 150, 255))  # blue background
        draw = ImageDraw.Draw(img)
        # Simple gear-ish cross pattern
        cx, cy, r = s // 2, s // 2, s * 3 // 8
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 220, 0, 255), width=max(1, s // 16))
        images.append(img)
    images[0].save(path, format='ICO',
                   sizes=[(s, s) for s in sizes],
                   append_images=images[1:])

if __name__ == '__main__':
    make_icon('BinhAnHMI.ico')
    print('BinhAnHMI.ico written')
```

### Pattern 6: Window title and __version__

**What:** `__init__.py` gains `__version__` and `DMCApp.title` property returns the versioned name.

```python
# src/dmccodegui/__init__.py
__version__ = '4.0.0'
__all__ = ['main', 'app_state', 'controller']

# src/dmccodegui/main.py — in DMCApp class
from dmccodegui import __version__   # or relative: from . import __version__

class DMCApp(App):
    title = f'Binh An HMI v{__version__}'
    ...
```

**Important:** `App.title` is a Kivy StringProperty already defined on the base class. Assigning at class level works as a default; it can also be set in `__init__`.

### Anti-Patterns to Avoid

- **Using `os.path.dirname(sys.executable)` as `sys._MEIPASS` equivalent:** In PyInstaller 6.x onedir, `sys.executable` points to the EXE one level above `_internal/`. The two paths are NOT the same. Always use `sys._MEIPASS` for bundle-relative paths.
- **Placing DLL binaries destined to `'.'` in COLLECT:** gclib.py constructs the path as `GCLIB_ROOT + '/dll/x64/gclib.dll'`. If you set `GCLIB_ROOT = sys._MEIPASS` and place the DLLs at destination `'dll/x64'`, they land at `_internal/dll/x64/` — matching the constructed path. Destination `'.'` would put DLLs at `_internal/gclib.dll` which would not be found.
- **Including diagnostics.py in the frozen build:** It references dev-only code; excludes=['dmccodegui.screens.diagnostics'] and omitting diagnostics.kv from datas removes it cleanly.
- **Using `--onefile`:** Explicitly out of scope (REQUIREMENTS.md Out of Scope). SDL2 DLL extraction to temp dir and users.json being wiped on restart are both disqualifying.
- **Putting users.json or settings.json inside `sys._MEIPASS`:** `_internal/` is read-only in a deployed bundle (writes silently fail or require elevation). Always redirect to `%APPDATA%`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SDL2/GLEW DLL collection | Manual DLL copying | `*[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)]` in COLLECT | `kivy_deps.sdl2.dep_bins` is the canonical source of truth for which SDL2 DLLs are needed; manual selection misses transitive deps |
| Kivy hidden imports | Manually list every kivy.* module | `hookspath=hookspath(), **get_deps_minimal(window='sdl2')` | Kivy's own hook machinery resolves its provider graph; manual lists go stale with Kivy updates |
| EXE version metadata | Compute tuple from string | Write version_file.txt with matching filevers/prodvers tuples | Windows property page reads the FixedFileInfo binary structure; string-only approaches don't populate the "File version" field |
| ICO file creation | External tool or hand-crafted binary | `Pillow Image.save(..., format='ICO', sizes=[...])` | Reproducible, commit-friendly, no external toolchain |

**Key insight:** PyInstaller's Kivy hooks (`hookspath()` + `get_deps_minimal`) encapsulate hundreds of hours of community debugging about which modules Kivy loads indirectly. Using them means you inherit all that knowledge without maintaining a fragile hidden imports list.

---

## Common Pitfalls

### Pitfall C1 (confirmed from prior research): --onefile mode breaks SDL2
**What goes wrong:** SDL2 DLLs are extracted to a temp directory at launch, then Windows locks them; on second launch the temp path changes and DLL loading fails. Also, `sys._MEIPASS` is wiped on exit, so users.json is lost.
**Why it happens:** `--onefile` unpacks to `%TEMP%\_MEIxxxxxx` on every launch.
**How to avoid:** Use `--onedir` only. This is already locked in REQUIREMENTS.md as Out of Scope for onefile.
**Warning signs:** App works on first launch, fails on second; users disappear on restart.

### Pitfall C2 (confirmed from prior research): SDL2/GLEW Trees missing from spec
**What goes wrong:** Kivy window silently fails — app starts, but no window appears or a black window shows immediately.
**Why it happens:** `Analysis()` only collects Python modules and directly-referenced binaries. SDL2/GLEW DLLs are loaded by Kivy at runtime through the `kivy_deps.*` packages, which PyInstaller can't auto-detect.
**How to avoid:** Always add `*[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)]` to COLLECT, not to EXE.
**Warning signs:** App runs from source but frozen build shows no window.

### Pitfall C3 (new): PyInstaller 6.x _internal folder changes MEIPASS semantics
**What goes wrong:** Code using `os.path.dirname(sys.executable)` to find bundled files finds only the EXE; all data files are one level deeper in `_internal/`.
**Why it happens:** PyInstaller 6.0 moved support files from the EXE directory into `_internal/`. `sys._MEIPASS` correctly points to `_internal/`, but code written for PyInstaller 5.x used `dirname(sys.executable)`.
**How to avoid:** Always use `sys._MEIPASS` for frozen-mode path resolution. GCLIB_ROOT must be set to `sys._MEIPASS`, not `dirname(sys.executable)`.
**Warning signs:** `FileNotFoundError` for .kv files or fonts; gclib DLL not found despite existing in the bundle.

### Pitfall C4 (confirmed from prior research): gclib DLL not in spec binaries=
**What goes wrong:** `import gclib` succeeds (gclib.py is a pure Python file), but `gclib.py()` raises `OSError: [WinError 126] The specified module could not be found` because the ctypes WinDLL() call can't find `gclib.dll`.
**Why it happens:** PyInstaller's ctypes auto-detection only works for bare filenames and absolute paths resolved at analysis time. gclib.py constructs the path from `os.environ["GCLIB_ROOT"]` at runtime, so PyInstaller never sees it during analysis.
**How to avoid:** Explicitly list all 4 DLLs in `binaries=` in Analysis(). Set `GCLIB_ROOT = sys._MEIPASS` before import. Ensure destination is `'dll/x64'` so the path `sys._MEIPASS + '/dll/x64/gclib.dll'` resolves correctly.
**Warning signs:** "No controller" mode silently active; connection attempts immediately fail.

### Pitfall C5: KV files not found by Builder.load_file() in frozen build
**What goes wrong:** `FileNotFoundError` when Builder tries to load `ui/*.kv`. `os.path.dirname(__file__)` in frozen mode points to `_internal/dmccodegui/` — only if the package was installed correctly into `_internal/`.
**Why it happens:** `__file__` inside a frozen module points into `sys._MEIPASS/dmccodegui/`, but datas= in the spec must land files at matching subpaths. If the datas tuple destination doesn't match the `__file__`-relative path, Builder.load_file() fails.
**How to avoid:** The datas= destination `'dmccodegui/ui'` makes files land at `_internal/dmccodegui/ui/`. Since `os.path.dirname(__file__)` resolves to `_internal/dmccodegui/` in frozen mode, the existing code `os.path.join(os.path.dirname(__file__), kv)` finds them correctly with no modification.
**Warning signs:** App starts, passes PIN screen, then crashes with FileNotFoundError on a `.kv` file.

### Pitfall C6: Font path uses `__file__` — must verify frozen-mode resolution
**What goes wrong:** `_FONT_DIR` in main.py is `os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'fonts', 'Noto_Sans', 'static')`. In frozen mode `__file__` points to `_internal/dmccodegui/main.pyc`, so `_FONT_DIR` resolves to `_internal/dmccodegui/assets/fonts/Noto_Sans/static/` — which is exactly where the datas= entry will put the fonts. No code change needed, but the 4 font files MUST be listed in datas= with destination `'dmccodegui/assets/fonts/Noto_Sans/static'`.
**Warning signs:** Kivy shows default fallback font (DroidSans), Vietnamese characters missing.

### Pitfall C7: Kivy 2.3 + PyInstaller 6.5 selectImports breakage
**What goes wrong:** Build step fails with `AttributeError: module 'PyInstaller.depend.bindepend' has no attribute 'selectImports'` during Kivy hook execution.
**Why it happens:** Kivy's pyinstaller hooks referenced a PyInstaller internal API (`selectImports`) that was removed in PyInstaller 6.5.
**How to avoid:** Kivy 2.3.1 is confirmed to have fixed hooks that work with PyInstaller 6.x. However, keep `pyinstaller-hooks-contrib` up to date. If the error appears, downgrade to PyInstaller 6.4 or update Kivy hooks.
**Warning signs:** `AttributeError: ...bindepend... selectImports` during `pyinstaller BinhAnHMI.spec`.

### Pitfall C8: diagnostics.kv loaded at startup before excludes can take effect
**What goes wrong:** `KV_FILES` list in main.py includes `"ui/diagnostics.kv"`. If the kv is included in datas= but the Python class is excluded, Kivy's Builder will load the .kv and try to resolve the class name, causing NameError.
**Why it happens:** KV loading is done at build() time from a static list in code.
**How to avoid:** Remove `"ui/diagnostics.kv"` from `KV_FILES` in main.py AND exclude it from datas=. Since diagnostics.py is excluded via `excludes=`, removing the KV entry is safe. The screen won't appear in the frozen build.
**Warning signs:** `Builder.load_file` complains about missing class or the diagnostics tab appears in frozen build.

---

## Code Examples

### _get_data_dir() — complete implementation

```python
# Source: PyInstaller 6.19 runtime-information docs pattern
import sys
import os

def _get_data_dir() -> str:
    """Return writable directory for mutable data files.

    Frozen (PyInstaller onedir): %APPDATA%\\BinhAnHMI\\
    Dev (python -m dmccodegui):  src/dmccodegui/auth/  (unchanged from today)
    """
    if getattr(sys, 'frozen', False):
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        data_dir = os.path.join(appdata, 'BinhAnHMI')
    else:
        data_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'auth'
        )
    os.makedirs(data_dir, exist_ok=True)
    return data_dir
```

### Frozen startup block (top of main.py, before ALL imports)

```python
# Source: gclib.py lines 29-32 (confirmed) + PyInstaller runtime docs
import sys
import os

# Must be before ANY import that transitively imports gclib
if getattr(sys, 'frozen', False):
    os.environ['GCLIB_ROOT'] = sys._MEIPASS  # _internal/ in PyInstaller 6 onedir
```

### DMCApp.__init__ wiring to _get_data_dir()

```python
# Existing constructor in main.py — replace hardcoded auth/ paths:
def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.state = MachineState()
    self.controller = GalilController()
    # ... other inits ...
    data_dir = _get_data_dir()
    users_path = os.path.join(data_dir, 'users.json')
    self.auth_manager = AuthManager(users_path)
    settings_path = os.path.join(data_dir, 'settings.json')
    mc.init(settings_path)
```

### build_windows.bat (Claude's discretion — canonical shape)

```bat
@echo off
cd /d "%~dp0..\.."
python -m PyInstaller deploy\windows\BinhAnHMI.spec --clean --noconfirm
echo.
echo Build complete. Output: dist\BinhAnHMI\BinhAnHMI.exe
```

### Smoke test helper (not a pytest test — manual VM verification)

```
Smoke test checklist (run on clean Windows 11 VM):
1. Copy dist\BinhAnHMI\ folder to VM (no Python, no Galil SDK)
2. Run BinhAnHMI.exe — Kivy window must open and reach PIN login screen (WIN-01)
3. Enter controller IP — connection log must show same response as dev env (WIN-02)
4. Log in as Admin, create a new user, restart app — user must still exist (WIN-05)
5. Right-click BinhAnHMI.exe > Properties > Details — version 4.0.0.0 must appear (WIN-07)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| All onedir files flat next to EXE | Files go into `_internal/` subfolder, EXE at root | PyInstaller 6.0 (2023) | `os.path.dirname(sys.executable) != sys._MEIPASS` — must use `sys._MEIPASS` |
| `contents_directory` not configurable | `contents_directory='.'` reverts to flat layout | PyInstaller 6.1 | We will use default `_internal/` layout (cleaner) |
| Kivy hooks required GStreamer binaries | Kivy hook updated to remove selectImports dep | Kivy 2.3.1 | Hooks work with PyInstaller 6.x |
| KV files manually Tree()'d in COLLECT | `datas=` tuples in Analysis() (modern approach) | PyInstaller 4+ | Preferred: Analysis datas= is more explicit and composable |

**Deprecated/outdated:**
- `**get_deps_all()` in spec: Bundles unused GStreamer, camera, audio providers, bloating bundle by ~50MB. Use `get_deps_minimal(window='sdl2')` instead.
- `kivy.tools.packaging.pyinstaller_hooks.runtime_hooks()`: Still valid but the default PyInstaller hook for Kivy now ships with `pyinstaller-hooks-contrib`, so `hookspath()` is the critical call and `runtime_hooks()` may be optional depending on version.

---

## Open Questions

1. **`kivy_deps.angle` — include or skip?**
   - What we know: `kivy_deps.angle` 0.4.0 is installed. ANGLE provides OpenGL via Direct3D, useful as fallback on systems without proper OpenGL drivers (VM, some Intel iGPUs).
   - What's unclear: Whether `get_deps_minimal(window='sdl2')` includes ANGLE trees automatically or requires explicit `*[Tree(p) for p in angle.dep_bins]` in COLLECT.
   - Recommendation: Include `angle.dep_bins` in COLLECT Trees for robustness in VM smoke tests. The size cost is small (~3MB).

2. **`win32timezone` hidden import — still required for Kivy 2.3.1?**
   - What we know: It has been required by Kivy's FileChooser for years (pywin32 timezone data). Listed in community guides.
   - What's unclear: Whether Kivy 2.3.1 + `pyinstaller-hooks-contrib` auto-includes it.
   - Recommendation: Include it explicitly in hiddenimports= as insurance; it won't cause problems if redundant.

3. **`__main__.py` as Analysis entry point vs `main.py`**
   - What we know: `src/dmccodegui/__main__.py` exists (enables `python -m dmccodegui`). Using it as the spec entry point means PyInstaller starts from a predictable module boundary.
   - What's unclear: Whether the relative imports in `main.py` work correctly when PyInstaller traces from `__main__.py`.
   - Recommendation: Use `__main__.py` as the Analysis entry point; it's the intended package entry for the frozen build. Verify import tracing during first build attempt.

4. **Diagnostics screen removal — runtime KV list or code exclusion?**
   - What we know: `KV_FILES` in main.py includes `"ui/diagnostics.kv"`. The `screens/diagnostics.py` class is imported via the `screens` package `__init__`.
   - What's unclear: Whether `excludes=['dmccodegui.screens.diagnostics']` in Analysis() is sufficient or if the KV file reference in main.py causes a load error.
   - Recommendation: Remove `"ui/diagnostics.kv"` from `KV_FILES` in main.py AND from datas=. This cleanly removes diagnostics from both frozen and dev builds simultaneously (acceptable per CONTEXT.md which says "diagnostics is dev-only").

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already installed, tests/ directory active) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` testpaths = ["tests"] |
| Quick run command | `python -m pytest tests/test_auth_manager.py tests/test_machine_config.py -x -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| WIN-01 | App launches on clean Windows 11 from bundle | smoke/manual | VM checklist (see Code Examples above) | manual-only |
| WIN-02 | gclib DLL loads from bundle, controller connects | smoke/manual | VM checklist step 3 | manual-only |
| WIN-05 | users.json redirects to APPDATA in frozen mode | unit | `python -m pytest tests/test_auth_manager.py -x -q` | ✅ (existing, extend) |
| WIN-05 | _get_data_dir() returns APPDATA path when frozen | unit | `python -m pytest tests/test_data_dir.py -x -q` | ❌ Wave 0 gap |
| WIN-07 | version_file.txt matches __version__ == '4.0.0' | unit | `python -m pytest tests/test_version.py -x -q` | ❌ Wave 0 gap |
| WIN-07 | DMCApp.title contains 'Binh An HMI v4.0.0' | unit | part of test_version.py | ❌ Wave 0 gap |

**Note:** WIN-01 and WIN-02 are VM smoke tests by nature — they require a clean Windows 11 VM and physical Galil controller. They cannot be meaningfully automated as pytest unit tests. The smoke test checklist in Code Examples above is the verification protocol.

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_auth_manager.py tests/test_machine_config.py tests/test_data_dir.py tests/test_version.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_data_dir.py` — covers WIN-05: `_get_data_dir()` returns APPDATA path when `sys.frozen=True`, local auth/ path otherwise
- [ ] `tests/test_version.py` — covers WIN-07: `__version__ == '4.0.0'` in `__init__.py`, `DMCApp.title` contains version string

*(Existing test infrastructure covers auth_manager and machine_config — no gaps there)*

---

## Sources

### Primary (HIGH confidence)

- gclib.py source (confirmed locally at `C:\Users\danii\AppData\Local\Programs\Python\Python313\Lib\site-packages\gclib.py`) — DLL load pattern, GCLIB_ROOT env var usage, exact 4 DLL filenames confirmed
- Kivy 2.3.1 official packaging docs — https://kivy.org/doc/stable/guide/packaging-windows.html — hookspath(), SDL2/GLEW Trees, get_deps_minimal()
- Kivy pyinstaller_hooks API — https://kivy.org/doc/stable/api-kivy.tools.packaging.pyinstaller_hooks.html — get_deps_all(), get_deps_minimal() signatures
- PyInstaller 6.19.0 official docs — https://pyinstaller.org/en/stable/ — spec file format, binaries/datas tuples, version_file, sys._MEIPASS semantics in onedir
- PyInstaller 6.0 changelog — _internal/ folder introduction and contents_directory option
- pip show output (confirmed locally) — Kivy 2.3.1, kivy_deps.sdl2 0.8.0, kivy_deps.glew 0.3.1, kivy_deps.angle 0.4.0, Python 3.13.7

### Secondary (MEDIUM confidence)

- Kivy School PyInstaller tutorial — https://kivyschool.com/pyinstaller-instructions/ — confirmed SDL2/GLEW pattern, datas format
- DEV Community arhamrumi — https://dev.to/arhamrumi/adding-version-information-to-a-pyinstaller-onefile-executable-6n8 — VSVersionInfo file format
- GitHub kivy/kivy issue #8653 — confirmed PyInstaller 6.5.0 + Kivy 2.3.0 selectImports fix; Kivy 2.3.1 resolved

### Tertiary (LOW confidence, flagged for validation)

- Community claim that `win32timezone` is still required — verify during first build attempt
- `kivy_deps.angle` Trees being needed explicitly — verify during first build attempt

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions confirmed from local pip, gclib.py source inspected
- Architecture patterns: HIGH — gclib.py GCLIB_ROOT pattern confirmed from source; PyInstaller spec patterns from official Kivy and PyInstaller docs
- Pitfalls C1/C2: HIGH — from prior research, confirmed in REQUIREMENTS.md Out of Scope and official docs
- Pitfalls C3 (_internal/): HIGH — confirmed from PyInstaller 6.0 changelog + community sources
- Pitfalls C4 (gclib DLL): HIGH — gclib.py source inspected; ctypes detection limitation confirmed from PyInstaller docs
- Pitfalls C5-C8: MEDIUM — derived from code inspection + known PyInstaller/Kivy patterns

**Research date:** 2026-04-21
**Valid until:** 2026-07-21 (stable ecosystem — PyInstaller 6.x and Kivy 2.3.x are current stable; re-verify if either upgrades)
