import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dmccodegui.app_state import MachineState


def test_machine_state_has_cycle_running():
    """RUN-04: MachineState must have cycle_running field."""
    s = MachineState()
    assert hasattr(s, 'cycle_running'), "Missing cycle_running field"
    assert s.cycle_running == False


def test_machine_state_has_cycle_completion_pct():
    """RUN-05: MachineState must have cycle_completion_pct field."""
    s = MachineState()
    assert hasattr(s, 'cycle_completion_pct'), "Missing cycle_completion_pct field"
    assert s.cycle_completion_pct == 0.0


def test_machine_state_has_cycle_tooth():
    """RUN-04: Serration cycle status field."""
    s = MachineState()
    assert hasattr(s, 'cycle_tooth'), "Missing cycle_tooth field"
    assert s.cycle_tooth == 0


def test_machine_state_has_cycle_pass():
    """RUN-04: Serration cycle status field."""
    s = MachineState()
    assert hasattr(s, 'cycle_pass'), "Missing cycle_pass field"
    assert s.cycle_pass == 0


def test_machine_state_has_cycle_depth():
    """RUN-04: Serration cycle status field."""
    s = MachineState()
    assert hasattr(s, 'cycle_depth'), "Missing cycle_depth field"
    assert s.cycle_depth == 0.0


def test_machine_state_has_cycle_elapsed_s():
    """RUN-05: Elapsed time field for ETA calculation."""
    s = MachineState()
    assert hasattr(s, 'cycle_elapsed_s'), "Missing cycle_elapsed_s field"
    assert s.cycle_elapsed_s == 0.0


def test_machine_state_backward_compatible():
    """Existing fields still work after adding cycle fields."""
    s = MachineState()
    assert s.connected == False
    assert 'A' in s.pos
    assert s.running == False
