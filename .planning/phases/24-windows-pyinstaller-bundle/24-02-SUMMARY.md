---
phase: 24-windows-pyinstaller-bundle
plan: "02"
subsystem: infra
tags: [pyinstaller, bundle, dlls, spec, icon, build-script]

# Dependency graph
requires:
  - "24-01: frozen-mode patches (_get_data_dir, GCLIB_ROOT, __version__, diagnostics exclusion)"
provides:
  - "deploy/windows/ build pipeline producing dist/BinhAnHMI/BinhAnHMI.exe"
  - "Vendored gclib DLLs in deploy/windows/vendor/dll/x64/"
  - "One-click build via deploy/windows/build_windows.bat"
affects:
  - "Phase 25 installer — packages the dist/BinhAnHMI/ folder"

# Tech tracking
tech-stack:
  added: [pyinstaller]
  patterns:
    - "SPECPATH-relative pathlib paths in .spec file for CWD-independent builds"
    - "get_deps_minimal() merge pattern to avoid duplicate kwargs in Analysis"
    - "Explicit KV file listing to exclude dev-only diagnostics.kv from bundle"

key-files:
  created:
    - deploy/windows/BinhAnHMI.spec
    - deploy/windows/version_file.txt
    - deploy/windows/gen_icon.py
    - deploy/windows/BinhAnHMI.ico
    - deploy/windows/build_windows.bat
    - deploy/windows/vendor/dll/x64/gclib.dll
    - deploy/windows/vendor/dll/x64/gclibo.dll
    - deploy/windows/vendor/dll/x64/libcrypto-1_1-x64.dll
    - deploy/windows/vendor/dll/x64/libssl-1_1-x64.dll
  modified:
    - src/dmccodegui/ui/base.kv
    - src/dmccodegui/screens/base.py
    - src/dmccodegui/screens/tab_bar.py
    - .gitignore

key-decisions:
  - "Vendored 4 gclib DLLs into repo rather than relying on system install — enables building on any machine"
  - "Used SPECPATH-relative pathlib.Path in spec since PyInstaller 6.x resolves from spec dir, not CWD"
  - "Merged get_deps_minimal() with app-specific hiddenimports/excludes/binaries to avoid duplicate kwargs"
  - "Explicit KV file list instead of glob to cleanly exclude diagnostics.kv from production bundle"
  - "Added kivy_matplotlib_widget NavigationIcons.ttf to datas — package registers it at import time"

patterns-established:
  - "Build pipeline lives in deploy/windows/ — spec, icon, version, build script, vendored DLLs"
  - "dist/ and build/ are gitignored — only deploy/ infrastructure is committed"

requirements-completed: [WIN-01, WIN-02, WIN-07]

# Metrics
duration: 25min
completed: 2026-04-21
---

# Phase 24 Plan 02: PyInstaller Build Pipeline Summary

**Complete Windows build pipeline: vendored DLLs, .spec file, icon, version metadata, build script — producing working BinhAnHMI.exe verified by human launch test**

## Performance

- **Duration:** ~25 min (including two rebuild cycles for launch fixes)
- **Completed:** 2026-04-21
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint)
- **Files created:** 9
- **Files modified:** 4

## Accomplishments
- 4 gclib DLLs vendored into `deploy/windows/vendor/dll/x64/` and committed to repo
- PyInstaller `.spec` file with Kivy hooks (SDL2, GLEW, ANGLE), gclib binaries, 20 KV files, 7 images, 4 fonts, kivy_matplotlib_widget font
- VSVersionInfo `version_file.txt` embedding version 4.0.0.0 in EXE properties
- Multi-resolution gear icon generated via Pillow script (`gen_icon.py`)
- One-click `build_windows.bat` that resolves to repo root and runs PyInstaller
- `dist/BinhAnHMI/BinhAnHMI.exe` (11.4 MB) launches and shows Kivy window with correct title
- Human verified: window title "Binh An HMI v4.0.0", EXE properties show version 4.0.0.0

## Task Commits

1. **Task 1: Vendor DLLs, spec file, version file, icon, build script** — `7b04e9b` (feat)
2. **Fix: Exclude DiagnosticsScreen + add NavigationIcons.ttf** — `fb94ded` (fix)
3. **Task 2: Human verification** — approved (EXE launches, correct title and version)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing kivy_matplotlib_widget font**
- **Found during:** Human launch test
- **Issue:** `kivy_matplotlib_widget.__init__` registers `NavigationIcons.ttf` at import time; PyInstaller collected the Python code but not the font data file
- **Fix:** Added `kivy_matplotlib_widget/fonts/NavigationIcons.ttf` to spec datas
- **Files modified:** `deploy/windows/BinhAnHMI.spec`

**2. [Rule 1 - Bug] DiagnosticsScreen FactoryException in production**
- **Found during:** Human launch test (second crash)
- **Issue:** Plan 24-01 removed DiagnosticsScreen from Python imports but `base.kv` still instantiated it in the ScreenManager, and `tab_bar.py`/`base.py` still referenced it
- **Fix:** Removed DiagnosticsScreen from `base.kv`, `base.py._SETUP_SCREENS`, `tab_bar.py.ALL_TABS` and `ROLE_TABS`. Switched spec from `*.kv` glob to explicit file list excluding `diagnostics.kv`
- **Files modified:** `src/dmccodegui/ui/base.kv`, `src/dmccodegui/screens/base.py`, `src/dmccodegui/screens/tab_bar.py`, `deploy/windows/BinhAnHMI.spec`

---

**Total deviations:** 2 auto-fixed (both Rule 1 — missing bundle data)
**Impact on plan:** Two additional files modified beyond plan scope (base.kv, base.py, tab_bar.py) to complete diagnostics exclusion. Rebuild required.

## Issues Encountered
- `dist/` directory lock on rebuild — previous EXE launch held file handles; required closing before `--clean` could proceed
- 1 pre-existing test failure (`test_axes_setup::test_enter_setup_skips_fire_when_already_setup`) — not caused by this plan

## User Setup Required
None.

## Next Phase Readiness
- `dist/BinhAnHMI/` folder is ready for packaging into an installer (Phase 25)
- Build pipeline is one-click reproducible via `deploy/windows/build_windows.bat`

---
*Phase: 24-windows-pyinstaller-bundle*
*Completed: 2026-04-21*
