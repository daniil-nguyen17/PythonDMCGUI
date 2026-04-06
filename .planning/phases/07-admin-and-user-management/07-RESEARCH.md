# Phase 7: Admin and User Management - Research

**Researched:** 2026-04-06
**Domain:** Kivy CRUD UI + AuthManager extension + JSON user store
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Screen Location & Access**
- New "Users" tab added to tab bar as the 6th (last) tab, after Diagnostics
- Tab order: Run, Axes Setup, Parameters, Profiles, Diagnostics, Users
- Visible to Admin role only — Operator and Setup never see it
- No additional PIN re-entry required; being logged in as Admin is sufficient
- Tab bar ROLE_TABS updated: admin list gets "users" appended

**User List Display**
- Card-based layout — one card per user showing name, role badge, and action buttons (Edit, Delete)
- Consistent with card patterns used elsewhere (Parameters screen cards)
- "Add User" button positioned at top-right of the Users screen, always visible

**Edit Flow**
- Tap "Edit" on a user card opens a centered modal overlay (reuses PIN overlay pattern)
- Overlay contains fields: Name (text input), PIN (numeric input, masked), Role (selector)
- Save and Cancel buttons on the overlay
- Same overlay pattern used for "Add User" (pre-populated with defaults)

**Delete Behavior**
- Tap "Delete" shows confirmation dialog: "Are you sure you want to delete [name]?" with Cancel/Confirm
- Prevents accidental deletions on touchscreen

**PIN Rules**
- PIN length: 4-6 digits (enforced on create and edit)
- Duplicate PINs not allowed — show error if PIN is already taken by another user
- PIN displayed as masked dots in the user list; visible in edit overlay for Admin to set

**Role Assignment**
- Three roles available: Operator, Setup, Admin (existing three-tier system)
- Default role for new users: Operator (safest default, Admin upgrades explicitly)
- Admin can change their own PIN but cannot change their own role (prevents self-demotion lockout)

**Username Rules**
- Usernames must be unique — show error if name already exists
- No character restrictions beyond non-empty (industrial names like "Joe", "Shift-2", etc.)

**Safety Guardrails**
- Cannot delete or demote the last Admin user — show error: "At least one Admin must exist"
- Minimum user count: just 1 Admin minimum; all non-Admin users can be deleted
- If currently logged-in user is deleted by another Admin: force logout on next user action (kicked to PIN overlay). No real-time push mechanism needed.
- Factory reset path: delete users.json manually, app recreates defaults on next boot

### Claude's Discretion
- Exact card styling and layout within the Users screen
- Role badge colors and visual design
- Overlay animation/transition details
- Error message exact wording and display duration
- Whether to show PIN in edit overlay as dots with a "show" toggle or plain text

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-07 | Admin can create, delete, and modify users (assign PINs and roles) | AuthManager CRUD methods + UsersScreen + UserEditOverlay cover all three operations |
| AUTH-08 | Admin user management is accessible from a dedicated screen behind Admin PIN | UsersScreen registered as "users" tab visible only in ROLE_TABS["admin"]; no extra PIN needed — Admin session is sufficient |
</phase_requirements>

---

## Summary

Phase 7 is a self-contained CRUD feature that extends an already-built auth layer. The `AuthManager` class in `auth/auth_manager.py` already holds the JSON data structure, `_load()`, `_save()`, `user_names`, `validate_pin()`, and `get_role()`. It needs three new methods: `create_user()`, `delete_user()`, and `update_user()`. All validation logic (unique name, unique PIN, 4–6 digit length, last-admin guard) belongs in `AuthManager` — not in the UI — so that it is independently testable.

