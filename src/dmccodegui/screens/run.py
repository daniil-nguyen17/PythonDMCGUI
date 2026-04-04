"""RunScreen — operator run screen with live axis positions and cycle monitoring."""
from __future__ import annotations

import time

from kivy.clock import Clock
from kivy.properties import (
    BooleanProperty,
    NumericProperty,
    ObjectProperty,
    StringProperty,
)
from kivy.uix.screenmanager import Screen

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

    # Knife Grind Adjustment properties (Plan 02-02 fills this panel)
    section_count = NumericProperty(0)
    delta_c_offsets: list = []  # per-section C-axis offset values (Plan 02-02)

    # -----------------------------------------------------------------------
    # Internal state
    # -----------------------------------------------------------------------
    _update_clock_event = None
    _cycle_start_time: float | None = None

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

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
