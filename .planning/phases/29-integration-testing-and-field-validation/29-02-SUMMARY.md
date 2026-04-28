---
phase: 29-integration-testing-and-field-validation
plan: 02
subsystem: testing
tags: [deployment, windows, raspberry-pi, galil, gclib, flat-grind, data-record, field-validation]

requires:
  - phase: 29-01-integration-testing-baseline
    provides: Zero-failure test suite (516 pass) and deployment READMEs for technician use

provides:
  - "Windows installer validated on clean factory PC with default Defender — no AV quarantine, no DLL errors"
  - "Flat Grind live cycle on real Galil controller (Windows) — live A/B plot, button graying, state updates, knife count increment"
  - "Pi 500 deployment via Method A (USB transfer) validated on 64-bit Bookworm — app reaches PIN login"
  - "Display preset auto-detected correctly as 15-inch from 1920x1080 on Pi"
  - "Flat Grind live cycle on Pi with real Galil controller — DR streaming produces live position data"
  - "Platform-conditional gclib flags (no -MG 0 / --subscribe MG on Linux)"
  - "Galil apt repo GPG SHA1 workaround ([trusted=yes]) + offline .deb vendor support for Pi Bookworm 2026+"
  - "Static IP (100.100.100.10/24) auto-configured via NetworkManager profile in install.sh"
  - "Desktop shortcut PYTHONPATH fix — app module not found resolved"
  - "Galil apt source arch restriction fixed to arm64 for Pi 500"

affects: [field-technicians, production-pi-deployment, windows-factory-deployment]

tech-stack:
  added: []
  patterns:
    - "Platform-conditional gclib PRIMARY_FLAGS: -MG 0 and --subscribe MG are Windows-only flags"
    - "install.sh NetworkManager nmcli profile for persistent static IP on eth0 across reboots"
    - "Offline .deb vendor bundle in deploy/pi/vendor/ allows air-gapped Pi gclib install"
    - "Galil apt source uses [trusted=yes] workaround for SHA1 GPG rejection on Bookworm 2026+"

key-files:
  created:
    - deploy/pi/vendor/README.md
  modified:
    - src/dmccodegui/controller.py
    - src/dmccodegui/hmi/mg_reader.py
    - src/dmccodegui/screens/flat_grind/run.py
    - src/dmccodegui/screens/serration/run.py
    - deploy/pi/install.sh
    - deploy/pi/binh-an-hmi.desktop
    - deploy/pi/README.md

key-decisions:
  - "gclib -MG 0 and --subscribe MG flags are Windows-only — Linux gclib does not support them; controlled via sys.platform check in PRIMARY_FLAGS and mg_reader"
  - "Galil apt repo GPG key uses SHA1 — rejected by Pi OS Bookworm 2026+; workaround is [trusted=yes] in sources.list entry plus offline .deb vendor bundle for air-gapped installs"
  - "Static IP for eth0 configured via NetworkManager nmcli profile in install.sh — persists across reboots unlike /etc/network/interfaces on Bookworm"
  - "Desktop shortcut Exec line must include PYTHONPATH=/opt/binh-an-hmi/src — without it, Python cannot find the dmccodegui package"
  - "Galil apt source arch=amd64,armhf excluded arm64 — fixed to arch=arm64 for Pi 500 (aarch64)"
  - "Method B (SD card image) and Method C (git clone) deferred — Method A USB/SCP validated on Pi 500 Bookworm is sufficient for field deployment"
  - "7-inch and 10-inch screen validation deferred — 15-inch display preset auto-detected correctly; smaller screens deferred to later if needed"

requirements-completed: [FIX-02, PI-06]

duration: field-validated (multi-session)
completed: 2026-04-27
---

# Phase 29 Plan 02: Hardware Validation and Field Testing Summary

**Windows installer and Pi 500 deployment both validated on real Galil hardware — 5 inline deployment bugs found and fixed during field testing**

## Performance

- **Duration:** Multi-session (field validation, hardware-dependent)
- **Started:** 2026-04-22
- **Completed:** 2026-04-27
- **Tasks:** 2 (both human-verified checkpoints)
- **Files modified:** 7 source/deploy files + 1 vendor README created

## Accomplishments

