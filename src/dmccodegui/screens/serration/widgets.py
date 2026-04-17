"""Serration-specific widgets.

Contains the CompPanel base widget and its concrete subclasses BCompPanel
(B-axis) and CCompPanel (C-axis / curve) for the Serration run screen.

Each panel is a scrollable editable list of per-serration compensation values,
with 1-based display labels (the backend still uses 0-based indices).

Classes
-------
CompPanel
    Abstract base: header + scrollable grid of index / value / save-button rows.
BCompPanel
    B-axis compensation (operator-editable, persisted).
CCompPanel
    C-axis curve compensation (calculated by #CCBUILD on the controller,
    editable here for fine-tuning).

Constants
---------
COMP_MIN_MM, COMP_MAX_MM
    Valid range for individual compensation values in mm (shared by B and C).
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
# Compensation bounds (shared by B and C panels)
# ---------------------------------------------------------------------------

COMP_MIN_MM: float = -5.0
COMP_MAX_MM: float = 5.0

# Legacy aliases used by external code
BCOMP_MIN_MM = COMP_MIN_MM
BCOMP_MAX_MM = COMP_MAX_MM

# ---------------------------------------------------------------------------
# DMC variable name constants
# ---------------------------------------------------------------------------

BCOMP_ARRAY_VAR: str = "bComp"
BCOMP_NUM_SERR_VAR: str = "numSerr"
CCOMP_ARRAY_VAR: str = "cComp"


# ---------------------------------------------------------------------------
# CompPanel — shared base for BComp and CComp
# ---------------------------------------------------------------------------

class CompPanel(BoxLayout):
    """Scrollable editable list widget for a per-serration compensation array.

    Each row: 1-based display index (col 0, fixed width) + TextInput (col 1,
    fills remaining space) + Save button (col 2, fixed width). The 1-based
    display label avoids operator confusion; the backend save_callback still
    receives the 0-based index.

    Subclasses set _title_prefix and _accent_color in their __init__ to
    customize the header appearance.

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

        # Header: title + refresh button
        header = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(40),
            spacing=dp(8),
        )

        self._title_label = Label(
            text=f'{self._title_prefix} — Serrations: --',
            font_size='13sp',
            bold=True,
            color=self._accent_color,
            halign='left',
            valign='middle',
        )
        self._title_label.bind(size=self._title_label.setter('text_size'))
        header.add_widget(self._title_label)

        refresh_btn = Button(
            text=self._refresh_btn_text,
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

        # Scrollable body — 3-column grid with FIXED column widths so values
        # align vertically across all rows regardless of digit count.
        self._scroll = ScrollView(
            do_scroll_x=False,
            bar_width=dp(4),
            scroll_type=['bars', 'content'],
        )
        self._grid = GridLayout(
            cols=3,
            size_hint_y=None,
            spacing=dp(2),
            padding=[dp(4), dp(2)],
        )
        self._grid.bind(minimum_height=self._grid.setter('height'))
        self._scroll.add_widget(self._grid)
        self.add_widget(self._scroll)

        # Store TextInput refs keyed by 0-based index for reliable lookup
        self._ti_widgets: dict[int, TextInput] = {}

    def _on_refresh_pressed(self, *args) -> None:
        if self.refresh_callback is not None:
            self.refresh_callback()

    def build_rows(self, values: list[float]) -> None:
        """Build or rebuild compensation rows from the given values list.

        Display labels are 1-based (1, 2, 3, ...) but save_callback receives
        the original 0-based index.

        Args:
            values: One float per serration, 0-based.
        """
        self._grid.clear_widgets()
        self._ti_widgets.clear()
        self.num_serrations = len(values)
        self._title_label.text = f'{self._title_prefix} — Serrations: {len(values)}'

        # Fixed column widths for vertical alignment
        IDX_W = dp(40)
        SAVE_W = dp(56)
        ROW_H = dp(40)

        for i, val in enumerate(values):
            # Col 0: 1-based index label — fixed width so numbers align
            idx_lbl = Label(
                text=str(i + 1),
                font_size='12sp',
                size_hint_x=None,
                width=IDX_W,
                size_hint_y=None,
                height=ROW_H,
                color=[0.396, 0.455, 0.545, 1],
                halign='center',
                valign='middle',
            )
            idx_lbl.bind(size=idx_lbl.setter('text_size'))
            self._grid.add_widget(idx_lbl)

            # Col 1: TextInput — fills remaining width
            ti = TextInput(
                text=f'{val:.4f}',
                multiline=False,
                input_filter='float',
                font_size='13sp',
                size_hint_y=None,
                height=ROW_H,
                halign='center',
            )
            self._ti_widgets[i] = ti
            self._grid.add_widget(ti)

            # Col 2: Save button — fixed width
            save_btn = Button(
                text='Luu',
                font_size='12sp',
                size_hint_x=None,
                width=SAVE_W,
                size_hint_y=None,
                height=ROW_H,
                background_normal='',
                background_color=[0.09, 0.40, 0.20, 1],
                color=[0.733, 0.969, 0.827, 1],
            )
            save_btn.bind(
                on_release=lambda btn, idx=i, field=ti: self._on_save(idx, field.text)
            )
            self._grid.add_widget(save_btn)

    def _on_save(self, index: int, text: str) -> None:
        """Validate and dispatch save for a single row.

        Args:
            index: 0-based serration index (backend).
            text:  New value string from the TextInput.
        """
        ti = self._ti_widgets.get(index)

        try:
            value_mm = float(text)
        except (ValueError, TypeError):
            self._flash_error(ti)
            return

        if not (COMP_MIN_MM <= value_mm <= COMP_MAX_MM):
            self._flash_error(ti)
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
