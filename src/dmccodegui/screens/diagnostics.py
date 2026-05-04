"""DiagnosticsScreen — placeholder for diagnostics screen."""
from __future__ import annotations

from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import Screen


class DiagnosticsScreen(Screen):
    """Reserved screen for future diagnostics tooling.

    Currently a stub — holds controller and state properties for injection
    by the screen loader but does not implement any diagnostic UI yet.
    """

    controller = ObjectProperty(None, allownone=True)
    state = ObjectProperty(None, allownone=True)