The screen itself (`UsersScreen`) follows the same Kivy patterns as `DiagnosticsScreen` (the simplest Screen stub) and `ProfilesScreen` (the most elaborate). Its KV layout uses the card pattern from `parameters.kv` for the user list, and the `ModalView` pattern from `pin_overlay.kv` for the create/edit overlay. Tab registration mirrors exactly how every other tab is registered, with one line added to `TabBar.ALL_TABS`, one entry appended to `TabBar.ROLE_TABS["admin"]`, one screen added to `base.kv`, one KV file added to `KV_FILES`, and one export added to `screens/__init__.py`.

The critical edge cases are all in `AuthManager`: preventing the last Admin deletion/demotion, rejecting duplicate PINs across all users (not just the same user), and detecting when the currently logged-in user has been deleted so the app can force-logout on next action. Pure Python coverage of these rules produces a fast, headless test suite consistent with the project's established pattern.

**Primary recommendation:** Implement in two plans — Plan 07-01: `AuthManager` CRUD + tests (pure Python, no Kivy), Plan 07-02: `UsersScreen` + `UserEditOverlay` + wiring (KV + Python, tested with headless import guards).

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Kivy `ModalView` | existing | Edit/Add user overlay | Already used in `PINOverlay`; same pattern, reuse all conventions |
| Kivy `Screen` | existing | `UsersScreen` base class | All screens in this project use `kivy.uix.screenmanager.Screen` |
| Kivy `ObjectProperty` / `StringProperty` | existing | Controller/state injection and data binding | Established project pattern |
| `json` stdlib | existing | Persist `users.json` | `AuthManager._load()` / `_save()` already uses it |
| `pytest` + `tmp_path` | existing | Headless unit tests | `test_auth_manager.py` already follows this pattern |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Kivy `TextInput` | existing | Name input and PIN input in overlay | Already in `ProfilesScreen` export popup; touchscreen-friendly |
| Kivy `ScrollView` | existing | Scrollable user card list | Used in `PINOverlay` user list and `ParametersScreen` |
| Kivy `BoxLayout` / `GridLayout` | existing | Card layout for users list | Matches patterns in `parameters.kv` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ModalView` for edit overlay | `Popup` | `Popup` adds a title bar and close button by default; `ModalView` is cleaner for custom overlays and already used by `PINOverlay` |
| Card list in `ScrollView` | `RecycleView` | `RecycleView` is appropriate for 100s of items; 3–10 users is well within `ScrollView` + `BoxLayout` territory |

**Installation:** No new dependencies. All libraries are already present.

---

## Architecture Patterns

### Recommended Project Structure

The new files follow exactly where analogous files already live:

```
src/dmccodegui/
├── auth/
│   └── auth_manager.py          # ADD: create_user(), delete_user(), update_user()
├── screens/
│   ├── users.py                 # NEW: UsersScreen + UserEditOverlay
│   └── __init__.py              # ADD: export UsersScreen
└── ui/
    ├── users.kv                 # NEW: UsersScreen + UserEditOverlay KV rules
    └── base.kv                  # ADD: UsersScreen with name: 'users'
```

`main.py` changes: add `"ui/users.kv"` to `KV_FILES`, inject `auth_manager` into `UsersScreen`.

`tab_bar.py` changes: add `("users", "Users")` to `ALL_TABS`, append `"users"` to `ROLE_TABS["admin"]`.

### Pattern 1: AuthManager CRUD Methods

**What:** Pure Python methods on `AuthManager` that validate, mutate `self._data["users"]`, and call `_save()`.
**When to use:** All user data changes must go through `AuthManager` — never mutate JSON directly in the UI.

```python
# src/dmccodegui/auth/auth_manager.py

def create_user(self, name: str, pin: str, role: str) -> Optional[str]:
    """Create a new user. Returns None on success, error string on failure."""
    if not name:
        return "Name cannot be empty"
    users = self._data.setdefault("users", {})
    if name in users:
        return f"User '{name}' already exists"
    if not (4 <= len(pin) <= 6) or not pin.isdigit():
        return "PIN must be 4-6 digits"
    if any(u["pin"] == pin for u in users.values()):
        return "PIN is already in use"
    users[name] = {"pin": pin, "role": role}
    self._save()
    return None

