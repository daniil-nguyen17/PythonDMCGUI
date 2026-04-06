# Phase 1: Auth and Navigation - Research

**Researched:** 2026-04-04
**Domain:** Kivy 2.3.1 — ModalView overlays, PIN entry, role-based tab navigation, inactivity timeout, RootLayout restructure
**Confidence:** HIGH

## Summary

This phase rebuilds the application shell: replacing the current `SomeMenu_ActionBar` + `Spinner` navigation with a persistent status bar and role-aware tab bar, and adding a fullscreen PIN overlay system for login and role elevation. All decisions are locked in CONTEXT.md — this research validates Kivy 2.3.1 capabilities and identifies the exact implementation patterns needed.

The largest structural change is `base.kv` and `main.py`. The current `RootLayout` is a vertical `BoxLayout` with `SomeMenu_ActionBar` → ticker bar → `ScreenManager`. The new layout stacks: `StatusBar` (48dp) → `TabBar` (48dp) → `ScreenManager` (fills remaining space), with a `ModalView`-based PIN overlay that sits above everything. The seven old screens are deleted; four empty placeholder screens replace them.

The `MachineState` dataclass must gain auth fields (`current_user`, `current_role`, `setup_unlocked`). An `AuthManager` class (plain Python, no external deps) handles PIN validation against `users.json`. The inactivity auto-lock is driven by `Window.bind(on_touch_down=...)` resetting a `Clock.schedule_once` event — a standard Kivy pattern confirmed by official docs.

**Primary recommendation:** Use `ModalView(auto_dismiss=False, size_hint=(1,1))` for the PIN overlay (blocks all interaction underneath), plain `BoxLayout` tab bar with `ToggleButton` or custom `Button` items driven by a `StringProperty` on the app/state, and `Window.bind(on_touch_down)` for the 30-minute idle timer.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**PIN Entry UI**
- Fullscreen dark overlay covers entire app on startup — nothing accessible until PIN entered
- Phone-style 3x4 numpad (1-9 top, 0 bottom center, backspace and enter)
- Large 44dp+ numpad buttons for touchscreen
- PIN digits shown as dots (masked)
- Pre-select last logged-in user on startup (name shown at top of overlay)
- "Switch User" available to pick a different name from a list
- Tap user name in status bar to open PIN overlay for switching users
- Reuse same fullscreen PIN overlay for Setup role unlock on restricted tabs

**User Storage**
- Plain JSON file (users.json) alongside the app
- PINs stored in plain text (no encryption)
- When users.json doesn't exist, create three default users: Admin (0000), Operator (1234), Setup (5678)

**PIN Feedback & Errors**
- Wrong PIN: shake animation + clear dots + "Invalid PIN" message for 2 seconds
- No lockout — operator can retry immediately
- Numpad button tap: color change highlight (standard Kivy press behavior), no sound

**Role Switching Flow**
- Setup user taps restricted tab → same PIN overlay → enter Setup PIN → tab unlocks
- Silent auto-lock after 30 minutes of no touch input
- On auto-lock: stay on current screen, restrict to Operator view; if on restricted tab, switch to Run tab
- No warning before auto-lock

**Tab Bar & Navigation**
- Tab bar at TOP, below status bar, 48dp height
- Icon + text style tabs (icon above label)
- Four tabs: Run, Axes Setup, Parameters, Diagnostics
- Operator: Run only; Setup: Run + Axes Setup + Parameters; Admin: all four
- Active tab: accent color highlight
- Tab bar height: 48dp

**Top Status Bar**
- 48dp persistent bar above tab bar
- Layout: Connection status (left) | User name + role badge (left-center) | Banner ticker (center/fill) | E-STOP (right)
- E-STOP: red, top-right, always visible
- Connection: green dot + machine name when connected, red when disconnected
- Tap user/role area → PIN overlay for user switch

**Startup Flow**
- Boot → auto-connect to DMC_ADDRESS or first discovered controller
- Auto-connect success: skip connection screen, go straight to PIN overlay
- Auto-connect fail: show connection screen
- After connection + PIN login: show tab UI
- Disconnect mid-session → return to connection screen

**Existing Screens**
- Remove all 7 old screens (Setup/connection screen preserved as pre-login flow)
- Create empty placeholder screens: Run, Axes Setup, Parameters, Diagnostics
- Old screens removed: Rest, Start, AxisD, Params, Buttons & Switches, Serration Knife

**Theme & Touch**
- Dark theme (existing BG_DARK navy palette from theme.kv)
- Axis accent colors: A=orange, B=purple, C=cyan, D=yellow
- All interactive elements 44dp+ minimum
- No animated transitions — instant screen switches

