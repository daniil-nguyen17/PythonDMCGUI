from __future__ import annotations

"""
buttons_switches.py — ButtonsSwitchesScreen

This screen provides real-time monitoring and manual control of all four axes:
  - Live status indicators (Reverse Limit, Home, Forward Limit, Motor Off) for A/B/C/D
  - Axis position sliders (manual jog by dragging)
  - Action buttons (Cancel, Them Da, Bot Da, etc.) — mapped to machine operations
  - Toggle switches (Enter Setup, Probing Mode, Chay Wheeler, etc.)

DMC STATUS READING: Uses 'MG _RP{axis}, _TS{axis}' command per axis.
  _RP{axis} — Reports Position (not currently used in display, but included for future use)
  _TS{axis} — Tells Status as a bitmask integer:
    Bit 2  (value 4):   Reverse Limit switch (active LOW — bit=0 means limit is hit)
    Bit 3  (value 8):   Forward Limit switch (active LOW — bit=0 means limit is hit)
    Bit 5  (value 32):  Motor Off (bit=1 means motor is off)
    Bit 6  (value 64):  Home switch (active LOW — bit=0 means home is active)

PHYSICAL INPUT MAPPING (from controller program comments):
  IN1:  Switch (reserved)
  IN2:  Switch — Jump to Setup page
  IN3:  Switch — Jump to Probe B axis
  IN4:  Switch (reserved)
  IN5:  Switch — Set angle first point
  IN6:  Switch — Set angle second point
  IN7:  Switch — Set angle third point
  IN8:  Switch — Set angle fourth point
  IN17: Switch — Wheeler A axis movement
  IN18: Switch — Wheeler B axis movement
  IN19: Switch — Wheeler C axis movement
  IN20: Switch — Wheeler D axis movement
  IN21: Switch — Wheeler X10 speed
  IN22: Switch — Wheeler X100 speed
  IN23: Switch — Jump to Probe edge A axis
  IN24: Signal — From probe
  IN25: Button — Adjust more grinder manually
  IN26: Button — Adjust less grinder manually
  IN27: Button (reserved)
  IN28: Button — Set Start Point
  IN29: Button — Set Rest Point
  IN30: Button — Start a turn

KV FILE: ui/buttons_switches.kv
  Checkboxes:
    ids.<axis>_reverse_limit   — Reverse limit indicator (A/B/C/D)
    ids.<axis>_home            — Home switch indicator (A/B/C/D)
    ids.<axis>_forward_limit   — Forward limit indicator (A/B/C/D)
    ids.<axis>_motor_off       — Motor off indicator (A/B/C/D)
  Sliders:
    ids.slider_<axis>          — Position slider (A/B/C/D), range -1000 to 1000
  Display labels:
    ids.value_<axis>_display   — Read-only TextInput showing slider position

UPDATE RATE: Status is polled at 10Hz (every 100ms) via Clock.schedule_interval
while this screen is visible. Updates stop when the operator navigates away.

THREADING MODEL:
  status refresh runs in jobs.submit() background thread; UI updates via Clock.schedule_once().
  Slider release callbacks call dmcCommand() which also uses jobs.submit().
"""

from kivy.uix.switch import Switch
from typing import Dict
from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

from ..app_state import MachineState
from ..controller import GalilController
from ..utils import jobs


