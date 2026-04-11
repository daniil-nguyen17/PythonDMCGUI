"""Flat Grind screen package.

Loads KV files and exports screen classes. Importing this package
automatically registers KV rules for all Flat Grind screens.
"""
import os
from kivy.lang import Builder

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_UI_DIR = os.path.normpath(os.path.join(_PKG_DIR, '..', '..', 'ui', 'flat_grind'))

Builder.load_file(os.path.join(_UI_DIR, 'run.kv'))
Builder.load_file(os.path.join(_UI_DIR, 'axes_setup.kv'))
Builder.load_file(os.path.join(_UI_DIR, 'parameters.kv'))

from .run import FlatGrindRunScreen  # noqa: E402
from .axes_setup import FlatGrindAxesSetupScreen  # noqa: E402
from .parameters import FlatGrindParametersScreen  # noqa: E402

__all__ = [
    "FlatGrindRunScreen",
    "FlatGrindAxesSetupScreen",
    "FlatGrindParametersScreen",
]
