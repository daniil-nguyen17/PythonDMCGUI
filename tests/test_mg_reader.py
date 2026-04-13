"""Tests for MgReader — MG message dispatcher and parser.

Tests are organized into classes that match the test names in the plan:
  - TestMgReaderDispatch: _classify_line correctness for all DMC message prefixes
  - TestStateFilteredFromLog: state/position messages do NOT reach log_handlers
  - TestHandlerRegistration: add_*_handler returns working unregister callables
  - TestMgHandleTimeout: _loop opens handle with correct GOpen/GTimeout args
  - TestStartStop: thread lifecycle, double-start guard
"""
from __future__ import annotations

import os
import sys
import threading
import types
from unittest.mock import MagicMock, patch, call

import pytest

# Add src to path so dmccodegui is importable without installation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mg_reader():
    """Import MgReader with Kivy and gclib fully mocked."""
    # Mock Kivy Clock before importing module
    mock_clock = MagicMock()
    kivy_mod = types.ModuleType("kivy")
    kivy_clock_mod = types.ModuleType("kivy.clock")
    kivy_clock_mod.Clock = mock_clock
    kivy_mod.clock = kivy_clock_mod

    with patch.dict("sys.modules", {
        "kivy": kivy_mod,
        "kivy.clock": kivy_clock_mod,
    }):
        # Force re-import if already cached
        sys.modules.pop("dmccodegui.hmi.mg_reader", None)
        from dmccodegui.hmi.mg_reader import MgReader
    return MgReader, mock_clock


# ---------------------------------------------------------------------------
# TestMgReaderDispatch
# ---------------------------------------------------------------------------

class TestMgReaderDispatch:
    """Tests for MgReader._classify_line static method."""

    def setup_method(self):
        self.MgReader, self.mock_clock = _make_mg_reader()

    def test_classify_state_message(self):
        """STATE:N returns ('state', int)."""
        result = self.MgReader._classify_line("STATE:3")
        assert result == ("state", 3)

    def test_classify_state_message_zero(self):
        """STATE:0 returns ('state', 0)."""
        result = self.MgReader._classify_line("STATE:0")
        assert result == ("state", 0)

    def test_classify_idling_for_input(self):
        """IDLING FOR INPUT prefix parsed with all 4 axes."""
        line = "IDLING FOR INPUT  A:100.0  B:200.0  C:300.0  D:400.0"
        kind, data = self.MgReader._classify_line(line)
        assert kind == "position"
        assert data["prefix"] == "IDLING FOR INPUT"
        assert data["A"] == pytest.approx(100.0)
        assert data["B"] == pytest.approx(200.0)
        assert data["C"] == pytest.approx(300.0)
        assert data["D"] == pytest.approx(400.0)

    def test_classify_pre_li(self):
        """PRE-LI prefix parsed with A and B axes."""
        line = "PRE-LI  A:100.0  B:200.0"
        kind, data = self.MgReader._classify_line(line)
        assert kind == "position"
        assert data["prefix"] == "PRE-LI"
        assert data["A"] == pytest.approx(100.0)
        assert data["B"] == pytest.approx(200.0)

    def test_classify_running(self):
        """RUNNING prefix parsed with A, B, C, LM axes."""
        line = "RUNNING  A:100.0  B:200.0  C:300.0  LM:5"
        kind, data = self.MgReader._classify_line(line)
        assert kind == "position"
        assert data["prefix"] == "RUNNING"
        assert data["A"] == pytest.approx(100.0)
        assert data["B"] == pytest.approx(200.0)
        assert data["C"] == pytest.approx(300.0)
        assert data["LM"] == pytest.approx(5.0)

    def test_classify_end_reached(self):
        """END REACHED prefix parsed with all 4 axes."""
        line = "END REACHED  A:100.0  B:200.0  C:300.0  D:400.0"
        kind, data = self.MgReader._classify_line(line)
        assert kind == "position"
        assert data["prefix"] == "END REACHED"
        assert data["A"] == pytest.approx(100.0)
        assert data["B"] == pytest.approx(200.0)
        assert data["C"] == pytest.approx(300.0)
        assert data["D"] == pytest.approx(400.0)

    def test_classify_freeform_log(self):
        """Any other text returns ('log', text)."""
        line = "Some freeform log text"
        result = self.MgReader._classify_line(line)
        assert result == ("log", "Some freeform log text")

    def test_classify_freeform_empty_prefix(self):
        """Lines not matching known prefixes go to log."""
        line = "Homing complete"
        kind, data = self.MgReader._classify_line(line)
        assert kind == "log"
        assert data == "Homing complete"

    def test_classify_position_negative_values(self):
        """Position parsing handles negative axis values."""
        line = "RUNNING  A:-12.5  B:0.0  C:300.0  LM:1"
        kind, data = self.MgReader._classify_line(line)
        assert kind == "position"
        assert data["A"] == pytest.approx(-12.5)

    def test_classify_idling_with_extra_keys(self):
        """IDLING FOR INPUT with extra keys like hmiState:3 parses naturally."""
        line = "IDLING FOR INPUT  A:100.0  B:200.0  C:300.0  D:400.0  hmiState:3  ctSesKni:5  ctStnKni:10"
        kind, data = self.MgReader._classify_line(line)
        assert kind == "position"
        assert data["prefix"] == "IDLING FOR INPUT"
        assert data["hmiState"] == pytest.approx(3.0)
        assert data["ctSesKni"] == pytest.approx(5.0)
        assert data["ctStnKni"] == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# TestStateFilteredFromLog
