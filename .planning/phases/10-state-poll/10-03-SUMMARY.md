---
phase: 10-state-poll
plan: 03
subsystem: ui
tags: [kivy, machine-state, subscription, run-screen, knife-count, disconnect-banner]

# Dependency graph
requires:
  - phase: 10-state-poll
    plan: 01
    provides: "MachineState with subscribe/notify, session_knife_count, stone_knife_count, cycle_running @property"

provides:
  - "RunScreen as pure view driven by MachineState subscription (no own polling loop)"
  - "session_knife_count and stone_knife_count labels visible in cycle status area"
  - "Red DISCONNECTED banner with elapsed-time counter at top of RunScreen"
  - "Auto-clearing disconnect banner on reconnect"

affects:
  - 11-estop-safety
  - 12-run-page-wiring

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "MachineState.subscribe() returns unsubscribe callable — store in _state_unsub, call in on_leave"
    - "Clock.schedule_once lambda bridging: subscribe lambda posts to main thread via Clock.schedule_once"
    - "_apply_state is single path for all Kivy property updates from controller state"
    - "Disconnect timer uses monotonic time, 1 Hz Clock.schedule_interval, cancels on reconnect"

key-files:
  created: []
  modified:
    - src/dmccodegui/screens/run.py
    - src/dmccodegui/ui/run.kv
    - tests/test_run_screen.py

key-decisions:
  - "test_plot_buffer_only_during_cycle updated to call _apply_state with MachineState instead of deleted _apply_ui — keeps test intent identical but uses new API"

patterns-established:
  - "Screen subscription pattern: on_pre_enter subscribes, on_leave unsubscribes, _apply_state handles all property updates"
  - "Disconnect elapsed timer: monotonic t0 stored on first disconnect, 1 Hz tick updates StringProperty, cleared on reconnect"

requirements-completed: [POLL-02, POLL-03, POLL-04]

# Metrics
duration: 8min
completed: 2026-04-06
---

# Phase 10 Plan 03: RunScreen MachineState Subscription Summary

**RunScreen migrated from 10 Hz self-poll to MachineState subscription with knife count labels (SESSION KNIVES / STONE KNIVES) and a red auto-clearing DISCONNECTED elapsed-time banner**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-06T04:57:00Z
- **Completed:** 2026-04-06T04:57:51Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Removed `_do_poll`, `_update_clock`, `_apply_ui`, `_read_cpm_values` methods — RunScreen no longer polls the controller directly
- Added `_apply_state(s: MachineState)` as the single path for updating all Kivy properties from subscription notifications
- Added `session_knife_count`, `stone_knife_count`, and `disconnect_banner` StringProperties with full KV bindings
- Disconnect banner in `run.kv` collapses to 0 height when connected, expands to 40dp red bar when disconnected with elapsed seconds counter
- Knife count section added to Cycle Status card (SESSION KNIVES + STONE KNIVES in same 2-col grid style as existing fields)
- All 206 tests green after updating `test_plot_buffer_only_during_cycle` to use `_apply_state` API

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate RunScreen from polling to MachineState subscription** - `0ea72b0` (feat)
2. **Task 2: Add knife count labels and disconnect banner to run.kv** - `77c38fd` (feat)

## Files Created/Modified

- `src/dmccodegui/screens/run.py` - Replaced polling infrastructure with MachineState subscription; added `_apply_state`, `_tick_disconnect_banner`, `session_knife_count`, `stone_knife_count`, `disconnect_banner` properties; removed `_update_clock_event` class attribute
- `src/dmccodegui/ui/run.kv` - Added disconnect banner widget at top of layout; added SESSION KNIVES / STONE KNIVES labels in cycle status card; increased card height 280->340dp (serration) and 180->240dp (flat)
- `tests/test_run_screen.py` - Updated `test_plot_buffer_only_during_cycle` to use `_apply_state` with MachineState instead of deleted `_apply_ui`

## Decisions Made

- `test_plot_buffer_only_during_cycle` updated to call `_apply_state` with a real `MachineState` object (STATE_IDLE vs STATE_GRINDING) rather than `_apply_ui` with raw dicts — test intent preserved, API updated to match new implementation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test using deleted _apply_ui to use _apply_state**
- **Found during:** Task 1 (RunScreen migration)
- **Issue:** `test_plot_buffer_only_during_cycle` called `r._apply_ui(pos_dict, cycle_dict)` directly; `_apply_ui` was deleted by the migration
- **Fix:** Replaced test body to call `r._apply_state(s)` with a `MachineState(connected=True, dmc_state=STATE_IDLE/STATE_GRINDING, pos=...)` — same behavioral assertion, updated to new API
- **Files modified:** tests/test_run_screen.py
- **Verification:** All 19 run_screen + machine_state_cycle tests pass; 206 total pass
- **Committed in:** `0ea72b0` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug: stale test reference to deleted method)
**Impact on plan:** Necessary for test suite to remain green after removing `_apply_ui`. No scope creep.

## Issues Encountered

None beyond the stale test reference above.

## Next Phase Readiness

- RunScreen is a pure subscriber of MachineState — no controller reads happen on this screen
- The centralized poller (Plan 01) owns all controller reads; RunScreen only reacts
- Ready for Phase 11 (E-STOP Safety) and Phase 12 (Run Page Wiring) which can set RunScreen properties via MachineState without touching RunScreen internals

---
*Phase: 10-state-poll*
*Completed: 2026-04-06*
