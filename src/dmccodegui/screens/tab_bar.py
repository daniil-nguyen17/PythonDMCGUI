"""TabBar widget — role-based navigation tabs."""
from __future__ import annotations

from typing import Callable, List, Optional

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
    _restricted_cb: Optional[Callable[[], None]] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def _tabs_for_role(role: str) -> List[str]:
        """Return list of allowed tab names for the given role.

        Unknown roles default to Operator view (run only). Pure Python — no
        Kivy needed, allowing direct unit testing.
        """
        return TabBar.ROLE_TABS.get(role, ["run"])

    def set_role(self, role: str, current_tab: str = "run") -> None:
        """Rebuild tabs for the given role. No-op if role has not changed."""
        if role == self._current_role:
            return
        self._current_role = role

        self.clear_widgets()
        allowed = self._tabs_for_role(role)
        tab_map = {name: label for name, label in self.ALL_TABS}

        # Ensure current_tab is in allowed tabs; fall back to "run"
        if current_tab not in allowed:
            current_tab = "run"

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

    def set_restricted_callback(self, cb: Callable[[], None]) -> None:
        """Register a callback invoked when user presses a restricted tab.

        The callback (e.g. lambda: app._show_pin_overlay("unlock")) is called
        instead of switching screens when the tab is not in the current role's
        allowed set.
        """
        self._restricted_cb = cb

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _on_tab_press(self, btn: Button, name: str) -> None:
        """Update visual state and set current_tab (triggers ScreenManager switch)."""
        # Reset all buttons to inactive
        for child in self.children:
            child.background_color = [0.071, 0.094, 0.133, 1]
        # Highlight pressed button
        btn.background_color = [0.133, 0.773, 0.369, 0.3]
        self.current_tab = name