### Claude's Discretion
- Exact icon choices for tab buttons
- PIN overlay visual design details (background opacity, card styling)
- Banner ticker scroll behavior and timing
- Connection screen layout within the existing pattern
- Exact accent color shade for active tab indicator

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-01 | User can log in by entering a 4-6 digit PIN on a touchscreen numeric keypad overlay | ModalView(auto_dismiss=False) + GridLayout 3x4 numpad; PIN stored as StringProperty, displayed as dots |
| AUTH-02 | App remembers last logged-in user and pre-selects them on startup | users.json stores `last_user` key; AuthManager reads on init; pre-fills username Label in overlay |
| AUTH-03 | Three user roles: Operator, Setup, Admin — each with different access levels | AuthManager returns role string from users.json; MachineState gains `current_role` field |
| AUTH-04 | Operator can only access RUN page and view (not edit) parameters | Tab bar visibility driven by `current_role`; only Run tab shown for Operator |
| AUTH-05 | Setup user can unlock via PIN overlay to access axes setup, parameters | Tapping a restricted tab triggers same PIN overlay; on success, `setup_unlocked=True` in state |
| AUTH-06 | Setup session auto-locks after configurable inactivity timeout, returning to Operator view | Window.bind(on_touch_down) resets Clock.schedule_once(1800s); on fire: set setup_unlocked=False, notify |
| NAV-01 | Persistent tab bar (Run, Axes Setup, Parameters, Diagnostics) replacing ActionBar+Spinner | New TabBar widget in base.kv; BoxLayout of Button/ToggleButton; replaces SomeMenu_ActionBar |
| NAV-02 | E-STOP button accessible from every screen via persistent top bar | E-STOP Button in StatusBar widget at top-right; wired to existing app.e_stop() |
| NAV-03 | Tab visibility is role-aware | TabBar buttons hidden/shown based on current_role StringProperty on app or state |
| NAV-04 | Connection status always visible in top bar | StatusBar left section: color dot + machine name; bound to state.connected and state.connected_address |
| NAV-05 | Current user name and role always visible in top bar with switch-user button | StatusBar left-center: Label with user + role; on_release opens PIN overlay |
| UI-01 | Consistent dark theme across all screens (BG_DARK navy palette) | Reuse existing theme.kv palette; all new KV uses same rgba constants |
| UI-02 | Axis accent color coding maintained: A=orange, B=purple, C=cyan, D=yellow | Existing colors preserved; new UI elements use same palette refs |
| UI-03 | All interactive elements meet minimum 44dp touch target | All Button/ToggleButton in new UI: size_hint_y None, height 44dp+ enforced |
| UI-04 | No animated transitions between screens | ScreenManager transition: NoTransition() set in base.kv or main.py |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Kivy | 2.3.1 (installed) | UI framework, ScreenManager, ModalView, Animation, Clock | Already in project; only UI framework in use |
| Python stdlib `json` | stdlib | Read/write users.json | No extra dep; simple flat file per project scope decision |
| Python stdlib `os` / `pathlib` | stdlib | Locate users.json alongside app | Already used in main.py for resource paths |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `kivy.uix.modalview.ModalView` | 2.3.1 | Fullscreen PIN overlay | Single overlay instance, opened/dismissed programmatically |
| `kivy.animation.Animation` | 2.3.1 | Shake animation on wrong PIN | Chain with `+` operator for left-right-center translation |
| `kivy.clock.Clock` | 2.3.1 | 30-minute inactivity timer | `schedule_once` + `cancel()` pattern on Window touch events |
| `kivy.core.window.Window` | 2.3.1 | Global touch intercept for idle timer | `Window.bind(on_touch_down=...)` |
| `kivy.uix.screenmanager.NoTransition` | 2.3.1 | Instant screen switches (UI-04) | Set as ScreenManager's transition in base.kv |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ModalView | FloatLayout overlay child | ModalView blocks underlying touches automatically; FloatLayout requires manual touch filtering |
| Plain JSON file | SQLite / shelve | JSON is transparent, no deps, fits stated project scope; SQLite is overkill for <10 users |
| Window.bind inactivity | Custom touch-cascade override | Window.bind is simpler and doesn't interfere with existing widget touch handling |

**Installation:** No new packages needed. All required libraries are part of Kivy 2.3.1 which is already installed.

---

## Architecture Patterns

### Recommended Project Structure Changes

