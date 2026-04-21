"""Tests for _get_data_dir() frozen/dev behaviour (WIN-05)."""
import os
import sys
import pytest


def test_frozen_mode_returns_appdata_binh_an_hmi(monkeypatch, tmp_path):
    """In frozen mode, _get_data_dir() returns %APPDATA%/BinhAnHMI and creates it."""
    # Arrange: simulate PyInstaller frozen environment
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    fake_appdata = str(tmp_path / "AppData" / "Roaming")
    monkeypatch.setenv("APPDATA", fake_appdata)

    # Re-import to pick up monkeypatched sys.frozen
    import importlib
    import dmccodegui.main as m
    importlib.reload(m)

    # Act
    result = m._get_data_dir()

    # Assert
    expected = os.path.join(fake_appdata, "BinhAnHMI")
    assert result == expected, f"Expected {expected!r}, got {result!r}"
    assert os.path.isdir(result), "_get_data_dir() must create the directory"


def test_frozen_mode_creates_directory(monkeypatch, tmp_path):
    """_get_data_dir() creates the BinhAnHMI directory if it doesn't exist."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    fake_appdata = str(tmp_path / "nonexistent" / "path")
    monkeypatch.setenv("APPDATA", fake_appdata)

    import importlib
    import dmccodegui.main as m
    importlib.reload(m)

    result = m._get_data_dir()
    assert os.path.isdir(result), "Directory must be created even if parent didn't exist"


def test_dev_mode_returns_auth_dir(monkeypatch):
    """In dev mode (no sys.frozen), _get_data_dir() returns the local auth/ directory."""
    # Ensure sys.frozen is not set
    monkeypatch.delattr(sys, "frozen", raising=False)

    import importlib
    import dmccodegui.main as m
    importlib.reload(m)

    result = m._get_data_dir()
    assert result.endswith("auth") or result.endswith("auth/") or result.endswith("auth\\"), (
        f"Dev mode should return a path ending in 'auth', got {result!r}"
    )


def test_frozen_fallback_no_appdata(monkeypatch, tmp_path):
    """In frozen mode with no APPDATA env var, falls back to ~/BinhAnHMI."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delenv("APPDATA", raising=False)
    # Point HOME/USERPROFILE to tmp_path so expanduser("~") is deterministic
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))

    import importlib
    import dmccodegui.main as m
    importlib.reload(m)

    result = m._get_data_dir()
    # Must contain BinhAnHMI regardless of home dir location
    assert "BinhAnHMI" in result, (
        f"Fallback path must include 'BinhAnHMI', got {result!r}"
    )
    assert os.path.isdir(result), "Fallback directory must be created"
