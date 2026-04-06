# Phase 14: State-Driven UI - Research

**Researched:** 2026-04-06
**Domain:** Kivy property binding, StatusBar extension, TabBar state gating, MachineState subscription pattern
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**State status display**
- State label lives in StatusBar — visible on ALL screens at all times
- Colored text label (not a badge/chip) matching StatusBar density
- State colors: IDLE=orange, GRINDING=green, SETUP=red, HOMING=orange, OFFLINE=red/gray, E-STOP=red
- Shows state name only — no elapsed time, no context, no animations
- dmc_state=0 maps to either OFFLINE (program_running=True, uninitialized) or E-STOP (program_running=False, program was killed)
- E-STOP vs OFFLINE distinction uses MachineState.program_running flag — controller-authoritative

**Setup mode badge**
- Yellow bar with "SETUP MODE" text centered, ~24dp tall
- Positioned between StatusBar and screen content area — visible on ALL screens
- Only visible when dmc_state == STATE_SETUP (3)
- Disappears on disconnect (clear everything, no stale state)

**Tab gating**
- Run tab: disabled and grayed during SETUP state
- Axes Setup + Parameters tabs: disabled and grayed during GRINDING or HOMING states
- Profiles and Users tabs: always accessible regardless of state
- HOMING uses same gating rules as GRINDING (both are "motion active" states)
- When disconnected: ALL tabs accessible (motion buttons within screens are individually disabled via motion_active=True)
- When state returns to IDLE: all tab gates release

**Cross-screen button gating**
- Profile import/apply buttons: disabled when motion_active (GRINDING/HOMING/disconnected)
- Parameters "Apply to Controller": disabled when motion_active
- Parameters "Read from Controller": always accessible (read-only operation)
- Run page buttons: already gated via motion_active from Phase 11 — no changes needed
- Axes Setup jog/teach: already gated on dmc_state==SETUP from Phase 13 — no changes needed

**Disconnect behavior**
- On disconnect: clear setup badge, release all tab gates, state label shows OFFLINE
- All tabs accessible when disconnected
- All motion buttons disabled within each screen (existing motion_active=True when disconnected)
- On reconnect: state rebuilds from first poll tick — no special logic needed

**State transitions**
- Instant updates only — no animations, no flashes, no color transitions
- Consistent with PROJECT.md constraint: "Animated screen transitions adds latency on industrial tool"

### Claude's Discretion
- Exact StatusBar layout adjustment to fit state label (may need to resize other elements)
- Setup badge implementation approach (separate widget vs canvas instruction)
- Tab gating mechanism (Kivy disabled property binding or ScreenManager override)
- How to propagate MachineState to tab bar for gating (subscription pattern or property binding)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-01 | Buttons enable/disable based on polled controller state (e.g., no Start Grind while already grinding) | motion_active pattern already on RunScreen; extend to ProfilesScreen and ParametersScreen via MachineState.subscribe() |
| UI-02 | Status label displays current controller state (IDLE, GRINDING, SETUP, HOMING, NEW SESSION) | StatusBar.update_from_state() already called on every poll tick; add state_text/state_color StringProperty/ListProperty |
| UI-03 | Setup mode badge visible on all screens when controller is in setup state | RootLayout in base.kv is the right place; add a dedicated Label widget between StatusBar and TabBar with opacity binding |
| UI-04 | Run tab disables when controller is in setup mode | TabBar._on_tab_press and set_role already rebuild buttons; need dmc_state-based gating layer separate from role-based gating |
| UI-05 | Connection status indicator visible at all times | Already implemented in StatusBar connection dot + text — no additional work; confirm it remains on all screens |
</phase_requirements>

---

## Summary

Phase 14 is a pure UI-wiring phase. Every piece of data it needs (dmc_state, connected, program_running) is already polled and held in MachineState. The work is surfacing that data in the right widgets at the right times.

The subscription architecture is already established: `MachineState.subscribe()` returns an unsubscribe callable, callbacks use `Clock.schedule_once` for thread safety, and `StatusBar.update_from_state()` is already called on every poll tick. This phase extends that same pattern to three new concerns: a state label in the StatusBar, a setup badge in RootLayout, and dmc_state-based gating in TabBar.