```
src/dmccodegui/
├── auth/
│   ├── __init__.py
│   ├── auth_manager.py      # AuthManager: load/save users.json, validate PIN, get role
│   └── users.json           # Created at runtime (default users on first boot)
├── screens/
│   ├── __init__.py          # Updated imports (remove old screens, add new placeholders)
│   ├── setup.py             # KEEP — connection/pre-login screen (unchanged)
│   ├── run.py               # NEW — empty placeholder
│   ├── axes_setup.py        # NEW — empty placeholder
│   ├── parameters.py        # NEW — empty placeholder
│   └── diagnostics.py       # NEW — empty placeholder
│   # OLD FILES DELETED: rest.py, start.py, axisDSetup.py, parameters_setup.py,
│   #                    buttons_switches.py, serration_knife.py, axis_angles.py, arrays.py
├── ui/
│   ├── theme.kv             # UNCHANGED — reuse existing palette
│   ├── setup.kv             # KEEP — connection screen (unchanged)
│   ├── pin_overlay.kv       # NEW — PINOverlay ModalView widget rule
│   ├── status_bar.kv        # NEW — StatusBar widget rule
│   ├── tab_bar.kv           # NEW — TabBar widget rule
│   ├── base.kv              # REWRITTEN — new RootLayout structure
│   # OLD KV FILES DELETED: rest.kv, start.kv, buttons_switches.kv,
│   #                       parameters_setup.kv, axisDSetup.kv, serration_knife.kv,
│   #                       axis_angles.kv (arrays.kv, edges.kv can be removed too)
├── app_state.py             # EXTENDED — add current_user, current_role, setup_unlocked
└── main.py                  # UPDATED — new KV_FILES list, screen injection, startup flow
```

### Pattern 1: AuthManager

**What:** Pure Python class (no Kivy) managing users.json — load, save, validate PIN, return role.
**When to use:** Called from PINOverlay screen on numpad submit; called from DMCApp.build() to bootstrap defaults.

```python
# src/dmccodegui/auth/auth_manager.py
import json
import os
from typing import Optional

DEFAULT_USERS = {
    "Admin":    {"pin": "0000", "role": "admin"},
    "Operator": {"pin": "1234", "role": "operator"},
    "Setup":    {"pin": "5678", "role": "setup"},
}

class AuthManager:
    def __init__(self, users_path: str):
        self.users_path = users_path
        self._users: dict = {}
        self._last_user: str = ""
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.users_path):
            with open(self.users_path, "r") as f:
                data = json.load(f)
            self._users = data.get("users", {})
            self._last_user = data.get("last_user", "")
        else:
            self._users = dict(DEFAULT_USERS)
            self._last_user = "Operator"
            self._save()

    def _save(self) -> None:
        with open(self.users_path, "w") as f:
            json.dump({"users": self._users, "last_user": self._last_user}, f, indent=2)

    @property
    def user_names(self) -> list[str]:
        return list(self._users.keys())

    @property
    def last_user(self) -> str:
        return self._last_user

    def validate_pin(self, username: str, pin: str) -> Optional[str]:
        """Returns role string on success, None on failure."""
        user = self._users.get(username)
        if user and user.get("pin") == pin:
            self._last_user = username
            self._save()
            return user["role"]
        return None

    def get_role(self, username: str) -> Optional[str]:
        user = self._users.get(username)
        return user["role"] if user else None
```

### Pattern 2: MachineState Auth Extension

**What:** Add auth fields to the existing `MachineState` dataclass.
**When to use:** Drives tab bar visibility, status bar display, and access control checks.

```python
# In app_state.py — add to MachineState dataclass fields:
current_user: str = ""
current_role: str = ""      # "operator" | "setup" | "admin" | ""
setup_unlocked: bool = False

# Add convenience method:
def set_auth(self, user: str, role: str) -> None:
    self.current_user = user
    self.current_role = role
    self.setup_unlocked = (role in ("setup", "admin"))
    self.notify()

def lock_setup(self) -> None:
    """Called by auto-lock timer and explicit logout."""
    if self.current_role == "setup":
        self.setup_unlocked = False
        self.notify()
```

### Pattern 3: PINOverlay (ModalView)

**What:** Fullscreen ModalView with `auto_dismiss=False`. Contains user selector, masked PIN display, 3x4 numpad.
**When to use:** On app startup (blocks access), on restricted tab tap (elevates to Setup), on status bar user tap (switch user).

