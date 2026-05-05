"""CircularSlider — speedometer-style dial for touchscreen value selection.

A 270-degree arc gauge that responds to touch drag. Used for Auto Wear
compensation value on the Run screens (flat grind + serration).

Usage in KV::

    CircularSlider:
        min_val: 0
        max_val: 50
        value: root.auto_wear
        on_value_change: root.auto_wear = args[1]
"""
from __future__ import annotations

import math

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line
from kivy.properties import (
    BooleanProperty,
    ColorProperty,
    NumericProperty,
    StringProperty,
)
from kivy.uix.widget import Widget


class CircularSlider(Widget):
    """Speedometer-style circular slider widget.

    Properties
    ----------
    min_val : float
        Minimum slider value (default 0).
    max_val : float
        Maximum slider value (default 50).
    value : float
        Current value.
    label_text : str
        Label displayed above the value (default "Auto Wear").
    arc_color : list
        RGBA color for the filled arc (default cyan-ish).
    track_color : list
        RGBA color for the background track.
    """

    min_val = NumericProperty(0)
    max_val = NumericProperty(50)
    value = NumericProperty(0)
    label_text = StringProperty("Auto Wear")
    arc_color = ColorProperty([0.2, 0.7, 0.9, 1])
    track_color = ColorProperty([0.25, 0.25, 0.25, 1])
    _touching = BooleanProperty(False)

    # Arc spans 270 degrees: from 225 deg (bottom-left) to -45 deg (bottom-right)
    _ARC_START = -225  # Kivy Ellipse angle_start (degrees, CCW from 3 o'clock)
    _ARC_END = -225 + 270  # angle_end
    _ARC_SPAN = 270

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw, value=self._redraw)
        Clock.schedule_once(self._redraw, 0)

    def _redraw(self, *_args):
        """Redraw the circular gauge."""
        self.canvas.clear()

        # Calculate dimensions
        cx = self.center_x
        cy = self.center_y
        radius = min(self.width, self.height) * 0.4
        line_width = max(8, radius * 0.15)

        # Value as fraction 0-1
        frac = 0.0
        if self.max_val > self.min_val:
            frac = (self.value - self.min_val) / (self.max_val - self.min_val)
        frac = max(0.0, min(1.0, frac))

        with self.canvas:
            # Background track (full 270-degree arc)
            Color(*self.track_color)
            Line(
                circle=(cx, cy, radius, self._ARC_START, self._ARC_END),
                width=line_width,
                cap='round',
            )

            # Filled arc (value portion)
            if frac > 0.01:
                Color(*self.arc_color)
                value_end = self._ARC_START + (self._ARC_SPAN * frac)
                Line(
                    circle=(cx, cy, radius, self._ARC_START, value_end),
                    width=line_width,
                    cap='round',
                )

            # Tick marks at 0, 25, 50
            Color(0.6, 0.6, 0.6, 0.8)
            for tick_frac in [0.0, 0.5, 1.0]:
                angle_deg = 225 - (self._ARC_SPAN * tick_frac)
                angle_rad = math.radians(angle_deg)
                inner = radius - line_width
                outer = radius + line_width * 0.5
                x1 = cx + inner * math.cos(angle_rad)
                y1 = cy + inner * math.sin(angle_rad)
                x2 = cx + outer * math.cos(angle_rad)
                y2 = cy + outer * math.sin(angle_rad)
                Line(points=[x1, y1, x2, y2], width=1.5)

        # Update text labels (rendered by KV overlay or internal Label)
        # We dispatch the event for parent to handle
        self.dispatch('on_value_change', self.value)

    def on_value_change(self, *_args):
        """Event dispatched when value changes."""
        pass

    def on_touch_down(self, touch):
        """Start tracking touch if within the gauge area."""
        if not self.collide_point(*touch.pos):
            return False
        # Check if touch is near the arc (within radius)
        cx, cy = self.center_x, self.center_y
        radius = min(self.width, self.height) * 0.4
        dx = touch.x - cx
        dy = touch.y - cy
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < radius * 1.8:  # generous touch area
            touch.grab(self)
            self._touching = True
            self._update_value_from_touch(touch)
            return True
        return False

    def on_touch_move(self, touch):
        """Update value as finger drags around the arc."""
        if touch.grab_current is self:
            self._update_value_from_touch(touch)
            return True
        return False

    def on_touch_up(self, touch):
        """Release touch tracking and dispatch on_release event."""
        if touch.grab_current is self:
            touch.ungrab(self)
            self._touching = False
            self.dispatch('on_release', self.value)
            return True
        return False

    def on_release(self, *_args):
        """Event dispatched when user lifts finger — use this to send commands."""
        pass

    def _update_value_from_touch(self, touch):
        """Convert touch position to a value on the arc."""
        cx, cy = self.center_x, self.center_y
        dx = touch.x - cx
        dy = touch.y - cy

        # Angle from center (atan2 gives radians from positive X axis)
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)

        # Convert to our arc coordinate system
        # Arc goes from 225 deg (start/min) clockwise to -45 deg (end/max)
        # Normalize angle to 0-360
        if angle_deg < 0:
            angle_deg += 360

        # Map angle to fraction
        # Start is at 225 deg, end is at 315 deg (going clockwise = decreasing angle)
        # Actually our arc goes from 225 CCW... let me recalculate
        # In standard math coords: start at 225 (bottom-left), sweep CW 270 deg to 315 (bottom-right)
        # Going CW from 225: 225 → 180 → 90 → 0 → 315
        # Fraction: offset from 225, going clockwise

        offset = 225 - angle_deg
        if offset < 0:
            offset += 360

        # Clamp to arc span
        if offset > self._ARC_SPAN:
            # Outside arc — snap to nearest end
            if offset > self._ARC_SPAN + 45:
                offset = 0  # snap to min
            else:
                offset = self._ARC_SPAN  # snap to max

        frac = offset / self._ARC_SPAN
        new_val = self.min_val + frac * (self.max_val - self.min_val)

        # Round to nearest integer for this use case
        new_val = round(new_val)
        new_val = max(self.min_val, min(self.max_val, new_val))

        if new_val != self.value:
            self.value = new_val

    # Register custom event
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    @classmethod
    def _register_event(cls):
        pass


# Register custom event types
CircularSlider.register_event_type('on_value_change')
CircularSlider.register_event_type('on_release')
