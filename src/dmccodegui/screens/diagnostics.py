"""DiagnosticsScreen — placeholder for diagnostics screen."""
from __future__ import annotations

from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import Screen


class DiagnosticsScreen(Screen):
    controller = ObjectProperty(None, allownone=True)
    state = ObjectProperty(None, allownone=True)