def delete_user(self, name: str) -> Optional[str]:
    """Delete a user. Returns None on success, error string on failure."""
    users = self._data.get("users", {})
    if name not in users:
        return f"User '{name}' not found"
    # Last admin guard
    if users[name]["role"] == "admin":
        admin_count = sum(1 for u in users.values() if u["role"] == "admin")
        if admin_count <= 1:
            return "At least one Admin must exist"
    del users[name]
    self._save()
    return None

def update_user(
    self,
    name: str,
    new_name: Optional[str] = None,
    new_pin: Optional[str] = None,
    new_role: Optional[str] = None,
    current_user: Optional[str] = None,
) -> Optional[str]:
    """Update a user's name, PIN, or role.

    current_user: the currently logged-in username (prevents self-demotion).
    Returns None on success, error string on failure.
    """
    users = self._data.get("users", {})
    if name not in users:
        return f"User '{name}' not found"
    user = users[name]

    # Role change: block self-demotion; block last-admin demotion
    if new_role is not None and new_role != user["role"]:
        if name == current_user:
            return "Cannot change your own role"
        if user["role"] == "admin" and new_role != "admin":
            admin_count = sum(1 for u in users.values() if u["role"] == "admin")
            if admin_count <= 1:
                return "At least one Admin must exist"

    # PIN validation
    if new_pin is not None:
        if not (4 <= len(new_pin) <= 6) or not new_pin.isdigit():
            return "PIN must be 4-6 digits"
        if any(uname != name and u["pin"] == new_pin for uname, u in users.items()):
            return "PIN is already in use"

    # Name change
    if new_name is not None and new_name != name:
        if not new_name:
            return "Name cannot be empty"
        if new_name in users:
            return f"User '{new_name}' already exists"
        users[new_name] = dict(user)
        del users[name]
        user = users[new_name]
        if self._data.get("last_user") == name:
            self._data["last_user"] = new_name

    if new_pin is not None:
        user["pin"] = new_pin
    if new_role is not None:
        user["role"] = new_role

    self._save()
    return None

def get_all_users(self) -> list[dict]:
    """Return list of dicts: [{'name': str, 'role': str, 'pin_masked': '••••'}]."""
    users = self._data.get("users", {})
    return [
        {"name": n, "role": u["role"], "pin_masked": "\u25cf" * len(u["pin"])}
        for n, u in users.items()
    ]
```

### Pattern 2: UsersScreen Class

**What:** `Screen` subclass with `auth_manager` `ObjectProperty`, uses `on_pre_enter` to rebuild the card list.
**When to use:** Screen is entered (tab switch); Admin edits/deletes trigger a rebuild.

```python
# src/dmccodegui/screens/users.py

from __future__ import annotations
from typing import Optional

