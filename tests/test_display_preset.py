"""Tests for screen resolution auto-detection (APP-04).

Tests _classify_resolution() and _detect_preset() from dmccodegui.main.
These functions live in the pre-Kivy block of main.py, so they are pure
(no Kivy dependency) and can be tested directly.

Uses importlib.reload(m) pattern from test_data_dir.py since main.py
has module-level side effects.
"""
from __future__ import annotations

import importlib
import json
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


# ---------------------------------------------------------------------------
# _classify_resolution tests (pure function, no mocking needed)
# ---------------------------------------------------------------------------

class TestClassifyResolution:
    def test_classify_7inch(self, monkeypatch):
        """800x480: short=480 <= 480 → '7inch'."""
        m = _load_main(monkeypatch)
        assert m._classify_resolution(800, 480) == "7inch"

    def test_classify_10inch(self, monkeypatch):
        """1024x600: short=600, 480 < 600 <= 600 → '10inch'."""
        m = _load_main(monkeypatch)
        assert m._classify_resolution(1024, 600) == "10inch"

    def test_classify_15inch(self, monkeypatch):
        """1920x1080: short=1080 > 600 → '15inch'."""
        m = _load_main(monkeypatch)
        assert m._classify_resolution(1920, 1080) == "15inch"

    def test_classify_ambiguous(self, monkeypatch):
        """1024x768: short=768 > 600 → '15inch' (round-down means larger preset for ambiguous).

        The threshold is short <= 600 for '10inch'. 768 > 600 so → '15inch'.
        """
        m = _load_main(monkeypatch)
        assert m._classify_resolution(1024, 768) == "15inch"


# ---------------------------------------------------------------------------
# _detect_preset tests (requires mocking screeninfo and settings.json)
# ---------------------------------------------------------------------------

class TestDetectPreset:
    def test_screeninfo_failure_fallback(self, monkeypatch, tmp_path):
        """When screeninfo.get_monitors raises Exception, _detect_preset returns '15inch'."""
        m = _load_main(monkeypatch)

        # No settings file
        settings_path = str(tmp_path / "settings.json")

        # Patch screeninfo to raise on get_monitors
        fake_screeninfo = MagicMock()
        fake_screeninfo.get_monitors.side_effect = Exception("No enumerators available")
        fake_screeninfo.common = MagicMock()
        fake_screeninfo.common.ScreenInfoError = Exception
        monkeypatch.setitem(sys.modules, "screeninfo", fake_screeninfo)
        monkeypatch.setitem(sys.modules, "screeninfo.common", fake_screeninfo.common)

        result = m._detect_preset(settings_path)
        assert result == "15inch", f"Expected '15inch' fallback, got {result!r}"

    def test_override_valid(self, monkeypatch, tmp_path):
        """settings.json with display_size='7inch' returns '7inch' without calling screeninfo."""
        m = _load_main(monkeypatch)

        settings_path = str(tmp_path / "settings.json")
        with open(settings_path, "w", encoding="utf-8") as fh:
            json.dump({"display_size": "7inch"}, fh)

        # screeninfo must NOT be called — if it is, the mock will raise
        fake_screeninfo = MagicMock()
        fake_screeninfo.get_monitors.side_effect = RuntimeError(
            "screeninfo should not be called when override is set"
        )
        monkeypatch.setitem(sys.modules, "screeninfo", fake_screeninfo)

        result = m._detect_preset(settings_path)
        assert result == "7inch", f"Expected '7inch' from override, got {result!r}"
        fake_screeninfo.get_monitors.assert_not_called()

    def test_override_invalid(self, monkeypatch, tmp_path):
        """settings.json with display_size='bad' returns '15inch' (NOT auto-detect).

        Invalid override falls back to '15inch' immediately, does NOT call screeninfo.
        """
        m = _load_main(monkeypatch)

        settings_path = str(tmp_path / "settings.json")
        with open(settings_path, "w", encoding="utf-8") as fh:
            json.dump({"display_size": "bad"}, fh)

        # screeninfo should NOT be called
        fake_screeninfo = MagicMock()
        fake_screeninfo.get_monitors.side_effect = RuntimeError(
            "screeninfo should not be called on invalid override"
        )
        monkeypatch.setitem(sys.modules, "screeninfo", fake_screeninfo)

        result = m._detect_preset(settings_path)
        assert result == "15inch", (
            f"Invalid override should return '15inch', got {result!r}"
        )
        fake_screeninfo.get_monitors.assert_not_called()

    def test_no_settings_file(self, monkeypatch, tmp_path):
        """When settings.json does not exist, _detect_preset calls screeninfo for auto-detect."""
        m = _load_main(monkeypatch)

        settings_path = str(tmp_path / "nonexistent_settings.json")

        # Provide a working screeninfo mock returning 1920x1080
        fake_monitor = MagicMock()
        fake_monitor.width = 1920
        fake_monitor.height = 1080
        fake_screeninfo = MagicMock()
        fake_screeninfo.get_monitors.return_value = [fake_monitor]
        fake_screeninfo.common = MagicMock()
        fake_screeninfo.common.ScreenInfoError = Exception
        monkeypatch.setitem(sys.modules, "screeninfo", fake_screeninfo)
        monkeypatch.setitem(sys.modules, "screeninfo.common", fake_screeninfo.common)

        result = m._detect_preset(settings_path)
        # screeninfo should have been consulted
        fake_screeninfo.get_monitors.assert_called_once()
        assert result == "15inch", f"Expected '15inch' from 1920x1080 monitor, got {result!r}"

    def test_startup_log_line(self, monkeypatch, tmp_path):
        """_detect_preset emits a log line containing the preset name.

        After print() migration (Phase 28-01), the log line goes to the
        rotating file handler rather than stdout. We verify via caplog.
        """
        import logging

        m = _load_main(monkeypatch)

        settings_path = str(tmp_path / "settings.json")
        with open(settings_path, "w", encoding="utf-8") as fh:
            json.dump({"display_size": "10inch"}, fh)

        # Capture log records emitted during _detect_preset()
        with MagicMock() as _unused:
            pass  # just to keep imports consistent

        import logging
        records = []

        class _Capture(logging.Handler):
            def emit(self, record):
                records.append(self.format(record))

        capture_handler = _Capture()
        capture_handler.setLevel(logging.DEBUG)
        root = logging.getLogger()
        root.addHandler(capture_handler)
        try:
            result = m._detect_preset(settings_path)
        finally:
            root.removeHandler(capture_handler)

        assert result == "10inch"
        combined = "\n".join(records)
        assert "10inch" in combined, (
            f"Expected '10inch' in log output, got: {combined!r}"
        )


# ---------------------------------------------------------------------------
# _DISPLAY_PRESETS structure test
# ---------------------------------------------------------------------------

class TestDisplayPresets:
    def test_density_values(self, monkeypatch):
        """Each preset in _DISPLAY_PRESETS has a 'density' key with a string numeric value."""
        m = _load_main(monkeypatch)

        assert hasattr(m, "_DISPLAY_PRESETS"), "_DISPLAY_PRESETS must exist in main module"
        presets = m._DISPLAY_PRESETS

        for name, preset in presets.items():
            assert "density" in preset, f"Preset '{name}' missing 'density' key"
            density_val = preset["density"]
            assert isinstance(density_val, str), (
                f"Preset '{name}' density must be a string, got {type(density_val)}"
            )
            try:
                float(density_val)
            except ValueError:
                pytest.fail(
                    f"Preset '{name}' density '{density_val}' is not parseable as float"
                )
