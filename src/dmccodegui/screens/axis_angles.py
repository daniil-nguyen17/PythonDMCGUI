from __future__ import annotations
from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Ellipse

from ..controller import GalilController
from ..app_state import MachineState
from ..utils import jobs


class ConnectorLine(Widget):
    """Draws a red line with circular nodes between two widgets or a vertical segment."""
    def __init__(self, start_widget: Widget, end_widget: Widget | None = None,
                 end_offset_y: float = 0, vertical_only: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.start_widget = start_widget
        self.end_widget = end_widget
        self.vertical_only = vertical_only
        self.end_offset_y = end_offset_y
        self.color = (1, 0, 0, 1)  # Red color
        self.thickness = 2
        self.circle_size = 10
        self.bind(pos=self.update_line, size=self.update_line)
        Clock.schedule_interval(self.update_line, 1 / 30)  # update ~30fps

    def update_line(self, *_):
        """Draws a connector line with circles at each endpoint."""
        try:
            start = self.start_widget.to_window(
                self.start_widget.center_x, self.start_widget.center_y
            )
        except Exception:
            return

        if self.end_widget:
            try:
                end = self.end_widget.to_window(
                    self.end_widget.center_x, self.end_widget.center_y
                )
            except Exception:
                return
            # Lower end point below input box
            end = (end[0], end[1] - self.end_offset_y)
        else:
            # For the preset vertical-only line
            end = (start[0], start[1] + 200)

        # Draw the line and nodes
        self.canvas.clear()
        with self.canvas:
            Color(*self.color)
            Line(points=[start[0], start[1], end[0], end[1]], width=self.thickness)
            Ellipse(
                pos=(start[0] - self.circle_size / 2, start[1] - self.circle_size / 2),
                size=(self.circle_size, self.circle_size),
            )
            Ellipse(
                pos=(end[0] - self.circle_size / 2, end[1] - self.circle_size / 2),
                size=(self.circle_size, self.circle_size),
            )


class AxisAnglesScreen(Screen):
    """Screen for configuring axis and angle parameters."""
    controller: GalilController = ObjectProperty(None)  # type: ignore
    state: MachineState = ObjectProperty(None)  # type: ignore

    def on_pre_enter(self, *_):
        """Called each time the screen is shown."""
        if not self.controller or not self.controller.is_connected():
            self.ids.status_label.text = "Controller not connected"
        else:
            self.ids.status_label.text = "Ready"

        # Schedule connector creation after layout stabilizes
        Clock.schedule_once(self._setup_connectors, 0.5)

    def _setup_connectors(self, *_):
        """Creates red connector lines from image points to input boxes."""
        image = self.ids.get("knife_image")
        if not image:
            return

        # These are the bottom-row inputs ("Angle" inputs)
        input_ids = ["input_b1", "input_b2", "input_b3", "input_b4"]
        inputs = [self.ids.get(i) for i in input_ids if i in self.ids]

        # --------------------------------------------------------------------
        # 🔴 START POINTS ON IMAGE
        # These are (x, y) pairs representing normalized image coordinates.
        # 0.0 = far left / bottom of the image, 1.0 = far right / top.
        # You can adjust these to control where the lines start on the knife.
        #
        # Example:
        # (0.1, 0.6) moves 10% from the left edge, 60% from the bottom edge.
        # --------------------------------------------------------------------
        relative_points = [
            (0.10, 0.50),  # preset line (leftmost, vertical only)
            (0.25, 0.55),  # connects to input_b1
            (0.45, 0.55),  # connects to input_b2
            (0.65, 0.52),  # connects to input_b3
            (0.85, 0.48),  # connects to input_b4
        ]

        # Remove old connectors if they exist
        if hasattr(self, "_connectors"):
            for line in self._connectors:
                self.remove_widget(line)
        self._connectors = []

        def clamp(val, minv, maxv):
            return max(min(val, maxv), minv)

        # Create anchor widgets for each point and link them
        for i, (rx, ry) in enumerate(relative_points):
            point_widget = Widget(size_hint=(None, None), size=(1, 1))
            self.add_widget(point_widget)

            def update_point_widget(_dt, ref_x=rx, ref_y=ry, img=image, widget=point_widget):
                # Clamp normalized values so they always stay inside the image
                ref_x = clamp(ref_x, 0.01, 0.99)
                ref_y = clamp(ref_y, 0.01, 0.99)
                img_x = img.x + img.width * ref_x
                img_y = img.y + img.height * ref_y
                widget.pos = (img_x, img_y)

            Clock.schedule_interval(update_point_widget, 1 / 30)

            # Line logic
            if i == 0:
                # Preset vertical-only line
                connector = ConnectorLine(point_widget, end_widget=None, vertical_only=True)
            else:
                end_widget = inputs[i - 1] if i - 1 < len(inputs) else None
                connector = ConnectorLine(point_widget, end_widget=end_widget, end_offset_y=50)

            self.add_widget(connector)
            self._connectors.append(connector)

    def on_apply(self):
        """Called when the Save/Apply button is pressed."""
        inputs = {}
        for key, widget in self.ids.items():
            if key.startswith("input_"):
                inputs[key] = widget.text
        summary = "\n".join(f"{k}: {v}" for k, v in inputs.items())
        msg = f"Applied Axis & Angles parameters:\n{summary}"

        def on_ui():
            self.ids.status_label.text = "Values applied."
            try:
                app = self.get_app()
                if app:
                    app._log_message(msg)
            except Exception:
                pass

        Clock.schedule_once(lambda *_: on_ui())

    def get_app(self):
        """Helper to fetch current running app."""
        try:
            from kivy.app import App
            return App.get_running_app()
        except Exception:
            return None
