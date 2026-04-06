"""
axes_setup.py — AxesSetupScreen

The primary setup tool for positioning axes before grinding. Setup/Admin personnel
can select any axis (A, B, C, D) from a sidebar, jog it with arrow buttons at
selectable step sizes (10mm/5mm/1mm), teach rest/start points for all axes at once
(capturing all active axes in one operation), and trigger quick action commands.

AXIS DEFINITIONS:
  A — Knife Length
  B — Knife Curve
  C — Grinder Up/Down
  D — Knife Angle

CPM (Counts Per Millimeter):
  Each axis has a CPM value that converts mm steps to encoder counts.
  Read live from controller on enter via "MG cpm{axis}". Falls back to AXIS_CPM_DEFAULTS.
  D axis is rotation — same CPM constant used for "degrees" label in UI.

TEACH OPERATION:
  teach_rest_point() and teach_start_point() each:
    1. Read current positions for active axes via "MG _TD{axis}" (from mc.get_axis_list())
    2. Write scalar DMC variables for active axes only in one semicolon-separated command
    3. Send BV to burn values to NV memory
  Guard: skipped if cycle_running is True.

AXIS SIDEBAR:
  _rebuild_axis_sidebar() hides the D axis button (opacity=0, disabled=True) on Serration
  machines by reading mc.get_axis_list(). Called on every on_pre_enter so hot-swap works.
  If the currently selected axis is no longer in the active axis list, auto-selects 'A'.

QUICK ACTIONS (software variable commands — adjust variable names at integration):
  go_to_rest_all()  → swGoRest=1
  go_to_start_all() → swGoStart=1
  home_all()        → swHomeAll=1
  (These send single-variable commands; the controller program handles axis routing.)

POLLING:
  No automatic polling. Positions are read once on tab enter and refreshed
  after each jog or teach operation (request-response only).

JOG:
  Uses PR (position relative) + BG per axis.
  counts = int(direction * step_mm * cpm)
  Command format: "PR{axis}={counts}" followed by "BG{axis}"

THREADING MODEL:
  All controller I/O in background thread via jobs.submit().
  UI updates posted back to main thread via Clock.schedule_once().

KV FILE: ui/axes_setup.kv
"""
from __future__ import annotations

from kivy.uix.screenmanager import Screen
from kivy.properties import (
    ObjectProperty,
    StringProperty,
    NumericProperty,
    BooleanProperty,
    DictProperty,
)
from kivy.clock import Clock

from ..app_state import MachineState
from ..controller import GalilController
from ..utils import jobs
import dmccodegui.machine_config as mc


# Default CPM values per axis. Read from controller on enter; fall back if read fails.
AXIS_CPM_DEFAULTS: dict[str, float] = {
    "A": 1200.0,
    "B": 1200.0,
    "C": 800.0,
    "D": 500.0,
}

# Axis display names used in the sidebar
AXIS_LABELS: dict[str, str] = {
    "A": "A  Knife Length",
    "B": "B  Knife Curve",
    "C": "C  Grinder Up/Down",
    "D": "D  Knife Angle",
}

# Axis accent colors (r, g, b, a) matching theme.kv comments
AXIS_COLORS: dict[str, list[float]] = {
    "A": [0.980, 0.569, 0.043, 1],   # orange
    "B": [0.659, 0.333, 0.965, 1],   # purple
    "C": [0.024, 0.714, 0.831, 1],   # cyan
    "D": [0.980, 0.749, 0.043, 1],   # yellow
}

# Map axis letter to KV id for sidebar button
_AXIS_BTN_IDS: dict[str, str] = {
    "A": "axis_btn_a",
    "B": "axis_btn_b",
    "C": "axis_btn_c",
    "D": "axis_btn_d",
}