```python
# src/dmccodegui/screens/pin_overlay.py  (or as a reusable widget)
from kivy.uix.modalview import ModalView
from kivy.properties import StringProperty, ObjectProperty
from kivy.animation import Animation
from kivy.clock import Clock

class PINOverlay(ModalView):
    """Fullscreen PIN entry overlay. auto_dismiss=False set in KV rule."""
    username = StringProperty("")
    pin_dots = StringProperty("")   # "● ● ●" masking
    error_msg = StringProperty("")
    mode = StringProperty("login")  # "login" | "switch" | "unlock"

    auth_manager = ObjectProperty(None)
    on_success = ObjectProperty(None)   # callback(username, role)

    def _pin_value(self) -> str:
        # count dots as PIN length — actual digits stored internally
        return self._pin_digits

    def on_kv_post(self, *_):
        self._pin_digits = ""

    def press_digit(self, digit: str) -> None:
        if len(self._pin_digits) >= 6:
            return
        self._pin_digits += digit
        self.pin_dots = "●" * len(self._pin_digits)
        self.error_msg = ""

    def press_backspace(self) -> None:
        self._pin_digits = self._pin_digits[:-1]
        self.pin_dots = "●" * len(self._pin_digits)

    def press_enter(self) -> None:
        role = self.auth_manager.validate_pin(self.username, self._pin_digits)
        if role is not None:
            self.dismiss()
            if self.on_success:
                self.on_success(self.username, role)
        else:
            self._show_error()

    def _show_error(self) -> None:
        self.error_msg = "Invalid PIN"
        self._pin_digits = ""
        self.pin_dots = ""
        # Shake the numpad card widget
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
```

**KV rule key points:**
```kv
# ui/pin_overlay.kv
<PINOverlay>:
    auto_dismiss: False
    size_hint: 1, 1
    background_color: 0, 0, 0, 0      # transparent — overlay_color handles dimming
    overlay_color: 0.031, 0.047, 0.071, 0.95   # near-opaque dark cover
    # CardFrame (id: pin_card) centered, ~400dp wide
    # Username label at top
    # Pin dots display row
    # Error message label
    # 3x4 numpad GridLayout: cols 3, rows 4
    #   Row 1: 1 2 3
    #   Row 2: 4 5 6
    #   Row 3: 7 8 9
    #   Row 4: backspace 0 enter
    # "Switch User" button below numpad
```

### Pattern 4: Inactivity Auto-Lock

**What:** `Window.bind(on_touch_down=...)` resets a `Clock.schedule_once` timer. When it fires, lock Setup role.
**When to use:** Active from app startup, fires after 30 minutes of no touch activity.

```python
# In DMCApp (main.py):
from kivy.core.window import Window
from kivy.clock import Clock

IDLE_TIMEOUT = 30 * 60   # 30 minutes in seconds

class DMCApp(App):
    def build(self):
        ...
        self._idle_event = None
        Window.bind(on_touch_down=self._reset_idle_timer)
        self._reset_idle_timer()   # start timer immediately
        return root

    def _reset_idle_timer(self, *args) -> None:
        if self._idle_event:
            self._idle_event.cancel()
        self._idle_event = Clock.schedule_once(self._on_idle_timeout, IDLE_TIMEOUT)

    def _on_idle_timeout(self, dt) -> None:
        """Auto-lock: drop Setup back to Operator view."""
        if self.state.current_role == "setup" and self.state.setup_unlocked:
            self.state.lock_setup()
            # If currently on a restricted tab, navigate to Run
            try:
                sm = self.root.ids.sm
                if sm.current in ("axes_setup", "parameters"):
                    sm.current = "run"
            except Exception:
                pass
```

### Pattern 5: New RootLayout (base.kv)

**What:** Vertical BoxLayout replacing the existing RootLayout. New structure: StatusBar → TabBar → ScreenManager.
**When to use:** This is the entire app shell.

```kv
# ui/base.kv (complete rewrite)
<RootLayout@BoxLayout>:
    orientation: 'vertical'
    canvas.before:
        Color:
            rgba: 0.031, 0.047, 0.071, 1
        Rectangle:
            pos: self.pos
            size: self.size

    StatusBar:
        id: status_bar
        size_hint_y: None
        height: '48dp'

    TabBar:
        id: tab_bar
        size_hint_y: None
        height: '48dp'

    ScreenManager:
        id: sm
        transition: NoTransition()
        SetupScreen:
            name: 'setup'
        RunScreen:
            name: 'run'
        AxesSetupScreen:
            name: 'axes_setup'
        ParametersScreen:
            name: 'parameters'
        DiagnosticsScreen:
            name: 'diagnostics'
```

### Pattern 6: Role-Aware Tab Bar

**What:** TabBar hides/shows buttons based on `app.state.current_role`. Kivy `opacity` and `disabled` used together because hiding a widget still occupies space — use `size_hint_x: 0` / `width: 0` trick or rebuild visible buttons on role change.
**When to use:** Rebuilding (clear_widgets + add_widget) is simpler and more reliable than binding size_hint to role strings in KV.

