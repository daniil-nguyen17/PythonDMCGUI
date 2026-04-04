"""RunScreen — operator run screen with live axis positions and cycle monitoring."""
from __future__ import annotations

import time

from kivy.clock import Clock
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

from ..app_state import MachineState
from ..controller import GalilController
from ..utils import jobs


# ---------------------------------------------------------------------------
# Machine type configuration — Phase 6 will replace this with a runtime setting
# ---------------------------------------------------------------------------
MACHINE_TYPE = "4axis_flat"  # Options: "4axis_flat", "4axis_convex", "3axis_serration"
IS_SERRATION = MACHINE_TYPE == "3axis_serration"

# Controller variable names for cycle status (configurable for different controller programs)
CYCLE_VAR_TOOTH = "tooth"
CYCLE_VAR_PASS = "pass_num"
CYCLE_VAR_DEPTH = "depth"
CYCLE_VAR_COMPLETION = "pctDone"

# ---------------------------------------------------------------------------
# Delta-C (Knife Grind Adjustment) constants — Plan 02-02 fills the full panel
# ---------------------------------------------------------------------------
DELTA_C_WRITABLE_START: int = 0    # First writable index in the deltaC array on controller
DELTA_C_WRITABLE_END: int = 99     # Last writable index (inclusive) — 100 elements total
DELTA_C_ARRAY_SIZE: int = DELTA_C_WRITABLE_END - DELTA_C_WRITABLE_START + 1  # = 100
DELTA_C_STEP: int = 50             # Adjustment increment per button press in controller counts


