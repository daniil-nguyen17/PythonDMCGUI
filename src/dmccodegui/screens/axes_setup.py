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

QUICK ACTIONS (HMI one-shot trigger commands):
  go_to_rest_all()  → hmiGoRs=0
  go_to_start_all() → hmiGoSt=0
  home_all()        → hmiHome=0

NO POLLING:
  Positions are read once on tab enter and refreshed after each jog or
  teach operation (request-response only).

JOG:
  Uses PR (position relative) + BG per axis.
  counts = int(direction * step_mm * cpm)
  Command format: "PR{axis}={counts}" followed by "BG{axis}"
  Gated on dmc_state == STATE_SETUP and no in-progress motion (_BG != 0).

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
from ..hmi.dmc_vars import (
    HMI_SETP, HMI_TRIGGER_FIRE, HMI_TRIGGER_DEFAULT,
    HMI_GO_REST, HMI_GO_START, HMI_EXIT_SETUP, HMI_HOME, HMI_NEWS,
    STATE_SETUP, STATE_GRINDING, STATE_HOMING,
)
import dmccodegui.machine_config as mc

# Screens that are siblings within the setup flow.
# Navigating between these does NOT trigger the exit-setup HMI command.
_SETUP_SCREENS: frozenset[str] = frozenset({
    "axes_setup", "parameters", "profiles", "users", "diagnostics",
})

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

    # Current mode: "" (no selection), "rest", or "start"
    _mode = StringProperty("")

    # Command response log for setup operations
    cmd_log_text = StringProperty("")

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

        Smart enter: if dmc_state is already STATE_SETUP (e.g. navigating from
        a sibling setup screen), skip hmiSetp=0 and just refresh values.
        """
        # Clear CPM so stale values from a previous visit can't be used
        self._axis_cpm = {}
        self._cpm_ready = False
        self.cmd_log_text = ""

        # Show/hide axis rows for current machine type
        self._rebuild_axis_rows()

        # Reset mode to unselected — operator must pick rest or start
        self._mode = ""
        rest_btn = self.ids.get("mode_rest_btn")
        start_btn = self.ids.get("mode_start_btn")
        if rest_btn:
            rest_btn.state = "normal"
        if start_btn:
            start_btn.state = "normal"

        # Update saved-value column labels for current mode
        self._update_saved_labels()
        self._update_save_button()

        # Guard: do NOT send hmiSetp while controller is in motion
        if (self.state is not None
                and self.state.dmc_state in (STATE_GRINDING, STATE_HOMING)):
            return

        # Fire hmiSetp only if we are NOT already in setup mode.
        # When dmc_state is already STATE_SETUP (e.g. navigating between setup
        # sibling screens), skip the trigger and just refresh values.
        if self.controller and self.controller.is_connected():
            already_in_setup = (
                self.state is not None and self.state.dmc_state == STATE_SETUP
            )
            if already_in_setup:
                jobs.submit(self._read_initial_values)
            else:
                jobs.submit(self._enter_setup_and_read)

    def on_leave(self, *args):
        """Fire hmiExSt=0 only when leaving to a non-setup screen.

        Navigating between setup siblings (axes_setup, parameters) does NOT
        trigger exit-setup — the controller stays in STATE_SETUP the whole time.
        """
        self._cpm_ready = False
        next_screen = ""
        if self.manager:
            next_screen = self.manager.current
        if next_screen not in _SETUP_SCREENS:
            if self.controller and self.controller.is_connected():
                ctrl = self.controller
                jobs.submit(lambda: ctrl.cmd(f"{HMI_EXIT_SETUP}={HMI_TRIGGER_FIRE}"))

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

    # ── Command log ────────────────────────────────────────────────────────

    def _log_cmd(self, text: str) -> None:
        """Append a line to the command response log (main thread). Cap at 50 lines."""
        lines = self.cmd_log_text.split('\n') if self.cmd_log_text else []
        lines.append(text)
        if len(lines) > 50:
            lines = lines[-50:]
        self.cmd_log_text = '\n'.join(lines)
        scroll = self.ids.get("setup_log_scroll")
        if scroll:
            Clock.schedule_once(lambda *_: setattr(scroll, 'scroll_y', 0))

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
        if self._mode == "rest":
            label_text = "Saved Rest"
            source = self.pos_rest
        elif self._mode == "start":
            label_text = "Saved Start"
            source = self.pos_start
        else:
            label_text = "---"
            source = {"A": "---", "B": "---", "C": "---", "D": "---"}

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
            btn.text = "LƯU ĐIỂM NGHỈ"
            btn.background_color = (0.031, 0.314, 0.471, 1)
            btn.disabled = False
        elif self._mode == "start":
            btn.text = "LƯU ĐIỂM BẮT ĐẦU"
            btn.background_color = (0.031, 0.471, 0.188, 1)
            btn.disabled = False
        else:
            btn.text = "CHỌN CHẾ ĐỘ"
            btn.background_color = (0.15, 0.15, 0.15, 0.6)
            btn.disabled = True

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

        Gates (in order):
          1. Controller connected
          2. dmc_state == STATE_SETUP (not in idle/grinding)
          3. _cpm_ready (CPM read from controller)
          4. cpm > 0 for the axis
          5. _BG{axis} == 0 (no jog in progress) — checked inside do_jog()
        """
        if not self.controller or not self.controller.is_connected():
            print(f"[AxesSetup] Jog {axis} blocked — controller not connected (controller={self.controller})")
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
                # In-progress gate: skip if previous jog still running
                try:
                    raw = ctrl.cmd(f"MG _BG{axis}").strip()
                    if float(raw) != 0:
                        return
                except Exception:
                    return

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
                final_val = f"{float(raw):.1f}"
                _push_pos(final_val)
                Clock.schedule_once(
                    lambda *_, a=axis, c=counts, v=final_val: self._log_cmd(
                        f"JOG {a}: {c:+d} cts -> {v}"
                    )
                )
            except Exception as e:
                Clock.schedule_once(lambda *_, err=e: self._log_cmd(f"JOG ERROR: {err}"))

        jobs.submit(do_jog)

    # ── Save ─────────────────────────────────────────────────────────────────

    def save_points(self) -> None:
        """Delegate to teach_rest_point or teach_start_point based on mode."""
        if self._mode == "rest":
            self.teach_rest_point()
        elif self._mode == "start":
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

                # Build log message
                log_parts = [f"restPt{a}={vals[a]}" for a in axis_list]
                log_msg = "REST SET: " + ", ".join(log_parts)

                def update_ui(*_):
                    self.pos_rest.update(readback)
                    self.pos_current.update(current)
                    self._update_position_labels()
                    if self._mode == "rest":
                        self._update_saved_labels()
                    self._log_cmd(log_msg)

                Clock.schedule_once(update_ui)
            except Exception as e:
                Clock.schedule_once(lambda *_, err=e: self._log_cmd(f"REST ERROR: {err}"))

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

                log_parts = [f"startPt{a}={vals[a]}" for a in axis_list]
                log_msg = "START SET: " + ", ".join(log_parts)

                def update_ui(*_):
                    self.pos_start.update(readback)
                    self.pos_current.update(current)
                    self._update_position_labels()
                    if self._mode == "start":
                        self._update_saved_labels()
                    self._log_cmd(log_msg)

                Clock.schedule_once(update_ui)
            except Exception as e:
                Clock.schedule_once(lambda *_, err=e: self._log_cmd(f"START ERROR: {err}"))

        jobs.submit(do_teach)

    # ── Quick actions ─────────────────────────────────────────────────────────

    def go_to_rest_all(self) -> None:
        """Fire HMI trigger to move all axes to rest position."""
        self._fire_hmi_trigger(HMI_GO_REST, "Go To Rest")

    def go_to_start_all(self) -> None:
        """Fire HMI trigger to move all axes to start position."""
        self._fire_hmi_trigger(HMI_GO_START, "Go To Start")

    def home_all(self) -> None:
        """Fire HMI trigger to home all axes."""
        self._fire_hmi_trigger(HMI_HOME, "Home All")

    def _fire_hmi_trigger(self, trigger_var: str, label: str) -> None:
        """Fire an HMI one-shot trigger via background thread."""
        if not self.controller or not self.controller.is_connected():
            return
        ctrl = self.controller

        def do_fire():
            try:
                ctrl.cmd(f"{trigger_var}={HMI_TRIGGER_FIRE}")
            except Exception as e:
                print(f"[AxesSetup] {label} failed: {e}")

        jobs.submit(do_fire)

    # ── New Session ───────────────────────────────────────────────────────────

    def on_new_session(self) -> None:
        """Show confirmation dialog for new session (stone change).

        Gated on setup_unlocked role — operators cannot start a new session.
        """
        if self.state and not self.state.setup_unlocked:
            return  # operator role — silently ignore
        from kivy.uix.popup import Popup
        from kivy.uix.button import Button
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label

        content = BoxLayout(orientation='vertical', spacing=8, padding=8)
        content.add_widget(Label(
            text="Start new session?\nThis will home all axes\nand reset knife counts.",
            halign='center',
        ))
        btns = BoxLayout(size_hint_y=None, height=48, spacing=8)
        popup = Popup(title="New Session", content=content, size_hint=(0.6, 0.4), auto_dismiss=False)

        def confirm(*_):
            popup.dismiss()
            self._fire_new_session()

        btns.add_widget(Button(text="Confirm", on_release=confirm))
        btns.add_widget(Button(text="Cancel", on_release=popup.dismiss))
        content.add_widget(btns)
        popup.open()

    def _fire_new_session(self) -> None:
        """Fire hmiNewS=0 to start a new session."""
        self._fire_hmi_trigger(HMI_NEWS, "New Session")

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