- Windows installer passed clean factory PC gate: no AV quarantine, no missing DLLs, PIN login reached from Start Menu shortcut
- Flat Grind live cycle on Windows: live A/B plot updated, motion buttons grayed during active motion, status bar showed GRINDING/IDLE transitions, knife count incremented
- Pi 500 deployment via USB/SCP (Method A) to 64-bit Bookworm confirmed working — app reached PIN login
- Display preset auto-detected as 15-inch from 1920x1080 resolution — correct and validated
- Pi with real Galil controller ran Flat Grind cycle — DR streaming produced live position data with A/B plot updating in real-time
- 5 deployment bugs discovered and fixed inline during field testing (platform flags, GPG key, static IP, PYTHONPATH, arch restriction)

## Task Commits

Tasks were human-verified checkpoints. Source changes committed by user inline during validation:

1. **Task 1: Windows clean-PC validation and live controller test** - `5743a3d` (test)
2. **Task 2: Pi deployment validation and live Galil controller test** - `88afad9` (fix)

## Files Created/Modified

- `src/dmccodegui/controller.py` — PRIMARY_FLAGS platform-conditional: no `-MG 0` on Linux
- `src/dmccodegui/hmi/mg_reader.py` — `--subscribe MG` flag Windows-only
- `src/dmccodegui/screens/flat_grind/run.py` — `--subscribe MG` flag Windows-only
- `src/dmccodegui/screens/serration/run.py` — `--subscribe MG` flag Windows-only
- `deploy/pi/install.sh` — major overhaul: gclib offline install, [trusted=yes] apt source, static IP via NetworkManager, PYTHONPATH in .desktop, arch=arm64
- `deploy/pi/binh-an-hmi.desktop` — PYTHONPATH=/opt/binh-an-hmi/src added to Exec line; python3 explicit
- `deploy/pi/README.md` — updated with Pi 500 support, new troubleshooting steps
- `deploy/pi/vendor/README.md` — offline gclib .deb bundling instructions

## Decisions Made

- **Platform-conditional gclib flags:** `-MG 0` and `--subscribe MG` are Windows-only gclib CLI arguments. Linux gclib does not recognize them and returns errors. Applied `sys.platform == 'win32'` guard in controller.py PRIMARY_FLAGS list and in mg_reader, flat_grind/run.py, serration/run.py.
- **Galil GPG SHA1 workaround:** The Galil apt repo GPG key uses SHA1 — rejected by Pi OS Bookworm 2026+. `[trusted=yes]` added to apt sources.list entry. Offline `.deb` vendor bundle in `deploy/pi/vendor/` added for air-gapped factory installs.
- **Static IP via NetworkManager:** Pi eth0 needed static IP (100.100.100.10/24) to reach controller at 100.100.100.2. Used `nmcli` to create a connection profile — persists across reboots on Bookworm, unlike `/etc/network/interfaces` which is ignored by NetworkManager.
- **PYTHONPATH in desktop shortcut:** The `.desktop` Exec line lacked `PYTHONPATH=/opt/binh-an-hmi/src` — Python could not find the dmccodegui package. Fixed in both install.sh and the committed .desktop file.
- **arch=arm64 for Galil apt source:** The Galil apt sources.list entry specified `arch=amd64,armhf` which excluded arm64 (Pi 500 aarch64). Fixed to `arch=arm64`.
- **Methods B and C deferred:** SD card image and git clone deployment methods were not validated. Method A (USB/SCP) is sufficient for factory deployment. Methods B and C deferred to a later phase if needed.
- **7-inch and 10-inch screens deferred:** Only 15-inch display (1920x1080) was available and validated. Smaller screen sizes deferred.

## Deviations from Plan

### Auto-fixed Issues (Rule 1 - Bugs found during field validation)

**1. [Rule 1 - Bug] gclib -MG 0 and --subscribe MG flags unsupported on Linux**
- **Found during:** Task 2 (Pi deployment validation)
- **Issue:** Linux gclib does not support `-MG 0` (set MG timeout) or `--subscribe MG` (subscribe to MG output) flags — both are Windows-specific gclib CLI arguments. App crashed on Pi at startup.
- **Fix:** Platform-conditional flag lists in controller.py PRIMARY_FLAGS, mg_reader.py, flat_grind/run.py, serration/run.py using `sys.platform == 'win32'` guard
- **Files modified:** `src/dmccodegui/controller.py`, `src/dmccodegui/hmi/mg_reader.py`, `src/dmccodegui/screens/flat_grind/run.py`, `src/dmccodegui/screens/serration/run.py`
- **Committed in:** `8e06aaa` (fix: strip gclib flags from address before connect and storage)

