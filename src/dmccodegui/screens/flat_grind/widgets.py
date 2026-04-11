"""Flat Grind-specific widgets and constants.

Contains the DeltaC bar chart widget and associated stone geometry constants
used by the Flat Grind run screen.

Note: BCompBarChart and BCOMP_* constants are Serration-specific and remain
in run.py until Phase 21 (Serration Screen Set) moves them to the Serration
screen module.

Classes
-------
_BaseBarChart
    Shared base for bar chart widgets. Draws per-section bars on a zero baseline.
    Subclasses set STEP as a class attribute.

DeltaCBarChart
    Bar chart for per-section deltaC (Knife Grind Adjustment) offsets.

Constants
---------
DELTA_C_WRITABLE_START, DELTA_C_WRITABLE_END, DELTA_C_ARRAY_SIZE, DELTA_C_STEP
    Controller array bounds and increment for the deltaC array.

STONE_SURFACE_MM, STONE_OVERHANG_MM, STEP_MM, STONE_WINDOW_INDICES
    Stone geometry constants for windowed compensation.

Functions
---------
stone_window_for_index(center, array_size, window)
    Return (start, end) inclusive indices of stone contact for a knife position.
"""
from __future__ import annotations

from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Rectangle
from kivy.properties import ListProperty, NumericProperty
from kivy.uix.widget import Widget

# ---------------------------------------------------------------------------
# Delta-C constants
# ---------------------------------------------------------------------------

DELTA_C_WRITABLE_START: int = 0    # First writable index in the deltaC array on controller
DELTA_C_WRITABLE_END: int = 99     # Last writable index (inclusive) — 100 elements total
DELTA_C_ARRAY_SIZE: int = DELTA_C_WRITABLE_END - DELTA_C_WRITABLE_START + 1  # = 100
DELTA_C_STEP: int = 50             # Adjustment increment per button press in controller counts

# Stone geometry for windowed compensation
STONE_SURFACE_MM: float = 40.0       # grinding surface width (outer - inner diameter / 2)
STONE_OVERHANG_MM: float = 3.0       # stone extends past heel (index 0 is 3mm past heel)
STEP_MM: float = 1.3                 # approx mm per deltaC index (avg of 1.2-1.4)
STONE_WINDOW_INDICES: int = int(STONE_SURFACE_MM / STEP_MM)  # ~30 indices


# ---------------------------------------------------------------------------
# Stone window helper
# ---------------------------------------------------------------------------

def stone_window_for_index(
    center: int,
    array_size: int = DELTA_C_ARRAY_SIZE,
    window: int = STONE_WINDOW_INDICES,
) -> tuple[int, int]:
    """Return (start, end) inclusive indices of stone contact for a knife position.

    The window is centered on *center*. Near the heel (low indices) or tip
    (high indices), the window shifts to stay within bounds.

    Examples (defaults: array_size=100, window=30):
        center=0  -> (0, 29)     heel: window pushed right
        center=50 -> (35, 65)    mid-knife: centered
        center=99 -> (70, 99)    tip: window pushed left
    """
    half = window // 2
    start = center - half
    end = start + window - 1

    if start < 0:
        end -= start
        start = 0
    if end > array_size - 1:
        start -= (end - (array_size - 1))
        end = array_size - 1
    start = max(0, start)

    return (start, end)


# ---------------------------------------------------------------------------
# _BaseBarChart
# ---------------------------------------------------------------------------

class _BaseBarChart(Widget):
    """Shared base for DeltaCBarChart and BCompBarChart.

    Draws a per-section bar chart on a zero baseline. Positive offsets extend
    above the centre line; negative offsets extend below. Tapping a bar selects
    it (highlighted in orange).

    Subclasses set ``STEP`` as a class attribute.

    Properties
    ----------
    offsets : ListProperty([])
        One float per section.
    selected_index : NumericProperty(-1)
        Index of the currently selected bar. -1 means nothing selected.
    max_offset : NumericProperty(500)
        Absolute offset value that maps to half the widget height (clamps bars).
    """

    offsets = ListProperty([])
    selected_index = NumericProperty(-1)
    max_offset = NumericProperty(500)

    STEP: int = 50  # Override in subclasses

    # ------------------------------------------------------------------
    # Reactive triggers — any change to size/pos/offsets/selection redraws
    # ------------------------------------------------------------------

    def on_offsets(self, *args) -> None:
        self._draw()

    def on_selected_index(self, *args) -> None:
        self._draw()

    def on_size(self, *args) -> None:
        self._draw()

    def on_pos(self, *args) -> None:
        self._draw()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        """Clear and redraw all bars using Kivy canvas instructions."""
        self.canvas.clear()
        offsets = list(self.offsets)
        n = len(offsets)
        if n == 0:
            return

        bar_w = self.width / n
        mid_y = self.y + self.height / 2.0
        half_h = self.height / 2.0

        with self.canvas:
            # Zero baseline — thin grey horizontal line
            Color(0.4, 0.4, 0.4, 1)
            Rectangle(pos=(self.x, mid_y - 0.5), size=(self.width, 1))

            for i, offset in enumerate(offsets):
                if self.max_offset > 0:
                    raw_h = abs(offset) / self.max_offset * half_h
                else:
                    raw_h = 0.0
                bar_h = max(10.0, raw_h)

                if i == int(self.selected_index):
                    Color(1.0, 0.65, 0.0, 1)
                else:
                    Color(0.235, 0.510, 0.960, 1)

                bar_x = self.x + i * bar_w
                if offset >= 0:
                    Rectangle(pos=(bar_x + 1, mid_y), size=(bar_w - 2, bar_h))
                else:
                    Rectangle(pos=(bar_x + 1, mid_y - bar_h), size=(bar_w - 2, bar_h))

    # ------------------------------------------------------------------
    # Touch handling
    # ------------------------------------------------------------------

    def on_touch_down(self, touch) -> bool:
        """Select the bar that was tapped."""
        if not self.collide_point(touch.x, touch.y):
            return False
        n = len(self.offsets)
        if n == 0:
            return True
        bar_w = self.width / n
        idx = int((touch.x - self.x) / bar_w)
        idx = max(0, min(n - 1, idx))
        self.selected_index = idx
        return True


