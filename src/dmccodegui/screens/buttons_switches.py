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
            self.refresh_axis_status()
        except Exception as e:
            print("Buttons and Switches Read Failed:", e)
            self._load_from_state()

    def refresh_axis_status(self) -> None:
        """Query controller for axis status and update checkboxes using MG command."""
        def do_refresh():
            try:
                axes = ['A', 'B', 'C', 'D']
                for axis in axes:
                    # Use MG command to get position and status in one call: MG _RP{axis}, _TS{axis}
                    mg_cmd = f"MG _RP{axis}, _TS{axis}"
                    data = self.controller.cmd(mg_cmd)
                    
                    if not data:
                        continue
                    
                    parts = data.split()
                    if len(parts) < 2:
                        continue
                    
                    try:
                        ts_value = int(parts[1])
                        
                        # Extract status bits from _TS{axis}
                        # Bit 2 (value 4): Reverse Limit Switch (active low, so invert)
                        reverse_limit = (ts_value & 4) == 0
                        
                        # Bit 3 (value 8): Forward Limit Switch (active low, so invert)
                        forward_limit = (ts_value & 8) == 0
                        
                        # Bit 5 (value 32): Motor Off
                        motor_off = (ts_value & 32) != 0
                        
                        # Bit 6 (value 64): Home switch (if applicable)
                        home = (ts_value & 64) == 0
                        
                        # Update UI on main thread
                        def update_ui(a=axis, rl=reverse_limit, hm=home, fl=forward_limit, mo=motor_off):
                            try:
                                self.ids[f"{a.lower()}_reverse_limit"].active = rl
                                self.ids[f"{a.lower()}_home"].active = hm
                                self.ids[f"{a.lower()}_forward_limit"].active = fl
                                self.ids[f"{a.lower()}_motor_off"].active = mo
                            except Exception:
                                pass
                        
                        Clock.schedule_once(lambda *_, u=update_ui: u())
                    except (ValueError, IndexError):
                        pass
            except Exception as e:
                print(f"Status refresh error: {e}")
        
        jobs.submit(do_refresh)

    def on_slider_release(self, axis: str, value: float) -> None:
        """Called when a slider is released. Sends PA command to controller."""
        try:
            # Round to integer
            int_value = int(round(value))
            
            # Update display
            display_id = f"value_{axis.lower()}_display"
            display = self.ids.get(display_id)
            if display:
                display.text = str(int_value)
            
            # Send command to controller
            self.dmcCommand(f"PA{axis}={int_value}")
            self.dmcCommand("BG")
        except Exception as e:
            self._alert(f"Slider error for {axis}: {e}")

    def on_slider_change(self, axis: str, value: float) -> None:
        """Update display value as slider moves (optional)."""
        try:
            int_value = int(round(value))
            display_id = f"value_{axis.lower()}_display"
            display = self.ids.get(display_id)
            if display:
                display.text = str(int_value)
        except Exception:
            pass


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

