from __future__ import annotations

"""
axisDSetup.py — AxisDSetupScreen

This screen is dedicated to setting up the D axis (knife angle) positions.
It manages three angle positions stored as individual restPt variables in the DMC program:
  - D Zero:   home/reference angle for the D axis  (restPtA)
  - D Angle1: first working angle position          (restPtB)
  - D Angle2: second working angle position         (restPtC)

DMC VARIABLES: restPtA, restPtB, restPtC (individual named variables)
  restPtA = D Zero position   (counts)
  restPtB = D Angle1 position (counts)
  restPtC = D Angle2 position (counts)

  Variable names imported from dmccodegui.hmi.dmc_vars (RESTPT_BY_AXIS).
  Previously used the RestPnt DMC array (indices 0-2) — migrated to individual variables in plan 09-03.

NOTE: This screen shares the restPtA/B/C variables with rest.py (A/B/C rest points).
If the two screens need to be independent in the future, allocate separate D-axis variables
in the DMC program and update both this file and axisDSetup.kv.

KV FILE: ui/axisDSetup.kv
  Each angle position has two widgets:
    ids.<axis>_ctrl    — VControl or HControl composite widget
                          └── ids.ctrl_input  — the editable TextInput inside the control
    ids.<axis>_display — read-only TextInput showing the value from the controller

WORKFLOW:
  1. On screen enter: reads restPtA/B/C from controller via individual MG queries
     and fills UI for A, B, C slots (which here represent D Zero, D Angle1, D Angle2).
  2. Operator uses arrow buttons (via adjust_axis) to nudge values.
  3. 'Save' button calls save_values(), which writes back to individual restPt variables.
     Note: Unlike start.py and rest.py, save_values() here does NOT send a PA/BG
     move command — it only saves the variable values.

THREADING MODEL:
  controller I/O in on_pre_enter is synchronous on the main thread (brief read).
  dmcCommand() and adjust_axis (which sends 'pa=' immediately) use jobs.submit().
"""

from typing import Dict

from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

from ..app_state import MachineState
from ..controller import GalilController
from ..utils import jobs
from dmccodegui.hmi.dmc_vars import RESTPT_A, RESTPT_B, RESTPT_C, RESTPT_BY_AXIS


