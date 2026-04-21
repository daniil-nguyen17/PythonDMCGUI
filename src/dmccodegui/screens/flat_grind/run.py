"""FlatGrindRunScreen — operator run screen with live axis positions and cycle monitoring."""
from __future__ import annotations

import threading
import time
from collections import deque

from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Line, Rectangle
from kivy.properties import (
    BooleanProperty,
    ListProperty,
    NumericProperty,
    StringProperty,
)
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
import matplotlib.pyplot  # noqa: F401 — required by kivy_matplotlib_widget internals
import kivy_matplotlib_widget  # noqa: F401 — registers MatplotFigure in Kivy Factory

from ...app_state import MachineState
from ...controller import GalilController
from ...hmi.dmc_vars import (
    STATE_GRINDING, STATE_HOMING,
    HMI_GRND, HMI_MORE, HMI_LESS, HMI_TRIGGER_FIRE,
    STARTPT_C,
    POS_BUF_IDX, POS_BUF_A, POS_BUF_B, POS_BUF_SIZE,
)
from ...hmi.poll import read_all_state
from ...utils import jobs
import dmccodegui.machine_config as mc
from ..base import BaseRunScreen
from .widgets import (
    DeltaCBarChart,
    ImageButton,
    _BaseBarChart,
    ARROW_UP_IMG,
    ARROW_DOWN_IMG,
    DELTA_C_WRITABLE_START,
    DELTA_C_WRITABLE_END,
    DELTA_C_ARRAY_SIZE,
    DELTA_C_STEP,
    STONE_SURFACE_MM,
    STONE_OVERHANG_MM,
    STEP_MM,
    STONE_WINDOW_INDICES,
    stone_window_for_index,
)


# Controller variable names for cycle status (configurable for different controller programs)
CYCLE_VAR_TOOTH = "tooth"
CYCLE_VAR_PASS = "pass_num"
CYCLE_VAR_DEPTH = "depth"

# ---------------------------------------------------------------------------
# Live A/B Position Plot constants
# ---------------------------------------------------------------------------
PLOT_UPDATE_HZ: int = 5       # Hz — plot redraw rate; tuning point: lower to 2-3 if Pi CPU load is too high
PLOT_BUFFER_SIZE: int = 750   # points — rolling history buffer; tuning point: reduce to 300 if Pi memory is constrained

# Theme-matched colors for matplotlib (hex strings, not Kivy RGBA lists)
BG_PANEL_HEX = "#0D1219"     # matches theme.bg_panel
TICK_COLOR = "#94A1B5"        # matches theme.text_mid
TRAIL_COLOR = "#7DF9FF"       # electric cyan — high contrast on dark navy
## TOOLPATH_COLOR removed — toolpath preview disabled to prevent jobs queue blocking

# ---------------------------------------------------------------------------
# Delta-C constants and DeltaCBarChart are imported from .widgets.
# They remain accessible as run.DELTA_C_WRITABLE_START etc. via the imports above
# for backward compatibility with existing test_delta_c_bar_chart.py imports.
# ---------------------------------------------------------------------------


def _format_mmss(seconds: float) -> str:
    """Format a duration in seconds as MM:SS string."""
    if seconds < 0:
        seconds = 0.0
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"


