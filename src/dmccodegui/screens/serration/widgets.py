"""Serration-specific widgets.

Contains the BCompPanel widget for the bComp (B-axis compensation)
array display used by the Serration run screen.

Classes
-------
BCompPanel
    Scrollable editable list widget for the serration bComp compensation array.
    Inherits from BoxLayout (vertical orientation).

Constants
---------
BCOMP_MIN_MM, BCOMP_MAX_MM
    Valid range for individual bComp compensation values in mm.

BCOMP_ARRAY_VAR
    DMC variable name for the bComp array.
    TODO: verify exact name against real Serration DMC program.

BCOMP_NUM_SERR_VAR
    DMC variable name for the number of serrations.
    TODO: verify exact name against real Serration DMC program.
"""
from __future__ import annotations

from typing import Callable, Optional

from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

# ---------------------------------------------------------------------------
# bComp bounds
# ---------------------------------------------------------------------------

BCOMP_MIN_MM: float = -5.0   # Minimum bComp compensation value in mm
BCOMP_MAX_MM: float = 5.0    # Maximum bComp compensation value in mm

# ---------------------------------------------------------------------------
# DMC variable name constants
# ---------------------------------------------------------------------------

# TODO: verify name against real Serration DMC program (customer to confirm)
BCOMP_ARRAY_VAR: str = "bComp"

# TODO: verify name against real Serration DMC program (customer to confirm)
BCOMP_NUM_SERR_VAR: str = "numSerr"


# ---------------------------------------------------------------------------
# BCompPanel
# ---------------------------------------------------------------------------

class BCompPanel(BoxLayout):
    """Scrollable editable list widget for the serration bComp compensation array.

    Displays per-serration B-axis compensation values as a scrollable list with
    one row per serration. Each row has: an index label, an editable TextInput,
    and a Save button.

    The parent screen (SerrationRunScreen) wires save_callback and
    refresh_callback before calling build_rows().

    Properties
    ----------
    num_serrations : NumericProperty(0)
        Current number of serrations. Updated by build_rows().

    Callbacks (set by parent screen)
    ----------------------------------
    save_callback : Callable[[int, float], None]
        Called with (index, value_mm) when operator saves a valid row.
    refresh_callback : Callable[[], None]
        Called when operator taps the "Read bComp" button.
    """

    num_serrations = NumericProperty(0)

    # Callbacks wired by SerrationRunScreen on screen entry
    save_callback: Optional[Callable[[int, float], None]] = None
    refresh_callback: Optional[Callable[[], None]] = None

    def __init__(self, **kwargs):
        kwargs.setdefault('orientation', 'vertical')
        super().__init__(**kwargs)

        # Header area: title label + "Read bComp" refresh button
        header = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(40),
            spacing=dp(8),
        )

        self._title_label = Label(
            text='bComp — Serrations: --',
            font_size='13sp',
            bold=True,
            color=[0.024, 0.714, 0.831, 1],  # cyan accent
            halign='left',
            valign='middle',
        )
        self._title_label.bind(size=self._title_label.setter('text_size'))
        header.add_widget(self._title_label)

        refresh_btn = Button(
            text='Doc bComp',
            font_size='12sp',
            size_hint_x=None,
            width=dp(100),
            background_normal='',
            background_color=[0.118, 0.227, 0.373, 1],
            color=[0.576, 0.773, 0.992, 1],
        )
        refresh_btn.bind(on_release=self._on_refresh_pressed)
        header.add_widget(refresh_btn)

        self.add_widget(header)

        # Scrollable body with grid for rows
        self._scroll = ScrollView(do_scroll_x=False)
        self._grid = GridLayout(
            cols=3,
            size_hint_y=None,
            spacing=dp(2),
            padding=[dp(4), dp(2)],
        )
        self._grid.bind(minimum_height=self._grid.setter('height'))
        self._scroll.add_widget(self._grid)
        self.add_widget(self._scroll)

    def _on_refresh_pressed(self, *args) -> None:
        """Delegate to refresh_callback if wired."""
        if self.refresh_callback is not None:
            self.refresh_callback()

    def build_rows(self, values: list[float]) -> None:
        """Build or rebuild the compensation rows from the given values list.

        Clears the grid, then creates one row per value in the list.
        Each row: index label (col 0) + TextInput (col 1) + Save button (col 2).

        Args:
            values: One float per serration. Length determines num_serrations.
        """
        self._grid.clear_widgets()
        self.num_serrations = len(values)
        self._title_label.text = f'bComp — Serrations: {len(values)}'

        for i, val in enumerate(values):
            # Col 0: index label
            idx_lbl = Label(
                text=str(i),
                font_size='12sp',
                size_hint_y=None,
                height=dp(44),
                color=[0.396, 0.455, 0.545, 1],
                halign='center',
                valign='middle',
            )
            idx_lbl.bind(size=idx_lbl.setter('text_size'))
            self._grid.add_widget(idx_lbl)

            # Col 1: TextInput
            ti = TextInput(
                text=f'{val:.4f}',
                multiline=False,
                input_filter='float',
                font_size='13sp',
                size_hint_y=None,
                height=dp(44),
                halign='center',
            )
            self._grid.add_widget(ti)

            # Col 2: Save button — capture index and textinput by closure
            save_btn = Button(
                text='Luu',
                font_size='12sp',
                size_hint_y=None,
                height=dp(44),
                background_normal='',
                background_color=[0.09, 0.40, 0.20, 1],
                color=[0.733, 0.969, 0.827, 1],
            )
            # Bind with index capture
            save_btn.bind(
                on_release=lambda btn, idx=i, field=ti: self._on_save(idx, field.text)
            )
            self._grid.add_widget(save_btn)

    def _on_save(self, index: int, text: str) -> None:
        """Handle save action for a single compensation row.

        Validates the text against BCOMP_MIN_MM / BCOMP_MAX_MM.
        On valid input: calls save_callback(index, value_mm).
        On invalid input: flashes the relevant TextInput red.

        Args:
            index: Zero-based serration index.
            text:  New value as string (from TextInput).
        """
        # Locate the TextInput widget for this row (col 1 of row index*3)
        grid_children = self._grid.children  # reversed order in Kivy
        # Grid is row-major but Kivy stores children reversed
        # Find the TextInput in the same row as the index label
        total = len(grid_children)
        # Each row has 3 widgets; row 'index' starts at grid position (total - 1 - index*3)
        # We need to find the TextInput for this row
        row_position = total - 1 - index * 3  # position of index label in reversed list
        text_input = None
        if row_position >= 1:
            text_input = grid_children[row_position - 1]  # TextInput is next in reversed order

        try:
            value_mm = float(text)
        except (ValueError, TypeError):
            self._flash_error(text_input)
            return

        if not (BCOMP_MIN_MM <= value_mm <= BCOMP_MAX_MM):
            self._flash_error(text_input)
            return

        if self.save_callback is not None:
            self.save_callback(index, value_mm)

    def _flash_error(self, widget) -> None:
        """Flash a widget red briefly to indicate invalid input."""
        if widget is None:
            return
        from kivy.animation import Animation
        original_color = list(getattr(widget, 'background_color', [0.18, 0.19, 0.22, 1]))
        anim = (
            Animation(background_color=[0.9, 0.2, 0.2, 1], duration=0.15)
            + Animation(background_color=original_color, duration=0.3)
        )
        anim.start(widget)
