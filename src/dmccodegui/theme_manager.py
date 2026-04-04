"""Theme manager for light/dark mode switching."""
from __future__ import annotations

from kivy.event import EventDispatcher
from kivy.properties import StringProperty, ListProperty


class ThemeManager(EventDispatcher):
    """Holds current theme colors. Widgets bind to these properties."""

    mode = StringProperty("dark")

    # Backgrounds
    bg_dark = ListProperty([0.031, 0.047, 0.071, 1])
    bg_panel = ListProperty([0.051, 0.071, 0.102, 1])
    bg_row = ListProperty([0.071, 0.094, 0.133, 1])
    bg_card = ListProperty([0.051, 0.071, 0.102, 1])

    # Borders
    border = ListProperty([0.118, 0.145, 0.188, 1])

    # Text
    text_main = ListProperty([0.886, 0.910, 0.941, 1])
    text_mid = ListProperty([0.580, 0.631, 0.710, 1])
    text_dim = ListProperty([0.282, 0.333, 0.420, 1])

    # Input
    input_bg = ListProperty([0.031, 0.047, 0.071, 1])
    input_fg = ListProperty([0.886, 0.910, 0.941, 1])
    input_cursor = ListProperty([0.580, 0.631, 0.710, 1])
    input_hint = ListProperty([0.282, 0.333, 0.420, 0.9])

    # PIN overlay
    overlay_bg = ListProperty([0.031, 0.047, 0.071, 0.95])

    DARK = {
        "bg_dark": [0.031, 0.047, 0.071, 1],
        "bg_panel": [0.051, 0.071, 0.102, 1],
        "bg_row": [0.071, 0.094, 0.133, 1],
        "bg_card": [0.051, 0.071, 0.102, 1],
        "border": [0.118, 0.145, 0.188, 1],
        "text_main": [0.886, 0.910, 0.941, 1],
        "text_mid": [0.580, 0.631, 0.710, 1],
        "text_dim": [0.282, 0.333, 0.420, 1],
        "input_bg": [0.031, 0.047, 0.071, 1],
        "input_fg": [0.886, 0.910, 0.941, 1],
        "input_cursor": [0.580, 0.631, 0.710, 1],
        "input_hint": [0.282, 0.333, 0.420, 0.9],
        "overlay_bg": [0.031, 0.047, 0.071, 0.95],
    }

    LIGHT = {
        "bg_dark": [0.925, 0.929, 0.933, 1],       # warm off-white
        "bg_panel": [0.898, 0.902, 0.910, 1],       # slightly darker panel
        "bg_row": [0.871, 0.878, 0.890, 1],         # row bg
        "bg_card": [0.949, 0.953, 0.957, 1],        # card bg slightly lighter
        "border": [0.780, 0.792, 0.812, 1],
        "text_main": [0.133, 0.153, 0.192, 1],      # dark text
        "text_mid": [0.349, 0.380, 0.435, 1],
        "text_dim": [0.545, 0.573, 0.624, 1],
        "input_bg": [0.949, 0.953, 0.957, 1],
        "input_fg": [0.133, 0.153, 0.192, 1],
        "input_cursor": [0.349, 0.380, 0.435, 1],
        "input_hint": [0.545, 0.573, 0.624, 0.9],
        "overlay_bg": [0.925, 0.929, 0.933, 0.95],
    }

    def toggle(self) -> str:
        """Toggle between light and dark mode. Returns new mode."""
        new_mode = "light" if self.mode == "dark" else "dark"
        self.set_mode(new_mode)
        return new_mode

    def set_mode(self, mode: str) -> None:
        """Apply a theme mode ('light' or 'dark')."""
        palette = self.LIGHT if mode == "light" else self.DARK
        self.mode = mode
        for key, value in palette.items():
            setattr(self, key, value)


# Singleton instance
theme = ThemeManager()