# ---------------------------------------------------------------------------

class TestStateFilteredFromLog:
    """STATE:N and position messages must NOT reach log_handlers."""

    def setup_method(self):
        self.MgReader, self.mock_clock = _make_mg_reader()

    def test_state_message_not_in_log_handlers(self):
        """STATE:N dispatches to state_handlers only, not log_handlers."""
        reader = self.MgReader()
        log_calls = []
        state_calls = []
        reader.add_log_handler(lambda msg: log_calls.append(msg))
        reader.add_state_handler(lambda s: state_calls.append(s))

        # Simulate dispatch by calling internal dispatch methods directly
        reader._dispatch_message("STATE:3")

        # state_handlers called; log_handlers NOT called
        # Clock.schedule_once defers; call the scheduled functions
        assert self.mock_clock.schedule_once.called
        for scheduled_call in self.mock_clock.schedule_once.call_args_list:
            fn = scheduled_call[0][0]
            fn(0)  # dt=0

        assert state_calls == [3]
        assert log_calls == [], "STATE message must NOT appear in log_handlers"

    def test_position_message_not_in_log_handlers(self):
        """Position messages dispatch to position_handlers only, not log_handlers."""
        reader = self.MgReader()
        log_calls = []
        position_calls = []
        reader.add_log_handler(lambda msg: log_calls.append(msg))
        reader.add_position_handler(lambda p: position_calls.append(p))

        reader._dispatch_message("RUNNING  A:1.0  B:2.0  C:3.0  LM:0")

        for scheduled_call in self.mock_clock.schedule_once.call_args_list:
            fn = scheduled_call[0][0]
            fn(0)

        assert len(position_calls) == 1
        assert log_calls == [], "Position message must NOT appear in log_handlers"

    def test_freeform_message_reaches_log_handlers(self):
        """Freeform log text dispatches to log_handlers only."""
        reader = self.MgReader()
        log_calls = []
        state_calls = []
        reader.add_log_handler(lambda msg: log_calls.append(msg))
        reader.add_state_handler(lambda s: state_calls.append(s))

        reader._dispatch_message("Knife grinding complete")

        for scheduled_call in self.mock_clock.schedule_once.call_args_list:
            fn = scheduled_call[0][0]
            fn(0)

        assert log_calls == ["Knife grinding complete"]
        assert state_calls == []


# ---------------------------------------------------------------------------
# TestHandlerRegistration
# ---------------------------------------------------------------------------

class TestHandlerRegistration:
    """Handler registration returns unregister callables."""

    def setup_method(self):
        self.MgReader, self.mock_clock = _make_mg_reader()

    def test_add_log_handler_returns_unregister(self):
        """add_log_handler returns callable that removes handler."""
        reader = self.MgReader()
        calls = []
        unregister = reader.add_log_handler(lambda msg: calls.append(msg))
        assert callable(unregister)

        # Handler works before unregister
        reader._dispatch_message("log line")
        for c in self.mock_clock.schedule_once.call_args_list:
            c[0][0](0)
        assert len(calls) == 1

        # Unregister removes it
        self.mock_clock.schedule_once.reset_mock()
        unregister()

        # Handler no longer receives messages
        reader._dispatch_message("another log line")
        for c in self.mock_clock.schedule_once.call_args_list:
            c[0][0](0)
        assert len(calls) == 1  # still 1, not 2

    def test_add_state_handler_returns_unregister(self):
        """add_state_handler returns callable that removes handler."""
        reader = self.MgReader()
        calls = []
        unregister = reader.add_state_handler(lambda s: calls.append(s))
        assert callable(unregister)

        reader._dispatch_message("STATE:1")
        for c in self.mock_clock.schedule_once.call_args_list:
            c[0][0](0)
        assert calls == [1]

        self.mock_clock.schedule_once.reset_mock()
        unregister()

        reader._dispatch_message("STATE:2")
        for c in self.mock_clock.schedule_once.call_args_list:
            c[0][0](0)
        assert calls == [1]  # still [1], not [1, 2]

    def test_add_position_handler_returns_unregister(self):
        """add_position_handler returns callable that removes handler."""
        reader = self.MgReader()
        calls = []
        unregister = reader.add_position_handler(lambda p: calls.append(p))
        assert callable(unregister)

        reader._dispatch_message("PRE-LI  A:1.0  B:2.0")
        for c in self.mock_clock.schedule_once.call_args_list:
            c[0][0](0)
        assert len(calls) == 1

        self.mock_clock.schedule_once.reset_mock()
        unregister()

        reader._dispatch_message("PRE-LI  A:3.0  B:4.0")
        for c in self.mock_clock.schedule_once.call_args_list:
            c[0][0](0)
        assert len(calls) == 1  # not 2

    def test_multiple_handlers_same_type(self):
        """Multiple log handlers all receive the same message."""
        reader = self.MgReader()
        calls_a = []
        calls_b = []
        reader.add_log_handler(lambda msg: calls_a.append(msg))
        reader.add_log_handler(lambda msg: calls_b.append(msg))

        reader._dispatch_message("hello")
        for c in self.mock_clock.schedule_once.call_args_list:
            c[0][0](0)

        assert calls_a == ["hello"]
        assert calls_b == ["hello"]


