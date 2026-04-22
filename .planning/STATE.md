---
gsd_state_version: 1.0
milestone: v4.0
milestone_name: Packaging & Deployment
status: unknown
stopped_at: Completed 26-02-PLAN.md
last_updated: "2026-04-22T01:30:52.597Z"
last_activity: 2026-04-22 — Phase 26 Plan 01 complete (Linux data-dir branch + deploy/pi/ skeleton)
progress:
  total_phases: 22
  completed_phases: 3
  total_plans: 6
  completed_plans: 7
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-21)

**Core value:** An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion, zero access to things they shouldn't touch.
**Current focus:** v4.0 — Phase 26 complete; Phase 27 (Screen Resolution Detection) next

## Current Position

```
Milestone : v4.0 Packaging & Deployment
Phase     : 26 of 29 (Pi OS Preparation and Install Script) — Complete
Plan      : 2 of 2 complete
Status    : 26-01 done (Linux data-dir + deploy/pi/ skeleton); 26-02 done (install.sh + tests)
Progress  : [██████████] 100%
```

Last activity: 2026-04-22 — Phase 26 Plan 02 complete (install.sh + 18 content-inspection tests)

## v4.0 Phase Map

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 24 | Windows PyInstaller Bundle | WIN-01, WIN-02, WIN-05, WIN-07 | **Complete** |
| 25 | Windows Inno Setup Installer | WIN-03, WIN-04, WIN-06 | **Complete** |
| 26 | Pi OS Preparation and Install Script | PI-01 through PI-05, PI-07 | **Complete** |
| 27 | Screen Resolution Detection | APP-04 | Not started |
| 28 | Logging Infrastructure | APP-01, APP-02, APP-03 | Not started |
| 29 | Integration Testing and Field Validation | FIX-02, PI-06 | Not started |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
v1.0-v3.0 phase-level decisions archived in `.planning/milestones/`.

Decisions affecting current work (v4.0):
- PyInstaller onedir mode only — onefile breaks SDL2 DLL and wipes users.json on every launch
- gclib.dll vendored into repo and listed in spec binaries= (ctypes not auto-detected by PyInstaller)
- users.json + settings.json redirect to APPDATA via _get_data_dir() before any Kivy import
- Pi Wayland disabled as first operation in install.sh — Kivy has no Wayland support
- Galil .deb installed before venv creation (venv pip install depends on system .so)
- Three Pi delivery methods coexist: USB/SCP, SD card image, git clone + install.sh
- screeninfo-based resolution detection in pre-Kivy block (same ordering pattern already established)
- [Phase 24]: GCLIB_ROOT patch uses getattr(sys, '_MEIPASS', '') guard so monkeypatched tests don't crash on missing _MEIPASS
- [Phase 24]: diagnostics.kv removed from KV_FILES — DiagnosticsScreen is dev-only, excluded from production bundle
- [Phase 24]: kivy_matplotlib_widget NavigationIcons.ttf must be explicitly included in spec datas
- [Phase 24]: DiagnosticsScreen references must be removed from base.kv, base.py, and tab_bar.py (not just screens/__init__.py)
- [Phase 24]: SPECPATH-relative pathlib paths in spec file — PyInstaller 6.x resolves relative paths from spec dir, not CWD
- [Phase 25-windows-inno-setup-installer]: ISCC step in build_windows.bat is non-fatal: PyInstaller bundle remains usable without Inno Setup installed
- [Phase 25-windows-inno-setup-installer]: Firewall rules use delete-before-add pattern so reinstalling does not duplicate rules (idempotent)
- [Phase 25-windows-inno-setup-installer]: AppId GUID is fixed per-script so Windows tracks upgrades correctly via Add/Remove Programs
- [Phase 25-windows-inno-setup-installer]: Installer verified on real Windows 11: all WIN-03/WIN-04/WIN-06 criteria confirmed, APPDATA preservation and firewall rule cleanup working
- [Phase 26-01]: _get_data_dir() Linux branch uses elif sys.platform == 'linux' — preserves all existing Windows behavior
- [Phase 26-01]: gclib 1.0.1 py3-none-any wheel — pure-Python ctypes wrapper, architecture-neutral; native .so from apt
- [Phase 26-01]: binh-an-hmi.png is 1x1 PNG placeholder from stdlib; real icon deferred to later phase
- [Phase 26]: Test regex for aarch64 arch_info check uses if/fi block pattern rather than re.DOTALL to avoid false-positive matches across full file
- [Phase 26]: install.sh places X11 forcing (do_wayland W1) before all apt/venv/gclib steps — enforced by test asserting x11_pos < apt_pos

### Critical Pitfalls (from research)

- C1: --onefile mode — use --onedir exclusively (SDL2 + data loss)
- C2: SDL2/GLEW Trees missing from spec — Kivy window silently fails
- C4: gclib DLL not in spec binaries= — silent no-controller mode
- C5: Bookworm Wayland — raspi-config X11 switch must be first install.sh operation
- C6: systemd before X11 ready — After=graphical-session.target + User=pi + DISPLAY=:0

### Research Flags (require validation)

- ~~gclib attribute names (GclibDllPath_) — confirm in installed gclib/__init__.py before Phase 24~~ (resolved: vendored DLLs + GCLIB_ROOT env var)
- kivy_matplotlib_widget ARM wheel on Bookworm — confirm PiWheels availability before Phase 26
- screeninfo on Pi HDMI-forced framebuffer — validate on real hardware in Phase 27

### Pending Todos

None yet.

### Blockers/Concerns

- kivy_matplotlib_widget ARM wheel availability unconfirmed (most likely Phase 26 failure point)

## Session Continuity

Last session: 2026-04-22T01:30:52.594Z
Stopped at: Completed 26-02-PLAN.md
Resume file: None
Next action: /gsd:plan-phase 26
