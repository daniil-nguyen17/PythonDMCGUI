"""Unit tests for ControllerPoller.

These tests do NOT require Kivy to be running. Clock.schedule_once and
Clock.schedule_interval are mocked to call callbacks immediately (or no-op
for interval), allowing _do_read / _apply / _on_disconnect to be exercised
synchronously.
"""
from __future__ import annotations

import time
import unittest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers shared across tests
# ---------------------------------------------------------------------------

def _make_mock_controller(cmd_side_effect=None, cmd_return_values=None):
    """Return a MagicMock GalilController.

    If cmd_side_effect is provided it is set directly on mock.cmd.side_effect.
    If cmd_return_values is provided, cmd.side_effect iterates through the list.
    """
    ctrl = MagicMock()
    ctrl.is_connected.return_value = True
    if cmd_side_effect is not None:
        ctrl.cmd.side_effect = cmd_side_effect
    elif cmd_return_values is not None:
        ctrl.cmd.side_effect = iter(cmd_return_values)
    return ctrl


def _make_mock_state():
    """Return a real (importable) MachineState-like object backed by a MagicMock for notify()."""
    from dmccodegui.app_state import MachineState
    state = MachineState()
    state.connected = True
    state.connected_address = "192.168.0.1"
    return state


def _make_poller(ctrl=None, state=None):
    """Construct a ControllerPoller with mocked Clock via patch context."""
    from dmccodegui.hmi.poll import ControllerPoller
    if ctrl is None:
        ctrl = _make_mock_controller()
    if state is None:
        state = _make_mock_state()
    poller = ControllerPoller(ctrl, state)
    return poller, ctrl, state


def _run_do_read_sync(poller):
    """Run _do_read and immediately flush any pending Clock.schedule_once callbacks.

    We patch Clock.schedule_once to call the callback immediately, then call
    _do_read().  This keeps tests synchronous.
    """
    with patch("dmccodegui.hmi.poll.Clock") as mock_clock:
        # schedule_once(fn, *args) -> call fn(0) immediately
        def immediate_schedule_once(fn, *args, **kwargs):
            fn(0)
        mock_clock.schedule_once.side_effect = immediate_schedule_once
        # Rebind the poller's reference
        poller._clock = mock_clock
        poller._do_read()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPollerWritesDmcState(unittest.TestCase):
    """test_poller_writes_dmc_state"""

    def test_poller_writes_dmc_state(self):
        """After one _do_read, state.dmc_state == 2 when controller returns '2.0000'."""
        # Batched response: a, b, c, d, dmc_state, ses_kni, stn_kni, xq_raw
        responses = [
            " 0.0000  0.0000  0.0000  0.0000  2.0000  0.0000  0.0000  0.0000\r\n",
        ]
        ctrl = _make_mock_controller(cmd_return_values=responses)
        state = _make_mock_state()
        poller, _, _ = _make_poller(ctrl, state)

        _run_do_read_sync(poller)

        self.assertEqual(state.dmc_state, 2)


class TestPollerWritesPositions(unittest.TestCase):
    """test_poller_writes_positions"""

    def test_poller_writes_positions(self):
        """After _do_read, state.pos matches the 4 axis values returned by controller."""
        # Batched response: a, b, c, d, dmc_state, ses_kni, stn_kni, xq_raw
        responses = [
            " 100.0000  200.0000  300.0000  400.0000  2.0000  0.0000  0.0000  0.0000\r\n",
        ]
        ctrl = _make_mock_controller(cmd_return_values=responses)
        state = _make_mock_state()
        poller, _, _ = _make_poller(ctrl, state)

        _run_do_read_sync(poller)

        self.assertAlmostEqual(state.pos["A"], 100.0)
        self.assertAlmostEqual(state.pos["B"], 200.0)
        self.assertAlmostEqual(state.pos["C"], 300.0)
        self.assertAlmostEqual(state.pos["D"], 400.0)


