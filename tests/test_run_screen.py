import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_run_screen_has_cycle_running_property():
    """RUN-04: RunScreen must expose cycle_running as a Kivy property."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    r = RunScreen()
    assert hasattr(r, 'cycle_running'), "RunScreen missing cycle_running property"


def test_run_screen_has_position_properties():
    """RUN-03: RunScreen must expose pos_a through pos_d."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    r = RunScreen()
    for axis in ('pos_a', 'pos_b', 'pos_c', 'pos_d'):
        assert hasattr(r, axis), f"RunScreen missing {axis} property"


def test_axis_positions_disconnected():
    """RUN-03: When disconnected, axis positions show '---'."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    r = RunScreen()
    # Default (no controller) should show '---'
    assert r.pos_a == '---', f"Expected '---', got '{r.pos_a}'"
    assert r.pos_b == '---', f"Expected '---', got '{r.pos_b}'"
    assert r.pos_c == '---', f"Expected '---', got '{r.pos_c}'"
    assert r.pos_d == '---', f"Expected '---', got '{r.pos_d}'"


def test_no_estop_in_run_bar():
    """RUN-02: E-STOP must NOT be in RunScreen — it is in StatusBar only."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    r = RunScreen()
    # RunScreen should not have any e_stop method or property
    assert not hasattr(r, 'e_stop_button'), "RunScreen should not have e_stop_button"


def test_cycle_status_machine_type():
    """RUN-04: is_serration flag controls cycle status field visibility."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen, IS_SERRATION
    r = RunScreen()
    assert hasattr(r, 'is_serration'), "RunScreen missing is_serration property"
    assert r.is_serration == IS_SERRATION


def test_progress_and_eta():
    """RUN-05: RunScreen exposes cycle_completion_pct and cycle_eta."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    r = RunScreen()
    assert hasattr(r, 'cycle_completion_pct'), "Missing cycle_completion_pct"
    assert hasattr(r, 'cycle_eta'), "Missing cycle_eta"
    assert r.cycle_completion_pct == 0
    assert r.cycle_eta == '--:--'


def test_delta_c_adjustment():
    """RUN-06: RunScreen has section_count and delta_c_offsets for Knife Grind Adjustment."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.run import RunScreen
    r = RunScreen()
    assert hasattr(r, 'section_count'), "Missing section_count"
    assert hasattr(r, 'delta_c_offsets'), "Missing delta_c_offsets"