The trickiest part is tab gating: the existing TabBar is purely role-driven (rebuilt in `set_role()`). Adding dmc_state gates requires a second gating axis — state-based disable/gray on top of role-based visibility. The recommended approach is a new `update_state_gates(dmc_state, connected)` method on TabBar that iterates current child buttons and sets `disabled`/`opacity` based on tab name.

**Primary recommendation:** Extend StatusBar, TabBar, and two screen classes using the existing subscribe/update_from_state pattern. Do not modify the poll loop or MachineState data model.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Kivy | Project standard | UI framework, properties, clock | Entire app is Kivy |
| kivy.properties.StringProperty | — | Reactive text binding for state_text | Used throughout; KV auto-updates labels |
| kivy.properties.ListProperty | — | Reactive RGBA binding for state_color | Used by connection_color in StatusBar |
| kivy.properties.BooleanProperty | — | Reactive visibility for setup badge | Used by motion_active on RunScreen |
| kivy.clock.Clock | — | Thread-safe deferred UI update | All state subscription callbacks use this |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| kivy.uix.label.Label | — | Setup badge text | Adding badge as a standalone widget in KV |
| kivy.graphics.Color + Rectangle | — | Canvas-drawn badge background | Already used in StatusBar and TabBar for custom backgrounds |

---

## Architecture Patterns

### Recommended Project Structure
No new files required. Changes are surgical extensions to:
```
src/dmccodegui/
├── screens/status_bar.py       # +state_text, state_color properties; update_from_state() extension
├── ui/status_bar.kv            # +state label widget in StatusBar horizontal layout
├── ui/base.kv                  # +setup badge widget between StatusBar and TabBar
├── screens/tab_bar.py          # +update_state_gates() method
├── main.py                     # +subscribe state to tab_bar.update_state_gates
├── screens/profiles.py         # +motion_active gating on import/apply buttons
└── screens/parameters.py       # +motion_active gating on Apply to Controller button
```

### Pattern 1: StatusBar State Label Extension

**What:** Add two Kivy properties (`state_text: StringProperty`, `state_color: ListProperty`) to `StatusBar`. Update them in `update_from_state()` using `_prev_dmc_state` change detection. Add a Label widget in `status_bar.kv`.

**When to use:** Any time a new piece of controller state needs to be reflected in the StatusBar.

**State-to-label mapping (Python):**
```python
# Source: app_state.py STATE constants (dmc_vars.py)
# In StatusBar.update_from_state():
STATE_COLORS = {
    1: ("IDLE",     [1.0,  0.6,  0.0,  1]),   # orange
    2: ("GRINDING", [0.13, 0.77, 0.37, 1]),   # green  (same as connected_color)
    3: ("SETUP",    [0.9,  0.2,  0.2,  1]),   # red
    4: ("HOMING",   [1.0,  0.6,  0.0,  1]),   # orange
}
dmc_state = getattr(state, "dmc_state", 0)
program_running = getattr(state, "program_running", True)
connected = getattr(state, "connected", False)

if not connected:
    if not program_running:
        label, color = "E-STOP", [0.9, 0.2, 0.2, 1]
    else:
        label, color = "OFFLINE", [0.55, 0.55, 0.55, 1]
else:
    label, color = STATE_COLORS.get(dmc_state, ("OFFLINE", [0.55, 0.55, 0.55, 1]))

if dmc_state != self._prev_dmc_state or connected != self._prev_connected:
    self._prev_dmc_state = dmc_state
    self.state_text = label
    self.state_color = color
```

**KV addition (status_bar.kv):** Insert a fixed-width Label between the banner ticker and the theme toggle:
```kv
Label:
    id: state_label
    text: root.state_text
    color: root.state_color
    size_hint_x: None
    width: '120dp'
    font_size: '20sp'
    bold: True
    halign: 'center'
    valign: 'middle'
    text_size: self.size
```

### Pattern 2: Setup Badge in RootLayout

