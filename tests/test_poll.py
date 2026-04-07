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
        responses = [
            " 2.0000\r\n",   # MG hmiState
            " 0.0000\r\n",   # MG _TPA
            " 0.0000\r\n",   # MG _TPB
            " 0.0000\r\n",   # MG _TPC
            " 0.0000\r\n",   # MG _TPD
            " 0.0000\r\n",   # MG ctSesKni
            " 0.0000\r\n",   # MG ctStnKni
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
        responses = [
            " 2.0000\r\n",     # MG hmiState
            " 100.0000\r\n",   # MG _TPA
            " 200.0000\r\n",   # MG _TPB
            " 300.0000\r\n",   # MG _TPC
            " 400.0000\r\n",   # MG _TPD
            " 0.0000\r\n",     # MG ctSesKni
            " 0.0000\r\n",     # MG ctStnKni
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
        responses = [
            " 1.0000\r\n",   # MG hmiState
            " 0.0000\r\n",   # MG _TPA
            " 0.0000\r\n",   # MG _TPB
            " 0.0000\r\n",   # MG _TPC
            " 0.0000\r\n",   # MG _TPD
            " 42.0000\r\n",  # MG ctSesKni
            " 77.0000\r\n",  # MG ctStnKni
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
        # First call raises; subsequent calls succeed
        good_responses = [
            " 1.0000\r\n",
            " 0.0000\r\n",
            " 0.0000\r\n",
            " 0.0000\r\n",
            " 0.0000\r\n",
            " 0.0000\r\n",
            " 0.0000\r\n",
        ]
        call_count = [0]

        def side_effect(cmd):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("transient error")
            idx = (call_count[0] - 2) % len(good_responses)
            return good_responses[idx]

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

        good_responses = [
            " 1.0000\r\n",
            " 0.0000\r\n",
            " 0.0000\r\n",
            " 0.0000\r\n",
            " 0.0000\r\n",
            " 0.0000\r\n",
            " 0.0000\r\n",
        ]

        def side_effect(cmd):
            call_count[0] += 1
            # First 3 calls raise (trigger disconnect)
            if call_count[0] <= 3:
                raise RuntimeError("comm error")
            # After that: succeed
            idx = (call_count[0] - 4) % len(good_responses)
            return good_responses[idx]

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
    """test_xq_read_failure_defaults_program_running_true"""

    def test_xq_read_failure_defaults_program_running_true(self):
        """If MG _XQ fails in _do_read, program_running defaults to True (conservative)."""
        # Provide good responses for the 7 normal reads
        good_responses = [
            " 1.0000\r\n",   # MG hmiState
            " 0.0000\r\n",   # MG _TPA
            " 0.0000\r\n",   # MG _TPB
            " 0.0000\r\n",   # MG _TPC
            " 0.0000\r\n",   # MG _TPD
            " 0.0000\r\n",   # MG ctSesKni
            " 0.0000\r\n",   # MG ctStnKni
        ]

        call_count = [0]

        def side_effect(cmd):
            call_count[0] += 1
            if "MG _XQ" in cmd:
                raise RuntimeError("XQ read failure")
            idx = (call_count[0] - 1) % len(good_responses)
            return good_responses[idx]

        ctrl = _make_mock_controller(cmd_side_effect=side_effect)
        state = _make_mock_state()
        poller, _, _ = _make_poller(ctrl, state)

        _run_do_read_sync(poller)

        self.assertTrue(state.program_running,
                        "program_running should be True (conservative) when _XQ read fails")

    def test_xq_failure_does_not_increment_fail_count(self):
        """_XQ read failure must NOT increment _fail_count (isolated try/except)."""
        good_responses = [
            " 1.0000\r\n",
            " 0.0000\r\n",
            " 0.0000\r\n",
            " 0.0000\r\n",
            " 0.0000\r\n",
            " 0.0000\r\n",
            " 0.0000\r\n",
        ]

        call_count = [0]

        def side_effect(cmd):
            call_count[0] += 1
            if "MG _XQ" in cmd:
                raise RuntimeError("XQ read failure")
            idx = (call_count[0] - 1) % len(good_responses)
            return good_responses[idx]

        ctrl = _make_mock_controller(cmd_side_effect=side_effect)
        state = _make_mock_state()
        poller, _, _ = _make_poller(ctrl, state)

        # Run multiple times — _fail_count should never increment because of _XQ
        for _ in range(5):
            _run_do_read_sync(poller)

        self.assertEqual(poller._fail_count, 0,
                         "_fail_count must stay 0 — _XQ failures are isolated")


if __name__ == "__main__":
    unittest.main()