class TestPollerWritesKnifeCounts(unittest.TestCase):
    """test_poller_writes_knife_counts"""

    def test_poller_writes_knife_counts(self):
        """After _do_read, session and stone knife counts are set correctly."""
        # Batched response: a, b, c, d, dmc_state, ses_kni, stn_kni, xq_raw
        responses = [
            " 0.0000  0.0000  0.0000  0.0000  1.0000  42.0000  77.0000  0.0000\r\n",
        ]
        ctrl = _make_mock_controller(cmd_return_values=responses)
        state = _make_mock_state()
        poller, _, _ = _make_poller(ctrl, state)

        _run_do_read_sync(poller)

        self.assertEqual(state.session_knife_count, 42)
        self.assertEqual(state.stone_knife_count, 77)


class TestDisconnectAfterThreeFailures(unittest.TestCase):
    """test_disconnect_after_three_failures"""

    def test_disconnect_after_three_failures(self):
        """After 3 consecutive cmd() exceptions, state.connected == False."""
        ctrl = _make_mock_controller(cmd_side_effect=RuntimeError("comm error"))
        state = _make_mock_state()
        poller, _, _ = _make_poller(ctrl, state)

        for _ in range(3):
            _run_do_read_sync(poller)

        self.assertFalse(state.connected)


class TestSingleFailureNoDisconnect(unittest.TestCase):
    """test_single_failure_no_disconnect"""

    def test_single_failure_no_disconnect(self):
        """One failure followed by success keeps state.connected == True."""
        # Batched response for the good call
        good_response = " 0.0000  0.0000  0.0000  0.0000  1.0000  0.0000  0.0000  0.0000\r\n"
        call_count = [0]

        def side_effect(cmd):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("transient error")
            return good_response

        ctrl = _make_mock_controller(cmd_side_effect=side_effect)
        state = _make_mock_state()
        poller, _, _ = _make_poller(ctrl, state)

        # First call: fails (fail_count = 1, below threshold)
        _run_do_read_sync(poller)
        self.assertTrue(state.connected, "Should still be connected after 1 failure")

        # Second call: succeeds (fail_count resets)
        _run_do_read_sync(poller)
        self.assertTrue(state.connected, "Should remain connected after recovery")


class TestReconnectClearsDisconnect(unittest.TestCase):
    """test_reconnect_clears_disconnect"""

    def test_reconnect_clears_disconnect(self):
        """After disconnect (3 failures), a successful poll restores state.connected == True."""
        call_count = [0]
        good_response = " 0.0000  0.0000  0.0000  0.0000  1.0000  0.0000  0.0000  0.0000\r\n"

        def side_effect(cmd):
            call_count[0] += 1
            # First 3 calls raise (trigger disconnect)
            if call_count[0] <= 3:
                raise RuntimeError("comm error")
            return good_response

        ctrl = _make_mock_controller(cmd_side_effect=side_effect)
        ctrl.connect.return_value = True  # reconnect succeeds
        state = _make_mock_state()
        poller, _, _ = _make_poller(ctrl, state)

        # Trigger 3 failures -> disconnect
        for _ in range(3):
            _run_do_read_sync(poller)

        self.assertFalse(state.connected, "Should be disconnected after 3 failures")

        # Next successful read should reconnect
        _run_do_read_sync(poller)

        self.assertTrue(state.connected, "Should be reconnected after successful poll")


class TestPollerStartStop(unittest.TestCase):
    """test_poller_start_stop"""

    def test_poller_start_stop(self):
        """start() creates a clock event; stop() cancels it."""
        from dmccodegui.hmi.poll import ControllerPoller
        ctrl = _make_mock_controller()
        state = _make_mock_state()
        poller = ControllerPoller(ctrl, state)

        with patch("dmccodegui.hmi.poll.Clock") as mock_clock:
            mock_event = MagicMock()
            mock_clock.schedule_interval.return_value = mock_event

            poller.start()

            mock_clock.schedule_interval.assert_called_once()
            # Confirm interval is close to 1/10 = 0.1s
            args, kwargs = mock_clock.schedule_interval.call_args
            self.assertAlmostEqual(args[1], 0.1, places=5)

            poller.stop()

            mock_event.cancel.assert_called_once()


