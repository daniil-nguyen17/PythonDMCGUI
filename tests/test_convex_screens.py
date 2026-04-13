"""Tests for the Convex screen package (Phase 22 Plan 01).

Verifies all CONV requirements covered by the package skeleton:
  - All three Convex screen classes importable
  - ConvexAdjustPanel importable from convex.widgets
  - Registry points to real Convex classes (not FlatGrind placeholders)
  - _CONVEX_PARAM_DEFS has all expected Flat Grind variable names (placeholder)
  - _CONVEX_PARAM_DEFS is an independent object (not a shallow copy)
  - Placeholder comment exists in machine_config.py above _CONVEX_PARAM_DEFS
  - convex/axes_setup.kv contains axis_row_d (4-axis machine)
  - No KV rule name collisions across all machine types
  - load_kv() is callable from convex package
"""
import os
import sys

os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# ---------------------------------------------------------------------------
# 1. ConvexRunScreen importable and is subclass of BaseRunScreen
# ---------------------------------------------------------------------------

def test_convex_run_screen_importable():
    """ConvexRunScreen can be imported and is a subclass of BaseRunScreen. [CONV-01 partial]"""
    from dmccodegui.screens.convex import ConvexRunScreen
    from dmccodegui.screens.base import BaseRunScreen

    assert ConvexRunScreen is not None, "ConvexRunScreen must be importable"
    assert issubclass(ConvexRunScreen, BaseRunScreen), (
        "ConvexRunScreen must be a subclass of BaseRunScreen"
    )


# ---------------------------------------------------------------------------
# 2. ConvexAxesSetupScreen importable and is subclass of BaseAxesSetupScreen
# ---------------------------------------------------------------------------

def test_convex_axes_setup_importable():
    """ConvexAxesSetupScreen can be imported and is a subclass of BaseAxesSetupScreen. [CONV-02]"""
    from dmccodegui.screens.convex import ConvexAxesSetupScreen
    from dmccodegui.screens.base import BaseAxesSetupScreen

    assert ConvexAxesSetupScreen is not None, "ConvexAxesSetupScreen must be importable"
    assert issubclass(ConvexAxesSetupScreen, BaseAxesSetupScreen), (
        "ConvexAxesSetupScreen must be a subclass of BaseAxesSetupScreen"
    )


# ---------------------------------------------------------------------------
# 3. ConvexAxesSetupScreen MRO includes BaseAxesSetupScreen
# ---------------------------------------------------------------------------

def test_convex_axes_setup_inherits_base():
    """ConvexAxesSetupScreen MRO includes BaseAxesSetupScreen. [CONV-02]"""
    from dmccodegui.screens.convex import ConvexAxesSetupScreen
    from dmccodegui.screens.base import BaseAxesSetupScreen

    mro = ConvexAxesSetupScreen.__mro__
    assert BaseAxesSetupScreen in mro, (
        f"BaseAxesSetupScreen must be in ConvexAxesSetupScreen MRO. "
        f"Got: {[c.__name__ for c in mro]}"
    )


# ---------------------------------------------------------------------------
# 4. ConvexParametersScreen importable and is subclass of BaseParametersScreen
# ---------------------------------------------------------------------------

def test_convex_params_importable():
    """ConvexParametersScreen can be imported and is a subclass of BaseParametersScreen. [CONV-03]"""
    from dmccodegui.screens.convex import ConvexParametersScreen
    from dmccodegui.screens.base import BaseParametersScreen

    assert ConvexParametersScreen is not None, "ConvexParametersScreen must be importable"
    assert issubclass(ConvexParametersScreen, BaseParametersScreen), (
        "ConvexParametersScreen must be a subclass of BaseParametersScreen"
    )


# ---------------------------------------------------------------------------
# 5. Convex param_defs has all expected Flat Grind variable names
# ---------------------------------------------------------------------------