```python
# In TabBar widget (Python class):
class TabBar(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self._app = None

    def set_role(self, role: str, current_tab: str) -> None:
        """Rebuild visible tabs based on role."""
        self.clear_widgets()
        tabs = self._tabs_for_role(role)
        for name, label, icon in tabs:
            btn = ToggleButton(
                text=label,
                group="tabs",
                state="down" if name == current_tab else "normal",
            )
            btn.bind(on_release=lambda b, n=name: self._switch_tab(n))
            self.add_widget(btn)

    def _tabs_for_role(self, role: str) -> list:
        all_tabs = [
            ("run",        "Run",        "run-icon"),
            ("axes_setup", "Axes Setup", "axes-icon"),
            ("parameters", "Parameters", "params-icon"),
            ("diagnostics","Diagnostics","diag-icon"),
        ]
        if role == "operator":
            return all_tabs[:1]
        elif role == "setup":
            return all_tabs[:3]
        else:  # admin
            return all_tabs
```

**Important:** Setup-role tabs (Axes Setup, Parameters) are visible after `setup_unlocked=True`. If `setup_unlocked=False` but role is `setup`, tapping them shows the PIN overlay to elevate. This means tabs are visible (role filter = setup) but tapping triggers unlock check, not direct navigation.

### Pattern 7: KV File Load Order (main.py)

The current `KV_FILES` list must be replaced. New order:

```python
KV_FILES = [
    "ui/theme.kv",       # base styles — always first
    "ui/pin_overlay.kv", # PINOverlay widget
    "ui/status_bar.kv",  # StatusBar widget
    "ui/tab_bar.kv",     # TabBar widget
    "ui/setup.kv",       # SetupScreen (connection screen — unchanged)
    "ui/run.kv",         # RunScreen placeholder
    "ui/axes_setup.kv",  # AxesSetupScreen placeholder
    "ui/parameters.kv",  # ParametersScreen placeholder
    "ui/diagnostics.kv", # DiagnosticsScreen placeholder
    "ui/base.kv",        # RootLayout — always last
]
```

### Anti-Patterns to Avoid

- **Hiding tabs with `opacity: 0`:** Invisible widgets still occupy horizontal space in a BoxLayout. Use `set_role()` to rebuild tabs with `clear_widgets()` + `add_widget()` instead.
- **Opening ModalView during `on_kv_post`:** Kivy may not have finished building the widget tree. Defer with `Clock.schedule_once(lambda *_: self._show_pin_overlay(), 0)` (0 = next frame).
- **Storing PIN digits in a KV StringProperty:** StringProperty changes trigger KV redraws. Store raw digits in a plain Python `str` attribute; only push the masked dots string to KV.
- **Calling `Window.bind` before `build()` returns:** Window events are reliable only after the root widget is returned from `build()`. Bind inside `build()` after constructing `root`.
- **Animating `x` position of a widget whose parent uses `pos_hint`:** `pos_hint` overrides `x`. Either remove `pos_hint` before animating, or animate a parent container. For the PIN card, use a plain `AnchorLayout` parent without `pos_hint` set on the card.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fullscreen blocking overlay | Custom FloatLayout child that consumes touches | `ModalView(auto_dismiss=False)` | ModalView handles touch blocking, z-ordering, fade-in/out automatically |
| Shake animation | Manual Clock.schedule_once chain with setattr | `Animation(x=...) + Animation(x=...)` chain | Kivy Animation handles timing, interpolation, and cleanup |
| Inactivity timeout | Polling loop in a background thread | `Clock.schedule_once` + `Window.bind(on_touch_down)` | No thread overhead, accurate, integrates with Kivy event loop |
| Instant screen transitions | Subclassing TransitionBase | `NoTransition()` | Built-in, zero lines of custom code |
| Role filtering tab display | `opacity`/`disabled` binding in KV | Rebuild tab list with `clear_widgets()` on role change | No widget-space leakage, simpler KV |

**Key insight:** Kivy has production-quality answers for all the tricky parts of this phase (overlays, animation, timers). None of the "hard" problems require custom solutions.

---

## Common Pitfalls

### Pitfall 1: ModalView background_color vs overlay_color
**What goes wrong:** Setting `background_color` to a dark semi-transparent RGBA makes the *card* dark, not the overlay. Result: the ModalView card is a dark rectangle but the window behind it is NOT dimmed.
**Why it happens:** In Kivy 2.0+, `background_color` is a multiplier on the widget's background texture, not the overlay dim. The overlay dim is `overlay_color`.
**How to avoid:** Set `overlay_color: 0.031, 0.047, 0.071, 0.95` on the ModalView for the dark cover, set `background_color: 0,0,0,0` (transparent), and put the card UI inside as a child widget with its own canvas.
**Warning signs:** Background is dark but the content behind ModalView is still visible through the card edges.

