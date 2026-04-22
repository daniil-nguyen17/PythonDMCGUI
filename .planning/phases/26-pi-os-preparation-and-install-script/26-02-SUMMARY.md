---
phase: 26-pi-os-preparation-and-install-script
plan: 02
subsystem: deploy
tags: [pi, linux, install-script, bash, tdd, kivy, gclib, aarch64]

# Dependency graph
requires:
  - phase: 26-01
    provides: deploy/pi/ skeleton (requirements-pi.txt, binh-an-hmi.desktop, binh-an-hmi.png, vendor/)
provides:
  - deploy/pi/install.sh (complete Pi OS Bookworm installer, aarch64-targeted)
  - tests/test_install_pi.py (18 content-inspection tests)
affects: [phase 29 integration testing, field validation on Pi hardware]

# Tech tracking
tech-stack:
  added: []
  patterns: [TDD red-green for shell script content inspection, module-scoped fixture for file read, idempotency guards via existence checks]

key-files:
  created:
    - deploy/pi/install.sh
    - tests/test_install_pi.py
  modified: []

key-decisions:
  - "Test regex for arch_info uses the if/fi block pattern rather than re.DOTALL to avoid false-positive matches across the full file"
  - "Venv test accepts VENV_DIR variable pattern (VENV_DIR + INSTALL_DIR constants) rather than requiring literal /opt/binh-an-hmi/venv string"
  - "X11 forcing (do_wayland W1) is first raspi-config operation — before apt, before gclib, before venv"
  - "aarch64 detection is informational only (log message about 20-40 min compile time) — script does not abort on 64-bit"

patterns-established:
  - "Content-inspection tests: module-scoped fixture reads file once, individual tests assert patterns via string search or re.search — mirrors Phase 25 test_installer.py"
  - "Idempotency: venv existence check (if [[ ! -d $VENV_DIR ]]), gclib installed check (dpkg -l | grep ^ii)"
  - "Step ordering: X11 -> screen blanking -> SSH -> apt -> gclib -> venv -> pip -> desktop shortcuts -> reboot"

requirements-completed: [PI-01, PI-04, PI-05]

# Metrics
duration: 3min
completed: "2026-04-22"
---

# Phase 26 Plan 02: Pi OS Install Script Summary

**Bash install.sh for Pi OS Bookworm (aarch64): forces X11 first, installs SDL2/build-essential/cmake dev headers for Kivy source compilation, installs Galil gclib via vendored .deb, creates idempotent venv at /opt/binh-an-hmi/venv, and deploys desktop shortcuts — with 18 TDD content-inspection tests.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-22T01:26:56Z
- **Completed:** 2026-04-22T01:29:50Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Complete `deploy/pi/install.sh`: transforms fresh Pi OS Bookworm SD card into working HMI workstation in one `sudo bash install.sh` command
- Script correctly orders X11 forcing (do_wayland W1) as the very first raspi-config call, before any apt or Python setup
- aarch64 build toolchain (build-essential, cmake, pkg-config, libsdl2-dev, libsdl2-image-dev, libsdl2-mixer-dev, libsdl2-ttf-dev, Mesa EGL/GLES2, GStreamer dev libs) installed so Kivy can compile from source on 64-bit Pi OS
- 18 content-inspection tests covering every requirement from the plan spec, all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Create install.sh and content-inspection tests** - `35e56e1` (feat)

**Plan metadata:** `[pending]` (docs: complete plan)

_Note: TDD task — test file written first (RED), then implementation (GREEN), then test fixes for regex precision._

## Files Created/Modified

- `deploy/pi/install.sh` - Complete Pi OS Bookworm installer (170 lines): X11 forcing, aarch64 build deps, Galil gclib, venv, pip install, desktop shortcuts, screen blanking, SSH, reboot countdown. `set -euo pipefail`, EUID root check, LOG_FILE tee throughout.
- `tests/test_install_pi.py` - 18 content-inspection tests covering: existence, set -euo pipefail, root check, architecture detection, X11 ordering, apt deps, aarch64 SDL2 build deps, gclib dpkg, venv path, pip with requirements-pi.txt, idempotency guards, screen blanking, SSH, desktop shortcut paths, reboot countdown, LOG_FILE, requirements-pi.txt kivy check, .desktop fields.