class DeltaCBarChart(Widget):
    """Bar-chart widget that draws per-section deltaC offsets on a zero baseline.

    Each bar represents one section of the knife. Positive offsets extend above
    the centre line; negative offsets extend below. Tapping a bar selects it
    (highlighted in orange); the RunScreen up/down buttons adjust the selected
    bar's offset.

    Properties
    ----------
    offsets : ListProperty([])
        One float per section.  Bound to RunScreen.delta_c_offsets in KV.
    selected_index : NumericProperty(-1)
        Index of the currently selected bar.  -1 means nothing selected.
    max_offset : NumericProperty(500)
        Absolute offset value that maps to half the widget height (clamps bars).
    """

    offsets = ListProperty([])
    selected_index = NumericProperty(-1)
    max_offset = NumericProperty(500)

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
                bar_h = max(2.0, raw_h)

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
      - _update_clock() fires at 10 Hz on the Kivy main thread (Clock.schedule_interval)
      - If controller is connected it submits _do_poll() to the background job thread
      - _do_poll() posts UI updates back to main thread via Clock.schedule_once

    KV file: ui/run.kv
    """

    # Injected by main.py after ScreenManager is built
    controller: GalilController = ObjectProperty(None, allownone=True)  # type: ignore
    state: MachineState = ObjectProperty(None, allownone=True)  # type: ignore

    # Kivy properties — bound in run.kv
    cycle_running = BooleanProperty(False)
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

    # Machine type flag — controls serration field visibility in KV
    is_serration = BooleanProperty(IS_SERRATION)

    # Knife Grind Adjustment properties
    section_count = NumericProperty(1)
    delta_c_offsets = ListProperty([0.0])        # one offset per section
    selected_section_value = StringProperty("0") # display value for the selected bar

    # -----------------------------------------------------------------------
    # Internal state
    # -----------------------------------------------------------------------
    _update_clock_event = None
    _cycle_start_time: float | None = None

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    def on_kv_post(self, base_widget) -> None:
        """Called by Kivy after all KV ids are assigned.

        Binds the DeltaCBarChart selection observer so selected_section_value
        stays in sync with whichever bar the operator taps.
        """
        chart = self.ids.get("delta_c_chart")
        if chart is not None:
            chart.bind(selected_index=self._on_chart_selection_changed)

    def on_pre_enter(self, *args) -> None:
        """Called by Kivy when operator navigates to this screen.

        Reads CPM values once in the background, then starts the 10 Hz poll loop.
        Shows disconnected indicators immediately if no controller.
        """
        if not self.controller or not self.controller.is_connected():
            self._show_disconnected()
        else:
            jobs.submit(self._read_cpm_values)

        if self._update_clock_event:
            self._update_clock_event.cancel()
        self._update_clock_event = Clock.schedule_interval(self._update_clock, 1 / 10.0)

    def on_leave(self, *args) -> None:
        """Called by Kivy when operator navigates away. Stops the poll loop."""
        if self._update_clock_event:
            self._update_clock_event.cancel()
            self._update_clock_event = None

    # -----------------------------------------------------------------------
    # Polling loop
    # -----------------------------------------------------------------------

    def _update_clock(self, dt: float) -> None:
        """10 Hz Kivy clock callback. Submits background poll if connected."""
        if not self.controller or not self.controller.is_connected():
            self._show_disconnected()
            return
        jobs.submit(self._do_poll)

    def _do_poll(self) -> None:
        """Background thread: read axis positions and cycle status from controller.

        Posts results to main thread via Clock.schedule_once.
        """
        try:
            pos: dict[str, float] = {}
            for axis in ("A", "B", "C", "D"):
                try:
                    raw = self.controller.cmd(f"MG _TP{axis}")
                    pos[axis] = float(raw.strip())
                except Exception:
                    pos[axis] = None  # type: ignore[assignment]

            cycle: dict[str, object] = {}
            if IS_SERRATION:
                for var, key in (
                    (CYCLE_VAR_TOOTH, "tooth"),
                    (CYCLE_VAR_PASS, "pass"),
                    (CYCLE_VAR_DEPTH, "depth"),
                ):
                    try:
                        raw = self.controller.cmd(f"MG {var}")
                        cycle[key] = float(raw.strip())
                    except Exception:
                        cycle[key] = None

            try:
                raw = self.controller.cmd(f"MG {CYCLE_VAR_COMPLETION}")
                cycle["pct"] = float(raw.strip())
            except Exception:
                cycle["pct"] = None

            Clock.schedule_once(lambda *_: self._apply_ui(pos, cycle))

        except Exception as e:
            print(f"[RunScreen] Poll error: {e}")

    def _apply_ui(self, pos: dict, cycle: dict) -> None:
        """Main thread: update all reactive Kivy properties from poll results."""
        # Axis positions — format as integer with comma thousands separator
        for axis, prop in (("A", "pos_a"), ("B", "pos_b"), ("C", "pos_c"), ("D", "pos_d")):
            val = pos.get(axis)
            if val is None:
                setattr(self, prop, "---")
            else:
                try:
                    setattr(self, prop, f"{int(val):,}")
                except (ValueError, TypeError):
                    setattr(self, prop, "---")

        # Cycle completion percentage
        pct = cycle.get("pct")
        if pct is not None:
            try:
                pct_float = float(pct)
                self.cycle_completion_pct = max(0.0, min(100.0, pct_float))
            except (ValueError, TypeError):
                pass

        # Serration-specific fields
        if IS_SERRATION:
            tooth = cycle.get("tooth")
            if tooth is not None:
                try:
                    self.cycle_tooth = str(int(float(tooth)))
                except (ValueError, TypeError):
                    pass

            pass_num = cycle.get("pass")
            if pass_num is not None:
                try:
                    self.cycle_pass = str(int(float(pass_num)))
                except (ValueError, TypeError):
                    pass

            depth = cycle.get("depth")
            if depth is not None:
                try:
                    self.cycle_depth = f"{float(depth):.2f}"
                except (ValueError, TypeError):
                    pass

        # Elapsed time — derived from _cycle_start_time (set when cycle starts)
        if self._cycle_start_time is not None and self.cycle_running:
            elapsed_s = time.time() - self._cycle_start_time
            self.cycle_elapsed = _format_mmss(elapsed_s)

            # ETA: only meaningful when pct > 1% to avoid noise / div-by-zero
            pct_val = self.cycle_completion_pct
            if pct_val > 1.0:
                eta_s = elapsed_s / pct_val * (100.0 - pct_val)
                self.cycle_eta = _format_mmss(eta_s)
            else:
                self.cycle_eta = "--:--"
        else:
            if not self.cycle_running:
                self.cycle_eta = "--:--"

    def _show_disconnected(self) -> None:
        """Show disconnected state: '---' for all positions, clear cycle values."""
        self.pos_a = "---"
        self.pos_b = "---"
        self.pos_c = "---"
        self.pos_d = "---"

    def _read_cpm_values(self) -> None:
        """Background thread: read CPM (counts per unit) for each axis.

        CPM axis variables may not exist on 3-axis machines — catches silently.
        Posts results back to main thread.
        """
        cpm: dict[str, str] = {}
        for axis in ("A", "B", "C", "D"):
            try:
                raw = self.controller.cmd(f"MG cpm{axis}")
                val = float(raw.strip())
                cpm[axis] = f"{int(val):,} cts = 1 unit"
            except Exception:
                cpm[axis] = ""

        def _apply_cpm(*_):
            self.cpm_a = cpm.get("A", "")
            self.cpm_b = cpm.get("B", "")
            self.cpm_c = cpm.get("C", "")
            self.cpm_d = cpm.get("D", "")

        Clock.schedule_once(_apply_cpm)

    # -----------------------------------------------------------------------
    # Action handlers
    # -----------------------------------------------------------------------

    def on_start_pause_toggle(self, btn_state: str) -> None:
        """Handle Start/Pause ToggleButton press.

        Parameters
        ----------
        btn_state : str — Kivy ToggleButton state: 'down' = START pressed,
                          'normal' = PAUSE (was running, now pausing).
        """
        if btn_state == "down":
            # START — begin cycle
            self._cycle_start_time = time.time()
            self.cycle_running = True
            self.cycle_elapsed = "00:00"
            self.cycle_eta = "--:--"
            self.cycle_completion_pct = 0

            def _start_cycle():
                try:
                    self.controller.cmd("XQ #CYCLE")
                except Exception as e:
                    print(f"[RunScreen] Start cycle error: {e}")
                    Clock.schedule_once(lambda *_: self._alert(f"Start failed: {e}"))

            jobs.submit(_start_cycle)
        else:
            # PAUSE — halt execution
            self.cycle_running = False

            def _pause_cycle():
                try:
                    self.controller.cmd("HX")
                except Exception as e:
                    print(f"[RunScreen] Pause cycle error: {e}")
                    Clock.schedule_once(lambda *_: self._alert(f"Pause failed: {e}"))

            jobs.submit(_pause_cycle)

    def on_go_to_rest(self) -> None:
        """Handle Go to Rest button press.

        Sends the REST command and resets the toggle button state.
        """
        # Reset toggle button to 'normal' (not pressed) state
        try:
            btn = self.ids.get("start_pause_btn")
            if btn:
                btn.state = "normal"
        except Exception:
            pass

        self.cycle_running = False

        def _go_rest():
            try:
                self.controller.cmd("XQ #REST")
            except Exception as e:
                print(f"[RunScreen] Go to rest error: {e}")
                Clock.schedule_once(lambda *_: self._alert(f"Go to rest failed: {e}"))

        if self.controller and self.controller.is_connected():
            jobs.submit(_go_rest)

    # -----------------------------------------------------------------------
    # Delta-C (Knife Grind Adjustment)
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

        result: list[float] = []
        chunk = size // n
        for i in range(n):
            start = i * chunk
            end = start + chunk if i < n - 1 else size
            val = offsets[i]
            result.extend([val] * (end - start))

        return result

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
