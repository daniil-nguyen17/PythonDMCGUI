---
phase: 25-windows-inno-setup-installer
plan: "02"
subsystem: infra
tags: [inno-setup, windows-installer, firewall, shortcuts, registry, human-verify]

requires:
  - phase: 25-windows-inno-setup-installer plan 01
    provides: deploy/windows/BinhAnHMI.iss and build_windows.bat ISCC step that produce dist/BinhAn_HMI_v4.0.0_Setup.exe

provides:
  - Human-verified Windows installer: BinhAn_HMI_v4.0.0_Setup.exe (46.6 MB) confirmed working end-to-end on Windows 11

affects:
  - 26-pi-os-preparation (installer story complete — no direct dep)

tech-stack:
  added: []
  patterns:
    - Human-verify checkpoint gating release artifact before phase closure

key-files:
  created: []
  modified: []

key-decisions:
  - "Installer verified on real Windows 11 machine — all WIN-03/WIN-04/WIN-06 acceptance criteria confirmed by human operator"
  - "APPDATA preservation on uninstall confirmed: %APPDATA%\\BinhAnHMI\\ survives uninstall/reinstall cycle"
  - "Firewall rules (UDP 60007 Galil DR, TCP 23 Galil TCP) confirmed created on install and removed on uninstall"

patterns-established:
  - "Human-verify checkpoint as final gate for release artifacts before phase close"

requirements-completed: [WIN-03, WIN-04, WIN-06]

duration: 1min
completed: 2026-04-22
---

# Phase 25 Plan 02: Windows Inno Setup Installer Verification Summary

**BinhAn_HMI_v4.0.0_Setup.exe (46.6 MB) verified end-to-end on Windows 11: shortcuts, Add/Remove Programs, firewall rules, APPDATA preservation, and optional auto-start registry key all confirmed correct**

## Performance

- **Duration:** 1 min (human-verify checkpoint — build completed in Plan 01)
- **Started:** 2026-04-22T00:00:00Z
- **Completed:** 2026-04-22T00:32:44Z
- **Tasks:** 2 (Task 1 build in prior session a1cc742, Task 2 human-verify approved)
- **Files modified:** 0 (verification only)

## Accomplishments

- Human operator installed BinhAn_HMI_v4.0.0_Setup.exe on a real Windows 11 machine and confirmed all acceptance criteria
- WIN-03: Start Menu "Binh An" folder and Desktop shortcut both work, Kivy window launches with correct title
- WIN-04: "Binh An HMI" appears in Windows Settings > Apps with publisher "Binh An"; uninstaller removes Program Files, shortcuts, and firewall rules cleanly
- WIN-06: HKCU\Software\Microsoft\Windows\CurrentVersion\Run key written when auto-start checkbox is checked; key removed on uninstall
- Firewall rules confirmed via netsh — UDP 60007 (Galil DR) and TCP 23 (Galil TCP) present after install, absent after uninstall
- APPDATA preservation confirmed: %APPDATA%\BinhAnHMI\ remains after uninstall

## Task Commits

Each task was committed atomically:

1. **Task 1: Build the installer** - `a1cc742` (chore) — build pipeline run, 46.6 MB installer produced
2. **Task 2: Verify installer on Windows** - human-verify approved (no code commit — verification only)

## Files Created/Modified

None — this plan is a verification-only gate; all implementation files were created in Plan 01.

## Decisions Made

- All WIN-03/WIN-04/WIN-06 acceptance criteria confirmed by human operator on real Windows 11 hardware — no rework required
- APPDATA preservation verified to be working correctly from the .iss [UninstallRun] section design

## Deviations from Plan

None — plan executed exactly as written. Human verification checkpoint approved on first attempt with all criteria passing.

## Issues Encountered

None. Installer passed all acceptance criteria on first install attempt.

## User Setup Required

None — Inno Setup 6 was already installed from Plan 01. No new external configuration required.

## Next Phase Readiness

- Phase 25 complete: Windows packaging story fully done (PyInstaller bundle + Inno Setup installer, both human-verified)
- Phase 26 (Pi OS Preparation and Install Script) can now proceed
- No blockers from Phase 25

---
*Phase: 25-windows-inno-setup-installer*
*Completed: 2026-04-22*
