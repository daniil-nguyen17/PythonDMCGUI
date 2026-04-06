from __future__ import annotations

"""
start.py — StartScreen

This screen lets the operator view and adjust the Start Point for each axis.
The Start Point is where the machine moves at the beginning of a grinding cycle
(Tooth 0 on A, B cleared from grinder, C already manually positioned).

DMC VARIABLES: startPtA, startPtB, startPtC, startPtD (individual named variables)
  startPtA = A axis start position     (counts)
  startPtB = B_left  start position    (counts) — left B motor
  startPtC = B_right start position    (counts) — right B motor
  startPtD = C axis  start position    (counts)

  Variable names imported from dmccodegui.hmi.dmc_vars (STARTPT_BY_AXIS).
  Previously used the StartPnt DMC array (indices 0-3) — migrated to individual variables in plan 09-03.

KV FILE: ui/start.kv
  Each axis has two widgets in the KV:
    ids.<axis>_ctrl    — HControl or VControl composite widget
                          └── ids.ctrl_input  — the editable TextInput inside the control
    ids.<axis>_display — read-only TextInput showing the value from the controller

WORKFLOW:
  1. On screen enter: auto-reads startPtA/B/C/D from controller via individual MG queries
     and fills both the editable input (ctrl_input) and the read-only display for each axis.
  2. Operator uses arrow buttons (via adjust_axis) or manually edits ctrl_input.
  3. 'Luu Diem Start' button calls save_values(), which:
       a. Writes new values to controller via semicolon-joined assignment
       b. Sends BV to save variables to flash
       c. Sends PA (Position Absolute) command for all 4 axes
       d. Sends BG (Begin) to start the move

THREADING MODEL:
  controller I/O in on_pre_enter is done on the calling thread (Kivy main thread)
  because on_pre_enter is brief and synchronous. For longer operations, use jobs.submit().
  dmcCommand() always submits to a background thread.
"""

from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

from ..app_state import MachineState
from ..controller import GalilController
from ..utils import jobs
from dmccodegui.hmi.dmc_vars import STARTPT_A, STARTPT_B, STARTPT_C, STARTPT_D, STARTPT_BY_AXIS


