from __future__ import annotations

import math
import pytest

from dmccodegui.controller import (
    GalilController,
    ControllerNotReady,
    IndexOutOfRange,
    ParseError,
)


class FakeDriver:
    def __init__(self) -> None:
        # Minimal backing store for arrays
        self.memory = {
            "EdgeB": [10000.0] * 24 + [0.0] * (150 - 24),
            "EdgeC": [10000.0] * 24 + [0.0] * (150 - 24),
        }
        self.opened = False
        self.ready = True  # controls _TPA readiness

    # Galil API
    def GOpen(self, address: str) -> None:  # noqa: N802
        self.opened = True

    def GClose(self) -> None:  # noqa: N802
        self.opened = False

    def GCommand(self, cmd: str) -> str:  # noqa: N802
        cmd = cmd.strip()
        if cmd.startswith("TC1"):
            return "0"
        if cmd.startswith("MG{Z10.0} _TPA"):
            if not self.ready:
                raise RuntimeError("not ready")
            return "0"
        if cmd.startswith("MG EdgeB[") or cmd.startswith("MG EdgeC["):
            name = "EdgeB" if "EdgeB" in cmd else "EdgeC"
            idx = int(cmd.split("[")[1].split("]")[0])
            try:
                return str(float(self.memory[name][idx]))
            except Exception:
                return "?"
        # generic passthrough
        raise RuntimeError(f"unsupported cmd: {cmd}")


def make_controller() -> GalilController:
    drv = FakeDriver()
    ctl = GalilController(driver=drv)
    assert ctl.connect("FAKE")
    ctl.set_max_edges(150)
    return ctl


def test_wait_for_ready_ok():
    ctl = make_controller()
    ctl.wait_for_ready(timeout_s=0.2)


def test_scalar_read_ok():
    ctl = make_controller()
    ctl.wait_for_ready(timeout_s=0.2)
    b0 = ctl.read_edge_b(0)
    c0 = ctl.read_edge_c(0)
    assert b0 == 10000.0
    assert c0 == 10000.0


def test_slice_read_ok():
    ctl = make_controller()
    ctl.wait_for_ready(timeout_s=0.2)
    vals = ctl.read_array_slice("EdgeB", 0, 5)
    assert len(vals) == 5
    assert all(v == 10000.0 for v in vals)


def test_out_of_range_index():
    ctl = make_controller()
    ctl.wait_for_ready(timeout_s=0.2)
    with pytest.raises(IndexOutOfRange):
        ctl.read_edge_b(10000)


def test_discover_length_trailing_zeros():
    ctl = make_controller()
    ctl.wait_for_ready(timeout_s=0.2)
    n = ctl.discover_length("EdgeB", probe_max=50, zero_run=3)
    assert n == 24


def test_not_ready_raises():
    drv = FakeDriver()
    drv.ready = False
    ctl = GalilController(driver=drv)
    assert ctl.connect("FAKE")
    with pytest.raises(ControllerNotReady):
        ctl.wait_for_ready(timeout_s=0.2, poll_s=0.05)


