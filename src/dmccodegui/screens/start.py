from __future__ import annotations

from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

from ..app_state import MachineState
from ..controller import GalilController
from ..utils import jobs

class StartScreen(Screen):
    controller: GalilController = ObjectProperty(None)  # type: ignore
    state: MachineState = ObjectProperty(None)  # type: ignore
    start_vals = ([0.0, 0.0, 0.0, 0.0])

    def on_pre_enter(self, *args):  # noqa: ANN001
        #"""Called right before the screen is shown."""
        try:
            vals = self.controller.upload_array("StartPnt", 0, 3)
        except Exception as e:
            print("StartPnt read failed:", e)
            return
        self.start_vals = (vals + [0,0,0,0])[:4]
        self._fill_inputs_from_vals(self.start_vals)
        
    def _fill_inputs_from_vals(self, vals):
        ids = self.ids
        mapping = [
            ("a_inp", 0),
            ("b_inp", 1),
            ("c_inp", 2),
            ("d_inp", 3),
        ]
        for wid, idx in mapping:
            ti = ids.get(wid)
            if ti is not None and idx < len(vals):
                ti.text = str(vals[idx])

    # saves values from UI and pushes them to controller
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
        self.start_vals = new_vals

        # 2) (Optional) keep your app-wide state in sync
        self.state.taught_points["Start"] = {
            "pos": {"A": new_vals[0], "B": new_vals[1], "C": new_vals[2], "D": new_vals[3]}
        }
        self.state.notify()
        try:
            if not self.controller or not self.controller.is_connected():
                raise RuntimeError("No controller connected")
            self.controller.download_array("StartPnt", 0, self.start_vals)
        except Exception as e:
            print("StartPnt send to controller failed:", e)
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
            
    def loadArrayToPage(self, *args):
        try:
            vals = self.controller.upload_array("StartPnt", 0, 3)
        except Exception as e:
            print("StartPnt read failed:", e)
            return
        self.start_vals = (vals + [0,0,0,0])[:4]
        self._fill_inputs_from_vals(self.start_vals)
        
    def _fill_inputs_from_vals(self, vals):
        ids = self.ids
        mapping = [
            ("a_inp", 0),
            ("b_inp", 1),
            ("c_inp", 2),
            ("d_inp", 3),
        ]
        for wid, idx in mapping:
            ti = ids.get(wid)
            if ti is not None and idx < len(vals):
                ti.text = str(vals[idx])       

