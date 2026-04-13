"""Tests for the Serration screen package (Phase 21 Plan 01).

Verifies all SERR requirements covered by the package skeleton:
  - All three Serration screen classes importable
  - BCompPanel importable from serration.widgets
  - Registry points to real Serration classes (not FlatGrind placeholders)
  - numSerr in _SERRATION_PARAM_DEFS
  - No D-axis vars in Serration param_defs
  - Serration axes_setup.kv has no axis_row_d
  - dmc_vars has BCOMP_ARRAY and BCOMP_NUM_SERR constants
"""
import os
import sys

os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# ---------------------------------------------------------------------------
# 1. SerrationRunScreen importable and is subclass of BaseRunScreen
# ---------------------------------------------------------------------------

def test_serration_run_screen_importable():
    """SerrationRunScreen can be imported and is a subclass of BaseRunScreen."""
    from dmccodegui.screens.serration import SerrationRunScreen
    from dmccodegui.screens.base import BaseRunScreen

    assert SerrationRunScreen is not None, "SerrationRunScreen must be importable"
    assert issubclass(SerrationRunScreen, BaseRunScreen), (
        "SerrationRunScreen must be a subclass of BaseRunScreen"
    )


# ---------------------------------------------------------------------------
# 2. SerrationAxesSetupScreen importable and is subclass of BaseAxesSetupScreen
# ---------------------------------------------------------------------------

def test_serration_axes_setup_importable():
    """SerrationAxesSetupScreen can be imported and is a subclass of BaseAxesSetupScreen."""
    from dmccodegui.screens.serration import SerrationAxesSetupScreen
    from dmccodegui.screens.base import BaseAxesSetupScreen

    assert SerrationAxesSetupScreen is not None, "SerrationAxesSetupScreen must be importable"
    assert issubclass(SerrationAxesSetupScreen, BaseAxesSetupScreen), (
        "SerrationAxesSetupScreen must be a subclass of BaseAxesSetupScreen"
    )


# ---------------------------------------------------------------------------
# 3. SerrationAxesSetupScreen MRO includes BaseAxesSetupScreen
# ---------------------------------------------------------------------------

def test_serration_axes_setup_inherits_base():
    """SerrationAxesSetupScreen MRO includes BaseAxesSetupScreen."""
    from dmccodegui.screens.serration import SerrationAxesSetupScreen
    from dmccodegui.screens.base import BaseAxesSetupScreen

    mro = SerrationAxesSetupScreen.__mro__
    assert BaseAxesSetupScreen in mro, (
        f"BaseAxesSetupScreen must be in SerrationAxesSetupScreen MRO. "
        f"Got: {[c.__name__ for c in mro]}"
    )


# ---------------------------------------------------------------------------
# 4. SerrationParametersScreen importable and is subclass of BaseParametersScreen
# ---------------------------------------------------------------------------

def test_serration_params_importable():
    """SerrationParametersScreen can be imported and is a subclass of BaseParametersScreen."""
    from dmccodegui.screens.serration import SerrationParametersScreen
    from dmccodegui.screens.base import BaseParametersScreen

    assert SerrationParametersScreen is not None, "SerrationParametersScreen must be importable"
    assert issubclass(SerrationParametersScreen, BaseParametersScreen), (
        "SerrationParametersScreen must be a subclass of BaseParametersScreen"
    )


# ---------------------------------------------------------------------------
# 5. numSerr in _SERRATION_PARAM_DEFS via get_param_defs()
# ---------------------------------------------------------------------------

def test_serration_param_defs_has_numserr():
    """mc.get_param_defs('3-Axes Serration Grind') contains a dict with var='numSerr'."""
    import tempfile
    import dmccodegui.machine_config as mc

    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        settings_path = f.name

    try:
        mc.init(settings_path)
        param_defs = mc.get_param_defs("3-Axes Serration Grind")

        var_names = [d["var"] for d in param_defs]
        assert "numSerr" in var_names, (
            f"numSerr must be in Serration param_defs. Got vars: {var_names}"
        )

        # Also verify the entry has correct metadata
        num_serr_entry = next(d for d in param_defs if d["var"] == "numSerr")
        assert num_serr_entry["group"] == "Geometry", (
            f"numSerr must be in group 'Geometry', got '{num_serr_entry['group']}'"
        )
        assert num_serr_entry["min"] == 1.0, (
            f"numSerr min must be 1.0, got {num_serr_entry['min']}"
        )
        assert num_serr_entry["max"] == 200.0, (
            f"numSerr max must be 200.0, got {num_serr_entry['max']}"
        )
    finally:
        os.unlink(settings_path)


# ---------------------------------------------------------------------------
# 6. No D-axis vars in Serration param_defs
# ---------------------------------------------------------------------------