def test_convex_param_defs_has_all_flat_grind_vars():
    """mc.get_param_defs('4-Axes Convex Grind') contains all expected variable names. [CONV-03]"""
    import tempfile
    import dmccodegui.machine_config as mc

    expected_vars = {
        "knfThk", "edgeThk",
        "fdA", "fdB", "fdCdn", "fdCup", "fdPark", "fdD",
        "pitchA", "pitchB", "pitchC", "pitchD",
        "ratioA", "ratioB", "ratioC", "ratioD",
        "ctsRevA", "ctsRevB", "ctsRevC", "ctsRevD",
    }

    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        settings_path = f.name

    try:
        mc.init(settings_path)
        param_defs = mc.get_param_defs("4-Axes Convex Grind")

        var_names = {d["var"] for d in param_defs}
        missing = expected_vars - var_names

        assert not missing, (
            f"Convex param_defs is missing expected vars: {missing}. "
            f"Got: {var_names}"
        )
    finally:
        os.unlink(settings_path)


# ---------------------------------------------------------------------------
# 6. _CONVEX_PARAM_DEFS is independent from _FLAT_PARAM_DEFS
# ---------------------------------------------------------------------------

def test_convex_param_defs_independent():
    """_CONVEX_PARAM_DEFS is not the same object as _FLAT_PARAM_DEFS, and dicts are distinct objects. [CONV-04]"""
    from dmccodegui.machine_config import _CONVEX_PARAM_DEFS, _FLAT_PARAM_DEFS

    assert _CONVEX_PARAM_DEFS is not _FLAT_PARAM_DEFS, (
        "_CONVEX_PARAM_DEFS must not be the same list object as _FLAT_PARAM_DEFS"
    )

    # Verify individual dict entries are also independent objects
    for i, (convex_d, flat_d) in enumerate(zip(_CONVEX_PARAM_DEFS, _FLAT_PARAM_DEFS)):
        assert convex_d is not flat_d, (
            f"_CONVEX_PARAM_DEFS[{i}] must be a distinct dict object from _FLAT_PARAM_DEFS[{i}]. "
            f"Found same object at index {i}: {convex_d!r}"
        )


# ---------------------------------------------------------------------------
# 7. _CONVEX_PARAM_DEFS has placeholder comment in machine_config.py source
# ---------------------------------------------------------------------------