class StartScreen(Screen):
    # Injected by main.py after the ScreenManager is built
    controller: GalilController = ObjectProperty(None)  # type: ignore
    state: MachineState = ObjectProperty(None)          # type: ignore

    # Local copy of the start point values (4 floats: A, B_left, B_right, C)
    # Maps to startPtA, startPtB, startPtC, startPtD on the controller.
    # Updated from the controller on enter, and written back on save.
    start_vals = ([0.0, 0.0, 0.0, 0.0])

    def on_pre_enter(self, *args):
        """
        Called by Kivy each time the operator navigates to this screen.

        Reads startPtA, startPtB, startPtC, startPtD from the controller via individual
        MG queries and fills both the editable inputs and read-only display boxes for all 4 axes.

        Axis-to-variable mapping:
          A widget       <- startPtA (index 0)
          B_left widget  <- startPtB (index 1)
          B_right widget <- startPtC (index 2)
          C widget       <- startPtD (index 3)

        Falls back to self._load_from_state() if:
          - No controller is connected
          - The controller read throws an exception (e.g. timeout, disconnected)
        """
        try:
            if not self.controller or not self.controller.is_connected():
                raise RuntimeError("No controller connected")
            # Read each start point variable individually via MG query
            vals = []
            for axis in ["A", "B", "C", "D"]:
                raw = self.controller.cmd(f"MG {STARTPT_BY_AXIS[axis]}").strip()
                vals.append(float(raw))
            self.start_vals = vals
            self._fill_inputs_from_vals(self.start_vals)
        except Exception as e:
            print("start point read failed:", e)
            self._load_from_state()  # Fall back to last saved state values

    def _get_axis_input(self, axis: str):
        """
        Retrieve the editable TextInput widget inside an axis control composite widget.

        The HControl / VControl widgets defined in theme.kv expose an inner TextInput
        as ids.ctrl_input. This helper navigates that two-level id lookup.

        Parameters
        ----------
        axis : str — axis key matching an id prefix in the KV ('a', 'b_left', 'b_right', 'c')
                     Note: axis names are lowercased and used as id prefix, e.g. 'A' -> 'a_ctrl'

        Returns None if the widget or its ctrl_input sub-widget is not found.

        To add a new axis: ensure the KV has an id of the form '<axis_lower>_ctrl'
        that contains an inner id 'ctrl_input'.
        """
        try:
            ctrl = self.ids.get(f"{axis.lower()}_ctrl")
            if not ctrl:
                return None
            return ctrl.ids.get("ctrl_input")
        except Exception:
            return None

    def _get_axis_display(self, axis: str):
        """
        Retrieve the read-only display TextInput for an axis.

        The display box shows the value currently in the controller (set from
        the last individual variable read). It is not directly editable by the operator.

        Parameters
        ----------
        axis : str — axis key (e.g. 'A', 'B_left', 'B_right', 'C')

        Returns None if the widget is not found.
        """
        try:
            return self.ids.get(f"{axis.lower()}_display")
        except Exception:
            return None

    def _fill_inputs_from_vals(self, vals):
        """
        Populate both the editable ctrl_input and the read-only display TextInput
        for each axis from a list of values.

        Axis-to-index mapping (matches startPtA/B/C/D order):
          A       -> vals[0]  (startPtA)
          B_left  -> vals[1]  (startPtB)
          B_right -> vals[2]  (startPtC)
          C       -> vals[3]  (startPtD)

        If a widget is not found (e.g. screen not fully built yet), that axis is
        silently skipped. Handles lists shorter than 4 elements safely via index check.

        Parameters
        ----------
        vals : list[float] — 4-element list [A, B_left, B_right, C] in counts
        """
        mapping = [
            ("A",       0),
            ("B_left",  1),
            ("B_right", 2),
            ("C",       3),
        ]
        for axis, idx in mapping:
            ti      = self._get_axis_input(axis)
            display = self._get_axis_display(axis)
            if ti is not None and idx < len(vals):
                ti.text = str(vals[idx])
            if display is not None and idx < len(vals):
                display.text = str(vals[idx])

    def save_values(self) -> None:
        """
        Read values from the UI inputs, save them to the controller, then move motors.

        Steps:
          1. Read each axis TextInput (via _get_axis_input) and parse as float.
             Non-numeric input is highlighted red and defaults to 0.0.
          2. Update self.start_vals with the new values.
          3. Update state.taught_points["Start"] for cross-screen access.
          4. Write individual variables to controller: startPtA=v;startPtB=v;startPtC=v;startPtD=v
          5. Send BV to save variables to flash.
          6. Send PA (Position Absolute) command with all 4 axis values.
          7. Send BG (Begin) to start the move.

        CAUTION: Sending BG immediately moves the motors. Ensure all limits and
        safety interlocks are active before pressing 'Luu Diem Start'.

        To change the motor move behavior (e.g. speed, synchronization), modify the
        dmcCommand calls at the bottom of this method.
        """
        def get_axis_num(axis: str) -> float:
            """Parse a float from the axis TextInput. Returns 0.0 on parse failure."""
            ti = self._get_axis_input(axis)
            s = ti.text.strip() if ti and ti.text is not None else "0"
            try:
                return float(s)
            except ValueError:
                # Highlight the field red to signal invalid input to the operator
                if ti:
                    ti.background_color = (1, 0.6, 0.6, 1)
                return 0.0

        # Collect values in order: A, B_left, B_right, C
        new_vals = [
            get_axis_num("A"),
            get_axis_num("B_left"),
            get_axis_num("B_right"),
            get_axis_num("C"),
        ]

        # 1) Store locally on this screen
        self.start_vals = new_vals

        # 2) Sync to app-wide state so other screens can read it
        self.state.taught_points["Start"] = {
            "pos": {"A": new_vals[0], "B_left": new_vals[1], "B_right": new_vals[2], "C": new_vals[3]}
        }
        self.state.notify()

        # 3) Push to controller via individual variable assignments (semicolon-joined)
        #    Mapping: A->startPtA, B_left->startPtB, B_right->startPtC, C->startPtD
        try:
            if not self.controller or not self.controller.is_connected():
                raise RuntimeError("No controller connected")
            axes = ["A", "B", "C", "D"]
            parts = [f"{STARTPT_BY_AXIS[axes[i]]}={self.start_vals[i]}" for i in range(len(axes))]
            self.controller.cmd(";".join(parts))
            self.controller.cmd("BV")  # Save variables to flash
        except Exception as e:
            print("start point send to controller failed:", e)
            return  # Abort move if write failed

        # 4) Move all axes to the new start position
        # PA format: "PA A, B_left, B_right, C" — all 4 axes in one command
        self.dmcCommand("PA " + str(new_vals[0]) + ", " + str(new_vals[1]) + ", " + str(new_vals[2]) + ", " + str(new_vals[3]))
        self.dmcCommand("BG")  # Begin motion on all previously specified axes

    def adjust_axis(self, axis: str, delta: float) -> None:
        """
        Nudge an axis value by delta counts and update the ctrl_input TextInput.

        Called by the arrow buttons in the KV (left/right or up/down) via:
            on_release: root.adjust_axis('A', -(step_value))
            on_release: root.adjust_axis('A',  (step_value))

        The delta is determined by the step toggle buttons (X1=1, X10=10, X100=100).
        Result is cast to int to keep counts as whole numbers.

        Parameters
        ----------
        axis  : str   — axis key ('A', 'B_left', 'B_right', 'C')
        delta : float — signed amount to add to the current value (can be negative)

        Note: This only updates the UI field. The operator must press 'Luu Diem Start'
        to write to the controller and move the motor.
        """
        w = self._get_axis_input(axis)
        if not w:
            return
        try:
            cur = float(w.text or "0")
        except Exception:
            cur = 0.0
        new_val = int(cur + delta)
        w.text = str(new_val)

    def dmcCommand(self, command: str) -> None:
        """
        Send a raw DMC command string to the controller in a background thread.

        All controller communication is non-blocking — the command is submitted to
        the thread pool and the UI remains responsive. Errors are printed to console
        and shown in the app banner via _alert().

        Parameters
        ----------
        command : str — raw DMC command (e.g. 'PA 1000, 2000, 2000, 500', 'BG', 'ST')

        Example DMC commands used by this screen:
          'PA A, B, C, D'  — Position Absolute (move to absolute counts)
          'BG'             — Begin motion on all pending axes
        """
        if not self.controller or not self.controller.is_connected():
            self._alert("No controller connected")
            return

        def do_command():
            try:
                self.controller.cmd(command)
                print(f"[DMC] Command sent: {command}")
            except Exception as e:
                print(f"[DMC] Command failed: {command} -> {e}")
                Clock.schedule_once(lambda *_: self._alert(f"Command failed: {e}"))

        jobs.submit(do_command)

    def _alert(self, message: str) -> None:
        """
        Push a message to the app-wide banner ticker via DMCApp._log_message().

        Falls back to state.log() if the app object is unavailable (e.g. during tests).

        Parameters
        ----------
        message : str — text to display in the banner
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

    def loadArrayToPage(self, *args):
        """
        Manually re-read start point variables from the controller and refresh the UI.

        Bound to the 'Lay Diem Start Ve Man Hinh' button in the KV:
            on_release: root.loadArrayToPage()

        Use this if the operator suspects the on-screen values are out of sync with
        the controller (e.g. after a power cycle or external edit of the variables).

        Does nothing (with a print) if the controller is disconnected or read fails.
        """
        try:
            # Read each start point variable individually via MG query
            vals = []
            for axis in ["A", "B", "C", "D"]:
                raw = self.controller.cmd(f"MG {STARTPT_BY_AXIS[axis]}").strip()
                vals.append(float(raw))
        except Exception as e:
            print("start point read failed:", e)
            return
        self.start_vals = vals
        self._fill_inputs_from_vals(self.start_vals)

    def _load_from_state(self) -> None:
        """
        Fall-back loader: populate axis TextInputs from MachineState.taught_points["Start"].

        Called when the controller is not connected or the read fails in on_pre_enter().
        Only fills the editable ctrl_input — NOT the read-only display — since there is
        no fresh controller data to show.

        Data structure expected in state:
            state.taught_points["Start"]["pos"] = {
                "A": float, "B_left": float, "B_right": float, "C": float
            }

        If the key does not exist, all inputs default to "0.0".
        """
        data = (self.state.taught_points.get("Start") or {}).get("pos", {}) if self.state else {}
        a       = str(data.get("A",       0.0))
        b_left  = str(data.get("B_left",  0.0))
        b_right = str(data.get("B_right", 0.0))
        c       = str(data.get("C",       0.0))
        if (ti := self._get_axis_input("A")):       ti.text = a
        if (ti := self._get_axis_input("B_left")):  ti.text = b_left
        if (ti := self._get_axis_input("B_right")): ti.text = b_right
        if (ti := self._get_axis_input("C")):       ti.text = c