class AxesSetupScreen(Screen):
    """Full axes setup screen: sidebar, jog controls, teach buttons, quick actions."""

    # Injected by main.py after ScreenManager is built
    controller: GalilController = ObjectProperty(None, allownone=True)  # type: ignore
    state: MachineState = ObjectProperty(None, allownone=True)          # type: ignore

    # Currently selected axis shown in the main panel
    _selected_axis = StringProperty("A")

    # Current jog step size in mm (or degrees for D axis)
    _current_step_mm = NumericProperty(10.0)

    # Live position values per axis (display strings)
    pos_current: dict[str, str] = DictProperty(
        {"A": "---", "B": "---", "C": "---", "D": "---"}
    )
    pos_rest: dict[str, str] = DictProperty(
        {"A": "---", "B": "---", "C": "---", "D": "---"}
    )
    pos_start: dict[str, str] = DictProperty(
        {"A": "---", "B": "---", "C": "---", "D": "---"}
    )

    # Suppress UI callbacks during programmatic updates
    _loading = BooleanProperty(False)

    # CPM cache — populated from controller on enter, seeded with defaults
    _axis_cpm: dict[str, float]

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._axis_cpm = dict(AXIS_CPM_DEFAULTS)

    def on_pre_enter(self, *args):
        """One-time read of all positions and CPM on tab entry.

        Also rebuilds the axis sidebar to match the active machine type —
        this enables hot-swap: changing machine type and re-entering the
        screen immediately shows the correct sidebar layout.
        """
        # Rebuild sidebar for current machine type
        self._rebuild_axis_sidebar()

        # One-time read of CPM, current positions, and taught points
        if self.controller and self.controller.is_connected():
            jobs.submit(self._read_initial_values)

    # ── Axis sidebar ──────────────────────────────────────────────────────────

    def _rebuild_axis_sidebar(self) -> None:
        """Show/hide axis sidebar buttons based on the active machine type.

        Uses opacity/disabled swap (NOT widget add/remove) to preserve KV ids.
        If the currently selected axis is not in the active axis list,
        auto-selects 'A' (the first visible axis).

        Uses mc.get_axis_list() to determine which axes are active.
        On error (machine not configured), falls back to showing all 4 axes.
        """
        try:
            axis_list = mc.get_axis_list()
        except ValueError:
            # machine_config not yet configured — show all axes as fallback
            axis_list = ["A", "B", "C", "D"]

        if not axis_list:
            print("[AxesSetup] _rebuild_axis_sidebar: empty axis_list, skipping")
            return

        for axis, btn_id in _AXIS_BTN_IDS.items():
            btn = self.ids.get(btn_id)
            if btn is None:
                continue
            visible = axis in axis_list
            btn.opacity = 1.0 if visible else 0.0
            btn.disabled = not visible

        # If selected axis is now hidden, auto-select the first visible one
        if self._selected_axis not in axis_list:
            self._selected_axis = axis_list[0]
            # Also update KV toggle button state: set first axis button to 'down'
            first_btn_id = _AXIS_BTN_IDS.get(axis_list[0])
            if first_btn_id:
                first_btn = self.ids.get(first_btn_id)
                if first_btn is not None:
                    first_btn.state = "down"

    # ── Axis selection ────────────────────────────────────────────────────────

    def select_axis(self, axis: str) -> None:
        """Set the active axis shown in the main panel."""
        self._selected_axis = axis

    # ── Step size ─────────────────────────────────────────────────────────────

    def set_step(self, mm: float) -> None:
        """Set the jog step size. Called from KV ToggleButton on_release."""
        self._current_step_mm = mm

    # ── Jog ───────────────────────────────────────────────────────────────────

    def jog_axis(self, axis: str, direction: int) -> None:
        """
        Jog the given axis by (direction * _current_step_mm * cpm) counts.

        Uses PR (Position Relative) + BG per axis so only the target axis moves.
        Commands: "PR{axis}={counts}" then "BG{axis}".
        Both commands are sent in one background job to keep them sequential.
        """
        if not self.controller or not self.controller.is_connected():
            return

        cpm = self._axis_cpm.get(axis, AXIS_CPM_DEFAULTS.get(axis, 0.0))
        if cpm <= 0:
            return

        counts = int(direction * self._current_step_mm * cpm)
        ctrl = self.controller

        def do_jog():
            try:
                ctrl.cmd(f"PR{axis}={counts}")
                ctrl.cmd(f"BG{axis}")
                # Read back new position after move command
                raw = ctrl.cmd(f"MG _TD{axis}").strip()

                def update_pos(*_):
                    try:
                        self.pos_current[axis] = f"{float(raw):.1f}"
                    except (ValueError, TypeError):
                        pass

                Clock.schedule_once(update_pos)
            except Exception as e:
                print(f"[AxesSetup] Jog {axis} failed: {e}")

        jobs.submit(do_jog)

    # ── Teach ─────────────────────────────────────────────────────────────────

    def teach_rest_point(self) -> None:
        """
        Capture active axis positions and store as rest points.

        Reads positions only for axes in mc.get_axis_list() to avoid
        controller errors on undefined variables (e.g. no D axis on Serration).

        1. Read MG _TD{axis} for each axis in mc.get_axis_list()
        2. Write restPt{axis}=val for each axis in one semicolon-separated command
        3. Send BV to burn to NV memory
        Guard: skipped if cycle_running is True.
        """
        if self.state and self.state.cycle_running:
            return
        if not self.controller or not self.controller.is_connected():
            return

        try:
            axis_list = mc.get_axis_list()
        except ValueError:
            axis_list = ["A", "B", "C", "D"]

        if not axis_list:
            print("[AxesSetup] teach_rest_point: empty axis_list, aborting")
            return

        ctrl = self.controller

        def do_teach():
            try:
                # Read positions for active axes only
                vals: dict[str, int] = {}
                for axis in axis_list:
                    raw = ctrl.cmd(f"MG _TD{axis}").strip()
                    vals[axis] = int(float(raw))

                # Build write command for active axes only
                parts = [f"restPt{axis}={vals[axis]}" for axis in axis_list]
                write_cmd = ";".join(parts)
                ctrl.cmd(write_cmd)
                ctrl.cmd("BV")

                # Read back from controller to confirm values were stored
                readback: dict[str, str] = {}
                current: dict[str, str] = {}
                for axis in axis_list:
                    try:
                        raw = ctrl.cmd(f"MG restPt{axis}").strip()
                        readback[axis] = f"{float(raw):.1f}"
                    except Exception:
                        readback[axis] = str(vals[axis])
                    try:
                        raw = ctrl.cmd(f"MG _TD{axis}").strip()
                        current[axis] = f"{float(raw):.1f}"
                    except Exception:
                        pass

                def update_ui(*_):
                    for axis, val in readback.items():
                        self.pos_rest[axis] = val
                    for axis, val in current.items():
                        self.pos_current[axis] = val

                Clock.schedule_once(update_ui)
            except Exception as e:
                print(f"[AxesSetup] teach_rest_point failed: {e}")

        jobs.submit(do_teach)

    def teach_start_point(self) -> None:
        """
        Capture active axis positions and store as start points.

        Reads positions only for axes in mc.get_axis_list() to avoid
        controller errors on undefined variables (e.g. no D axis on Serration).

        1. Read MG _TD{axis} for each axis in mc.get_axis_list()
        2. Write startPt{axis}=val for each axis in one semicolon-separated command
        3. Send BV to burn to NV memory
        Guard: skipped if cycle_running is True.
        """
        if self.state and self.state.cycle_running:
            return
        if not self.controller or not self.controller.is_connected():
            return

        try:
            axis_list = mc.get_axis_list()
        except ValueError:
            axis_list = ["A", "B", "C", "D"]

        if not axis_list:
            print("[AxesSetup] teach_start_point: empty axis_list, aborting")
            return

        ctrl = self.controller

        def do_teach():
            try:
                # Read positions for active axes only
                vals: dict[str, int] = {}
                for axis in axis_list:
                    raw = ctrl.cmd(f"MG _TD{axis}").strip()
                    vals[axis] = int(float(raw))

                # Build write command for active axes only
                parts = [f"startPt{axis}={vals[axis]}" for axis in axis_list]
                write_cmd = ";".join(parts)
                ctrl.cmd(write_cmd)
                ctrl.cmd("BV")

                # Read back from controller to confirm values were stored
                readback: dict[str, str] = {}
                current: dict[str, str] = {}
                for axis in axis_list:
                    try:
                        raw = ctrl.cmd(f"MG startPt{axis}").strip()
                        readback[axis] = f"{float(raw):.1f}"
                    except Exception:
                        readback[axis] = str(vals[axis])
                    try:
                        raw = ctrl.cmd(f"MG _TD{axis}").strip()
                        current[axis] = f"{float(raw):.1f}"
                    except Exception:
                        pass

                def update_ui(*_):
                    for axis, val in readback.items():
                        self.pos_start[axis] = val
                    for axis, val in current.items():
                        self.pos_current[axis] = val

                Clock.schedule_once(update_ui)
            except Exception as e:
                print(f"[AxesSetup] teach_start_point failed: {e}")

        jobs.submit(do_teach)

    # ── Quick actions ─────────────────────────────────────────────────────────

    def go_to_rest_all(self) -> None:
        """Send software variable command to move all axes to rest position."""
        self._send_sw_var("swGoRest=1")

    def go_to_start_all(self) -> None:
        """Send software variable command to move all axes to start position."""
        self._send_sw_var("swGoStart=1")

    def home_all(self) -> None:
        """Send software variable command to home all axes."""
        self._send_sw_var("swHomeAll=1")

    def _send_sw_var(self, command: str) -> None:
        """Submit a single software-variable command via background thread."""
        if not self.controller or not self.controller.is_connected():
            return

        ctrl = self.controller

        def do_send():
            try:
                ctrl.cmd(command)
            except Exception as e:
                print(f"[AxesSetup] Command '{command}' failed: {e}")

        jobs.submit(do_send)

    # ── Initial load ──────────────────────────────────────────────────────────

    def _read_initial_values(self) -> None:
        """
        Background job: one-time read of CPM, current positions, and taught
        rest/start points from controller. Called once on on_pre_enter.

        Only reads for active axes (from mc.get_axis_list()) to avoid
        controller errors on undefined variables.
        """
        ctrl = self.controller
        if not ctrl or not ctrl.is_connected():
            return

        try:
            axis_list = mc.get_axis_list()
        except ValueError:
            axis_list = ["A", "B", "C", "D"]

        # Read CPM values for each axis (attempt all — CPM vars exist on most machines)
        cpm_updates = {}
        for axis in ("A", "B", "C", "D"):
            try:
                raw = ctrl.cmd(f"MG cpm{axis}").strip()
                val = float(raw)
                if val > 0:
                    cpm_updates[axis] = val
            except Exception:
                pass  # Keep default

        # Read current positions for active axes
        current_updates: dict[str, str] = {}
        for axis in axis_list:
            try:
                raw = ctrl.cmd(f"MG _TD{axis}").strip()
                current_updates[axis] = f"{float(raw):.1f}"
            except Exception:
                pass

        # Read existing rest/start points for active axes only
        rest_updates: dict[str, str] = {}
        start_updates: dict[str, str] = {}
        for axis in axis_list:
            try:
                raw = ctrl.cmd(f"MG restPt{axis}").strip()
                rest_updates[axis] = f"{float(raw):.1f}"
            except Exception:
                pass
            try:
                raw = ctrl.cmd(f"MG startPt{axis}").strip()
                start_updates[axis] = f"{float(raw):.1f}"
            except Exception:
                pass

        def apply_updates(*_):
            self._axis_cpm.update(cpm_updates)
            for axis, val in current_updates.items():
                self.pos_current[axis] = val
            for axis, val in rest_updates.items():
                self.pos_rest[axis] = val
            for axis, val in start_updates.items():
                self.pos_start[axis] = val

        Clock.schedule_once(apply_updates)

    # ── Utility ───────────────────────────────────────────────────────────────

    def _alert(self, message: str) -> None:
        """Push a message to the app-wide banner ticker."""
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
