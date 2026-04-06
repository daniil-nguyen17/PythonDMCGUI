from __future__ import annotations
from kivy.uix.screenmanager import Screen
from typing import Dict

from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

from ..app_state import MachineState
from ..controller import GalilController
from ..utils import jobs
from dmccodegui.hmi.dmc_vars import RESTPT_BY_AXIS

class ParametersSetupScreen(Screen):
    controller: GalilController = ObjectProperty(None)  # type: ignore
    state: MachineState = ObjectProperty(None)  # type: ignore

    def on_pre_enter(self, *args):  # noqa: ANN001
        try:
            if not self.controller or not self.controller.is_connected():
                raise RuntimeError("No controller connected")
            # Read each rest point variable individually via MG query (A, B, C only)
            vals = []
            for axis in ["A", "B", "C"]:
                raw = self.controller.cmd(f"MG {RESTPT_BY_AXIS[axis]}").strip()
                vals.append(float(raw))
            self.rest_vals = vals
            self._fill_inputs_from_vals(self.rest_vals)
        except Exception as e:
            print("rest point read failed:", e)
            self._load_from_state()

    def _get_axis_input(self, axis: str):
        try:
            ctrl = self.ids.get(f"{axis.lower()}_ctrl")
            if not ctrl:
                return None
            return ctrl.ids.get("ctrl_input")
        except Exception:
            return None

    def _load_from_state(self) -> None:
        data = (self.state.taught_points.get("Rest") or {}).get("pos", {}) if self.state else {}
        a = str(data.get("A", 0.0))
        b = str(data.get("B", 0.0))
        c = str(data.get("C", 0.0))
        if (ti := self._get_axis_input("A")): ti.text = a
        if (ti := self._get_axis_input("B")): ti.text = b
        if (ti := self._get_axis_input("C")): ti.text = c

    def save_values(self) -> None:
        def get_axis_num(axis: str) -> float:
            ti = self._get_axis_input(axis)
            s = ti.text.strip() if ti and ti.text is not None else "0"
            try:
                return float(s)
            except ValueError:
                # optional: visually flag bad input
                if ti: ti.background_color = (1, 0.6, 0.6, 1)
                return 0.0

        # A, B, C in order — rest points for 3 axes
        new_vals = [
            get_axis_num("A"),
            get_axis_num("B"),
            get_axis_num("C"),
        ]

        # 1) Save to local array on the screen
        self.rest_vals = new_vals

        # 2) Keep app-wide state in sync
        self.state.taught_points["Rest"] = {
            "pos": {"A": new_vals[0], "B": new_vals[1], "C": new_vals[2]}
        }
        self.state.notify()
        try:
            if not self.controller or not self.controller.is_connected():
                raise RuntimeError("No controller connected")
            # Push the Rest values via individual variable assignments (semicolon-joined)
            axes = ["A", "B", "C"]
            parts = [f"{RESTPT_BY_AXIS[axes[i]]}={self.rest_vals[i]}" for i in range(len(axes))]
            self.controller.cmd(";".join(parts))
            self.controller.cmd("BV")  # Save variables to flash
        except Exception as e:
            print("rest point send to controller failed:", e)
            return
        # Send command to controller to move axis to new position
        self.dmcCommand("PA "+str(new_vals[0])+", " +str(new_vals[1])+", "+str(new_vals[2]))
        self.dmcCommand("BG")

    def loadArrayToPage(self, *args):
        try:
            # Read rest point variables from controller individually (A, B, C only)
            vals = []
            for axis in ["A", "B", "C"]:
                raw = self.controller.cmd(f"MG {RESTPT_BY_AXIS[axis]}").strip()
                vals.append(float(raw))
        except Exception as e:
            print("rest point read failed:", e)
            return
        self.rest_vals = vals
        self._fill_inputs_from_vals(self.rest_vals)

    def _fill_inputs_from_vals(self, vals):
        mapping = [
            ("A", 0),
            ("B", 1),
            ("C", 2),
        ]
        for axis, idx in mapping:
            ti = self._get_axis_input(axis)
            if ti is not None and idx < len(vals):
                ti.text = str(vals[idx])

    def dmcCommand(self, command: str) -> None:
        """Send a command to the DMC controller."""
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
