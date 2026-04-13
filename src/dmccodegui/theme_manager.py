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
        "bg_dark": [0.945, 0.935, 0.910, 1],       # warm cream (yellow hue)
        "bg_panel": [0.910, 0.900, 0.875, 1],       # slightly darker warm panel
        "bg_row": [0.875, 0.865, 0.840, 1],         # row bg warm
        "bg_card": [0.960, 0.952, 0.930, 1],        # card bg warm lighter
        "border": [0.750, 0.735, 0.700, 1],         # warm border
        "text_main": [0.100, 0.100, 0.120, 1],      # near-black text for contrast
        "text_mid": [0.280, 0.280, 0.320, 1],       # dark gray secondary
        "text_dim": [0.450, 0.440, 0.470, 1],       # medium gray dim
        "input_bg": [0.970, 0.965, 0.950, 1],       # warm white input
        "input_fg": [0.100, 0.100, 0.120, 1],       # dark input text
        "input_cursor": [0.280, 0.280, 0.320, 1],
        "input_hint": [0.500, 0.490, 0.510, 0.9],
        "overlay_bg": [0.945, 0.935, 0.910, 0.95],
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
