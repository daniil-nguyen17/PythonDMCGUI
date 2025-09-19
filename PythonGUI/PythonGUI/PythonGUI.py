from os import name
import kivy
import gclib
import sys
import datetime

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.button import Button
from kivy.clock import Clock
from functools import partial
from kivy.uix.textinput import TextInput
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty, NumericProperty


class SettingScreen(Screen):
    pass


class EdgePointScreen(Screen):
    pass


class RestPointScreen(Screen):
    pass


class StartPointScreen(Screen):
    pass


class ParameterScreen(Screen):
    pass


class ArrayScreen(Screen):
    array_name = StringProperty("arr")  # Galil array name
    array_len = NumericProperty(130)  # number of elements

    def on_kv_post(self, *_):
        if getattr(self, "_built_rows", False):
            return
        self._built_rows = True
        self._value_labels = []  # left (controller values)
        self._value_inputs = []  # right (editable inputs)

        left = self.ids.left_grid
        right = self.ids.right_grid

        for i in range(int(self.array_len)):
            # --- LEFT: index, "=", value label
            idx = Label(
                text=f"{i:03d}",
                size_hint_y=None,
                height="28dp",
                halign="right",
                valign="middle",
            )
            idx.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
            eq = Label(text="=", size_hint_y=None, height="28dp")
            val = Label(text="", size_hint_y=None, height="28dp")
            left.add_widget(idx)
            left.add_widget(eq)
            left.add_widget(val)
            self._value_labels.append(val)

            # --- RIGHT: index, TextInput
            idx2 = Label(
                text=f"{i:03d}",
                size_hint_y=None,
                height="28dp",
                halign="right",
                valign="middle",
            )
            idx2.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
            ti = TextInput(
                text="",
                multiline=False,
                input_filter="float",
                size_hint_y=None,
                height="28dp",
            )
            right.add_widget(idx2)
            right.add_widget(ti)
            self._value_inputs.append(ti)

    # ---------- Buttons ----------
    def load_from_controller(self):
        dmc = self._galil()
        if not dmc:
            print("No controller connection (app.root.dmc or app.g not set).")
            return
        vals = self._read_array(dmc)
        if vals is None:
            return
        for i, v in enumerate(vals):
            self._value_labels[i].text = f"{v}"

    def copy_current_to_inputs(self):
        for i, lbl in enumerate(self._value_labels):
            self._value_inputs[i].text = lbl.text

    def write_to_controller(self):
        dmc = self._galil()
        if not dmc:
            print("No controller connection (app.root.dmc or app.g not set).")
            return

        # build assignments for non-empty inputs
        assigns = []
        for i, ti in enumerate(self._value_inputs):
            s = ti.text.strip()
            if not s:
                continue
            try:
                float(s)  # validate numeric
                assigns.append(f"{self.array_name}[{i}]={s}")
                ti.background_color = (1, 1, 1, 1)  # clear error tint
            except ValueError:
                ti.background_color = (1, 0.6, 0.6, 1)  # mark bad input

        # send in safe chunks
        line = ""
        for cmd in assigns:
            if len(line) + len(cmd) + 1 < 300:
                line = (line + ";" + cmd) if line else cmd
            else:
                dmc.GCommand(line)
                line = cmd
        if line:
            dmc.GCommand(line)
        print(f"Wrote {len(assigns)} entries to {self.array_name}.")

    # ---------- Helpers ----------
    def _galil(self):
        """Return a gclib handle from app.root.dmc or app.g."""
        app = App.get_running_app()
        dmc = (
            getattr(app.root, "dmc", None)
            if app and getattr(app, "root", None)
            else None
        )
        return dmc or getattr(app, "g", None)

    def _read_array(self, dmc):
        """Read array in chunks and return a list of floats."""
        name = self.array_name
        n = int(self.array_len)
        out = []
        i = 0
        while i < n:
            count = min(20, n - i)
            refs = ", ".join(f"{name}[{j}]" for j in range(i, i + count))
            resp = dmc.GCommand("MG " + refs).strip()
            parts = resp.replace("\r", " ").replace("\n", " ").split()
            out.extend(float(p) for p in parts)
            i += count
        return out[:n]


class ScreenManager(ScreenManager):
    pass


class DMCControllerSetting(BoxLayout):

    def dmcCommand(self, cmd):
        dmc = getattr(self, "dmc", None)
        if not dmc:
            print("No controller connection yet.")
            return
        try:
            rc = self.dmc.GCommand(cmd)  # Send command into the GCommand gclib API
        except Exception as e:
            print(e)
            tc1 = self.dmc.GCommand("TC1")
            print(tc1)
            self.ids.avTitle.title = "Error: " + tc1  # Update title with error message

    # This function is called at 10Hz.
    # It will call the functions to update the selected screen
    # need to add code to update each screen (6) to have variable values updated
    def _update_clock(self, dt):
        if self.controllerConnected == 1:
            self.updateHomingScreen()
        elif self.controllerConnected == 2:
            self.updateCutScreen()

    def disconnectAndRefresh(self):
        # TODO: close Galil connection(s), refresh UI state
        print("Disconnect requested")
        dmc = getattr(self, "dmc", None)
        if dmc:
            try:
                dmc.GClose()
            except Exception:
                pass
        self.controllerConnected = 0
        if "avTitle" in self.ids:
            self.ids.avTitle.title = "Disconnected"
        print("Disconnect requested")

    def eStop(self):
        if self.controllerConnected > 0:
            self.dmcCommand("AB")  # The abort command will disable the drive.
            self.controllerConnected = 0
            self.dmc.GClose()  # close connection to controller
        self.ids.chooseController.collapse = False  # Open starting screen
        self.ids.avTitle.title = "E-STOP Triggered."  # Update the title

    # This function is called when a controller is selected on the first page
    def selectController(self, value, *args):
        opened = self.appGOpen(value)
        if opened:
            self.ids.homeSetup.collapse = False  # Open the Homing and Setup screen
            self.ids.avTitle.title = (
                "Connected to: " + value
            )  # Update the title to show the connected controller
            self.controllerConnected = 1
            self.dmcCommand("XQ")  # Run the downloaded program

    # This function is called when a controller is selected on the first page
    def appGOpen(self, value):
        try:
            self.dmc.GOpen(value + " -d")  # Call GOpen with the IP Address selected
            return 1
        except Exception as e:
            self.ids.avTitle.title = "Error: " + str(e)
            return 0

    # def on_kv_post(self, base_widget):
    # default landing page
    # Clock.schedule_once(lambda *_: self.switch_screen("normal"), 0)


class DMCCodeGUI(App):

    def build(self):
        title = "Binh An Controller App"
        return DMCControllerSetting()


if __name__ == "__main__":
    DMCCodeGUI().run()