try:
    from kivy.uix.screenmanager import Screen
    from kivy.uix.modalview import ModalView
    from kivy.properties import ObjectProperty, StringProperty
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    from kivy.uix.boxlayout import BoxLayout
    from kivy.clock import Clock

    from dmccodegui.theme_manager import theme

    class UserEditOverlay(ModalView):
        """Modal overlay for creating or editing a user."""
        error_msg = StringProperty("")
        # Filled by opener: existing name (edit) or "" (add)
        target_name = StringProperty("")

        auth_manager = ObjectProperty(None, allownone=True)
        on_saved = ObjectProperty(None, allownone=True)  # callback()
        current_user = StringProperty("")  # logged-in username for self-demotion guard

        def open_for_add(self, auth_manager, current_user: str, on_saved) -> None:
            self.auth_manager = auth_manager
            self.current_user = current_user
            self.on_saved = on_saved
            self.target_name = ""
            self.error_msg = ""
            self.open()

        def open_for_edit(self, auth_manager, name: str, current_user: str, on_saved) -> None:
            self.auth_manager = auth_manager
            self.current_user = current_user
            self.on_saved = on_saved
            self.target_name = name
            self.error_msg = ""
            self.open()

        def press_save(self) -> None:
            am = self.auth_manager
            if am is None:
                return
            name_input = self.ids.get("name_input")
            pin_input  = self.ids.get("pin_input")
            role_btn   = self.ids.get("role_selector")
            if not name_input or not pin_input or not role_btn:
                return
            name = name_input.text.strip()
            pin  = pin_input.text.strip()
            role = role_btn.text.lower()

            if self.target_name == "":
                err = am.create_user(name, pin, role)
            else:
                err = am.update_user(
                    self.target_name,
                    new_name=name if name != self.target_name else None,
                    new_pin=pin if pin else None,
                    new_role=role,
                    current_user=self.current_user,
                )
            if err:
                self.error_msg = err
                Clock.schedule_once(lambda *_: setattr(self, "error_msg", ""), 3)
            else:
                self.dismiss()
                if callable(self.on_saved):
                    self.on_saved()

    class UsersScreen(Screen):
        auth_manager = ObjectProperty(None, allownone=True)
        state = ObjectProperty(None, allownone=True)

        def on_pre_enter(self, *_) -> None:
            self._rebuild_cards()

        def _rebuild_cards(self) -> None:
            """Clear and repopulate the user card list."""
            container = self.ids.get("cards_container")
            if container is None or self.auth_manager is None:
                return
            container.clear_widgets()
            for user in self.auth_manager.get_all_users():
                self._add_user_card(container, user)

        def _add_user_card(self, container, user: dict) -> None:
            # Dynamically built card — see KV alternative below
            ...

        def on_add_press(self) -> None:
            overlay = UserEditOverlay(auto_dismiss=False, size_hint=(None, None),
                                      width="500dp", height="480dp")
            overlay.open_for_add(
                self.auth_manager,
                current_user=self.state.current_user if self.state else "",
                on_saved=self._rebuild_cards,
            )

        def on_edit_press(self, name: str) -> None:
            overlay = UserEditOverlay(auto_dismiss=False, size_hint=(None, None),
                                      width="500dp", height="480dp")
            overlay.open_for_edit(
                self.auth_manager,
                name=name,
                current_user=self.state.current_user if self.state else "",
                on_saved=self._rebuild_cards,
            )

        def on_delete_press(self, name: str) -> None:
            self._show_confirm_delete(name)

        def _show_confirm_delete(self, name: str) -> None:
            from kivy.uix.modalview import ModalView
            from kivy.uix.popup import Popup

            content = BoxLayout(orientation="vertical", padding="16dp", spacing="12dp")
            lbl = Label(
                text=f"Delete user '{name}'?",
                font_size="22sp",
                color=(1, 1, 1, 1),
                halign="center", valign="middle",
            )
            lbl.bind(size=lbl.setter("text_size"))
            content.add_widget(lbl)

            btn_row = BoxLayout(size_hint_y=None, height="56dp", spacing="12dp")
            confirm = Button(text="Delete", background_normal="",
                             background_color=(0.9, 0.2, 0.2, 1), font_size="20sp")
            cancel  = Button(text="Cancel",  background_normal="",
                             background_color=(0.35, 0.35, 0.35, 1), font_size="20sp")
            btn_row.add_widget(confirm)
            btn_row.add_widget(cancel)
            content.add_widget(btn_row)

            popup = Popup(title="", content=content,
                          size_hint=(0.45, 0.3), auto_dismiss=False,
                          separator_height=0)

            def do_delete(*_):
                popup.dismiss()
                err = self.auth_manager.delete_user(name)
                if err:
                    self._show_error(err)
                else:
                    # Force-logout if deleted user is the currently logged-in user
                    if self.state and self.state.current_user == name:
                        self.state.set_auth("", "operator")
                    self._rebuild_cards()

            confirm.bind(on_release=do_delete)
            cancel.bind(on_release=lambda *_: popup.dismiss())
            popup.open()

        def _show_error(self, msg: str) -> None:
            from kivy.uix.popup import Popup
            lbl = Label(text=msg, font_size="18sp", halign="center", valign="middle")
            lbl.bind(size=lbl.setter("text_size"))
            popup = Popup(title="Error", content=lbl, size_hint=(0.5, 0.3))
            popup.open()

