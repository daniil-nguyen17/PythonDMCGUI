from __future__ import annotations

from typing import Dict

from kivy.properties import ObjectProperty, StringProperty, NumericProperty
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

from ..app_state import MachineState
from ..controller import GalilController
from ..utils import jobs


class ArraysScreen(Screen):
    controller: GalilController = ObjectProperty(None)  # type: ignore
    state: MachineState = ObjectProperty(None)  # type: ignore
    array_name: str = StringProperty("arr")
    array_len: int = NumericProperty(150)
    _built: bool = False
    _value_labels: list = []
    _value_inputs: list = []

    def on_kv_post(self, *_):
        if self._built:
            return
        self._built = True
        left = self.ids.get("left_grid")
        right = self.ids.get("right_grid")
        if not left or not right:
            return
        self._value_labels = []
        self._value_inputs = []
        for i in range(int(self.array_len)):
            # left side
            from kivy.uix.label import Label  # local import to avoid global dependency at import time
            from kivy.uix.textinput import TextInput
            idx = Label(text=f"{i:03d}", size_hint_y=None, height='28dp', halign='right', valign='middle')
            idx.bind(size=lambda w, *_: setattr(w, 'text_size', w.size))
            eq = Label(text='=', size_hint_y=None, height='28dp')
            val = Label(text='', size_hint_y=None, height='28dp')
            left.add_widget(idx)
            left.add_widget(eq)
            left.add_widget(val)
            self._value_labels.append(val)

            # right side
            idx2 = Label(text=f"{i:03d}", size_hint_y=None, height='28dp', halign='right', valign='middle')
            idx2.bind(size=lambda w, *_: setattr(w, 'text_size', w.size))
            ti = TextInput(text='', multiline=False, input_filter='float', size_hint_y=None, height='28dp')
            right.add_widget(idx2)
            right.add_widget(ti)
            self._value_inputs.append(ti)

    def load_from_controller(self) -> None:
        name = self.array_name
        n = int(self.array_len)

        if not self.controller or not self.controller.is_connected():
            Clock.schedule_once(lambda *_: self._alert("No controller connected"))
            return

        def do_read() -> None:
            try:
                # Ensure controller is ready (arrays declared and numeric)
                self.controller.wait_for_ready()
                # Discover actual length up to configured max
                length = self.controller.discover_length(name, probe_max=n)
                if length <= 0:
                    vals = []
                else:
                    vals = self.controller.read_array_slice(name, 0, length)
                def on_ui() -> None:
                    self.state.arrays[name] = vals
                    # update labels (clear beyond length)
                    for i, lbl in enumerate(self._value_labels):
                        lbl.text = f"{vals[i]}" if i < len(vals) else ""
                    self.state.notify()
                Clock.schedule_once(lambda *_: on_ui())
            except Exception as e:
                msg = f"Array read error: {e}"
                Clock.schedule_once(lambda *_: self._alert(msg))

        jobs.submit(do_read)

    def copy_current_to_inputs(self) -> None:
        for i, lbl in enumerate(self._value_labels):
            if i < len(self._value_inputs):
                self._value_inputs[i].text = lbl.text

    def write_to_controller(self, updates: Dict[int, float]) -> None:
        name = self.array_name

        if not self.controller or not self.controller.is_connected():
            Clock.schedule_once(lambda *_: self._alert("No controller connected"))
            return

        def do_write() -> None:
            try:
                self.controller.write_array(name, updates)
                # after write, re-read to confirm
                vals = self.controller.read_array(name, int(self.array_len))
                def on_ui() -> None:
                    self.state.arrays[name] = vals
                    # update labels
                    for i, v in enumerate(vals):
                        if i < len(self._value_labels):
                            self._value_labels[i].text = f"{v}"
                    self.state.notify()
                Clock.schedule_once(lambda *_: on_ui())
            except Exception as e:
                msg = f"Array write error: {e}"
                Clock.schedule_once(lambda *_: self._alert(msg))

        jobs.submit(do_write)

    def write_inputs_to_controller(self) -> None:
        updates: Dict[int, float] = {}
        for i, ti in enumerate(self._value_inputs):
            s = ti.text.strip()
            if not s:
                continue
            try:
                v = float(s)
                updates[i] = v
                ti.background_color = (1, 1, 1, 1)
            except Exception:
                ti.background_color = (1, 0.6, 0.6, 1)
        if updates:
            self.write_to_controller(updates)

    def _alert(self, message: str) -> None:
        try:
            from kivy.app import App
            app = App.get_running_app()
            if app and hasattr(app, "_log_message"):
                getattr(app, "_log_message")(message)
                return
        except Exception:
            pass
        # fallback
        if self.state:
            self.state.log(message)

