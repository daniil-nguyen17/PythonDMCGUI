# Phase 17: Poll Reset and Cold-Start Fix - Research

**Researched:** 2026-04-07
**Domain:** Internal bug fixes — ControllerPoller lifecycle and MachineState cold-start defaults
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Fail count reset
- Reset `_fail_count = 0` and `_disconnect_start = None` in `ControllerPoller.stop()`
- This covers disconnect_and_refresh, app shutdown, and any future stop/start cycle
- Single reset point in stop() — not in start(), not in both

#### Cold-start label fix
- Set `program_running = True` as the default in `MachineState.__init__`
- This makes cold-start (not connected + program_running=True) show OFFLINE (gray), not E-STOP (red)
- After a real E-STOP (ST+HX kills DMC program), poll sets program_running=False correctly — E-STOP label appears only after actual emergency stop
- Matches Phase 11 conservative default pattern ("assume running if uncertain")

#### Test coverage
- Unit test: create poller, simulate failures to increment _fail_count, call stop(), assert _fail_count == 0 and _disconnect_start is None
- Cold-start test: on fresh MachineState (never polled), StatusBar.update_from_state shows OFFLINE not E-STOP
- RECOVER chain test: cold-start recover_enabled=False (not connected), after E-STOP disconnect recover_enabled=False, after reconnect with program stopped recover_enabled=True

### Claude's Discretion
- Exact test structure and naming
- Whether to add integration-style test combining both fixes
- Any additional edge cases discovered during implementation

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| POLL-03 | HMI detects controller connection loss and displays disconnected status | _fail_count reset ensures clean reconnect cycle; stop() is the definitive reset point — covers all paths (disconnect_and_refresh, on_stop, future cycles) |
| UI-02 | Status label displays current controller state (IDLE, GRINDING, SETUP, HOMING, NEW SESSION) | Cold-start default program_running=True ensures status bar reads OFFLINE on first render; real E-STOP sets program_running=False after first poll |
</phase_requirements>

---

## Summary

Phase 17 is two narrow, self-contained bug fixes with no external dependencies and no new libraries. Both bugs share a root cause: incorrect default values that produce wrong UI before the first successful controller poll.

Fix 1 (POLL-03): `ControllerPoller.stop()` currently cancels the clock event but leaves `_fail_count` and `_disconnect_start` dirty. When `disconnect_and_refresh()` calls `_stop_poller()` and then `_start_poller()`, the next reconnect cycle inherits accumulated failure count, potentially triggering a premature disconnect callback on the first read. Adding two reset lines to `stop()` closes this.

Fix 2 (UI-02): `MachineState.program_running` defaults to `False` (line 49 of app_state.py). StatusBar's `update_from_state()` interprets `connected=False AND program_running=False` as E-STOP (red). This means the app shows E-STOP before any connection is ever attempted — a misleading alarm state. Changing the default to `True` makes cold-start show OFFLINE (gray), which is honest. The E-STOP label will still appear correctly after a real emergency stop because the poll loop reads `_XQ` and sets `program_running=False` at that point.

There is one test that already asserts `program_running` defaults to `False` (`TestProgramRunningDefault` in test_poll.py line 312-315). Changing the default requires updating that assertion.

**Primary recommendation:** Two one-line production changes + targeted test additions + one test assertion fix. No architecture changes.

---

## Standard Stack

No new libraries. Phase uses existing project stack only.

| Component | Version | Purpose |
|-----------|---------|---------|
| Python stdlib `unittest` | 3.13 | Poller tests (existing test_poll.py pattern) |
| pytest | 9.0.2 | Test runner (existing test_status_bar.py uses pytest-style classes) |
| Kivy `Clock` | project version | Mocked in tests via `patch("dmccodegui.hmi.poll.Clock")` |

**No new installs required.**

---

## Architecture Patterns

### Existing Code Locations

| File | Line | What to change |
|------|------|----------------|
| `src/dmccodegui/hmi/poll.py` | 68–72 (stop method) | Add `self._fail_count = 0` and `self._disconnect_start = None` after `self._clock_event = None` |
| `src/dmccodegui/app_state.py` | 49 | Change `program_running: bool = False` to `program_running: bool = True` |
| `tests/test_poll.py` | 312–315 | Update `TestProgramRunningDefault` assertion from `assertFalse` to `assertTrue` |

### ControllerPoller.stop() — Current vs Target

Current:
```python
def stop(self) -> None:
    """Stop polling. Safe to call even if not started."""
    if self._clock_event is not None:
        self._clock_event.cancel()
        self._clock_event = None
```

