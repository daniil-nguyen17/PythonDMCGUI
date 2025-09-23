from __future__ import annotations

from dmccodegui.controller import GalilController


class DummyDriver:
    def __init__(self):
        self.store = {"arr": [0.0] * 10}
        self.opened = False

    def GOpen(self, address: str) -> None:  # noqa: N802
        self.opened = True

    def GClose(self) -> None:  # noqa: N802
        self.opened = False

    def GCommand(self, cmd: str) -> str:  # noqa: N802
        if cmd.startswith("MG "):
            refs = cmd[3:]
            vals = []
            for r in refs.split(","):
                name, idx = r.strip().split("[")
                idx = int(idx[:-1])
                vals.append(str(self.store[name][idx]))
            return " ".join(vals)
        if ";" in cmd or "[" in cmd:
            for part in cmd.split(";"):
                if not part:
                    continue
                name, rest = part.split("[")
                idx, val = rest.split("]=")
                self.store[name][int(idx)] = float(val)
            return ""
        return ""


def test_round_trip():
    d = DummyDriver()
    c = GalilController(driver=d)
    assert c.connect("addr")
    vals = c.read_array("arr", 5)
    assert vals == [0.0] * 5
    c.write_array("arr", {3: 12.5})
    vals2 = c.read_array("arr", 5)
    assert vals2[3] == 12.5

