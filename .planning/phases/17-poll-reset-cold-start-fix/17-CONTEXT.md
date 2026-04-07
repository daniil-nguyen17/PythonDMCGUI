# Phase 17: Poll Reset and Cold-Start Fix - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Two specific bug fixes in the poll/status bar connection lifecycle: (1) reset `_fail_count` on poller stop so reconnection starts clean, and (2) fix cold-start status bar to show OFFLINE instead of E-STOP before first connection. Gap closure from v2.0 milestone audit.

</domain>

<decisions>
## Implementation Decisions

### Fail count reset
- Reset `_fail_count = 0` and `_disconnect_start = None` in `ControllerPoller.stop()`
- This covers disconnect_and_refresh, app shutdown, and any future stop/start cycle
- Single reset point in stop() — not in start(), not in both

### Cold-start label fix
- Set `program_running = True` as the default in `MachineState.__init__`
- This makes cold-start (not connected + program_running=True) show OFFLINE (gray), not E-STOP (red)
- After a real E-STOP (ST+HX kills DMC program), poll sets program_running=False correctly — E-STOP label appears only after actual emergency stop
- Matches Phase 11 conservative default pattern ("assume running if uncertain")

### Test coverage
- Unit test: create poller, simulate failures to increment _fail_count, call stop(), assert _fail_count == 0 and _disconnect_start is None
- Cold-start test: on fresh MachineState (never polled), StatusBar.update_from_state shows OFFLINE not E-STOP
- RECOVER chain test: cold-start recover_enabled=False (not connected), after E-STOP disconnect recover_enabled=False, after reconnect with program stopped recover_enabled=True

### Claude's Discretion
- Exact test structure and naming
- Whether to add integration-style test combining both fixes
- Any additional edge cases discovered during implementation

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ControllerPoller` (hmi/poll.py): stop() method exists at line 68 — add reset lines there
- `StatusBar` (screens/status_bar.py): update_from_state() line 73 — cold-start logic at lines 112-116
- `MachineState` (app_state.py): constructor where program_running default is set
- Existing test_poll.py: has _fail_count tests (test_xq_failure_does_not_increment_fail_count)
- Existing test_status_bar.py: has status bar state tests

### Established Patterns
- _fail_count is only written from background thread (jobs FIFO single-worker) — stop() runs on main thread but only when clock event is cancelled (no race)
- StatusBar uses `_prev_*` cache pattern to skip redundant UI updates
- Phase 11 pattern: program_running defaults True when uncertain (conservative)

### Integration Points
- `disconnect_and_refresh()` in main.py calls `_stop_poller()` — the reset happens inside stop()
- MachineState.program_running is read by StatusBar, RunScreen, and poller._apply()

</code_context>

<specifics>
## Specific Ideas

No specific requirements — both fixes are well-defined by success criteria and the audit findings.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 17-poll-reset-cold-start-fix*
*Context gathered: 2026-04-07*