class TestDisconnectClosesHandle(unittest.TestCase):
    """test_disconnect_closes_handle"""

    def test_disconnect_closes_handle(self):
        """After hitting DISCONNECT_THRESHOLD failures, controller.disconnect() is called."""
        ctrl = _make_mock_controller(cmd_side_effect=RuntimeError("comm error"))
        state = _make_mock_state()
        poller, _, _ = _make_poller(ctrl, state)

        for _ in range(3):
            _run_do_read_sync(poller)

        # controller.disconnect should have been submitted to jobs, but since
        # _on_disconnect submits to jobs.submit, we need to verify it was called.
        # The actual call happens via jobs.submit; to keep tests synchronous we
        # patch jobs.submit to call fn immediately during the test.
        # Re-run with jobs patched:
        ctrl2 = _make_mock_controller(cmd_side_effect=RuntimeError("comm error"))
        state2 = _make_mock_state()
        poller2, _, _ = _make_poller(ctrl2, state2)

        with patch("dmccodegui.hmi.poll.jobs") as mock_jobs:
            # make jobs.submit call fn immediately
            mock_jobs.submit.side_effect = lambda fn: fn()

            with patch("dmccodegui.hmi.poll.Clock") as mock_clock:
                def immediate_once(fn, *a, **kw):
                    fn(0)
                mock_clock.schedule_once.side_effect = immediate_once

                for _ in range(3):
                    poller2._do_read()

        ctrl2.disconnect.assert_called_once()


# ---------------------------------------------------------------------------
# Phase 17 — poller stop reset tests
# ---------------------------------------------------------------------------

class TestPollerStopResetsFailCount(unittest.TestCase):
    """Verify stop() resets _fail_count and _disconnect_start unconditionally."""

    def test_stop_resets_fail_count_and_disconnect_start(self):
        """stop() sets _fail_count=0 and _disconnect_start=None after being set."""
        poller, ctrl, state = _make_poller()
        # Simulate state after partial disconnect
        poller._fail_count = 5
        poller._disconnect_start = time.monotonic()

        with patch("dmccodegui.hmi.poll.Clock") as mock_clock:
            mock_event = MagicMock()
            mock_clock.schedule_interval.return_value = mock_event
            poller.start()
            poller.stop()

        self.assertEqual(poller._fail_count, 0,
                         "_fail_count must be reset to 0 by stop()")
        self.assertIsNone(poller._disconnect_start,
                          "_disconnect_start must be reset to None by stop()")


# ---------------------------------------------------------------------------
# Phase 11 — program_running tests
# ---------------------------------------------------------------------------

class TestProgramRunningDefault(unittest.TestCase):
    """test_program_running_default_true"""

    def test_program_running_default_true(self):
        """MachineState().program_running defaults to True."""
        from dmccodegui.app_state import MachineState
        state = MachineState()
        self.assertTrue(state.program_running)


# ---------------------------------------------------------------------------
# Phase 17 — cold-start StatusBar integration test
# ---------------------------------------------------------------------------

class TestColdStartShowsOffline(unittest.TestCase):
    """Fresh MachineState (never polled) must cause StatusBar to show OFFLINE."""

    def test_cold_start_status_bar_shows_offline(self):
        """A brand-new MachineState with defaults drives StatusBar to OFFLINE, not E-STOP."""
        from dmccodegui.app_state import MachineState
        from dmccodegui.screens.status_bar import StatusBar
        state = MachineState()  # Real defaults — connected=False, program_running=True
        sb = StatusBar()
        sb.update_from_state(state)
        self.assertEqual(sb.state_text, "OFFLINE",
                         f"Cold-start should show OFFLINE, got '{sb.state_text}'")


class TestApplySetsProgramRunning(unittest.TestCase):
    """test_apply_sets_program_running"""

    def test_apply_sets_program_running_true(self):
        """_apply(..., program_running=True) sets state.program_running to True."""
        poller, ctrl, state = _make_poller()
        # Call _apply directly with program_running=True
        poller._apply(1, 0.0, 0.0, 0.0, 0.0, 0, 0, True)
        self.assertTrue(state.program_running)

    def test_apply_sets_program_running_false(self):
        """_apply(..., program_running=False) sets state.program_running to False."""
        poller, ctrl, state = _make_poller()
        state.program_running = True  # Set to True first
        poller._apply(1, 0.0, 0.0, 0.0, 0.0, 0, 0, False)
        self.assertFalse(state.program_running)


