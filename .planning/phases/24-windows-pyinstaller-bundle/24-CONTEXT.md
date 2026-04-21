# Phase 24: Windows PyInstaller Bundle - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Package the working HMI into a self-contained PyInstaller onedir bundle for Windows 11. Python, all dependencies, and the gclib DLLs are included. Mutable user data (users.json, settings.json) persists across restarts via %APPDATA%. The frozen build passes a clean-VM smoke test. No installer (Phase 25), no Pi (Phase 26), no logging (Phase 28).

</domain>

<decisions>
## Implementation Decisions

### App Identity & Naming
- Canonical app name: **Binh An HMI**
- EXE filename: `BinhAnHMI.exe`
- APPDATA folder: `%APPDATA%/BinhAnHMI/`
- Window title: `Binh An HMI v4.0.0` (version included in title)
- Version source of truth: `__version__ = '4.0.0'` in `src/dmccodegui/__init__.py`
- Version appears in EXE file properties (WIN-07) and window title
- Custom placeholder icon generated during this phase (gear/grinder motif .ico)
- Window title change happens in Phase 24 (both frozen and dev builds show it)

### Data Persistence
- **Frozen builds:** users.json and settings.json stored in `%APPDATA%/BinhAnHMI/`
- **Dev mode (python -m dmccodegui):** files stay local in `src/dmccodegui/auth/` as today
- Detection: standard `getattr(sys, 'frozen', False)` check
- First launch: auto-create default users (Admin/0000, Operator/1234, Setup/5678)
- settings.json: keep current first-launch machine type picker behavior
- Corrupt/missing files: auto-recreate defaults silently (no error dialog)
- Profile CSVs: remain import/export only, not stored in APPDATA

### gclib DLL Sourcing
- 4 DLLs required: `gclib.dll`, `gclibo.dll`, `libcrypto-1_1-x64.dll`, `libssl-1_1-x64.dll`
- Source: `C:\Program Files (x86)\Galil\gclib\dll\x64\` (confirmed on dev machine)
- Vendor to: `deploy/windows/vendor/` in the repo (committed to git)
- Frozen startup: set `os.environ['GCLIB_ROOT']` to EXE directory before gclib import
- gclib.py: let PyInstaller collect from site-packages (not vendored)
- Build machine does NOT need Galil SDK installed (vendored DLLs are self-contained)

### Bundle Content Boundaries
- **Include:** all 21 .kv files, 7 image assets (arrows + knife_demo.png), only 4 Noto Sans fonts (Regular, Bold, Italic, BoldItalic)
- **Exclude:** ~76 unused Noto Sans font variants, diagnostics screen (diagnostics.py + diagnostics.kv), .dmc files, .xlsx files, profile CSVs, .planning/, tests/, .md files
- Diagnostics screen is dev-only, strip from production build

### Claude's Discretion
- PyInstaller spec structure and hook configuration
- Hidden imports list for Kivy
- SDL2/GLEW tree collection approach
- Exact placeholder icon design
- `_get_data_dir()` function implementation details
- Build script (build_windows.bat) internals

</decisions>

<specifics>
## Specific Ideas

- gclib.py loads DLLs via `WinDLL(os.environ["GCLIB_ROOT"] + '/dll/x64/...')` — patching GCLIB_ROOT is the cleanest approach (no modification to gclib.py needed)
- The app currently does `try: import gclib` with fallback to None — this pattern should work in frozen builds as long as DLLs are findable
- Research identified critical pitfall C1 (onefile mode breaks SDL2) and C2 (SDL2/GLEW trees missing) — both inform spec design

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `controller.py`: gclib import with try/except fallback (lines 14-28) — frozen mode GCLIB_ROOT patch must execute before this import
- `main.py`: Config.set block before Window import (lines 9-15) — established pattern for pre-import configuration
- `auth/auth_manager.py`: takes `users_path` as constructor arg — path redirect just changes what's passed in
- `machine_config.py`: takes `settings_path` parameter — same redirect pattern

### Established Patterns
- Pre-import configuration: Config.set calls before Kivy Window import in main.py — GCLIB_ROOT and APPDATA setup follows this pattern
- Font registration: `_FONT_DIR` uses `os.path.dirname(os.path.abspath(__file__))` — needs frozen-mode equivalent using `sys._MEIPASS` or EXE dir
- Relative imports with fallback: main.py lines 42-60 do `try: from .module` / `except: from dmccodegui.module` — frozen build uses the package form

### Integration Points
- `main.py` build() method (line ~125-131): passes hardcoded `auth/users.json` and `auth/settings.json` paths — this is where `_get_data_dir()` redirect plugs in
- `__init__.py`: currently empty — will gain `__version__ = '4.0.0'`
- New files: `deploy/windows/dmccodegui.spec`, `deploy/windows/vendor/*.dll`, `deploy/windows/build_windows.bat`
- App class `title` property: needs to return `f'Binh An HMI v{__version__}'`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 24-windows-pyinstaller-bundle*
*Context gathered: 2026-04-21*
