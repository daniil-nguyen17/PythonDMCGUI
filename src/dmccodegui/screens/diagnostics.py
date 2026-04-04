"""DiagnosticsScreen — placeholder for diagnostics screen."""
from __future__ import annotations

from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty


class DiagnosticsScreen(Screen):
    controller = ObjectProperty(None, allownone=True)
    state = ObjectProperty(None, allownone=True)