class TestXQReadFailureDefaultsTrue(unittest.TestCase):
    """test_xq_read_failure_defaults_program_running_true

    With batched reads, _XQ is part of the single batch command.
    When the batch succeeds, xq_raw >= 0 means True; xq_raw < 0 means False.
    program_running=True is the initial MachineState default (conservative).
    """

    def test_program_running_true_when_xq_zero(self):
        """program_running is True when xq_raw=0 (program running on thread 0)."""
        # xq_raw = 0.0000 in batch
        batch = " 0.0000  0.0000  0.0000  0.0000  1.0000  0.0000  0.0000  0.0000\r\n"
        ctrl = _make_mock_controller(cmd_return_values=[batch])
        state = _make_mock_state()
        poller, _, _ = _make_poller(ctrl, state)

        _run_do_read_sync(poller)

        self.assertTrue(state.program_running,
                        "program_running should be True when xq_raw=0")

    def test_program_running_false_when_xq_negative(self):
        """program_running is False when xq_raw=-1 (program not running)."""
        # xq_raw = -1.0000 in batch
        batch = " 0.0000  0.0000  0.0000  0.0000  1.0000  0.0000  0.0000 -1.0000\r\n"
        ctrl = _make_mock_controller(cmd_return_values=[batch])
        state = _make_mock_state()
        poller, _, _ = _make_poller(ctrl, state)
        state.program_running = True

        _run_do_read_sync(poller)

        self.assertFalse(state.program_running,
                         "program_running should be False when xq_raw=-1")

    def test_batch_failure_preserves_program_running(self):
        """When entire batch fails, program_running retains its last known value (stale-on-failure)."""
        ctrl = _make_mock_controller(cmd_side_effect=RuntimeError("comm error"))
        state = _make_mock_state()
        state.program_running = True
        poller, _, _ = _make_poller(ctrl, state)

        _run_do_read_sync(poller)

        self.assertTrue(state.program_running,
                        "program_running preserved (not zeroed) when batch fails")


# ---------------------------------------------------------------------------
# Phase 23-01 — Connection hardening tests
# ---------------------------------------------------------------------------

