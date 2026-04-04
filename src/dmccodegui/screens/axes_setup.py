"""AxesSetupScreen — placeholder for axes setup screen."""
from __future__ import annotations

from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty


class AxesSetupScreen(Screen):
    controller = ObjectProperty(None, allownone=True)
    state = ObjectProperty(None, allownone=True)
