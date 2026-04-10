"""RunScreen — operator run screen with live axis positions and cycle monitoring."""
from __future__ import annotations

import time
from collections import deque

from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Line, Rectangle
from kivy.properties import (
    BooleanProperty,
    ListProperty,
    NumericProperty,
    ObjectProperty,
    StringProperty,
)
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
import matplotlib.pyplot  # noqa: F401 — required by kivy_matplotlib_widget internals
import kivy_matplotlib_widget  # noqa: F401 — registers MatplotFigure in Kivy Factory

from ..app_state import MachineState
from ..controller import GalilController
from ..hmi.dmc_vars import (
    STATE_GRINDING, STATE_HOMING,
    HMI_GRND, HMI_MORE, HMI_LESS, HMI_TRIGGER_FIRE,
    STARTPT_A, STARTPT_B, STARTPT_C,
    POS_BUF_IDX, POS_BUF_A, POS_BUF_B, POS_BUF_SIZE,
)
from ..utils import jobs
import dmccodegui.machine_config as mc


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
TOOLPATH_COLOR = "#445566"    # muted grey-blue for expected path ghost line

# ---------------------------------------------------------------------------
# Delta-C (Knife Grind Adjustment) constants — Plan 02-02 fills the full panel
# ---------------------------------------------------------------------------
DELTA_C_WRITABLE_START: int = 0    # First writable index in the deltaC array on controller
DELTA_C_WRITABLE_END: int = 99     # Last writable index (inclusive) — 100 elements total
DELTA_C_ARRAY_SIZE: int = DELTA_C_WRITABLE_END - DELTA_C_WRITABLE_START + 1  # = 100
DELTA_C_STEP: int = 50             # Adjustment increment per button press in controller counts

# ---------------------------------------------------------------------------
# bComp (Serration Grind Adjustment) constants
# ---------------------------------------------------------------------------
BCOMP_STEP: int = 50               # Adjustment increment per button press in controller counts


class _BaseBarChart(Widget):
    """Shared base for DeltaCBarChart and BCompBarChart.

    Draws a per-section bar chart on a zero baseline. Positive offsets extend
    above the centre line; negative offsets extend below. Tapping a bar selects
    it (highlighted in orange).

    Subclasses set ``STEP`` as a class attribute.

    Properties
    ----------
    offsets : ListProperty([])
        One float per section.
    selected_index : NumericProperty(-1)
        Index of the currently selected bar. -1 means nothing selected.
    max_offset : NumericProperty(500)
        Absolute offset value that maps to half the widget height (clamps bars).
    """

    offsets = ListProperty([])
    selected_index = NumericProperty(-1)
    max_offset = NumericProperty(500)

    STEP: int = 50  # Override in subclasses

    # ------------------------------------------------------------------
    # Reactive triggers — any change to size/pos/offsets/selection redraws
    # ------------------------------------------------------------------

    def on_offsets(self, *args) -> None:
        self._draw()

    def on_selected_index(self, *args) -> None:
        self._draw()

    def on_size(self, *args) -> None:
        self._draw()

    def on_pos(self, *args) -> None:
        self._draw()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        """Clear and redraw all bars using Kivy canvas instructions."""
        self.canvas.clear()
        offsets = list(self.offsets)
        n = len(offsets)
        if n == 0:
            return

        bar_w = self.width / n
        mid_y = self.y + self.height / 2.0
        half_h = self.height / 2.0

        with self.canvas:
            # Zero baseline — thin grey horizontal line
            Color(0.4, 0.4, 0.4, 1)
            Rectangle(pos=(self.x, mid_y - 0.5), size=(self.width, 1))

            for i, offset in enumerate(offsets):
                # Bar height proportional to |offset| / max_offset, minimum 2px
                if self.max_offset > 0:
                    raw_h = abs(offset) / self.max_offset * half_h
                else:
                    raw_h = 0.0
                bar_h = max(10.0, raw_h)

                # Colour: orange if selected, blue otherwise
                if i == int(self.selected_index):
                    Color(1.0, 0.65, 0.0, 1)
                else:
                    Color(0.235, 0.510, 0.960, 1)

                bar_x = self.x + i * bar_w
                if offset >= 0:
                    # Positive: draw above the zero line
                    Rectangle(pos=(bar_x + 1, mid_y), size=(bar_w - 2, bar_h))
                else:
                    # Negative: draw below the zero line
                    Rectangle(pos=(bar_x + 1, mid_y - bar_h), size=(bar_w - 2, bar_h))

    # ------------------------------------------------------------------
    # Touch handling
    # ------------------------------------------------------------------

    def on_touch_down(self, touch) -> bool:
        """Select the bar that was tapped."""
        if not self.collide_point(touch.x, touch.y):
            return False
        n = len(self.offsets)
        if n == 0:
            return True
        bar_w = self.width / n
        idx = int((touch.x - self.x) / bar_w)
        idx = max(0, min(n - 1, idx))
        self.selected_index = idx
        return True


