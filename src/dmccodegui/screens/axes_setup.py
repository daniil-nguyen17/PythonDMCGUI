"""
axes_setup.py — AxesSetupScreen

All axes visible at once with jog controls per axis. Two modes: "Set Rest
Points" and "Set Start Points" — a single Save button writes the current
positions as rest or start points accordingly.

AXIS DEFINITIONS:
  A — Knife Length
  B — Knife Curve
  C — Grinder Up/Down
  D — Knife Angle

CPM (Counts Per Millimeter):
  Each axis has a CPM value that converts mm steps to encoder counts.
  Read live from controller on enter via "MG cpm{axis}". Falls back to AXIS_CPM_DEFAULTS.
  D axis is rotation — same CPM constant used for "degrees" label in UI.

MODE:
  _mode = "rest" | "start"
  Controls which saved values are shown in the "Saved" column and which
  variable set (restPt / startPt) the Save button writes to.

SAVE:
  save_points() delegates to teach_rest_point() or teach_start_point()
  based on _mode. Each reads current _TD positions, writes to controller,
  burns BV, and reads back to confirm.

AXIS VISIBILITY:
  _rebuild_axis_rows() hides the D axis row (opacity=0, disabled=True) on
  Serration machines by reading mc.get_axis_list(). Called on every
  on_pre_enter so hot-swap works.

QUICK ACTIONS (software variable commands):
  go_to_rest_all()  → swGoRest=1
  go_to_start_all() → swGoStart=1
  home_all()        → swHomeAll=1

NO POLLING:
  Positions are read once on tab enter and refreshed after each jog or
  teach operation (request-response only).

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
from ..hmi.dmc_vars import HMI_SETP, HMI_TRIGGER_FIRE, HMI_TRIGGER_DEFAULT
import dmccodegui.machine_config as mc


# Default CPM values per axis. Read from controller on enter; fall back if read fails.
AXIS_CPM_DEFAULTS: dict[str, float] = {
    "A": 1200.0,
    "B": 1200.0,
    "C": 800.0,
    "D": 500.0,
}

# Axis display names (used in code references; KV has its own labels)
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

# Map axis letter to KV id for axis row (for hide/show on Serration)
_AXIS_ROW_IDS: dict[str, str] = {
    "A": "axis_row_a",
    "B": "axis_row_b",
    "C": "axis_row_c",
    "D": "axis_row_d",
}


class AxesSetupScreen(Screen):
    """All-axes setup screen with mode toggle, jog per axis, and save button."""

    # Injected by main.py after ScreenManager is built
    controller: GalilController = ObjectProperty(None, allownone=True)  # type: ignore
    state: MachineState = ObjectProperty(None, allownone=True)          # type: ignore

    # Current mode: "rest" or "start"
    _mode = StringProperty("rest")

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

    # True once CPM values have been read from the controller.
    # Jog is blocked until this is True to prevent moves with wrong CPM.
    _cpm_ready = BooleanProperty(False)

    # CPM cache — empty until read from controller (no defaults used for jog)
    _axis_cpm: dict[str, float]

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._axis_cpm = {}
        self._cpm_ready = False

    def on_pre_enter(self, *args):
        """One-time read of all positions and CPM on tab entry.

        Also rebuilds axis row visibility to match the active machine type —
        this enables hot-swap: changing machine type and re-entering the
        screen immediately shows the correct layout.
        """
        # Clear CPM so stale values from a previous visit can't be used
        self._axis_cpm = {}
        self._cpm_ready = False

        # Show/hide axis rows for current machine type
        self._rebuild_axis_rows()

        # Update saved-value column labels for current mode
        self._update_saved_labels()

        # Fire hmiSetp to tell controller we're in setup mode, then read values
        if self.controller and self.controller.is_connected():
            jobs.submit(self._enter_setup_and_read)

    def on_leave(self, *args):
        """Reset hmiSetp=1 to exit setup mode and clear CPM ready flag."""
        self._cpm_ready = False
        if self.controller and self.controller.is_connected():
            try:
                self.controller.cmd(f"{HMI_SETP}={HMI_TRIGGER_DEFAULT}")
            except Exception:
                pass

    # ── Axis row visibility ──────────────────────────────────────────────────

    def _rebuild_axis_rows(self) -> None:
        """Show/hide axis rows based on the active machine type.

        Uses opacity/disabled swap (NOT widget add/remove) to preserve KV ids.
        Uses mc.get_axis_list() to determine which axes are active.
        On error (machine not configured), falls back to showing all 4 axes.
        """
        try:
            axis_list = mc.get_axis_list()
        except ValueError:
            axis_list = ["A", "B", "C", "D"]

        if not axis_list:
            print("[AxesSetup] _rebuild_axis_rows: empty axis_list, skipping")
            return

        for axis, row_id in _AXIS_ROW_IDS.items():
            row = self.ids.get(row_id)
            if row is None:
                continue
            visible = axis in axis_list
            row.opacity = 1.0 if visible else 0.0
            row.disabled = not visible
            row.size_hint_y = None if visible else 0
            row.height = "80dp" if visible else 0

    # ── Mode toggle ──────────────────────────────────────────────────────────

    def set_mode(self, mode: str) -> None:
        """Switch between 'rest' and 'start' mode. Updates saved-value labels
        and save button text/color."""
        self._mode = mode
        self._update_saved_labels()
        self._update_save_button()

    def _update_position_labels(self) -> None:
        """Push pos_current values directly to KV label widgets.

        KV expressions like root.pos_current.get('A') do NOT rebind when the
        dict changes, so we must update the Label.text imperatively.
        """
        for axis in ("A", "B", "C", "D"):
            lbl = self.ids.get(f"pos_{axis.lower()}")
            if lbl:
                lbl.text = self.pos_current.get(axis, "---")

    def _update_saved_labels(self) -> None:
        """Update the 'Saved Rest' / 'Saved Start' labels and values in each
        axis row to match the current mode."""
        label_text = "Saved Rest" if self._mode == "rest" else "Saved Start"
        source = self.pos_rest if self._mode == "rest" else self.pos_start

        for axis in ("A", "B", "C", "D"):
            lbl = self.ids.get(f"saved_label_{axis.lower()}")
            val = self.ids.get(f"saved_val_{axis.lower()}")
            if lbl:
                lbl.text = label_text
            if val:
                val.text = source.get(axis, "---")

    def _update_save_button(self) -> None:
        """Update save button text and color based on current mode."""
        btn = self.ids.get("save_btn")
        if not btn:
            return
        if self._mode == "rest":
            btn.text = "SAVE AS REST POINTS"
            btn.background_color = (0.031, 0.314, 0.471, 1)
        else:
            btn.text = "SAVE AS START POINTS"
            btn.background_color = (0.031, 0.471, 0.188, 1)

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

        if not self._cpm_ready:
            print(f"[AxesSetup] Jog blocked — CPM not yet read from controller")
            return

        cpm = self._axis_cpm.get(axis, 0.0)
        if cpm <= 0:
            print(f"[AxesSetup] Jog blocked — no CPM value for axis {axis}, _axis_cpm={self._axis_cpm}")
            return

        counts = int(direction * self._current_step_mm * cpm)
        print(f"[AxesSetup] Jog {axis}: step={self._current_step_mm} * cpm={cpm} = {counts} counts")
        ctrl = self.controller

        lbl_id = f"pos_{axis.lower()}"

        def _push_pos(val_str):
            """Push a position string to the single axis label on the main thread."""
            def _update(*_):
                self.pos_current[axis] = val_str
                lbl = self.ids.get(lbl_id)
                if lbl:
                    lbl.text = val_str
            Clock.schedule_once(_update)

        def do_jog():
            try:
                ctrl.cmd(f"PR{axis}={counts}")
                ctrl.cmd(f"BG{axis}")
                # Poll position live while axis is moving, update label each tick
                import time
                for _ in range(60):  # up to 6 seconds max
                    time.sleep(0.1)
                    try:
                        raw = ctrl.cmd(f"MG _TD{axis}").strip()
                        _push_pos(f"{float(raw):.1f}")
                    except Exception:
                        pass
                    try:
                        bg_raw = ctrl.cmd(f"MG _BG{axis}").strip()
                        if float(bg_raw) == 0:
                            break  # motion complete
                    except Exception:
                        break
                # Final position read after motion stopped
                raw = ctrl.cmd(f"MG _TD{axis}").strip()
                print(f"[AxesSetup] Jog {axis} final: MG _TD{axis} -> {raw}")
                _push_pos(f"{float(raw):.1f}")
            except Exception as e:
                print(f"[AxesSetup] Jog {axis} failed: {e}")

        jobs.submit(do_jog)

    # ── Save ─────────────────────────────────────────────────────────────────

    def save_points(self) -> None:
        """Delegate to teach_rest_point or teach_start_point based on mode."""
        if self._mode == "rest":
            self.teach_rest_point()
        else:
            self.teach_start_point()

    # ── Teach ─────────────────────────────────────────────────────────────────

    def teach_rest_point(self) -> None:
        """
        Capture active axis positions and store as rest points.

        1. Read MG _TD{axis} for each axis in mc.get_axis_list()
        2. Write restPt{axis}=val in one semicolon-separated command
        3. Send BV to burn to NV memory
        4. Read back to confirm
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
                vals: dict[str, int] = {}
                for axis in axis_list:
                    raw = ctrl.cmd(f"MG _TD{axis}").strip()
                    vals[axis] = int(float(raw))

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
                    self.pos_rest.update(readback)
                    self.pos_current.update(current)
                    self._update_position_labels()
                    # Refresh saved-value column if in rest mode
                    if self._mode == "rest":
                        self._update_saved_labels()

                Clock.schedule_once(update_ui)
            except Exception as e:
                print(f"[AxesSetup] teach_rest_point failed: {e}")

        jobs.submit(do_teach)

    def teach_start_point(self) -> None:
        """
        Capture active axis positions and store as start points.

        1. Read MG _TD{axis} for each axis in mc.get_axis_list()
        2. Write startPt{axis}=val in one semicolon-separated command
        3. Send BV to burn to NV memory
        4. Read back to confirm
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
                vals: dict[str, int] = {}
                for axis in axis_list:
                    raw = ctrl.cmd(f"MG _TD{axis}").strip()
                    vals[axis] = int(float(raw))

                parts = [f"startPt{axis}={vals[axis]}" for axis in axis_list]
                write_cmd = ";".join(parts)
                ctrl.cmd(write_cmd)
                ctrl.cmd("BV")

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
                    self.pos_start.update(readback)
                    self.pos_current.update(current)
                    self._update_position_labels()
                    # Refresh saved-value column if in start mode
                    if self._mode == "start":
                        self._update_saved_labels()

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

    def _enter_setup_and_read(self) -> None:
        """Fire hmiSetp=0 to enter setup mode, then read all initial values."""
        ctrl = self.controller
        if not ctrl or not ctrl.is_connected():
            return
        try:
            ctrl.cmd(f"{HMI_SETP}={HMI_TRIGGER_FIRE}")
            print(f"[AxesSetup] Fired {HMI_SETP}={HMI_TRIGGER_FIRE}")
        except Exception as e:
            print(f"[AxesSetup] Failed to fire hmiSetp: {e}")
        self._read_initial_values()

    @staticmethod
    def _read_one(ctrl, command: str) -> str | None:
        """Send a single MG command, return stripped response or None on error."""
        try:
            raw = ctrl.cmd(command).strip()
            return raw
        except Exception as e:
            print(f"[AxesSetup] Read failed: {command} -> {e}")
            return None

    def _read_initial_values(self) -> None:
        """
        Background job: one-time read of CPM, current positions, and taught
        rest/start points from controller. Called once on on_pre_enter.

        Each value is read individually with its own cmd() call.
        All reads are logged so misalignment can be debugged.
        """
        ctrl = self.controller
        if not ctrl or not ctrl.is_connected():
            return

        try:
            axis_list = mc.get_axis_list()
        except ValueError:
            axis_list = ["A", "B", "C", "D"]

        rd = self._read_one

        # ── 1. CPM values (all 4 axes) ───────────────────────────────────
        # Only axes with a successful read get a CPM value.
        # Axes that fail stay out of _axis_cpm so jog is blocked for them.
        cpm_updates: dict[str, float] = {}
        for axis in ("A", "B", "C", "D"):
            raw = rd(ctrl, f"MG cpm{axis}")
            if raw is not None:
                try:
                    val = float(raw)
                    if val > 0:
                        cpm_updates[axis] = val
                    else:
                        print(f"[AxesSetup] CPM {axis} returned {val} (not positive), jog blocked for this axis")
                except (ValueError, TypeError):
                    print(f"[AxesSetup] CPM {axis} parse failed: '{raw}', jog blocked for this axis")
            else:
                print(f"[AxesSetup] CPM {axis} read failed, jog blocked for this axis")
        print(f"[AxesSetup] CPM values from controller: {cpm_updates}")

        # ── 2. Rest points (active axes only) ────────────────────────────
        rest_updates: dict[str, str] = {}
        for axis in axis_list:
            raw = rd(ctrl, f"MG restPt{axis}")
            if raw is not None:
                try:
                    rest_updates[axis] = f"{float(raw):.1f}"
                except (ValueError, TypeError):
                    pass
        print(f"[AxesSetup] Rest points read: {rest_updates}")

        # ── 3. Start points (active axes only) ───────────────────────────
        start_updates: dict[str, str] = {}
        for axis in axis_list:
            raw = rd(ctrl, f"MG startPt{axis}")
            if raw is not None:
                try:
                    start_updates[axis] = f"{float(raw):.1f}"
                except (ValueError, TypeError):
                    pass
        print(f"[AxesSetup] Start points read: {start_updates}")

        # ── 4. Current positions LAST (active axes only) ─────────────────
        # Read _TD last so it reflects the most up-to-date position
        current_updates: dict[str, str] = {}
        for axis in axis_list:
            raw = rd(ctrl, f"MG _TD{axis}")
            if raw is not None:
                try:
                    current_updates[axis] = f"{float(raw):.1f}"
                except (ValueError, TypeError):
                    pass
        print(f"[AxesSetup] Current positions read: {current_updates}")

        def apply_updates(*_):
            self._axis_cpm.update(cpm_updates)
            self._cpm_ready = True
            self.pos_current.update(current_updates)
            self.pos_rest.update(rest_updates)
            self.pos_start.update(start_updates)
            # Push to KV labels imperatively (DictProperty doesn't rebind .get())
            self._update_position_labels()
            # Refresh the saved-value column with loaded data
            self._update_saved_labels()

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
