from __future__ import annotations

from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import Screen

from ..app_state import MachineState
from ..controller import GalilController


class SettingsScreen(Screen):
    controller: GalilController = ObjectProperty(None)  # type: ignore
    state: MachineState = ObjectProperty(None)  # type: ignore