def test_serration_params_no_d_axis_vars():
    """None of the D-axis vars appear in Serration param_defs."""
    import tempfile
    import dmccodegui.machine_config as mc

    d_axis_vars = {"fdD", "pitchD", "ratioD", "ctsRevD"}

    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        settings_path = f.name

    try:
        mc.init(settings_path)
        param_defs = mc.get_param_defs("3-Axes Serration Grind")

        var_names = {d["var"] for d in param_defs}
        found_d_vars = d_axis_vars & var_names

        assert not found_d_vars, (
            f"D-axis vars must NOT appear in Serration param_defs. "
            f"Found: {found_d_vars}"
        )
    finally:
        os.unlink(settings_path)


# ---------------------------------------------------------------------------
# 7. BCompPanel importable from serration.widgets
# ---------------------------------------------------------------------------

def test_bcomp_panel_importable():
    """BCompPanel can be imported from dmccodegui.screens.serration.widgets."""
    from dmccodegui.screens.serration.widgets import BCompPanel
    from kivy.uix.boxlayout import BoxLayout

    assert BCompPanel is not None, "BCompPanel must be importable"
    assert issubclass(BCompPanel, BoxLayout), (
        "BCompPanel must inherit from BoxLayout"
    )


# ---------------------------------------------------------------------------
# 8. Registry points to Serration classes (not flat_grind)
# ---------------------------------------------------------------------------

def test_registry_points_to_serration_classes():
    """_REGISTRY['3-Axes Serration Grind']['screen_classes'] values contain 'serration' not 'flat_grind'."""
    from dmccodegui.machine_config import _REGISTRY

    serration_entry = _REGISTRY["3-Axes Serration Grind"]
    screen_classes = serration_entry["screen_classes"]

    for role, dotted_path in screen_classes.items():
        assert "serration" in dotted_path, (
            f"screen_classes['{role}'] must reference serration module, "
            f"got: '{dotted_path}'"
        )
        assert "flat_grind" not in dotted_path, (
            f"screen_classes['{role}'] must NOT reference flat_grind (Phase 20 placeholder), "
            f"got: '{dotted_path}'"
        )


# ---------------------------------------------------------------------------
# 9. serration/axes_setup.kv has no axis_row_d
# ---------------------------------------------------------------------------