Target (two lines added):
```python
def stop(self) -> None:
    """Stop polling. Safe to call even if not started."""
    if self._clock_event is not None:
        self._clock_event.cancel()
        self._clock_event = None
    self._fail_count = 0
    self._disconnect_start = None
```

The reset lines run unconditionally — if stop() is called when already stopped, the reset is still safe (idempotent). This is intentional: belt-and-suspenders safety for any future caller.

### MachineState.program_running — Current vs Target

Current (app_state.py line 49):
```python
program_running: bool = False
```

Target:
```python
program_running: bool = True
```

This is consistent with the Phase 11 conservative pattern already established in `_do_read()` — when `_XQ` read fails, `program_running` defaults to `True` (line 138 of poll.py). The dataclass field default should match this conservative posture.

### StatusBar cold-start logic (READ-ONLY — no changes needed)

Lines 112–116 of status_bar.py already handle the two disconnected cases correctly:
```python
if not connected:
    if not program_running:
        label, color = "E-STOP", [0.9, 0.2, 0.2, 1]
    else:
        label, color = "OFFLINE", [0.55, 0.55, 0.55, 1]
```

With `program_running` defaulting to `True`, `connected=False AND program_running=True` routes to OFFLINE. No StatusBar code changes needed.

### Threading Safety Note

`stop()` runs on the Kivy main thread. `_fail_count` and `_disconnect_start` are written from the jobs worker thread inside `_do_read()`. However, `stop()` is only called after `_clock_event.cancel()` has executed — meaning no new `_on_tick` callbacks will fire, and any in-flight `_do_read()` on the worker will complete without queuing another callback. The race window is negligible and matches the existing pattern: if a `_do_read()` is in-flight when `stop()` runs, it may write `_fail_count` after the reset, but the clock is already cancelled so no further ticks will observe that count. This is the same reasoning noted in CONTEXT.md.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Mocking Clock in tests | Custom async harness | `patch("dmccodegui.hmi.poll.Clock")` with `side_effect` pattern (already established in test_poll.py) |
| State assertions | Custom state diffing | Direct field access on real `MachineState()` instances |

---

## Common Pitfalls

### Pitfall 1: Reset only in `start()` instead of `stop()`
**What goes wrong:** If reset is placed in `start()`, a stop() followed by delayed start() would carry dirty state into the gap. Also, `on_stop()` calls `_stop_poller()` without a subsequent `start()` — reset in start() would miss app shutdown cleanup.
**How to avoid:** Keep reset exclusively in `stop()` per locked decision.

### Pitfall 2: Forgetting the existing `TestProgramRunningDefault` assertion
**What goes wrong:** Changing `program_running` default to `True` breaks `test_program_running_default_false` at test_poll.py line 312–315 without a corresponding fix.
**How to avoid:** Update the assertion from `assertFalse` to `assertTrue` in the same plan task as the app_state.py change.

### Pitfall 3: The `_make_state()` helper in test_status_bar.py already uses `program_running=True`
**What to know:** `_make_state()` at line 24 of test_status_bar.py already sets `program_running=True` as its default. This means existing status bar tests are written against the correct behavior. No test_status_bar.py changes are needed — the existing tests already pass with `program_running=True`.

### Pitfall 4: New cold-start test must use a fresh `MachineState()` — not `_make_state()`
**What goes wrong:** The test helper `_make_state()` uses `types.SimpleNamespace`, not a real `MachineState`. The cold-start test for POLL-03/UI-02 must instantiate `MachineState()` directly to test the real default value.
**How to avoid:** In the new test, do `from dmccodegui.app_state import MachineState; state = MachineState()` and assert `state.program_running is True`.

### Pitfall 5: RECOVER chain test logic
**What to know:** `recover_enabled` in StatusBar (line 87) is `connected and not program_running`. The three RECOVER states to test are:
- Cold-start: `connected=False`, `program_running=True` → `recover_enabled=False` (correct: not connected)
- Post E-STOP disconnect: `connected=False`, `program_running=False` → `recover_enabled=False` (correct: not connected)
- Reconnect with stopped program: `connected=True`, `program_running=False` → `recover_enabled=True` (correct: show RECOVER button)

---

## Code Examples

### Test: fail_count reset on stop

```python
class TestPollerStopResetsFailCount(unittest.TestCase):
    def test_stop_resets_fail_count_and_disconnect_start(self):
        """stop() resets _fail_count to 0 and _disconnect_start to None."""
        import time
        poller, ctrl, state = _make_poller()
        # Simulate accumulated failure state
        poller._fail_count = 5
        poller._disconnect_start = time.monotonic()

        # stop() should reset both
        with patch("dmccodegui.hmi.poll.Clock"):
            poller.stop()

        self.assertEqual(poller._fail_count, 0)
        self.assertIsNone(poller._disconnect_start)
```

