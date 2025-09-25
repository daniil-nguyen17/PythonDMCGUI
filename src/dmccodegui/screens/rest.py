from __future__ import annotations

from typing import Dict

from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

from ..app_state import MachineState
from ..controller import GalilController
from ..utils import jobs

class RestScreen(Screen):
    controller: GalilController = ObjectProperty(None)  # type: ignore
    state: MachineState = ObjectProperty(None)  # type: ignore
    rest_vals = ([0.0, 0.0, 0.0, 0.0])

    def on_pre_enter(self, *args):  # noqa: ANN001
        try:
            if not self.controller or not self.controller.is_connected():
                raise RuntimeError("No controller connected")
            vals = self.controller.upload_array("RestPnt", 0, 3)
            self.rest_vals = (vals + [0,0,0,0])[:4]
            self._fill_inputs_from_vals(self.rest_vals)
        except Exception as e:
            print("RestPnt read failed:", e)
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
        d = str(data.get("D", 0.0))
        if (ti := self._get_axis_input("A")): ti.text = a
        if (ti := self._get_axis_input("B")): ti.text = b
        if (ti := self._get_axis_input("C")): ti.text = c
        if (ti := self._get_axis_input("D")): ti.text = d

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

        # A, B, C, D in order → local array
        new_vals = [
            get_axis_num("A"),
            get_axis_num("B"),
            get_axis_num("C"),
            get_axis_num("D"),
        ]

        # 1) Save to your local array on the screen
        self.rest_vals = new_vals

        # 2) (Optional) keep your app-wide state in sync
        self.state.taught_points["Rest"] = {
            "pos": {"A": new_vals[0], "B": new_vals[1], "C": new_vals[2], "D": new_vals[3]}
        }
        self.state.notify()
        try:
            if not self.controller or not self.controller.is_connected():
                raise RuntimeError("No controller connected")
            # Push the Rest values we just collected
            self.controller.download_array("RestPnt", 0, self.rest_vals)
        except Exception as e:
            print("RestPnt send to controller failed:", e)
            return

    def loadArrayToPage(self, *args):
        try:
            # Read Rest array from controller, not Start
            vals = self.controller.upload_array("RestPnt", 0, 3)
        except Exception as e:
            print("RestPnt read failed:", e)
            return
        self.rest_vals = (vals + [0,0,0,0])[:4]
        self._fill_inputs_from_vals(self.rest_vals)

    def _fill_inputs_from_vals(self, vals):
        mapping = [
            ("A", 0),
            ("B", 1),
            ("C", 2),
            ("D", 3),
        ]
        for axis, idx in mapping:
            ti = self._get_axis_input(axis)
            if ti is not None and idx < len(vals):
                ti.text = str(vals[idx])

    # This lets us adjust the array values for array
    def adjust_axis(self, axis: str, delta: float) -> None:
        w = self._get_axis_input(axis)
        if not w:
            return
        try:
            cur = float(w.text or "0")
        except Exception:
            cur = 0.0
        w.text = str(int(cur + delta))

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

