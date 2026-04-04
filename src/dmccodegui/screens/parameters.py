"""ParametersScreen — placeholder for parameters screen."""
from __future__ import annotations

from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty


class ParametersScreen(Screen):
    controller = ObjectProperty(None, allownone=True)
    state = ObjectProperty(None, allownone=True)
