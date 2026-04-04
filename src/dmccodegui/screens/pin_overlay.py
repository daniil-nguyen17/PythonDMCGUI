"""PINOverlay — fullscreen ModalView PIN entry for login, user switch, and role unlock."""
from __future__ import annotations

from kivy.uix.modalview import ModalView
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.properties import StringProperty, ObjectProperty
from kivy.animation import Animation
from kivy.clock import Clock


class PINOverlay(ModalView):
    """Fullscreen PIN entry overlay.

    Modes:
        login   — startup authentication, pre-selects last_user
        switch  — switch to a different user account
        unlock  — elevate to Setup/Admin role on restricted tab tap
    """

    username = StringProperty("")
    pin_dots = StringProperty("")
    error_msg = StringProperty("")
    mode = StringProperty("login")

    # Injected from app
    auth_manager = ObjectProperty(None, allownone=True)

    # Callback: on_success(username: str, role: str)
    on_success = ObjectProperty(None, allownone=True)

    def on_kv_post(self, *_) -> None:
        self._pin_digits: str = ""

    # ------------------------------------------------------------------
    # Public open helpers
    # ------------------------------------------------------------------

    def open_for_login(self, auth_manager, on_success) -> None:
        """Open overlay for initial login. Pre-selects last logged-in user."""
        self.auth_manager = auth_manager
        self.on_success = on_success
        self.mode = "login"
        self.username = auth_manager.last_user
        self._clear_input()
        self.open()

    def open_for_unlock(self, auth_manager, on_success) -> None:
        """Open overlay for role elevation (restricted tab tap).

        Any Setup or Admin user can authenticate. Show user list if more than
        one elevated user exists.
        """
        self.auth_manager = auth_manager
        self.on_success = on_success
        self.mode = "unlock"
        # Pre-select first elevated user if available
        elevated = [
            name for name in auth_manager.user_names
            if auth_manager.get_role(name) in ("setup", "admin")
        ]
        self.username = elevated[0] if elevated else ""
        self._clear_input()
        self.open()

    def open_for_switch(self, auth_manager, on_success) -> None:
        """Open overlay for user switching from status bar."""
        self.auth_manager = auth_manager
        self.on_success = on_success
        self.mode = "switch"
        self.username = auth_manager.last_user
        self._clear_input()
        self.open()

    # ------------------------------------------------------------------
    # Numpad actions
    # ------------------------------------------------------------------

    def press_digit(self, digit: str) -> None:
        """Append a digit to the current PIN (max 6 digits)."""
        if len(self._pin_digits) >= 6:
            return
        self._pin_digits += digit
        self.pin_dots = "\u25cf" * len(self._pin_digits)
        self.error_msg = ""

    def press_backspace(self) -> None:
        """Remove the last digit from the current PIN."""
        self._pin_digits = self._pin_digits[:-1]
        self.pin_dots = "\u25cf" * len(self._pin_digits)

    def press_enter(self) -> None:
        """Validate the entered PIN against the auth manager."""
        if not self.auth_manager:
            return
        if not self.username:
            self.error_msg = "Select a user first"
            return
        role = self.auth_manager.validate_pin(self.username, self._pin_digits)
        if role is not None:
            self.dismiss()
            if self.on_success:
                self.on_success(self.username, role)
        else:
            self._show_error()

    # ------------------------------------------------------------------
    # User list
    # ------------------------------------------------------------------

    def show_user_list(self) -> None:
        """Show a scrollable list of users to select from."""
        if not self.auth_manager:
            return

        # Build a popup-style list inside a BoxLayout swapped into the card
        user_list_layout = self.ids.get("user_list_layout")
        numpad_layout = self.ids.get("numpad_layout")
        if user_list_layout is None or numpad_layout is None:
            return

        # Clear existing user buttons and rebuild
        user_list_layout.clear_widgets()

        names = self.auth_manager.user_names
        for name in names:
            btn = Button(
                text=name,
                size_hint_y=None,
                height="56dp",
                font_size="18sp",
                background_normal="",
                background_down="",
                background_color=[0.071, 0.094, 0.133, 1],
                color=[0.875, 0.906, 0.949, 1],
            )
            btn.bind(on_release=lambda b, n=name: self._select_user(n))
            user_list_layout.add_widget(btn)

        # Show user list, hide numpad
        numpad_layout.opacity = 0
        numpad_layout.disabled = True
        user_list_layout.opacity = 1
        user_list_layout.disabled = False

    def _select_user(self, name: str) -> None:
        """Select a user from the list and return to PIN entry."""
        self.username = name
        self._clear_input()

        user_list_layout = self.ids.get("user_list_layout")
        numpad_layout = self.ids.get("numpad_layout")
        if user_list_layout is None or numpad_layout is None:
            return

        # Hide user list, show numpad
        user_list_layout.opacity = 0
        user_list_layout.disabled = True
        numpad_layout.opacity = 1
        numpad_layout.disabled = False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _clear_input(self) -> None:
        """Reset PIN digits, dots, and error message."""
        self._pin_digits = ""
        self.pin_dots = ""
        self.error_msg = ""

    def _show_error(self) -> None:
        """Display error, clear input, shake the PIN card."""
        self.error_msg = "Invalid PIN"
        self._clear_input()

        card = self.ids.get("pin_card")
        if card:
            orig_x = card.x
            shake = (
                Animation(x=orig_x - 12, duration=0.05)
                + Animation(x=orig_x + 12, duration=0.05)
                + Animation(x=orig_x - 8, duration=0.05)
                + Animation(x=orig_x + 8, duration=0.05)
                + Animation(x=orig_x, duration=0.05)
            )
            shake.start(card)

        Clock.schedule_once(lambda *_: setattr(self, "error_msg", ""), 2)
