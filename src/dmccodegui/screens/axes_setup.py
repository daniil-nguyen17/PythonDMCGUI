"""Backward-compatibility wrapper. Real implementation in screens.flat_grind.axes_setup."""
from .flat_grind.axes_setup import (  # noqa: F401
    _AXIS_ROW_IDS,
    AXIS_COLORS,
    AXIS_CPM_DEFAULTS,
    AXIS_LABELS,
)
from .flat_grind.axes_setup import FlatGrindAxesSetupScreen as AxesSetupScreen  # noqa: F401
