---
phase: 05-csv-profile-system
plan: "02"
subsystem: ui
tags: [kivy, profiles, csv, import, export, diff, file-chooser, role-gating, modal]

dependency_graph:
  requires:
    - phase: 05-01
      provides: profiles.py CSV engine (export_profile, parse_profile_csv, compute_diff, validate_import)
  provides:
    - ProfilesScreen Kivy Screen with full import/export UI
    - FileChooserOverlay ModalView for CSV file selection
    - DiffDialog ModalView with scrollable diff table
    - profiles.kv KV layout (dark theme, 64dp buttons, status label)
    - Profiles tab in TabBar for Setup/Admin roles
  affects: [05-03-validation-phase]

tech-stack:
  added: []
  patterns:
    - ModalView overlay pattern (auto_dismiss=False, size_hint 1,1 or 0.9,0.85)
    - jobs.submit() for all controller I/O — never on main thread
    - state.subscribe() in on_pre_enter / unsubscribe in on_leave lifecycle pattern
    - Kivy classes inside try/except ImportError block for headless test compatibility
    - Inline Popup construction in Python (no KV rule) for dynamic popups

key-files:
  created:
    - src/dmccodegui/ui/profiles.kv
  modified:
    - src/dmccodegui/screens/profiles.py
    - src/dmccodegui/screens/tab_bar.py
    - src/dmccodegui/screens/__init__.py
    - src/dmccodegui/ui/base.kv
    - src/dmccodegui/main.py
    - tests/test_tab_bar.py

key-decisions:
  - "Kivy classes wrapped in try/except ImportError — keeps headless profile engine tests working with zero changes"
  - "Inline Popup construction in Python (not KV rules) — dynamic export name popup and overwrite confirm require runtime TextInput access"
  - "ProfilesScreen export to __init__.py required — Factory.RootLayout() resolves screen classes via Factory registry at build() time"
  - "status_text StringProperty on ProfilesScreen — safe to set from background thread; Kivy schedules canvas update on next frame"

patterns-established:
  - "ModalView overlay: auto_dismiss=False, all controller callbacks via jobs.submit()"
  - "Screen lifecycle: subscribe in on_pre_enter, unsubscribe callable stored and called in on_leave"
  - "Role gating via tab visibility only — ProfilesScreen has no internal role checks"

requirements-completed: [CSV-01, CSV-02, CSV-03, CSV-04, CSV-05]

duration: 12min
completed: "2026-04-04"
---

# Phase 05 Plan 02: Profiles Screen UI Summary

**ProfilesScreen with FileChooserOverlay, DiffDialog, export name popup, and role-gated tab — completing the full CSV import/export user flow.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-04T14:32:00Z
- **Completed:** 2026-04-04T14:44:00Z
- **Tasks:** 2
- **Files modified:** 6 (+ 1 created)

## Accomplishments

- ProfilesScreen with full export and import flows, all controller I/O on background thread
- FileChooserOverlay and DiffDialog ModalView classes defined in Python + KV
- Export popup with name input and overwrite confirmation; import with machine-type check, diff review, BV burn
- Import button disabled/greyed when cycle_running is True (state subscription)
- Profiles tab added to TabBar for Setup/Admin only; operator does not see it
- ProfilesScreen registered in ScreenManager (base.kv) and KV_FILES (main.py)
- 3 new role-visibility tests added to test_tab_bar.py — all 109 tests pass

## Task Commits

1. **Task 1: ProfilesScreen class, KV layout, FileChooser overlay, diff dialog, export popup** - `905f053` (feat)
2. **Task 2: Wire ProfilesScreen into app shell (tab bar, screen manager, KV_FILES) + role test** - `5504c0a` (feat)

## Files Created/Modified

- `src/dmccodegui/screens/profiles.py` — Extended with ProfilesScreen, FileChooserOverlay, DiffDialog, get_profiles_dir(); pure-Python engine unchanged
- `src/dmccodegui/ui/profiles.kv` — KV rules for all three Kivy classes; dark theme, 64dp buttons, status label
- `src/dmccodegui/screens/tab_bar.py` — Added ("profiles", "Profiles") to ALL_TABS; added "profiles" to setup and admin ROLE_TABS
- `src/dmccodegui/screens/__init__.py` — Added ProfilesScreen import and __all__ entry so Factory registry finds it at app build
- `src/dmccodegui/ui/base.kv` — Added ProfilesScreen name='profiles' to ScreenManager before DiagnosticsScreen
- `src/dmccodegui/main.py` — Added "ui/profiles.kv" to KV_FILES after parameters.kv
- `tests/test_tab_bar.py` — Updated local ROLE_TABS mirror; added TestProfilesTabRoleVisibility (3 tests)

## Decisions Made

- Kivy classes wrapped in `try/except ImportError` so the pure-Python CSV engine tests run headlessly without Kivy. This preserves the 25 test_profiles.py tests exactly as written in Plan 01.
- Inline Popup construction in Python rather than KV rules, because the export name popup and overwrite confirm need runtime access to a TextInput widget reference — KV rules cannot capture widget refs at dismiss time.
- ProfilesScreen must be exported from `screens/__init__.py` because `main.py` does `import dmccodegui.screens as _screens` (noqa: F401) to ensure all screen classes are registered with Kivy's Factory before `Factory.RootLayout()` is called.
- `status_text` is a `StringProperty` assigned directly from background threads — Kivy defers canvas updates to the next frame so this is thread-safe.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added ProfilesScreen to screens/__init__.py**
- **Found during:** Task 2 (wiring app shell)
- **Issue:** main.py imports `dmccodegui.screens` to register all screen classes with the Kivy Factory; ProfilesScreen was not in `__init__.py` so it would be invisible to `Factory.RootLayout()` at build time, causing a `FactoryException: Unknown class <ProfilesScreen>`
- **Fix:** Added `from .profiles import ProfilesScreen` and `"ProfilesScreen"` to `__all__`
- **Files modified:** src/dmccodegui/screens/__init__.py
- **Verification:** `python -c "from dmccodegui.screens.profiles import ProfilesScreen"` succeeds; 109 tests pass
- **Committed in:** 5504c0a (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential fix — without it the app would crash on startup when it tries to instantiate the ScreenManager with an unregistered ProfilesScreen class. Zero scope creep.

## Issues Encountered

None — plan executed cleanly.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| src/dmccodegui/screens/profiles.py (ProfilesScreen class) | FOUND |
| src/dmccodegui/ui/profiles.kv | FOUND |
| src/dmccodegui/screens/tab_bar.py (profiles in ALL_TABS) | FOUND |
| src/dmccodegui/ui/base.kv (ProfilesScreen in ScreenManager) | FOUND |
| src/dmccodegui/main.py (profiles.kv in KV_FILES) | FOUND |
| tests/test_tab_bar.py (TestProfilesTabRoleVisibility) | FOUND |
| Commit 905f053 (Task 1) | FOUND |
| Commit 5504c0a (Task 2) | FOUND |
| 109 tests pass | CONFIRMED |

## Next Phase Readiness

- CSV profile system (Plans 01+02) is complete: engine + UI both ship
- Profiles tab available to Setup/Admin users immediately on auth
- Phase 6 (machine-type module) can extend `MACHINE_TYPE` without touching ProfilesScreen
- No blockers for next phase

---
*Phase: 05-csv-profile-system*
*Completed: 2026-04-04*