**2. [Rule 1 - Bug] Galil apt repo GPG SHA1 key rejected by Pi OS Bookworm 2026+**
- **Found during:** Task 2 (install.sh execution on Pi)
- **Issue:** Bookworm 2026+ apt rejects SHA1 GPG signatures by default. `apt-get update` failed with "NO_PUBKEY" or signature error, blocking gclib install.
- **Fix:** Added `[trusted=yes]` to the Galil apt sources.list entry; added offline `.deb` vendor bundle support in `deploy/pi/vendor/` as fallback
- **Files modified:** `deploy/pi/install.sh`, `deploy/pi/vendor/README.md`
- **Committed in:** `88afad9`

**3. [Rule 1 - Bug] Pi eth0 had no static IP — controller unreachable**
- **Found during:** Task 2 (live controller test on Pi)
- **Issue:** Pi eth0 defaulted to DHCP and did not get an IP in the 100.100.100.x subnet. Controller at 100.100.100.2 was unreachable.
- **Fix:** install.sh now runs `nmcli con add` to create a persistent eth0 static IP profile (100.100.100.10/24) via NetworkManager
- **Files modified:** `deploy/pi/install.sh`
- **Committed in:** `88afad9`

**4. [Rule 1 - Bug] Desktop shortcut missing PYTHONPATH — app module not found**
- **Found during:** Task 2 (first app launch from desktop shortcut)
- **Issue:** `.desktop` Exec line lacked `PYTHONPATH=/opt/binh-an-hmi/src` — Python's module search path did not include the src/ directory and `import dmccodegui` failed with ModuleNotFoundError.
- **Fix:** Updated `binh-an-hmi.desktop` Exec line to include `PYTHONPATH=/opt/binh-an-hmi/src` and explicit `python3`; updated install.sh to generate the .desktop with correct Exec
- **Files modified:** `deploy/pi/binh-an-hmi.desktop`, `deploy/pi/install.sh`
- **Committed in:** `88afad9`

**5. [Rule 1 - Bug] Galil apt source arch=amd64,armhf excluded arm64 (Pi 500)**
- **Found during:** Task 2 (gclib apt install on Pi 500 aarch64)
- **Issue:** The Galil apt sources.list entry restricted packages to `amd64,armhf` architectures. Pi 500 runs aarch64 (arm64) — gclib .deb was skipped as "not applicable architecture".
- **Fix:** Changed apt sources.list entry arch restriction to `arch=arm64`
- **Files modified:** `deploy/pi/install.sh`
- **Committed in:** `88afad9`

---

**Total deviations:** 5 auto-fixed (all Rule 1 - Bugs discovered during field testing)
**Impact on plan:** All 5 fixes were required for Pi deployment to function. Windows validation required no code changes. The plan anticipated inline bug fixing during hardware validation — this was expected and handled correctly.

### Deferred Items

- **Pi Method B (SD card image):** Not validated. Deferred — Method A is sufficient for current deployment needs.
- **Pi Method C (git clone):** Not validated. Deferred.
- **7-inch and 10-inch display presets:** Not validated on real hardware. 15-inch confirmed correct. Deferred.

## Issues Encountered

- The Pi 500 uses aarch64 (arm64) which is not the typical armhf that older Pi deployment guides target. Multiple issues (Galil apt arch, gclib flag compatibility) were specific to this architecture change.
- Galil's apt repository infrastructure has not been updated for Bookworm's stricter GPG requirements — the `[trusted=yes]` workaround is a pragmatic fix until Galil updates their signing key.
- The NetworkManager static IP approach on Bookworm differs from older Pi OS guidance (`/etc/dhcpcd.conf` or `/etc/network/interfaces`) — both legacy methods are ignored by NetworkManager on Bookworm.

## User Setup Required

None — all deployment steps are automated via install.sh. Technician reference: `deploy/pi/README.md`.

## Next Phase Readiness

- Phase 29 (Integration Testing and Field Validation) is complete — both plans done
- v4.0 milestone requirements FIX-02 and PI-06 are satisfied
- Windows installer is production-ready for factory deployment
- Pi 500 deployment via USB/SCP is validated for field use
- The 5 inline fixes are committed — deploy/pi/install.sh is the authoritative deployment script

---
*Phase: 29-integration-testing-and-field-validation*
*Completed: 2026-04-27*