class AxisDSetupScreen(Screen):
    # Injected by main.py after the ScreenManager is built
    controller: GalilController = ObjectProperty(None)  # type: ignore
    state: MachineState = ObjectProperty(None)          # type: ignore

    # Local copy of the D-axis angle positions (3 floats: Zero, Angle1, Angle2)
    # Maps to restPtA, restPtB, restPtC on the controller.
    rest_vals = ([0.0, 0.0, 0.0])

    def on_pre_enter(self, *args):
        """
        Called by Kivy each time the operator navigates to this screen.

        Reads restPtA, restPtB, restPtC from the controller via individual MG queries
        and fills both the editable inputs and read-only display boxes for the three D-axis angles.

        Falls back to self._load_from_state() if:
          - No controller is connected
          - The controller read throws an exception

        Note: The axis IDs in the KV are 'A', 'B', 'C' (as inherited from the shared
        KV/control pattern), but they logically represent D-axis Zero, Angle1, Angle2.
        """
        try:
            if not self.controller or not self.controller.is_connected():
                raise RuntimeError("No controller connected")
            # Read each rest point variable individually via MG query
            vals = []
            for axis in ["A", "B", "C"]:
                raw = self.controller.cmd(f"MG {RESTPT_BY_AXIS[axis]}").strip()
                vals.append(float(raw))
            self.rest_vals = vals
            self._fill_inputs_from_vals(self.rest_vals)
        except Exception as e:
            print("AxisDSetup read failed:", e)
            self._load_from_state()  # Fall back to last saved state values

    def _get_axis_input(self, axis: str):
        """
        Retrieve the editable TextInput widget inside an axis control composite widget.

        The VControl / HControl widgets defined in theme.kv expose an inner TextInput
        as ids.ctrl_input. This helper navigates that two-level id lookup.

        Parameters
        ----------
        axis : str — axis key matching an id prefix in the KV ('a', 'b', 'c')
                     Maps to D-axis positions: A=DZero, B=DAngle1, C=DAngle2

        Returns None if the widget or its ctrl_input sub-widget is not found.
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
        Retrieve the read-only display TextInput for a D-axis angle position.

        The display box shows the value from the last controller read.
        It is not directly editable by the operator.

        Parameters
        ----------
        axis : str — axis key ('A', 'B', 'C') representing D Zero, D Angle1, D Angle2

        Returns None if the widget is not found.
        """
        try:
            return self.ids.get(f"{axis.lower()}_display")
        except Exception:
            return None

    def _load_from_state(self) -> None:
        """
        Fall-back loader: populate axis TextInputs from MachineState.taught_points["Rest"].

        Called when the controller is not connected or the read fails in on_pre_enter().
        Only fills the editable ctrl_input — NOT the read-only display.

        Data structure expected in state:
            state.taught_points["Rest"]["pos"] = {
                "A": float, "B": float, "C": float
            }

        A/B/C here correspond to the KV widget IDs (D Zero/Angle1/Angle2).
        If the key does not exist, all inputs default to "0.0".
        """
        data = (self.state.taught_points.get("Rest") or {}).get("pos", {}) if self.state else {}
        a = str(data.get("A", 0.0))
        b = str(data.get("B", 0.0))
        c = str(data.get("C", 0.0))
        if (ti := self._get_axis_input("A")): ti.text = a
        if (ti := self._get_axis_input("B")): ti.text = b
        if (ti := self._get_axis_input("C")): ti.text = c

    def save_values(self) -> None:
        """
        Read the three D-axis angle values from the UI inputs and write them to
        the controller's individual restPt variables. Does NOT issue a motor move command.

        Steps:
          1. Read each TextInput and parse as float. Invalid input = red highlight + 0.0.
          2. Update self.rest_vals and state.taught_points["Rest"].
          3. Write to controller via semicolon-joined assignment: restPtA=v;restPtB=v;restPtC=v
          4. Send BV to save variables to flash.

        Unlike start.py and rest.py, no PA/BG move is sent after saving. The operator
        must issue motion commands separately (e.g. via buttons_switches.py or the
        DMC terminal) to move the D axis to a saved angle.

        To add a move after save: append dmcCommand("PA ...") and dmcCommand("BG") below
        the variable write, following the pattern in rest.py.
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

        new_vals = [
            get_axis_num("A"),  # D Zero position
            get_axis_num("B"),  # D Angle1 position
            get_axis_num("C"),  # D Angle2 position
        ]

        # Store locally on this screen
        self.rest_vals = new_vals

        # Sync to app-wide state
        self.state.taught_points["Rest"] = {
            "pos": {"A": new_vals[0], "B": new_vals[1], "C": new_vals[2]}
        }
        self.state.notify()

        # Push to controller via individual variable assignments (no motor move — see docstring above)
        try:
            if not self.controller or not self.controller.is_connected():
                raise RuntimeError("No controller connected")
            axes = ["A", "B", "C"]
            parts = [f"{RESTPT_BY_AXIS[axes[i]]}={self.rest_vals[i]}" for i in range(len(axes))]
            self.controller.cmd(";".join(parts))
            self.controller.cmd("BV")  # Save variables to flash
        except Exception as e:
            print("AxisDSetup send to controller failed:", e)
            return

    def loadArrayToPage(self, *args):
        """
        Manually re-read rest point variables from the controller and refresh the UI.

        Bound to the load button in the KV (if present):
            on_release: root.loadArrayToPage()

        Use this if the on-screen values appear out of sync with the controller.
        Does nothing (with a print) if the read fails.
        """
        try:
            # Read each rest point variable individually via MG query
            vals = []
            for axis in ["A", "B", "C"]:
                raw = self.controller.cmd(f"MG {RESTPT_BY_AXIS[axis]}").strip()
                vals.append(float(raw))
        except Exception as e:
            print("AxisDSetup read failed:", e)
            return
        self.rest_vals = vals
        self._fill_inputs_from_vals(self.rest_vals)

    def _fill_inputs_from_vals(self, vals):
        """
        Populate both the editable ctrl_input and the read-only display TextInput
        for each angle position from a list of values.

        Axis-to-index mapping:
          A (D Zero)   -> vals[0]
          B (D Angle1) -> vals[1]
          C (D Angle2) -> vals[2]

        Parameters
        ----------
        vals : list[float] — 3-element list [DZero, DAngle1, DAngle2] in counts
        """
        mapping = [
            ("A", 0),  # D Zero
            ("B", 1),  # D Angle1
            ("C", 2),  # D Angle2
        ]
        for axis, idx in mapping:
            ti      = self._get_axis_input(axis)
            display = self._get_axis_display(axis)
            if ti is not None and idx < len(vals):
                ti.text = str(vals[idx])
            if display is not None and idx < len(vals):
                display.text = str(vals[idx])

    def adjust_axis(self, axis: str, delta: float) -> None:
        """
        Nudge a D-axis angle value by delta counts, update the UI, and immediately
        send a position command to the controller.

        Unlike start.py and rest.py, this method sends a 'pa=' command immediately
        on each button press (not waiting for a 'Save' button). This allows
        the operator to jog the D axis in real time for fine angle adjustment.

        Parameters
        ----------
        axis  : str   — axis key ('A', 'B', 'C') for D Zero/Angle1/Angle2
        delta : float — signed amount to add to the current value (positive = increase)

        DMC command sent: 'pa=<new_value>'
          This sets the position absolute target for the currently addressed axis.
          Note: 'pa=' without specifying axis letter addresses the currently selected axis.
          To address a specific axis, the command should include the axis letter (e.g. 'PAD=value').
          Review the DMC program to ensure axis addressing is correct.
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
        # Send position command immediately (live jog behavior)
        self.dmcCommand("pa=" + str(new_val))

    def dmcCommand(self, command: str) -> None:
        """
        Send a raw DMC command string to the controller in a background thread.

        All controller communication is non-blocking. Errors are printed to console
        and shown in the app banner via _alert().

        Parameters
        ----------
        command : str — raw DMC command (e.g. 'pa=1500', 'BG', 'ST')

        Example DMC commands used by this screen:
          'pa=<n>'  — Set position absolute target (used during live jog)
          'BG'      — Begin motion (if needed after pa=)
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
