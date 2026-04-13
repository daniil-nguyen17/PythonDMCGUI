"""Convex-specific widgets.

Contains the ConvexAdjustPanel placeholder widget used by the Convex run screen.

TODO: Replace ConvexAdjustPanel placeholder after customer sign-off on
convex-specific adjustment controls. Current implementation is a visual
stub pending customer specification of the exact convex compensation
parameters and adjustment workflow.

Classes
-------
ConvexAdjustPanel
    Placeholder adjust panel for the Convex run screen. Displays a header
    and pending-specs message. Will be replaced with real controls once
    customer provides convex DMC variable specs.
"""
from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label


class ConvexAdjustPanel(BoxLayout):
    """Placeholder adjust panel for the Convex run screen.

    A vertical BoxLayout containing a styled header and a "pending specs"
    label. Replaced with full adjustment controls once customer provides
    convex compensation specifications.

    TODO: Replace this placeholder with real convex adjustment controls
    after customer sign-off on convex DMC variable names and workflow.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'

        # Header label — cyan accent matching convex theme
        header = Label(
            text='Convex Adjustments',
            font_size='13sp',
            bold=True,
            color=[0.024, 0.714, 0.831, 1],  # cyan accent
            halign='left',
            valign='middle',
            size_hint_y=None,
            height='32dp',
        )
        header.bind(size=header.setter('text_size'))
        self.add_widget(header)

        # Placeholder label — subdued grey
        placeholder = Label(
            text='Pending customer specs',
            font_size='12sp',
            color=[0.396, 0.455, 0.545, 1],  # subdued grey
            halign='center',
            valign='middle',
        )
        placeholder.bind(size=placeholder.setter('text_size'))
        self.add_widget(placeholder)
