from __future__ import annotations

import types
from dmccodegui.controller import GalilController


class DummyDriver:
    def __init__(self):
        self.opened = False
        self.cmds: list[str] = []

    def GOpen(self, address: str) -> None:  # noqa: N802
        self.opened = True

    def GClose(self) -> None:  # noqa: N802
        self.opened = False

    def GCommand(self, cmd: str) -> str:  # noqa: N802
        self.cmds.append(cmd)
        if cmd.startswith("MG{Z10.0} _RPA"):
            return "1 2 3 4 0"
        if cmd.startswith("MG{Z10.0} _SPA"):
            return "100"
        if cmd.startswith("MG "):
            return "1 2 3"
        return ""


def test_connect_and_cmd():
    drv = DummyDriver()
    c = GalilController(driver=drv)
    assert c.connect("X.X.X.X") is True
    assert c.is_connected() is True
    assert c.cmd("MG 1") == ""
    c.disconnect()
    assert c.is_connected() is False



def test_arrays():
    drv = DummyDriver()
    c = GalilController(driver=drv)
    c.connect("addr")
    vals = c.read_array("arr", 3)
    assert vals == [1.0, 2.0, 3.0]
    c.write_array("arr", {0: 5.0, 2: 9.0})
    assert any("arr[0]=5.0" in cmd or "arr[2]=9.0" in cmd for cmd in drv.cmds)

