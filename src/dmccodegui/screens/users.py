"""UsersScreen and UserEditOverlay — Admin-only user management screen."""
from __future__ import annotations

from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Kivy classes — only imported when a Kivy event loop is present
# ---------------------------------------------------------------------------

try:
    from kivy.clock import Clock
    from kivy.properties import ObjectProperty, StringProperty
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    from kivy.uix.modalview import ModalView
    from kivy.uix.popup import Popup
    from kivy.uix.screenmanager import Screen
    from kivy.uix.textinput import TextInput
    from dmccodegui.theme_manager import theme

    # Role badge colours (RGBA tuples)
    _ROLE_COLORS = {
        "operator": (0.133, 0.773, 0.369, 0.9),   # green
        "setup":    (1.0,   0.65,  0.0,   0.9),   # orange
        "admin":    (0.0,   0.8,   0.85,  0.9),   # cyan
    }
    _ROLE_LABELS = {
        "operator": "Operator",
        "setup":    "Setup",
        "admin":    "Admin",
    }
    _ROLES = ["operator", "setup", "admin"]

    # ------------------------------------------------------------------
    # UserEditOverlay
    # ------------------------------------------------------------------

    class UserEditOverlay(ModalView):
        """Modal overlay for creating or editing a user account.

        Usage:
            overlay = UserEditOverlay()
            overlay.open_for_add(auth_manager, current_user="Admin", on_saved=callback)
            # or
            overlay.open_for_edit(auth_manager, "Operator", current_user="Admin", on_saved=callback)
        """

        error_msg = StringProperty("")
        target_name = StringProperty("")
        current_user = StringProperty("")

        def __init__(self, **kwargs):
            kwargs.setdefault("auto_dismiss", False)
            kwargs.setdefault("size_hint", (None, None))
            kwargs.setdefault("width", "500dp")
            kwargs.setdefault("height", "480dp")
            super().__init__(**kwargs)
            self._auth_manager = None
            self._on_saved: Optional[Callable[[], None]] = None
            self._selected_role: str = "operator"
            self._error_clear_event = None

        def open_for_add(
            self,
            auth_manager,
            current_user: str = "",
            on_saved: Optional[Callable[[], None]] = None,
        ) -> None:
            """Prepare the overlay for adding a new user, then open it."""
            self._auth_manager = auth_manager
            self._on_saved = on_saved
            self.current_user = current_user
            self.target_name = ""
            self.error_msg = ""
            self._selected_role = "operator"
            # Wait until widgets are ready before setting values
            Clock.schedule_once(lambda *_: self._init_fields_for_add(), 0)
            self.open()

        def open_for_edit(
            self,
            auth_manager,
            name: str,
            current_user: str = "",
            on_saved: Optional[Callable[[], None]] = None,
        ) -> None:
            """Prepare the overlay for editing an existing user, then open it."""
            self._auth_manager = auth_manager
            self._on_saved = on_saved
            self.current_user = current_user
            self.target_name = name
            self.error_msg = ""

            users = {u["name"]: u for u in auth_manager.get_all_users()}
            user_info = users.get(name, {})
            current_role = user_info.get("role", "operator")
            self._selected_role = current_role

            Clock.schedule_once(lambda *_: self._init_fields_for_edit(name, current_role), 0)
            self.open()

        def _init_fields_for_add(self) -> None:
            """Clear all fields after the overlay has opened."""
            try:
                self.ids.name_input.text = ""
                self.ids.pin_input.text = ""
            except Exception:
                pass
            self._select_role("operator")

        def _init_fields_for_edit(self, name: str, current_role: str) -> None:
            """Populate fields for editing an existing user."""
            try:
                self.ids.name_input.text = name
                self.ids.pin_input.text = ""
            except Exception:
                pass
            self._select_role(current_role)
            # Disable role buttons if editing self (no self-demotion)
            is_self = (name == self.current_user)
            try:
                for role in _ROLES:
                    btn = self.ids[f"role_btn_{role}"]
                    btn.disabled = is_self
                    btn.opacity = 0.4 if is_self else 1.0
            except Exception:
                pass

        def _select_role(self, role: str) -> None:
            """Update button visual state to reflect the selected role."""
            self._selected_role = role
            try:
                for r in _ROLES:
                    btn = self.ids[f"role_btn_{r}"]
                    if r == role:
                        color = _ROLE_COLORS.get(r, (0.3, 0.3, 0.3, 1))
                        btn.background_color = color
                    else:
                        btn.background_color = tuple(theme.bg_row)
            except Exception:
                pass

        def press_save(self) -> None:
            """Read fields, call CRUD method, handle errors or success."""
            try:
                name = self.ids.name_input.text.strip()
                pin = self.ids.pin_input.text.strip()
                role = self._selected_role
            except Exception:
                return

            if self._auth_manager is None:
                self._show_error("No auth manager available.")
                return

            if self.target_name == "":
                # Add mode
                error = self._auth_manager.create_user(name, pin, role)
            else:
                # Edit mode
                new_name = name if name != self.target_name else None
                new_pin = pin if pin else None
                new_role = role
                error = self._auth_manager.update_user(
                    self.target_name,
                    new_name=new_name,
                    new_pin=new_pin,
                    new_role=new_role,
                    current_user=self.current_user,
                )

            if error:
                self._show_error(error)
            else:
                self.dismiss()
                if callable(self._on_saved):
                    self._on_saved()

        def _show_error(self, message: str) -> None:
            """Display an error message and auto-clear after 3 seconds."""
            if self._error_clear_event:
                self._error_clear_event.cancel()
            self.error_msg = message
            self._error_clear_event = Clock.schedule_once(
                lambda *_: setattr(self, "error_msg", ""), 3
            )

        def press_cancel(self) -> None:
            """Dismiss the overlay without saving."""
            self.dismiss()

    # ------------------------------------------------------------------
    # UsersScreen
    # ------------------------------------------------------------------

    class UsersScreen(Screen):
        """Admin-only screen for managing user accounts.

        Displays a scrollable card list of all users. Provides Add, Edit,
        and Delete actions via modal overlays and confirmation popups.

        Properties injected by main.py:
            auth_manager (AuthManager): CRUD interface for users.json
            state (MachineState): Current login state.
        """

        auth_manager = ObjectProperty(None, allownone=True)
        state = ObjectProperty(None, allownone=True)

        # ------------------------------------------------------------------
        # Lifecycle
        # ------------------------------------------------------------------

        def on_pre_enter(self, *args) -> None:
            """Refresh the user card list each time the screen is entered."""
            self._rebuild_cards()

        # ------------------------------------------------------------------
        # Card builder
        # ------------------------------------------------------------------

        def _rebuild_cards(self) -> None:
            """Clear and repopulate the cards_container from auth_manager data."""
            try:
                container = self.ids.cards_container
            except Exception:
                return

            container.clear_widgets()

            if self.auth_manager is None:
                return

            users = self.auth_manager.get_all_users()
            for user in users:
                card = self._make_card(user["name"], user["role"], user["pin_masked"])
                container.add_widget(card)

        def _make_card(self, name: str, role: str, pin_masked: str) -> BoxLayout:
            """Build a single user card widget."""
            from dmccodegui.theme_manager import theme

            role_color = _ROLE_COLORS.get(role, (0.5, 0.5, 0.5, 0.9))
            role_label = _ROLE_LABELS.get(role, role.capitalize())

            # Outer card: horizontal layout with left colour stripe
            card = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height="80dp",
                spacing=0,
            )

            # Left role-colour stripe
            from kivy.uix.widget import Widget
            stripe = Widget(size_hint_x=None, width="6dp")
            with stripe.canvas.before:
                from kivy.graphics import Color, Rectangle
                Color(*role_color)
                Rectangle(pos=stripe.pos, size=stripe.size)
            stripe.bind(
                pos=lambda w, v: self._redraw(w),
                size=lambda w, v: self._redraw(w),
            )
            card.add_widget(stripe)

            # Card body background
            body = BoxLayout(
                orientation="horizontal",
                padding=("12dp", "8dp"),
                spacing="12dp",
            )
            with body.canvas.before:
                from kivy.graphics import Color, Rectangle
                Color(*theme.bg_card)
                self._card_bg_rect = Rectangle(pos=body.pos, size=body.size)
            body.bind(
                pos=lambda w, v: self._redraw_rect(w),
                size=lambda w, v: self._redraw_rect(w),
            )

            # --- Info column ---
            info_col = BoxLayout(orientation="vertical", spacing="4dp")

            # Name
            name_lbl = Label(
                text=name,
                font_size="20sp",
                bold=True,
                color=theme.text_main,
                halign="left",
                valign="middle",
                size_hint_y=None,
                height="36dp",
            )
            name_lbl.bind(size=name_lbl.setter("text_size"))
            info_col.add_widget(name_lbl)

            # Role badge + masked PIN row
            badge_row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height="28dp",
                spacing="10dp",
            )

            role_badge = Label(
                text=f"  {role_label}  ",
                font_size="14sp",
                color=(0.02, 0.02, 0.02, 1),
                size_hint_x=None,
                width="90dp",
                size_hint_y=None,
                height="24dp",
                halign="center",
                valign="middle",
            )
            with role_badge.canvas.before:
                from kivy.graphics import Color, RoundedRectangle
                Color(*role_color)
                RoundedRectangle(
                    pos=role_badge.pos,
                    size=role_badge.size,
                    radius=[8],
                )
            role_badge.bind(
                pos=lambda w, v: self._redraw(w),
                size=lambda w, v: self._redraw(w),
            )
            badge_row.add_widget(role_badge)

            pin_lbl = Label(
                text=pin_masked,
                font_size="18sp",
                color=theme.text_dim,
                halign="left",
                valign="middle",
            )
            pin_lbl.bind(size=pin_lbl.setter("text_size"))
            badge_row.add_widget(pin_lbl)

            info_col.add_widget(badge_row)
            body.add_widget(info_col)

            # --- Buttons column ---
            btn_col = BoxLayout(
                orientation="horizontal",
                size_hint_x=None,
                width="200dp",
                spacing="8dp",
                padding=("0dp", "8dp"),
            )

            edit_btn = Button(
                text="Edit",
                font_size="17sp",
                size_hint_y=None,
                height="50dp",
                background_normal="",
                background_color=(0.1, 0.35, 0.65, 1),
                color=(1, 1, 1, 1),
            )
            edit_btn.bind(on_release=lambda *_, n=name: self.on_edit_press(n))
            btn_col.add_widget(edit_btn)

            delete_btn = Button(
                text="Delete",
                font_size="17sp",
                size_hint_y=None,
                height="50dp",
                background_normal="",
                background_color=(0.65, 0.1, 0.1, 1),
                color=(1, 1, 1, 1),
            )
            delete_btn.bind(on_release=lambda *_, n=name: self.on_delete_press(n))
            btn_col.add_widget(delete_btn)

            body.add_widget(btn_col)
            card.add_widget(body)

            return card

        @staticmethod
        def _redraw(widget) -> None:
            """Force canvas redraw by clearing and re-instructing."""
            widget.canvas.before.clear()

        @staticmethod
        def _redraw_rect(widget) -> None:
            """No-op — canvas bind handles rectangle updates via lambda."""
            pass

        # ------------------------------------------------------------------
        # Action handlers
        # ------------------------------------------------------------------

        def on_add_press(self) -> None:
            """Open UserEditOverlay in add mode."""
            overlay = UserEditOverlay()
            current_user = ""
            if self.state:
                current_user = getattr(self.state, "current_user", "")
            overlay.open_for_add(
                self.auth_manager,
                current_user=current_user,
                on_saved=self._rebuild_cards,
            )

        def on_edit_press(self, name: str) -> None:
            """Open UserEditOverlay in edit mode for the named user."""
            overlay = UserEditOverlay()
            current_user = ""
            if self.state:
                current_user = getattr(self.state, "current_user", "")
            overlay.open_for_edit(
                self.auth_manager,
                name,
                current_user=current_user,
                on_saved=self._rebuild_cards,
            )

        def on_delete_press(self, name: str) -> None:
            """Show a confirmation popup before deleting a user."""
            content = BoxLayout(
                orientation="vertical",
                padding="16dp",
                spacing="12dp",
            )
            msg = Label(
                text=f"Delete user '{name}'?\nThis cannot be undone.",
                font_size="18sp",
                halign="center",
                valign="middle",
                color=(0.886, 0.910, 0.941, 1),
            )
            msg.bind(size=msg.setter("text_size"))
            content.add_widget(msg)

            btn_row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height="52dp",
                spacing="12dp",
            )
            cancel_btn = Button(
                text="Cancel",
                font_size="17sp",
                background_normal="",
                background_color=(0.3, 0.3, 0.3, 1),
            )
            delete_btn = Button(
                text="Delete",
                font_size="17sp",
                background_normal="",
                background_color=(0.7, 0.1, 0.1, 1),
            )
            btn_row.add_widget(cancel_btn)
            btn_row.add_widget(delete_btn)
            content.add_widget(btn_row)

            popup = Popup(
                title=f"Confirm Delete",
                content=content,
                size_hint=(0.45, 0.35),
                auto_dismiss=False,
            )
            cancel_btn.bind(on_release=lambda *_: popup.dismiss())
            delete_btn.bind(
                on_release=lambda *_: (popup.dismiss(), self._do_delete(name))
            )
            popup.open()

        def _do_delete(self, name: str) -> None:
            """Execute the delete and handle outcomes."""
            if self.auth_manager is None:
                return

            error = self.auth_manager.delete_user(name)
            if error:
                self._show_error_popup(error)
                return

            # If we deleted the currently logged-in user, force logout
            current_user = ""
            if self.state:
                current_user = getattr(self.state, "current_user", "")
            if current_user and current_user == name:
                if self.state:
                    self.state.set_auth("", "operator")

            self._rebuild_cards()

        def _show_error_popup(self, message: str) -> None:
            """Display a simple error popup."""
            lbl = Label(
                text=message,
                font_size="17sp",
                halign="center",
                valign="middle",
                color=(0.886, 0.910, 0.941, 1),
            )
            lbl.bind(size=lbl.setter("text_size"))
            popup = Popup(
                title="Error",
                content=lbl,
                size_hint=(0.5, 0.3),
            )
            popup.open()

except ImportError:
    # Kivy not available (headless test environment) — skip UI classes silently.
    pass
