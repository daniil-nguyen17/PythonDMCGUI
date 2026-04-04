---
phase: 01-auth-and-navigation
plan: 03
subsystem: auth-ui
tags: [kivy, modalview, pin-auth, role-gating, idle-timer]

# Dependency graph
requires:
  - 01-01 (AuthManager, MachineState auth fields)
  - 01-02 (TabBar, StatusBar, ScreenManager shell)
provides:
  - PINOverlay ModalView widget with numpad, dot masking, shake animation
  - Fullscreen login PIN flow: blocks app until authenticated
  - Role-gated tab bar: operator/setup/admin tab sets
  - User switching from StatusBar user/role area
  - Setup/Admin role elevation on restricted tab tap
  - 30-minute idle auto-lock returning to Operator view
  - Auth state reset on disconnect
affects:
  - All phases (auth state flows through MachineState to every screen)
  - 02-run-screen (must not require auth — already on run tab after login)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PINOverlay(ModalView): open_for_login/unlock/switch pattern for reusable overlay"
    - "TabBar._tabs_for_role staticmethod: pure Python, testable without Kivy"
    - "TabBar.set_restricted_callback: deferred callback from main.py for restricted tabs"
    - "StatusBar.bind_user_tap: wires user button to app callback from Python side"
    - "Window.bind(on_touch_down) + Clock.schedule_once: idle auto-lock pattern"
    - "Shake Animation: chained Animation with + operator on pin_card.x"

key-files:
  created:
    - src/dmccodegui/screens/pin_overlay.py
    - src/dmccodegui/ui/pin_overlay.kv
    - tests/test_tab_bar.py
  modified:
    - src/dmccodegui/main.py
    - src/dmccodegui/screens/tab_bar.py
    - src/dmccodegui/screens/status_bar.py
    - src/dmccodegui/ui/status_bar.kv
    - src/dmccodegui/screens/__init__.py

key-decisions:
  - "PINOverlay user list uses opacity/disabled swap on numpad_layout vs user_list_layout — avoids removing/re-adding widgets which can lose KV bindings"
  - "TabBar defaults to operator (not admin) from Plan 03 onward — real auth replaces the temporary admin default from Plan 02"
  - "StatusBar.bind_user_tap called from main.py build() so callback is app-scoped; on_user_tap in KV calls root.on_user_tap() to support pre-bind and post-bind scenarios"
  - "_tabs_for_role implemented as staticmethod on TabBar class — tests import the class but use the method directly without Kivy event loop"

# Metrics
duration: 4min
completed: 2026-04-04
---

# Phase 1 Plan 03: PIN Overlay + Auth Flow Summary

**Fullscreen ModalView PIN overlay with numpad, dot masking, shake animation, user switching, role-gated tabs, and 30-minute idle auto-lock wired into the Kivy app**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-04T06:30:59Z
- **Completed:** 2026-04-04T06:34:35Z
- **Tasks:** 2
- **Files modified:** 8 (3 created, 5 modified)

## Accomplishments

- `PINOverlay(ModalView)`: `press_digit`, `press_backspace`, `press_enter`, shake animation on wrong PIN, user list swap via opacity/disabled
- `open_for_login`, `open_for_unlock`, `open_for_switch` helper methods for three distinct overlay modes
- `pin_overlay.kv`: fullscreen dark overlay (`overlay_color: 0.031, 0.047, 0.071, 0.95`), centered card with AnchorLayout (no `pos_hint` on card per research Pitfall 2), 3x4 numpad, user list ScrollView
- `TabBar._tabs_for_role` promoted to `staticmethod` — pure Python, tested without Kivy
- `TabBar.set_restricted_callback` — plugs in callback from `main.py` for restricted tab tap
- `StatusBar.bind_user_tap` + `on_user_tap` + `user_btn` KV id — user/role area tap opens switch overlay
- `main.py`: `AuthManager` constructed in `__init__`, `PINOverlay` in `build()`, full login/unlock/switch dispatch, `disconnect_and_refresh` resets auth, idle auto-lock via `Window.bind(on_touch_down)` with 30-minute `Clock.schedule_once`
- All 22 tests pass (5 new tab_bar tests + 17 existing)

## Task Commits

Each task was committed atomically:

1. **Task 1: PINOverlay widget (Python + KV)** — `e969b59` (feat)
2. **TDD RED: tab bar role filtering tests** — `79cf6b6` (test)
3. **Task 2: Wire auth flow in main.py + role-gated tabs** — `088f53b` (feat)

## Files Created/Modified

- `src/dmccodegui/screens/pin_overlay.py` — PINOverlay ModalView with all PIN logic
- `src/dmccodegui/ui/pin_overlay.kv` — fullscreen overlay KV rule
- `src/dmccodegui/screens/__init__.py` — PINOverlay exported
- `src/dmccodegui/main.py` — auth flow, idle timer, PIN overlay wiring
- `src/dmccodegui/screens/tab_bar.py` — _tabs_for_role staticmethod, set_restricted_callback
- `src/dmccodegui/screens/status_bar.py` — bind_user_tap, on_user_tap
- `src/dmccodegui/ui/status_bar.kv` — user_btn id + on_release wired
- `tests/test_tab_bar.py` — 5 unit tests for role tab filtering (no Kivy required)

## Decisions Made

- PINOverlay user list uses `opacity`/`disabled` swap on `numpad_layout` vs `user_list_layout` — avoids removing/re-adding widgets which can lose KV id bindings
- `TabBar` now defaults to `operator` role from Plan 03 onward (replaces the temporary `admin` default from Plan 02)
- `StatusBar.bind_user_tap` is called from `main.py` `build()` after the KV tree exists; `user_btn` in KV also calls `root.on_user_tap()` to ensure both paths work
- `_tabs_for_role` implemented as `staticmethod` — tests can import the method directly without triggering Kivy Window/GL init

## Deviations from Plan

### Auto-added Methods

**1. [Rule 2 - Missing functionality] StatusBar.bind_user_tap / on_user_tap**
- **Found during:** Task 2
- **Issue:** Plan specified wiring StatusBar user tap to switch overlay but StatusBar had no mechanism to receive the app callback. The KV button existed but had no id and no on_release hook.
- **Fix:** Added `bind_user_tap(cb)`, `on_user_tap()` methods to StatusBar; added `id: user_btn` and `on_release: root.on_user_tap()` to status_bar.kv
- **Files modified:** `status_bar.py`, `status_bar.kv`
- **Commit:** `088f53b`

## Issues Encountered

None — all automation ran cleanly. The bind_user_tap addition was a minor forward-looking necessity (Rule 2), not a blocker.

## User Setup Required

None — PIN overlay will appear automatically on next app launch when connected. Default users are pre-created in `auth/users.json` on first run.

## Next Phase Readiness

- Plan 03 complete — full auth flow is live: PIN overlay on startup, role-gated tabs, user switching, idle auto-lock
- Plan 04 (final plan in phase) can now be executed — remaining task is integration testing the complete flow
- All placeholder screens (Run, Axes Setup, Parameters, Diagnostics) remain ready for phase 2-5 content injection
- StatusBar correctly shows current user/role after login via `state.notify()` -> `update_from_state()`

---
*Phase: 01-auth-and-navigation*
*Completed: 2026-04-04*