def test_serration_axes_setup_kv_no_d_axis():
    """ui/serration/axes_setup.kv must not contain axis_row_d."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    kv_path = os.path.join(
        project_root, 'src', 'dmccodegui', 'ui', 'serration', 'axes_setup.kv'
    )

    assert os.path.exists(kv_path), f"axes_setup.kv must exist at: {kv_path}"

    with open(kv_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "axis_row_d" not in content, (
        "ui/serration/axes_setup.kv must NOT contain 'axis_row_d' — "
        "D-axis is absent from Serration machine (3-axis only)"
    )


# ---------------------------------------------------------------------------
# 10. dmc_vars has BCOMP_ARRAY and BCOMP_NUM_SERR constants
# ---------------------------------------------------------------------------

def test_dmc_vars_bcomp_constants():
    """BCOMP_ARRAY and BCOMP_NUM_SERR constants are importable from dmc_vars and are strings."""
    from dmccodegui.hmi.dmc_vars import BCOMP_ARRAY, BCOMP_NUM_SERR

    assert isinstance(BCOMP_ARRAY, str), (
        f"BCOMP_ARRAY must be a string, got {type(BCOMP_ARRAY)}"
    )
    assert isinstance(BCOMP_NUM_SERR, str), (
        f"BCOMP_NUM_SERR must be a string, got {type(BCOMP_NUM_SERR)}"
    )
    assert len(BCOMP_ARRAY) > 0, "BCOMP_ARRAY must not be empty"
    assert len(BCOMP_NUM_SERR) > 0, "BCOMP_NUM_SERR must not be empty"


# ---------------------------------------------------------------------------
# 11. SerrationRunScreen has no pos_d property (Plan 02)
# ---------------------------------------------------------------------------

def test_serration_run_screen_no_d_axis():
    """SerrationRunScreen has no pos_d property — D-axis absent from Serration machine."""
    from dmccodegui.screens.serration import SerrationRunScreen

    s = SerrationRunScreen()
    assert 'pos_d' not in s.properties(), (
        "SerrationRunScreen must NOT have pos_d — D-axis is absent from Serration (3-axis only)"
    )
    assert 'pos_a' in s.properties(), "SerrationRunScreen must have pos_a"
    assert 'pos_b' in s.properties(), "SerrationRunScreen must have pos_b"
    assert 'pos_c' in s.properties(), "SerrationRunScreen must have pos_c"


# ---------------------------------------------------------------------------
# 12. SerrationRunScreen has _read_bcomp and _write_bcomp_element methods (Plan 02)
# ---------------------------------------------------------------------------

def test_serration_run_screen_has_bcomp_methods():
    """SerrationRunScreen has _read_bcomp and _write_bcomp_element as callable methods."""
    from dmccodegui.screens.serration import SerrationRunScreen

    s = SerrationRunScreen()
    assert callable(getattr(s, '_read_bcomp', None)), (
        "SerrationRunScreen must have a callable _read_bcomp method"
    )
    assert callable(getattr(s, '_write_bcomp_element', None)), (
        "SerrationRunScreen must have a callable _write_bcomp_element method"
    )


# ---------------------------------------------------------------------------
# 13. serration/run.py has no matplotlib import
# ---------------------------------------------------------------------------

def test_serration_run_screen_no_matplotlib():
    """serration/run.py source file does not contain 'import matplotlib'."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    run_py_path = os.path.join(
        project_root, 'src', 'dmccodegui', 'screens', 'serration', 'run.py'
    )

    assert os.path.exists(run_py_path), f"serration/run.py must exist at: {run_py_path}"

    with open(run_py_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for actual import statements (not comments)
    lines = content.splitlines()
    import_lines = [
        line for line in lines
        if ('import matplotlib' in line or 'from matplotlib' in line)
        and not line.strip().startswith('#')
    ]
    assert not import_lines, (
        f"serration/run.py must NOT contain matplotlib imports. Found: {import_lines}"
    )


# ---------------------------------------------------------------------------
# 14. BCompPanel.build_rows() sets num_serrations correctly (Plan 02)
# ---------------------------------------------------------------------------

def test_bcomp_panel_renders_rows():
    """BCompPanel.build_rows([0.1, 0.2, 0.3]) sets num_serrations == 3."""
    from dmccodegui.screens.serration.widgets import BCompPanel

    panel = BCompPanel()
    panel.build_rows([0.1, 0.2, 0.3])

    assert panel.num_serrations == 3, (
        f"BCompPanel.num_serrations must be 3 after build_rows([0.1, 0.2, 0.3]), "
        f"got {panel.num_serrations}"
    )


# ---------------------------------------------------------------------------
# 15. BCompPanel validation constants are well-formed (Plan 02)
# ---------------------------------------------------------------------------

def test_bcomp_panel_validation():
    """BCOMP_MIN_MM and BCOMP_MAX_MM are floats with min < 0 < max."""
    from dmccodegui.screens.serration.widgets import BCOMP_MIN_MM, BCOMP_MAX_MM

    assert isinstance(BCOMP_MIN_MM, float), (
        f"BCOMP_MIN_MM must be a float, got {type(BCOMP_MIN_MM)}"
    )
    assert isinstance(BCOMP_MAX_MM, float), (
        f"BCOMP_MAX_MM must be a float, got {type(BCOMP_MAX_MM)}"
    )
    assert BCOMP_MIN_MM < 0, (
        f"BCOMP_MIN_MM must be negative, got {BCOMP_MIN_MM}"
    )
    assert BCOMP_MAX_MM > 0, (
        f"BCOMP_MAX_MM must be positive, got {BCOMP_MAX_MM}"
    )
    assert BCOMP_MIN_MM < BCOMP_MAX_MM, (
        f"BCOMP_MIN_MM ({BCOMP_MIN_MM}) must be less than BCOMP_MAX_MM ({BCOMP_MAX_MM})"
    )


# ---------------------------------------------------------------------------
# 16. ui/serration/run.kv has no pos_d (Plan 02)
# ---------------------------------------------------------------------------

def test_serration_run_kv_no_d_axis():
    """ui/serration/run.kv must not contain 'pos_d'."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    kv_path = os.path.join(
        project_root, 'src', 'dmccodegui', 'ui', 'serration', 'run.kv'
    )

    assert os.path.exists(kv_path), f"run.kv must exist at: {kv_path}"

    with open(kv_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert 'pos_d' not in content, (
        "ui/serration/run.kv must NOT contain 'pos_d' — D-axis absent from Serration machine"
    )


# ---------------------------------------------------------------------------
# 17. ui/serration/run.kv has no MatplotFigure (Plan 02)
# ---------------------------------------------------------------------------

def test_serration_run_kv_no_matplotlib():
    """ui/serration/run.kv must not contain 'MatplotFigure'."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    kv_path = os.path.join(
        project_root, 'src', 'dmccodegui', 'ui', 'serration', 'run.kv'
    )

    assert os.path.exists(kv_path), f"run.kv must exist at: {kv_path}"

    with open(kv_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert 'MatplotFigure' not in content, (
        "ui/serration/run.kv must NOT contain 'MatplotFigure' — no matplotlib in Serration run screen"
    )


# ---------------------------------------------------------------------------
# 18. ui/serration/run.kv has bcomp_panel id (Plan 02)
# ---------------------------------------------------------------------------

def test_serration_run_kv_has_bcomp():
    """ui/serration/run.kv must contain 'bcomp_panel' id."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    kv_path = os.path.join(
        project_root, 'src', 'dmccodegui', 'ui', 'serration', 'run.kv'
    )

    assert os.path.exists(kv_path), f"run.kv must exist at: {kv_path}"

    with open(kv_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert 'bcomp_panel' in content, (
        "ui/serration/run.kv must contain 'bcomp_panel' id — required for BCompPanel wiring"
    )
