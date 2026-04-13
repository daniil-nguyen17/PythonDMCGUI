"""Serration screen package.

Exports screen classes. KV files are loaded via load_kv() which must be
called before screen instantiation (main.py build() handles this).

NOTE: KV loading is NOT done at import time to avoid circular imports
when screens/__init__.py imports this package while dmccodegui.screens
is still being initialized. Kivy's #:import directive in the KV files
references dmccodegui.screens.serration.* which fails if the parent
package attribute is not yet set.
"""
import os
from kivy.lang import Builder

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_UI_DIR = os.path.normpath(os.path.join(_PKG_DIR, '..', '..', 'ui', 'serration'))

_kv_loaded = False


def load_kv() -> None:
    """Load Serration KV files. Safe to call multiple times (idempotent)."""
    global _kv_loaded
    if _kv_loaded:
        return
    Builder.load_file(os.path.join(_UI_DIR, 'run.kv'))
    Builder.load_file(os.path.join(_UI_DIR, 'axes_setup.kv'))
    Builder.load_file(os.path.join(_UI_DIR, 'parameters.kv'))
    _kv_loaded = True


from .run import SerrationRunScreen  # noqa: E402
from .axes_setup import SerrationAxesSetupScreen  # noqa: E402
from .parameters import SerrationParametersScreen  # noqa: E402

__all__ = [
    "SerrationRunScreen",
    "SerrationAxesSetupScreen",
    "SerrationParametersScreen",
    "load_kv",
]