class DeltaCBarChart(_BaseBarChart):
    """Bar-chart widget that draws per-section deltaC offsets on a zero baseline.

    Each bar represents one section of the knife. Positive offsets extend above
    the centre line; negative offsets extend below. Tapping a bar selects it
    (highlighted in orange); the RunScreen up/down buttons adjust the selected
    bar's offset.

    Segment labels are drawn below the bars: "MŨI" (tip) on the left edge,
    "GÓT" (heel) on the right edge, and segment numbers centred under each bar.

    Properties
    ----------
    offsets : ListProperty([])
        One float per section.  Bound to RunScreen.delta_c_offsets in KV.
    selected_index : NumericProperty(-1)
        Index of the currently selected bar.  -1 means nothing selected.
    max_offset : NumericProperty(500)
        Absolute offset value that maps to half the widget height (clamps bars).
    """

    STEP: int = DELTA_C_STEP
    _LABEL_HEIGHT: int = 18  # px reserved at bottom for labels

    def _draw(self) -> None:
        self.canvas.clear()
        offsets = list(self.offsets)
        n = len(offsets)
        if n == 0:
            return

        label_h = self._LABEL_HEIGHT
        bar_w = self.width / n
        # Reserve label_h at bottom for segment labels
        chart_top = self.y + self.height
        chart_bottom = self.y + label_h
        chart_h = chart_top - chart_bottom
        mid_y = chart_bottom + chart_h / 2.0
        half_h = chart_h / 2.0

        with self.canvas:
            # Zero baseline
            Color(0.4, 0.4, 0.4, 1)
            Rectangle(pos=(self.x, mid_y - 0.5), size=(self.width, 1))

            # Bars
            for i, offset in enumerate(offsets):
                if self.max_offset > 0:
                    raw_h = abs(offset) / self.max_offset * half_h
                else:
                    raw_h = 0.0
                bar_h = max(10.0, raw_h)

                if i == int(self.selected_index):
                    Color(1.0, 0.65, 0.0, 1)
                else:
                    Color(0.235, 0.510, 0.960, 1)

                bar_x = self.x + i * bar_w
                if offset >= 0:
                    Rectangle(pos=(bar_x + 1, mid_y), size=(bar_w - 2, bar_h))
                else:
                    Rectangle(pos=(bar_x + 1, mid_y - bar_h), size=(bar_w - 2, bar_h))

            # Segment number labels under each bar
            Color(0.7, 0.7, 0.7, 1)
            for i in range(n):
                lbl = CoreLabel(text=str(i + 1), font_size=10)
                lbl.refresh()
                tex = lbl.texture
                bx = self.x + i * bar_w + (bar_w - tex.width) / 2.0
                Rectangle(texture=tex, pos=(bx, self.y), size=tex.size)

            # "MŨI" (tip) label — left edge
            Color(0.95, 0.75, 0.3, 1)
            tip_lbl = CoreLabel(text='MŨI', font_size=10, bold=True)
            tip_lbl.refresh()
            tip_tex = tip_lbl.texture
            Rectangle(
                texture=tip_tex,
                pos=(self.x + 2, self.y),
                size=tip_tex.size,
            )

            # "GÓT" (heel) label — right edge
            heel_lbl = CoreLabel(text='GÓT', font_size=10, bold=True)
            heel_lbl.refresh()
            heel_tex = heel_lbl.texture
            Rectangle(
                texture=heel_tex,
                pos=(self.x + self.width - heel_tex.width - 2, self.y),
                size=heel_tex.size,
            )

    def on_touch_down(self, touch) -> bool:
        """Select bar — ignore touches in the label strip at the bottom."""
        if not self.collide_point(touch.x, touch.y):
            return False
        if touch.y < self.y + self._LABEL_HEIGHT:
            return False
        n = len(self.offsets)
        if n == 0:
            return True
        bar_w = self.width / n
        idx = int((touch.x - self.x) / bar_w)
        idx = max(0, min(n - 1, idx))
        self.selected_index = idx
        return True