class FlatGrindRunScreen(BaseRunScreen):
    """
    FlatGrindRunScreen — core operator screen for monitoring and controlling grinding cycles.

    Layout: two-column (left: plot placeholder + adjustment placeholder,
            right: cycle status + axis positions), bottom action bar.

    Threading model:
      - MachineState.subscribe() delivers state changes from the centralized poller
      - _apply_state() is the single path for updating all Kivy properties
      - Plot redraws run on a separate 5 Hz clock to protect E-STOP latency

    Inherits controller/state ObjectProperties and subscribe/unsubscribe lifecycle
    from BaseRunScreen.

    KV file: ui/flat_grind/run.kv
    """

    # Kivy properties — bound in run.kv
    # NOTE: FlatGrindRunScreen.cycle_running is a Kivy BooleanProperty (for KV bindings/opacity).
    # MachineState.cycle_running is a Python @property derived from dmc_state.
    # These are distinct — _apply_state bridges the two.
    cycle_running = BooleanProperty(False)
    # motion_active is True when dmc_state is GRINDING or HOMING, or when disconnected.
    # KV binds disabled: root.motion_active on all motion-triggering buttons.
    # The STOP button is visible (opacity=1) only when motion_active is True.
    motion_active = BooleanProperty(False)
    cycle_tooth = StringProperty("0")
    cycle_pass = StringProperty("0")
    cycle_depth = StringProperty("0.00")
    cycle_elapsed = StringProperty("00:00")
    cycle_eta = StringProperty("--:--")
    cycle_completion_pct = NumericProperty(0)

    # Axis position strings — default to disconnected indicator
    pos_a = StringProperty("---")
    pos_b = StringProperty("---")
    pos_c = StringProperty("---")
    pos_d = StringProperty("---")

    # CPM (counts per unit) annotation strings
    cpm_a = StringProperty("")
    cpm_b = StringProperty("")
    cpm_c = StringProperty("")
    cpm_d = StringProperty("")

    # Machine type flag — updated dynamically on every on_pre_enter via mc.is_serration()
    # Controls serration field visibility in KV (cycle status tooth/pass/depth)
    is_serration = BooleanProperty(False)

    # Knife Grind Adjustment properties (Delta-C — Flat/Convex)
    section_count = NumericProperty(1)
    delta_c_offsets = ListProperty([0.0])        # one offset per section
    selected_section_value = StringProperty("0") # display value for the selected bar
    # Compensation mode: "cumulative" or "spline"
    comp_mode = StringProperty("cumulative")

    # Knife count display strings (Phase 10)
    session_knife_count = StringProperty("0")
    stone_knife_count = StringProperty("0")

    # Stone Compensation readback — persistent label in Stone Compensation card (Phase 15)
    start_pt_c = StringProperty("---")

    # Disconnect banner (empty string = no banner visible)
    disconnect_banner = StringProperty("")

    # MG message log — scrollable text on Run page for controller debug output
    mg_log_text = StringProperty("")

    # -----------------------------------------------------------------------
    # Internal state
    # -----------------------------------------------------------------------
    # NOTE: _state_unsub is owned by BaseRunScreen — do NOT shadow it here
    _plot_clock_event = None
    _disconnect_clock = None     # 1 Hz elapsed time updater for disconnect banner
    _disconnect_t0: float | None = None   # monotonic time of disconnect start
    _plot_buf_x: deque = None  # type: ignore — initialized in __init__
    _plot_buf_y: deque = None  # type: ignore
    _fig = None
    _ax = None
    _plot_line = None
    _cycle_start_time: float | None = None
    _last_cycle_duration: float | None = None  # total seconds of last completed grind
    _elapsed_clock_event = None
    _cpm_a_raw: float = 1200.0  # counts per mm — updated by _read_cpm_values
    _cpm_b_raw: float = 1200.0
    ## Toolpath preview disabled — was causing jobs queue blocking
    _pos_clock_event = None  # lightweight position poll (replaces centralized poller on Run)
    _pos_busy: bool = False  # guard: skip tick if previous read still in flight
    _mg_thread: threading.Thread | None = None
    _mg_stop_event: threading.Event | None = None
    _grind_cmd_time: float | None = None  # monotonic time of last on_start_grind — grace period for state transition
    _GRIND_GRACE_SEC: float = 2.0  # seconds to wait before allowing grind-end detection

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._plot_buf_x = deque(maxlen=PLOT_BUFFER_SIZE)
        self._plot_buf_y = deque(maxlen=PLOT_BUFFER_SIZE)

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    def on_kv_post(self, base_widget) -> None:
        """Called by Kivy after all KV ids are assigned.

        Binds the DeltaCBarChart selection observer so selected_section_value
        stays in sync with whichever bar the operator taps.
        Initializes the MatplotFigure plot widget for the live A/B position trail.
        """
        chart = self.ids.get("delta_c_chart")
        if chart is not None:
            chart.bind(selected_index=self._on_chart_selection_changed)

        self._rebuild_section_buttons(max(1, int(self.section_count)))

        plot_wgt = self.ids.get("ab_plot")
        if plot_wgt is not None:
            self._fig = Figure(figsize=(4, 3), facecolor=BG_PANEL_HEX)
            self._ax = self._fig.add_subplot(111)
            self._configure_plot_axes()
            # Live A/B trace
            self._plot_line, = self._ax.plot(
                [], [], color=TRAIL_COLOR, linewidth=1.2, label='THUC TE',
            )
            plot_wgt.figure = self._fig
            # Disable all touch interaction — preserves E-STOP responsiveness
            plot_wgt.do_pan_x = False
            plot_wgt.do_pan_y = False
            plot_wgt.do_scale = False
            plot_wgt.touch_mode = 'none'
            plot_wgt.disable_mouse_scrolling = True

    def on_pre_enter(self, *args) -> None:
        """Called by Kivy when operator navigates to this screen.

        Polling strategy:
          1. One-shot read on entry to populate positions/state
          2. NO continuous polling while idle (buttons stay stable)
          3. Continuous 5 Hz poll starts when START GRIND is pressed
          4. Poll stops after grind ends (one final read included)
          5. MG reader stays active for controller log messages
        """
        # BaseRunScreen.on_pre_enter subscribes to MachineState (disconnect detection)
        super().on_pre_enter(*args)

        # Apply machine-type-specific widget visibility
        self._apply_machine_type_widgets()

        # Single batched one-shot read: positions, state, CPMs, startPts, stone arcs
        # All reads run in ONE job so no response collisions with user commands
        self._do_page_load_read()

        # Start plot redraw clock (lightweight — just redraws existing buffer)
        self._plot_clock_event = Clock.schedule_interval(self._tick_plot, 1.0 / PLOT_UPDATE_HZ)

        # Start per-screen MG reader (own gclib handle, --subscribe MG)
        self._start_mg_reader()

    def on_leave(self, *args) -> None:
        """Called by Kivy when operator navigates away.

        Cancels screen-specific clocks, then delegates unsubscribe to BaseRunScreen.
        """
        # Cancel screen-specific clocks BEFORE super().on_leave() fires unsubscribe
        # (per Pitfall #1: threads/clocks must stop before listener list is cleared)
        if self._disconnect_clock:
            self._disconnect_clock.cancel()
            self._disconnect_clock = None
            self._disconnect_t0 = None
        self._stop_pos_poll()
        if self._elapsed_clock_event:
            self._elapsed_clock_event.cancel()
            self._elapsed_clock_event = None
        if self._plot_clock_event:
            self._plot_clock_event.cancel()
            self._plot_clock_event = None
        # Stop per-screen MG reader thread
        self._stop_mg_reader()

        # BaseRunScreen.on_leave unsubscribes from MachineState
        super().on_leave(*args)

    # -----------------------------------------------------------------------
    # Machine type widget switching
    # -----------------------------------------------------------------------

    def _apply_machine_type_widgets(self) -> None:
        """Toggle panel and row visibility based on the active machine type.

        Called on every on_pre_enter so hot-swapping machine type takes effect
        immediately when the operator re-enters this screen.

        Uses opacity/disabled swap (NOT widget add/remove) to preserve KV ids.
        """
        serration = False
        try:
            serration = mc.is_serration()
        except ValueError:
            # machine_config not yet configured — fall back to non-serration layout
            pass

        self.is_serration = serration

        # Delta-C panel: visible on Flat/Convex, collapsed on Serration
        delta_c_panel = self.ids.get("delta_c_panel")
        if delta_c_panel is not None:
            delta_c_panel.opacity = 0.0 if serration else 1.0
            delta_c_panel.disabled = serration
            delta_c_panel.height = 0 if serration else 185

        # D axis position row: hidden on Serration
        pos_d_row = self.ids.get("pos_d_row")
        if pos_d_row is not None:
            pos_d_row.opacity = 0.0 if serration else 1.0

    # -----------------------------------------------------------------------
    # State subscription handler
    # -----------------------------------------------------------------------

    def _on_state_change(self, state) -> None:
        """BaseRunScreen lifecycle hook — delegates to _apply_state."""
        self._apply_state(state)

    def _apply_state(self, s: MachineState) -> None:
        """Main thread: apply DR state updates — positions, grind detection, disconnect.

        Called on every DataRecordListener packet (~5-10 Hz). Acts as the
        primary source of truth for positions and state. The TCP poll in
        _tick_pos() is kept as a secondary/fallback source; when both fire,
        Kivy properties deduplicate identical values (no-op assignment).
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

            # --- Position updates from DR ---
            a = s.pos.get("A", 0.0)
            b = s.pos.get("B", 0.0)
            c = s.pos.get("C", 0.0)
            d = s.pos.get("D", 0.0)
            self.pos_a = f"{int(a):,}"
            self.pos_b = f"{int(b):,}"
            self.pos_c = f"{int(c):,}"
            self.pos_d = f"{int(d):,}"

            # --- Knife counts + stone position from DR ---
            self.session_knife_count = str(s.session_knife_count)
            self.stone_knife_count = str(s.stone_knife_count)
            if s.start_pt_c:
                self.start_pt_c = f"Stone Pos: {s.start_pt_c:,}"

            # --- Grind state detection from DR ---
            dmc_state = s.dmc_state
            now_grinding = dmc_state == STATE_GRINDING

            if now_grinding:
                # Feed plot buffer from DR positions
                self._plot_buf_x.append(a)
                self._plot_buf_y.append(b)

                # Ensure buttons are grayed out
                if not self.motion_active:
                    self.motion_active = True
                if not self.cycle_running:
                    self.cycle_running = True

                # Start polling if not already running (catches late grind detection)
                if self._pos_clock_event is None:
                    self._start_pos_poll()

            elif self.cycle_running and not now_grinding and dmc_state != 0:
                # Grace period: don't detect grind-end within 2s of pressing
                # Start Grind — the controller needs time to transition from
                # IDLE to GRINDING.  Without this, stale IDLE state from DR
                # (in-flight before hmiGrnd=0 was sent) causes false grind-end.
                if self._grind_cmd_time is not None:
                    elapsed = _time.monotonic() - self._grind_cmd_time
                    if elapsed < self._GRIND_GRACE_SEC:
                        return  # too soon — ignore this state update
                # Grind ended: DR says no longer grinding
                self._grind_cmd_time = None
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

    def _tick_disconnect_banner(self, dt: float) -> None:
        """1 Hz callback: update disconnect elapsed time banner."""
        import time as _time
        if self._disconnect_t0 is not None:
            elapsed = int(_time.monotonic() - self._disconnect_t0)
            self.disconnect_banner = f"DISCONNECTED ({elapsed}s)"

    def _show_disconnected(self) -> None:
        """Show disconnected state: '---' for all positions."""
        self.pos_a = "---"
        self.pos_b = "---"
        self.pos_c = "---"
        self.pos_d = "---"

    # -----------------------------------------------------------------------
    # Lightweight position poll — only runs during grind cycle
    # -----------------------------------------------------------------------

    def _do_page_load_read(self) -> None:
        """Single batched job: read ALL controller state on page entry.

        Combines positions, state, CPMs, startPtC, startPtA/B, and contour
        arrays into ONE sequential job. This prevents response collisions
        with user commands (deltaC writes) since everything completes before
        the user can interact.
        """
        if not self.controller or not self.controller.is_connected():
            return
        ctrl = self.controller

        def _do():
            # 1. Positions + state
            result = read_all_state(ctrl)
            if result is None:
                return
            a, b, c, d, dmc_state, ses_kni, stn_kni, program_running = result

            # 2. CPM values
            _CPM_DEFAULTS = {"A": 1200.0, "B": 1200.0, "C": 800.0, "D": 360000.0}
            cpm_results: dict[str, float] = {}
            for axis in ("A", "B", "C", "D"):
                try:
                    raw = ctrl.cmd(f"MG cpm{axis}").strip()
                    cpm_results[axis] = float(raw)
                except Exception:
                    cpm_results[axis] = _CPM_DEFAULTS.get(axis, 1.0)

            # 3. startPtC
            start_c_val = None
            try:
                from ...hmi.dmc_vars import STARTPT_C
                raw = ctrl.cmd(f"MG {STARTPT_C}").strip()
                start_c_val = int(float(raw))
            except Exception:
                pass

            # 4. Read existing deltaC array (baseline from profile/previous session)
            existing_delta_c = None
            try:
                raw_dc = ctrl.upload_array_auto("deltaC")
                if raw_dc:
                    existing_delta_c = [float(v) for v in raw_dc]
                    print(f"[FlatGrindRunScreen] Read existing deltaC: {len(existing_delta_c)} elements")
            except Exception:
                pass

            # 5. startPtA/B + contour arrays
            start_a_mm, start_b_mm = None, None
            contour_a_mm, contour_b_mm = None, None
            try:
                from ...hmi.dmc_vars import STARTPT_A, STARTPT_B
                start_a = float(ctrl.cmd(f"MG {STARTPT_A}").strip())
                start_b = float(ctrl.cmd(f"MG {STARTPT_B}").strip())
                cpm_a = cpm_results.get("A", 1200.0)
                cpm_b = cpm_results.get("B", 1200.0)
                start_a_mm = start_a / cpm_a
                start_b_mm = start_b / cpm_b

                delta_a = ctrl.upload_array_auto("deltaA")
                delta_b = ctrl.upload_array_auto("deltaB")
                if delta_a and delta_b:
                    n = min(len(delta_a), len(delta_b))
                    acc_a, acc_b = start_a, start_b
                    ca, cb = [start_a_mm], [start_b_mm]
                    for k in range(n):
                        acc_a += delta_a[k]
                        acc_b += delta_b[k]
                        ca.append(acc_a / cpm_a)
                        cb.append(acc_b / cpm_b)
                    contour_a_mm = ca
                    contour_b_mm = cb
            except Exception:
                pass

            def _apply(*_):
                # Positions
                self.pos_a = f"{int(a):,}"
                self.pos_b = f"{int(b):,}"
                self.pos_c = f"{int(c):,}"
                self.pos_d = f"{int(d):,}"
                self.session_knife_count = str(ses_kni)
                self.stone_knife_count = str(stn_kni)
                # Guard: don't overwrite if on_start_grind already fired
                if not self.cycle_running:
                    self.cycle_running = dmc_state == STATE_GRINDING
                if not self.motion_active:
                    self.motion_active = dmc_state in (STATE_GRINDING, STATE_HOMING)

                # CPMs
                for axis, cpm in cpm_results.items():
                    prop = f"cpm_{axis.lower()}"
                    if hasattr(self, prop):
                        setattr(self, prop, f"{cpm:.0f} cts/mm")
                    if axis == "A":
                        self._cpm_a_raw = cpm
                    elif axis == "B":
                        self._cpm_b_raw = cpm

                # startPtC
                if start_c_val is not None:
                    self.start_pt_c = f"Stone Pos: {start_c_val:,}"

                # Stone arcs + contour
                if start_a_mm is not None and start_b_mm is not None:
                    self._draw_stone(
                        start_a_mm, start_b_mm, contour_a_mm, contour_b_mm
                    )

                # Store baseline deltaC from controller (profile/previous session)
                if existing_delta_c is not None:
                    self._controller_delta_c = existing_delta_c
                    self._last_delta_c = list(existing_delta_c)
                else:
                    self._controller_delta_c = [0.0] * DELTA_C_ARRAY_SIZE
                    self._last_delta_c = [0.0] * DELTA_C_ARRAY_SIZE

                # If already grinding when we enter, start polling
                if self.cycle_running:
                    self._start_pos_poll()

            Clock.schedule_once(_apply)

        jobs.submit(_do)

    def _start_pos_poll(self) -> None:
        """Start 5 Hz position polling. Called when grind starts."""
        if self._pos_clock_event is not None:
            return
        self._pos_clock_event = Clock.schedule_interval(self._tick_pos, 1.0 / PLOT_UPDATE_HZ)

    def _stop_pos_poll(self) -> None:
        """Stop position polling. Called when grind ends or on_leave."""
        if self._pos_clock_event is not None:
            self._pos_clock_event.cancel()
            self._pos_clock_event = None
        self._pos_busy = False

    def _set_poll_rate(self, hz: float) -> None:
        """Switch position poll rate (e.g., 5 Hz idle, 1 Hz during grind)."""
        if self._pos_clock_event is not None:
            self._pos_clock_event.cancel()
        self._pos_clock_event = Clock.schedule_interval(self._tick_pos, 1.0 / hz)

    def _tick_elapsed(self, dt: float) -> None:
        """1 Hz clock: update elapsed time display only. ETA/progress driven by _tick_pos."""
        if self._cycle_start_time is None:
            return
        elapsed = time.monotonic() - self._cycle_start_time
        self.cycle_elapsed = _format_mmss(elapsed)

    def _stop_elapsed(self) -> None:
        """Stop the elapsed timer and record cycle duration."""
        if self._elapsed_clock_event is not None:
            self._elapsed_clock_event.cancel()
            self._elapsed_clock_event = None
        if self._cycle_start_time is not None:
            self._last_cycle_duration = time.monotonic() - self._cycle_start_time
            self.cycle_completion_pct = 100
            self.cycle_eta = "00:00"
            self._cycle_start_time = None

    def _tick_pos(self, dt: float) -> None:
        """5 Hz clock: read positions + state from controller in background.

        Uses a busy guard to prevent job pileup — if the previous read is still
        in the jobs queue or in-flight, this tick is skipped. This prevents the
        FIFO queue from backing up and blocking operator commands.

        Uses read_all_state() for a single batched MG command covering all 8 values.
        """
        if self._pos_busy:
            return  # previous read still in flight — skip this tick
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

            # Bail early if urgent job is waiting (e.g., Start Grind)
            if cancel.is_set():
                self._pos_busy = False
                return

            a, b, c, d, dmc_state, ses_kni, stn_kni, program_running = result

            def _apply(*_):
                self._pos_busy = False  # ready for next tick
                # Update positions on screen
                self.pos_a = f"{int(a):,}"
                self.pos_b = f"{int(b):,}"
                self.pos_c = f"{int(c):,}"
                self.pos_d = f"{int(d):,}"
                # Feed plot buffer only during grind
                if dmc_state == STATE_GRINDING:
                    self._plot_buf_x.append(a)
                    self._plot_buf_y.append(b)
                # Update knife counts
                self.session_knife_count = str(ses_kni)
                self.stone_knife_count = str(stn_kni)
                # Detect grind end: was grinding, now idle → stop polling
                # Grace period: don't detect grind-end within 2s of pressing
                # Start Grind — controller needs time to transition state.
                was_grinding = self.cycle_running
                new_grinding = dmc_state == STATE_GRINDING
                if was_grinding and not new_grinding:
                    if self._grind_cmd_time is not None:
                        import time as _t2
                        if (_t2.monotonic() - self._grind_cmd_time) < self._GRIND_GRACE_SEC:
                            return  # too soon — skip this tick
                    self._grind_cmd_time = None
                    self.cycle_running = False
                    self.motion_active = False
                    self._stop_pos_poll()
                    self._stop_elapsed()
                    self._read_start_pt_c()  # refresh Stone Pos after auto wear
            Clock.schedule_once(_apply)

        jobs.submit(_do)

    def _configure_plot_axes(self) -> None:
        """Style the A/B position plot axes to match machine orientation.

        X = A axis (mm): positive (heel ~257mm) on LEFT, 0 (tip) on RIGHT
        Y = B axis (mm): negative on TOP, positive on BOTTOM
        """
        ax = self._ax
        self._fig.patch.set_facecolor(BG_PANEL_HEX)
        ax.set_facecolor(BG_PANEL_HEX)
        ax.set_aspect("auto")
        ax.tick_params(colors=TICK_COLOR, labelsize=7, length=3, width=0.5)
        for spine in ax.spines.values():
            spine.set_edgecolor(TICK_COLOR)
            spine.set_linewidth(0.5)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
        ax.set_xlabel("A  (mm)   GOT <-          -> MUI", fontsize=8, color=TICK_COLOR)
        ax.set_ylabel("B  (mm)", fontsize=8, color=TICK_COLOR)
        ax.invert_xaxis()   # positive (heel) on left, 0 (tip) on right
        ax.invert_yaxis()   # negative on top, positive on bottom
        ax.grid(False)
        self._fig.subplots_adjust(left=0.12, right=0.97, top=0.97, bottom=0.18)

    def _tick_plot(self, dt: float) -> None:
        """5 Hz Kivy clock: redraw the live A/B trace in mm. Main thread only."""
        if self._plot_line is None:
            return
        xs_raw = list(self._plot_buf_x)
        ys_raw = list(self._plot_buf_y)
        if len(xs_raw) < 2:
            return
        cpm_a = self._cpm_a_raw
        cpm_b = self._cpm_b_raw
        xs = [v / cpm_a for v in xs_raw]
        ys = [v / cpm_b for v in ys_raw]
        self._plot_line.set_data(xs, ys)
        self._ax.relim()
        self._ax.autoscale_view()
        self._fig.canvas.draw_idle()

    # -----------------------------------------------------------------------
    # Action handlers
    # -----------------------------------------------------------------------

    def on_stop(self) -> None:
        """Send ST ABCD via submit_urgent — preempts polls, thread-safe."""
        if not self.controller or not self.controller.is_connected():
            return
        def do_stop():
            try:
                self.controller.cmd("ST ABCD")
            except Exception as e:
                msg = f"Stop failed: {e}"
                Clock.schedule_once(lambda *_, m=msg: self._alert(m))
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
                print("[Shutdown] hmiSetp fired — entering setup")
                _t.sleep(0.5)

                # Step 2: Trigger homing
                ctrl.cmd(f"{HMI_HOME}={HMI_TRIGGER_FIRE}")
                print("[Shutdown] hmiHome fired — homing axes")

                # Step 3: Wait for homing to complete (poll hmiState)
                # hmiState goes 4 (HOMING) during home, returns to 3 (SETUP) when done
                for _ in range(120):  # max 60 seconds (120 × 0.5s)
                    _t.sleep(0.5)
                    try:
                        raw = ctrl.cmd(f"MG {HMI_STATE_VAR}").strip()
                        state = int(float(raw))
                        if state == STATE_SETUP:
                            print("[Shutdown] Homing complete — state back to SETUP")
                            break
                    except Exception:
                        pass
                else:
                    print("[Shutdown] Homing timeout — proceeding with BV anyway")

                # Step 4: Save all variables to NV
                # BV can take several seconds — wait then retry once
                _t.sleep(1.5)
                try:
                    ctrl.cmd("BV")
                except Exception:
                    print("[Shutdown] BV first attempt timed out — retrying")
                    _t.sleep(2.0)
                    ctrl.cmd("BV")
                print("[Shutdown] BV done — all variables saved")

                Clock.schedule_once(lambda *_: setattr(self, 'motion_active', False))

            except Exception as e:
                msg = f"Shutdown failed: {e}"
                print(f"[Shutdown] error: {e}")
                Clock.schedule_once(lambda *_, m=msg: self._alert(m))
                Clock.schedule_once(lambda *_: setattr(self, 'motion_active', False))

        jobs.submit(_do_shutdown)

    def on_start_grind(self) -> None:
        """Send hmiGrnd=0 via jobs.submit to start/continue grinding cycle.

        Clears the A/B position plot trail so each cycle gets a fresh view.
        Uses the HMI one-shot trigger pattern — never XQ direct calls.
        Guards: cannot start grind while in SETUP mode or during active motion.
        """
        if not self.controller or not self.controller.is_connected():
            return
        # Guard: don't fire hmiGrnd if already in motion or cycle running
        # Uses self.motion_active (updated by _tick_pos) not self.state.dmc_state (stale)
        if self.motion_active or self.cycle_running:
            return

        # Clear live trace for fresh cycle view; toolpath ghost line stays
        self._plot_buf_x.clear()
        self._plot_buf_y.clear()
        if self._plot_line is not None:
            self._plot_line.set_data([], [])
            if self._fig and self._fig.canvas:
                self._fig.canvas.draw_idle()

        # Start elapsed timer
        self._cycle_start_time = time.monotonic()
        self.cycle_elapsed = "00:00"
        if self._last_cycle_duration is not None:
            self.cycle_eta = _format_mmss(self._last_cycle_duration)
        else:
            self.cycle_eta = "--:--"
        self.cycle_completion_pct = 0
        if self._elapsed_clock_event is None:
            self._elapsed_clock_event = Clock.schedule_interval(self._tick_elapsed, 1.0)

        # Send grind command via submit_urgent — preempts any queued polls,
        # fires instantly. cancel_event causes in-flight _tick_pos to bail early.
        def _fire():
            try:
                self.controller.cmd(f"{HMI_GRND}={HMI_TRIGGER_FIRE}")
            except Exception as e:
                msg = f"Start failed: {e}"
                Clock.schedule_once(lambda *_, m=msg: self._alert(m))

        jobs.submit_urgent(_fire)

        # Immediately disable grind button and enable stop button
        self._grind_cmd_time = time.monotonic()  # grace period starts now
        self.motion_active = True
        self.cycle_running = True

        # Start position polling for grind monitoring
        self._start_pos_poll()

    def on_more_stone(self) -> None:
        """Send hmiMore=0 then read startPtC after delay to update persistent label.

        Fires the HMI_MORE trigger, then retries readback up to 3 times (1s apart)
        to give the DMC subroutine time to finish updating startPtC.
        """
        if not self.controller or not self.controller.is_connected():
            return

        ctrl = self.controller

        def _fire():
            import time as _time
            try:
                before_raw = ctrl.cmd(f"MG {STARTPT_C}").strip()
                before = int(float(before_raw))
                print(f"[FlatGrindRunScreen] More stone — startPtC BEFORE: {before}")
            except Exception as e:
                print(f"[FlatGrindRunScreen] More stone — failed to read startPtC before: {e}")

            try:
                ctrl.cmd(f"{HMI_MORE}={HMI_TRIGGER_FIRE}")
            except Exception as e:
                msg = f"More stone failed: {e}"
                Clock.schedule_once(lambda *_, m=msg: self._alert(m))
                return

            # Wait for DMC subroutine to finish, then retry readback
            for attempt in range(3):
                _time.sleep(1.0)
                try:
                    after_raw = ctrl.cmd(f"MG {STARTPT_C}").strip()
                    after = int(float(after_raw))
                    print(f"[FlatGrindRunScreen] More stone — startPtC AFTER: {after}")
                    Clock.schedule_once(
                        lambda *_, v=after: setattr(self, 'start_pt_c', f"Stone Pos: {v:,}")
                    )
                    break
                except Exception as e:
                    print(f"[FlatGrindRunScreen] More stone — readback attempt {attempt + 1} failed: {e}")

        from ...utils.jobs import submit_urgent
        submit_urgent(_fire)

    def on_less_stone(self) -> None:
        """Send hmiLess=0 then read startPtC after delay to update persistent label.

        Mirror of on_more_stone but fires HMI_LESS. Retries readback up to 3 times
        (1s apart) to give the DMC subroutine time to finish updating startPtC.
        """
        if not self.controller or not self.controller.is_connected():
            return

        ctrl = self.controller

        def _fire():
            import time as _time
            try:
                before_raw = ctrl.cmd(f"MG {STARTPT_C}").strip()
                before = int(float(before_raw))
                print(f"[FlatGrindRunScreen] Less stone — startPtC BEFORE: {before}")
            except Exception as e:
                print(f"[FlatGrindRunScreen] Less stone — failed to read startPtC before: {e}")

            try:
                ctrl.cmd(f"{HMI_LESS}={HMI_TRIGGER_FIRE}")
            except Exception as e:
                msg = f"Less stone failed: {e}"
                Clock.schedule_once(lambda *_, m=msg: self._alert(m))
                return

            # Wait for DMC subroutine to finish, then retry readback
            for attempt in range(3):
                _time.sleep(1.0)
                try:
                    after_raw = ctrl.cmd(f"MG {STARTPT_C}").strip()
                    after = int(float(after_raw))
                    print(f"[FlatGrindRunScreen] Less stone — startPtC AFTER: {after}")
                    Clock.schedule_once(
                        lambda *_, v=after: setattr(self, 'start_pt_c', f"Stone Pos: {v:,}")
                    )
                    break
                except Exception as e:
                    print(f"[FlatGrindRunScreen] Less stone — readback attempt {attempt + 1} failed: {e}")

        from ...utils.jobs import submit_urgent
        submit_urgent(_fire)

    # -----------------------------------------------------------------------
    # Delta-C (Knife Grind Adjustment) — Flat/Convex machines
    # -----------------------------------------------------------------------

    def on_section_count_change(self, value: int) -> None:
        """Clamp section count to 1-10 and resize delta_c_offsets list.

        Preserves existing offset values; pads with 0.0 for new sections;
        truncates when count decreases.
        """
        clamped = max(1, min(10, int(value)))
        self.section_count = clamped
        old = list(self.delta_c_offsets)
        self.delta_c_offsets = (old + [0.0] * clamped)[:clamped]
        self._rebuild_section_buttons(clamped)

    def _rebuild_section_buttons(self, n: int) -> None:
        """Rebuild per-section up/down arrow buttons to match the bar count.

        Images are flipped 180° so subtract arrows point up and add arrows
        point down, matching the bar direction they affect.
        """
        from kivy.graphics import PushMatrix, PopMatrix, Rotate

        up_row = self.ids.get("adjust_up_row")
        down_row = self.ids.get("adjust_down_row")
        if up_row is None or down_row is None:
            return

        up_row.clear_widgets()
        down_row.clear_widgets()

        def _flip_widget(widget):
            """Rotate a widget 180° around its centre."""
            with widget.canvas.before:
                PushMatrix()
                rot = Rotate(angle=180)
            with widget.canvas.after:
                PopMatrix()
            def _update_origin(*_a, w=widget, r=rot):
                r.origin = w.center
            widget.bind(pos=_update_origin, size=_update_origin)

        for i in range(n):
            # Subtract row (top): red down-arrow image flipped → points up
            down_btn = ImageButton(
                source=ARROW_DOWN_IMG,
                size_hint=(1, 1),
                allow_stretch=True,
                keep_ratio=True,
            )
            _flip_widget(down_btn)
            down_btn.bind(on_release=lambda btn, idx=i: self._adjust_section(idx, -1))
            down_row.add_widget(down_btn)

            # Add row (bottom): green up-arrow image flipped → points down
            up_btn = ImageButton(
                source=ARROW_UP_IMG,
                size_hint=(1, 1),
                allow_stretch=True,
                keep_ratio=True,
            )
            _flip_widget(up_btn)
            up_btn.bind(on_release=lambda btn, idx=i: self._adjust_section(idx, 1))
            up_row.add_widget(up_btn)

    def _adjust_section(self, index: int, direction: int) -> None:
        """Adjust a specific section's offset and select it on the chart."""
        chart = self.ids.get("delta_c_chart")
        if chart is not None:
            chart.selected_index = index
        if index < 0 or index >= len(self.delta_c_offsets):
            return
        offsets = list(self.delta_c_offsets)
        offsets[index] += direction * DELTA_C_STEP
        self.delta_c_offsets = offsets
        self.selected_section_value = str(int(self.delta_c_offsets[index]))

    def _on_chart_selection_changed(self, chart_widget, selected_index: int) -> None:
        """Observer bound to delta_c_chart.selected_index via on_kv_post.

        Updates selected_section_value so the 'Selected: X cts' label refreshes
        whenever the operator taps a bar or the selection is cleared.
        """
        idx = int(selected_index)
        if 0 <= idx < len(self.delta_c_offsets):
            self.selected_section_value = str(int(self.delta_c_offsets[idx]))
        else:
            self.selected_section_value = "0"

    def on_adjust_up(self) -> None:
        """Add DELTA_C_STEP to the currently selected bar's offset."""
        chart = self.ids.get("delta_c_chart")
        if chart is None:
            return
        idx = int(chart.selected_index)
        if idx < 0 or idx >= len(self.delta_c_offsets):
            return
        offsets = list(self.delta_c_offsets)
        offsets[idx] += DELTA_C_STEP
        self.delta_c_offsets = offsets
        self.selected_section_value = str(int(self.delta_c_offsets[idx]))

    def on_adjust_down(self) -> None:
        """Subtract DELTA_C_STEP from the currently selected bar's offset."""
        chart = self.ids.get("delta_c_chart")
        if chart is None:
            return
        idx = int(chart.selected_index)
        if idx < 0 or idx >= len(self.delta_c_offsets):
            return
        offsets = list(self.delta_c_offsets)
        offsets[idx] -= DELTA_C_STEP
        self.delta_c_offsets = offsets
        self.selected_section_value = str(int(self.delta_c_offsets[idx]))

    def toggle_comp_mode(self) -> None:
        """Toggle between cumulative and spline compensation modes."""
        if self.comp_mode == "cumulative":
            self.comp_mode = "spline"
        else:
            self.comp_mode = "cumulative"
        print(f"[FlatGrindRunScreen] Compensation mode: {self.comp_mode}")

    def on_clear_delta_c(self) -> None:
        """Reset all section offsets to zero."""
        n = max(1, int(self.section_count))
        self.delta_c_offsets = [0.0] * n
        chart = self.ids.get("delta_c_chart")
        if chart is not None:
            idx = int(chart.selected_index)
            if 0 <= idx < n:
                self.selected_section_value = "0"

    def on_apply_delta_c(self) -> None:
        """Add bar adjustments ON TOP of existing deltaC values and send to controller.

        The deltaC array was loaded from a profile (CSV import or previous BV).
        The bar offsets represent ADJUSTMENTS to that baseline — not replacements.
        Final value = baseline + bar adjustment.
        Only sends indices that actually changed from what's currently on the controller.
        """
        if not self.controller or not self.controller.is_connected():
            return
        adjustments = self._offsets_to_delta_c()
        ctrl = self.controller

        # Add adjustments on top of the baseline read from controller
        baseline = getattr(self, '_controller_delta_c', None)
        if baseline is None:
            baseline = [0.0] * len(adjustments)

        values = [0.0] * len(adjustments)
        for i in range(len(adjustments)):
            b = baseline[i] if i < len(baseline) else 0.0
            values[i] = b + adjustments[i]

        # Compare against last-sent values to find changed indices
        prev = getattr(self, '_last_delta_c', None)
        if prev is None:
            prev = list(baseline)

        changed: list[tuple[int, float]] = []
        for i, v in enumerate(values):
            if i >= len(prev) or abs(v - prev[i]) > 1e-9:
                changed.append((i, v))

        if not changed:
            print("[FlatGrindRunScreen] deltaC: no changes to apply")
            return

        print(f"[FlatGrindRunScreen] Apply deltaC: {len(changed)} changed indices "
              f"(out of {len(values)} total)")

        def _send():
            try:
                line = ""
                written = 0
                for idx, v in changed:
                    cmd = f"deltaC[{DELTA_C_WRITABLE_START + idx}]={round(v):.0f}"
                    if len(line) + len(cmd) + 1 < 80:
                        line = f"{line};{cmd}" if line else cmd
                    else:
                        ctrl.cmd(line)
                        written += line.count("=")
                        line = cmd
                if line:
                    ctrl.cmd(line)
                    written += line.count("=")
                # Cache sent values for next diff
                self._last_delta_c = list(values)
                print(f"[FlatGrindRunScreen] deltaC written: {written} elements")
            except Exception as e:
                err_msg = f"Apply failed: {e}"
                print(f"[FlatGrindRunScreen] Apply deltaC error: {e}")
                Clock.schedule_once(lambda *_, msg=err_msg: self._alert(msg))

        jobs.submit(_send)

    def _offsets_to_delta_c(self) -> list[float]:
        """Expand per-section offsets into deltaC array.

        Dispatches to the active compensation mode (self.comp_mode):
          - "cumulative": offset carries forward until cancelled
          - "spline":     smooth cubic interpolation between bar centers

        Stone geometry:
          - 347mm outer / 267mm inner = 40mm grind surface per side (left side)
          - Start point is 3mm past heel
          - Each deltaC index ≈ 1.2–1.5mm (STEP_MM ≈ 1.3)
          - deltaC values are incremental C-axis movements (LI vector mode)
          - Cumulative sum of deltaC = actual C-axis position profile
        """
        if self.comp_mode == "spline":
            return self._offsets_to_delta_c_spline()
        return self._offsets_to_delta_c_cumulative()

    def _offsets_to_delta_c_cumulative(self) -> list[float]:
        """Cumulative mode: each bar's offset carries forward for all subsequent indices.

        The offset at each bar is a CHANGE from the previous level. To return
        to baseline, the user must add the opposite offset in a later bar.

        Example (5 bars, bar 3 = +50):
          Bar 1: +0   → cumulative = 0    → indices  0-19 all get 0
          Bar 2: +0   → cumulative = 0    → indices 20-39 all get 0
          Bar 3: +50  → cumulative = 50   → indices 40-59 transition to 50
          Bar 4: +0   → cumulative = 50   → indices 60-79 stay at 50
          Bar 5: +0   → cumulative = 50   → indices 80-99 stay at 50

        deltaC values are the incremental changes needed to produce this
        cumulative position profile. Within each bar's range, the offset
        change is distributed evenly across the bar width for smooth ramping.
        """
        n = max(1, int(self.section_count))
        size = DELTA_C_ARRAY_SIZE
        offsets = list(self.delta_c_offsets)
        while len(offsets) < n:
            offsets.append(0.0)

        # Build the desired cumulative position profile
        # Each bar's offset adds to the running total
        position = [0.0] * size
        chunk = size // n
        cumulative = 0.0

        for i in range(n):
            first = i * chunk
            last = (first + chunk - 1) if i < n - 1 else (size - 1)
            prev_level = cumulative
            cumulative += offsets[i]

            # Ramp smoothly from prev_level to cumulative across this bar
            span = last - first + 1
            for j in range(span):
                t = j / max(1, span - 1)  # 0.0 to 1.0
                position[first + j] = prev_level + (cumulative - prev_level) * t

        # Convert position profile to incremental deltaC
        # Positive C = more grinding (stone moves down toward knife)
        result = [0.0] * size
        result[0] = position[0]
        for i in range(1, size):
            result[i] = position[i] - position[i - 1]

        return result

    def _offsets_to_delta_c_spline(self) -> list[float]:
        """Spline mode: smooth cubic interpolation between bar center control points.

        User sets offset values at bar centers. A natural cubic spline
        interpolates between control points. The endpoints are clamped
        to zero slope (natural boundary condition).

        deltaC values are the derivative of the spline (incremental changes
        needed to produce the smooth position curve).
        """
        import numpy as np
        from scipy.interpolate import CubicSpline

        n = max(1, int(self.section_count))
        size = DELTA_C_ARRAY_SIZE
        offsets = list(self.delta_c_offsets)
        while len(offsets) < n:
            offsets.append(0.0)

        chunk = size // n

        # Control points at bar centers
        x_points = []
        y_points = []

        # Pin start at 0
        x_points.append(0)
        y_points.append(0.0)

        for i in range(n):
            first = i * chunk
            last = (first + chunk - 1) if i < n - 1 else (size - 1)
            center = (first + last) // 2
            # Cumulative offset up to this bar
            cum = sum(offsets[:i + 1])
            x_points.append(center)
            y_points.append(cum)

        # Pin end at last value
        x_points.append(size - 1)
        y_points.append(y_points[-1])

        # Remove duplicates (if center == 0 or center == size-1)
        seen = set()
        unique_x, unique_y = [], []
        for xv, yv in zip(x_points, y_points):
            if xv not in seen:
                seen.add(xv)
                unique_x.append(xv)
                unique_y.append(yv)

        if len(unique_x) < 2:
            return [0.0] * size

        # Natural cubic spline (zero second derivative at endpoints)
        cs = CubicSpline(unique_x, unique_y, bc_type='natural')

        # Evaluate position at every index
        indices = np.arange(size, dtype=float)
        position = cs(indices)

        # Convert position profile to incremental deltaC
        # Positive C = more grinding (stone moves down toward knife)
        result = [0.0] * size
        result[0] = float(position[0])
        for i in range(1, size):
            result[i] = float(position[i] - position[i - 1])

        return result

    # -----------------------------------------------------------------------
    # Stone Compensation and CPM
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
                Clock.schedule_once(lambda *_, v=val: setattr(self, 'start_pt_c', f"Stone Pos: {v:,}"))
            except Exception:
                Clock.schedule_once(lambda *_: setattr(self, 'start_pt_c', '---'))
        jobs.submit(_do)

    def _read_cpm_values(self) -> None:
        """Background: read cpmA/B/C/D from controller and populate CPM annotation labels."""
        if not self.controller or not self.controller.is_connected():
            return
        ctrl = self.controller
        # Default CPM values if controller read fails
        _CPM_DEFAULTS = {"A": 1200.0, "B": 1200.0, "C": 800.0, "D": 360000.0}

        def _do():
            results: dict[str, str] = {}
            raw_cpms: dict[str, float] = {}
            for axis in ("A", "B", "C", "D"):
                try:
                    raw = ctrl.cmd(f"MG cpm{axis}").strip()
                    cpm = float(raw)
                except Exception:
                    cpm = _CPM_DEFAULTS.get(axis, 0.0)
                raw_cpms[axis] = cpm
                if cpm > 0:
                    unit = "1 deg" if axis == "D" else "1mm"
                    results[axis] = f"{int(cpm):,} counts = {unit}"

            def _apply(*_):
                for axis, text in results.items():
                    setattr(self, f"cpm_{axis.lower()}", text)
                # Store raw numeric CPM for plot scaling
                if raw_cpms.get("A", 0) > 0:
                    self._cpm_a_raw = raw_cpms["A"]
                if raw_cpms.get("B", 0) > 0:
                    self._cpm_b_raw = raw_cpms["B"]
            Clock.schedule_once(_apply)

        jobs.submit(_do)

    def _read_start_and_draw_stone(self) -> None:
        """Read startPtA/B (2 fast commands) and draw stone arcs on the plot.

        No array reads — just 2 scalar MG commands that won't block the queue.
        """
        if not self.controller or not self.controller.is_connected():
            return
        ctrl = self.controller

        def _do():
            try:
                from ...hmi.dmc_vars import STARTPT_A, STARTPT_B
                start_a = float(ctrl.cmd(f"MG {STARTPT_A}").strip())
                start_b = float(ctrl.cmd(f"MG {STARTPT_B}").strip())
                start_a_mm = start_a / self._cpm_a_raw
                start_b_mm = start_b / self._cpm_b_raw
                print(f"[FlatGrindRunScreen] Stone: startPt=({start_a_mm:.1f}, {start_b_mm:.1f})mm")

                # Read delta arrays for knife contour
                delta_a = ctrl.upload_array_auto("deltaA")
                delta_b = ctrl.upload_array_auto("deltaB")
                print(f"[FlatGrindRunScreen] Contour: deltaA[{len(delta_a)}], deltaB[{len(delta_b)}]")

                # Build contour path: cumsum from startPt
                contour_a_mm = None
                contour_b_mm = None
                if delta_a and delta_b:
                    n = min(len(delta_a), len(delta_b))
                    cpm_a = self._cpm_a_raw
                    cpm_b = self._cpm_b_raw
                    acc_a, acc_b = start_a, start_b
                    ca = [acc_a / cpm_a]
                    cb = [acc_b / cpm_b]
                    for i in range(n):
                        acc_a += delta_a[i]
                        acc_b += delta_b[i]
                        ca.append(acc_a / cpm_a)
                        cb.append(acc_b / cpm_b)
                    contour_a_mm = ca
                    contour_b_mm = cb
                    print(f"[FlatGrindRunScreen] Contour: A={ca[0]:.1f}->{ca[-1]:.1f}, "
                          f"B={cb[0]:.1f}->{cb[-1]:.1f}")

                def _apply(*_):
                    self._draw_stone(start_a_mm, start_b_mm, contour_a_mm, contour_b_mm)
                Clock.schedule_once(_apply)
            except Exception as e:
                print(f"[FlatGrindRunScreen] Read startPt/contour error: {e}")

        # Route through jobs queue — thread-safe, runs on worker thread
        jobs.submit(_do)

    def _draw_stone(self, start_a_mm: float, start_b_mm: float,
                    contour_a: list[float] | None = None,
                    contour_b: list[float] | None = None) -> None:
        """Draw stone arcs, startPt marker, and knife contour on the plot.

        Stone arcs and startPt are always drawn.
        Knife contour drawn if contour_a/contour_b are provided (from controller deltas).
        """
        if self._ax is None:
            return

        import numpy as np
        ax = self._ax

        # Clean up old elements
        for line in list(ax.lines):
            if getattr(line, '_stone_arc', False) or \
               getattr(line, '_startpt_marker', False) or \
               getattr(line, '_contour_line', False):
                line.remove()
        for txt in list(ax.texts):
            if getattr(txt, '_startpt_label', False):
                txt.remove()

        # --- Knife contour (from controller delta arrays) ---
        if contour_a and contour_b:
            cline, = ax.plot(contour_a, contour_b, color='#556677',
                            linewidth=1.5, linestyle='--', label='DU KIEN')
            cline._contour_line = True

        # --- Stone arcs ---
        outer_r = 347.0 / 2.0
        inner_r = 267.0 / 2.0
        center_a = start_a_mm - outer_r
        center_b = start_b_mm

        # Show only the grinding face (~120deg) facing the knife
        theta = np.linspace(-np.pi / 3, np.pi / 3, 80)
        for radius, color, style, label in [
            (outer_r, '#776622', '--', '347mm'),
            (inner_r, '#775533', ':', '267mm'),
        ]:
            arc_a = center_a + radius * np.cos(theta)
            arc_b = center_b + radius * np.sin(theta)
            line, = ax.plot(arc_a, arc_b, color=color, linewidth=1.2,
                           linestyle=style, label=label)
            line._stone_arc = True

        # --- StartPt marker (heel) ---
        marker, = ax.plot(start_a_mm, start_b_mm, 'o', color='#ff4444',
                         markersize=6, zorder=10)
        marker._startpt_marker = True

        txt = ax.annotate(
            f'GOT (Heel)\nA={start_a_mm:.0f}  B={start_b_mm:.0f}',
            xy=(start_a_mm, start_b_mm),
            xytext=(start_a_mm - 30, start_b_mm + 40),
            fontsize=7, color='#ff6666',
            arrowprops=dict(arrowstyle='->', color='#ff4444', lw=0.8),
        )
        txt._startpt_label = True

        self._fig.subplots_adjust(left=0.12, right=0.97, top=0.97, bottom=0.18)
        if self._fig and self._fig.canvas:
            self._fig.canvas.draw_idle()

    def _append_mg_log(self, text: str) -> None:
        """Main thread: append MG message to the log (cap at 200 lines)."""
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
        """Background thread: subscribe to MG via UDP and drain unsolicited messages.

        GMessage() takes NO arguments — timeout controlled by GTimeout().
        """
        try:
            import gclib  # type: ignore
        except ImportError:
            print("[RunScreen] MG reader: gclib not available")
            return

        handle = None
        try:
            handle = gclib.py()
            handle.GOpen(f"{address} --subscribe MG")
            handle.GTimeout(500)  # 500ms so loop checks stop_event regularly
            print(f"[RunScreen] MG reader connected: {address} --subscribe MG")
        except Exception as e:
            print(f"[RunScreen] MG reader open failed: {e}")
            if handle:
                try:
                    handle.GClose()
                except Exception:
                    pass
            return

        try:
            while not stop_event.is_set():
                try:
                    msg = handle.GMessage()  # blocks up to 500ms (GTimeout)
                    if msg:
                        for line in msg.strip().split('\n'):
                            line = line.strip()
                            if line:
                                Clock.schedule_once(
                                    lambda *_, t=line: self._append_mg_log(t)
                                )
                except Exception:
                    # Timeout or read error — just retry
                    pass
        finally:
            try:
                handle.GClose()
            except Exception:
                pass
            print("[RunScreen] MG reader closed")

    # -----------------------------------------------------------------------
    # Utilities
    # -----------------------------------------------------------------------

    def _alert(self, message: str) -> None:
        """Push a message to the app-wide banner ticker.

        Falls back to state.log() if the app object is unavailable (e.g. during tests).
        """
        try:
            from kivy.app import App
            app = App.get_running_app()
            if app and hasattr(app, "_log_message"):
                getattr(app, "_log_message")(message)
                return
        except Exception:
            pass
        if self.state:
            self.state.log(message)
