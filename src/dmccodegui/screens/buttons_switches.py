from __future__ import annotations
from kivy.uix.switch import Switch
from typing import Dict
from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

from ..app_state import MachineState
from ..controller import GalilController
from ..utils import jobs

# 'IN1: SWITCH:                                              %
# 'IN2: SWITCH: JUMP TO SETUP PAGE                                             %
# 'IN3: SWITCH: JUMP TO PROBE B AXIS                                           %
# 'IN4: SWITCH:                                                 %
# 'IN5: SWITCH: SET ANGLE FIRST POINT                                          %
# 'IN6: SWITCH: SET ANGLE SECOND POINT                                         %
# 'IN7: SWITCH: SET ANGLE THIRD POINT                                          %
# 'IN8: SWITCH: SET ANGLE FOURTH POINT
# 'IN17: SWITCH: WHEELER A AXIS MOVEMENT                                       %
# 'IN18: SWITCH: WHEELER B AXIS MOVEMENT                                       %
# 'IN19: SWITCH: WHEELER C AXIS MOVEMENT                                       %
# 'IN20: SWITCH: WHEELER D AXIS MOVEMENT                                       %
# 'IN21: SWITCH: WHEELER X10 SPEED                                             %
# 'IN22: SWITCH: WHEELER X100 SPEED                                            %
# 'IN23: SWITCH: JUMP TO PROBE EDGE A AXIS  
# 
# 'IN24: ------:   SIGNAL FROM PROBE                                           %
# 'IN25: BUTTON: ADJUST MORE GRINDER MANUALLY                                   %
# 'IN26: BUTTON: ADJUST LESS GRINDER MANUALLY                                   %
# 'IN27: BUTTON:                                                             %
# 'IN28: BUTTON: SET START POINT                                             %
# 'IN29: BUTTON: SET REST POINT                                                  
# 'IN30: BUTTON: TO START A TURN  
class ButtonsSwitchesScreen(Screen):
    controller: GalilController = ObjectProperty(None)  # type: ignore
    state: MachineState = ObjectProperty(None)  # type: ignore

    def on_pre_enter(self, *args):  # noqa: ANN001
        try:
            if not self.controller or not self.controller.is_connected():
                raise RuntimeError("No controller connected")
        except Exception as e:
            print("Buttons and Switches Read Failed:", e)
            self._load_from_state()


    def _load_from_state(self) -> None:
        pass


    def loadArrayToPage(self, *args):
        pass

    # This lets us adjust the array values for array
    def adjust_axis(self, axis: str, delta: float) -> None:
        w = self._get_axis_input(axis)
        if not w:
            return
        try:
            cur = float(w.text or "0")
        except Exception:
            cur = 0.0
        new_val = int(cur + delta)
        w.text = str(new_val)
        

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

