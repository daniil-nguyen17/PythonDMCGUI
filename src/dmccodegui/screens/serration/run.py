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
    STARTPT_B,
    BCOMP_ARRAY, BCOMP_NUM_SERR,
    CT_SES_KNI, CT_STN_KNI,
)
from ...hmi.poll import read_all_state
from ...utils import jobs
from ..base import BaseRunScreen
from .widgets import BCompPanel, CCompPanel, CCOMP_ARRAY_VAR

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
    _bcomp_viz = None
    _ccomp_values: list[float] = []
    _ccomp_panel: CCompPanel | None = None
    _ccomp_viz = None
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
        reads startPtB, wires bComp panel callbacks, and auto-reads bComp.
        """
        super().on_pre_enter(*args)

        # One-shot read to populate UI (no continuous polling until grind starts)
        self._do_one_shot_read()

        # Read startPtB so the Stone Compensation label is populated on entry
        self._read_start_pt_c()

        # Wire bComp panel + visualization and trigger initial read
        panel = self.ids.get('bcomp_panel')
        self._bcomp_viz = self.ids.get('bcomp_viz')
        if panel is not None:
            self._bcomp_panel = panel
            panel.save_callback = self._on_bcomp_save
            panel.refresh_callback = self._read_bcomp_job
            self._read_bcomp_job()

        # Wire cComp panel + visualization and trigger initial read
        cpanel = self.ids.get('ccomp_panel')
        self._ccomp_viz = self.ids.get('ccomp_viz')
        if cpanel is not None:
            self._ccomp_panel = cpanel
            cpanel.save_callback = self._on_ccomp_save
            cpanel.refresh_callback = self._read_ccomp_job
            self._read_ccomp_job()

        # Start per-screen MG reader (own gclib handle, --subscribe MG)
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

        # Stop per-screen MG reader thread
        self._stop_mg_reader()

        super().on_leave(*args)

    # -----------------------------------------------------------------------
    # Position poll
    # -----------------------------------------------------------------------

    def _do_one_shot_read(self) -> None:
        """Single read of positions + state to populate UI on page load.

        Includes a short delay to let the controller finish processing
        hmiExSt (setup exit) before reading state — avoids reading stale
        dmc_state=SETUP when returning from a setup screen.
        """
        if not self.controller or not self.controller.is_connected():
            return
        ctrl = self.controller

        def _do():
            import time as _time
            _time.sleep(0.15)  # let hmiExSt transition complete
            result = read_all_state(ctrl)
            if result is None:
                return
            a, b, c, _d, dmc_state, ses_kni, stn_kni, program_running = result

            def _apply(*_):
                self.pos_a = f"{int(a):,}"
                self.pos_b = f"{int(b):,}"
                self.pos_c = f"{int(c):,}"
                self.session_knife_count = str(ses_kni)
                self.stone_knife_count = str(stn_kni)
                # Guard: don't overwrite if on_start_grind already fired
                if not self.cycle_running:
                    self.cycle_running = dmc_state == STATE_GRINDING
                if not self.motion_active:
                    self.motion_active = dmc_state in (STATE_GRINDING, STATE_HOMING)
                # If already grinding when we enter, start polling
                if self.cycle_running:
                    self._start_pos_poll()
            Clock.schedule_once(_apply)

        jobs.submit(_do)

    def _start_pos_poll(self) -> None:
        """Start 5 Hz position polling. Called when grind starts."""
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

        Reads 3 axes only (no D display). Uses a busy guard to prevent job pileup.
        Uses read_all_state() for a single batched MG command. The D axis value
        from the batch result is intentionally ignored — Serration has no D display.
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

            result = read_all_state(ctrl)
            if result is None:
                self._pos_busy = False
                return

            if cancel.is_set():
                self._pos_busy = False
                return

            a, b, c, _d, dmc_state, ses_kni, stn_kni, program_running = result
            # D axis value is intentionally ignored — Serration has no D display

            def _apply(*_):
                self._pos_busy = False
                self.pos_a = f"{int(a):,}"
                self.pos_b = f"{int(b):,}"
                self.pos_c = f"{int(c):,}"
                self.session_knife_count = str(ses_kni)
                self.stone_knife_count = str(stn_kni)
                # Detect grind end: was grinding, now idle → stop polling
                was_grinding = self.cycle_running
                new_grinding = dmc_state == STATE_GRINDING
                if was_grinding and not new_grinding:
                    self.cycle_running = False
                    self.motion_active = False
                    self._stop_pos_poll()
                    self._stop_elapsed()
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
        """Main thread: apply DR state updates — positions, grind detection, disconnect.

        Called on every DataRecordListener packet (~10 Hz). Acts as the
        primary source of truth for positions and state. The TCP poll in
        _tick_pos() is kept as a secondary/fallback source; when both fire,
        Kivy properties deduplicate identical values (no-op assignment).

        Serration is 3-axis (A, B, C) — D-axis data from DR is ignored.
        """
        import time as _time

        if s.connected:
            # Clear disconnect banner if reconnected
            if self.disconnect_banner:
                self.disconnect_banner = ""
            if self._disconnect_clock:
                self._disconnect_clock.cancel()
                self._disconnect_clock = None
                self._disconnect_t0 = None

            # --- Position updates from DR (3-axis only, no D) ---
            a = s.pos.get("A", 0.0)
            b = s.pos.get("B", 0.0)
            c = s.pos.get("C", 0.0)
            self.pos_a = f"{int(a):,}"
            self.pos_b = f"{int(b):,}"
            self.pos_c = f"{int(c):,}"

            # --- Knife counts from DR ---
            self.session_knife_count = str(s.session_knife_count)
            self.stone_knife_count = str(s.stone_knife_count)
            # Note: stone position for serration is startPtB (B-axis), not startPtC.
            # DR streams startPtC via ZAD which is wrong for this machine.
            # Stone position is read via TCP in _read_start_pt_c() instead.

            # --- Grind state detection from DR ---
            dmc_state = s.dmc_state
            now_grinding = dmc_state == STATE_GRINDING

            if now_grinding:
                # Ensure buttons are grayed out
                if not self.motion_active:
                    self.motion_active = True
                if not self.cycle_running:
                    self.cycle_running = True

                # Start polling if not already running (catches late grind detection)
                if self._pos_clock_event is None:
                    self._start_pos_poll()

            elif self.cycle_running and not now_grinding and dmc_state != 0:
                # Grind ended: DR says no longer grinding
                self.cycle_running = False
                self.motion_active = False
                self._stop_pos_poll()
                self._stop_elapsed()
                self._read_start_pt_c()

        else:
            # Disconnected: disable all motion buttons, stop polling
            self.cycle_running = False
            self.motion_active = True
            self._stop_pos_poll()
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
        """Background job: read numSerr + bComp array via bulk upload.

        Uses upload_array_auto (GArrayUpload) for a single TCP command instead
        of N sequential MG reads. Falls back to chunked MG automatically.
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
                "[SerrationRunScreen] _read_bcomp: numSerr=%s is not positive", n
            )
            return

        try:
            all_vals = ctrl.upload_array_auto(BCOMP_ARRAY)
            values = all_vals[:n]
            # Pad if array on controller is shorter than numSerr
            while len(values) < n:
                values.append(0.0)
        except Exception as e:
            logger.warning("[SerrationRunScreen] _read_bcomp: bulk read failed: %s", e)
            return

        def _apply(*_):
            self.num_serr = n
            self.num_serr_str = f"Serrations: {n}"
            self._bcomp_values = values
            if self._bcomp_panel is not None:
                self._bcomp_panel.build_rows(values)
            if self._bcomp_viz is not None:
                self._bcomp_viz.update_dots(values)

        Clock.schedule_once(_apply)

    def _on_bcomp_save(self, index: int, value_mm: float) -> None:
        """Callback from bComp panel: update local cache + viz, then write."""
        if 0 <= index < len(self._bcomp_values):
            self._bcomp_values[index] = value_mm
        if self._bcomp_viz is not None:
            self._bcomp_viz.update_dots(self._bcomp_values)
        self._write_bcomp_element(index, value_mm)

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

        panel = self._bcomp_panel

        def _do():
            cmd = f"{BCOMP_ARRAY}[{index}]={value_mm:.4f}"
            try:
                ctrl.cmd(cmd)
            except Exception as e:
                # Handle broken — try reset + retry once
                if "write error" in str(e).lower() or "read error" in str(e).lower():
                    logger.warning("[SerrationRunScreen] bComp write error — resetting handle and retrying")
                    try:
                        ctrl.reset_handle()
                        ctrl.cmd(cmd)
                    except Exception as e2:
                        logger.error("[SerrationRunScreen] bComp retry failed: %s", e2)
                        if panel is not None:
                            Clock.schedule_once(lambda *_: panel.flash_result(index, False))
                        return
                else:
                    logger.error("[SerrationRunScreen] _write_bcomp_element: failed %s[%d]: %s",
                                 BCOMP_ARRAY, index, e)
                    if panel is not None:
                        Clock.schedule_once(lambda *_: panel.flash_result(index, False))
                    return
            logger.debug("[SerrationRunScreen] _write_bcomp_element: wrote %s[%d]=%.4f",
                         BCOMP_ARRAY, index, value_mm)
            if panel is not None:
                Clock.schedule_once(lambda *_: panel.flash_result(index, True))

        jobs.submit(_do)

    # -----------------------------------------------------------------------
    # cComp panel — read and write
    # -----------------------------------------------------------------------

    def _read_ccomp_job(self) -> None:
        """Submit _read_ccomp as a background job."""
        jobs.submit(self._read_ccomp)

    def _read_ccomp(self) -> None:
        """Background job: read numSerr + cComp array via bulk upload.

        Uses upload_array_auto (GArrayUpload) for a single TCP command instead
        of N sequential MG reads. Falls back to chunked MG automatically.
        """
        ctrl = self.controller
        if not ctrl or not ctrl.is_connected():
            logger.warning("[SerrationRunScreen] _read_ccomp: controller not connected")
            return

        try:
            raw_n = ctrl.cmd(f"MG {BCOMP_NUM_SERR}").strip()
            n = int(float(raw_n))
        except Exception as e:
            logger.warning("[SerrationRunScreen] _read_ccomp: failed to read numSerr: %s", e)
            return

        if n <= 0:
            logger.warning("[SerrationRunScreen] _read_ccomp: numSerr=%s not positive", n)
            return

        try:
            all_vals = ctrl.upload_array_auto(CCOMP_ARRAY_VAR)
            values = all_vals[:n]
            while len(values) < n:
                values.append(0.0)
        except Exception as e:
            logger.warning("[SerrationRunScreen] _read_ccomp: bulk read failed: %s", e)
            return

        def _apply(*_):
            self._ccomp_values = values
            if self._ccomp_panel is not None:
                self._ccomp_panel.build_rows(values)
            if self._ccomp_viz is not None:
                self._ccomp_viz.update_dots(values)

        Clock.schedule_once(_apply)

    def _on_ccomp_save(self, index: int, value_mm: float) -> None:
        """Callback from cComp panel: update local cache + viz, then write."""
        if 0 <= index < len(self._ccomp_values):
            self._ccomp_values[index] = value_mm
        if self._ccomp_viz is not None:
            self._ccomp_viz.update_dots(self._ccomp_values)
        self._write_ccomp_element(index, value_mm)

    def _write_ccomp_element(self, index: int, value_mm: float) -> None:
        """Write a single cComp element to the controller.

        Sends cComp[{index}]={value_mm:.4f} in a background job.
        Same pattern as _write_bcomp_element.

        Args:
            index:    Zero-based serration index.
            value_mm: Compensation value in mm, validated by CCompPanel._on_save().
        """
        if not self.controller or not self.controller.is_connected():
            return
        ctrl = self.controller

        panel = self._ccomp_panel

        def _do():
            cmd = f"{CCOMP_ARRAY_VAR}[{index}]={value_mm:.4f}"
            try:
                ctrl.cmd(cmd)
            except Exception as e:
                # Handle broken — try reset + retry once
                if "write error" in str(e).lower() or "read error" in str(e).lower():
                    logger.warning("[SerrationRunScreen] cComp write error — resetting handle and retrying")
                    try:
                        ctrl.reset_handle()
                        ctrl.cmd(cmd)
                    except Exception as e2:
                        logger.error("[SerrationRunScreen] cComp retry failed: %s", e2)
                        if panel is not None:
                            Clock.schedule_once(lambda *_: panel.flash_result(index, False))
                        return
                else:
                    logger.error("[SerrationRunScreen] _write_ccomp_element: failed %s[%d]: %s",
                                 CCOMP_ARRAY_VAR, index, e)
                    if panel is not None:
                        Clock.schedule_once(lambda *_: panel.flash_result(index, False))
                    return
            logger.debug("[SerrationRunScreen] _write_ccomp_element: wrote %s[%d]=%.4f",
                         CCOMP_ARRAY_VAR, index, value_mm)
            if panel is not None:
                Clock.schedule_once(lambda *_: panel.flash_result(index, True))

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
                Clock.schedule_once(lambda *_, err=e: logger.error("Start grind failed: %s", err))

        jobs.submit_urgent(_fire)

        # Immediately disable grind button and enable stop button
        self.motion_active = True
        self.cycle_running = True

        # Start position polling for grind monitoring
        self._start_pos_poll()

    def on_stop(self) -> None:
        """Send ST ABCD via submit_urgent — preempts polls, thread-safe."""
        if not self.controller or not self.controller.is_connected():
            return

        def do_stop():
            try:
                self.controller.cmd("ST ABCD")
            except Exception as e:
                Clock.schedule_once(lambda *_, err=e: logger.error("Stop failed: %s", err))

        jobs.submit_urgent(do_stop)

    def on_shutdown(self) -> None:
        """Shutdown: enter setup → home → wait for homing complete → BV.

        Sequence:
          1. hmiSetp=0 — enter setup mode (DMC goes to #SULOOP)
          2. hmiHome=0 — trigger homing (DMC runs #HOME from #SULOOP)
          3. Poll hmiState until it returns to 3 (SETUP) — homing done
          4. BV — save all variables to NV memory
        """
        if not self.controller or not self.controller.is_connected():
            return
        if self.motion_active or self.cycle_running:
            return

        from dmccodegui.hmi.dmc_vars import (
            HMI_SETP, HMI_HOME, HMI_TRIGGER_FIRE, HMI_STATE_VAR,
            STATE_HOMING, STATE_SETUP,
        )

        self.motion_active = True  # Disable buttons during shutdown

        def _do_shutdown():
            import time as _t
            ctrl = self.controller
            try:
                # Step 1: Enter setup mode
                ctrl.cmd(f"{HMI_SETP}={HMI_TRIGGER_FIRE}")
                logger.info("[Shutdown] hmiSetp fired — entering setup")
                _t.sleep(0.5)

                # Step 2: Trigger homing
                ctrl.cmd(f"{HMI_HOME}={HMI_TRIGGER_FIRE}")
                logger.info("[Shutdown] hmiHome fired — homing axes")

                # Step 3: Wait for homing to complete (poll hmiState)
                for _ in range(120):  # max 60 seconds
                    _t.sleep(0.5)
                    try:
                        raw = ctrl.cmd(f"MG {HMI_STATE_VAR}").strip()
                        state = int(float(raw))
                        if state == STATE_SETUP:
                            logger.info("[Shutdown] Homing complete — state back to SETUP")
                            break
                    except Exception:
                        pass
                else:
                    logger.warning("[Shutdown] Homing timeout — proceeding with BV anyway")

                # Step 4: Save all variables to NV
                # BV can take several seconds after homing — wait then retry once
                _t.sleep(1.0)
                try:
                    ctrl.cmd("BV")
                except Exception:
                    logger.warning("[Shutdown] BV first attempt timed out — retrying")
                    _t.sleep(2.0)
                    ctrl.cmd("BV")
                logger.info("[Shutdown] BV done — all variables saved")

                Clock.schedule_once(lambda *_: setattr(self, 'motion_active', False))

            except Exception as e:
                msg = f"Shutdown failed: {e}"
                logger.error("[Shutdown] error: %s", e)
                Clock.schedule_once(lambda *_, m=msg: self._alert(m))
                Clock.schedule_once(lambda *_: setattr(self, 'motion_active', False))

        jobs.submit(_do_shutdown)

    def on_more_stone(self) -> None:
        """Send hmiMore=0 then read startPtB after delay to update label.

        Fires the HMI_MORE trigger, sleeps 800ms for the DMC subroutine to
        complete, then reads startPtB and updates the stone compensation label.
        """
        if not self.controller or not self.controller.is_connected():
            return
        ctrl = self.controller

        def _fire():
            import time as _time
            try:
                before_raw = ctrl.cmd(f"MG {STARTPT_B}").strip()
                before = int(float(before_raw))
                logger.debug("[SerrationRunScreen] More stone — startPtB BEFORE: %s", before)
            except Exception as e:
                logger.debug("[SerrationRunScreen] More stone — failed to read startPtB before: %s", e)

            try:
                ctrl.cmd(f"{HMI_MORE}={HMI_TRIGGER_FIRE}")
            except Exception as e:
                logger.error("[SerrationRunScreen] More stone failed: %s", e)
                return

            # Wait for DMC subroutine to finish, then retry readback
            for attempt in range(3):
                _time.sleep(1.0)
                try:
                    after_raw = ctrl.cmd(f"MG {STARTPT_B}").strip()
                    after = int(float(after_raw))
                    logger.debug("[SerrationRunScreen] More stone — startPtB AFTER: %s", after)
                    Clock.schedule_once(
                        lambda *_, v=after: setattr(self, 'start_pt_c', f"Stone Pos: {v:,}")
                    )
                    break
                except Exception as e:
                    logger.debug("[SerrationRunScreen] More stone — readback attempt %d failed: %s", attempt + 1, e)

        from ...utils.jobs import submit_urgent
        submit_urgent(_fire)

    def on_less_stone(self) -> None:
        """Send hmiLess=0 then read startPtB after delay to update label.

        Mirror of on_more_stone but fires HMI_LESS.
        """
        if not self.controller or not self.controller.is_connected():
            return
        ctrl = self.controller

        def _fire():
            import time as _time
            try:
                before_raw = ctrl.cmd(f"MG {STARTPT_B}").strip()
                before = int(float(before_raw))
                logger.debug("[SerrationRunScreen] Less stone — startPtB BEFORE: %s", before)
            except Exception as e:
                logger.debug("[SerrationRunScreen] Less stone — failed to read startPtB before: %s", e)

            try:
                ctrl.cmd(f"{HMI_LESS}={HMI_TRIGGER_FIRE}")
            except Exception as e:
                logger.error("[SerrationRunScreen] Less stone failed: %s", e)
                return

            # Wait for DMC subroutine to finish, then retry readback
            for attempt in range(3):
                _time.sleep(1.0)
                try:
                    after_raw = ctrl.cmd(f"MG {STARTPT_B}").strip()
                    after = int(float(after_raw))
                    logger.debug("[SerrationRunScreen] Less stone — startPtB AFTER: %s", after)
                    Clock.schedule_once(
                        lambda *_, v=after: setattr(self, 'start_pt_c', f"Stone Pos: {v:,}")
                    )
                    break
                except Exception as e:
                    logger.debug("[SerrationRunScreen] Less stone — readback attempt %d failed: %s", attempt + 1, e)

        from ...utils.jobs import submit_urgent
        submit_urgent(_fire)

    # -----------------------------------------------------------------------
    # Stone Compensation
    # -----------------------------------------------------------------------

    def _read_start_pt_c(self) -> None:
        """Background: read startPtB from controller and update stone comp label."""
        if not self.controller or not self.controller.is_connected():
            return
        ctrl = self.controller

        def _do():
            try:
                raw = ctrl.cmd(f"MG {STARTPT_B}").strip()
                val = int(float(raw))
                Clock.schedule_once(
                    lambda *_, v=val: setattr(self, 'start_pt_c', f"Stone Pos: {v:,}")
                )
            except Exception:
                Clock.schedule_once(lambda *_: setattr(self, 'start_pt_c', '---'))

        jobs.submit(_do)

    # -----------------------------------------------------------------------
    # Alert helper
    # -----------------------------------------------------------------------

    def _alert(self, message: str) -> None:
        """Push a message to the app-wide banner ticker."""
        try:
            from kivy.app import App
            app = App.get_running_app()
            if app and hasattr(app, "_log_message"):
                app._log_message(message)
                return
        except Exception:
            pass
        if self.state:
            self.state.log(message)

    # -----------------------------------------------------------------------
    # MG message handler (controller log) — called by app-wide MgReader
    # -----------------------------------------------------------------------

    def _on_mg_log(self, text: str) -> None:
        """Main thread: append a freeform MG log message (cap at 200 lines)."""
        lines = self.mg_log_text.split('\n') if self.mg_log_text else []
        lines.append(text)
        if len(lines) > 200:
            lines = lines[-200:]
        self.mg_log_text = '\n'.join(lines)
        # Auto-scroll the log
        log_view = self.ids.get("mg_log_scroll")
        if log_view:
            Clock.schedule_once(lambda *_: setattr(log_view, 'scroll_y', 0))

    # -----------------------------------------------------------------------
    # MG Message Reader — per-screen gclib handle for unsolicited messages
    # -----------------------------------------------------------------------

    def _start_mg_reader(self) -> None:
        """Open a second gclib handle subscribed to MG on a background thread."""
        if self._mg_thread is not None:
            return
        if not self.controller or not self.controller.is_connected():
            return

        addr = getattr(self.controller, '_address', '')
        if not addr:
            return

        self._mg_stop_event = threading.Event()
        self._mg_thread = threading.Thread(
            target=self._mg_reader_loop,
            args=(addr, self._mg_stop_event),
            daemon=True,
        )
        self._mg_thread.start()

    def _stop_mg_reader(self) -> None:
        """Signal MG reader thread to stop and join."""
        if self._mg_stop_event is not None:
            self._mg_stop_event.set()
        if self._mg_thread is not None:
            self._mg_thread.join(timeout=2.0)
            self._mg_thread = None
            self._mg_stop_event = None

    def _mg_reader_loop(self, address: str, stop_event: threading.Event) -> None:
        """Background thread: subscribe to MG via UDP and drain unsolicited messages."""
        try:
            import gclib  # type: ignore
        except ImportError:
            print("[SerrationRunScreen] MG reader: gclib not available")
            return

        handle = None
        try:
            handle = gclib.py()
            handle.GOpen(f"{address} --subscribe MG")
            handle.GTimeout(500)
            print(f"[SerrationRunScreen] MG reader connected: {address} --subscribe MG")
        except Exception as e:
            print(f"[SerrationRunScreen] MG reader open failed: {e}")
            if handle:
                try:
                    handle.GClose()
                except Exception:
                    pass
            return

        try:
            while not stop_event.is_set():
                try:
                    msg = handle.GMessage()
                    if msg:
                        for line in msg.strip().split('\n'):
                            line = line.strip()
                            if line:
                                Clock.schedule_once(
                                    lambda *_, t=line: self._on_mg_log(t)
                                )
                except Exception:
                    pass
        finally:
            try:
                handle.GClose()
            except Exception:
                pass
            print("[SerrationRunScreen] MG reader closed")
