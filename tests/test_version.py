"""Tests for __version__ and DMCApp.title branding (WIN-07)."""


def test_package_version():
    """dmccodegui.__version__ must equal '4.0.0'."""
    import dmccodegui
    assert dmccodegui.__version__ == "4.0.0", (
        f"Expected __version__ == '4.0.0', got {dmccodegui.__version__!r}"
    )


def test_dmc_app_title_contains_version():
    """DMCApp.title class attribute must contain 'Binh An HMI v4.0.0'."""
    # Import without instantiating (Kivy runtime not available in tests)
    import importlib
    import sys

    # Ensure sys.frozen is absent so the frozen block doesn't fire
    if hasattr(sys, "frozen"):
        del sys.frozen

    # We need to import just the class — use importlib to avoid triggering
    # Kivy window creation (the module-level imports do NOT start a window).
    import dmccodegui.main as m
    importlib.reload(m)

    assert hasattr(m.DMCApp, "title"), "DMCApp must have a 'title' class attribute"
    assert "Binh An HMI v4.0.0" in m.DMCApp.title, (
        f"DMCApp.title must contain 'Binh An HMI v4.0.0', got {m.DMCApp.title!r}"
    )
