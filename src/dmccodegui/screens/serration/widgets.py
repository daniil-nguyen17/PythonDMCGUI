"""Serration-specific widgets.

Contains the CompPanel base widget and its concrete subclasses BCompPanel
(B-axis) and CCompPanel (C-axis / curve) for the Serration run screen.

Each panel is a horizontal strip of per-serration compensation elements with
Up/Down arrow buttons for 0.1 mm increments.  Values auto-save on button press.

CompVisualization draws a bar chart + dot overlay above the panel, with bars
and dots aligned vertically to the panel columns below.

Classes
-------
CompVisualization
    Bar chart + dot overlay for compensation values.
CompPanel
    Horizontal strip: [index, up-arrow, value, down-arrow] per serration.
BCompPanel / BCompVisualization
    B-axis compensation (cyan accent).
CCompPanel / CCompVisualization
    C-axis curve compensation (orange accent).

Constants
---------
COMP_MIN_MM, COMP_MAX_MM
    Valid range for individual compensation values in mm (shared by B and C).
COMP_STEP_MM
    Increment per Up/Down button press (0.1 mm).
"""
from __future__ import annotations

import os as _os
from typing import Callable, Optional

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Rectangle, Line as GLine
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

# ---------------------------------------------------------------------------
# Compensation bounds and step
# ---------------------------------------------------------------------------

COMP_MIN_MM: float = -15.0
COMP_MAX_MM: float = 15.0
COMP_STEP_MM: float = 0.1

# Legacy aliases used by external code
BCOMP_MIN_MM = COMP_MIN_MM
BCOMP_MAX_MM = COMP_MAX_MM

# ---------------------------------------------------------------------------
# DMC variable name constants
# ---------------------------------------------------------------------------

BCOMP_ARRAY_VAR: str = "bComp"
BCOMP_NUM_SERR_VAR: str = "numSerr"
CCOMP_ARRAY_VAR: str = "cComp"

# Asset paths for arrow images
_ASSETS_DIR = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))),
    'assets', 'images',
)
ARROW_UP_IMG = _os.path.join(_ASSETS_DIR, 'arrow-up-green.png')
ARROW_DOWN_IMG = _os.path.join(_ASSETS_DIR, 'arrow-down-red.png')


class _ImageButton(ButtonBehavior, Image):
    """Image that acts as a button."""
    pass


# ---------------------------------------------------------------------------
# CompVisualization — bar chart + dot overlay
# ---------------------------------------------------------------------------

class CompVisualization(Widget):
    """Bar chart with dot overlay for per-serration compensation values.

    Draws vertical bars from a center line (zero baseline) to each value,
    with a colored dot at each bar tip. Positive = green/up, negative = red/down.
    Auto-scales Y axis to fit data.
    """

    MARGIN_X = dp(20)
    MARGIN_Y = dp(8)

    _viz_title: str = ""

    def __init__(self, accent_color=None, **kwargs):
        super().__init__(**kwargs)
        self._values: list[float] = []
        self._accent = accent_color or [0.5, 0.5, 0.5, 1]
        self._label = Label(
            text=self._viz_title,
            font_size='11sp',
            color=self._accent,
            halign='left',
            valign='top',
            size_hint=(None, None),
            size=(dp(200), dp(16)),
        )
        self._label.bind(size=self._label.setter('text_size'))
        self.add_widget(self._label)
        self.bind(pos=self._redraw, size=self._redraw)

    def update_dots(self, values: list[float]) -> None:
        """Update the visualization with new compensation values."""
        self._values = list(values)
        self._redraw()

    def highlight_dot(self, index: int) -> None:
        """No-op kept for API compatibility."""
        pass

    def _redraw(self, *args) -> None:
        self.canvas.after.clear()
        values = self._values
        n = len(values)

        # Position the label
        self._label.pos = (self.x + dp(4), self.top - dp(18))
        self._label.text = f"{self._viz_title} — {n} pts" if n else self._viz_title

        if n < 2:
            return

        w = self.width
        h = self.height
        mx = self.MARGIN_X
        my = self.MARGIN_Y

        # Auto-scale
        max_abs = max(abs(v) for v in values) if values else 1.0
        max_abs = max(max_abs, 0.5)

        center_y = self.y + h / 2
        scale_y = (h / 2 - my) / max_abs

        # Bar geometry
        bar_w = max(2.0, (w - 2 * mx) / n - 2)

        with self.canvas.after:
            # Center line (zero baseline)
            Color(0.4, 0.4, 0.4, 0.5)
            GLine(points=[self.x + mx, center_y, self.right - mx, center_y], width=1)

            dot_r = dp(4)
            for i, val in enumerate(values):
                x = self.x + mx + i / (n - 1) * (w - 2 * mx)
                y = center_y + val * scale_y

                # Color based on value
                if abs(val) < 0.01:
                    c = (0.5, 0.5, 0.5, 0.6)
                elif val > 0:
                    intensity = min(abs(val) / max_abs, 1.0)
                    c = (0.2, 0.4 + 0.6 * intensity, 0.2, 0.8)
                else:
                    intensity = min(abs(val) / max_abs, 1.0)
                    c = (0.4 + 0.6 * intensity, 0.2, 0.2, 0.8)

                # Vertical bar from center to value
                Color(*c)
                bar_h = abs(y - center_y)
                if bar_h > 1:
                    bar_bottom = min(center_y, y)
                    Rectangle(
                        pos=(x - bar_w / 2, bar_bottom),
                        size=(bar_w, bar_h),
                    )

                # Dot at tip
                Color(c[0], c[1], c[2], 1.0)  # full opacity for dot
                Ellipse(pos=(x - dot_r, y - dot_r), size=(dot_r * 2, dot_r * 2))


