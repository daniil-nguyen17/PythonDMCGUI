"""Base screen classes for DMC Code GUI.

Provides shared controller wiring, MachineState subscription lifecycle, and
setup-mode entry/exit logic used by all machine screen sets.

Classes
-------
SetupScreenMixin
    Mixin for screens that participate in setup mode. Owns the canonical
    _SETUP_SCREENS frozenset and the enter/exit guard methods.

BaseRunScreen
    Thin base for run/operator screens. Owns controller/state ObjectProperties
    and the subscribe-on-enter / unsubscribe-on-leave lifecycle. Subclasses
    override _on_state_change(state).

BaseAxesSetupScreen
    Base for axes-setup screens. Includes jog infrastructure (jog_axis, CPM
    read pattern) plus SetupScreenMixin lifecycle. Subclasses add axis row
    visibility and teach-point writes for their specific machine type.

BaseParametersScreen
    Base for parameter-editor screens. Includes card builder, dirty tracking,
    validate_field, apply_to_controller, read_from_controller, and
    _rebuild_for_machine_type. All methods use mc.get_param_defs() dynamically.

Design notes
------------
- All lifecycle hooks (on_pre_enter, on_leave) are defined here in Python, never
  in .kv files. See Kivy GitHub #2565 — on_pre_enter silently skips for the first
  screen added via kv.
- SetupScreenMixin has NO __init__ to avoid cooperative MRO issues (Pitfall #3).
- controller and state ObjectProperties are defined per base class (not a separate
  mixin) to avoid diamond MRO complexity.
- _state_unsub is owned exclusively by the base. Subclasses must NOT store their
  own _state_unsub; use differently-named attributes for additional subscriptions.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from kivy.clock import Clock
from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import Screen

try:
    import matplotlib.pyplot as plt  # noqa: F401 — used in BaseRunScreen.cleanup()
except ImportError:  # pragma: no cover
    plt = None  # type: ignore[assignment]

import dmccodegui.machine_config as mc
from dmccodegui.utils.jobs import submit  # noqa: F401 — re-exported for test patching

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SetupScreenMixin
# ---------------------------------------------------------------------------

class SetupScreenMixin:
    """Mixin for screens that participate in setup mode.

    Owns the canonical _SETUP_SCREENS frozenset so the definition is never
    duplicated across axes_setup.py and parameters.py.

    Both guard methods use lazy imports so this mixin can be imported before
    Kivy environment initialisation (e.g. in tests).

    This mixin intentionally has NO __init__ — all state it needs (controller,
    state, manager) comes from the base Screen class.
    """

    _SETUP_SCREENS: frozenset = frozenset({
        "axes_setup", "parameters", "profiles", "users", "diagnostics",
    })

    def _enter_setup_if_needed(self) -> None:
        """Fire hmiSetp=0 unless already in setup or the controller is in motion.

        Guards:
          1. Skip if STATE_GRINDING or STATE_HOMING.
          2. Skip if already in STATE_SETUP (sibling-screen navigation).
          3. Skip if controller not connected.
        """
        from ..hmi.dmc_vars import (  # noqa: PLC0415
            STATE_GRINDING, STATE_HOMING, STATE_SETUP,
            HMI_SETP, HMI_TRIGGER_FIRE,
        )

        if (self.state is not None  # type: ignore[attr-defined]
                and self.state.dmc_state in (STATE_GRINDING, STATE_HOMING)):  # type: ignore[attr-defined]
            return

        if self.controller and self.controller.is_connected():  # type: ignore[attr-defined]
            already_in_setup = (
                self.state is not None  # type: ignore[attr-defined]
                and self.state.dmc_state == STATE_SETUP  # type: ignore[attr-defined]
            )
            if not already_in_setup:
                ctrl = self.controller  # type: ignore[attr-defined]
                submit(lambda: ctrl.cmd(f"{HMI_SETP}={HMI_TRIGGER_FIRE}"))

    def _exit_setup_if_needed(self) -> None:
        """Fire hmiExSt=0 only when leaving to a non-setup screen.

        Navigating between setup siblings (axes_setup <-> parameters) does NOT
        fire exit-setup — the controller stays in STATE_SETUP the whole time.
        """
        from ..hmi.dmc_vars import HMI_EXIT_SETUP, HMI_TRIGGER_FIRE  # noqa: PLC0415

        next_screen = ""
        if self.manager:  # type: ignore[attr-defined]
            next_screen = self.manager.current  # type: ignore[attr-defined]

        if next_screen not in self._SETUP_SCREENS:
            if self.controller and self.controller.is_connected():  # type: ignore[attr-defined]
                ctrl = self.controller  # type: ignore[attr-defined]
                submit(lambda: ctrl.cmd(f"{HMI_EXIT_SETUP}={HMI_TRIGGER_FIRE}"))


# ---------------------------------------------------------------------------
# BaseRunScreen
# ---------------------------------------------------------------------------

class BaseRunScreen(Screen):
    """Base for machine run screens.

    Owns:
    - controller / state ObjectProperties (injected by main.py)
    - MachineState subscribe-on-enter / unsubscribe-on-leave lifecycle
    - _on_state_change dispatch (override in subclasses)

    Does NOT own:
    - pos_poll, mg_reader, matplotlib, deltaC/bComp, or cycle controls
    - SetupScreenMixin (run screens do not enter setup mode)
    """

    controller = ObjectProperty(None, allownone=True)
    state = ObjectProperty(None, allownone=True)

    _state_unsub: Optional[Callable[[], None]] = None

    def on_pre_enter(self, *args) -> None:
        """Subscribe to MachineState and apply current state immediately."""
        if self.state is not None:
            self._state_unsub = self.state.subscribe(
                lambda s: Clock.schedule_once(lambda *_: self._on_state_change(s))
            )
            self._on_state_change(self.state)

    def on_leave(self, *args) -> None:
        """Unsubscribe from MachineState."""
        if self._state_unsub is not None:
            self._state_unsub()
            self._state_unsub = None
        else:
            logger.warning(
                "[%s] on_leave called but _state_unsub was None — possible double-leave",
                self.__class__.__name__,
            )

    def _on_state_change(self, state) -> None:
        """Called on every MachineState update. Override in subclasses."""
        pass

    def cleanup(self) -> None:
        """Tear down all resources owned by this run screen. Non-blocking and idempotent.

        Teardown order (locked):
        1. Stop position poll (cancel Clock interval).
        2. Signal mg_reader thread to stop — set event only, do NOT join.
        3. Close matplotlib figure.
        4. Unsubscribe from MachineState.

        Called by the screen loader on programmatic screen removal (Phase 20 swap).
        The existing _stop_mg_reader() on on_leave keeps its join for normal navigation.
        """
        # 1. Stop position poll
        if hasattr(self, '_stop_pos_poll'):
            logger.info("[%s] cleanup: stopping pos_poll", self.__class__.__name__)
            self._stop_pos_poll()

        # 2. Signal mg_reader thread — set event, clear reference, do NOT join
        if getattr(self, '_mg_stop_event', None) is not None:
            logger.info("[%s] cleanup: signalling mg_stop_event", self.__class__.__name__)
            self._mg_stop_event.set()
        self._mg_thread = None  # type: ignore[attr-defined]

        # 3. Close matplotlib figure
        fig = getattr(self, '_fig', None)
        if fig is not None:
            logger.info("[%s] cleanup: closing matplotlib figure", self.__class__.__name__)
            if plt is not None:
                plt.close(fig)
            self._fig = None  # type: ignore[attr-defined]

        # 4. Unsubscribe from MachineState
        if self._state_unsub is not None:
            logger.info("[%s] cleanup: unsubscribing state listener", self.__class__.__name__)
            self._state_unsub()
            self._state_unsub = None


# ---------------------------------------------------------------------------
# BaseAxesSetupScreen
# ---------------------------------------------------------------------------

class BaseAxesSetupScreen(Screen, SetupScreenMixin):
    """Base for axes-setup screens.

    Owns:
    - controller / state ObjectProperties
    - subscribe-on-enter / unsubscribe-on-leave lifecycle (delegates to
      SetupScreenMixin for setup enter/exit)
    - jog_axis() with axis_list from machine_config
    - CPM read pattern (_read_cpm_for_axis, _schedule_cpm_read)
    - _on_state_change dispatch (override in subclasses)

    Does NOT own:
    - _rebuild_axis_rows() or _AXIS_ROW_IDS — machine-specific (subclass)
    """

    controller = ObjectProperty(None, allownone=True)
    state = ObjectProperty(None, allownone=True)

    _state_unsub: Optional[Callable[[], None]] = None

    # Jog infrastructure — instance attributes initialised in __init__
    # so each instance has its own dict (not shared at class level).
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._axis_cpm: dict[str, float] = {}
        self._cpm_ready: bool = False
        self._current_step_mm: float = 10.0

    def on_pre_enter(self, *args) -> None:
        """Subscribe to MachineState and enter setup mode."""
        if self.state is not None:
            self._state_unsub = self.state.subscribe(
                lambda s: Clock.schedule_once(lambda *_: self._on_state_change(s))
            )
            self._on_state_change(self.state)
        self._enter_setup_if_needed()

    def on_leave(self, *args) -> None:
        """Exit setup mode and unsubscribe from MachineState."""
        self._exit_setup_if_needed()
        if self._state_unsub is not None:
            self._state_unsub()
            self._state_unsub = None
        else:
            logger.warning(
                "[%s] on_leave called but _state_unsub was None",
                self.__class__.__name__,
            )

    def _on_state_change(self, state) -> None:
        """Called on every MachineState update. Override in subclasses."""
        pass

    def cleanup(self) -> None:
        """Tear down resources owned by this axes-setup screen. Idempotent.

        Unsubscribes the MachineState listener. Called by the screen loader
        on programmatic screen removal (Phase 20 swap).
        """
        if self._state_unsub is not None:
            logger.info("[%s] cleanup: unsubscribing state listener", self.__class__.__name__)
            self._state_unsub()
            self._state_unsub = None

    # ------------------------------------------------------------------
    # Jog infrastructure
    # ------------------------------------------------------------------

    def jog_axis(self, axis: str, direction: int) -> None:
        """Jog the given axis by (direction * _current_step_mm * cpm) counts.

        Uses PR (Position Relative) + BG per axis so only the target axis moves.
        Commands: "PR{axis}={counts}" then "BG{axis}".
        Both commands are sent in one background job to keep them sequential.

        Gates (in order):
          1. Controller connected
          2. dmc_state == STATE_SETUP
          3. _cpm_ready (CPM read from controller)
          4. cpm > 0 for the axis
          5. _BG{axis} == 0 (no jog in progress) — checked inside do_jog()

        Validates axis against mc.get_axis_list() so Serration (3-axis) and
        Convex (4-axis) machines automatically block invalid axes.
        """
        import dmccodegui.machine_config as mc  # noqa: PLC0415

        if not self.controller or not self.controller.is_connected():
            logger.debug(
                "[%s] Jog %s blocked — controller not connected",
                self.__class__.__name__, axis,
            )
            return

        from ..hmi.dmc_vars import STATE_SETUP  # noqa: PLC0415
        if not self.state or getattr(self.state, 'dmc_state', None) != STATE_SETUP:
            logger.debug(
                "[%s] Jog %s blocked — dmc_state != STATE_SETUP",
                self.__class__.__name__, axis,
            )
            return

        try:
            axis_list = mc.get_axis_list()
        except ValueError:
            axis_list = ["A", "B", "C", "D"]

        if axis not in axis_list:
            logger.debug(
                "[%s] Jog %s blocked — axis not in axis_list %s",
                self.__class__.__name__, axis, axis_list,
            )
            return

        if not self._cpm_ready:
            logger.debug("[%s] Jog blocked — CPM not yet read", self.__class__.__name__)
            return

        cpm = self._axis_cpm.get(axis, 0.0)
        if cpm <= 0:
            logger.debug(
                "[%s] Jog blocked — no CPM value for axis %s, _axis_cpm=%s",
                self.__class__.__name__, axis, self._axis_cpm,
            )
            return

        counts = int(direction * self._current_step_mm * cpm)
        logger.debug(
            "[%s] Jog %s: step=%s * cpm=%s = %s counts",
            self.__class__.__name__, axis, self._current_step_mm, cpm, counts,
        )
        ctrl = self.controller
        lbl_id = f"pos_{axis.lower()}"

        def _push_pos(val_str: str) -> None:
            def _update(*_):
                if hasattr(self, 'pos_current'):
                    self.pos_current[axis] = val_str  # type: ignore[attr-defined]
                lbl = self.ids.get(lbl_id)
                if lbl:
                    lbl.text = val_str
            Clock.schedule_once(_update)

        def do_jog():
            import time  # noqa: PLC0415
            try:
                # In-progress gate: skip if previous jog still running
                try:
                    raw = ctrl.cmd(f"MG _BG{axis}").strip()
                    if float(raw) != 0:
                        return
                except Exception:
                    return

                ctrl.cmd(f"PR{axis}={counts}")
                ctrl.cmd(f"BG{axis}")

                # Poll position live while axis is moving
                for _ in range(60):
                    time.sleep(0.1)
                    try:
                        raw = ctrl.cmd(f"MG _TD{axis}").strip()
                        _push_pos(f"{float(raw):.1f}")
                    except Exception:
                        pass
                    try:
                        bg_raw = ctrl.cmd(f"MG _BG{axis}").strip()
                        if float(bg_raw) == 0:
                            break
                    except Exception:
                        break

                # Final position read
                raw = ctrl.cmd(f"MG _TD{axis}").strip()
                final_val = f"{float(raw):.1f}"
                _push_pos(final_val)
                Clock.schedule_once(
                    lambda *_, a=axis, c=counts, v=final_val: self._log_jog(a, c, v)
                )
            except Exception as exc:
                Clock.schedule_once(lambda *_, err=exc: self._log_jog_error(err))

        submit(do_jog)

    def _log_jog(self, axis: str, counts: int, final_pos: str) -> None:
        """Log a completed jog. Subclasses can override to write to a cmd log widget."""
        logger.info("[%s] JOG %s: %+d cts -> %s", self.__class__.__name__, axis, counts, final_pos)

    def _log_jog_error(self, exc: Exception) -> None:
        """Log a jog error. Subclasses can override to surface in a cmd log widget."""
        logger.error("[%s] JOG ERROR: %s", self.__class__.__name__, exc)

    def _schedule_cpm_read(self) -> None:
        """Schedule a CPM read from the controller for all axes.

        Safe to call from the main thread — posts to the background job queue.
        Sets _cpm_ready=True on success (even if some axes fail).
        """
        submit(self._read_cpm_for_axis)

    def _read_cpm_for_axis(self) -> None:
        """Background job: read cpm{axis} from controller for all 4 axes.

        Only axes with a successful, positive read get a CPM entry.
        Sets _cpm_ready=True once the read attempt completes (regardless of
        how many axes succeeded).
        """
        ctrl = self.controller
        if not ctrl or not ctrl.is_connected():
            return

        cpm_updates: dict[str, float] = {}
        for axis in ("A", "B", "C", "D"):
            try:
                raw = ctrl.cmd(f"MG cpm{axis}").strip()
                val = float(raw)
                if val > 0:
                    cpm_updates[axis] = val
                else:
                    logger.debug(
                        "[%s] CPM %s returned %s (not positive), jog blocked for this axis",
                        self.__class__.__name__, axis, val,
                    )
            except Exception as exc:
                logger.debug(
                    "[%s] CPM %s read failed: %s", self.__class__.__name__, axis, exc
                )

        logger.debug("[%s] CPM values from controller: %s", self.__class__.__name__, cpm_updates)

        def _apply(*_):
            self._axis_cpm.update(cpm_updates)
            self._cpm_ready = True

        Clock.schedule_once(_apply)


# ---------------------------------------------------------------------------
# BaseParametersScreen
# ---------------------------------------------------------------------------

class BaseParametersScreen(Screen, SetupScreenMixin):
    """Base for parameter-editor screens.

    Owns:
    - controller / state ObjectProperties
    - subscribe-on-enter / unsubscribe-on-leave lifecycle (delegates to
      SetupScreenMixin for setup enter/exit)
    - build_param_cards() — reads mc.get_param_defs() dynamically
    - validate_field() — validation against param def min/max/group rules
    - dirty tracking (_dirty dict, _mark_dirty, _clear_dirty, _has_dirty)
    - apply_to_controller() and read_from_controller()
    - _rebuild_for_machine_type() — rebuilds cards and state for hot-swap
    - _on_state_change dispatch (override in subclasses)
    """

    controller = ObjectProperty(None, allownone=True)
    state = ObjectProperty(None, allownone=True)

    _state_unsub: Optional[Callable[[], None]] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Param defs dict -- keyed by var name.
        # Initialised to Flat Grind defaults so validation works immediately
        # (e.g. in tests that create a screen without calling on_pre_enter).
        try:
            param_defs = mc.get_param_defs()
        except (ValueError, Exception):
            from dmccodegui.machine_config import _FLAT_PARAM_DEFS  # noqa: PLC0415
            param_defs = _FLAT_PARAM_DEFS
        self._param_defs: dict[str, dict] = {p["var"]: p for p in param_defs}
        # Last known controller values {var_name: float}
        self._controller_vals: dict[str, float] = {}
        # User-edited strings not yet applied {var_name: str}
        self._dirty: dict[str, str] = {}
        # Widget refs for border color updates {var_name: widget_ref}
        self._field_widgets: dict[str, object] = {}

    def on_pre_enter(self, *args) -> None:
        """Rebuild cards, subscribe to state, and enter setup mode."""
        self._rebuild_for_machine_type()

        if self.state is not None:
            self._state_unsub = self.state.subscribe(
                lambda s: Clock.schedule_once(lambda *_: self._on_state_change(s))
            )
            self._on_state_change(self.state)

        self._enter_setup_if_needed()

    def on_leave(self, *args) -> None:
        """Exit setup mode and unsubscribe from MachineState."""
        self._exit_setup_if_needed()
        if self._state_unsub is not None:
            self._state_unsub()
            self._state_unsub = None
        else:
            logger.warning(
                "[%s] on_leave called but _state_unsub was None",
                self.__class__.__name__,
            )

    def _on_state_change(self, state) -> None:
        """Called on every MachineState update. Override in subclasses."""
        pass

    def cleanup(self) -> None:
        """Tear down resources owned by this parameters screen. Idempotent.

        Unsubscribes the MachineState listener. Called by the screen loader
        on programmatic screen removal (Phase 20 swap).
        """
        if self._state_unsub is not None:
            logger.info("[%s] cleanup: unsubscribing state listener", self.__class__.__name__)
            self._state_unsub()
            self._state_unsub = None

    # ------------------------------------------------------------------
    # Dirty tracking
    # ------------------------------------------------------------------

    def _mark_dirty(self, var_name: str, text: str) -> None:
        """Mark a parameter as dirty (user-modified, not yet applied)."""
        self._dirty[var_name] = text

    def _clear_dirty(self, var_name: str | None = None) -> None:
        """Clear dirty state. Pass var_name to clear one param; None to clear all."""
        if var_name is None:
            self._dirty.clear()
        else:
            self._dirty.pop(var_name, None)

    def _has_dirty(self) -> bool:
        """Return True if any parameter has unsaved edits."""
        return bool(self._dirty)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    # Groups that reject zero values (calibration params)
    _ZERO_REJECT_GROUPS = frozenset({"Calibration"})
    # Groups that reject negative values
    _NEGATIVE_REJECT_GROUPS = frozenset({"Feedrates", "Calibration"})

    def validate_field(self, var_name: str, text: str) -> str:
        """Validate a text entry for the named parameter.

        Returns:
            'error'    -- non-numeric, out of range, or special rule violation
            'modified' -- valid numeric value that differs from controller value
            'valid'    -- valid numeric value matching controller value
        """
        param = self._param_defs.get(var_name)
        if param is None:
            return 'error'

        try:
            value = float(text)
        except (ValueError, TypeError):
            return 'error'

        if param['group'] in self._ZERO_REJECT_GROUPS and value == 0.0:
            return 'error'

        if param['group'] in self._NEGATIVE_REJECT_GROUPS and value < 0:
            return 'error'

        if not (param['min'] <= value <= param['max']):
            return 'error'

        ctrl_val = self._controller_vals.get(var_name)
        if ctrl_val is not None and abs(value - ctrl_val) < 1e-9:
            return 'valid'

        return 'modified'

    # ------------------------------------------------------------------
    # Machine type rebuild
    # ------------------------------------------------------------------

    def _rebuild_for_machine_type(self) -> None:
        """Rebuild parameter cards for the current active machine type.

        Clears and rebuilds all state that depends on PARAM_DEFS so that
        hot-swapping machine type and entering this screen shows the correct
        parameters.

        Called at the start of on_pre_enter.
        """
        try:
            param_defs = mc.get_param_defs()
        except ValueError:
            return  # machine_config not configured — keep existing state

        self._param_defs = {p["var"]: p for p in param_defs}
        self._field_widgets.clear()
        self._dirty.clear()

        self.build_param_cards()

    # ------------------------------------------------------------------
    # Card builder
    # ------------------------------------------------------------------

    def build_param_cards(self) -> None:
        """Build grouped parameter cards dynamically in the cards_container.

        Reads from mc.get_param_defs() to get the current machine type's params.
        Clears the container before rebuilding to handle hot-swap without duplicates.
        """
        from collections import OrderedDict  # noqa: PLC0415

        # Group accent colors — consistent across all machine types
        GROUP_COLORS: dict[str, list[float]] = {
            "Geometry":    [0.980, 0.569, 0.043, 1],
            "Feedrates":   [0.024, 0.714, 0.831, 1],
            "Calibration": [0.659, 0.333, 0.965, 1],
        }

        # Border color constants
        BORDER_NORMAL = [0.118, 0.145, 0.188, 1]

        try:
            container = self.ids.get('cards_container')
        except Exception:
            container = None

        if container is None:
            return

        try:
            param_defs = mc.get_param_defs()
        except ValueError:
            param_defs = []

        from kivy.graphics import Color, RoundedRectangle, Rectangle  # noqa: PLC0415
        from kivy.uix.boxlayout import BoxLayout  # noqa: PLC0415
        from kivy.uix.label import Label  # noqa: PLC0415
        from kivy.uix.textinput import TextInput  # noqa: PLC0415
        from kivy.uix.widget import Widget  # noqa: PLC0415

        groups: OrderedDict[str, list] = OrderedDict()
        for p in param_defs:
            groups.setdefault(p['group'], []).append(p)

        container.clear_widgets()
        self._field_widgets.clear()

        for group_name, params in groups.items():
            accent = GROUP_COLORS.get(group_name, [0.5, 0.5, 0.5, 1])

            card_wrapper = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                spacing=0,
            )
            card_wrapper.bind(minimum_height=card_wrapper.setter('height'))

            stripe = Widget(size_hint_x=None, width=6, size_hint_y=1)
            with stripe.canvas.before:
                Color(rgba=accent)
                _rect = RoundedRectangle(pos=stripe.pos, size=stripe.size, radius=[3, 0, 0, 3])
            stripe.bind(pos=lambda w, v, r=_rect: setattr(r, 'pos', v))
            stripe.bind(size=lambda w, v, r=_rect: setattr(r, 'size', v))
            card_wrapper.add_widget(stripe)

            card = BoxLayout(
                orientation='vertical',
                padding=[12, 12, 12, 12],
                spacing=6,
                size_hint_y=None,
            )
            card.bind(minimum_height=card.setter('height'))

            with card.canvas.before:
                Color(rgba=[0.051, 0.071, 0.102, 1])
                _bg = Rectangle(pos=card.pos, size=card.size)
            card.bind(pos=lambda w, v, r=_bg: setattr(r, 'pos', v))
            card.bind(size=lambda w, v, r=_bg: setattr(r, 'size', v))

            header = Label(
                text=group_name,
                font_size='22sp',
                bold=True,
                size_hint_y=None,
                height=40,
                halign='left',
                valign='middle',
                color=accent,
            )
            header.bind(size=header.setter('text_size'))
            card.add_widget(header)

            for p in params:
                row = BoxLayout(
                    orientation='horizontal',
                    size_hint_y=None,
                    height=48,
                    spacing=4,
                )

                lbl = Label(
                    text=p['label'],
                    font_size='18sp',
                    size_hint_x=0.35,
                    halign='left',
                    valign='middle',
                )
                lbl.bind(size=lbl.setter('text_size'))
                row.add_widget(lbl)

                var_lbl = Label(
                    text=p['var'],
                    font_size='16sp',
                    size_hint_x=0.15,
                    halign='center',
                    valign='middle',
                    color=[accent[0], accent[1], accent[2], 0.6],
                )
                var_lbl.bind(size=var_lbl.setter('text_size'))
                row.add_widget(var_lbl)

                ti = TextInput(
                    text='',
                    multiline=False,
                    size_hint_x=0.35,
                    font_size='18sp',
                    halign='center',
                )
                var_name = p['var']
                ti.bind(text=lambda widget, text, v=var_name: self.on_field_text_change(v, text))
                self._field_widgets[var_name] = ti
                row.add_widget(ti)

                unit_lbl = Label(
                    text=p['unit'],
                    font_size='16sp',
                    size_hint_x=0.15,
                    halign='right',
                    valign='middle',
                )
                unit_lbl.bind(size=unit_lbl.setter('text_size'))
                row.add_widget(unit_lbl)

                card.add_widget(row)

            card_wrapper.add_widget(card)
            container.add_widget(card_wrapper)

    def on_field_text_change(self, var_name: str, text: str) -> None:
        """Called by KV on_text bindings when a field value changes."""
        if getattr(self, '_loading', False):
            return

        state = self.validate_field(var_name, text)
        widget = self._field_widgets.get(var_name)
        if widget is not None:
            self._set_field_state(widget, state)

        if state == 'modified':
            self._mark_dirty(var_name, text)
        else:
            self._clear_dirty(var_name)

    def _set_field_state(self, widget, state: str) -> None:
        """Update the border color of a TextInput widget based on validation state."""
        BORDER_NORMAL = [0.118, 0.145, 0.188, 1]
        BORDER_AMBER = [0.980, 0.749, 0.043, 0.9]
        BORDER_RED = [0.900, 0.200, 0.200, 0.9]
        try:
            if state == 'error':
                color = BORDER_RED
            elif state == 'modified':
                color = BORDER_AMBER
            else:
                color = BORDER_NORMAL

            if hasattr(widget, '_border_color_instruction'):
                widget._border_color_instruction.rgba = color
            widget._param_state = state
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Apply to controller
    # ------------------------------------------------------------------

    def apply_to_controller(self) -> None:
        """Send all dirty parameters to controller, read back, then burn NV."""
        import time  # noqa: PLC0415
        from dmccodegui.hmi.dmc_vars import (  # noqa: PLC0415
            HMI_CALC, HMI_TRIGGER_FIRE, STATE_GRINDING, STATE_HOMING,
        )

        if not self._dirty:
            return
        if self.controller is None or not self.controller.is_connected():
            return
        if self.state is not None:
            motion_active = (
                not self.state.connected
                or self.state.dmc_state in (STATE_GRINDING, STATE_HOMING)
            )
            if motion_active:
                return

        dirty_snapshot = dict(self._dirty)
        param_defs_snapshot = mc.get_param_defs()

        def _job():
            ctrl = self.controller
            if ctrl is None:
                return

            for var_name, text in dirty_snapshot.items():
                try:
                    ctrl.cmd(f"{var_name}={text}")
                except Exception:
                    pass

            try:
                ctrl.cmd(f"{HMI_CALC}={HMI_TRIGGER_FIRE}")
            except Exception:
                pass

            time.sleep(0.5)

            new_vals: dict[str, float] = {}
            for p in param_defs_snapshot:
                var = p['var']
                try:
                    raw = ctrl.cmd(f"MG {var}")
                    new_vals[var] = float(raw.strip())
                except Exception:
                    pass

            try:
                ctrl.cmd("BV")
            except Exception:
                pass

            def _update_ui(*_args):
                self._controller_vals.update(new_vals)
                self._dirty.clear()
                if hasattr(self, 'pending_count'):
                    self.pending_count = 0  # type: ignore[attr-defined]
                for vname, widget in self._field_widgets.items():
                    self._set_field_state(widget, 'valid')

            Clock.schedule_once(_update_ui)

        submit(_job)

    # ------------------------------------------------------------------
    # Read from controller
    # ------------------------------------------------------------------

    def read_from_controller(self) -> None:
        """Refresh all parameter values from the controller.

        Reads only the vars defined for the active machine type.
        """

        if self.controller is None:
            return

        if not mc.is_configured():
            return

        param_defs_snapshot = mc.get_param_defs()

        def _job():
            ctrl = self.controller
            if ctrl is None:
                return

            new_vals: dict[str, float] = {}
            for p in param_defs_snapshot:
                var = p['var']
                try:
                    raw = ctrl.cmd(f"MG {var}")
                    new_vals[var] = float(raw.strip())
                except Exception:
                    pass

            def _update_ui(*_args):
                loading_was = getattr(self, '_loading', False)
                try:
                    if hasattr(self, '_loading'):
                        self._loading = True  # type: ignore[attr-defined]
                    self._controller_vals.update(new_vals)
                    for var_name, widget in self._field_widgets.items():
                        val = new_vals.get(var_name)
                        if val is not None and hasattr(widget, 'text'):
                            widget.text = str(val)
                    self._dirty.clear()
                    if hasattr(self, 'pending_count'):
                        self.pending_count = 0  # type: ignore[attr-defined]
                    for var_name, widget in self._field_widgets.items():
                        self._set_field_state(widget, 'valid')
                finally:
                    if hasattr(self, '_loading'):
                        self._loading = loading_was  # type: ignore[attr-defined]

            Clock.schedule_once(_update_ui)

        submit(_job)