class TestConnectionHardening(unittest.TestCase):
    """Tests that connect() and reset_handle() pass --direct and --timeout flags to GOpen."""

    def _make_ctrl_with_mock_driver(self):
        """Return a GalilController with a mock driver (GOpen does not raise)."""
        from dmccodegui.controller import GalilController
        mock_driver = MagicMock()
        mock_driver.GOpen.return_value = None  # success
        ctrl = GalilController(driver=mock_driver)
        return ctrl, mock_driver

    def test_connect_passes_direct_and_timeout_flags(self):
        """connect(addr) calls GOpen with '{addr} --direct --timeout 1000 -MG 0'."""
        from dmccodegui.controller import PRIMARY_FLAGS
        ctrl, mock_driver = self._make_ctrl_with_mock_driver()
        ctrl.connect("192.168.0.1")
        mock_driver.GOpen.assert_called_once_with(f"192.168.0.1 {PRIMARY_FLAGS}")

    def test_reset_handle_passes_direct_and_timeout_flags(self):
        """reset_handle(addr) calls GOpen with '{addr} --direct --timeout 1000 -MG 0'."""
        from dmccodegui.controller import PRIMARY_FLAGS
        ctrl, mock_driver = self._make_ctrl_with_mock_driver()
        ctrl._address = "192.168.0.1"
        ctrl._connected = True
        ctrl.reset_handle("192.168.0.1")
        # GOpen should have been called with flags
        calls = mock_driver.GOpen.call_args_list
        self.assertTrue(
            any(f"192.168.0.1 {PRIMARY_FLAGS}" in str(c) for c in calls),
            f"GOpen not called with expected flags. Calls: {calls}"
        )

    def test_reset_handle_no_address_uses_self_address(self):
        """reset_handle() with no address falls back to self._address."""
        from dmccodegui.controller import PRIMARY_FLAGS
        ctrl, mock_driver = self._make_ctrl_with_mock_driver()
        ctrl._address = "192.168.0.99"
        ctrl._connected = True
        ctrl.reset_handle()  # no explicit address
        calls = mock_driver.GOpen.call_args_list
        self.assertTrue(
            any(f"192.168.0.99 {PRIMARY_FLAGS}" in str(c) for c in calls),
            f"GOpen not called with self._address. Calls: {calls}"
        )

    def test_reset_handle_with_explicit_address_uses_that_address(self):
        """reset_handle(addr) uses the given address, not self._address."""
        from dmccodegui.controller import PRIMARY_FLAGS
        ctrl, mock_driver = self._make_ctrl_with_mock_driver()
        ctrl._address = "192.168.0.1"
        ctrl._connected = True
        ctrl.reset_handle("10.0.0.5")
        calls = mock_driver.GOpen.call_args_list
        self.assertTrue(
            any(f"10.0.0.5 {PRIMARY_FLAGS}" in str(c) for c in calls),
            f"GOpen not called with explicit address. Calls: {calls}"
        )

    def test_connect_log_includes_direct_and_timeout(self):
        """connect() logger message includes '--direct' and 'timeout=1000ms'."""
        ctrl, mock_driver = self._make_ctrl_with_mock_driver()
        log_messages = []
        ctrl.set_logger(log_messages.append)
        ctrl.connect("192.168.0.1")
        self.assertTrue(
            any("--direct" in m and "timeout=1000ms" in m for m in log_messages),
            f"Expected log with '--direct' and 'timeout=1000ms'. Got: {log_messages}"
        )


# ---------------------------------------------------------------------------
# Phase 23-01 — Mega-batch read tests
# ---------------------------------------------------------------------------

# Batched response: 8 space-delimited floats
# Order: a, b, c, d, dmc_state, ses_kni, stn_kni, xq_raw
_GOOD_BATCH = " 100.0000  200.0000  300.0000  400.0000  2.0000  42.0000  77.0000  0.0000\r\n"
# xq_raw >= 0 means program_running=True; -1 means False
_BATCH_PROG_FALSE = " 0.0000  0.0000  0.0000  0.0000  1.0000  0.0000  0.0000 -1.0000\r\n"


class TestMegaBatchRead(unittest.TestCase):
    """Tests for the module-level read_all_state() function."""

    def test_returns_tuple_on_success(self):
        """read_all_state returns (a,b,c,d,dmc_state,ses_kni,stn_kni,program_running) on success."""
        from dmccodegui.hmi.poll import read_all_state
        ctrl = _make_mock_controller(cmd_return_values=[_GOOD_BATCH])
        result = read_all_state(ctrl)
        self.assertIsNotNone(result)
        a, b, c, d, dmc_state, ses_kni, stn_kni, program_running = result
        self.assertAlmostEqual(a, 100.0)
        self.assertAlmostEqual(b, 200.0)
        self.assertAlmostEqual(c, 300.0)
        self.assertAlmostEqual(d, 400.0)
        self.assertEqual(dmc_state, 2)
        self.assertEqual(ses_kni, 42)
        self.assertEqual(stn_kni, 77)
        self.assertTrue(program_running)  # xq_raw=0 >= 0

    def test_program_running_false_when_xq_negative(self):
        """read_all_state sets program_running=False when xq_raw < 0."""
        from dmccodegui.hmi.poll import read_all_state
        ctrl = _make_mock_controller(cmd_return_values=[_BATCH_PROG_FALSE])
        result = read_all_state(ctrl)
        self.assertIsNotNone(result)
        self.assertFalse(result[7])

    def test_returns_none_on_exception(self):
        """read_all_state returns None when ctrl.cmd raises Exception."""
        from dmccodegui.hmi.poll import read_all_state
        ctrl = _make_mock_controller(cmd_side_effect=RuntimeError("comm error"))
        result = read_all_state(ctrl)
        self.assertIsNone(result)

    def test_returns_none_when_too_few_values(self):
        """read_all_state returns None when response has fewer than 8 values."""
        from dmccodegui.hmi.poll import read_all_state
        ctrl = _make_mock_controller(cmd_return_values=[" 1.0 2.0 3.0\r\n"])
        result = read_all_state(ctrl)
        self.assertIsNone(result)

    def test_uses_batch_cmd(self):
        """read_all_state calls ctrl.cmd with exactly BATCH_CMD."""
        from dmccodegui.hmi.poll import read_all_state
        from dmccodegui.hmi.dmc_vars import BATCH_CMD
        ctrl = _make_mock_controller(cmd_return_values=[_GOOD_BATCH])
        read_all_state(ctrl)
        ctrl.cmd.assert_called_once_with(BATCH_CMD)

    def test_batch_cmd_uses_tda_not_tpa(self):
        """BATCH_CMD uses _TDA/_TDB/_TDC/_TDD (told position), NOT _TPA/_TPB/_TPC/_TPD."""
        from dmccodegui.hmi.dmc_vars import BATCH_CMD
        self.assertIn("_TDA", BATCH_CMD)
        self.assertIn("_TDB", BATCH_CMD)
        self.assertIn("_TDC", BATCH_CMD)
        self.assertIn("_TDD", BATCH_CMD)
        self.assertNotIn("_TPA", BATCH_CMD)
        self.assertNotIn("_TPB", BATCH_CMD)
        self.assertNotIn("_TPC", BATCH_CMD)
        self.assertNotIn("_TPD", BATCH_CMD)