except ImportError:
    pass
```

### Pattern 3: Role Selector Widget in KV

**What:** Three toggle-style `Button` widgets grouped horizontally, one per role. Active role has accent background.
**When to use:** Inside `UserEditOverlay` for selecting Operator/Setup/Admin.

```kv
# Inside <UserEditOverlay> KV rule — role selector row
BoxLayout:
    id: role_selector_row
    orientation: 'horizontal'
    size_hint_y: None
    height: '52dp'
    spacing: '4dp'

    Button:
        id: role_operator
        text: 'Operator'
        font_size: '18sp'
        background_normal: ''
        background_color: 0.133, 0.773, 0.369, 0.9  # active if selected
        on_release: root._select_role('operator')

    Button:
        id: role_setup
        text: 'Setup'
        font_size: '18sp'
        background_normal: ''
        background_color: theme.bg_row
        on_release: root._select_role('setup')

    Button:
        id: role_admin
        text: 'Admin'
        font_size: '18sp'
        background_normal: ''
        background_color: theme.bg_row
        on_release: root._select_role('admin')
```

The `UserEditOverlay._select_role(role)` method updates button backgrounds and stores `self._selected_role`.

### Pattern 4: Tab Registration

**What:** Two-line change to `tab_bar.py`; three-line change to `base.kv`; one KV file added to `main.py`.

```python
# tab_bar.py — ADD "users" tab

ALL_TABS = [
    ("run", "Run"),
    ("axes_setup", "Axes Setup"),
    ("parameters", "Parameters"),
    ("profiles", "Profiles"),
    ("diagnostics", "Diagnostics"),
    ("users", "Users"),              # NEW
]

ROLE_TABS = {
    "operator": ["run"],
    "setup": ["run", "axes_setup", "parameters", "profiles"],
    "admin": ["run", "axes_setup", "parameters", "profiles", "diagnostics", "users"],  # "users" appended
}
```

```kv
# base.kv — ADD inside ScreenManager block
UsersScreen:
    name: 'users'
```

```python
# main.py KV_FILES — ADD before base.kv
"ui/users.kv",   # UsersScreen + UserEditOverlay
```

`UsersScreen` needs `auth_manager` injected in `build()`:
```python
# main.py build() — ADD after existing injection loop
users_screen = next((s for s in sm.screens if getattr(s, 'name', '') == 'users'), None)
if users_screen and hasattr(users_screen, 'auth_manager'):
    users_screen.auth_manager = self.auth_manager
