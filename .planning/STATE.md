---
gsd_state_version: 1.0
milestone: v4.0
milestone_name: Packaging & Deployment
status: unknown
stopped_at: Phase 24 planned
last_updated: "2026-04-21T11:44:29.378Z"
last_activity: 2026-04-21 — v4.0 roadmap created (Phases 24-29)
progress:
  total_phases: 22
  completed_phases: 0
  total_plans: 2
  completed_plans: 1
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-21)

**Core value:** An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion, zero access to things they shouldn't touch.
**Current focus:** v4.0 — Phase 24: Windows PyInstaller Bundle

## Current Position

```
Milestone : v4.0 Packaging & Deployment
Phase     : 24 of 29 (Windows PyInstaller Bundle)
Plan      : —
Status    : Ready to plan
Progress  : [░░░░░░░░░░] 0%
```

Last activity: 2026-04-21 — v4.0 roadmap created (Phases 24-29)

## v4.0 Phase Map

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 24 | Windows PyInstaller Bundle | WIN-01, WIN-02, WIN-05, WIN-07 | Not started |
| 25 | Windows Inno Setup Installer | WIN-03, WIN-04, WIN-06 | Not started |
| 26 | Pi OS Preparation and Install Script | PI-01 through PI-05, PI-07 | Not started |
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

### Critical Pitfalls (from research)

- C1: --onefile mode — use --onedir exclusively (SDL2 + data loss)
- C2: SDL2/GLEW Trees missing from spec — Kivy window silently fails
- C4: gclib DLL not in spec binaries= — silent no-controller mode
- C5: Bookworm Wayland — raspi-config X11 switch must be first install.sh operation
- C6: systemd before X11 ready — After=graphical-session.target + User=pi + DISPLAY=:0

### Research Flags (require validation)

- gclib attribute names (GclibDllPath_) — confirm in installed gclib/__init__.py before Phase 24
- kivy_matplotlib_widget ARM wheel on Bookworm — confirm PiWheels availability before Phase 26
- screeninfo on Pi HDMI-forced framebuffer — validate on real hardware in Phase 27

### Pending Todos

None yet.

### Blockers/Concerns

- gclib DLL attribute names unconfirmed for current gclib version (MEDIUM risk — Phase 24)
- kivy_matplotlib_widget ARM wheel availability unconfirmed (most likely Phase 26 failure point)

## Session Continuity

Last session: 2026-04-21T11:44:29.374Z
Stopped at: Phase 24 planned
Resume file: .planning/phases/24-windows-pyinstaller-bundle/24-01-PLAN.md
Next action: /gsd:plan-phase 24
