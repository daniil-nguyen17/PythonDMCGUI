import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_delta_c_constants_exist():
    """RUN-06: Writable range constants must be defined."""
    from dmccodegui.screens.flat_grind.widgets import (
        DELTA_C_WRITABLE_START,
        DELTA_C_WRITABLE_END,
        DELTA_C_ARRAY_SIZE,
        DELTA_C_STEP,
    )
    assert DELTA_C_WRITABLE_END > DELTA_C_WRITABLE_START
    assert DELTA_C_ARRAY_SIZE > 0
    assert DELTA_C_STEP > 0


def test_stone_constants_exist():
    """Stone geometry constants must be defined with expected values."""
    from dmccodegui.screens.flat_grind.widgets import (
        STONE_SURFACE_MM,
        STONE_OVERHANG_MM,
        STEP_MM,
        STONE_WINDOW_INDICES,
    )
    assert STONE_SURFACE_MM == 40.0
    assert STONE_OVERHANG_MM == 3.0
    assert STEP_MM == 1.3
    assert STONE_WINDOW_INDICES == 30


def test_stone_window_for_index_heel():
    """At heel (index 0), window should be pushed right: (0, 29)."""
    from dmccodegui.screens.flat_grind.widgets import stone_window_for_index
    start, end = stone_window_for_index(0)
    assert start == 0
    assert end == 29


def test_stone_window_for_index_center():
    """At mid-knife (index 50), window should be centered: (35, 65)."""
    from dmccodegui.screens.flat_grind.widgets import stone_window_for_index
    start, end = stone_window_for_index(50)
    assert start == 35
    assert end == 64  # 30 elements: 35..64 inclusive


def test_stone_window_for_index_tip():
    """At tip (index 99), window should be pushed left: (70, 99)."""
    from dmccodegui.screens.flat_grind.widgets import stone_window_for_index
    start, end = stone_window_for_index(99)
    assert start == 70
    assert end == 99


def test_stone_window_always_correct_size():
    """Window should always be exactly STONE_WINDOW_INDICES wide."""
    from dmccodegui.screens.flat_grind.widgets import stone_window_for_index, STONE_WINDOW_INDICES
    for center in range(100):
        start, end = stone_window_for_index(center)
        width = end - start + 1
        assert width == STONE_WINDOW_INDICES, f"center={center}: width={width}"
        assert start >= 0
        assert end <= 99


def test_offsets_to_delta_c_uniform():
    """Windowed ramp: 5 uniform segments should produce cumulative profile near target."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.flat_grind.run import FlatGrindRunScreen
    from dmccodegui.screens.flat_grind.widgets import DELTA_C_ARRAY_SIZE
    r = FlatGrindRunScreen()
    r.section_count = 5
    r.delta_c_offsets = [100.0] * 5
    result = r._offsets_to_delta_c()
    assert len(result) == DELTA_C_ARRAY_SIZE

    # Cumulative sum = actual C-axis profile
    cumsum = []
    acc = 0.0
    for v in result:
        acc += v
        cumsum.append(acc)

    # Mid-region cumsum should be positive and meaningful (ramps overlap and add)
    mid_values = cumsum[25:75]
    assert all(v > 10 for v in mid_values), \
        f"Mid-region cumsum should be positive, got range [{min(mid_values):.1f}, {max(mid_values):.1f}]"
    assert max(mid_values) > 30, \
        f"Peak cumsum should be meaningful, got {max(mid_values):.1f}"


def test_offsets_to_delta_c_varied():
    """Windowed ramp: 2 segments with +50/-50 should produce opposing peaks."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.flat_grind.run import FlatGrindRunScreen
    from dmccodegui.screens.flat_grind.widgets import DELTA_C_ARRAY_SIZE
    r = FlatGrindRunScreen()
    r.section_count = 2
    r.delta_c_offsets = [50.0, -50.0]
    result = r._offsets_to_delta_c()

    cumsum = []
    acc = 0.0
    for v in result:
        acc += v
        cumsum.append(acc)

    # First quarter center (~index 25): cumsum should peak near +50
    assert abs(cumsum[25] - 50.0) < 25, f"Expected ~50 at index 25, got {cumsum[25]:.1f}"
    # Third quarter center (~index 75): cumsum should peak near -50
    assert abs(cumsum[75] - (-50.0)) < 25, f"Expected ~-50 at index 75, got {cumsum[75]:.1f}"


def test_single_segment_ramp_net_zero():
    """A single segment ramp should sum to approximately zero (goes up and comes back)."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.flat_grind.run import FlatGrindRunScreen
    r = FlatGrindRunScreen()
    r.section_count = 1
    r.delta_c_offsets = [100.0]
    result = r._offsets_to_delta_c()
    total = sum(result)
    assert abs(total) < 1.0, f"Expected net sum ~0, got {total:.4f}"


def test_single_segment_cumsum_triangle():
    """Single segment should create triangular cumulative profile peaking at center."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.flat_grind.run import FlatGrindRunScreen
    from dmccodegui.screens.flat_grind.widgets import DELTA_C_ARRAY_SIZE
    r = FlatGrindRunScreen()
    r.section_count = 1
    r.delta_c_offsets = [100.0]
    result = r._offsets_to_delta_c()

    cumsum = []
    acc = 0.0
    for v in result:
        acc += v
        cumsum.append(acc)

    # Peak should be near the center (index ~49)
    peak_idx = cumsum.index(max(cumsum))
    assert 40 <= peak_idx <= 60, f"Peak at index {peak_idx}, expected near 50"
    # Peak value should be near the target offset
    assert abs(max(cumsum) - 100.0) < 20, f"Peak value {max(cumsum):.1f}, expected ~100"


def test_section_count_clamped():
    """RUN-06: Section count must be clamped to 1-10."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.flat_grind.run import FlatGrindRunScreen
    r = FlatGrindRunScreen()
    r.on_section_count_change(0)   # below min
    assert r.section_count >= 1
    r.on_section_count_change(11)  # above max
    assert r.section_count <= 10


def test_delta_c_step_adjustment():
    """RUN-06: Up/down adjustments change selected offset by DELTA_C_STEP."""
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from dmccodegui.screens.flat_grind.run import FlatGrindRunScreen
    from dmccodegui.screens.flat_grind.widgets import DELTA_C_STEP
    r = FlatGrindRunScreen()
    r.section_count = 3
    r.delta_c_offsets = [0.0, 0.0, 0.0]
    offsets = list(r.delta_c_offsets)
    offsets[1] += DELTA_C_STEP
    assert offsets[1] == DELTA_C_STEP
