from __future__ import annotations

from typing import Dict

from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

from ..app_state import MachineState
from ..controller import GalilController
from ..utils import jobs
from ..utils.fmt import try_float


class StartScreen(Screen):
    controller: GalilController = ObjectProperty(None)  # type: ignore
    state: MachineState = ObjectProperty(None)  # type: ignore

    def on_pre_enter(self, *args):  # noqa: ANN001
        self._load_from_state()

    def _load_from_state(self) -> None:
        data = (self.state.taught_points.get("Start") or {}).get("pos", {}) if self.state else {}
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
        vals: Dict[str, float] = {
            "A": try_float(ids.get("a_inp").text if ids.get("a_inp") else "0"),
            "B": try_float(ids.get("b_inp").text if ids.get("b_inp") else "0"),
            "C": try_float(ids.get("c_inp").text if ids.get("c_inp") else "0"),
            "D": try_float(ids.get("d_inp").text if ids.get("d_inp") else "0"),
        }
        self.state.taught_points["Start"] = {"pos": vals}
        self.state.notify()

    def teach_from_current(self) -> None:
        if not self.controller or not self.controller.is_connected():
            Clock.schedule_once(lambda *_: self._alert("No controller connected"))
            return
        def do_teach() -> None:
            try:
                st = self.controller.read_status()
                pos = st.get("pos", {})
                def on_ui() -> None:
                    self.state.taught_points["Start"] = {"pos": pos}
                    self.state.notify()
                    self._load_from_state()
                Clock.schedule_once(lambda *_: on_ui())
            except Exception as e:
                msg = f"Teach Start error: {e}"
                Clock.schedule_once(lambda *_: self._alert(msg))
        jobs.submit(do_teach)

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