**What:** Add a standalone Label (styled as a yellow bar) directly in `base.kv`, between `StatusBar` and `TabBar`. Its `opacity` is 0 when not in SETUP state, 1 when SETUP.

**When to use:** Any global mode indicator that must appear on all screens without per-screen subscription.

**Approach — KV rule in base.kv:**
```kv
# Between StatusBar and TabBar in RootLayout:
Label:
    id: setup_badge
    text: 'SETUP MODE'
    size_hint_y: None
    height: '0dp'        # collapsed when hidden (opacity + height=0 prevents layout gap)
    opacity: 0
    bold: True
    font_size: '17sp'
    color: 0, 0, 0, 1
    canvas.before:
        Color:
            rgba: 1, 0.85, 0, 1
        Rectangle:
            pos: self.pos
            size: self.size
```

**Python wiring in main.py** (inside `build()`, after state subscription is set up):
```python
# Inside DMCApp.build():
setup_badge = root.ids.setup_badge

def _update_setup_badge(s):
    in_setup = s.connected and s.dmc_state == STATE_SETUP
    setup_badge.opacity = 1.0 if in_setup else 0.0
    setup_badge.height = '24dp' if in_setup else '0dp'

self.state.subscribe(
    lambda s: Clock.schedule_once(lambda *_: _update_setup_badge(s))
)
```

**Design note:** Using `height='0dp'` when hidden prevents layout gap — the badge takes no vertical space when SETUP is not active. When visible, it expands to 24dp and pushes the TabBar + ScreenManager down. This is the correct Kivy approach (not `opacity` alone, which keeps layout space).

### Pattern 3: TabBar State-Based Gating

**What:** Add `update_state_gates(dmc_state: int, connected: bool)` to `TabBar`. This method iterates the current child buttons, maps tab name to gating rules, and sets `disabled` + color on each button.

**Gate rules (from locked decisions):**
```python
# In TabBar.update_state_gates():
from dmccodegui.hmi.dmc_vars import STATE_SETUP, STATE_GRINDING, STATE_HOMING

MOTION_ACTIVE = dmc_state in (STATE_GRINDING, STATE_HOMING)

TAB_GATES = {
    "run":        lambda: dmc_state == STATE_SETUP,
    "axes_setup": lambda: MOTION_ACTIVE,
    "parameters": lambda: MOTION_ACTIVE,
    # profiles, diagnostics, users: never gated by state
}
```

**When disconnected:** `connected=False` → all gates off (all tabs accessible, motion buttons inside screens handle their own gating via `motion_active=True`).

**Button disable visual — in update_state_gates():**
```python
for btn in self.children:
    tab_name = getattr(btn, '_tab_name', None)
    if tab_name is None:
        continue
    gate_fn = TAB_GATES.get(tab_name)
    should_disable = gate_fn() if gate_fn and connected else False
    btn.disabled = should_disable
    if should_disable:
        btn.background_color = [0.2, 0.2, 0.2, 0.5]   # gray
        btn.color = [0.5, 0.5, 0.5, 1]
    elif btn.state == 'down':
        btn.background_color = [0.133, 0.773, 0.369, 0.3]  # active
        btn.color = [1, 1, 1, 1]
    else:
        btn.background_color = list(theme.bg_row)
        btn.color = [1, 1, 1, 1]
```

**Critical implementation detail:** The existing `set_role()` creates buttons without storing the tab name on the button widget. The `_tab_name` attribute must be set during button creation in `set_role()`:
```python
btn._tab_name = name   # Add this line in set_role() after creating each btn
```

**Wiring in main.py:**
```python
# Subscribe TabBar to state changes:
def _update_tab_gates(s):
    tab_bar.update_state_gates(s.dmc_state, s.connected)

self.state.subscribe(
    lambda s: Clock.schedule_once(lambda *_: _update_tab_gates(s))
)
```

**Navigate-away guard:** When Run tab becomes disabled (SETUP state active) and operator is currently on Run screen, the controller is in setup — this is expected. The operator navigated via Axes Setup or Parameters tab (which are enabled in SETUP). No forced navigation needed.

