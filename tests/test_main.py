"""Tests for main app structure (UI-04: NoTransition) and startup config."""
import importlib
import logging
import os
import sys

import pytest


def test_no_transition():
    """Verify base.kv declares NoTransition on the ScreenManager."""
    base_kv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "src", "dmccodegui", "ui", "base.kv"
    )
    with open(base_kv_path, "r") as f:
        content = f.read()
    assert "NoTransition" in content, (
        "base.kv must use NoTransition on ScreenManager (UI-04)"
    )
    # Also verify the import line exists
    assert "#:import NoTransition" in content, (
        "base.kv must import NoTransition from kivy.uix.screenmanager"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_main():
    """Reload dmccodegui.main and return the module.

    Uses the same pattern as test_display_preset.py — Kivy is installed,
    so a plain reload works.  Returns the freshly loaded module object.
    """
    import dmccodegui.main as m
    importlib.reload(m)
    return m


# ---------------------------------------------------------------------------
# TestAngleBackend
# ---------------------------------------------------------------------------

class TestAngleBackend:
    """Tests for FIX-03: ANGLE GL backend env var and startup log."""

    def teardown_method(self):
        """Clean up KIVY_GL_BACKEND env var after each test."""
        os.environ.pop("KIVY_GL_BACKEND", None)

    def test_angle_backend_env_set(self):
        """On win32, after the pre-Kivy block, KIVY_GL_BACKEND == 'angle_sdl2'."""
        # Clear any existing value so setdefault takes effect
        os.environ.pop("KIVY_GL_BACKEND", None)

        from unittest.mock import patch
        with patch.object(sys, "platform", "win32"):
            m = _reload_main()

        assert os.environ.get("KIVY_GL_BACKEND") == "angle_sdl2", (
            "KIVY_GL_BACKEND should be set to angle_sdl2 on Windows"
        )

    def test_gl_backend_log_line(self):
        """Startup emits a log message containing 'GL backend:' with env var value."""
        os.environ.pop("KIVY_GL_BACKEND", None)

        records: list[str] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(self.format(record))

        capture_handler = _Capture()
        capture_handler.setLevel(logging.DEBUG)
        root = logging.getLogger()
        root.addHandler(capture_handler)
        try:
            m = _reload_main()
        finally:
            root.removeHandler(capture_handler)

        gl_lines = [r for r in records if "GL backend:" in r]
        assert gl_lines, (
            "Expected at least one log record containing 'GL backend:'"
        )
        # The logged value should reflect the actual env var (not be hardcoded)
        actual = os.environ.get("KIVY_GL_BACKEND", "default (platform gl)")
        assert any(actual in line for line in gl_lines), (
            f"GL backend log should contain '{actual}', got: {gl_lines}"
        )
