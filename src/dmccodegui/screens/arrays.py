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
    array_name = StringProperty("arr")
    array_len = NumericProperty(250)
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

    def on_pre_enter(self, *args):  # noqa: ANN001
        try:
            if not self.controller or not self.controller.is_connected():
                raise RuntimeError("No controller connected")

            vals = []
            for i in range(int(self.array_len)):
                try:
                    resp = self.controller.cmd(f"MG {self.array_name}[{i}]").strip()
                    if resp == "?":
                        # Element doesn't exist, stop reading here
                        print(f"Array {self.array_name} has {i} elements (stopped at uninitialized element)")
                        break
                    vals.append(float(resp))
                except Exception:
                    # Error reading this element, stop here
                    print(f"Array {self.array_name} has {i} elements (stopped at error)")
                    break

            print(f"Successfully read {len(vals)} elements from {self.array_name}")

            for i, val in enumerate(vals):
                if i < len(self._value_labels):
                    self._value_labels[i].text = str(val)

            for i in range(len(vals), len(self._value_labels)):
                self._value_labels[i].text = ""

        except Exception as e:
            print(f"{self.array_name} read failed:", e)
            # Fall back to app state like start/rest screens do
            self._load_from_state()
    

    def _load_from_state(self) -> None:
        """Load array values from app state when controller read fails."""
        if not self.state:
            return
            
        # Get values from state
        vals = self.state.arrays.get(self.array_name, [])
        
        # Update labels with state values (or empty if no state)
        for i, lbl in enumerate(self._value_labels):
            if i < len(vals):
                lbl.text = str(vals[i])
            else:
                lbl.text = "" 
        
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
                
                # First, test if the array exists by trying to read the first element
                try:
                    test_val = self.controller.read_array_elem(name, 0)
                    print(f"[CTRL] Array {name} exists, first element: {test_val}")
                except Exception as e:
                    if "Bad function or array" in str(e) or "57" in str(e):
                        msg = f"Array '{name}' is not declared on the controller. Please ensure the controller program declares this array first."
                        Clock.schedule_once(lambda *_: self._alert(msg))
                        return
                    else:
                        raise e
                
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

    def write_inputs_to_controller(self) -> None:
        #"""Collect numbers from right-hand TextInputs and push to controller."""
        if not self.controller or not self.controller.is_connected():
            Clock.schedule_once(lambda *_: self._alert("No controller connected"))
            return
        updates: Dict[int, float] = {}
        # Gather numeric edits (skip blanks, mark invalids)
        for i, ti in enumerate(self._value_inputs):
            s = (ti.text or "").strip()
            if not s:
                continue
            try:
                v = float(s)
                updates[i] = v
                ti.background_color = (1, 1, 1, 1)
            except Exception:
                ti.background_color = (1, 0.6, 0.6, 1)

        if not updates:
            Clock.schedule_once(lambda *_: self._alert("No edits to write"))
            return

        self._write_updates(updates)

    def _write_updates(self, updates: Dict[int, float]) -> None:
        #"""Write sparse updates efficiently in contiguous runs, then refresh UI."""
        name = self.array_name
        n = int(self.array_len)

        def do_write() -> None:
            wrote = 0
            try:
                # batch contiguous indices: [10]=..,[11]=..,[12]=.. → one call
                run_start = None
                run_vals: list[float] = []
                for idx in sorted(updates.keys()):
                    val = updates[idx]
                    if run_start is None:
                        run_start = idx
                        run_vals = [val]
                    elif idx == run_start + len(run_vals):
                        run_vals.append(val)
                    else:
                        wrote += self.controller.download_array(name, run_start, run_vals)
                        run_start, run_vals = idx, [val]
                if run_start is not None and run_vals:
                    wrote += self.controller.download_array(name, run_start, run_vals)

                # re-read to reflect new values (only read what we actually wrote)
                max_written = max(updates.keys()) if updates else 0
                vals = self.controller.upload_array(name, 0, min(max_written, n - 1))

                def on_ui() -> None:
                    # paint left labels
                    for i, v in enumerate(vals[:len(self._value_labels)]):
                        self._value_labels[i].text = str(v)
                    for j in range(len(vals), len(self._value_labels)):
                        self._value_labels[j].text = ""
                    # also mirror into state if you track arrays there
                    if self.state:
                        self.state.arrays[name] = vals
                        self.state.notify()
                    self._alert(f"Wrote {wrote} value(s) to {name}")
                Clock.schedule_once(lambda *_: on_ui())

            except Exception as ex:
                msg = f"Array write error: {ex}"
                Clock.schedule_once(lambda *_: self._alert(msg))

        from ..utils import jobs
        jobs.submit(do_write)
    
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

