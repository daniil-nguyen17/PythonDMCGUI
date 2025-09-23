from __future__ import annotations

from dmccodegui.controller import GalilController


class AddrDriver:
    def __init__(self):
        self.opened = False

    def GOpen(self, address: str) -> None:  # noqa: N802
        self.opened = True

    def GClose(self) -> None:  # noqa: N802
        self.opened = False

    def GCommand(self, cmd: str) -> str:  # noqa: N802
        return "OK"

    def GAddresses(self):  # noqa: N802
        return {
            "192.168.0.50": "DMC Rev1",
            "COM1": "Serial port",
        }


def test_list_addresses_filters_serial():
    c = GalilController(driver=AddrDriver())
    addrs = c.list_addresses()
    assert "192.168.0.50" in addrs
    assert "COM1" not in addrs


