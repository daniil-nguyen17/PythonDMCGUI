# Phase 18: Base Class Extraction - Research

**Researched:** 2026-04-11
**Domain:** Python multiple inheritance, Kivy Screen lifecycle, MachineState subscription pattern
**Confidence:** HIGH — all findings drawn from live codebase inspection, no external research required

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Extraction boundary:**
- BaseRunScreen: thin — owns controller/state ObjectProperties, MachineState subscribe/unsubscribe lifecycle, _on_state_change dispatch only. Does NOT own pos_poll, mg_reader, matplotlib, deltaC/bComp, or cycle controls.
- BaseAxesSetupScreen: includes jog infrastructure — owns controller/state properties, on_pre_enter/on_leave lifecycle, jog_axis() with axis_list from machine_config, and the CPM read pattern. Serration/Convex inherit jog for free, only customize axis rows and teach points.
- BaseParametersScreen: includes card builder + dirty tracking — owns controller/state properties, lifecycle, build_param_cards(), validate_field(), dirty tracking, apply_to_controller(), read_from_controller(). All of these already use machine_config dynamically.
- Existing RunScreen/AxesSetupScreen/ParametersScreen keep their current names and inherit from the new bases. No rename in this phase (Phase 19 handles FlatGrind* rename). Isolates MRO risk.
- _BaseBarChart and DeltaCBarChart are Flat Grind-specific — move to screens/flat_grind_widgets.py along with DELTA_C_* constants and stone_window_for_index()
- BCompBarChart and BCOMP_* constants are Serration-specific — stay in run.py for now, move to serration in Phase 21
- bComp is NOT a Flat Grind feature — remove from flat_grind_widgets.py, defer to Serration phase

