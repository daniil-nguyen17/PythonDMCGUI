"""SerrationRunScreen — operator run screen for Serration machines.

3-axis (A, B, C) position display, cycle controls, more/less stone, bComp panel,
and a plot stub. No D-axis, no matplotlib, no DeltaC bar chart.

The bComp panel is the primary differentiator from Flat Grind — it displays a
per-serration B-axis compensation list that operators can read from and write to
the controller one element at a time.

Threading model (same as FlatGrindRunScreen):
  - All controller I/O via submit() / submit_urgent() (background job thread)
  - All UI updates via Clock.schedule_once() (Kivy main thread)
  - MachineState.subscribe() delivers state changes from the centralized poller
  - _on_state_change() is the single path for updating Kivy properties from state

KV file: ui/serration/run.kv

TODO: verify bComp array name against real Serration DMC program (customer to confirm)
"""
from __future__ import annotations

import logging
import threading

from kivy.clock import Clock
from kivy.properties import (
    BooleanProperty,
    NumericProperty,
    StringProperty,
)

from ...hmi.dmc_vars import (
    STATE_GRINDING, STATE_HOMING,
    HMI_GRND, HMI_MORE, HMI_LESS, HMI_TRIGGER_FIRE,
    STARTPT_C,
    BCOMP_ARRAY, BCOMP_NUM_SERR,
    CT_SES_KNI, CT_STN_KNI,
)
from ...utils import jobs
from ..base import BaseRunScreen
from .widgets import BCompPanel

logger = logging.getLogger(__name__)


