---
phase: 28-logging-infrastructure
plan: 03
subsystem: infra
tags: [rsync, pyinstaller, deploy, pi, testing, pytest]

# Dependency graph
requires:
  - phase: 26-pi-os-preparation-and-install-script
    provides: deploy/pi/install.sh with initial rsync block and existing exclusions
  - phase: 24-windows-pyinstaller-bundle
    provides: deploy/windows/BinhAnHMI.spec with datas= block listing only explicit runtime assets
provides:
  - "Extended install.sh rsync with 5 additional --exclude patterns (.claude/, *.md, *.xlsx, *.dmc, pyproject.toml)"
  - "Content-inspection test suite (6 tests) verifying both Windows spec and Pi install.sh exclude non-runtime files"
affects: [29-integration-testing-and-field-validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Content-inspection tests read source artifacts as text (no actual build required)"
    - "module-scoped pytest fixtures for file I/O to avoid repeated reads across tests"

key-files:
  created:
    - tests/test_bundle_exclusions.py
  modified:
    - deploy/pi/install.sh

key-decisions:
  - "Rsync --exclude='*.md' uses glob (no leading slash) so it applies recursively at any depth"
  - "Rsync --exclude='.claude/' includes trailing slash to match directories only, not files named .claude"
  - "Windows spec tests extract the datas=[ block by string slicing between 'datas=[' and '],' to scope assertions to the datas list only"

patterns-established:
  - "Bundle exclusion tests: read spec/script as text, extract relevant block, assert forbidden patterns absent"

requirements-completed: [APP-03]

# Metrics
duration: 10min
completed: 2026-04-22
---

# Phase 28 Plan 03: Bundle Exclusion Hardening Summary

**Pi install.sh rsync extended with 5 non-runtime exclusions (.claude/, *.md, *.xlsx, *.dmc, pyproject.toml) and 6 content-inspection tests guard both Windows spec and Pi rsync against regression**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-22T02:25:00Z
- **Completed:** 2026-04-22T02:35:43Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- install.sh rsync block now excludes all non-runtime file categories from /opt/binh-an-hmi/ on Pi
- 6 pytest content-inspection tests enforce both Windows spec datas= and Pi rsync exclusion invariants
- Existing 18 Pi install tests all pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend install.sh rsync exclusions** - `f7c5429` (feat)
2. **Task 2: Create content-inspection tests for bundle exclusions** - `2c1c09f` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `deploy/pi/install.sh` - Added 5 rsync --exclude patterns for .claude/, *.md, *.xlsx, *.dmc, pyproject.toml
- `tests/test_bundle_exclusions.py` - 6 content-inspection tests for Windows spec datas= and Pi rsync exclusions

## Decisions Made

- Rsync `--exclude='*.md'` glob (no leading slash) applies recursively at any depth — covers nested README files and planning docs
- Rsync `--exclude='.claude/'` trailing slash matches directory only (not a hypothetical file named `.claude`)
- Windows spec tests slice text between `datas=[` and `],` to scope assertions to the datas list, avoiding false positives from comments or other spec sections

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- APP-03 (packages contain only runtime files) is now verified by automated tests
- Phase 29 integration testing can proceed; Pi rsync and Windows bundle are clean of dev artifacts
- No blockers

---
*Phase: 28-logging-infrastructure*
*Completed: 2026-04-22*