```

### Anti-Patterns to Avoid

- **Mutating `users.json` directly in the UI layer:** All writes must go through `AuthManager` methods so validation always runs. The UI calls `auth_manager.create_user()` etc., never `json.dump()`.
- **Real-time push for deleted-user logout:** The locked decision is force-logout on next user action. Do not add Kivy event bindings or `Clock` polling to detect deletion in real time.
- **Blocking the Kivy main thread for file I/O:** `AuthManager._save()` is a synchronous JSON write of a tiny file (< 1 KB). `jobs.submit()` is not needed here — the write is faster than a single frame. This matches how the existing `AuthManager._save()` already works.
- **Duplicating validation in KV:** PIN length and uniqueness checks belong in `AuthManager`, not in KV `on_text` handlers. Keep KV as presentation only.
- **Forgetting `try/except ImportError` guard:** `UsersScreen` and `UserEditOverlay` are Kivy classes. Wrap in the same `try/except ImportError: pass` pattern used in `profiles.py` so headless unit tests can import the module.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Confirmation dialog | Custom ModalView subclass | Kivy `Popup` | `Popup` covers this case — used in `ProfilesScreen` for overwrite confirm and error display |
| Overlay dismissal on outside tap | Custom touch handler | `auto_dismiss=False` on `ModalView` | Prevents accidental dismissal on touchscreen — already used by `PINOverlay` |
| Scrollable card list | Custom layout manager | `ScrollView` + `BoxLayout` (size_hint_y=None, height=minimum_height) | Established pattern from `PINOverlay` user list and `ParametersScreen` |
| Role persistence across app restart | Custom caching | `AuthManager._data` loaded once on init, always in sync | JSON round-trip on every `_save()` is the chosen approach |

**Key insight:** Every UI pattern needed by this phase already exists in the codebase. This phase is composition, not invention.

---

## Common Pitfalls

### Pitfall 1: Tab Bar Test Out of Sync

**What goes wrong:** `test_tab_bar.py` hard-codes the expected list for admin as `["run", "axes_setup", "parameters", "profiles", "diagnostics"]`. After adding `"users"` to `ROLE_TABS["admin"]`, the test will fail.
**Why it happens:** The test mirrors `ROLE_TABS` locally rather than importing `TabBar` (to avoid Kivy init). The mirror is stale.
**How to avoid:** Update `test_tab_bar.py` `_tabs_for_role` mirror AND the `test_admin_tabs` assertion in the same plan that modifies `tab_bar.py`.
**Warning signs:** `test_admin_tabs` failure after tab_bar.py change.

### Pitfall 2: `auth_manager` Injection Missing for UsersScreen

**What goes wrong:** `main.py`'s existing injection loop only injects `controller` and `state`. `UsersScreen` needs `auth_manager` too. Forgetting to add explicit injection leaves `auth_manager = None` at runtime, causing silent no-ops when Admin tries to view the user list.
**Why it happens:** The loop `for screen in sm.screens: if hasattr(screen, 'controller') and hasattr(screen, 'state')` only handles `controller`/`state`.
**How to avoid:** Add explicit `UsersScreen` lookup after the loop (same pattern used for `setup` screen callbacks).
**Warning signs:** Users screen shows empty list with no error.

### Pitfall 3: Last-Admin Guard Race on Name Change

**What goes wrong:** `update_user()` with `new_name` deletes the old key and creates a new one. If the admin-count guard runs before the rename, the deleted old key temporarily makes the admin count appear lower than it is.
**Why it happens:** Guard logic reads `users` dict mid-mutation.
**How to avoid:** Check the guard BEFORE any mutation. In the code example above, the guard uses the current `user["role"]` before any delete/insert.
**Warning signs:** Error "At least one Admin must exist" when renaming the only Admin.

### Pitfall 4: Duplicate PIN Check Includes Self

**What goes wrong:** When editing an existing user's PIN to the same value (e.g. Admin confirming unchanged PIN `"0000"`), the duplicate-PIN check sees the user's own PIN in the `users` dict and raises "PIN is already in use".
**Why it happens:** `any(u["pin"] == new_pin for u in users.values())` includes the user being edited.
**How to avoid:** Exclude the current user: `any(uname != name and u["pin"] == new_pin for uname, u in users.items())`. This is already shown in the code example above.
**Warning signs:** Cannot save an unchanged PIN during edit.

### Pitfall 5: KV Widget `ids` Access Before `on_kv_post`

**What goes wrong:** Accessing `self.ids.name_input` in `__init__` raises `KeyError` because KV ids are not populated until after `on_kv_post`.
**Why it happens:** Kivy's two-phase initialization — Python `__init__` runs before KV rules are applied.
**How to avoid:** Only access `self.ids` inside `on_kv_post`, `on_pre_enter`, or event callbacks — never in `__init__`. The `pin_overlay.py` uses `on_kv_post` for `self._pin_digits = ""` initialization; follow the same pattern.
**Warning signs:** `KeyError: 'name_input'` or `AttributeError` on screen entry.

---

## Code Examples

### AuthManager: get_all_users() for Card Population

```python
# Source: direct codebase analysis of auth_manager.py structure
def get_all_users(self) -> list[dict]:
    """Return display-safe user records (no raw PIN, masked dots shown)."""
    users = self._data.get("users", {})
    return [
        {
            "name": name,
            "role": user["role"],
            "pin_masked": "\u25cf" * len(user["pin"]),
        }
        for name, user in users.items()
    ]
