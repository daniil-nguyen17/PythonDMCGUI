---
phase: 07-admin-and-user-management
plan: 02
subsystem: auth
tags: [kivy, users, admin, crud, modal, pin, role-management]

# Dependency graph
requires:
  - phase: 07-01
    provides: AuthManager CRUD methods and users tab in ROLE_TABS

provides:
  - UsersScreen: Admin-only card-based user management screen
  - UserEditOverlay: Modal overlay for create/edit user with name/PIN/role fields
  - users.kv: KV layout rules for both widgets
  - Wire-up in main.py: auth_manager + state injected, KV loaded, idle redirect extended

affects: [08-kiosk, testing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "try/except ImportError guard for all Kivy screen/overlay classes — headless test compatibility"
    - "ModalView with auto_dismiss=False and Clock.schedule_once for field init after open()"
    - "Role badge as Label with RoundedRectangle canvas.before — pure Kivy, no external widget"
    - "Card list rebuilt on every on_pre_enter — simple correctness over optimization"

key-files:
  created:
    - src/dmccodegui/screens/users.py
    - src/dmccodegui/ui/users.kv
  modified:
    - src/dmccodegui/screens/__init__.py
    - src/dmccodegui/ui/base.kv
    - src/dmccodegui/main.py

key-decisions:
  - "UsersScreen._rebuild_cards() called on every on_pre_enter — simple, always-correct list refresh"
  - "UserEditOverlay uses Clock.schedule_once for field init — ensures widget IDs are bound before text assignment"
  - "Role selector buttons disabled (not hidden) when editing current user — visual cue that self-demotion is blocked"
  - "Force logout on self-delete calls state.set_auth('', 'operator') — resets auth state without navigating (TabBar/PIN overlay handles navigation)"

patterns-established:
  - "UsersScreen pattern: inject auth_manager via ObjectProperty + explicit post-loop injection in main.py build()"
  - "Error display: StringProperty error_msg on overlay + Clock.schedule_once clear after 3s"

requirements-completed: [AUTH-07, AUTH-08]

# Metrics
duration: 3min
completed: 2026-04-06
---

# Phase 7 Plan 02: Users Screen Summary

**Admin user management screen with card list, modal Add/Edit overlay (name/PIN/role), and Delete with confirmation — wired into app shell with auth_manager injection and idle-lock coverage**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-06T00:47:36Z
- **Completed:** 2026-04-06T00:50:51Z
- **Tasks:** 2 of 3 complete (Task 3 is human-verify checkpoint)
- **Files modified:** 5

## Accomplishments

- UsersScreen shows card-based list of all users (name, role badge with color, masked PIN)
- UserEditOverlay modal handles Add (create_user) and Edit (update_user) with role selector
- Self-demotion guard: role buttons disabled in edit overlay when editing the currently logged-in user
- Delete confirmation popup; deleting the current logged-in user calls state.set_auth("", "operator") to force logout
- Validation errors (duplicate name, duplicate PIN, invalid PIN, last-admin) displayed in overlay via error_msg property
- All 150 existing tests pass with zero regressions
- UsersScreen registered in ScreenManager, KV loaded, auth_manager injected, idle timeout extended to cover users screen

## Task Commits

Each task was committed atomically:

1. **Task 1: Create UsersScreen, UserEditOverlay, and KV layout** - `0de1163` (feat)
2. **Task 2: Wire UsersScreen into app shell** - `4e29224` (feat)
3. **Task 3: Verify Admin user management flow** - awaiting human verification

## Files Created/Modified

- `src/dmccodegui/screens/users.py` - UsersScreen and UserEditOverlay classes with try/except ImportError guard
- `src/dmccodegui/ui/users.kv` - KV layout for UsersScreen (header + ScrollView card list) and UserEditOverlay (name/PIN/role fields)
- `src/dmccodegui/screens/__init__.py` - Added UsersScreen export and __all__ entry
- `src/dmccodegui/ui/base.kv` - Added UsersScreen to ScreenManager with name: 'users'
- `src/dmccodegui/main.py` - Added ui/users.kv to KV_FILES, explicit auth_manager/state injection for UsersScreen, 'users' in idle timeout screen list

## Decisions Made

- UsersScreen._rebuild_cards() called on every on_pre_enter — simple, always-correct list refresh (no caching complexity)
- UserEditOverlay uses Clock.schedule_once for field init after open() — ensures widget IDs are bound before text assignment
- Role selector buttons disabled (not hidden) when editing current user — visual cue that self-demotion is blocked per auth_manager validation
- Force logout on self-delete calls state.set_auth("", "operator") — resets auth state; TabBar will reflect operator role on next render

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Task 3 (human-verify checkpoint) must be completed before this plan is formally closed
- After approval: Phase 7 is complete (all AUTH requirements fulfilled)
- Phase 8 (Kiosk) can begin once human verification confirms the full flow works

---
*Phase: 07-admin-and-user-management*
*Completed: 2026-04-06*
