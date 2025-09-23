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
    dmc = gclib.py()  # gclib object to communicate with Galil controllers
    sliderRange = (-500, 500000)
    cutLengthDefault = 500000
    controllerConnected = 0

    def on_kv_post(self, *_):
        # start periodic UI update and populate the list
        Clock.schedule_interval(self._update_clock, 0.1)
        self.populateControllers()

    # set title for the app depending on the page
    def _set_title(self, text):
        av = App.get_running_app().root.ids.get("avTitle")
        if av:
            av.title = text

    # start the app clock
    def start(self):
        Clock.schedule_interval(
            self._update_clock, 1 / 10.0
        )  # Setup the UI to run clock update 10 times a second
        self.populateControllers()

    # This function disconnects from the controller,
    # returns the screen to the Choose Controller menu,
    # and refreshes the controller list
    def disconnectAndRefresh(self):
        self.controllerConnected = 0
        self.dmc.GClose()  # close connection to controller
        App.get_running_app().root.ids.avTitle.title = (
            "Binh An Controller Setting"  # Update the title
        )
        self.populateControllers()

    # This function will populate the UI is available controllers on the network
    def populateControllers(self, *args):
        row = self.ids.get("row1")
        if not row:
            print("row1 id not found")
            return
        row.clear_widgets()

        # headers
        row.add_widget(
            Label(
                size_hint=(0.33, 0.15),
                height=34,
                text="[b]Click to Select Controller[/b]",
                markup=True,
            )
        )
        row.add_widget(
            Label(size_hint=(0.33, 0.15), height=34, text="[b]Address[/b]", markup=True)
        )
        row.add_widget(
            Label(
                size_hint=(0.33, 0.15), height=34, text="[b]Revision[/b]", markup=True
            )
        )

        try:
            controllers = self.dmc.GAddresses()  # dict-like
        except Exception as e:
            row.add_widget(Label(text=f"Error: {e}"))
            row.add_widget(Button(text="Refresh", on_press=self.populateControllers))
            row.add_widget(Label())
            return

        if controllers:
            for key, value in controllers.items():  # Python 3
                # button to select controller
                btn = Button(
                    size_hint=(0.33, 0.15),
                    height=34,
                    text=value.split("Rev")[0],
                    background_color=(0.6, 0.9, 1.0, 1),
                )
                btn.bind(on_press=partial(self.selectController, key))
                row.add_widget(btn)

                row.add_widget(Label(size_hint=(0.33, 0.15), height=34, text=key))

                rev = "Special"
                if "Rev" in value:
                    parts = value.split("Rev", 1)
                    if len(parts) > 1:
                        rev = "Rev" + parts[1]
                row.add_widget(Label(size_hint=(0.33, 0.15), height=34, text=rev))
        else:
            row.add_widget(
                Label(size_hint=(0.33, 0.15), height=34, text="No Controllers Found")
            )
            row.add_widget(
                Button(
                    size_hint=(0.33, 0.15),
                    height=34,
                    text="Refresh",
                    on_press=self.populateControllers,
                )
            )
            row.add_widget(Label())

    def selectController(self, address, *args):
        if self.appGOpen(address):
            self._set_title("Connected to: " + address)
            self.controllerConnected = 1
            # self.dmcCommand("XQ")   # uncomment if you want to immediately run a program

    def appGOpen(self, address):
        try:
            self.dmc.GOpen(address + " -d")
            return 1
        except Exception as e:
            self._set_title("Error: " + str(e))
            return 0

    def dmcCommand(self, cmd):
        try:
            self.dmc.GCommand(cmd)
        except Exception as e:
            try:
                tc1 = self.dmc.GCommand("TC1")
            except Exception:
                tc1 = str(e)
            self._set_title("Error: " + tc1)

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
            App.get_running_app().root.ids.avTitle.title = (
                "Error: " + tc1
            )  # Update title with error message

    # This function is called at 10Hz.
    # It will call the functions to update the selected screen
    # need to add code to update each screen (6) to have variable values updated
    def _update_clock(self, dt):
        if self.controllerConnected == 1:
            self.updateHomingScreen()
        elif self.controllerConnected == 2:
            self.updateCutScreen()

    # This function will update the homing screen UI elements.
    # The function will ask for the Reported Position (RP) and Tell the state of the Switches (TS)
    # From this data the LED elements, text elements and sliders can be updated.
    def updateHomingScreen(self):
        data = self.dmc.GCommand("MG{Z10.0} _RPA, _TSA")  # Get Position and Switch info
        self.ids["TPA"].text = data.split()[0]  # Update the Position Text Element
        self.ids["slider_TPA"].value = int(data.split()[0])  # Update the Slider element
        if (
            int(data.split()[1]) & 128
        ):  # extract bit index 7 in _TSA that tells if the axis is moving
            self.ids["_BGA"].text = "Axis Moving"
        else:
            self.ids["_BGA"].text = "Idle"
        if (
            int(data.split()[1]) & 4
        ):  # extract bit index 2 in _TSA for the Reverse Limit Switch status
            self.ids["_RLA"].active = False
        else:
            self.ids["_RLA"].active = True
        if (
            int(data.split()[1]) & 8
        ):  # extract bit index 3 in _TSA for the Forward Limit Switch status
            self.ids["_FLA"].active = False
        else:
            self.ids["_FLA"].active = True
        if (
            int(data.split()[1]) & 32
        ):  # extract bit index 5 in _TSA for the Motor Off status
            self.ids["_MOA"].active = True
        else:
            self.ids["_MOA"].active = False

    # reopen chooseController automatically when the setting screen is selected again
    def on_pre_enter(self, *args):
        ch = self.ids.get("chooseController")
        if ch and hasattr(ch, "collapse"):
            ch.collapse = False

    # def on_kv_post(self, base_widget):
    # default landing page
    # Clock.schedule_once(lambda *_: self.switch_screen("normal"), 0)


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


class SM(ScreenManager):
    pass


class DMCControllerSetting(BoxLayout):
    # for disconnect button on actionbar > disconnect from controller and refresh the page
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
            App.get_running_app().root.ids.avTitle.title = "Disconnected"
        print("Disconnect requested")

    # for estop button on action bar > emergency stop to abort everything
    def eStop(self):
        if self.controllerConnected > 0:
            self.dmcCommand("AB")  # The abort command will disable the drive.
            self.controllerConnected = 0
            self.dmc.GClose()  # close connection to controller
        self.ids.chooseController.collapse = False  # Open starting screen
        App.get_running_app().root.ids.avTitle.title = (
            "E-STOP Triggered."  # Update the title
        )


class DMCCodeGUI(App):

    def build(self):
        title = "Binh An Controller App"
        # Builder.load_file("dmccodegui.kv")
        return DMCControllerSetting()


if __name__ == "__main__":
    DMCCodeGUI().run()