# ---------------------------------------------------------------------------
# TestMgHandleTimeout
# ---------------------------------------------------------------------------

class TestMgHandleTimeout:
    """MG handle opens with correct connection string and GTimeout."""

    def setup_method(self):
        self.MgReader, self.mock_clock = _make_mg_reader()

    def _run_loop_one_iteration(self, address="192.168.1.100"):
        """Run _loop with a stop event that fires after one pass."""
        reader = self.MgReader()

        mock_gclib = MagicMock()
        mock_handle = MagicMock()
        mock_gclib.py.return_value = mock_handle

        stop_event = threading.Event()

        # Make GMessage raise after first call to end loop
        call_count = [0]
        def side_effect_gmessage():
            call_count[0] += 1
            if call_count[0] >= 1:
                stop_event.set()
                raise Exception("timeout")
            return ""

        mock_handle.GMessage.side_effect = side_effect_gmessage

        with patch.dict("sys.modules", {"gclib": mock_gclib}):
            reader._loop(address, stop_event)

        return mock_handle, mock_gclib

    def test_loop_opens_handle_with_correct_string(self):
        """_loop opens handle with '--direct --subscribe MG --timeout 500'."""
        address = "192.168.1.100"
        mock_handle, mock_gclib = self._run_loop_one_iteration(address)

        # GOpen called with address + required flags
        mock_handle.GOpen.assert_called_once()
        gopen_arg = mock_handle.GOpen.call_args[0][0]
        assert "--direct" in gopen_arg
        assert "--subscribe MG" in gopen_arg
        assert "--timeout 500" in gopen_arg
        assert address in gopen_arg

    def test_loop_calls_gtimeout_after_gopen(self):
        """_loop calls GTimeout(500) after GOpen."""
        mock_handle, mock_gclib = self._run_loop_one_iteration()

        mock_handle.GTimeout.assert_called_with(500)

    def test_loop_calls_gclose_on_exit(self):
        """_loop calls GClose() when the stop event is set."""
        mock_handle, mock_gclib = self._run_loop_one_iteration()
        mock_handle.GClose.assert_called()


# ---------------------------------------------------------------------------
# TestStartStop
# ---------------------------------------------------------------------------

class TestStartStop:
    """start() / stop() thread lifecycle tests."""

    def setup_method(self):
        self.MgReader, self.mock_clock = _make_mg_reader()

    def _make_reader_with_mock_loop(self):
        """Return reader and a threading.Event that signals loop has started."""
        reader = self.MgReader()
        loop_started = threading.Event()
        stop_gate = threading.Event()

        def fake_loop(address, stop_event):
            loop_started.set()
            stop_event.wait(timeout=3.0)

        reader._loop = fake_loop
        return reader, loop_started, stop_gate

    def test_start_creates_thread(self):
        """start() creates and starts a background thread."""
        reader, loop_started, _ = self._make_reader_with_mock_loop()
        reader.start("192.168.1.100")
        assert loop_started.wait(timeout=2.0), "Loop did not start within 2s"
        assert reader._mg_thread is not None
        assert reader._mg_thread.is_alive()
        # Cleanup
        if reader._mg_stop_event:
            reader._mg_stop_event.set()
        reader._mg_thread.join(timeout=2.0)

    def test_stop_joins_thread(self):
        """stop() sets stop event and joins thread within 2s."""
        reader, loop_started, _ = self._make_reader_with_mock_loop()
        reader.start("192.168.1.100")
        loop_started.wait(timeout=2.0)

        reader.stop()
        assert reader._mg_thread is None, "Thread reference should be cleared after stop()"

    def test_double_start_is_noop(self):
        """Calling start() twice does not create a second thread."""
        reader, loop_started, _ = self._make_reader_with_mock_loop()
        reader.start("192.168.1.100")
        loop_started.wait(timeout=2.0)

        first_thread = reader._mg_thread
        reader.start("192.168.1.100")  # second start — should be noop
        second_thread = reader._mg_thread

        assert first_thread is second_thread, "Double start must not replace thread"

        # Cleanup
        reader.stop()

    def test_stop_without_start_is_safe(self):
        """stop() on a fresh (never started) MgReader does not raise."""
        reader = self.MgReader()
        reader.stop()  # must not raise

    def test_stop_clears_thread_reference(self):
        """After stop(), _mg_thread is None."""
        reader, loop_started, _ = self._make_reader_with_mock_loop()
        reader.start("192.168.1.100")
        loop_started.wait(timeout=2.0)
        reader.stop()
        assert reader._mg_thread is None