# ---------------------------------------------------------------------------
# DeltaCBarChart
# ---------------------------------------------------------------------------

class DeltaCBarChart(_BaseBarChart):
    """Bar-chart widget that draws per-section deltaC offsets on a zero baseline.

    Each bar represents one section of the knife. Positive offsets extend above
    the centre line; negative offsets extend below. Tapping a bar selects it
    (highlighted in orange); the RunScreen up/down buttons adjust the selected
    bar's offset.

    Segment labels are drawn below the bars: "GOT" (heel) on the left edge,
    "MUI" (tip) on the right edge, and segment numbers centred under each bar.

    Properties
    ----------
    offsets : ListProperty([])
        One float per section.  Bound to RunScreen.delta_c_offsets in KV.
    selected_index : NumericProperty(-1)
        Index of the currently selected bar.  -1 means nothing selected.
    max_offset : NumericProperty(500)
        Absolute offset value that maps to half the widget height (clamps bars).
    """

    STEP: int = DELTA_C_STEP
    _LABEL_HEIGHT: int = 18  # px reserved at bottom for labels

    def _draw(self) -> None:
        self.canvas.clear()
        offsets = list(self.offsets)
        n = len(offsets)
        if n == 0:
            return

        label_h = self._LABEL_HEIGHT
        bar_w = self.width / n
        # Reserve label_h at bottom for segment labels
        chart_top = self.y + self.height
        chart_bottom = self.y + label_h
        chart_h = chart_top - chart_bottom
        mid_y = chart_bottom + chart_h / 2.0
        half_h = chart_h / 2.0

        with self.canvas:
            # Zero baseline
            Color(0.4, 0.4, 0.4, 1)
            Rectangle(pos=(self.x, mid_y - 0.5), size=(self.width, 1))

            # Bars
            for i, offset in enumerate(offsets):
                if self.max_offset > 0:
                    raw_h = abs(offset) / self.max_offset * half_h
                else:
                    raw_h = 0.0
                bar_h = max(10.0, raw_h)

                if i == int(self.selected_index):
                    Color(1.0, 0.65, 0.0, 1)
                else:
                    Color(0.235, 0.510, 0.960, 1)

                bar_x = self.x + i * bar_w
                if offset >= 0:
                    Rectangle(pos=(bar_x + 1, mid_y), size=(bar_w - 2, bar_h))
                else:
                    Rectangle(pos=(bar_x + 1, mid_y - bar_h), size=(bar_w - 2, bar_h))

            # Segment number labels under each bar
            Color(0.7, 0.7, 0.7, 1)
            for i in range(n):
                lbl = CoreLabel(text=str(i + 1), font_size=10)
                lbl.refresh()
                tex = lbl.texture
                bx = self.x + i * bar_w + (bar_w - tex.width) / 2.0
                Rectangle(texture=tex, pos=(bx, self.y), size=tex.size)

            # "GOT" (heel) label — left edge (grind start)
            Color(0.95, 0.75, 0.3, 1)
            heel_lbl = CoreLabel(text='GOT', font_size=10, bold=True)
            heel_lbl.refresh()
            heel_tex = heel_lbl.texture
            Rectangle(
                texture=heel_tex,
                pos=(self.x + 2, self.y),
                size=heel_tex.size,
            )

            # "MUI" (tip) label — right edge (grind end)
            tip_lbl = CoreLabel(text='MUI', font_size=10, bold=True)
            tip_lbl.refresh()
            tip_tex = tip_lbl.texture
            Rectangle(
                texture=tip_tex,
                pos=(self.x + self.width - tip_tex.width - 2, self.y),
                size=tip_tex.size,
            )

            # Stone window overlay — shows which indices are under the stone
            sel = int(self.selected_index)
            if sel >= 0 and n > 0:
                chunk = DELTA_C_ARRAY_SIZE // n
                seg_first = sel * chunk
                seg_last = (seg_first + chunk - 1) if sel < n - 1 else (DELTA_C_ARRAY_SIZE - 1)
                seg_center = (seg_first + seg_last) // 2

                win_start, win_end = stone_window_for_index(seg_center)

                px_per_idx = self.width / DELTA_C_ARRAY_SIZE
                overlay_x = self.x + win_start * px_per_idx
                overlay_w = (win_end - win_start + 1) * px_per_idx

                # Semi-transparent yellow fill
                Color(1.0, 1.0, 0.0, 0.10)
                Rectangle(pos=(overlay_x, chart_bottom), size=(overlay_w, chart_h))

                # Edge lines
                Color(1.0, 1.0, 0.0, 0.35)
                Rectangle(pos=(overlay_x, chart_bottom), size=(1, chart_h))
                Rectangle(pos=(overlay_x + overlay_w - 1, chart_bottom), size=(1, chart_h))

    def on_touch_down(self, touch) -> bool:
        """Select bar — ignore touches in the label strip at the bottom."""
        if not self.collide_point(touch.x, touch.y):
            return False
        if touch.y < self.y + self._LABEL_HEIGHT:
            return False
        n = len(self.offsets)
        if n == 0:
            return True
        bar_w = self.width / n
        idx = int((touch.x - self.x) / bar_w)
        idx = max(0, min(n - 1, idx))
        self.selected_index = idx
        return True