def test_convex_param_defs_has_placeholder_comment():
    """machine_config.py source contains 'Placeholder' in the 2 lines before _CONVEX_PARAM_DEFS definition. [CONV-04]"""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    mc_path = os.path.join(
        project_root, 'src', 'dmccodegui', 'machine_config.py'
    )

    assert os.path.exists(mc_path), f"machine_config.py must exist at: {mc_path}"

    with open(mc_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find the line that defines _CONVEX_PARAM_DEFS
    def_line_idx = None
    for i, line in enumerate(lines):
        if '_CONVEX_PARAM_DEFS' in line and '=' in line and 'List[Dict]' in line:
            def_line_idx = i
            break

    assert def_line_idx is not None, (
        "Could not find '_CONVEX_PARAM_DEFS: List[Dict] =' definition in machine_config.py"
    )

    # Check the 2 lines preceding the definition for "Placeholder"
    preceding_lines = ''.join(lines[max(0, def_line_idx - 2):def_line_idx])
    assert "Placeholder" in preceding_lines, (
        f"Expected 'Placeholder' in the 2 lines before _CONVEX_PARAM_DEFS definition. "
        f"Found:\n{preceding_lines!r}"
    )


# ---------------------------------------------------------------------------
# 8. ConvexAdjustPanel importable from convex.widgets
# ---------------------------------------------------------------------------

def test_convex_adjust_panel_importable():
    """ConvexAdjustPanel can be imported from dmccodegui.screens.convex.widgets. [CONV-01 partial]"""
    from dmccodegui.screens.convex.widgets import ConvexAdjustPanel
    from kivy.uix.boxlayout import BoxLayout

    assert ConvexAdjustPanel is not None, "ConvexAdjustPanel must be importable"
    assert issubclass(ConvexAdjustPanel, BoxLayout), (
        "ConvexAdjustPanel must inherit from BoxLayout"
    )

    # Instantiate and check children count
    panel = ConvexAdjustPanel()
    assert len(panel.children) >= 1, (
        f"ConvexAdjustPanel must have at least 1 child widget after instantiation. "
        f"Got {len(panel.children)} children."
    )


# ---------------------------------------------------------------------------
# 9. Registry points to Convex classes (not flat_grind)
# ---------------------------------------------------------------------------

def test_registry_points_to_convex_classes():
    """_REGISTRY['4-Axes Convex Grind']['screen_classes'] values contain 'convex' not 'flat_grind'. [CONV-01/02/03]"""
    from dmccodegui.machine_config import _REGISTRY

    convex_entry = _REGISTRY["4-Axes Convex Grind"]
    screen_classes = convex_entry["screen_classes"]

    for role, dotted_path in screen_classes.items():
        assert "convex" in dotted_path, (
            f"screen_classes['{role}'] must reference convex module, "
            f"got: '{dotted_path}'"
        )
        assert "flat_grind" not in dotted_path, (
            f"screen_classes['{role}'] must NOT reference flat_grind (Phase 20 placeholder), "
            f"got: '{dotted_path}'"
        )


# ---------------------------------------------------------------------------
# 10. convex/axes_setup.kv contains axis_row_d (4-axis machine)
# ---------------------------------------------------------------------------

def test_convex_axes_setup_kv_has_d_axis():
    """ui/convex/axes_setup.kv must contain axis_row_d — Convex is a 4-axis machine. [CONV-02]"""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    kv_path = os.path.join(
        project_root, 'src', 'dmccodegui', 'ui', 'convex', 'axes_setup.kv'
    )

    assert os.path.exists(kv_path), f"axes_setup.kv must exist at: {kv_path}"

    with open(kv_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "axis_row_d" in content, (
        "ui/convex/axes_setup.kv must contain 'axis_row_d' — "
        "D-axis is present on Convex machine (4-axis)"
    )


# ---------------------------------------------------------------------------
# 11. No KV rule name collisions across all machine screen KV files
# ---------------------------------------------------------------------------

def test_no_kv_rule_name_collisions():
    """No duplicate <ClassName>: rule headers across all KV files under ui/. [ALL]"""
    import re

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    ui_dir = os.path.join(project_root, 'src', 'dmccodegui', 'ui')

    assert os.path.exists(ui_dir), f"UI directory must exist at: {ui_dir}"

    # Collect all <ClassName>: headers from all .kv files
    rule_pattern = re.compile(r'^<(\w+)>:', re.MULTILINE)
    seen_rules: dict[str, str] = {}  # class_name -> file path
    duplicates: list[str] = []

    for dirpath, dirnames, filenames in os.walk(ui_dir):
        for filename in filenames:
            if not filename.endswith('.kv'):
                continue
            kv_path = os.path.join(dirpath, filename)
            with open(kv_path, 'r', encoding='utf-8') as f:
                content = f.read()
            matches = rule_pattern.findall(content)
            for class_name in matches:
                rel_path = os.path.relpath(kv_path, project_root)
                if class_name in seen_rules:
                    duplicates.append(
                        f"'{class_name}' found in both '{seen_rules[class_name]}' "
                        f"and '{rel_path}'"
                    )
                else:
                    seen_rules[class_name] = rel_path

    assert not duplicates, (
        f"KV rule name collisions found — second definition silently shadows first:\n"
        + "\n".join(f"  - {d}" for d in duplicates)
    )


# ---------------------------------------------------------------------------
# 12. load_kv() is callable from convex package
# ---------------------------------------------------------------------------

def test_convex_load_kv_callable():
    """load_kv exported from dmccodegui.screens.convex is callable. [infrastructure]"""
    from dmccodegui.screens.convex import load_kv

    assert load_kv is not None, "load_kv must be importable from dmccodegui.screens.convex"
    assert callable(load_kv), (
        f"load_kv must be callable. Got type: {type(load_kv)}"
    )