## Decisions Made

- **X11 ordering test uses position comparison** (`x11_pos < apt_pos`) rather than checking file structure — ensures ordering contract is enforced at the byte level.
- **Test regex for venv** accepts either literal `/opt/binh-an-hmi/venv` or the variable pattern (`VENV_DIR.*venv` + `/opt/binh-an-hmi`) — the script uses `VENV_DIR="$INSTALL_DIR/venv"` so the literal is split across two constants.
- **arch_info test** uses if/fi block pattern check rather than `re.DOTALL` scan of the entire file — avoids false-positive match where header comment mentions `aarch64 / 64-bit)` and root-check block later has `exit 1` (unrelated lines, hundreds of lines apart).
- **No kiosk/systemd/watchdog code** — deferred per CONTEXT.md and plan spec. Script installs a normal desktop app with an icon only.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test regex false-positive on aarch64/exit 1 check**
- **Found during:** Task 1 (GREEN phase — running tests after install.sh creation)
- **Issue:** `re.search(r"aarch64.*exit\s+1", text, re.DOTALL)` triggered because `re.DOTALL` makes `.` match newlines — header comment `aarch64 / 64-bit)` on line 5 and `exit 1` in root-check on line 44 were hundreds of characters apart but matched
- **Fix:** Replaced with dual-condition check using if/fi block pattern — only flags `exit 1` inside an `if.*aarch64.*fi` block
- **Files modified:** tests/test_install_pi.py
- **Verification:** test_install_sh_arch_info passes, and a hypothetical script that DID abort on aarch64 would still be caught
- **Committed in:** 35e56e1 (Task 1 commit)

**2. [Rule 1 - Bug] Test for venv path failed on variable-substitution pattern**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** `assert "/opt/binh-an-hmi/venv" in install_sh_text` failed because the script uses two separate constants: `INSTALL_DIR="/opt/binh-an-hmi"` and `VENV_DIR="$INSTALL_DIR/venv"` — the literal path never appears as one string
- **Fix:** Extended assertion to also accept the variable pattern (VENV_DIR containing "venv" AND INSTALL_DIR path present)
- **Files modified:** tests/test_install_pi.py
- **Verification:** test_install_sh_venv passes
- **Committed in:** 35e56e1 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 — test regex bugs)
**Impact on plan:** Both fixes tightened test accuracy. No scope creep. install.sh content unchanged between RED and GREEN.

## Issues Encountered

- Pre-existing test failures (16 tests) confirmed via `git stash` round-trip: `test_axes_setup.py::test_enter_setup_skips_fire_when_already_setup`, `test_run_screen.py`, `test_screen_loader.py`, `test_status_bar.py` failures all existed before Plan 02 changes. Out of scope per deviation boundary rule. Logged to context only.

## User Setup Required

None — no external service configuration required. The installer itself requires the Galil `.deb` file to be placed in `deploy/pi/vendor/galil-release_1_all.deb` before running on Pi hardware (documented in `deploy/pi/vendor/README.md` from Plan 01).

## Next Phase Readiness

- Phase 26 complete — both plans done (Plan 01: Linux data-dir + deploy/pi/ skeleton; Plan 02: install.sh + tests)
- Phase 27 (Screen Resolution Detection) can proceed — no blockers from this phase
- On-Pi validation deferred to Phase 29 (Integration Testing and Field Validation)
- Remaining known concern: kivy-matplotlib-widget ARM wheel availability on aarch64 PiWheels still unconfirmed — will surface during Phase 29 hardware run

---
*Phase: 26-pi-os-preparation-and-install-script*
*Completed: 2026-04-22*
