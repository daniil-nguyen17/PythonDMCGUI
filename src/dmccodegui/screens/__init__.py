# src/dmccodegui/screens/__init__.py

from .setup import SetupScreen
from .arrays import ArraysScreen
from .rest import RestScreen
from .start import StartScreen
# EdgePointBScreen/EdgePointCScreen are declared in KV inheriting ArraysScreen
# Import/export screen classes
from .parameters_setup import ParametersSetupScreen
from .buttons_switches import ButtonsSwitchesScreen
from .axis_angles import AxisAnglesScreen  # ✅ add this line

__all__ = [
    "SetupScreen",
    "ArraysScreen",
    "RestScreen",
    "StartScreen",
    "ParametersSetupScreen",
    "ButtonsSwitchesScreen",
    "AxisAnglesScreen",  # ✅ export it too
]
