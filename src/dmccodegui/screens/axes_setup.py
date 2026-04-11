"""Backward-compatibility wrapper. Real implementation in screens.flat_grind.axes_setup."""
from .flat_grind.axes_setup import FlatGrindAxesSetupScreen as AxesSetupScreen  # noqa: F401
from .flat_grind.axes_setup import (  # noqa: F401
    AXIS_CPM_DEFAULTS, AXIS_LABELS, AXIS_COLORS, _AXIS_ROW_IDS,
)
