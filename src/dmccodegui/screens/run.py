"""RunScreen — placeholder for the operator run screen."""
from __future__ import annotations

from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty


class RunScreen(Screen):
    controller = ObjectProperty(None, allownone=True)
    state = ObjectProperty(None, allownone=True)