```

### Headless Test Pattern for AuthManager CRUD

```python
# Source: tests/test_auth_manager.py fixture pattern
def test_create_user(tmp_users_path):
    am = AuthManager(str(tmp_users_path))
    err = am.create_user("Alice", "1111", "operator")
    assert err is None
    assert "Alice" in am.user_names
    assert am.get_role("Alice") == "operator"

def test_create_user_duplicate_name(tmp_users_path):
    am = AuthManager(str(tmp_users_path))
    err = am.create_user("Admin", "9999", "operator")  # "Admin" already exists
    assert err is not None

def test_create_user_duplicate_pin(tmp_users_path):
    am = AuthManager(str(tmp_users_path))
    err = am.create_user("Alice", "0000", "operator")  # "0000" is Admin's PIN
    assert err is not None

def test_delete_last_admin_blocked(tmp_users_path):
    am = AuthManager(str(tmp_users_path))
    # Remove non-admin users first
    am.delete_user("Operator")
    am.delete_user("Setup")
    err = am.delete_user("Admin")
    assert err is not None
    assert "Admin" in am.user_names  # not deleted

def test_update_self_role_blocked(tmp_users_path):
    am = AuthManager(str(tmp_users_path))
    err = am.update_user("Admin", new_role="operator", current_user="Admin")
    assert err is not None
```

### Force-Logout Pattern on Delete

```python
# Source: UsersScreen._confirm_delete pattern
def _do_delete(self, name: str) -> None:
    err = self.auth_manager.delete_user(name)
    if err:
        self._show_error(err)
        return
    # Force logout if the deleted user is currently logged in
    if self.state and self.state.current_user == name:
        self.state.set_auth("", "operator")
        # App's PIN overlay will appear on next restricted action
    self._rebuild_cards()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hard-coded DEFAULT_USERS only | DEFAULT_USERS as fallback + CRUD via AuthManager | Phase 7 | Admin can manage users at runtime without file edits |
| TabBar admin = 5 tabs | TabBar admin = 6 tabs (+ Users) | Phase 7 | Admin sees Users tab; no change for Operator or Setup |

**Deprecated/outdated:** Nothing is deprecated. Phase 7 is additive only.

---

## Open Questions

1. **`auth_manager` injection point in `main.py`**
   - What we know: The existing injection loop handles `controller` and `state`. `UsersScreen` needs `auth_manager` too.
   - What's unclear: Whether to add `auth_manager` to the generic loop or handle `UsersScreen` explicitly by name.
   - Recommendation: Handle explicitly by name (same pattern as `setup` screen callback wiring) to avoid unintended injection into other screens.

2. **Role selector initial state in edit overlay**
   - What we know: Edit overlay should pre-select the user's current role.
   - What's unclear: Whether to use three toggle-style buttons (simpler) or a `Spinner` widget.
   - Recommendation: Three buttons — consistent with the touchscreen-first design; no need for `Spinner`. Pre-select by setting one button's `background_color` to accent on `open_for_edit`.