class BCompBarChart(_BaseBarChart):
    """Bar-chart widget that draws per-serration bComp offsets on a zero baseline.

    Mirrors DeltaCBarChart exactly but reads/writes the ``bComp`` DMC array
    instead of ``deltaC``. Used only on 3-Axes Serration Grind machines.

    Array size is driven by the ``numSerr`` variable (number of serrations).

    Properties
    ----------
    offsets : ListProperty([])
        One float per serration.  Bound to RunScreen.bcomp_offsets in KV.
    selected_index : NumericProperty(-1)
        Index of the currently selected bar.  -1 means nothing selected.
    max_offset : NumericProperty(500)
        Absolute offset value that maps to half the widget height (clamps bars).
    """

    STEP: int = BCOMP_STEP


def _format_mmss(seconds: float) -> str:
    """Format a duration in seconds as MM:SS string."""
    if seconds < 0:
        seconds = 0.0
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"


class RunScreen(Screen):
    """
    RunScreen — core operator screen for monitoring and controlling grinding cycles.

    Layout: two-column (left: plot placeholder + adjustment placeholder,
            right: cycle status + axis positions), bottom action bar.

    Threading model:
      - MachineState.subscribe() delivers state changes from the centralized poller
      - _apply_state() is the single path for updating all Kivy properties
      - Plot redraws run on a separate 5 Hz clock to protect E-STOP latency

    KV file: ui/run.kv
    """

    # Injected by main.py after ScreenManager is built
    controller: GalilController = ObjectProperty(None, allownone=True)  # type: ignore
    state: MachineState = ObjectProperty(None, allownone=True)  # type: ignore

    # Kivy properties — bound in run.kv
    # NOTE: RunScreen.cycle_running is a Kivy BooleanProperty (for KV bindings/opacity).
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

    # Serration Grind Adjustment properties (bComp — Serration only)
    bcomp_offsets = ListProperty([0.0])          # one offset per serration tooth
    selected_bcomp_value = StringProperty("0")   # display value for the selected bar

    # Knife count display strings (Phase 10)
    session_knife_count = StringProperty("0")
    stone_knife_count = StringProperty("0")

    # Stone Compensation readback — persistent label in Stone Compensation card (Phase 15)
    start_pt_c = StringProperty("---")

    # Disconnect banner (empty string = no banner visible)
    disconnect_banner = StringProperty("")

    # -----------------------------------------------------------------------
    # Internal state
    # -----------------------------------------------------------------------
    _state_unsub = None          # unsubscribe callable returned by MachineState.subscribe()
    _plot_clock_event = None
    _disconnect_clock = None     # 1 Hz elapsed time updater for disconnect banner
    _disconnect_t0: float | None = None   # monotonic time of disconnect start
    _plot_buf_x: deque = None  # type: ignore — initialized in __init__
    _plot_buf_y: deque = None  # type: ignore
    _fig = None
    _ax = None
    _plot_line = None
    _cycle_start_time: float | None = None
    _cpm_a_raw: float = 1200.0  # counts per mm — updated by _read_cpm_values
    _cpm_b_raw: float = 1200.0
    _toolpath_line = None        # matplotlib line artist for expected path
    _toolpath_loaded: bool = False

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
        Binds the BCompBarChart selection observer for selected_bcomp_value.
        Initializes the MatplotFigure plot widget for the live A/B position trail.
        """
        chart = self.ids.get("delta_c_chart")
        if chart is not None:
            chart.bind(selected_index=self._on_chart_selection_changed)

        bcomp_chart = self.ids.get("bcomp_chart")
        if bcomp_chart is not None:
            bcomp_chart.bind(selected_index=self._on_bcomp_chart_selection_changed)

        plot_wgt = self.ids.get("ab_plot")
        if plot_wgt is not None:
            self._fig = Figure(figsize=(4, 3), facecolor=BG_PANEL_HEX)
            self._ax = self._fig.add_subplot(111)
            self._configure_plot_axes()
            # Expected toolpath — dashed ghost line (drawn first, behind live trace)
            self._toolpath_line, = self._ax.plot(
                [], [], color=TOOLPATH_COLOR, linewidth=2.0, linestyle='--', label='DỰ KIẾN',
            )
            # Live A/B trace — solid cyan on top
            self._plot_line, = self._ax.plot(
                [], [], color=TRAIL_COLOR, linewidth=1.2, label='THỰC TẾ',
            )
            self._ax.legend(
                fontsize=7, facecolor=BG_PANEL_HEX, labelcolor='white',
                loc='upper right', framealpha=0.8,
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

        Applies machine type widget visibility, subscribes to MachineState for
        live updates, and applies the current state immediately so values are
        visible before the next poll fires.
        Also starts the 5 Hz plot redraw clock.
        """
        # Stop the centralized poller — its 10 Hz MG traffic floods the
        # controller bus and blocks GDK unsolicited message printing during grind.
        from kivy.app import App
        app = App.get_running_app()
        if app and hasattr(app, '_stop_poller'):
            app._stop_poller()

        # Apply machine-type-specific widget visibility first
        self._apply_machine_type_widgets()

        # Subscribe to MachineState — unsubscribe callable stored for on_leave
        if self.state is not None:
            self._state_unsub = self.state.subscribe(
                lambda s: Clock.schedule_once(lambda *_: self._apply_state(s))
            )
            # Apply current state immediately (shows values without waiting for next poll)
            self._apply_state(self.state)

        # Start 5 Hz plot redraw (separate clock to protect E-STOP latency)
        self._plot_clock_event = Clock.schedule_interval(self._tick_plot, 1.0 / PLOT_UPDATE_HZ)

        # Read startPtC from controller so the Stone Compensation label is populated on entry
        self._read_start_pt_c()

        # Read CPM values from controller for axis position annotations
        self._read_cpm_values()

        # Read deltaA/deltaB to draw expected toolpath (FIFO after CPM read)
        self._read_toolpath()

    def on_leave(self, *args) -> None:
        """Called by Kivy when operator navigates away.

        Unsubscribes from MachineState and cancels all clocks.
        """
        if self._state_unsub:
            self._state_unsub()
            self._state_unsub = None
        if self._disconnect_clock:
            self._disconnect_clock.cancel()
            self._disconnect_clock = None
            self._disconnect_t0 = None
        if self._plot_clock_event:
            self._plot_clock_event.cancel()
            self._plot_clock_event = None
        # Invalidate toolpath so it re-reads on next entry (picks up profile changes)
        self._toolpath_loaded = False

        # Restart the centralized poller for other screens
        from kivy.app import App
        app = App.get_running_app()
        if app and hasattr(app, '_start_poller'):
            app._start_poller()

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

        # Delta-C panel: visible on Flat/Convex, hidden on Serration
        delta_c_panel = self.ids.get("delta_c_panel")
        if delta_c_panel is not None:
            delta_c_panel.opacity = 0.0 if serration else 1.0
            delta_c_panel.disabled = serration

        # bComp panel: visible on Serration, hidden on Flat/Convex
        bcomp_panel = self.ids.get("bcomp_panel")
        if bcomp_panel is not None:
            bcomp_panel.opacity = 1.0 if serration else 0.0
            bcomp_panel.disabled = not serration

        # D axis position row: hidden on Serration
        pos_d_row = self.ids.get("pos_d_row")
        if pos_d_row is not None:
            pos_d_row.opacity = 0.0 if serration else 1.0

    # -----------------------------------------------------------------------
    # State subscription handler
    # -----------------------------------------------------------------------

    def _apply_state(self, s: MachineState) -> None:
        """Main thread: apply MachineState to RunScreen Kivy properties.

        Called on every MachineState change notification. This is the single
        path for updating all reactive Kivy properties on this screen.
        """
        import time as _time

        # Connection state
        if s.connected:
            # Clear disconnect banner and stop elapsed timer
            if self.disconnect_banner:
                self.disconnect_banner = ""
            if self._disconnect_clock:
                self._disconnect_clock.cancel()
                self._disconnect_clock = None
                self._disconnect_t0 = None

            # Axis positions — format as integer with comma thousands separator
            for axis, prop in (("A", "pos_a"), ("B", "pos_b"), ("C", "pos_c"), ("D", "pos_d")):
                val = s.pos.get(axis)
                if val is not None:
                    try:
                        setattr(self, prop, f"{int(val):,}")
                    except (ValueError, TypeError):
                        setattr(self, prop, "---")
                else:
                    setattr(self, prop, "---")

            # Knife counts
            self.session_knife_count = str(s.session_knife_count)
            self.stone_knife_count = str(s.stone_knife_count)

            # Cycle running from controller state (drives Kivy property for KV bindings)
            self.cycle_running = s.cycle_running
            # Motion gate: True when axes may be in motion (disables motion buttons)
            self.motion_active = s.dmc_state in (STATE_GRINDING, STATE_HOMING)

        else:
            # Disconnected: freeze positions (don't overwrite with zeros)
            self.cycle_running = False
            self.motion_active = True  # Disable all motion buttons when disconnected
            # Start disconnect elapsed timer if not already running
            if self._disconnect_clock is None:
                self._disconnect_t0 = _time.monotonic()
                self._tick_disconnect_banner(0)  # immediate first tick
                self._disconnect_clock = Clock.schedule_interval(
                    self._tick_disconnect_banner, 1.0
                )

        # Feed raw A/B to plot buffer while connected.
        # Positions come from the #SHOWPOS controller thread (aPos/bPos/cPos/dPos)
        # which updates every 50ms regardless of grinding state.
        # Buffer is cleared on START GRIND so each cycle gets a fresh trail.
        if s.connected:
            raw_a = s.pos.get("A")
            raw_b = s.pos.get("B")
            if raw_a is not None and raw_b is not None:
                try:
                    self._plot_buf_x.append(float(raw_a))
                    self._plot_buf_y.append(float(raw_b))
                except (ValueError, TypeError):
                    pass

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

    def _configure_plot_axes(self) -> None:
        """Style the A/B position plot axes to match app dark theme.

        Axes are labelled in mm (A = length, B = width).  Left edge = MŨI (tip),
        right edge = GÓT (heel) to match the segment bar below.
        """
        ax = self._ax
        self._fig.patch.set_facecolor(BG_PANEL_HEX)
        ax.set_facecolor(BG_PANEL_HEX)
        ax.set_aspect("equal", adjustable="datalim")
        ax.tick_params(colors=TICK_COLOR, labelsize=7, length=3, width=0.5)
        for spine in ax.spines.values():
            spine.set_edgecolor(TICK_COLOR)
            spine.set_linewidth(0.5)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
        ax.set_xlabel("A  (mm)   MŨI →  GÓT", fontsize=8, color=TICK_COLOR)
        ax.set_ylabel("B  (mm)", fontsize=8, color=TICK_COLOR)
        ax.grid(False)
        self._fig.tight_layout(pad=0.5)

    def _tick_plot(self, dt: float) -> None:
        """5 Hz Kivy clock: redraw the live A/B trace in mm. Main thread only.

        Axis limits are fixed by the toolpath — no relim/autoscale needed.
        """
        if self._plot_line is None:
            return
        xs_raw = list(self._plot_buf_x)
        ys_raw = list(self._plot_buf_y)
        if len(xs_raw) < 2:
            return
        # Convert counts → mm using CPM values
        cpm_a = self._cpm_a_raw
        cpm_b = self._cpm_b_raw
        xs = [v / cpm_a for v in xs_raw]
        ys = [v / cpm_b for v in ys_raw]
        self._plot_line.set_data(xs, ys)
        # Fall back to autoscale only if toolpath hasn't set limits yet
        if not self._toolpath_loaded:
            self._ax.relim()
            self._ax.autoscale_view()
        self._fig.canvas.draw_idle()

    # -----------------------------------------------------------------------
    # Action handlers
    # -----------------------------------------------------------------------

    def on_stop(self) -> None:
        """Send ST ABCD via priority path (halts axes, DMC program thread stays alive)."""
        if not self.controller or not self.controller.is_connected():
            return
        def do_stop():
            try:
                self.controller.cmd("ST ABCD")
            except Exception as e:
                Clock.schedule_once(lambda *_: self._alert(f"Stop failed: {e}"))
        from ..utils.jobs import submit_urgent
        submit_urgent(do_stop)

    def on_start_grind(self) -> None:
        """Send hmiGrnd=0 via jobs.submit to start/continue grinding cycle.

        Clears the A/B position plot trail so each cycle gets a fresh view.
        Uses the HMI one-shot trigger pattern — never XQ direct calls.
        Guards: cannot start grind while in SETUP mode or during active motion.
        """
        if not self.controller or not self.controller.is_connected():
            return
        # Guard: don't fire hmiGrnd if controller is in setup or already in motion
        if self.state is not None:
            from ..hmi.dmc_vars import STATE_SETUP, STATE_HOMING
            if self.state.dmc_state in (STATE_SETUP, STATE_GRINDING, STATE_HOMING):
                return

        # Clear live trace for fresh cycle view; toolpath ghost line stays
        self._plot_buf_x.clear()
        self._plot_buf_y.clear()
        if self._plot_line is not None:
            self._plot_line.set_data([], [])
            if self._fig and self._fig.canvas:
                self._fig.canvas.draw_idle()

        def _fire():
            try:
                self.controller.cmd(f"{HMI_GRND}={HMI_TRIGGER_FIRE}")
            except Exception as e:
                Clock.schedule_once(lambda *_: self._alert(f"Start failed: {e}"))

        jobs.submit(_fire)

    def on_more_stone(self) -> None:
        """Send hmiMore=0 then read startPtC after 400ms delay to update persistent label.

        Fires the HMI_MORE trigger, sleeps 400ms for the DMC #MOREGRI subroutine to
        complete, then reads startPtC and updates the persistent start_pt_c label.
        No toast-style alert — operator sees the result in the Stone Compensation card.
        """
        if not self.controller or not self.controller.is_connected():
            return

        ctrl = self.controller

        def _fire():
            import time as _time
            try:
                before_raw = ctrl.cmd(f"MG {STARTPT_C}").strip()
                before = int(float(before_raw))
                print(f"[RunScreen] More stone — startPtC BEFORE: {before}")
            except Exception as e:
                print(f"[RunScreen] More stone — failed to read startPtC before: {e}")
                before = None

            try:
                ctrl.cmd(f"{HMI_MORE}={HMI_TRIGGER_FIRE}")
            except Exception as e:
                Clock.schedule_once(lambda *_: self._alert(f"More stone failed: {e}"))
                return

            _time.sleep(0.4)

            try:
                after_raw = ctrl.cmd(f"MG {STARTPT_C}").strip()
                after = int(float(after_raw))
                print(f"[RunScreen] More stone — startPtC AFTER: {after}")
                Clock.schedule_once(
                    lambda *_, v=after: setattr(self, 'start_pt_c', f"Stone Pos: {v:,}")
                )
            except Exception as e:
                print(f"[RunScreen] More stone — failed to read startPtC after: {e}")

        jobs.submit(_fire)

    def on_less_stone(self) -> None:
        """Send hmiLess=0 then read startPtC after 400ms delay to update persistent label.

        Mirror of on_more_stone but fires HMI_LESS. Sleeps 400ms for the DMC
        #LESSGRI subroutine to complete, then reads startPtC and updates the
        persistent start_pt_c label. No toast-style alert.
        """
        if not self.controller or not self.controller.is_connected():
            return

        ctrl = self.controller

        def _fire():
            import time as _time
            try:
                before_raw = ctrl.cmd(f"MG {STARTPT_C}").strip()
                before = int(float(before_raw))
                print(f"[RunScreen] Less stone — startPtC BEFORE: {before}")
            except Exception as e:
                print(f"[RunScreen] Less stone — failed to read startPtC before: {e}")
                before = None

            try:
                ctrl.cmd(f"{HMI_LESS}={HMI_TRIGGER_FIRE}")
            except Exception as e:
                Clock.schedule_once(lambda *_: self._alert(f"Less stone failed: {e}"))
                return

            _time.sleep(0.4)

            try:
                after_raw = ctrl.cmd(f"MG {STARTPT_C}").strip()
                after = int(float(after_raw))
                print(f"[RunScreen] Less stone — startPtC AFTER: {after}")
                Clock.schedule_once(
                    lambda *_, v=after: setattr(self, 'start_pt_c', f"Stone Pos: {v:,}")
                )
            except Exception as e:
                print(f"[RunScreen] Less stone — failed to read startPtC after: {e}")

        jobs.submit(_fire)

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
        """Convert section offsets to a 100-element deltaC array and send to controller.

        Only writes the writable index range [DELTA_C_WRITABLE_START, DELTA_C_WRITABLE_END].
        Submits the download_array call on the background job thread.
        """
        if not self.controller or not self.controller.is_connected():
            return
        values = self._offsets_to_delta_c()

        def _send():
            try:
                self.controller.download_array(
                    "deltaC",
                    DELTA_C_WRITABLE_START,
                    values,
                )
            except Exception as e:
                print(f"[RunScreen] Apply deltaC error: {e}")
                Clock.schedule_once(lambda *_: self._alert(f"Apply failed: {e}"))

        jobs.submit(_send)

    def _offsets_to_delta_c(self) -> list[float]:
        """Expand per-section offsets into the full DELTA_C_ARRAY_SIZE-element array.

        Each section covers ``DELTA_C_ARRAY_SIZE // section_count`` indices.  The
        last section absorbs any remainder so the output length is always
        exactly DELTA_C_ARRAY_SIZE.

        Only the first index of each segment receives the offset value and the
        last index receives the negated offset (to return the grind to normal).
        All other indices in the segment are zero.

        Returns
        -------
        list[float]
            Length DELTA_C_ARRAY_SIZE (== DELTA_C_WRITABLE_END - DELTA_C_WRITABLE_START + 1).
        """
        n = max(1, int(self.section_count))
        size = DELTA_C_ARRAY_SIZE
        offsets = list(self.delta_c_offsets)
        while len(offsets) < n:
            offsets.append(0.0)

        result: list[float] = [0.0] * size
        chunk = size // n
        for i in range(n):
            first = i * chunk
            last = (first + chunk - 1) if i < n - 1 else (size - 1)
            val = offsets[i]
            result[first] = val
            result[last] = -val

        return result

    # -----------------------------------------------------------------------
    # bComp (Serration Grind Adjustment) — Serration machines only
    # -----------------------------------------------------------------------

    def _on_bcomp_chart_selection_changed(self, chart_widget, selected_index: int) -> None:
        """Observer bound to bcomp_chart.selected_index via on_kv_post.

        Updates selected_bcomp_value so the 'Selected: X cts' label refreshes
        whenever the operator taps a bar or the selection is cleared.
        """
        idx = int(selected_index)
        if 0 <= idx < len(self.bcomp_offsets):
            self.selected_bcomp_value = str(int(self.bcomp_offsets[idx]))
        else:
            self.selected_bcomp_value = "0"

    def on_bcomp_adjust_up(self) -> None:
        """Add BCOMP_STEP to the currently selected bComp bar's offset."""
        chart = self.ids.get("bcomp_chart")
        if chart is None:
            return
        idx = int(chart.selected_index)
        if idx < 0 or idx >= len(self.bcomp_offsets):
            return
        offsets = list(self.bcomp_offsets)
        offsets[idx] += BCOMP_STEP
        self.bcomp_offsets = offsets
        self.selected_bcomp_value = str(int(self.bcomp_offsets[idx]))

    def on_bcomp_adjust_down(self) -> None:
        """Subtract BCOMP_STEP from the currently selected bComp bar's offset."""
        chart = self.ids.get("bcomp_chart")
        if chart is None:
            return
        idx = int(chart.selected_index)
        if idx < 0 or idx >= len(self.bcomp_offsets):
            return
        offsets = list(self.bcomp_offsets)
        offsets[idx] -= BCOMP_STEP
        self.bcomp_offsets = offsets
        self.selected_bcomp_value = str(int(self.bcomp_offsets[idx]))

    def _read_bcomp(self) -> None:
        """Background thread: read bComp array from controller.

        Array size is determined by reading numSerr from the controller.
        Posts results back to main thread.
        """
        if not self.controller or not self.controller.is_connected():
            return

        ctrl = self.controller

        def _do_read():
            try:
                # Get the number of serration teeth from controller
                raw_num = ctrl.cmd("MG numSerr").strip()
                num_serr = max(1, int(float(raw_num)))
            except Exception:
                num_serr = len(self.bcomp_offsets) or 1

            offsets: list[float] = []
            for i in range(num_serr):
                try:
                    raw = ctrl.cmd(f"MG bComp[{i}]").strip()
                    offsets.append(float(raw))
                except Exception:
                    offsets.append(0.0)

            def _apply(*_):
                self.bcomp_offsets = offsets
                if self.bcomp_offsets:
                    self.selected_bcomp_value = str(int(self.bcomp_offsets[0]))

            Clock.schedule_once(_apply)

        jobs.submit(_do_read)

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

    def _read_toolpath(self) -> None:
        """Background: read deltaA/deltaB arrays and startPtA/B from controller.

        Reconstructs the expected toolpath by cumulative-summing the deltas
        from the start positions, converts to mm, and draws on the plot.
        """
        if self._toolpath_loaded:
            return
        if not self.controller or not self.controller.is_connected():
            return
        ctrl = self.controller

        def _do():
            try:
                # Read start positions (counts)
                start_a = float(ctrl.cmd(f"MG {STARTPT_A}").strip())
                start_b = float(ctrl.cmd(f"MG {STARTPT_B}").strip())

                # Read delta arrays
                delta_a = ctrl.upload_array_auto("deltaA")
                delta_b = ctrl.upload_array_auto("deltaB")

                if not delta_a or not delta_b:
                    return

                # Cumulative sum from start position → absolute positions (counts)
                n = min(len(delta_a), len(delta_b))
                abs_a = [0.0] * n
                abs_b = [0.0] * n
                acc_a = start_a
                acc_b = start_b
                for i in range(n):
                    acc_a += delta_a[i]
                    acc_b += delta_b[i]
                    abs_a[i] = acc_a
                    abs_b[i] = acc_b

                # Convert counts → mm
                cpm_a = self._cpm_a_raw
                cpm_b = self._cpm_b_raw
                mm_a = [v / cpm_a for v in abs_a]
                mm_b = [v / cpm_b for v in abs_b]

                def _apply(*_):
                    self._toolpath_loaded = True
                    self._draw_toolpath(mm_a, mm_b)
                Clock.schedule_once(_apply)

            except Exception as e:
                print(f"[RunScreen] Read toolpath error: {e}")

        jobs.submit(_do)

    def _draw_toolpath(self, mm_a: list[float], mm_b: list[float]) -> None:
        """Draw the expected toolpath on the plot and lock axis limits."""
        if self._toolpath_line is None or self._ax is None:
            return

        self._toolpath_line.set_data(mm_a, mm_b)

        # Set axis limits from toolpath extents with padding
        if mm_a and mm_b:
            pad_a = max(1.0, (max(mm_a) - min(mm_a)) * 0.05)
            pad_b = max(1.0, (max(mm_b) - min(mm_b)) * 0.05)
            self._ax.set_xlim(min(mm_a) - pad_a, max(mm_a) + pad_a)
            self._ax.set_ylim(min(mm_b) - pad_b, max(mm_b) + pad_b)

        if self._fig and self._fig.canvas:
            self._fig.canvas.draw_idle()

    def on_apply_bcomp(self) -> None:
        """Write bComp offsets to controller bComp array and burn NV.

        Submits the write commands on the background job thread.
        """
        if not self.controller or not self.controller.is_connected():
            return

        offsets_snapshot = list(self.bcomp_offsets)
        ctrl = self.controller

        def _send():
            try:
                for i, val in enumerate(offsets_snapshot):
                    ctrl.cmd(f"bComp[{i}]={int(val)}")
                ctrl.cmd("BV")
            except Exception as e:
                print(f"[RunScreen] Apply bComp error: {e}")
                Clock.schedule_once(lambda *_: self._alert(f"Apply bComp failed: {e}"))

        jobs.submit(_send)

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