### Test: cold-start MachineState shows OFFLINE

```python
class TestColdStartStatusBar(unittest.TestCase):
    def test_cold_start_shows_offline_not_estop(self):
        """Fresh MachineState (never polled) shows OFFLINE on StatusBar."""
        from dmccodegui.app_state import MachineState
        from dmccodegui.screens.status_bar import StatusBar
        state = MachineState()
        sb = StatusBar()
        sb.update_from_state(state)
        self.assertEqual(sb.state_text, "OFFLINE")
```

### Test: RECOVER chain

```python
def test_recover_enabled_chain(self):
    """recover_enabled is False at cold-start, False after E-STOP, True after reconnect."""
    from dmccodegui.screens.status_bar import StatusBar
    sb = StatusBar()

    # Cold-start: not connected, program_running=True (new default)
    state_cold = _make_state(connected=False, program_running=True)
    sb.update_from_state(state_cold)
    assert sb.recover_enabled is False

    # Post E-STOP: not connected, program_running=False
    state_estop = _make_state(connected=False, program_running=False)
    sb.update_from_state(state_estop)
    assert sb.recover_enabled is False

    # Reconnect with stopped program: connected, program_running=False
    state_recover = _make_state(connected=True, program_running=False)
    sb.update_from_state(state_recover)
    assert sb.recover_enabled is True
```

---

## Validation Architecture

nyquist_validation is enabled in config.json.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pytest.ini or pyproject.toml (existing) |
| Quick run command | `pytest tests/test_poll.py tests/test_status_bar.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| POLL-03 | _fail_count reset to 0 after stop() | unit | `pytest tests/test_poll.py::TestPollerStopResetsFailCount -x` | Wave 0 (new class) |
| POLL-03 | _disconnect_start reset to None after stop() | unit | `pytest tests/test_poll.py::TestPollerStopResetsFailCount -x` | Wave 0 (new class) |
| UI-02 | Fresh MachineState shows OFFLINE, not E-STOP | unit | `pytest tests/test_poll.py::TestColdStartStatusBar -x` | Wave 0 (new class) |
| UI-02 | RECOVER chain: cold/E-STOP/reconnect states | unit | `pytest tests/test_status_bar.py -k recover_chain -x` | Wave 0 (new test) |
| UI-02 | program_running defaults True | unit | `pytest tests/test_poll.py::TestProgramRunningDefault -x` | ✅ (update assertion) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_poll.py tests/test_status_bar.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `TestPollerStopResetsFailCount` class in `tests/test_poll.py` — covers POLL-03
- [ ] `TestColdStartStatusBar` class in `tests/test_poll.py` (or test_status_bar.py) — covers UI-02 cold-start
- [ ] `test_recover_enabled_chain` in `tests/test_status_bar.py` — covers UI-02 RECOVER chain
- [ ] Update `TestProgramRunningDefault.test_program_running_default_false` assertion to `assertTrue` after default changes to `True`

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| program_running defaults False | program_running defaults True | Phase 17 | Cold-start shows OFFLINE instead of E-STOP |
| stop() only cancels clock event | stop() also resets _fail_count / _disconnect_start | Phase 17 | Reconnect cycles start with clean failure count |

---

## Open Questions

None. Both fixes are fully specified by the locked decisions in CONTEXT.md and verified against the existing source code.

---

## Sources

### Primary (HIGH confidence)
- `src/dmccodegui/hmi/poll.py` — ControllerPoller implementation, stop() at line 68, _fail_count at line 54, _disconnect_start at line 55
- `src/dmccodegui/app_state.py` — MachineState dataclass, program_running default at line 49
- `src/dmccodegui/screens/status_bar.py` — update_from_state() disconnected branch at lines 112–116
- `tests/test_poll.py` — existing test patterns, TestProgramRunningDefault at line 308
- `tests/test_status_bar.py` — existing StatusBar test patterns, _make_state() helper

### Secondary (MEDIUM confidence)
- `.planning/phases/17-poll-reset-cold-start-fix/17-CONTEXT.md` — locked implementation decisions from /gsd:discuss-phase
- `.planning/STATE.md` — Phase 11 conservative default decision recorded at line 126

---

## Metadata

**Confidence breakdown:**
- Production changes: HIGH — exact lines identified in source, behavior fully understood
- Test gaps: HIGH — existing test helpers and patterns directly reusable
- Threading safety: HIGH — same reasoning as Phase 10/11 decisions in STATE.md

**Research date:** 2026-04-07
**Valid until:** Stable (pure internal code, no external dependencies)
