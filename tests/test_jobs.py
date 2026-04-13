"""Unit tests for JobThread.submit_urgent() and GalilController.reset_handle().

Tests are designed to run fast (<2s each) using threading synchronization primitives.
"""
from __future__ import annotations

import threading
import time
import unittest
from unittest.mock import MagicMock, call, patch


# ---------------------------------------------------------------------------
# submit_urgent tests
# ---------------------------------------------------------------------------

class TestSubmitUrgent(unittest.TestCase):
    """Tests for JobThread.submit_urgent() priority queue behavior."""

    def setUp(self):
        """Create a fresh JobThread for each test (not using global instance)."""
        from dmccodegui.utils.jobs import JobThread
        self.jt = JobThread()

    def tearDown(self):
        self.jt.stop(timeout=2.0)

    def test_submit_urgent_runs_before_normal(self):
        """submit_urgent preempts queued normal jobs — URGENT appears before a,b,c."""
        results = []
        done = threading.Event()

        # Blocker: hold the worker so we can queue up jobs before they drain
        blocker = threading.Event()

        def block_job():
            blocker.wait(timeout=2.0)

        def make_appender(val):
            def fn():
                results.append(val)
            return fn

        def urgent_fn():
            results.append("URGENT")

        def signal_done():
            done.set()

        # Submit blocker first so normal jobs queue up behind it
        self.jt.submit(block_job)
        self.jt.submit(make_appender("a"))
        self.jt.submit(make_appender("b"))
        self.jt.submit(make_appender("c"))
        # Signal done after all normal jobs
        self.jt.submit(signal_done)

        # Now submit urgent — it should preempt a, b, c
        self.jt.submit_urgent(urgent_fn)

        # Release the blocker
        blocker.set()

        done.wait(timeout=3.0)

        self.assertIn("URGENT", results)
        urgent_idx = results.index("URGENT")
        for letter in ("a", "b", "c"):
            if letter in results:
                self.assertLess(urgent_idx, results.index(letter),
                                f"URGENT should appear before '{letter}' but results={results}")

    def test_submit_urgent_sets_cancel_event(self):
        """submit_urgent() sets the cancel_event that in-flight normal jobs can observe."""
        cancel_was_set = threading.Event()
        blocker = threading.Event()

        def long_running_normal():
            # In-flight normal job checks cancel_event
            if self.jt.cancel_event.is_set():
                cancel_was_set.set()
            blocker.wait(timeout=2.0)
            # Check again after release
            if self.jt.cancel_event.is_set():
                cancel_was_set.set()

        urgent_ready = threading.Event()

        def urgent_fn():
            urgent_ready.set()

        self.jt.submit(long_running_normal)

        # Give the normal job time to start running
        time.sleep(0.05)

        self.jt.submit_urgent(urgent_fn)

        # cancel_event should now be set
        # Give a brief moment for submit_urgent to execute
        time.sleep(0.05)

        self.assertTrue(self.jt.cancel_event.is_set(),
                        "cancel_event should be set after submit_urgent() is called")

        # Release blocker and wait for urgent to complete
        blocker.set()
        urgent_ready.wait(timeout=2.0)

    def test_submit_urgent_module_level(self):
        """Module-level jobs.submit_urgent() delegates to the global JobThread."""
        import dmccodegui.utils.jobs as jobs_module

        called = threading.Event()

        def fn():
            called.set()

        # Patch get_jobs() to return our test JobThread
        with patch.object(jobs_module, "get_jobs", return_value=self.jt):
            jobs_module.submit_urgent(fn)

        called.wait(timeout=2.0)
        self.assertTrue(called.is_set(), "submit_urgent module-level fn should have been called")


# ---------------------------------------------------------------------------
# reset_handle tests
# ---------------------------------------------------------------------------

class TestResetHandle(unittest.TestCase):
    """Tests for GalilController.reset_handle()."""

    def _make_controller(self, driver=None):
        from dmccodegui.controller import GalilController
        ctrl = GalilController(driver=driver)
        return ctrl

    def test_reset_handle_calls_gclose_gopen(self):
        """reset_handle('addr') calls GClose then GOpen('addr') and stays connected."""
        driver = MagicMock()
        ctrl = self._make_controller(driver=driver)
        ctrl._connected = True
        ctrl._address = "192.168.0.1"

        result = ctrl.reset_handle("192.168.0.1")

        self.assertTrue(result, "reset_handle should return True on success")
        self.assertTrue(ctrl.is_connected(), "_connected should stay True")
        # Verify GClose called before GOpen
        manager = MagicMock()
        manager.attach_mock(driver.GClose, "GClose")
        manager.attach_mock(driver.GOpen, "GOpen")
        # Verify both were called
        from dmccodegui.controller import PRIMARY_FLAGS
        driver.GClose.assert_called_once()
        driver.GOpen.assert_called_once_with(f"192.168.0.1 {PRIMARY_FLAGS}")
        # Verify order: GClose index < GOpen index in call list
        gclose_idx = None
        gopen_idx = None
        for i, c in enumerate(driver.mock_calls):
            if c == call.GClose():
                gclose_idx = i
            elif c == call.GOpen(f"192.168.0.1 {PRIMARY_FLAGS}"):
                gopen_idx = i
        self.assertIsNotNone(gclose_idx, "GClose was not called")
        self.assertIsNotNone(gopen_idx, "GOpen was not called")
        self.assertLess(gclose_idx, gopen_idx, "GClose must be called before GOpen")

    def test_reset_handle_failure_sets_disconnected(self):
        """When GOpen raises, reset_handle returns False and _connected is False."""
        driver = MagicMock()
        driver.GOpen.side_effect = RuntimeError("connection refused")
        ctrl = self._make_controller(driver=driver)
        ctrl._connected = True
        ctrl._address = "192.168.0.1"

        result = ctrl.reset_handle("192.168.0.1")

        self.assertFalse(result, "reset_handle should return False on GOpen failure")
        self.assertFalse(ctrl.is_connected(), "_connected should be False after failure")

    def test_reset_handle_uses_stored_address_when_none_given(self):
        """reset_handle() with no args uses self._address."""
        driver = MagicMock()
        ctrl = self._make_controller(driver=driver)
        ctrl._connected = True
        ctrl._address = "10.0.0.5"

        result = ctrl.reset_handle()

        from dmccodegui.controller import PRIMARY_FLAGS
        self.assertTrue(result)
        driver.GOpen.assert_called_once_with(f"10.0.0.5 {PRIMARY_FLAGS}")

    def test_reset_handle_returns_false_when_no_address(self):
        """reset_handle() with no stored address returns False immediately."""
        driver = MagicMock()
        ctrl = self._make_controller(driver=driver)
        ctrl._connected = True
        ctrl._address = ""

        result = ctrl.reset_handle()

        self.assertFalse(result, "reset_handle should return False with no address")
        driver.GClose.assert_not_called()
        driver.GOpen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
