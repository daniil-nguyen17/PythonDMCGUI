"""Tests for centralized logging infrastructure (APP-01, APP-02).

Tests setup_logging() and _setup_excepthook() from dmccodegui.main.
These functions live in the pre-Kivy block of main.py, so they are pure
(no Kivy dependency) and can be tested directly.

Uses direct function import pattern — we import the functions directly
after patching _get_data_dir so the log directory stays in tmp_path.
"""
from __future__ import annotations

import importlib
import logging
import logging.handlers
import sys
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_main(monkeypatch):
    """Reload dmccodegui.main and return the module.

    Always reloads to pick up monkeypatched environment state.
    Kivy Config/Window calls happen at module level — we monkeypatch
    them away before reload so tests never touch real Kivy state.
    """
    import dmccodegui.main as m
    importlib.reload(m)
    return m


def _fresh_root_logger():
    """Remove all handlers from the root logger and return it."""
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass
    return root


# ---------------------------------------------------------------------------
# Task 1 tests: setup_logging() + _setup_excepthook()
# ---------------------------------------------------------------------------

class TestSetupLogging:

    def test_log_file_created(self, monkeypatch, tmp_path):
        """setup_logging() creates logs/app.log under _get_data_dir()."""
        m = _load_main(monkeypatch)
        _fresh_root_logger()

        monkeypatch.setattr(m, "_get_data_dir", lambda: str(tmp_path))
        m.setup_logging()

        log_file = tmp_path / "logs" / "app.log"
        assert log_file.exists(), f"Expected {log_file} to exist after setup_logging()"

    def test_rotating_handler_config(self, monkeypatch, tmp_path):
        """Root logger has a RotatingFileHandler with correct maxBytes and backupCount."""
        m = _load_main(monkeypatch)
        _fresh_root_logger()

        monkeypatch.setattr(m, "_get_data_dir", lambda: str(tmp_path))
        m.setup_logging()

        root = logging.getLogger()
        rotating = [
            h for h in root.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert rotating, "Root logger must have a RotatingFileHandler"
        h = rotating[0]
        assert h.maxBytes == 5 * 1024 * 1024, (
            f"Expected maxBytes=5242880, got {h.maxBytes}"
        )
        assert h.backupCount == 3, f"Expected backupCount=3, got {h.backupCount}"

    def test_log_format(self, monkeypatch, tmp_path):
        """Log records match format: 'YYYY-MM-DD HH:MM:SS LEVEL [module] message'.

        %(module)s is the Python source module name (filename without .py),
        not the logger name. A log call made from this test file will emit
        [test_logging] as the module.
        """
        import re

        m = _load_main(monkeypatch)
        _fresh_root_logger()

        monkeypatch.setattr(m, "_get_data_dir", lambda: str(tmp_path))
        m.setup_logging()

        log_file = tmp_path / "logs" / "app.log"
        logging.getLogger("test_module").info("hello world")

        content = log_file.read_text(encoding="utf-8")
        # %(module)s gives the source file module name (test_logging), not the logger name.
        # Pattern: "2026-04-22 02:35:12 INFO [test_logging] hello world"
        pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \w+ \[\w+\] hello world"
        assert re.search(pattern, content), (
            f"Log format mismatch. Content: {content!r}"
        )

    def test_console_handler_when_stderr_exists(self, monkeypatch, tmp_path):
        """StreamHandler is added when sys.stderr is not None."""
        m = _load_main(monkeypatch)
        _fresh_root_logger()

        monkeypatch.setattr(m, "_get_data_dir", lambda: str(tmp_path))
        # Ensure stderr is not None (normal dev scenario)
        monkeypatch.setattr(sys, "stderr", sys.__stderr__)
        m.setup_logging()

        root = logging.getLogger()
        stream_handlers = [h for h in root.handlers if isinstance(h, logging.StreamHandler)
                           and not isinstance(h, logging.handlers.RotatingFileHandler)]
        assert stream_handlers, "StreamHandler must be present when sys.stderr is not None"

    def test_no_console_handler_when_stderr_none(self, monkeypatch, tmp_path):
        """StreamHandler is NOT added when sys.stderr is None (frozen no-console)."""
        m = _load_main(monkeypatch)
        _fresh_root_logger()

        monkeypatch.setattr(m, "_get_data_dir", lambda: str(tmp_path))
        monkeypatch.setattr(sys, "stderr", None)
        m.setup_logging()

        root = logging.getLogger()
        stream_handlers = [h for h in root.handlers if isinstance(h, logging.StreamHandler)
                           and not isinstance(h, logging.handlers.RotatingFileHandler)]
        assert not stream_handlers, (
            "StreamHandler must NOT be added when sys.stderr is None"
        )


class TestSetupExcepthook:

    def test_excepthook_patched(self, monkeypatch, tmp_path):
        """After _setup_excepthook(), sys.excepthook is not sys.__excepthook__."""
        m = _load_main(monkeypatch)
        _fresh_root_logger()

        monkeypatch.setattr(m, "_get_data_dir", lambda: str(tmp_path))
        m.setup_logging()
        m._setup_excepthook()

        assert sys.excepthook is not sys.__excepthook__, (
            "_setup_excepthook() must replace sys.excepthook"
        )

    def test_excepthook_logs_traceback(self, monkeypatch, tmp_path):
        """Calling the patched excepthook with ValueError writes traceback to log file."""
        m = _load_main(monkeypatch)
        _fresh_root_logger()

        monkeypatch.setattr(m, "_get_data_dir", lambda: str(tmp_path))
        m.setup_logging()
        m._setup_excepthook()

        log_file = tmp_path / "logs" / "app.log"

        # Synthesize an exception
        try:
            raise ValueError("test uncaught error")
        except ValueError:
            exc_type, exc_value, exc_tb = sys.exc_info()

        # Call the patched hook directly
        sys.excepthook(exc_type, exc_value, exc_tb)

        # Flush handlers
        for h in logging.getLogger().handlers:
            h.flush()

        content = log_file.read_text(encoding="utf-8")
        assert "Uncaught exception" in content, (
            f"Expected 'Uncaught exception' in log, got: {content!r}"
        )
        assert "ValueError" in content, (
            f"Expected 'ValueError' in log, got: {content!r}"
        )

    def test_excepthook_keyboard_interrupt(self, monkeypatch, tmp_path):
        """Patched excepthook with KeyboardInterrupt does NOT produce CRITICAL log entry."""
        m = _load_main(monkeypatch)
        _fresh_root_logger()

        monkeypatch.setattr(m, "_get_data_dir", lambda: str(tmp_path))
        m.setup_logging()
        m._setup_excepthook()

        log_file = tmp_path / "logs" / "app.log"

        # Synthesize a KeyboardInterrupt
        try:
            raise KeyboardInterrupt()
        except KeyboardInterrupt:
            exc_type, exc_value, exc_tb = sys.exc_info()

        # Patch original hook to avoid side effects
        monkeypatch.setattr(sys, "__excepthook__", lambda *a: None)

        sys.excepthook(exc_type, exc_value, exc_tb)

        for h in logging.getLogger().handlers:
            h.flush()

        content = log_file.read_text(encoding="utf-8")
        assert "CRITICAL" not in content, (
            f"KeyboardInterrupt must not produce CRITICAL log entry, got: {content!r}"
        )