class ButtonsSwitchesScreen(Screen):
    # Injected by main.py after the ScreenManager is built
    controller: GalilController = ObjectProperty(None)  # type: ignore
    state: MachineState = ObjectProperty(None)          # type: ignore

    _update_clock_event = None  # Reference to the scheduled 10Hz Clock event

    def on_pre_enter(self, *args):
        """
        Called by Kivy each time the operator navigates to this screen.

        Performs an immediate status refresh to populate the checkboxes, then
        starts the 10Hz continuous update loop so indicators stay live.

        Falls back to _load_from_state() if the controller is not connected.
        _load_from_state() is currently a no-op (pass) — add state-based fallback
        display logic there if needed.
        """
        try:
            if not self.controller or not self.controller.is_connected():
                raise RuntimeError("No controller connected")
            self.refresh_axis_status()
            self.start()  # Begin continuous 10Hz status polling
        except Exception as e:
            print("Buttons and Switches Read Failed:", e)
            self._load_from_state()

    def on_leave(self, *args):
        """
        Called by Kivy when the operator navigates away from this screen.

        Stops the 10Hz status update loop to avoid wasting CPU and controller
        bandwidth while this screen is not visible.
        """
        self.stop_update()

    def start(self) -> None:
        """
        Schedule the continuous status update to run at 10Hz (every 100ms).

        Cancels any existing schedule event first to prevent duplicate callbacks
        if start() is called more than once (e.g. returning to the screen).

        To change the update rate: modify the interval value (1/10.0 = 100ms).
        For example, 1/5.0 = 200ms (5Hz) for slower polling.
        """
        if self._update_clock_event:
            self._update_clock_event.cancel()
        self._update_clock_event = Clock.schedule_interval(self._update_clock, 1 / 10.0)

    def stop_update(self) -> None:
        """
        Cancel the scheduled 10Hz status update and clear the event reference.

        Called automatically by on_leave(). Also safe to call manually if the
        operator triggers a long-running operation and you want to pause polling.
        """
        if self._update_clock_event:
            self._update_clock_event.cancel()
            self._update_clock_event = None

    def _update_clock(self, dt: float) -> None:
        """
        Periodic callback at 10Hz — triggers a background status refresh.

        Parameters
        ----------
        dt : float — time delta since last call (provided by Kivy Clock, unused here)

        Skips the refresh silently if the controller is not connected, so this
        callback remains harmless even if the controller disconnects mid-session.
        """
        if not self.controller or not self.controller.is_connected():
            return
        self.refresh_axis_status()

    def refresh_axis_status(self) -> None:
        """
        Query the controller for axis status and update the four checkbox indicators
        for each axis (A, B, C, D) using the _TS (Tell Status) bitmask command.

        The MG command format: 'MG _RP{axis}, _TS{axis}'
          Returns two space-separated values: position and status bitmask.

        Status bitmask (_TS) interpretation:
          Bit 2  (& 4):   Reverse Limit — active low (0 = limit hit, show checked)
          Bit 3  (& 8):   Forward Limit — active low (0 = limit hit, show checked)
          Bit 5  (& 32):  Motor Off — active high (1 = motor is off, show checked)
          Bit 6  (& 64):  Home switch — active low (0 = home triggered, show checked)

        All controller I/O runs in a background thread (jobs.submit). UI checkbox
        updates are posted back to the Kivy main thread via Clock.schedule_once.

        To add a new status indicator: extend the update_ui() closure to include
        the new ids key, and add the corresponding CheckBox in buttons_switches.kv.
        """
        def do_refresh():
            try:
                axes = ['A', 'B', 'C', 'D']
                for axis in axes:
                    # Query both position and status in one MG command
                    mg_cmd = f"MG _RP{axis}, _TS{axis}"
                    data = self.controller.cmd(mg_cmd)

                    if not data:
                        continue

                    parts = data.split()
                    if len(parts) < 2:
                        continue

                    try:
                        ts_value = int(parts[1])

                        # Decode status bits (active-low limits: 0 = triggered)
                        reverse_limit = (ts_value & 4) == 0   # Bit 2 low = reverse limit hit
                        forward_limit = (ts_value & 8) == 0   # Bit 3 low = forward limit hit
                        motor_off     = (ts_value & 32) != 0  # Bit 5 high = motor is off
                        home          = (ts_value & 64) == 0  # Bit 6 low = home switch active

                        # Update checkbox indicators on the Kivy main thread
                        def update_ui(a=axis, rl=reverse_limit, hm=home, fl=forward_limit, mo=motor_off):
                            try:
                                self.ids[f"{a.lower()}_reverse_limit"].active = rl
                                self.ids[f"{a.lower()}_home"].active           = hm
                                self.ids[f"{a.lower()}_forward_limit"].active  = fl
                                self.ids[f"{a.lower()}_motor_off"].active      = mo
                            except Exception:
                                pass  # Widget may not exist if KV doesn't define that axis

                        Clock.schedule_once(lambda *_, u=update_ui: u())
                    except (ValueError, IndexError):
                        pass  # Ignore malformed controller responses
            except Exception as e:
                print(f"Status refresh error: {e}")

        jobs.submit(do_refresh)

    def on_slider_release(self, axis: str, value: float) -> None:
        """
        Called when a slider is released (touch_up event in KV).

        Rounds the slider value to the nearest integer, updates the display TextInput,
        and sends a PA (Position Absolute) command to move the axis to that position.
        A BG (Begin) command is sent immediately after to start the motion.

        KV binding (in buttons_switches.kv):
            Slider:
                on_touch_up: root.on_slider_release('A', self.value)

        Parameters
        ----------
        axis  : str   — axis letter ('A', 'B', 'C', 'D')
        value : float — raw slider value (range: -1000 to 1000 as defined in KV)

        DMC commands sent:
          'PA{axis}={int_value}' — Set target position for this specific axis
          'BG'                   — Begin motion immediately

        CAUTION: This sends real motor motion commands. Ensure safety interlocks
        are active before the operator uses these sliders.
        """
        try:
            int_value = int(round(value))

            # Update the read-only display TextInput next to the slider
            display_id = f"value_{axis.lower()}_display"
            display = self.ids.get(display_id)
            if display:
                display.text = str(int_value)

            # Send position + begin commands
            self.dmcCommand(f"PA{axis}={int_value}")
            self.dmcCommand("BG")
        except Exception as e:
            self._alert(f"Slider error for {axis}: {e}")

    def on_slider_change(self, axis: str, value: float) -> None:
        """
        Optional real-time callback as the slider moves (before release).

        Updates only the display label — does NOT send any controller commands.
        Useful to show the target position as the operator drags the slider.

        This method is not currently bound in the KV. To enable live display updates
        while dragging, add to buttons_switches.kv:
            Slider:
                on_value: root.on_slider_change('A', self.value)

        Parameters
        ----------
        axis  : str   — axis letter ('A', 'B', 'C', 'D')
        value : float — current slider value
        """
        try:
            int_value = int(round(value))
            display_id = f"value_{axis.lower()}_display"
            display = self.ids.get(display_id)
            if display:
                display.text = str(int_value)
        except Exception:
            pass

    def _load_from_state(self) -> None:
        """
        Fall-back when controller is not connected on screen enter.

        Currently a no-op. To display cached values when disconnected, add logic
        here to read from self.state and populate the slider displays.
        """
        pass

    def loadArrayToPage(self, *args):
        """
        Placeholder for array load — not used on this screen.

        Included for API consistency with other screens (start.py, rest.py).
        This screen does not use a named DMC array for its inputs.
        """
        pass

    def adjust_axis(self, axis: str, delta: float) -> None:
        """
        Nudge an axis text input value by delta and update the display.

        NOTE: This method references self._get_axis_input() which is NOT defined
        on this class (it exists on StartScreen / RestScreen). This method is
        currently unused by the buttons_switches.kv and will raise AttributeError
        if called. It is kept as a placeholder for future fine-step controls.

        To fix: either define _get_axis_input() here pointing to the slider display
        TextInputs, or remove this method if it is not needed.

        Parameters
        ----------
        axis  : str   — axis key
        delta : float — signed amount to add to the current display value
        """
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
        """
        Send a raw DMC command string to the controller in a background thread.

        All controller communication is non-blocking. Errors are printed to console
        and shown in the app banner via _alert().

        Parameters
        ----------
        command : str — raw DMC command (e.g. 'PAA=500', 'BG', 'ST ABCD')

        Example DMC commands used by this screen:
          'PA{axis}={n}'  — Position Absolute for a specific axis (e.g. 'PAA=500')
          'BG'            — Begin motion on all pending axes
        """
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
        """
        Push a message to the app-wide banner ticker via DMCApp._log_message().

        Falls back to state.log() if the app object is unavailable (e.g. during tests).

        Parameters
        ----------
        message : str — text to display in the banner
        """
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