When Axes Setup or Parameters tab becomes disabled (GRINDING state) and operator is on one of those screens, the screen should force-navigate to Run. Add this in `update_state_gates()`:
```python
# After computing gates — if currently active tab just got disabled, navigate to run
try:
    from kivy.app import App
    app = App.get_running_app()
    sm = app.root.ids.sm
    if sm.current in ("axes_setup", "parameters") and MOTION_ACTIVE:
        sm.current = "run"
        self.current_tab = "run"
        # Reset visual state of all buttons
except Exception:
    pass
```

### Pattern 4: Screen-Level motion_active Gating (Profiles + Parameters)

**What:** Replicate the RunScreen `motion_active` BooleanProperty pattern on `ProfilesScreen` and `ParametersScreen`. Subscribe in `on_pre_enter`, unsubscribe in `on_leave`. Use the same disconnected=True logic.

**ProfilesScreen — current issue:** `_update_import_button()` only checks `state.cycle_running` (old approach). This must change to check `motion_active` (GRINDING or HOMING or disconnected).

```python
# In ProfilesScreen._update_import_button():
if self.state is None:
    motion_active = False
else:
    from dmccodegui.hmi.dmc_vars import STATE_GRINDING, STATE_HOMING
    motion_active = (
        not self.state.connected
        or self.state.dmc_state in (STATE_GRINDING, STATE_HOMING)
    )
btn.disabled = motion_active
btn.opacity = 0.4 if motion_active else 1.0
```

**ParametersScreen — `apply_to_controller()` guard:** Currently checks `state.cycle_running`. Change to check `motion_active`:
```python
# In ParametersScreen.apply_to_controller():
if self.state is not None:
    from dmccodegui.hmi.dmc_vars import STATE_GRINDING, STATE_HOMING
    motion_active = (
        not self.state.connected
        or self.state.dmc_state in (STATE_GRINDING, STATE_HOMING)
    )
    if motion_active:
        return
```