### Pitfall 2: Animating x on a pos_hint-constrained widget
**What goes wrong:** Shake animation does nothing (card snaps back instantly) because the parent layout keeps overriding `x` via `pos_hint`.
**Why it happens:** Layout passes override `x`/`y` after every resize or layout cycle. `pos_hint` wins over animated `x`.
**How to avoid:** The PIN card inside ModalView should be a direct child with `size_hint: None, None` and explicit `pos_hint: {'center_x': 0.5, 'center_y': 0.5}` removed, replaced by `AnchorLayout` wrapping. Animate the card, not the anchor.
**Warning signs:** Animation callback fires but widget doesn't visibly move.

### Pitfall 3: Opening ModalView too early (during kv_post or build)
**What goes wrong:** App crashes or overlay appears before screen manager is rendered.
**Why it happens:** Kivy widget tree construction is not complete during `on_kv_post` or early in `build()`.
**How to avoid:** Always defer first PIN overlay open: `Clock.schedule_once(lambda *_: overlay.open(), 0)` inside `build()` after `return root`, or inside `on_start()`.
**Warning signs:** `AttributeError` on `ids`, or overlay renders without the background being visible.

### Pitfall 4: ScreenManager transition not set — residual slide animation
**What goes wrong:** Screen switches show a brief left/right slide even though transitions are supposed to be instant.
**Why it happens:** Default `ScreenManager` transition is `SlideTransition`. If `NoTransition()` is not explicitly set, every `sm.current = '...'` triggers a slide.
**How to avoid:** Set in KV: `ScreenManager: transition: NoTransition()` or in Python `sm.transition = NoTransition()` immediately after ScreenManager creation.
**Warning signs:** Visible slide when switching tabs.

### Pitfall 5: users.json path on Windows vs Pi
**What goes wrong:** `users.json` writes to current working directory on Windows dev machine but is inaccessible at `os.getcwd()` when running on Pi.
**Why it happens:** CWD is unpredictable when launched as a service or from a launcher.
**How to avoid:** Place `users.json` alongside `main.py` using `os.path.dirname(os.path.abspath(__file__))`. Already the pattern used in the existing codebase for `resource_add_path`.
**Warning signs:** FileNotFoundError on Pi at startup, or silent creation in unexpected directory.

### Pitfall 6: Tab rebuild triggers on every state.notify()
**What goes wrong:** `TabBar.set_role()` is called on every MachineState change (position updates, connection status), causing the tab bar to flicker or reset which tab is "active".
**Why it happens:** If the tab bar subscribes to `state.subscribe(...)` without filtering for auth changes, every `state.notify()` triggers a rebuild.
**How to avoid:** Only call `set_role()` when `current_role` or `setup_unlocked` actually changes. Cache last role/unlocked state and compare before rebuilding.
**Warning signs:** Active tab resets to "normal" state mid-operation.

---

## Code Examples

Verified patterns from official Kivy 2.3.1 sources:

### NoTransition (instant screen switch)
```python
# Source: https://kivy.org/doc/stable/api-kivy.uix.screenmanager.html
from kivy.uix.screenmanager import ScreenManager, NoTransition

sm = ScreenManager(transition=NoTransition())
```

### ModalView — fullscreen, no dismiss on outside tap
```python
# Source: https://kivy.org/doc/stable/api-kivy.uix.modalview.html
from kivy.uix.modalview import ModalView

overlay = ModalView(auto_dismiss=False, size_hint=(1, 1))
overlay.open()        # shows overlay
overlay.dismiss()     # hides overlay
```

### Animation shake chain
```python
# Source: https://kivy.org/doc/stable/api-kivy.animation.html
from kivy.animation import Animation

def shake(widget):
    orig_x = widget.x
    anim = (
        Animation(x=orig_x - 12, duration=0.05)
        + Animation(x=orig_x + 12, duration=0.05)
        + Animation(x=orig_x - 8, duration=0.05)
        + Animation(x=orig_x + 8, duration=0.05)
        + Animation(x=orig_x, duration=0.05)
    )
    anim.start(widget)
```

### Inactivity timer with Window touch reset
```python
# Source: https://kivy.org/doc/stable/api-kivy.core.window.html
#         https://kivy.org/doc/stable/api-kivy.clock.html
from kivy.core.window import Window
from kivy.clock import Clock

class DMCApp(App):
    def build(self):
        root = ...
        self._idle_event = None
        Window.bind(on_touch_down=self._reset_idle_timer)
        Clock.schedule_once(lambda *_: self._reset_idle_timer(), 0)
        return root

    def _reset_idle_timer(self, *args) -> None:
        if self._idle_event:
            self._idle_event.cancel()
        self._idle_event = Clock.schedule_once(self._on_idle_timeout, 30 * 60)

    def _on_idle_timeout(self, dt) -> None:
        self.state.lock_setup()
```

