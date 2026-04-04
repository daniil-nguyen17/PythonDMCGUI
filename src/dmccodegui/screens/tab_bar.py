"""TabBar widget — role-based navigation tabs."""
from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.properties import StringProperty


class TabBar(BoxLayout):
    """Horizontal tab bar that shows role-appropriate navigation tabs."""

    current_tab = StringProperty("run")

    ALL_TABS = [
        ("run", "\u25B6\nRun"),
        ("axes_setup", "\u2699\nAxes Setup"),
        ("parameters", "\u2630\nParameters"),
        ("diagnostics", "\u2609\nDiagnostics"),
    ]

    ROLE_TABS = {
        "operator": ["run"],
        "setup": ["run", "axes_setup", "parameters"],
        "admin": ["run", "axes_setup", "parameters", "diagnostics"],
    }

    _current_role: str = ""

    def set_role(self, role: str, current_tab: str = "run") -> None:
        """Rebuild tabs for the given role. No-op if role has not changed."""
        if role == self._current_role:
            return
        self._current_role = role

        self.clear_widgets()
        allowed = self.ROLE_TABS.get(role, ["run"])
        tab_map = {name: label for name, label in self.ALL_TABS}

        for name in allowed:
            label = tab_map.get(name, name)
            btn = Button(
                text=label,
                group="tabs",
                halign="center",
                valign="middle",
                font_size="12sp",
            )
            btn.background_normal = ""
            btn.background_down = ""
            if name == current_tab:
                btn.background_color = [0.133, 0.773, 0.369, 0.3]  # accent active
                btn.state = "down"
            else:
                btn.background_color = [0.071, 0.094, 0.133, 1]
            # Capture name in closure
            btn.bind(on_release=lambda b, n=name: self._on_tab_press(b, n))
            self.add_widget(btn)

        self.current_tab = current_tab

    def _on_tab_press(self, btn: Button, name: str) -> None:
        """Update visual state and set current_tab (triggers ScreenManager switch)."""
        # Reset all buttons to inactive
        for child in self.children:
            child.background_color = [0.071, 0.094, 0.133, 1]
        # Highlight pressed button
        btn.background_color = [0.133, 0.773, 0.369, 0.3]
        self.current_tab = name