ParametersScreen also needs `on_pre_enter` to subscribe to state changes for dynamic apply button gating. Currently it only gates at call time. A subscription + `_update_apply_button()` method (mirroring ProfilesScreen's `_update_import_button()`) provides live gating.

### Anti-Patterns to Avoid

- **Adding state subscription to StatusBar itself:** StatusBar is already updated from main.py subscription. Don't add a second `subscribe()` call inside StatusBar — this doubles the listener count.
- **Storing tab names only in the KV text:** Tab names are not reliably extractable from the button `text` property (text is the display label like "Axes Setup", name is "axes_setup"). Always store `btn._tab_name = name` in `set_role()`.
- **Using `opacity=0` alone for setup badge:** `opacity=0` hides the widget visually but preserves its layout height. Must set `height='0dp'` when hidden to avoid a blank gap between StatusBar and TabBar.
- **Gating tabs when disconnected:** Per locked decisions, all tabs are accessible when disconnected. Gate logic must check `connected` first.
- **Forcing navigation away from Run when SETUP activates:** Operator starting setup from the physical panel while on Run screen is valid. Don't force-navigate from Run when SETUP activates — only force-navigate from setup screens when GRINDING/HOMING activates.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Thread-safe UI update | Direct property assignment in background thread | `Clock.schedule_once(lambda *_: ...)` wrapping the subscriber callback | Kivy canvas operations are not thread-safe; Clock.schedule_once defers to main thread |
| State change detection | Polling dmc_state in a Clock interval | MachineState.subscribe() | Already wired to every poll tick at 10 Hz; no separate clock needed |
| Cross-screen badge | Per-screen badge widget + per-screen subscription | Single widget in RootLayout (base.kv) + single main.py subscription | One source of truth; badge is impossible to miss per design decision |
| Role-to-tabs mapping | Rebuilding ALL_TABS logic | Reuse existing TabBar.set_role() | set_role already handles role-based visibility; state gates are a second orthogonal axis |

---

## Common Pitfalls

### Pitfall 1: _prev_dmc_state Cache Missing in StatusBar
**What goes wrong:** `update_from_state()` sets `state_text` on every poll tick even when nothing changed. With 10 Hz polling, this triggers KV redraws 600 times/minute.
**Why it happens:** StatusBar already uses `_prev_connected`, `_prev_user`, etc. for change detection but the new field misses the pattern.
**How to avoid:** Add `_prev_dmc_state: int = -1` as a class attribute and gate state_text/state_color updates behind `if dmc_state != self._prev_dmc_state or connected != self._prev_connected`.
**Warning signs:** Visible flicker on state label; CPU load higher than baseline.

### Pitfall 2: Tab Gating vs Role Visibility Conflict
**What goes wrong:** `update_state_gates()` iterates `self.children`. But `TabBar.children` in Kivy is in reverse order (last-added first). Also, `set_role()` calls `clear_widgets()` then re-adds buttons — gating state is lost on every role change.
**Why it happens:** `set_role()` rebuilds the entire button list. If gating is applied via stored state on buttons, role-change discards it.
**How to avoid:** After `set_role()` completes, immediately call `update_state_gates()` with the current dmc_state/connected. In main.py, wire both: role change re-calls gates update.
**Warning signs:** Tabs appear ungated after user logs in with a different role.

### Pitfall 3: Setup Badge Height Leaving a Ghost Gap
**What goes wrong:** Setting `opacity: 0` on setup badge still reserves its height in the BoxLayout — a blank strip appears between StatusBar and TabBar.
**Why it happens:** Kivy `opacity` is visual only. Layout calculation uses `size_hint`/`height`.
**How to avoid:** Set `height: '0dp'` (or `size_hint_y: None; height: 0`) when badge is hidden. Toggle height in the Python callback alongside opacity.
**Warning signs:** Blank strip between StatusBar and TabBar when not in SETUP mode.

### Pitfall 4: ProfilesScreen Import Button Re-Wired to Wrong Gate
**What goes wrong:** Profile import button gates on `state.cycle_running` (old pattern) instead of `motion_active`. During HOMING, import is not blocked.
**Why it happens:** `_update_import_button()` was written before `motion_active` pattern was established in Phase 11.
**How to avoid:** Change gate condition to check `dmc_state in (STATE_GRINDING, STATE_HOMING) or not connected`.
**Warning signs:** Import button remains active during HOMING.

### Pitfall 5: Tabs Inaccessible When Disconnected
**What goes wrong:** Tab gating logic does not short-circuit on `connected=False`, so all tabs are disabled when disconnected (since dmc_state may still hold the last known value).
**Why it happens:** dmc_state is not cleared on disconnect — it retains its last value. Checking `dmc_state == STATE_SETUP` without checking `connected` first can produce stale gates.
**How to avoid:** In `update_state_gates()`, check `connected` first: if `not connected`, clear all gates (all tabs accessible).
**Warning signs:** Operator disconnects, tabs become disabled/inaccessible — cannot navigate to reconnect screen.

### Pitfall 6: ParametersScreen Apply Button Not Live-Gated
**What goes wrong:** The `apply_to_controller()` guard only prevents execution at call time. The Apply button remains visually enabled while GRINDING/HOMING.
**Why it happens:** The existing subscribe in `on_pre_enter` only updates `_update_import_button()` — ParametersScreen has no subscribe for apply-button gating.
**How to avoid:** Add a `_update_apply_button()` method and wire it into the existing subscription in `on_pre_enter`.
**Warning signs:** Apply button visible and enabled while grinding; tap does nothing (guard prevents execution) but gives no visual feedback.

---

## Code Examples

### StatusBar.update_from_state() Extension

```python
# Source: src/dmccodegui/screens/status_bar.py — existing pattern extended
# Add to StatusBar class:
state_text = StringProperty("OFFLINE")
state_color = ListProperty([0.55, 0.55, 0.55, 1])
_prev_dmc_state: int = -1

_STATE_MAP = {
    1: ("IDLE",     [1.0,  0.60, 0.0,  1]),   # orange
    2: ("GRINDING", [0.13, 0.77, 0.37, 1]),   # green
    3: ("SETUP",    [0.9,  0.2,  0.2,  1]),   # red
    4: ("HOMING",   [1.0,  0.60, 0.0,  1]),   # orange
}

# Inside update_from_state(), after existing connected block:
dmc_state = getattr(state, "dmc_state", 0)
program_running = getattr(state, "program_running", True)

if dmc_state != self._prev_dmc_state or connected != self._prev_connected:
    self._prev_dmc_state = dmc_state
    if not connected:
        if not program_running:
            label, color = "E-STOP", [0.9, 0.2, 0.2, 1]
        else:
            label, color = "OFFLINE", [0.55, 0.55, 0.55, 1]
    else:
        label, color = self._STATE_MAP.get(dmc_state, ("OFFLINE", [0.55, 0.55, 0.55, 1]))
    self.state_text = label
    self.state_color = color
```

### TabBar.update_state_gates()

```python
# Source: src/dmccodegui/screens/tab_bar.py — new method
from dmccodegui.hmi.dmc_vars import STATE_SETUP, STATE_GRINDING, STATE_HOMING

def update_state_gates(self, dmc_state: int, connected: bool) -> None:
    """Apply dmc_state-based disable gates to current tab buttons.

    Called from main.py on every MachineState change.
    Operates orthogonally to set_role() role-based visibility.
    """
    motion_active = connected and dmc_state in (STATE_GRINDING, STATE_HOMING)

    # Tab-name -> should_disable predicate (only applies when connected)
    gate: dict[str, bool] = {
        "run":        connected and dmc_state == STATE_SETUP,
        "axes_setup": motion_active,
        "parameters": motion_active,
        # profiles, diagnostics, users: no state gate
    }

    for btn in self.children:
        tab_name = getattr(btn, '_tab_name', None)
        if tab_name is None:
            continue
        should_disable = gate.get(tab_name, False)
        btn.disabled = should_disable
        if should_disable:
            btn.background_color = [0.15, 0.15, 0.15, 0.6]
            btn.color = [0.4, 0.4, 0.4, 1]
        elif btn.state == 'down':
            btn.background_color = [0.133, 0.773, 0.369, 0.3]
            btn.color = [1, 1, 1, 1]
        else:
            btn.background_color = list(theme.bg_row)
            btn.color = [1, 1, 1, 1]
```

### main.py Wiring (inside build())

```python
# Source: src/dmccodegui/main.py — additions to build()
from .hmi.dmc_vars import STATE_SETUP

# After existing StatusBar subscription:
setup_badge = root.ids.setup_badge

def _update_setup_badge(s):
    in_setup = s.connected and s.dmc_state == STATE_SETUP
    setup_badge.opacity = 1.0 if in_setup else 0.0
    setup_badge.height = dp(24) if in_setup else 0

self.state.subscribe(
    lambda s: Clock.schedule_once(lambda *_: _update_setup_badge(s))
)

# Tab state gates:
def _update_tab_gates(s):
    tab_bar.update_state_gates(s.dmc_state, s.connected)

self.state.subscribe(
    lambda s: Clock.schedule_once(lambda *_: _update_tab_gates(s))
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `state.cycle_running` as button gate | `dmc_state in (STATE_GRINDING, STATE_HOMING)` via motion_active | Phase 11 | Controller is authority; Python-derived cycle_running is removed as gate |
| Profile import gated on `cycle_running` only | Gate on `motion_active` (GRINDING or HOMING or disconnected) | Phase 14 | HOMING also blocks import |
| TabBar purely role-driven | TabBar role-driven + dmc_state-driven overlay | Phase 14 | Run tab blocks during SETUP; setup tabs block during motion |

---

## Open Questions

1. **Setup badge height toggle via Python dp() vs KV string**
   - What we know: Kivy `height` accepts both `'24dp'` strings (in KV) and `dp(24)` (Python float)
   - What's unclear: Whether assigning a string like `'24dp'` directly in Python to a `height` NumericProperty works without an explicit `dp()` call
   - Recommendation: Use `from kivy.metrics import dp` and assign `dp(24)` / `0` in Python for the badge height toggle

2. **Force-navigate from setup screens when GRINDING starts**
   - What we know: If operator is on Axes Setup and GRINDING starts (controller-side, e.g. physical panel), the tab becomes disabled but the screen remains shown
   - What's unclear: Whether update_state_gates() should force-navigate to Run in this case, and whether that is disruptive
   - Recommendation: Include forced navigation (sm.current = "run") in update_state_gates() when axes_setup or parameters is the current screen and motion_active becomes True — this prevents a confusing state where the visible screen has a disabled tab

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | none (pytest auto-discovers tests/) |
| Quick run command | `python -m pytest tests/test_app_state.py tests/test_tab_bar.py -x -q` |
| Full suite command | `python -m pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | motion_active gates Profile import when GRINDING/HOMING | unit | `python -m pytest tests/test_profiles.py -x -q` | ✅ |
| UI-01 | motion_active gates Parameters Apply when GRINDING/HOMING | unit | `python -m pytest tests/test_parameters.py -x -q` | ✅ |
| UI-02 | StatusBar shows correct state_text for each dmc_state value | unit | `python -m pytest tests/test_status_bar.py -x -q` | ❌ Wave 0 |
| UI-02 | E-STOP vs OFFLINE distinction uses program_running flag | unit | `python -m pytest tests/test_status_bar.py -x -q` | ❌ Wave 0 |
| UI-03 | Setup badge appears when dmc_state==STATE_SETUP and connected | unit | `python -m pytest tests/test_main_estop.py -x -q` (extend) or new | ❌ Wave 0 |
| UI-04 | TabBar.update_state_gates disables Run tab during SETUP | unit | `python -m pytest tests/test_tab_bar.py -x -q` | ✅ (extend) |
| UI-04 | TabBar.update_state_gates disables axes_setup/parameters during GRINDING/HOMING | unit | `python -m pytest tests/test_tab_bar.py -x -q` | ✅ (extend) |
| UI-04 | All tabs accessible when disconnected | unit | `python -m pytest tests/test_tab_bar.py -x -q` | ✅ (extend) |
| UI-05 | StatusBar connection indicator present (already implemented) | smoke | `python -m pytest tests/test_run_screen.py::test_no_estop_in_run_bar -x -q` | ✅ |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_tab_bar.py tests/test_app_state.py -x -q`
- **Per wave merge:** `python -m pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_status_bar.py` — covers UI-02: state_text per dmc_state, E-STOP vs OFFLINE, color properties
- [ ] `tests/test_status_bar.py` — covers UI-03 indirectly: state_text shows "SETUP" when dmc_state==3 and connected
- [ ] Extend `tests/test_tab_bar.py` — covers UI-04: update_state_gates method (new method, no tests yet)

---

## Sources

### Primary (HIGH confidence)
- Direct source inspection: `src/dmccodegui/screens/status_bar.py` — update_from_state() pattern, _prev_* caching
- Direct source inspection: `src/dmccodegui/screens/tab_bar.py` — set_role(), _on_tab_press(), button construction
- Direct source inspection: `src/dmccodegui/screens/run.py` — _apply_state(), motion_active pattern, subscribe/unsubscribe
- Direct source inspection: `src/dmccodegui/main.py` — build(), subscription wiring to StatusBar
- Direct source inspection: `src/dmccodegui/ui/base.kv` — RootLayout structure
- Direct source inspection: `src/dmccodegui/ui/status_bar.kv` — current StatusBar widget layout
- Direct source inspection: `src/dmccodegui/app_state.py` — MachineState fields, subscribe(), notify()
- Direct source inspection: `src/dmccodegui/hmi/dmc_vars.py` — STATE_* constants

### Secondary (MEDIUM confidence)
- Kivy documentation (training knowledge): BoxLayout height=0 suppresses layout; dp() conversion for Python height assignment; BooleanProperty/StringProperty/ListProperty reactive binding; Clock.schedule_once thread-safety guarantee

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — entire stack is already used; no new libraries
- Architecture: HIGH — patterns are literal copies/extensions of existing RunScreen and StatusBar patterns in the codebase
- Pitfalls: HIGH — derived directly from code inspection of the actual files being modified
- Tab gating: MEDIUM — new method on TabBar; approach is sound but `_tab_name` attribute storage on Kivy ToggleButton objects warrants a test to confirm persistence

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable — no external dependencies)