class BCompVisualization(CompVisualization):
    """B-axis compensation visualization (cyan accent)."""
    _viz_title = "bComp — Bù răng"

    def __init__(self, **kwargs):
        super().__init__(accent_color=[0.024, 0.714, 0.831, 1], **kwargs)


class CCompVisualization(CompVisualization):
    """C-axis compensation visualization (orange accent)."""
    _viz_title = "cComp — Đường cong"

    def __init__(self, **kwargs):
        super().__init__(accent_color=[0.980, 0.569, 0.043, 1], **kwargs)


# ---------------------------------------------------------------------------
# CompPanel — horizontal strip with arrow buttons
# ---------------------------------------------------------------------------

class CompPanel(BoxLayout):
    """Horizontal strip of per-serration compensation elements.

    Each element is a narrow vertical column:
        [index label]   — 1-based, top
        [up-arrow btn]  — green arrow image
        [value label]   — current value in mm
        [down-arrow btn] — red arrow image

    Elements are proportionally spaced to align with CompVisualization dots.
    Arrow buttons auto-save: pressing up/down immediately fires save_callback.

    Properties
    ----------
    num_serrations : NumericProperty(0)

    Callbacks (set by parent screen)
    ---------------------------------
    save_callback    : Callable[[int, float], None]
    refresh_callback : Callable[[], None]
    """

    num_serrations = NumericProperty(0)

    save_callback: Optional[Callable[[int, float], None]] = None
    refresh_callback: Optional[Callable[[], None]] = None

    # Subclass overrides
    _title_prefix: str = "Comp"
    _accent_color: list[float] = [0.5, 0.5, 0.5, 1]
    _refresh_btn_text: str = "Doc"

    def __init__(self, **kwargs):
        kwargs.setdefault('orientation', 'vertical')
        super().__init__(**kwargs)

        # Horizontal strip — padding recalculated on resize to align
        # element centers with viz dot centers
        self._strip = BoxLayout(
            orientation='horizontal',
            size_hint_y=1,
            spacing=dp(0),
            padding=[0, 0, 0, 0],
        )
        self.add_widget(self._strip)
        self.bind(width=self._update_strip_padding)

        # Storage for programmatic updates
        self._values: dict[int, float] = {}
        self._val_labels: dict[int, Label] = {}

    def _on_refresh_pressed(self, *args) -> None:
        if self.refresh_callback is not None:
            self.refresh_callback()

    def build_rows(self, values: list[float]) -> None:
        """Build or rebuild compensation elements in a horizontal strip.

        Each element is a narrow vertical column:
            [index label]
            [up button]
            [value label]
            [down button]
        All laid out left-to-right, proportionally spaced to align with
        the dots on the CompVisualization above.
        Tooth 1 on the left.
        """
        self._strip.clear_widgets()
        self._values.clear()
        self._val_labels.clear()
        self.num_serrations = len(values)

        for i, val in enumerate(values):
            self._values[i] = val

            col = BoxLayout(
                orientation='vertical',
                size_hint_x=1,  # proportional — all columns equal width
                spacing=dp(1),
            )

            # Index label (top)
            idx_lbl = Label(
                text=str(i + 1),
                font_size='14sp',
                color=[0.396, 0.455, 0.545, 1],
                size_hint_y=None,
                height=dp(18),
                halign='center',
                valign='middle',
            )
            idx_lbl.bind(size=idx_lbl.setter('text_size'))
            col.add_widget(idx_lbl)

            # Up button (green arrow image)
            up_btn = _ImageButton(
                source=ARROW_UP_IMG,
                size_hint_y=1,
                allow_stretch=True,
                keep_ratio=True,
            )
            up_btn.bind(
                on_release=lambda btn, idx=i: self._on_step(idx, COMP_STEP_MM)
            )
            col.add_widget(up_btn)

            # Value label (center)
            val_lbl = Label(
                text=f'{val:.1f}',
                font_size='16sp',
                bold=True,
                color=[0.85, 0.85, 0.85, 1],
                size_hint_y=None,
                height=dp(22),
                halign='center',
                valign='middle',
            )
            val_lbl.bind(size=val_lbl.setter('text_size'))
            self._val_labels[i] = val_lbl
            col.add_widget(val_lbl)

            # Down button (red arrow image)
            down_btn = _ImageButton(
                source=ARROW_DOWN_IMG,
                size_hint_y=1,
                allow_stretch=True,
                keep_ratio=True,
            )
            down_btn.bind(
                on_release=lambda btn, idx=i: self._on_step(idx, -COMP_STEP_MM)
            )
            col.add_widget(down_btn)

            self._strip.add_widget(col)

        # Align element centers with viz dots
        self._update_strip_padding()

    def _update_strip_padding(self, *args) -> None:
        """Recalculate strip padding so element centers align with viz dots.

        Viz places dot i at: MARGIN_X + i/(n-1) * (width - 2*MARGIN_X)
        Strip element i center is at: pad_left + (i+0.5) * elem_width
        For alignment: pad_left + 0.5*elem_width = MARGIN_X
        and:           pad_left + (n-0.5)*elem_width = width - MARGIN_X

        Solving: elem_width = (width - 2*MARGIN_X) / (n-1)
                 pad_left   = MARGIN_X - elem_width/2
        """
        n = self.num_serrations
        if n < 2:
            self._strip.padding = [CompVisualization.MARGIN_X, 0,
                                   CompVisualization.MARGIN_X, 0]
            return

        w = self.width
        margin = CompVisualization.MARGIN_X
        elem_w = (w - 2 * margin) / (n - 1)
        pad = max(0, margin - elem_w / 2)
        self._strip.padding = [pad, 0, pad, 0]

    def _on_step(self, index: int, delta: float) -> None:
        """Increment/decrement a value, update UI, and auto-save."""
        old_val = self._values.get(index, 0.0)
        new_val = round(old_val + delta, 4)
        new_val = max(COMP_MIN_MM, min(COMP_MAX_MM, new_val))

        self._values[index] = new_val

        # Update UI
        lbl = self._val_labels.get(index)
        if lbl:
            lbl.text = f'{new_val:.1f}'

        # Auto-save
        if self.save_callback is not None:
            self.save_callback(index, new_val)

    def flash_result(self, index: int, success: bool) -> None:
        """Briefly flash a value label green (success) or red (failure)."""
        lbl = self._val_labels.get(index)
        if lbl is None:
            return
        color = [0.2, 0.9, 0.2, 1] if success else [0.9, 0.2, 0.2, 1]
        lbl.color = color
        Animation.cancel_all(lbl, 'color')
        anim = Animation(color=[0.85, 0.85, 0.85, 1], duration=0.8, t='out_quad')
        anim.start(lbl)


# ---------------------------------------------------------------------------
# BCompPanel — B-axis compensation
# ---------------------------------------------------------------------------

class BCompPanel(CompPanel):
    """B-axis per-serration compensation panel (cyan accent)."""

    _title_prefix = "bComp"
    _accent_color = [0.024, 0.714, 0.831, 1]  # cyan
    _refresh_btn_text = "Doc bComp"


# ---------------------------------------------------------------------------
# CCompPanel — C-axis curve compensation
# ---------------------------------------------------------------------------

class CCompPanel(CompPanel):
    """C-axis per-serration curve compensation panel (orange accent).

    Calculated by #CCBUILD on the controller from crvPeak and numSerr.
    The HMI reads and displays the array, and lets the operator fine-tune
    individual values and save them back.
    """

    _title_prefix = "cComp"
    _accent_color = [0.980, 0.569, 0.043, 1]  # orange
    _refresh_btn_text = "Doc cComp"
