---
phase: 25-windows-inno-setup-installer
plan: "01"
subsystem: infra
tags: [inno-setup, windows-installer, pyinstaller, firewall, shortcuts, registry]

requires:
  - phase: 24-windows-pyinstaller-bundle
    provides: dist/BinhAnHMI/ onedir bundle that the .iss script packages

provides:
  - deploy/windows/BinhAnHMI.iss — complete Inno Setup 6 script for single-file setup .exe
  - tests/test_installer.py — 16 content-inspection tests for .iss correctness
  - build_windows.bat extended with non-fatal ISCC.exe compilation step

affects:
  - 26-pi-os-preparation (no direct dep, but installer completes the Windows packaging story)

tech-stack:
  added: [Inno Setup 6 (.iss scripting)]
  patterns:
    - TDD for config/script files via plain-text content inspection tests
    - Delete-before-add firewall rule pattern for idempotent reinstalls
    - Non-fatal optional tool detection in batch scripts (ISCC path probe + graceful skip)

key-files:
  created:
    - deploy/windows/BinhAnHMI.iss
    - tests/test_installer.py
  modified:
    - deploy/windows/build_windows.bat

key-decisions:
  - "ISCC step in build_windows.bat is non-fatal: PyInstaller bundle remains usable without Inno Setup installed"
  - "Firewall rules use delete-before-add pattern so reinstalling does not duplicate rules"
  - "Startup task is unchecked by default (WIN-06) — HKCU Run key written only when user opts in"
  - "AppId GUID is fixed (not regenerated) so Windows tracks upgrades correctly via Add/Remove Programs"

patterns-established:
  - "Content-inspection testing: read script/config file as text, assert required patterns with re.search — no .iss parser needed"
  - "Batch optional-tool pattern: probe known install path, fall back to PATH, warn+skip if absent"

requirements-completed: [WIN-03, WIN-04, WIN-06]

duration: 2min
completed: 2026-04-21
---

# Phase 25 Plan 01: Windows Inno Setup Installer Summary

**Inno Setup 6 .iss script packaging the PyInstaller onedir bundle with Start Menu/Desktop shortcuts, Add/Remove Programs entry, optional HKCU auto-start, and idempotent Galil firewall rules (UDP 60007 + TCP 23)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-21T15:19:04Z
- **Completed:** 2026-04-21T15:19:26Z
- **Tasks:** 2 (Task 1 TDD, Task 2 extension)
- **Files modified:** 3

## Accomplishments

- Created deploy/windows/BinhAnHMI.iss with all 8 Inno Setup sections covering shortcuts (WIN-03), Add/Remove Programs with uninstall icon (WIN-04), optional startup task unchecked by default (WIN-06), and idempotent firewall rules for Galil DR (UDP 60007) and Galil TCP (TCP 23)
- Created tests/test_installer.py with 16 passing content-inspection tests (TDD RED then GREEN)
- Extended build_windows.bat with a non-fatal ISCC.exe compilation step that gracefully skips with a warning if Inno Setup is not installed

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Test scaffold** - `e7a1428` (test)
2. **Task 1 GREEN: BinhAnHMI.iss** - `8d6a10c` (feat)
3. **Task 2: Build script ISCC step** - `fd635b1` (feat)

_Note: TDD task split into RED (test) and GREEN (implementation) commits_

## Files Created/Modified

- `deploy/windows/BinhAnHMI.iss` - Complete Inno Setup 6 script: [Setup], [Languages], [Tasks], [Files], [Icons], [Registry], [Run], [UninstallRun]
- `tests/test_installer.py` - 16 content-inspection tests asserting .iss correctness for WIN-03/04/06
- `deploy/windows/build_windows.bat` - Appended ISCC.exe probe + non-fatal compile step

## Decisions Made

- ISCC step non-fatal: if Inno Setup is not installed, the batch script prints a warning with the download URL and exits 0 — the PyInstaller bundle is still deliverable without the installer .exe
- Firewall rules use delete-before-add so reinstalling over an existing copy does not accumulate duplicate rules
- AppId GUID is hardcoded (not generated per-build) so Windows can track version upgrades and uninstalls correctly through Add/Remove Programs

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

`test_axes_setup.py::test_enter_setup_skips_fire_when_already_setup` was already failing before this plan's changes (confirmed by stash-and-rerun). It is a pre-existing failure in unrelated code and out of scope per the deviation scope boundary rule. Logged to deferred items.

## User Setup Required

**External tool requires manual installation before running build_windows.bat end-to-end.**

- Install Inno Setup 6 from https://jrsoftware.org/isdl.php (download innosetup-6.7.1.exe, run with defaults)
- Verify: open Command Prompt and run `"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /?`
- After install, re-run `deploy\windows\build_windows.bat` to produce `dist\BinhAn_HMI_v4.0.0_Setup.exe`

## Next Phase Readiness

- Phase 25 Plan 01 complete: .iss script and test scaffold in place, build integration done
- Phase 26 (Pi OS Preparation and Install Script) can proceed independently
- Actual installer .exe build requires Inno Setup 6 to be installed on the build machine

---
*Phase: 25-windows-inno-setup-installer*
*Completed: 2026-04-21*