### Defer overlay open to next frame
```python
# Prevents crash when opening ModalView during build()
from kivy.clock import Clock

def build(self):
    root = Factory.RootLayout()
    ...
    Clock.schedule_once(lambda *_: self._show_pin_on_start(), 0)
    return root

def _show_pin_on_start(self):
    if self.state.connected:
        self._pin_overlay.open()
    else:
        # connection screen handles this
        pass
```

### KV: 3x4 Numpad GridLayout
```kv
# Verified Kivy KV pattern for touch-target numpad
GridLayout:
    cols: 3
    rows: 4
    spacing: '4dp'
    size_hint: None, None
    width: '330dp'
    height: '280dp'
    # Row 1
    Button:
        text: '1'
        font_size: '24sp'
        size_hint: 1, None
        height: '64dp'
        on_release: root.press_digit('1')
    # ... repeat for 2-9
    # Row 4
    Button:
        text: '<'
        font_size: '24sp'
        size_hint: 1, None
        height: '64dp'
        on_release: root.press_backspace()
    Button:
        text: '0'
        font_size: '24sp'
        size_hint: 1, None
        height: '64dp'
        on_release: root.press_digit('0')
    Button:
        text: 'OK'
        font_size: '20sp'
        size_hint: 1, None
        height: '64dp'
        on_release: root.press_enter()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ActionBar + Spinner navigation | Persistent tab bar (BoxLayout of Buttons) | This phase | Eliminates multi-level menu navigation |
| No auth — all screens accessible | PIN overlay + role gating | This phase | Foundation for all subsequent phases |
| SomeMenu_ActionBar widget | StatusBar + TabBar widgets | This phase | Separation of concerns; each has focused responsibility |
| Banner ticker in RootLayout body | Banner ticker in StatusBar center section | This phase | Status bar consolidates all persistent UI |

**Deprecated/outdated (to be removed in this phase):**
- `SomeMenu_ActionBar`: Entire widget and all its KV — replaced by StatusBar + TabBar
- All 7 old screen KV files (rest.kv, start.kv, buttons_switches.kv, parameters_setup.kv, axisDSetup.kv, serration_knife.kv, axis_angles.kv)
- All 7 old screen Python classes (RestScreen, StartScreen, ButtonsSwitchesScreen, ParametersSetupScreen, AxisDSetupScreen, SerratedKnifeScreen, AxisAnglesScreen, ArraysScreen)
- `arrays.kv` and `edges.kv` (not referenced outside deleted screens)
- `banner_text` StringProperty in DMCApp moves inside StatusBar's ticker section

---

## Open Questions

1. **users.json writable path on Pi in kiosk mode**
   - What we know: Phase 8 locks the filesystem; `os.path.dirname(__file__)` works on Windows dev
   - What's unclear: Whether the app's install directory is writable in kiosk mode on Pi
   - Recommendation: Use `__file__`-relative path now; add a note that Phase 8 must confirm write permissions (tracked in STATE.md as existing concern)

2. **Tab bar icon assets**
   - What we know: Claude's discretion for exact icon choices; existing assets are PNG files in `assets/images/`
   - What's unclear: Whether any suitable icons already exist in the assets folder, or if placeholder text-only tabs are acceptable for Phase 1
   - Recommendation: Default to text-only tabs (`Icon + label` per CONTEXT.md) using Unicode symbols (e.g., play triangle for Run, gear for Setup) until proper icons are sourced; no external icon font required

3. **SetupScreen (connection screen) startup flow integration**
   - What we know: Connection screen is preserved; auto-connect success → skip to PIN overlay; auto-connect fail → show connection screen
   - What's unclear: The current `initial_refresh()` auto-connect in SetupScreen fires in `main.py build()` and navigates nowhere on success. The new flow must trigger PIN overlay after successful connect.
   - Recommendation: Add a callback hook in `SetupScreen.connect()`: on success, if `_autoconnect` path, call `app._show_pin_overlay()`. The ScreenManager should start on `'setup'` screen and only switch to `'run'` after PIN login.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (declared in pyproject.toml dev deps) |
| Config file | None — no pytest.ini or pyproject.toml [tool.pytest] section exists |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | PIN overlay opens on startup; numpad input produces masked dots | manual-only | — | ❌ Wave 0 |
| AUTH-02 | users.json last_user pre-selects username in overlay | unit | `pytest tests/test_auth_manager.py::test_last_user_persistence -x` | ❌ Wave 0 |
| AUTH-03 | validate_pin returns correct role; wrong PIN returns None | unit | `pytest tests/test_auth_manager.py::test_validate_pin -x` | ❌ Wave 0 |
| AUTH-04 | Operator role → tabs_for_role returns Run only | unit | `pytest tests/test_tab_bar.py::test_operator_tabs -x` | ❌ Wave 0 |
| AUTH-05 | Setup role taps restricted tab → PIN overlay opens | manual-only | — | ❌ Wave 0 |
| AUTH-06 | lock_setup() sets setup_unlocked=False and notifies | unit | `pytest tests/test_app_state.py::test_lock_setup -x` | ❌ Wave 0 |
| NAV-01 | TabBar renders visible buttons matching role | manual-only | — | ❌ Wave 0 |
| NAV-02 | E-STOP button exists in StatusBar | manual-only | — | ❌ Wave 0 |
| NAV-03 | Admin role → all 4 tabs visible; Setup → 3 tabs | unit | `pytest tests/test_tab_bar.py::test_role_tab_counts -x` | ❌ Wave 0 |
| NAV-04 | Connection status string reflects state.connected | unit | `pytest tests/test_app_state.py::test_connection_status -x` | ❌ Wave 0 |
| NAV-05 | current_user and current_role in MachineState after set_auth | unit | `pytest tests/test_app_state.py::test_set_auth -x` | ❌ Wave 0 |
| UI-01 | Dark palette constants used in new KV files | manual-only | — | — |
| UI-02 | Axis colors unchanged in theme.kv | manual-only | — | — |
| UI-03 | All buttons height >= 44dp in new KV | manual-only | — | — |
| UI-04 | NoTransition set on ScreenManager | unit | `pytest tests/test_main.py::test_no_transition -x` | ❌ Wave 0 |

**Note on manual-only tests:** Kivy UI requires a running display and event loop. Unit tests cover pure Python logic (AuthManager, MachineState, role filtering). Visual layout (button sizing, overlay appearance, animation) requires manual smoke testing. Automated Kivy widget tests exist (`kivy.tests` headless mode) but require substantial setup not warranted for this project scale.

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` — package init
- [ ] `tests/test_auth_manager.py` — covers AUTH-02, AUTH-03 (pure Python, no Kivy required)
- [ ] `tests/test_app_state.py` — covers AUTH-06, NAV-04, NAV-05 (pure Python dataclass tests)
- [ ] `tests/test_tab_bar.py` — covers AUTH-04, NAV-03 (pure Python tab filtering logic)
- [ ] `tests/test_main.py` — covers UI-04 (ScreenManager transition type)
- [ ] `tests/conftest.py` — shared fixtures (mock AuthManager, mock MachineState)
- [ ] Framework config: add `[tool.pytest.ini_options] testpaths = ["tests"]` to pyproject.toml

