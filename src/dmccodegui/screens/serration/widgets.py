"""Serration-specific widgets.

Contains the BCompPanel widget skeleton for the bComp (B-axis compensation)
array display used by the Serration run screen.

Plan 02 (SerrationRunScreen) fills in the full scrollable list implementation.

Classes
-------
BCompPanel
    Skeleton widget for the serration bComp compensation array editor.
    Inherits from BoxLayout (needs layout, not bare Widget).

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

from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout

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
    """Skeleton widget for the serration bComp compensation array editor.

    Displays per-serration B-axis compensation values as a scrollable list.
    Plan 02 (SerrationRunScreen) implements the full list with editable rows.

    Properties
    ----------
    num_serrations : NumericProperty(0)
        Current number of serrations. Controls how many rows are shown.
    """

    num_serrations = NumericProperty(0)

    def build_rows(self, values: list[float]) -> None:
        """Build or rebuild the compensation rows from the given values list.

        Args:
            values: One float per serration, length must match num_serrations.
                    Plan 02 implements the full row build logic.
        """
        # Stub — Plan 02 implements the full scrollable list
        pass

    def _on_save(self, index: int, text: str) -> None:
        """Handle save action for a single compensation row.

        Args:
            index: Zero-based serration index.
            text:  New value as string (from TextInput).
                   Plan 02 validates and writes to controller.
        """
        # Stub — Plan 02 implements validation and controller write
        pass
