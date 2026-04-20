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
from dmccodegui.theme_manager import theme  # noqa: F401 — used in build_param_cards
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

    # ------------------------------------------------------------------
    # App-wide poller helpers
    # ------------------------------------------------------------------
    # Setup pages do NOT need the 10 Hz centralized poll — jog_axis() polls
    # _TD{axis} live while BG is active (see BaseAxesSetupScreen.jog_axis),
    # DR streaming uses UDP — no TCP contention with setup commands.
    # These are kept as no-ops to preserve call sites in setup/parameter screens.
    def _stop_app_poller(self) -> None:
        pass  # DR uses UDP — no TCP contention, no need to stop

    def _start_app_poller(self) -> None:
        pass  # DR listener runs continuously

    def _apply_dmc_state(self, dmc_state: int) -> None:
        """Main thread: write dmc_state into MachineState.

        While the app-wide poller is stopped (during setup), the mixin is the
        only writer of state.dmc_state. This must be called after any direct
        MG hmiState read so the jog gate (dmc_state == STATE_SETUP) unblocks.
        """
        if self.state is not None:  # type: ignore[attr-defined]
            self.state.dmc_state = dmc_state  # type: ignore[attr-defined]
            self.state.notify()  # type: ignore[attr-defined]

    def _enter_setup_if_needed(self) -> None:
        """Stop app-wide poller, optimistically enter setup, then confirm via fresh read.

        Main-thread work (synchronous, happens before screen is fully visible):
          1. Stop the 10 Hz centralized poller (idempotent).
          2. If cached state is NOT a motion state (GRINDING/HOMING), optimistically
             set state.dmc_state = STATE_SETUP so the jog gate in BaseAxesSetupScreen
             doesn't silently block the first click. The background job below will
             correct it if reality differs.

        Background-thread work (runs via jobs.submit):
          3. Fresh-read MG hmiState — stale MachineState cannot be trusted here.
          4. If STATE_GRINDING/HOMING, warn, push the REAL state back (un-do the
             optimistic setup so jog is re-blocked), return.
          5. If not already STATE_SETUP, fire hmiSetp=0, sleep briefly, re-read
             to confirm the transition.
          6. Push the confirmed state to MachineState on main thread.

        Race we're fixing: without the optimistic main-thread set, users could
        click a jog button within ~100-200 ms of entering the screen and have
        it silently blocked because state.dmc_state was still stale from the
        prior screen (usually STATE_IDLE).
        """
        from ..hmi.dmc_vars import (  # noqa: PLC0415
            STATE_GRINDING, STATE_HOMING, STATE_SETUP,
            HMI_STATE_VAR, HMI_SETP, HMI_TRIGGER_FIRE,
        )

        # Stop poller unconditionally — idempotent, noop if already stopped
        self._stop_app_poller()

        if not (self.controller and self.controller.is_connected()):  # type: ignore[attr-defined]
            return

        # Optimistic pre-set: if cached state isn't motion, mark as STATE_SETUP
        # so jog_axis's gate unblocks immediately. Background job verifies.
        if self.state is not None:  # type: ignore[attr-defined]
            cached = getattr(self.state, 'dmc_state', None)  # type: ignore[attr-defined]
            if cached not in (STATE_GRINDING, STATE_HOMING):
                self._apply_dmc_state(STATE_SETUP)

        ctrl = self.controller  # type: ignore[attr-defined]
        cls_name = self.__class__.__name__

        def do_enter():
            import time  # noqa: PLC0415
            try:
                # Fresh read — confirm or correct the optimistic pre-set
                raw = ctrl.cmd(f"MG {HMI_STATE_VAR}").strip()
                current = int(float(raw))

                if current in (STATE_GRINDING, STATE_HOMING):
                    logger.warning(
                        "[%s] setup entry blocked — machine in motion (state=%d); "
                        "correcting optimistic state",
                        cls_name, current,
                    )
                    # Correct the optimistic pre-set: push the REAL state back
                    Clock.schedule_once(lambda *_, s=current: self._apply_dmc_state(s))
                    return

                if current != STATE_SETUP:
                    ctrl.cmd(f"{HMI_SETP}={HMI_TRIGGER_FIRE}")
                    # DMC transitions take a few ms — confirm via readback
                    time.sleep(0.08)
                    try:
                        raw = ctrl.cmd(f"MG {HMI_STATE_VAR}").strip()
                        current = int(float(raw))
                    except Exception:
                        pass  # keep previous `current` value

                # Final confirmed state (may equal optimistic, but always apply)
                Clock.schedule_once(lambda *_, s=current: self._apply_dmc_state(s))
            except Exception as exc:
                logger.error("[%s] setup entry failed: %s", cls_name, exc)

        submit(do_enter)

    def _exit_setup_if_needed(self) -> None:
        """Fire hmiExSt=0 and restart app-wide poller when leaving setup area.

        Navigating between setup siblings (axes_setup <-> parameters) does NOT
        fire exit-setup and does NOT restart the poller — the controller stays
        in STATE_SETUP and the bus stays quiet the whole time.

        After firing hmiExSt, we set state.dmc_state to STATE_IDLE because the
        DMC jumps to #MAIN which sets hmiState=1.  Without #ZALOOP running, DR
        cannot overwrite dmc_state (ZAA=0 is filtered), so we must do it here.
        """
        from ..hmi.dmc_vars import HMI_EXIT_SETUP, HMI_TRIGGER_FIRE, STATE_IDLE  # noqa: PLC0415

        next_screen = ""
        if self.manager:  # type: ignore[attr-defined]
            next_screen = self.manager.current  # type: ignore[attr-defined]

        if next_screen in self._SETUP_SCREENS:
            return  # sibling setup nav — keep poller stopped, stay in setup

        if self.controller and self.controller.is_connected():  # type: ignore[attr-defined]
            ctrl = self.controller  # type: ignore[attr-defined]
            submit(lambda: ctrl.cmd(f"{HMI_EXIT_SETUP}={HMI_TRIGGER_FIRE}"))

        # Update state immediately — DMC transitions to IDLE after hmiExSt
        self._apply_dmc_state(STATE_IDLE)

        # Leaving setup area entirely — resume centralized polling (no-op with DR)
        self._start_app_poller()


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
        2. Unregister from app-wide MgReader (if registered via _mg_log_unreg).
        3. Close matplotlib figure.
        4. Unsubscribe from MachineState.

        Called by the screen loader on programmatic screen removal (Phase 20 swap).
        MgReader lifecycle is app-wide — only handler registration is screen-level.
        """
        # 1. Stop position poll
        if hasattr(self, '_stop_pos_poll'):
            logger.info("[%s] cleanup: stopping pos_poll", self.__class__.__name__)
            self._stop_pos_poll()

        # 2. Unregister from app-wide MgReader (run screens register on_enter)
        if getattr(self, '_mg_log_unreg', None) is not None:
            logger.info("[%s] cleanup: unregistering mg_log_handler", self.__class__.__name__)
            try:
                self._mg_log_unreg()  # type: ignore[attr-defined]
            except Exception:
                pass
            self._mg_log_unreg = None  # type: ignore[attr-defined]

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
        # Motion poll state — set True while _poll_motion_until_idle is running
        # so overlapping calls (e.g. user clicking Rest then Start quickly) are
        # ignored instead of stacking two polling loops on the jobs worker.
        self._motion_poll_active: bool = False

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

    _prev_connected: bool = True  # track transitions

    def _on_state_change(self, state) -> None:
        """React to MachineState updates — disconnect safety + position refresh.

        On disconnect: cancel active motion polling (safety), log warning.
        On reconnect: log info.
        Subclasses may override but should call super()._on_state_change(state).
        """
        connected = getattr(state, 'connected', False)
        was_connected = self._prev_connected

        if was_connected and not connected:
            # Disconnected while on setup screen — cancel any active jog/motion poll
            logger.warning(
                "[%s] Controller disconnected while on axes-setup screen",
                self.__class__.__name__,
            )
            self._motion_poll_active = False

        elif not was_connected and connected:
            logger.info(
                "[%s] Controller reconnected on axes-setup screen",
                self.__class__.__name__,
            )

        self._prev_connected = connected

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

    # ------------------------------------------------------------------
    # Motion polling — used after firing HMI goto triggers (Rest/Start)
    # ------------------------------------------------------------------

    def _push_live_pos(self, axis: str, val_str: str) -> None:
        """Main-thread helper: push a live position reading to pos_current
        (DictProperty) and the corresponding KV label imperatively.

        Safe to call from background threads — schedules the real update
        on the main thread via Clock.schedule_once.
        """
        def _update(*_):
            if hasattr(self, 'pos_current'):
                self.pos_current[axis] = val_str  # type: ignore[attr-defined]
            lbl = self.ids.get(f"pos_{axis.lower()}")
            if lbl:
                lbl.text = val_str
        Clock.schedule_once(_update)

    def _poll_motion_until_idle(
        self,
        axis_list: list[str],
        label: str,
        timeout_sec: float = 60.0,
    ) -> None:
        """Background-thread poll loop that tracks a multi-axis move initiated
        by a non-jog command (e.g. hmiGoRs / hmiGoSt triggers firing #GOREST / #GOSTR).

        Phases:
          1. Wait up to 500 ms for any axis's _BG to go non-zero. If motion
             never starts, assume we're already at target and exit after a
             final readback — no long timeout penalty.
          2. Poll _TD{axis} and _BG{axis} for each axis at 10 Hz, updating
             pos_current and the KV labels live, until ALL axes are idle
             (_BG == 0) or timeout_sec elapses.
          3. One final _TD readback per axis so labels settle at exact final
             values, then log completion via _log_motion_complete (override
             in subclass for UI log).

        Re-entry guard: if _motion_poll_active is already True, logs and
        returns immediately — the caller must wait for the active poll to
        finish before starting another.

        Args:
            axis_list: Axis letters to track (e.g. ["A","B","C","D"] for flat).
            label: Short label for log messages (e.g. "GOTO REST").
            timeout_sec: Max seconds to wait for motion to complete.
        """
        if self._motion_poll_active:
            logger.debug(
                "[%s] _poll_motion_until_idle: already active, ignoring %s",
                self.__class__.__name__, label,
            )
            return

        ctrl = self.controller  # type: ignore[attr-defined]
        if not ctrl or not ctrl.is_connected():
            return

        self._motion_poll_active = True
        cls_name = self.__class__.__name__

        def do_poll():
            import time  # noqa: PLC0415
            try:
                # -- Phase 1: wait for motion to start (up to 500 ms) ------
                started = False
                for _ in range(5):
                    time.sleep(0.1)
                    for axis in axis_list:
                        try:
                            raw = ctrl.cmd(f"MG _BG{axis}").strip()
                            if float(raw) != 0:
                                started = True
                                break
                        except Exception:
                            pass
                    if started:
                        break

                if not started:
                    # Motion never started — already at target. Do a final
                    # readback so labels are accurate, then exit.
                    for axis in axis_list:
                        try:
                            pos = ctrl.cmd(f"MG _TD{axis}").strip()
                            self._push_live_pos(axis, f"{float(pos):.1f}")
                        except Exception:
                            pass
                    Clock.schedule_once(
                        lambda *_, l=label: self._log_motion_complete(l, "already at target")
                    )
                    return

                # -- Phase 2: poll until all axes idle -----------------------
                max_ticks = int(timeout_sec * 10)
                for _ in range(max_ticks):
                    time.sleep(0.1)
                    all_idle = True
                    for axis in axis_list:
                        try:
                            pos = ctrl.cmd(f"MG _TD{axis}").strip()
                            self._push_live_pos(axis, f"{float(pos):.1f}")
                        except Exception:
                            pass
                        try:
                            raw = ctrl.cmd(f"MG _BG{axis}").strip()
                            if float(raw) != 0:
                                all_idle = False
                        except Exception:
                            pass
                    if all_idle:
                        break
                else:
                    # Fell through without breaking — we hit the timeout
                    Clock.schedule_once(
                        lambda *_, l=label: self._log_motion_complete(l, "TIMEOUT")
                    )
                    return

                # -- Phase 3: final readback so labels settle exactly -------
                for axis in axis_list:
                    try:
                        pos = ctrl.cmd(f"MG _TD{axis}").strip()
                        self._push_live_pos(axis, f"{float(pos):.1f}")
                    except Exception:
                        pass
                Clock.schedule_once(
                    lambda *_, l=label: self._log_motion_complete(l, "done")
                )
            except Exception as exc:
                logger.error("[%s] _poll_motion_until_idle failed: %s", cls_name, exc)
                Clock.schedule_once(
                    lambda *_, l=label, e=exc: self._log_motion_complete(l, f"ERROR: {e}")
                )
            finally:
                self._motion_poll_active = False

        submit(do_poll)

    def _log_motion_complete(self, label: str, reason: str) -> None:
        """Main-thread: log motion completion. Subclasses can override to
        write to a cmd log widget instead of (or in addition to) the logger."""
        logger.info("[%s] %s: %s", self.__class__.__name__, label, reason)

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
        # Pre-init instance attrs BEFORE super().__init__ because Kivy fires
        # on_kv_post during super().__init__, which calls build_param_cards()
        # and needs these dicts to exist already.
        try:
            param_defs = mc.get_param_defs()
        except (ValueError, Exception):
            from dmccodegui.machine_config import _FLAT_PARAM_DEFS  # noqa: PLC0415
            param_defs = _FLAT_PARAM_DEFS
        self._param_defs: dict[str, dict] = {p["var"]: p for p in param_defs}
        self._controller_vals: dict[str, float] = {}
        self._dirty: dict[str, str] = {}
        self._field_widgets: dict[str, object] = {}
        self._dot_widgets: dict[str, object] = {}
        super().__init__(**kwargs)

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

    _prev_connected: bool = True  # track transitions

    def _on_state_change(self, state) -> None:
        """React to MachineState updates — log disconnect/reconnect.

        Subclasses may override but should call super()._on_state_change(state).
        """
        connected = getattr(state, 'connected', False)
        was_connected = self._prev_connected

        if was_connected and not connected:
            logger.warning(
                "[%s] Controller disconnected while on parameters screen",
                self.__class__.__name__,
            )
        elif not was_connected and connected:
            logger.info(
                "[%s] Controller reconnected on parameters screen",
                self.__class__.__name__,
            )

        self._prev_connected = connected

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
        """Build grouped parameter cards in a 2-column grid layout.

        Cards are arranged in horizontal pairs (2 per row) inside
        the cards_container ScrollView. Each card has a colored header
        with group icon, name, and param count badge. Each param row
        has a dirty-dot indicator that lights up on change.

        Layout rules:
          - All cards are locked to the same fixed height (CARD_HEIGHT) and
            width (size_hint_x=0.5) regardless of how many params they hold,
            so paired rows always look aesthetically balanced.
          - Each card's param rows live inside an inner ScrollView so cards
            with lots of params (e.g. Calibration with 12) scroll internally
            instead of stretching the whole layout.
          - The outer page-level ScrollView still exists for when there are
            more card rows than fit on screen.
        """
        from collections import OrderedDict  # noqa: PLC0415
        from kivy.graphics import Color, RoundedRectangle, Rectangle, Ellipse  # noqa: PLC0415
        from kivy.uix.boxlayout import BoxLayout  # noqa: PLC0415
        from kivy.uix.label import Label  # noqa: PLC0415
        from kivy.uix.scrollview import ScrollView  # noqa: PLC0415
        from kivy.uix.textinput import TextInput  # noqa: PLC0415
        from kivy.uix.widget import Widget  # noqa: PLC0415
        from kivy.metrics import dp  # noqa: PLC0415

        # Fixed card height — all cards share this regardless of param count.
        # dp(480) = ~36 header + ~440 param area ≈ 10 param rows at 44 dp each
        # visible before the inner ScrollView kicks in. Cards with fewer
        # params simply have empty space below the last row; cards with more
        # scroll internally.
        CARD_HEIGHT = dp(480)

        # Group accent colors
        GROUP_COLORS: dict[str, list[float]] = {
            "Geometry":    [0.980, 0.569, 0.043, 1],
            "Feedrates":   [0.024, 0.714, 0.831, 1],
            "Calibration": [0.659, 0.333, 0.965, 1],
            "Positions":   [0.659, 0.333, 0.965, 1],
        }

        # Group icons (unicode shapes for visual distinction)
        GROUP_ICONS: dict[str, str] = {
            "Geometry":    "\u25c6",   # diamond
            "Feedrates":   "\u25b6",   # play/arrow
            "Calibration": "\u2699",   # gear
            "Positions":   "\u25ce",   # bullseye
        }

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

        groups: OrderedDict[str, list] = OrderedDict()
        for p in param_defs:
            groups.setdefault(p['group'], []).append(p)

        container.clear_widgets()
        self._field_widgets.clear()
        self._dot_widgets = {}

        # --- Build individual card wrappers, then pair them into rows ---
        card_list: list = []

        for group_name, params in groups.items():
            accent = GROUP_COLORS.get(group_name, [0.5, 0.5, 0.5, 1])
            icon_char = GROUP_ICONS.get(group_name, "\u25cf")

            # Card wrapper: stripe + card body — FIXED HEIGHT so all cards
            # are visually uniform in a pair row regardless of param count.
            card_wrapper = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                size_hint_x=0.5,
                height=CARD_HEIGHT,
                spacing=0,
            )

            # Left accent stripe — fills full card height via size_hint_y=1
            stripe = Widget(size_hint_x=None, width=dp(6), size_hint_y=1)
            with stripe.canvas.before:
                Color(rgba=accent)
                _rect = RoundedRectangle(
                    pos=stripe.pos, size=stripe.size, radius=[3, 0, 0, 3],
                )
            stripe.bind(pos=lambda w, v, r=_rect: setattr(r, 'pos', v))
            stripe.bind(size=lambda w, v, r=_rect: setattr(r, 'size', v))
            card_wrapper.add_widget(stripe)

            # Card body — fills the remaining horizontal space in the wrapper
            # and stretches vertically to match CARD_HEIGHT (size_hint_y=1).
            card = BoxLayout(
                orientation='vertical',
                padding=[dp(12), dp(10), dp(12), dp(10)],
                spacing=dp(4),
                size_hint_y=1,
            )

            with card.canvas.before:
                Color(rgba=theme.bg_panel)
                _bg = Rectangle(pos=card.pos, size=card.size)
            card.bind(pos=lambda w, v, r=_bg: setattr(r, 'pos', v))
            card.bind(size=lambda w, v, r=_bg: setattr(r, 'size', v))

            # --- Header row: icon + group name + spacer + "N params" badge ---
            header_row = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(36),
                spacing=dp(8),
            )

            # Icon circle
            icon_lbl = Label(
                text=icon_char,
                font_size='18sp',
                bold=True,
                size_hint_x=None,
                width=dp(28),
                halign='center',
                valign='middle',
                color=accent,
            )
            icon_lbl.bind(size=icon_lbl.setter('text_size'))
            header_row.add_widget(icon_lbl)

            # Group name
            name_lbl = Label(
                text=group_name.upper(),
                font_size='16sp',
                bold=True,
                halign='left',
                valign='middle',
                color=accent,
            )
            name_lbl.bind(size=name_lbl.setter('text_size'))
            header_row.add_widget(name_lbl)

            # Param count badge
            count_lbl = Label(
                text=f'{len(params)} params',
                font_size='12sp',
                size_hint_x=None,
                width=dp(70),
                halign='right',
                valign='middle',
                color=list(theme.text_dim),
            )
            count_lbl.bind(size=count_lbl.setter('text_size'))
            header_row.add_widget(count_lbl)

            card.add_widget(header_row)

            # --- Inner ScrollView for param rows ---
            # Cards with many params scroll internally; cards with few just
            # show the rows at top with empty space below. Either way every
            # card has the same outer height.
            rows_scroll = ScrollView(
                size_hint_y=1,
                do_scroll_x=False,
                bar_width=dp(4),
                scroll_type=['bars', 'content'],
            )
            rows_box = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                spacing=dp(4),
            )
            rows_box.bind(minimum_height=rows_box.setter('height'))
            rows_scroll.add_widget(rows_box)
            card.add_widget(rows_scroll)

            # --- Param rows ---
            for p in params:
                row = BoxLayout(
                    orientation='horizontal',
                    size_hint_y=None,
                    height=dp(44),
                    spacing=dp(4),
                )

                # Label
                lbl = Label(
                    text=p['label'],
                    font_size='16sp',
                    size_hint_x=0.40,
                    halign='left',
                    valign='middle',
                )
                lbl.bind(size=lbl.setter('text_size'))
                row.add_widget(lbl)

                # Variable name (dim accent)
                var_lbl = Label(
                    text=p['var'],
                    font_size='13sp',
                    size_hint_x=0.18,
                    halign='center',
                    valign='middle',
                    color=[accent[0], accent[1], accent[2], 0.5],
                )
                var_lbl.bind(size=var_lbl.setter('text_size'))
                row.add_widget(var_lbl)

                # TextInput value
                ti = TextInput(
                    text='',
                    multiline=False,
                    size_hint_x=0.28,
                    font_size='16sp',
                    halign='center',
                )
                var_name = p['var']
                ti.bind(text=lambda widget, text, v=var_name: self.on_field_text_change(v, text))
                self._field_widgets[var_name] = ti
                row.add_widget(ti)

                # Unit label
                unit_lbl = Label(
                    text=p['unit'],
                    font_size='13sp',
                    size_hint_x=0.10,
                    halign='left',
                    valign='middle',
                    color=list(theme.text_dim),
                )
                unit_lbl.bind(size=unit_lbl.setter('text_size'))
                row.add_widget(unit_lbl)

                # Dirty dot indicator
                dot = Widget(
                    size_hint=(None, None),
                    size=(dp(14), dp(14)),
                    opacity=0,
                )
                dot.pos_hint = {'center_y': 0.5}
                with dot.canvas:
                    dot._dot_color = Color(rgba=[0.980, 0.749, 0.043, 1])
                    dot._dot_ellipse = Ellipse(
                        pos=dot.pos, size=dot.size,
                    )
                dot.bind(
                    pos=lambda w, v: setattr(w._dot_ellipse, 'pos', v),
                    size=lambda w, v: setattr(w._dot_ellipse, 'size', v),
                )
                self._dot_widgets[var_name] = dot
                row.add_widget(dot)

                # Param rows go into the inner ScrollView's rows_box,
                # NOT directly onto the card (header still goes on card).
                rows_box.add_widget(row)

            card_wrapper.add_widget(card)
            card_list.append(card_wrapper)

        # --- Arrange cards into 2-column rows ---
        # Every card_wrapper is locked to CARD_HEIGHT, so the pair_row just
        # pins to that same height. No more minimum_height gymnastics — the
        # row height is known up-front.
        for i in range(0, len(card_list), 2):
            pair_row = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=CARD_HEIGHT,
                spacing=dp(12),
            )

            pair_row.add_widget(card_list[i])

            if i + 1 < len(card_list):
                pair_row.add_widget(card_list[i + 1])
            else:
                # Odd number of groups — add spacer for the empty right column.
                # size_hint_x=0.5 matches the card wrapper width so the single
                # card on this row is the same width as paired cards on other rows.
                spacer = Widget(size_hint_x=0.5)
                pair_row.add_widget(spacer)

            container.add_widget(pair_row)

    def on_field_text_change(self, var_name: str, text: str) -> None:
        """Called by KV on_text bindings when a field value changes."""
        if getattr(self, '_loading', False):
            return

        state = self.validate_field(var_name, text)
        widget = self._field_widgets.get(var_name)
        if widget is not None:
            self._set_field_state(widget, state, var_name)

        if state == 'modified':
            self._mark_dirty(var_name, text)
        else:
            self._clear_dirty(var_name)

    def _set_field_state(self, widget, state: str, var_name: str = '') -> None:
        """Update border color of TextInput and dirty dot based on validation state."""
        BORDER_NORMAL = [0.118, 0.145, 0.188, 1]
        BORDER_AMBER = [0.980, 0.749, 0.043, 0.9]
        BORDER_RED = [0.900, 0.200, 0.200, 0.9]
        DOT_AMBER = [0.980, 0.749, 0.043, 1]
        DOT_RED = [0.900, 0.200, 0.200, 1]
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

            # Update dirty dot if available
            dot = self._dot_widgets.get(var_name) if var_name else None
            if dot is None and hasattr(self, '_dot_widgets'):
                # Try to find by reverse-lookup from widget
                for vn, w in self._field_widgets.items():
                    if w is widget:
                        dot = self._dot_widgets.get(vn)
                        break
            if dot is not None:
                if state == 'error':
                    dot.opacity = 1
                    if hasattr(dot, '_dot_color'):
                        dot._dot_color.rgba = DOT_RED
                elif state == 'modified':
                    dot.opacity = 1
                    if hasattr(dot, '_dot_color'):
                        dot._dot_color.rgba = DOT_AMBER
                else:
                    dot.opacity = 0
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
                    self._set_field_state(widget, 'valid', vname)

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

    # ------------------------------------------------------------------
    # First time setup — write all params so DMC variables exist
    # ------------------------------------------------------------------

    def first_time_setup(self) -> None:
        """Write every parameter field value to the controller, run #VARCALC, burn NV.

        Used on a fresh controller where DMC variables may not exist yet.
        Writes every PARAM_DEF value (from the text fields, or the current
        controller value) so the controller has a complete set of variables.
        Then fires hmiCalc to run #VARCALC and burns to non-volatile memory.
        """
        import time  # noqa: PLC0415
        from dmccodegui.hmi.dmc_vars import (  # noqa: PLC0415
            HMI_CALC, HMI_TRIGGER_FIRE,
        )

        if self.controller is None or not self.controller.is_connected():
            return

        param_defs_snapshot = mc.get_param_defs()

        # Collect values: prefer text field, then controller cache
        values: dict[str, str] = {}
        for p in param_defs_snapshot:
            var = p['var']
            widget = self._field_widgets.get(var)
            text = ''
            if widget is not None and hasattr(widget, 'text') and widget.text.strip():
                text = widget.text.strip()
            elif var in self._controller_vals:
                text = str(self._controller_vals[var])
            if text:
                values[var] = text

        def _job():
            ctrl = self.controller
            if ctrl is None:
                return

            # Write every parameter
            for var_name, text in values.items():
                try:
                    ctrl.cmd(f"{var_name}={text}")
                except Exception:
                    pass

            # Fire #VARCALC
            try:
                ctrl.cmd(f"{HMI_CALC}={HMI_TRIGGER_FIRE}")
            except Exception:
                pass

            time.sleep(0.5)

            # Read back all values
            new_vals: dict[str, float] = {}
            for p in param_defs_snapshot:
                var = p['var']
                try:
                    raw = ctrl.cmd(f"MG {var}")
                    new_vals[var] = float(raw.strip())
                except Exception:
                    pass

            # Burn to NV
            try:
                ctrl.cmd("BV")
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

    # ------------------------------------------------------------------
    # Run calculation — trigger #VARCALC for new knife profile
    # ------------------------------------------------------------------

    def run_calculation(self) -> None:
        """Fire hmiCalc to run #VARCALC on the controller, then read back values.

        Used when a new knife profile is loaded and derived variables (cpm,
        thkCt, bOutDis, cComp curve, etc.) need to be recalculated from
        the current parameter values already on the controller.
        Also writes any pending dirty field values before triggering.
        """
        import time  # noqa: PLC0415
        from dmccodegui.hmi.dmc_vars import (  # noqa: PLC0415
            HMI_CALC, HMI_TRIGGER_FIRE,
        )

        if self.controller is None or not self.controller.is_connected():
            return

        param_defs_snapshot = mc.get_param_defs()
        dirty_snapshot = dict(self._dirty) if self._dirty else {}

        def _job():
            ctrl = self.controller
            if ctrl is None:
                return

            # Write any pending dirty values first
            for var_name, text in dirty_snapshot.items():
                try:
                    ctrl.cmd(f"{var_name}={text}")
                except Exception:
                    pass

            # Fire #VARCALC
            try:
                ctrl.cmd(f"{HMI_CALC}={HMI_TRIGGER_FIRE}")
            except Exception:
                pass

            time.sleep(0.5)

            # Read back all values
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
