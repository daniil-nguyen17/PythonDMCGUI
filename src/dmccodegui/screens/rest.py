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

    def on_pre_enter(self, *args):  # noqa: ANN001
        self._load_from_state()

    def _load_from_state(self) -> None:
        data = (self.state.taught_points.get("Rest") or {}).get("pos", {}) if self.state else {}
        a = str(data.get("A", 0.0))
        b = str(data.get("B", 0.0))
        c = str(data.get("C", 0.0))
        d = str(data.get("D", 0.0))
        ids = self.ids
        if ids.get("a_inp"): ids["a_inp"].text = a
        if ids.get("b_inp"): ids["b_inp"].text = b
        if ids.get("c_inp"): ids["c_inp"].text = c
        if ids.get("d_inp"): ids["d_inp"].text = d

    def save_values(self) -> None:
        ids = self.ids

        def get_num(wid: str) -> float:
            ti = ids.get(wid)
            s = ti.text.strip() if ti and ti.text is not None else "0"
            try:
                return float(s)
            except ValueError:
                # optional: visually flag bad input
                if ti: ti.background_color = (1, 0.6, 0.6, 1)
                return 0.0

        # A, B, C, D in order → local array
        new_vals = [
            get_num("a_inp"),
            get_num("b_inp"),
            get_num("c_inp"),
            get_num("d_inp"),
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
            self.controller.download_array("RestPnt", 0, self.start_vals)
        except Exception as e:
            print("RestPnt send to controller failed:", e)
            return

    def loadArrayToPage(self, *args):
        try:
            vals = self.controller.upload_array("StartPnt", 0, 3)
        except Exception as e:
            print("StartPnt read failed:", e)
            return
        self.start_vals = (vals + [0,0,0,0])[:4]
        self._fill_inputs_from_vals(self.start_vals)

        try:
            if not self.controller or not self.controller.is_connected():
                raise RuntimeError("No controller connected")
            self.controller.download_array("RestPnt", 0, new_vals)
        except Exception as e:
            print("RestPnt send to controller failed:", e)
            return

    # This lets us adjust the array values for array
    def adjust_axis(self, axis: str, delta: float) -> None:
        ids = self.ids
        key = f"{axis.lower()}_inp"
        w = ids.get(key)
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

