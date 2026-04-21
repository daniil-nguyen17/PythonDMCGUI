# src/dmccodegui/screens/__init__.py

from .setup import SetupScreen
from .status_bar import StatusBar
from .tab_bar import TabBar
from .flat_grind import FlatGrindRunScreen, FlatGrindAxesSetupScreen, FlatGrindParametersScreen
from .run import RunScreen  # backward-compat alias
from .axes_setup import AxesSetupScreen  # backward-compat alias
from .parameters import ParametersScreen  # backward-compat alias
from .profiles import ProfilesScreen
# DiagnosticsScreen excluded from production builds (dev-only)
from .pin_overlay import PINOverlay
from .users import UsersScreen
from .base import BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen, SetupScreenMixin
from .flat_grind_widgets import DeltaCBarChart

__all__ = [
    "SetupScreen",
    "StatusBar",
    "TabBar",
    "FlatGrindRunScreen",
    "FlatGrindAxesSetupScreen",
    "FlatGrindParametersScreen",
    "RunScreen",
    "AxesSetupScreen",
    "ParametersScreen",
    "ProfilesScreen",
    "PINOverlay",
    "UsersScreen",
    "BaseRunScreen",
    "BaseAxesSetupScreen",
    "BaseParametersScreen",
    "SetupScreenMixin",
    "DeltaCBarChart",
]
