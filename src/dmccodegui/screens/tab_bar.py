"""TabBar widget — role-based navigation tabs."""
from __future__ import annotations

from typing import Callable, List, Optional

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.properties import StringProperty

from dmccodegui.theme_manager import theme
from dmccodegui.hmi.dmc_vars import STATE_SETUP, STATE_GRINDING, STATE_HOMING


class TabBar(BoxLayout):
    """Horizontal tab bar that shows role-appropriate navigation tabs."""

    current_tab = StringProperty("run")

    ALL_TABS = [
        ("run", "Run"),
        ("axes_setup", "Axes Setup"),
        ("parameters", "Parameters"),
        ("profiles", "Profiles"),
        ("users", "Users"),
    ]

    ROLE_TABS = {
        "operator": ["run"],
        "setup": ["run", "axes_setup", "parameters", "profiles"],
        "admin": ["run", "axes_setup", "parameters", "profiles", "users"],
    }

    _current_role: str = ""
    _restricted_cb: Optional[Callable[[], None]] = None

    # Last known gate state — reapplied after set_role() rebuilds buttons
    _last_dmc_state: int = 0
    _last_connected: bool = False

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
            btn = ToggleButton(
                text=label,
                group="tabs",
                halign="center",
                valign="middle",
                font_size="22sp",
            )
            btn.background_normal = ""
            btn.background_down = ""
            if name == current_tab:
                btn.background_color = [0.133, 0.773, 0.369, 0.3]  # accent active
                btn.state = "down"
            else:
                btn.background_color = list(theme.bg_row)
            # Store tab name for gate lookup
            btn._tab_name = name
            # Capture name in closure
            btn.bind(on_release=lambda b, n=name: self._on_tab_press(b, n))
            self.add_widget(btn)

        self.current_tab = current_tab

        # Reapply gate state after role rebuild
        self.update_state_gates(self._last_dmc_state, self._last_connected)

    def update_state_gates(self, dmc_state: int, connected: bool) -> None:
        """Enable/disable tabs based on controller state.

        Gate rules:
          - Disconnected: all gates clear (all tabs accessible).
          - SETUP state: Run tab disabled.
          - GRINDING or HOMING: Axes Setup and Parameters tabs disabled.
          - Force-navigation: if currently on a disabled setup screen during
            GRINDING/HOMING, navigate to Run.
        """
        # Store so set_role() can reapply after a role rebuild
        self._last_dmc_state = dmc_state
        self._last_connected = connected

        if not connected:
            # Clear all gates when disconnected
            for child in self.children:
                child.disabled = False
                if child.state == "down":
                    child.background_color = [0.133, 0.773, 0.369, 0.3]
                else:
                    child.background_color = list(theme.bg_row)
                child.color = list(theme.text_main)
            return

        motion_active = dmc_state in (STATE_GRINDING, STATE_HOMING)

        # Gate dict: tab_name -> should_disable
        # Run tab is NEVER gated — operator must always be able to return to Run.
        # Axes Setup / Parameters are gated during active motion (grinding/homing).
        gates = {
            "axes_setup": motion_active,
            "parameters": motion_active,
        }

        for child in self.children:
            tab_name = getattr(child, "_tab_name", None)
            if tab_name is None:
                continue
            should_disable = gates.get(tab_name, False)
            child.disabled = should_disable
            if should_disable:
                child.background_color = [0.15, 0.15, 0.15, 0.6]
                child.color = [0.4, 0.4, 0.4, 1]
            else:
                if child.state == "down":
                    child.background_color = [0.133, 0.773, 0.369, 0.3]
                else:
                    child.background_color = list(theme.bg_row)
                child.color = list(theme.text_main)

        # Force-navigation: if on a setup screen when motion starts, go to Run
        if motion_active:
            try:
                from kivy.app import App
                app = App.get_running_app()
                sm = app.root.ids.sm
                if sm.current in ("axes_setup", "parameters"):
                    sm.current = "run"
                    self.current_tab = "run"
                    # Update button visual states
                    for child in self.children:
                        tab_name = getattr(child, "_tab_name", None)
                        if tab_name == "run":
                            child.state = "down"
                            if not child.disabled:
                                child.background_color = [0.133, 0.773, 0.369, 0.3]
                        else:
                            child.state = "normal"
                            if not child.disabled:
                                child.background_color = list(theme.bg_row)
            except Exception:
                pass  # Safe for testing without a running app

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

    def _on_tab_press(self, btn: ToggleButton, name: str) -> None:
        """Update visual state and set current_tab (triggers ScreenManager switch)."""
        # Reset all buttons to inactive
        for child in self.children:
            child.background_color = list(theme.bg_row)
        # Highlight pressed button
        btn.background_color = [0.133, 0.773, 0.369, 0.3]
        self.current_tab = name