class TestBatchCallCount(unittest.TestCase):
    """Tests that _do_read() issues exactly 1 ctrl.cmd call on the success path."""

    def test_do_read_calls_cmd_exactly_once(self):
        """_do_read() must call ctrl.cmd exactly 1 time on a successful read."""
        ctrl = _make_mock_controller(cmd_return_values=[_GOOD_BATCH])
        state = _make_mock_state()
        poller, _, _ = _make_poller(ctrl, state)

        _run_do_read_sync(poller)

        self.assertEqual(ctrl.cmd.call_count, 1,
                         f"Expected 1 ctrl.cmd call, got {ctrl.cmd.call_count}")


class TestStaleOnFailure(unittest.TestCase):
    """Tests that failed reads keep last known values and count toward disconnect."""

    def test_fail_increments_fail_count(self):
        """When read_all_state returns None, _do_read increments _fail_count."""
        ctrl = _make_mock_controller(cmd_side_effect=RuntimeError("comm error"))
        state = _make_mock_state()
        poller, _, _ = _make_poller(ctrl, state)

        _run_do_read_sync(poller)

        self.assertEqual(poller._fail_count, 1)

    def test_fail_does_not_call_apply(self):
        """When read_all_state returns None, _apply is never called (values preserved)."""
        ctrl = _make_mock_controller(cmd_side_effect=RuntimeError("comm error"))
        state = _make_mock_state()
        poller, _, _ = _make_poller(ctrl, state)

        # Record state before
        state.pos["A"] = 99.0
        state.dmc_state = 7

        _run_do_read_sync(poller)

        # Values must NOT have changed
        self.assertAlmostEqual(state.pos["A"], 99.0,
                               msg="Last known A position must be preserved on failure")
        self.assertEqual(state.dmc_state, 7,
                         msg="Last known dmc_state must be preserved on failure")

    def test_threshold_fires_on_disconnect(self):
        """When _fail_count reaches DISCONNECT_THRESHOLD, _on_disconnect is scheduled."""
        from dmccodegui.hmi.poll import DISCONNECT_THRESHOLD
        ctrl = _make_mock_controller(cmd_side_effect=RuntimeError("comm error"))
        state = _make_mock_state()
        poller, _, _ = _make_poller(ctrl, state)

        for _ in range(DISCONNECT_THRESHOLD):
            _run_do_read_sync(poller)

        self.assertFalse(state.connected,
                         "state.connected must be False after DISCONNECT_THRESHOLD failures")


if __name__ == "__main__":
    unittest.main()