class SerrationRunScreen(BaseRunScreen):
    """
    SerrationRunScreen — operator screen for Serration grinding machines.

    Layout: left column (bComp panel + plot stub), right column (controller log +
    stone compensation + grind progress), bottom action bar.

    Differences from FlatGrindRunScreen:
      - 3 axes only (A, B, C) — no D-axis properties or widgets
      - No matplotlib — plot area is a placeholder stub
      - No DeltaC bar chart — replaced by bComp scrollable list
      - BCompPanel reads/writes per-serration B-axis compensation values

    Inherits controller/state ObjectProperties and subscribe/unsubscribe lifecycle
    from BaseRunScreen.
    """

    # -----------------------------------------------------------------------
    # Kivy properties — bound in run.kv
    # -----------------------------------------------------------------------

    # Cycle state
    cycle_running = BooleanProperty(False)
    motion_active = BooleanProperty(False)

    # Cycle display strings
    cycle_elapsed = StringProperty("00:00")
    cycle_eta = StringProperty("--:--")
    cycle_completion_pct = NumericProperty(0)

    # Axis position strings (3-axis — A, B, C only; no D-axis)
    pos_a = StringProperty("---")
    pos_b = StringProperty("---")
    pos_c = StringProperty("---")

    # Knife counts
    session_knife_count = StringProperty("0")
    stone_knife_count = StringProperty("0")

    # Stone compensation readback
    start_pt_c = StringProperty("---")

    # Disconnect banner (empty string = no banner)
    disconnect_banner = StringProperty("")

    # MG message log
    mg_log_text = StringProperty("")

    # bComp panel display
    num_serr = NumericProperty(0)
    num_serr_str = StringProperty("Serrations: --")

    # -----------------------------------------------------------------------
    # Internal state
    # -----------------------------------------------------------------------
    # NOTE: _state_unsub is owned by BaseRunScreen — do NOT shadow it here

    _bcomp_values: list[float] = []
    _bcomp_panel: BCompPanel | None = None
    _pos_clock_event = None
    _pos_busy: bool = False
    _mg_thread: threading.Thread | None = None
    _mg_stop_event: threading.Event | None = None
    _disconnect_clock = None
    _disconnect_t0: float | None = None
    _cycle_start_time: float | None = None
    _last_cycle_duration: float | None = None
    _elapsed_clock_event = None

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    def on_pre_enter(self, *args) -> None:
        """Called by Kivy when operator navigates to this screen.

        Subscribes to MachineState (via BaseRunScreen), starts position poll,
        reads startPtC, wires bComp panel callbacks, and auto-reads bComp.
        """
        super().on_pre_enter(*args)

        # Stop the centralized poller — its traffic floods the controller bus
        from kivy.app import App
        app = App.get_running_app()
        if app and hasattr(app, '_stop_poller'):
            app._stop_poller()

        # Start position poll
        self._start_pos_poll()

        # Read startPtC so the Stone Compensation label is populated on entry
        self._read_start_pt_c()

        # Wire bComp panel callbacks and trigger initial read
        panel = self.ids.get('bcomp_panel')
        if panel is not None:
            self._bcomp_panel = panel
            panel.save_callback = self._write_bcomp_element
            panel.refresh_callback = self._read_bcomp_job
            self._read_bcomp_job()

        # Start MG message reader
        self._start_mg_reader()

    def on_leave(self, *args) -> None:
        """Called by Kivy when operator navigates away.

        Cancels screen-specific clocks, stops position poll and MG reader,
        then delegates unsubscribe to BaseRunScreen.
        """
        if self._disconnect_clock:
            self._disconnect_clock.cancel()
            self._disconnect_clock = None
            self._disconnect_t0 = None

        self._stop_pos_poll()

        if self._elapsed_clock_event:
            self._elapsed_clock_event.cancel()
            self._elapsed_clock_event = None

        self._stop_mg_reader()

        # Restart the centralized poller for other screens
        from kivy.app import App
        app = App.get_running_app()
        if app and hasattr(app, '_start_poller'):
            app._start_poller()

        super().on_leave(*args)

    # -----------------------------------------------------------------------
    # Position poll
    # -----------------------------------------------------------------------

    def _start_pos_poll(self) -> None:
        """Start 5 Hz position polling."""
        if self._pos_clock_event is not None:
            return
        self._pos_clock_event = Clock.schedule_interval(self._tick_pos, 0.2)

    def _stop_pos_poll(self) -> None:
        """Stop position polling."""
        if self._pos_clock_event is not None:
            self._pos_clock_event.cancel()
            self._pos_clock_event = None
        self._pos_busy = False

    def _set_poll_rate(self, hz: float) -> None:
        """Switch position poll rate."""
        if self._pos_clock_event is not None:
            self._pos_clock_event.cancel()
        self._pos_clock_event = Clock.schedule_interval(self._tick_pos, 1.0 / hz)

    def _tick_pos(self, dt: float) -> None:
        """5 Hz clock: read A, B, C positions + state from controller in background.

        Reads 3 axes only (no D). Uses a busy guard to prevent job pileup.
        """
        if self._pos_busy:
            return
        if not self.controller or not self.controller.is_connected():
            return
        ctrl = self.controller
        self._pos_busy = True

        def _do():
            from ...utils.jobs import get_jobs
            cancel = get_jobs().cancel_event

            try:
                raw = ctrl.cmd("MG _TPA, _TPB, _TPC").strip()
                vals = [float(v) for v in raw.split()]
                a, b, c = vals[0], vals[1], vals[2]
            except Exception:
                self._pos_busy = False
                return

            if cancel.is_set():
                self._pos_busy = False
                return

            dmc_state = 0
            ses_kni = 0
            stn_kni = 0
            try:
                from ...hmi.dmc_vars import HMI_STATE_VAR
                raw2 = ctrl.cmd(f"MG {HMI_STATE_VAR}, {CT_SES_KNI}, {CT_STN_KNI}").strip()
                vals2 = [float(v) for v in raw2.split()]
                dmc_state = int(vals2[0])
                ses_kni = int(vals2[1])
                stn_kni = int(vals2[2])
            except Exception:
                pass

            def _apply(*_):
                self._pos_busy = False
                self.pos_a = f"{int(a):,}"
                self.pos_b = f"{int(b):,}"
                self.pos_c = f"{int(c):,}"
                self.session_knife_count = str(ses_kni)
                self.stone_knife_count = str(stn_kni)
                was_grinding = self.cycle_running
                self.cycle_running = dmc_state == STATE_GRINDING
                self.motion_active = dmc_state in (STATE_GRINDING, STATE_HOMING)
                if was_grinding and not self.cycle_running:
                    self._stop_elapsed()
                    self._set_poll_rate(5)
                    self._read_start_pt_c()

            Clock.schedule_once(_apply)

        jobs.submit(_do)

    def _tick_elapsed(self, dt: float) -> None:
        """1 Hz clock: update elapsed time display."""
        import time
        if self._cycle_start_time is None:
            return
        elapsed = time.monotonic() - self._cycle_start_time
        m = int(elapsed) // 60
        s = int(elapsed) % 60
        self.cycle_elapsed = f"{m:02d}:{s:02d}"

    def _stop_elapsed(self) -> None:
        """Stop the elapsed timer and record cycle duration."""
        if self._elapsed_clock_event is not None:
            self._elapsed_clock_event.cancel()
            self._elapsed_clock_event = None
        if self._cycle_start_time is not None:
            import time
            self._last_cycle_duration = time.monotonic() - self._cycle_start_time
            self.cycle_completion_pct = 100
            self.cycle_eta = "00:00"
            self._cycle_start_time = None

    def _tick_disconnect_banner(self, dt: float) -> None:
        """1 Hz callback: update disconnect elapsed time banner."""
        import time
        if self._disconnect_t0 is not None:
            elapsed = int(time.monotonic() - self._disconnect_t0)
            self.disconnect_banner = f"DISCONNECTED ({elapsed}s)"

    # -----------------------------------------------------------------------
    # State subscription handler
    # -----------------------------------------------------------------------

    def _on_state_change(self, state) -> None:
        """BaseRunScreen lifecycle hook — delegates to _apply_state."""
        self._apply_state(state)

    def _apply_state(self, s) -> None:
        """Main thread: apply MachineState to SerrationRunScreen Kivy properties.

        Updates positions (A, B, C only), cycle status, knife counts.
        """
        import time as _time

        if s.connected:
            if self.disconnect_banner:
                self.disconnect_banner = ""
            if self._disconnect_clock:
                self._disconnect_clock.cancel()
                self._disconnect_clock = None
                self._disconnect_t0 = None

            # Axis positions — 3 axes only (no D)
            for axis, prop in (("A", "pos_a"), ("B", "pos_b"), ("C", "pos_c")):
                val = s.pos.get(axis)
                if val is not None:
                    try:
                        setattr(self, prop, f"{int(val):,}")
                    except (ValueError, TypeError):
                        setattr(self, prop, "---")
                else:
                    setattr(self, prop, "---")

            self.session_knife_count = str(s.session_knife_count)
            self.stone_knife_count = str(s.stone_knife_count)
            self.cycle_running = s.cycle_running
            self.motion_active = s.dmc_state in (STATE_GRINDING, STATE_HOMING)

        else:
            self.cycle_running = False
            self.motion_active = True
            if self._disconnect_clock is None:
                self._disconnect_t0 = _time.monotonic()
                self._tick_disconnect_banner(0)
                self._disconnect_clock = Clock.schedule_interval(
                    self._tick_disconnect_banner, 1.0
                )

    # -----------------------------------------------------------------------
    # bComp panel — read and write
    # -----------------------------------------------------------------------

    def _read_bcomp_job(self) -> None:
        """Submit _read_bcomp as a background job."""
        jobs.submit(self._read_bcomp)

    def _read_bcomp(self) -> None:
        """Background job: read numSerr from controller, then read bComp array.

        Reads BCOMP_NUM_SERR first to determine array length, then reads each
        element of BCOMP_ARRAY individually. On completion, updates the bComp
        panel on the main thread.

        TODO: verify bComp array name against real Serration DMC program
        """
        ctrl = self.controller
        if not ctrl or not ctrl.is_connected():
            logger.warning("[SerrationRunScreen] _read_bcomp: controller not connected")
            return

        try:
            raw_n = ctrl.cmd(f"MG {BCOMP_NUM_SERR}").strip()
            n = int(float(raw_n))
        except Exception as e:
            logger.warning("[SerrationRunScreen] _read_bcomp: failed to read numSerr: %s", e)
            return

        if n <= 0:
            logger.warning(
                "[SerrationRunScreen] _read_bcomp: numSerr=%s is not positive — "
                "verify variable name against Serration DMC program", n
            )
            return

        values: list[float] = []
        for i in range(n):
            try:
                raw_v = ctrl.cmd(f"MG {BCOMP_ARRAY}[{i}]").strip()
                values.append(float(raw_v))
            except Exception as e:
                logger.warning(
                    "[SerrationRunScreen] _read_bcomp: failed to read %s[%d]: %s",
                    BCOMP_ARRAY, i, e
                )
                values.append(0.0)

        def _apply(*_):
            self.num_serr = n
            self.num_serr_str = f"Serrations: {n}"
            self._bcomp_values = values
            if self._bcomp_panel is not None:
                self._bcomp_panel.build_rows(values)

        Clock.schedule_once(_apply)

    def _write_bcomp_element(self, index: int, value_mm: float) -> None:
        """Write a single bComp element to the controller.

        Sends bComp[{index}]={value_mm:.4f} in a background job.
        Mirrors the deltaC individual element write pattern from FlatGrindRunScreen.

        Args:
            index:    Zero-based serration index.
            value_mm: Compensation value in mm, validated by BCompPanel._on_save().

        TODO: verify bComp array name against real Serration DMC program
        """
        if not self.controller or not self.controller.is_connected():
            return
        ctrl = self.controller

        def _do():
            cmd = f"{BCOMP_ARRAY}[{index}]={value_mm:.4f}"
            try:
                ctrl.cmd(cmd)
                logger.debug(
                    "[SerrationRunScreen] _write_bcomp_element: wrote %s[%d]=%.4f",
                    BCOMP_ARRAY, index, value_mm
                )
            except Exception as e:
                logger.error(
                    "[SerrationRunScreen] _write_bcomp_element: failed to write %s[%d]: %s",
                    BCOMP_ARRAY, index, e
                )

        jobs.submit(_do)

    # -----------------------------------------------------------------------
    # Cycle action handlers
    # -----------------------------------------------------------------------

    def on_start_grind(self) -> None:
        """Send hmiGrnd=0 to start/continue grinding cycle.

        Uses the HMI one-shot trigger pattern — never XQ direct calls.
        Guards: cannot start while in motion or cycle already running.
        """
        if not self.controller or not self.controller.is_connected():
            return
        if self.motion_active or self.cycle_running:
            return

        # Start elapsed timer
        import time
        self._cycle_start_time = time.monotonic()
        self.cycle_elapsed = "00:00"
        if self._last_cycle_duration is not None:
            m = int(self._last_cycle_duration) // 60
            s = int(self._last_cycle_duration) % 60
            self.cycle_eta = f"{m:02d}:{s:02d}"
        else:
            self.cycle_eta = "--:--"
        self.cycle_completion_pct = 0
        if self._elapsed_clock_event is None:
            self._elapsed_clock_event = Clock.schedule_interval(self._tick_elapsed, 1.0)

        def _fire():
            try:
                self.controller.cmd(f"{HMI_GRND}={HMI_TRIGGER_FIRE}")
            except Exception as e:
                Clock.schedule_once(lambda *_: logger.error("Start grind failed: %s", e))

        jobs.submit_urgent(_fire)
        self._set_poll_rate(1)

    def on_stop(self) -> None:
        """Send ST ABCD via submit_urgent — preempts polls, thread-safe."""
        if not self.controller or not self.controller.is_connected():
            return

        def do_stop():
            try:
                self.controller.cmd("ST ABCD")
            except Exception as e:
                Clock.schedule_once(lambda *_: logger.error("Stop failed: %s", e))

        jobs.submit_urgent(do_stop)

    def on_more_stone(self) -> None:
        """Send hmiMore=0 then read startPtC after 400ms delay to update label.

        Fires the HMI_MORE trigger, sleeps 400ms for the DMC #MOREGRI subroutine to
        complete, then reads startPtC and updates the persistent start_pt_c label.
        """
        if not self.controller or not self.controller.is_connected():
            return
        ctrl = self.controller

        def _fire():
            import time as _time
            try:
                before_raw = ctrl.cmd(f"MG {STARTPT_C}").strip()
                before = int(float(before_raw))
                logger.debug("[SerrationRunScreen] More stone — startPtC BEFORE: %s", before)
            except Exception as e:
                logger.debug("[SerrationRunScreen] More stone — failed to read startPtC before: %s", e)

            try:
                ctrl.cmd(f"{HMI_MORE}={HMI_TRIGGER_FIRE}")
            except Exception as e:
                logger.error("[SerrationRunScreen] More stone failed: %s", e)
                return

            _time.sleep(0.4)

            try:
                after_raw = ctrl.cmd(f"MG {STARTPT_C}").strip()
                after = int(float(after_raw))
                logger.debug("[SerrationRunScreen] More stone — startPtC AFTER: %s", after)
                Clock.schedule_once(
                    lambda *_, v=after: setattr(self, 'start_pt_c', f"Stone Pos: {v:,}")
                )
            except Exception as e:
                logger.debug("[SerrationRunScreen] More stone — failed to read startPtC after: %s", e)

        from ...utils.jobs import submit_urgent
        submit_urgent(_fire)

    def on_less_stone(self) -> None:
        """Send hmiLess=0 then read startPtC after 400ms delay to update label.

        Mirror of on_more_stone but fires HMI_LESS. Sleeps 400ms for the DMC
        #LESSGRI subroutine to complete, then reads startPtC and updates the
        persistent start_pt_c label.
        """
        if not self.controller or not self.controller.is_connected():
            return
        ctrl = self.controller

        def _fire():
            import time as _time
            try:
                before_raw = ctrl.cmd(f"MG {STARTPT_C}").strip()
                before = int(float(before_raw))
                logger.debug("[SerrationRunScreen] Less stone — startPtC BEFORE: %s", before)
            except Exception as e:
                logger.debug("[SerrationRunScreen] Less stone — failed to read startPtC before: %s", e)

            try:
                ctrl.cmd(f"{HMI_LESS}={HMI_TRIGGER_FIRE}")
            except Exception as e:
                logger.error("[SerrationRunScreen] Less stone failed: %s", e)
                return

            _time.sleep(0.4)

            try:
                after_raw = ctrl.cmd(f"MG {STARTPT_C}").strip()
                after = int(float(after_raw))
                logger.debug("[SerrationRunScreen] Less stone — startPtC AFTER: %s", after)
                Clock.schedule_once(
                    lambda *_, v=after: setattr(self, 'start_pt_c', f"Stone Pos: {v:,}")
                )
            except Exception as e:
                logger.debug("[SerrationRunScreen] Less stone — failed to read startPtC after: %s", e)

        from ...utils.jobs import submit_urgent
        submit_urgent(_fire)

    # -----------------------------------------------------------------------
    # Stone Compensation
    # -----------------------------------------------------------------------

    def _read_start_pt_c(self) -> None:
        """Background: read startPtC from controller and update persistent label."""
        if not self.controller or not self.controller.is_connected():
            return
        ctrl = self.controller

        def _do():
            try:
                raw = ctrl.cmd(f"MG {STARTPT_C}").strip()
                val = int(float(raw))
                Clock.schedule_once(
                    lambda *_, v=val: setattr(self, 'start_pt_c', f"Stone Pos: {v:,}")
                )
            except Exception:
                Clock.schedule_once(lambda *_: setattr(self, 'start_pt_c', '---'))

        jobs.submit(_do)

    # -----------------------------------------------------------------------
    # MG message reader (controller log)
    # -----------------------------------------------------------------------

    def _start_mg_reader(self) -> None:
        """Start the MG (unsolicited message) reader thread for the controller log."""
        if self._mg_thread is not None and self._mg_thread.is_alive():
            return
        self._mg_stop_event = threading.Event()
        self._mg_thread = threading.Thread(
            target=self._mg_reader_loop,
            daemon=True,
            name="SerrationMGReader",
        )
        self._mg_thread.start()

    def _stop_mg_reader(self) -> None:
        """Stop the MG message reader thread (join for normal navigation)."""
        if self._mg_stop_event is not None:
            self._mg_stop_event.set()
        if self._mg_thread is not None:
            self._mg_thread.join(timeout=1.0)
            self._mg_thread = None
        self._mg_stop_event = None

    def _mg_reader_loop(self) -> None:
        """Background thread: poll controller for unsolicited (MG) messages."""
        stop = self._mg_stop_event
        ctrl = self.controller
        if ctrl is None or stop is None:
            return

        while not stop.is_set():
            try:
                msg = ctrl.message()
                if msg:
                    msg_strip = msg.strip()
                    if msg_strip:
                        def _append(msg_text=msg_strip):
                            existing = self.mg_log_text
                            lines = existing.split('\n') if existing else []
                            lines.append(msg_text)
                            if len(lines) > 100:
                                lines = lines[-100:]
                            self.mg_log_text = '\n'.join(lines)
                        Clock.schedule_once(lambda *_, f=_append: f())
            except Exception:
                pass
            stop.wait(0.1)