3. **PIN display in edit overlay**
   - What we know: CONTEXT.md marks "show toggle vs plain text" as Claude's discretion.
   - Recommendation: Show pre-filled masked dots; Admin types a new PIN to replace. Do not pre-fill with the actual PIN string. A "show/hide" toggle is optional polish — default to masked for safety.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pytest.ini` or `pyproject.toml` (project root) |
| Quick run command | `pytest tests/test_auth_manager.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-07 | `create_user()` validates and persists new user | unit | `pytest tests/test_auth_manager.py::test_create_user -x` | Wave 0 |
| AUTH-07 | `create_user()` rejects duplicate name | unit | `pytest tests/test_auth_manager.py::test_create_user_duplicate_name -x` | Wave 0 |
| AUTH-07 | `create_user()` rejects duplicate PIN | unit | `pytest tests/test_auth_manager.py::test_create_user_duplicate_pin -x` | Wave 0 |
| AUTH-07 | `create_user()` rejects invalid PIN length | unit | `pytest tests/test_auth_manager.py::test_create_user_invalid_pin -x` | Wave 0 |
| AUTH-07 | `delete_user()` removes user and persists | unit | `pytest tests/test_auth_manager.py::test_delete_user -x` | Wave 0 |
| AUTH-07 | `delete_user()` blocks last Admin deletion | unit | `pytest tests/test_auth_manager.py::test_delete_last_admin_blocked -x` | Wave 0 |
| AUTH-07 | `update_user()` changes PIN with uniqueness check | unit | `pytest tests/test_auth_manager.py::test_update_user_pin -x` | Wave 0 |
| AUTH-07 | `update_user()` blocks self-demotion | unit | `pytest tests/test_auth_manager.py::test_update_self_role_blocked -x` | Wave 0 |
| AUTH-07 | `update_user()` blocks last-admin demotion | unit | `pytest tests/test_auth_manager.py::test_update_last_admin_demotion_blocked -x` | Wave 0 |
| AUTH-08 | Admin role sees "users" tab; Operator/Setup do not | unit | `pytest tests/test_tab_bar.py -x` | Exists (needs update) |
| AUTH-08 | Admin users tab correctly includes "users" | unit | `pytest tests/test_tab_bar.py::TestTabsForRole::test_admin_tabs -x` | Exists (needs update) |

### Sampling Rate

- **Per task commit:** `pytest tests/test_auth_manager.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_auth_manager.py` — needs new test functions for CRUD methods (AUTH-07: create, delete, update, validation, last-admin guard, self-demotion guard). File exists but only covers read-only operations from Phase 1.
- [ ] `tests/test_tab_bar.py` — needs `_tabs_for_role` mirror updated to include `"users"` in admin list, and `test_admin_tabs` assertion updated (AUTH-08). File exists.

---

## Sources

### Primary (HIGH confidence)

- Direct codebase reading — `auth/auth_manager.py`, `screens/pin_overlay.py`, `screens/tab_bar.py`, `screens/__init__.py`, `main.py`, `ui/pin_overlay.kv`, `ui/base.kv`, `ui/parameters.kv`, `screens/profiles.py`
- Direct codebase reading — `tests/test_auth_manager.py`, `tests/test_tab_bar.py`, `tests/conftest.py`
- `.planning/phases/07-admin-and-user-management/07-CONTEXT.md` — all locked decisions

### Secondary (MEDIUM confidence)

- Kivy ModalView/Popup patterns — inferred from existing codebase usage (PINOverlay, ProfilesScreen popups)
- Kivy TextInput touchscreen pattern — inferred from existing overlay and profile export popup patterns

### Tertiary (LOW confidence)

- None — all findings grounded in direct code inspection of the live codebase.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; no new dependencies
- Architecture patterns: HIGH — every pattern verified directly in existing code
- Pitfalls: HIGH — each pitfall identified from concrete code paths (test_tab_bar.py mirror, injection loop scope, rename mutation order, self-PIN check, KV ids timing)
- Validation architecture: HIGH — test framework, existing patterns, and specific test names all grounded in actual test files

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable Kivy codebase; no external deps changing)