**Setup enter/exit pattern:**
- Shared SetupScreenMixin class with _enter_setup_if_needed() and _exit_setup_if_needed() methods
- Mixin includes the motion guard (skip hmiSetp if STATE_GRINDING or STATE_HOMING)
- Mixin owns the canonical _SETUP_SCREENS frozenset as a class attribute (currently duplicated in axes_setup.py and parameters.py)
- BaseAxesSetupScreen and BaseParametersScreen both use SetupScreenMixin
- BaseRunScreen does NOT use SetupScreenMixin (Run page doesn't enter setup mode)
- ProfilesScreen NOT wired to mixin in this phase — leave for later

**File organization:**
- All base classes in a single file: screens/base.py (BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen, SetupScreenMixin)
- Flat Grind-specific widgets and constants in: screens/flat_grind_widgets.py (DeltaCBarChart, _BaseBarChart, DELTA_C_* constants, stone_window_for_index())
- No new directories created in this phase

**Subscription lifecycle:**
- Base class subscribes to MachineState automatically in on_pre_enter, unsubscribes in on_leave (ARCH-02 compliance)
- Subclasses override _on_state_change(state) to handle their specific needs
- Base wraps subscription callback with Clock.schedule_once so subclasses can safely update Kivy widgets in their handler
- Base on_leave logs a warning if _state_unsub is still set when it shouldn't be (debug safety net)
- Subscribe regardless of controller connectivity — handles reconnect case
- controller and state ObjectProperties defined on each base class (not a separate mixin)
- No abstract cleanup hooks — standard super() pattern for thread teardown in subclasses

### Claude's Discretion
- Exact method signatures and docstrings on base class methods
- Internal implementation details of SetupScreenMixin
- Whether _on_state_change receives the full MachineState or specific changed fields
- Test structure and approach for verifying no behavior change

### Deferred Ideas (OUT OF SCOPE)
- ProfilesScreen wiring to SetupScreenMixin — not in Phase 18 scope
- BCompBarChart move to Serration module — Phase 21
- Base class for ProfilesScreen/UsersScreen — out of scope (already machine-agnostic per REQUIREMENTS.md)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ARCH-01 | Base classes extracted (BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen) with shared controller wiring, poll subscription, and lifecycle hooks | Code audit confirms exact boundaries for extraction from run.py, axes_setup.py, parameters.py |
| ARCH-02 | Base class enforces subscribe-on-enter / unsubscribe-on-leave for state listeners | MachineState.subscribe() returns an unsubscribe callable — base class pattern is straightforward. ParametersScreen already has the pattern; RunScreen has it; both need to move to base |
| ARCH-03 | Per-machine screen classes created (3 types x 3 screens = 9 classes) each with own .kv file | Note: ARCH-03 is listed as Phase 18 in REQUIREMENTS.md but CONTEXT.md explicitly defers class creation to later phases. Phase 18 only creates the base classes. Planner must resolve this discrepancy — likely ARCH-03 is partially addressed (base classes enable it) |
| ARCH-04 | All lifecycle hooks (on_pre_enter, on_enter, on_leave) defined in Python base classes, not in .kv files | Confirmed: no lifecycle hooks currently in any .kv file. Base class hooks must be defined in base.py, not in any .kv |
</phase_requirements>

---

## Summary

Phase 18 is a pure internal refactor: extract shared behavior out of three existing screens into base classes so that future machine-specific screens can inherit it with no additional wiring. The application must run identically before and after — zero user-visible change.

The codebase audit reveals a clear split. RunScreen already does the subscribe/unsubscribe pattern correctly (lines 525-528 and 556-558 of run.py). ParametersScreen does the same (on_pre_enter line 427-430, on_leave lines 441-444). The base class for RunScreen is essentially extracting those six lines plus the two ObjectProperty declarations. AxesSetupScreen does not subscribe to MachineState at all — the base class will add that capability for the first time, but the existing subclass implementation ignores _on_state_change (no override needed to preserve current behavior).

The riskiest operation is the MRO change: existing screens currently inherit from `Screen` directly. After Phase 18 they inherit from `BaseRunScreen(Screen)`, `BaseAxesSetupScreen(Screen, SetupScreenMixin)`, etc. Kivy's Screen class is not abstract and does not use cooperative multiple inheritance in any way that breaks standard Python MRO. The key validation is confirming no behavior change at the application level.

**Primary recommendation:** Write base.py with all three base classes and SetupScreenMixin, move DeltaC widgets to flat_grind_widgets.py, then change the three existing screen class declarations to inherit from the new bases. Validate by running the full test suite and doing a manual smoke test of the enter/leave cycle log output.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| kivy.uix.screenmanager.Screen | 2.2.0+ | Base for all screen classes | Already in use; base classes extend it |
| kivy.properties.ObjectProperty | 2.2.0+ | Typed controller/state injection | Already in use for all three screens |
| kivy.clock.Clock | 2.2.0+ | schedule_once for thread-safe UI updates | Already in use; base wraps subscription callback in it |
| Python stdlib abc | 3.10+ | NOT needed — standard super() pattern chosen | User locked this decision |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| MachineState.subscribe() | project | Returns unsubscribe callable | Base class calls in on_pre_enter, stores in _state_unsub |
| jobs.submit() | project | Background thread pool | Subclasses use for controller I/O; base does not submit directly |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single screens/base.py | One file per base | Three files is cleaner for discovery but user locked single-file |
| abc.ABC + abstractmethod | Standard super() | abc requires all concrete classes to implement abstract methods — adds ceremony, user locked against it |
| Mixin for controller/state | Per-base ObjectProperty | Mixin approach risks diamond MRO complexity; user locked per-base properties |

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended Project Structure
```
src/dmccodegui/screens/
├── base.py              # NEW: BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen, SetupScreenMixin
├── flat_grind_widgets.py # NEW: _BaseBarChart, DeltaCBarChart, DELTA_C_* constants, stone_window_for_index()
├── run.py               # MODIFIED: RunScreen inherits BaseRunScreen; removes moved widgets
├── axes_setup.py        # MODIFIED: AxesSetupScreen inherits BaseAxesSetupScreen + SetupScreenMixin
├── parameters.py        # MODIFIED: ParametersScreen inherits BaseParametersScreen + SetupScreenMixin
└── __init__.py          # MODIFIED: export new base classes
```

### Pattern 1: BaseRunScreen — Thin Subscription Base

**What:** Owns controller/state ObjectProperties plus subscribe-on-enter / unsubscribe-on-leave. Subclasses override _on_state_change().

**When to use:** Any screen that needs live MachineState updates.

**Example:**
```python
# screens/base.py
from kivy.clock import Clock
from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import Screen

class BaseRunScreen(Screen):
    """Base for machine run screens. Owns subscribe/unsubscribe lifecycle."""

    controller = ObjectProperty(None, allownone=True)
    state = ObjectProperty(None, allownone=True)

    _state_unsub = None  # unsubscribe callable from MachineState.subscribe()

    def on_pre_enter(self, *args):
        if self.state is not None:
            self._state_unsub = self.state.subscribe(
                lambda s: Clock.schedule_once(lambda *_: self._on_state_change(s))
            )
            self._on_state_change(self.state)  # apply immediately

    def on_leave(self, *args):
        if self._state_unsub is not None:
            self._state_unsub()
            self._state_unsub = None
        else:
            print(f"[{self.__class__.__name__}] WARNING: on_leave called but _state_unsub was None")

    def _on_state_change(self, state) -> None:
        """Override in subclasses to handle state updates."""
        pass
```

The existing RunScreen then becomes:
```python
class RunScreen(BaseRunScreen):
    # ... all existing code stays, plus:
    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)  # handles subscription
        # ... all existing RunScreen.on_pre_enter logic except the subscribe block

    def on_leave(self, *args):
        # ... all existing cleanup clocks, pollers...
        super().on_leave(*args)  # handles unsubscribe last

    def _on_state_change(self, state):
        self._apply_state(state)  # delegates to existing method
```

### Pattern 2: SetupScreenMixin — Deduplicated Setup Enter/Exit

**What:** Consolidates the duplicated `_SETUP_SCREENS` frozenset and the hmiSetp/hmiExSt guards currently in both axes_setup.py and parameters.py.

**When to use:** Any screen that participates in setup mode (enters setup on arrive, exits setup on leave to non-sibling).

**Key insight from code audit:** The exact same guard pattern appears in both files:
- axes_setup.py lines 192-206: STATE_GRINDING/HOMING check, already_in_setup check, jobs.submit()
- parameters.py lines 411-424: identical structure

The frozenset `_SETUP_SCREENS` is literally duplicated at axes_setup.py:79 and parameters.py:48.

**Example:**
```python
class SetupScreenMixin:
    """Mixin for screens that participate in setup mode."""

    _SETUP_SCREENS: frozenset = frozenset({
        "axes_setup", "parameters", "profiles", "users", "diagnostics",
    })

    def _enter_setup_if_needed(self) -> None:
        """Fire hmiSetp=0 unless already in setup or controller is in motion."""
        from ..hmi.dmc_vars import STATE_GRINDING, STATE_HOMING, STATE_SETUP, HMI_SETP, HMI_TRIGGER_FIRE
        from ..utils import jobs
        if (self.state is not None
                and self.state.dmc_state in (STATE_GRINDING, STATE_HOMING)):
            return
        if self.controller and self.controller.is_connected():
            already_in_setup = (
                self.state is not None
                and self.state.dmc_state == STATE_SETUP
            )
            if not already_in_setup:
                ctrl = self.controller
                jobs.submit(lambda: ctrl.cmd(f"{HMI_SETP}={HMI_TRIGGER_FIRE}"))

    def _exit_setup_if_needed(self) -> None:
        """Fire hmiExSt=0 only when leaving to a non-setup screen."""
        from ..hmi.dmc_vars import HMI_EXIT_SETUP, HMI_TRIGGER_FIRE
        from ..utils import jobs
        next_screen = ""
        if self.manager:
            next_screen = self.manager.current
        if next_screen not in self._SETUP_SCREENS:
            if self.controller and self.controller.is_connected():
                ctrl = self.controller
                jobs.submit(lambda: ctrl.cmd(f"{HMI_EXIT_SETUP}={HMI_TRIGGER_FIRE}"))
```

### Pattern 3: BaseAxesSetupScreen — Jog Infrastructure Inheritance

**What:** Owns the jog_axis(), CPM read pattern, and _enter/_exit_setup lifecycle. Subclasses add axis row visibility and teach point writes for their specific axes.

**Key detail from code audit:** jog_axis() at axes_setup.py:331-413 uses `self._axis_cpm`, `self._current_step_mm`, `self._cpm_ready` — all instance attributes already. No static coupling to axis count. The only coupling to be aware of: `_rebuild_axis_rows()` uses `_AXIS_ROW_IDS` dict which maps axis letters to KV widget ids. This method is machine-specific and belongs in the subclass, not the base.

**MRO for AxesSetupScreen:**
```python
class BaseAxesSetupScreen(Screen, SetupScreenMixin):
    ...

class AxesSetupScreen(BaseAxesSetupScreen):
    ...
```

Python MRO resolves to: AxesSetupScreen -> BaseAxesSetupScreen -> Screen -> SetupScreenMixin -> object. This is valid. The `super()` chain works correctly because Screen does not override `__init_subclass__` in a way that breaks mixin injection.

### Pattern 4: BaseParametersScreen — Card Builder Inheritance

**What:** Owns build_param_cards(), validate_field(), dirty tracking dict, apply_to_controller(), read_from_controller(). All already use mc.get_param_defs() dynamically — no machine-type coupling.

**Key detail from code audit:** parameters.py is the largest extraction. The state subscription in on_pre_enter (line 427-430) and on_leave (lines 441-444) moves to base. The _rebuild_for_machine_type() method stays in parameters.py/subclass since it calls build_param_cards() which is moving to the base — so either _rebuild_for_machine_type also moves to base (preferred), or it calls super().build_param_cards(). Since the user locked that build_param_cards() belongs to the base, _rebuild_for_machine_type should move there too.

### Anti-Patterns to Avoid

- **Defining on_pre_enter in .kv files:** Kivy silently skips on_pre_enter for the first screen loaded via kv (GitHub #2565). User has explicitly locked: all lifecycle hooks in Python only. The existing screens already follow this correctly.
- **Calling unsubscribe twice:** If a subclass also stores _state_unsub and calls it in on_leave before super(), the base on_leave tries to call None. Convention: only base stores/clears _state_unsub. Subclass calls super().on_leave() which handles it.
- **Inheriting from both Screen and another Screen subclass:** Not relevant here, but note that Kivy Screen cannot be multiple-inherited from two Screen subclasses simultaneously.
- **Forgetting to call super() in subclass lifecycle hooks:** The entire value of the base class is lost if RunScreen.on_pre_enter does not call super().on_pre_enter(). Test for this explicitly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Thread-safe UI update from subscription callback | Custom threading.Event / queue | Clock.schedule_once() | Already established pattern; base wraps subscribe callback in schedule_once |
| Abstract method enforcement | Custom decorator or raise NotImplementedError | Standard super() pattern (user locked) | abc adds ceremony; _on_state_change() has a pass default, not abstract |
| Setup screen detection | Per-screen hardcoded set | SetupScreenMixin._SETUP_SCREENS frozenset | Canonical location prevents drift |
| Unsubscribe guard | try/except around call | MachineState.subscribe() already handles remove-on-missing (ValueError caught) | See app_state.py:70-73 |

---

## Common Pitfalls

### Pitfall 1: super() call order in on_leave
**What goes wrong:** Subclass calls super().on_leave() before stopping its own background threads (pos_poll, mg_reader, elapsed clock). The unsubscribe fires while the subscription callback can still fire from ongoing poll notifications, leading to a race where _apply_state runs after the screen is gone.
**Why it happens:** Natural instinct is to call super() first.
**How to avoid:** In RunScreen.on_leave(), stop all clocks and threads first, then call super().on_leave() last. This ensures the subscription is the last thing torn down.
**Warning signs:** AttributeError or NoneType errors in _apply_state after navigation.

### Pitfall 2: _state_unsub ownership ambiguity
**What goes wrong:** Both base and subclass store an _state_unsub attribute. One overwrites the other, leaking a subscription.
**Why it happens:** If RunScreen.on_pre_enter subscribes to MachineState separately (e.g., for a specific callback) AND the base also subscribes, two listeners exist but only one callable is stored.
**How to avoid:** Base owns the single _state_unsub for the _on_state_change dispatch. If subclasses need additional subscriptions (unlikely given the single _on_state_change override), they use differently named attributes (e.g., _extra_unsub) and manage them themselves.
**Warning signs:** After two enter/leave cycles, log shows duplicate callbacks.

### Pitfall 3: MRO call order with SetupScreenMixin
**What goes wrong:** BaseAxesSetupScreen(Screen, SetupScreenMixin) — if SetupScreenMixin defines __init__, Screen.__init__ may not be called correctly.
**Why it happens:** Mixin with __init__ breaks cooperative inheritance unless it calls super().__init__().
**How to avoid:** SetupScreenMixin should NOT define __init__. All state it needs (controller, state, manager) comes from the Screen/base class. The mixin only adds methods.
**Warning signs:** Kivy widget tree not built, ids empty.

### Pitfall 4: Importing from base.py before Kivy environment is initialized
**What goes wrong:** Test files that do `from screens.base import BaseRunScreen` at module level fail because Kivy needs KIVY_NO_ENV_CONFIG before first import.
**Why it happens:** base.py imports from kivy.properties and kivy.uix.screenmanager at module level.
**How to avoid:** Same pattern as all existing tests — set env vars before import, do imports inside test functions.
**Warning signs:** "No module named 'kivy'" or Kivy display initialization errors in test runs.

### Pitfall 5: flat_grind_widgets.py import in run.py breaks if bComp is removed
**What goes wrong:** If run.py imports DeltaCBarChart from flat_grind_widgets.py but BCompBarChart remains in run.py, KV file references to `BCompBarChart` must still resolve. Since BCompBarChart stays in run.py (per locked decision), and KV references it by class name, the Factory registration is via the module that defines it. No action needed — BCompBarChart stays where it is.
**Why it happens:** Kivy Factory registers widget classes by name from whatever module imports them into the Factory namespace (via `from screens import *` in __init__.py or via Builder.load_file triggering class registration).
**How to avoid:** Confirm `from screens.flat_grind_widgets import DeltaCBarChart` in run.py is sufficient for KV to find DeltaCBarChart. It is — Kivy Factory uses the class name, not the module path.
**Warning signs:** `FactoryException: Unknown class <DeltaCBarChart>` at runtime.

---

## Code Examples

Verified from live codebase (not external docs):

### Existing subscribe pattern in RunScreen (to be moved to base)
```python
# run.py lines 525-531 — this block moves to BaseRunScreen.on_pre_enter
if self.state is not None:
    self._state_unsub = self.state.subscribe(
        lambda s: Clock.schedule_once(lambda *_: self._apply_state(s))
    )
    self._apply_state(self.state)
```

After extraction, the base does:
```python
# base.py BaseRunScreen.on_pre_enter
if self.state is not None:
    self._state_unsub = self.state.subscribe(
        lambda s: Clock.schedule_once(lambda *_: self._on_state_change(s))
    )
    self._on_state_change(self.state)
```

And RunScreen._on_state_change delegates:
```python
def _on_state_change(self, state):
    self._apply_state(state)
```

### Existing unsubscribe pattern in RunScreen (to be moved to base)
```python
# run.py lines 556-558 — this block moves to BaseRunScreen.on_leave
if self._state_unsub:
    self._state_unsub()
    self._state_unsub = None
```

After extraction, base adds the warning:
```python
# base.py BaseRunScreen.on_leave
if self._state_unsub is not None:
    self._state_unsub()
    self._state_unsub = None
else:
    print(f"[{self.__class__.__name__}] WARNING: on_leave but _state_unsub was None")
```

### MachineState.subscribe() contract (from app_state.py)
```python
# app_state.py lines 66-75
def subscribe(self, fn: ChangeListener) -> Callable[[], None]:
    self._listeners.append(fn)

    def unsubscribe() -> None:
        try:
            self._listeners.remove(fn)
        except ValueError:
            pass  # already removed — safe to call twice

    return unsubscribe
```

Key fact: unsubscribe is safe to call even if already called (ValueError caught). The base class warning for None _state_unsub is a logic guard, not a crash risk.

### Existing _SETUP_SCREENS duplication (to be consolidated)
```python
# axes_setup.py line 79 — REMOVE after extraction
_SETUP_SCREENS: frozenset[str] = frozenset({
    "axes_setup", "parameters", "profiles", "users", "diagnostics",
})

# parameters.py line 48 — REMOVE after extraction
_SETUP_SCREENS: frozenset = frozenset({
    "axes_setup", "parameters", "profiles", "users", "diagnostics",
})
```

Both move to SetupScreenMixin as a class attribute.

### ObjectProperty injection pattern (main.py — NOT changed)
```python
# main.py lines 114-119 — unchanged by Phase 18
sm = root.ids.sm
for screen in sm.screens:
    if hasattr(screen, 'controller') and hasattr(screen, 'state'):
        screen.controller = self.controller
        screen.state = self.state
```

This works because the base class defines controller and state ObjectProperties — the injection loop finds them correctly on the existing screen names.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Each screen subscribes independently | Base class owns subscribe/unsubscribe | Phase 18 | Subscription leak is impossible if base is used correctly |
| _SETUP_SCREENS duplicated in two files | Single canonical frozenset in SetupScreenMixin | Phase 18 | One place to add new sibling setup screens |
| Flat Grind-specific widgets in run.py | Move to flat_grind_widgets.py | Phase 18 | run.py becomes the FlatGrindRunScreen's file in Phase 19 without surprise dependencies |

**No deprecated APIs involved.** All Kivy APIs in use (ObjectProperty, Screen, Clock.schedule_once) are stable.

---

## Open Questions

1. **ARCH-03 scope in Phase 18**
   - What we know: REQUIREMENTS.md maps ARCH-03 to Phase 18. ARCH-03 says "9 per-machine screen classes created." But CONTEXT.md explicitly limits Phase 18 to base class extraction only — no per-machine class creation.
   - What's unclear: Whether ARCH-03 is partially satisfied by creating the base classes (which enables per-machine classes) or whether it requires the actual subclasses.
   - Recommendation: Treat Phase 18 as addressing ARCH-01, ARCH-02, ARCH-04. ARCH-03 will be addressed across Phases 19-22. The planner should note this scope clarification.

2. **_on_state_change signature — full state or delta**
   - What we know: User left this to discretion. MachineState.subscribe() passes the full state object. Base class wraps with schedule_once.
   - What's unclear: Whether to pass (state) or (self, state) or add **kwargs for future extensibility.
   - Recommendation: Use `def _on_state_change(self, state: MachineState) -> None` — simple, consistent with existing _apply_state(s) signatures throughout run.py.

3. **AxesSetupScreen does not currently subscribe to MachineState**
   - What we know: AxesSetupScreen has no _state_unsub, no subscribe() call. It reads dmc_state from self.state directly when needed (e.g., in on_pre_enter guard at line 192).
   - What's unclear: Does adding a subscription via BaseAxesSetupScreen risk any side effects? The default _on_state_change() is a no-op, so no — adding a subscription with a no-op callback is safe.
   - Recommendation: Base subscribes unconditionally. AxesSetupScreen does not override _on_state_change. No behavior change.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (from pyproject.toml [tool.pytest.ini_options]) |
| Config file | pyproject.toml |
| Quick run command | `pytest tests/test_base_classes.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARCH-01 | BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen importable; existing screens inherit from them | unit | `pytest tests/test_base_classes.py::test_base_class_inheritance -x` | ❌ Wave 0 |
| ARCH-02 | Subscribe on enter, unsubscribe on leave; zero duplicate callbacks after two cycles | unit | `pytest tests/test_base_classes.py::test_subscription_lifecycle -x` | ❌ Wave 0 |
| ARCH-03 | (deferred — see Open Questions) | N/A | N/A | N/A |
| ARCH-04 | No on_pre_enter/on_enter/on_leave defined in any .kv file | static | `pytest tests/test_base_classes.py::test_no_lifecycle_in_kv -x` | ❌ Wave 0 |

Additional regression tests needed:
| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| RunScreen still functions (subscribe fires, _apply_state called) | unit | `pytest tests/test_run_screen.py -x` | ✅ (existing) |
| AxesSetupScreen still functions (jog, teach, mode toggle) | unit | `pytest tests/test_axes_setup.py -x` | ✅ (existing) |
| ParametersScreen still functions (validate, dirty tracking, apply) | unit | `pytest tests/test_parameters.py -x` | ✅ (existing) |
| DeltaCBarChart importable from flat_grind_widgets | unit | `pytest tests/test_flat_grind_widgets.py -x` | ❌ Wave 0 |
| run.py can still import DeltaCBarChart after move | unit | part of test_run_screen.py | needs update |

### Sampling Rate
- **Per task commit:** `pytest tests/test_base_classes.py tests/test_run_screen.py tests/test_axes_setup.py tests/test_parameters.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_base_classes.py` — covers ARCH-01, ARCH-02, ARCH-04 and subscription lifecycle
- [ ] `tests/test_flat_grind_widgets.py` — covers DeltaCBarChart import after move to flat_grind_widgets.py
- [ ] `tests/test_axes_setup.py` needs update — import path for DeltaCBarChart may be referenced indirectly

*(Existing test infrastructure: pytest + pyproject.toml configuration already present. No framework install needed.)*

---

## Sources

### Primary (HIGH confidence)
- Live codebase: `src/dmccodegui/screens/run.py` — RunScreen lifecycle, subscribe/unsubscribe, widget structure
- Live codebase: `src/dmccodegui/screens/axes_setup.py` — AxesSetupScreen lifecycle, jog infrastructure, _SETUP_SCREENS
- Live codebase: `src/dmccodegui/screens/parameters.py` — ParametersScreen lifecycle, build_param_cards, dirty tracking, _SETUP_SCREENS
- Live codebase: `src/dmccodegui/app_state.py` — MachineState.subscribe() contract, unsubscribe safety
- Live codebase: `src/dmccodegui/main.py` — ObjectProperty injection pattern, KV loading order
- Live codebase: `src/dmccodegui/screens/__init__.py` — current exports
- Live codebase: `tests/` — existing test patterns (env setup, mock strategy)
- `.planning/phases/18-base-class-extraction/18-CONTEXT.md` — locked user decisions

### Secondary (MEDIUM confidence)
- Python MRO documentation — cooperative multiple inheritance with mixins is standard Python, no external verification needed for this use case

### Tertiary (LOW confidence)
- Kivy GitHub #2565 (on_pre_enter silently skips for first kv-loaded screen) — referenced in STATE.md critical pitfalls; not independently verified in this research session, but already incorporated into locked decisions

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all from live codebase, no new libraries introduced
- Architecture: HIGH — extract boundaries confirmed by reading all three screen files
- Pitfalls: HIGH — most derived from reading existing code patterns and STATE.md accumulated pitfalls

**Research date:** 2026-04-11
**Valid until:** This research reflects the codebase as of Phase 17 completion. Valid until any of run.py, axes_setup.py, or parameters.py are modified.