---

## Sources

### Primary (HIGH confidence)
- Kivy 2.3.1 official docs — ModalView: https://kivy.org/doc/stable/api-kivy.uix.modalview.html
- Kivy 2.3.1 official docs — Animation: https://kivy.org/doc/stable/api-kivy.animation.html
- Kivy 2.3.1 official docs — Clock: https://kivy.org/doc/stable/api-kivy.clock.html
- Kivy 2.3.1 official docs — Window: https://kivy.org/doc/stable/api-kivy.core.window.html
- Kivy 2.3.1 official docs — ScreenManager: https://kivy.org/doc/stable/api-kivy.uix.screenmanager.html
- Direct codebase reading: `main.py`, `app_state.py`, `base.kv`, `theme.kv`, `setup.py`, `screens/__init__.py`, `utils/jobs.py`

### Secondary (MEDIUM confidence)
- Kivy 2.3.1 installed version confirmed via `pip show kivy` — version 2.3.1 on Python 3.13

### Tertiary (LOW confidence)
- None — all findings verified against official docs or codebase

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Kivy 2.3.1 installed; all APIs verified in official docs
- Architecture: HIGH — patterns derived from reading existing codebase conventions and official Kivy docs
- Pitfalls: HIGH — ModalView background_color/overlay_color split verified in official docs; animation/pos_hint conflict is well-documented Kivy behavior
- Auth logic: HIGH — pure Python, no external dependencies, simple JSON file
- Test infrastructure: MEDIUM — pytest present in pyproject.toml dev deps but no test directory exists yet

**Research date:** 2026-04-04
**Valid until:** 2026-07-04 (Kivy 2.x API is stable; 90 days reasonable)
