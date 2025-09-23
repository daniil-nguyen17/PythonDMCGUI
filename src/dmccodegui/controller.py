from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .utils.fmt import clamp, parse_number_list


log = logging.getLogger(__name__)


class GalilDriverProtocol:
    """Minimal protocol so we can mock in tests.

    Real implementation is gclib.py handle with GOpen/GClose/GCommand.
    """

    def GOpen(self, address: str) -> None:  # noqa: N802 (Galil API name)
        ...

    def GClose(self) -> None:  # noqa: N802
        ...

    def GCommand(self, cmd: str) -> str:  # noqa: N802
        ...


class GalilController:
    def __init__(self, driver: Optional[GalilDriverProtocol] = None) -> None:
        self._driver = driver
        self._connected = False
        self._logger: Optional[callable] = None

    def set_logger(self, fn: Optional[callable]) -> None:
        self._logger = fn

    # Discovery
    def list_addresses(self) -> Dict[str, str]:
        """Return mapping of address -> description/revision if available.

        Uses gclib GAddresses when the underlying driver implements it.
        """
        drv = self._driver
        if drv is None:
            try:
                import gclib  # type: ignore
                drv = gclib.py()
            except Exception as e:  # pragma: no cover
                log.error("GAddresses unavailable: %s", e)
                return {}
        try:
            addrs = getattr(drv, "GAddresses", None)
            if not addrs:
                return {}
            result = addrs()
            # result may be dict-like
            items: Dict[str, str] = dict(result) if result else {}
            return items
        except Exception as e:
            log.error("list_addresses error: %s", e)
            return {}

    # Connection
    def connect(self, address: str) -> bool:
        if self._driver is None:
            try:
                import gclib  # type: ignore

                self._driver = gclib.py()
            except Exception as e:  # pragma: no cover
                log.error("Failed to import gclib: %s", e)
                return False
        try:
            self._driver.GOpen(address + " -d")
            self._connected = True
            if self._logger:
                try:
                    self._logger(f"Connected to: {address}")
                except Exception:
                    pass
            return True
        except Exception as e:
            log.error("connect error: %s", e)
            self._connected = False
            return False

    def disconnect(self) -> None:
        if self._driver is None:
            return
        try:
            self._driver.GClose()
        except Exception:
            pass
        finally:
            self._connected = False
            if self._logger:
                try:
                    self._logger("Disconnected")
                except Exception:
                    pass

    def is_connected(self) -> bool:
        return self._connected

    # Commands
    def cmd(self, command: str) -> str:
        if not self._driver or not self._connected:
            # Surface a clear message to UI when called while disconnected
            if self._logger:
                try:
                    self._logger("No controller connected")
                except Exception:
                    pass
            raise RuntimeError("No controller connected")
        try:
            resp = self._driver.GCommand(command)
            if self._logger:
                try:
                    self._logger(f"CMD {command} -> {resp.strip()}")
                except Exception:
                    pass
            return resp
        except Exception as e:
            # Try to fetch error string
            try:
                tc1 = self._driver.GCommand("TC1")
            except Exception:
                tc1 = str(e)
            if self._logger:
                try:
                    self._logger(f"Error: {tc1}")
                except Exception:
                    pass
            raise RuntimeError(tc1)

    def _raw_cmd(self, command: str) -> str:
        """Internal command without logger side-effects.

        Used for high-frequency polling to avoid UI spam.
        """
        if not self._driver:
            raise RuntimeError("No driver")
        try:
            return self._driver.GCommand(command)
        except Exception as e:
            try:
                tc1 = self._driver.GCommand("TC1")
            except Exception:
                tc1 = str(e)
            raise RuntimeError(tc1)

    def verify_connection(self) -> bool:
        """Try a benign command to determine if a working connection exists.

        If successful, marks controller as connected.
        """
        if not self._driver:
            return False
        try:
            _ = self._driver.GCommand("MG{Z10.0} _SPA")
            self._connected = True
            if self._logger:
                try:
                    self._logger("Verified existing connection")
                except Exception:
                    pass
            return True
        except Exception:
            self._connected = False
            return False

    # Status
    def read_status(self) -> Dict[str, Any]:
        resp = self._raw_cmd("MG{Z10.0} _RPA, _RPB, _RPC, _RPD, _TSA")
        nums = parse_number_list(resp)
        pos = {"A": nums[0] if len(nums) > 0 else 0.0,
               "B": nums[1] if len(nums) > 1 else 0.0,
               "C": nums[2] if len(nums) > 2 else 0.0,
               "D": nums[3] if len(nums) > 3 else 0.0}
        inputs_faults = int(nums[4]) if len(nums) > 4 else 0
        # Speed reading as example; adapt as needed
        sp = 0.0
        try:
            sp = float(self._raw_cmd("MG{Z10.0} _SPA"))
        except Exception:
            pass
        return {"pos": pos, "inputs": inputs_faults, "faults": inputs_faults, "speeds": sp}

    # Teach
    def teach_point(self, name: str) -> None:
        # Snapshot current positions into a named point on controller side if desired; keep simple here
        resp = self.cmd("MG{Z10.0} _RPA, _RPB, _RPC, _RPD")
        nums = parse_number_list(resp)
        if len(nums) < 4:
            raise RuntimeError("failed to read positions")
        # For now, storing happens at app state level by caller
        _ = {"A": nums[0], "B": nums[1], "C": nums[2], "D": nums[3]}

    # Arrays
    def read_array(self, name: str, count: int) -> List[float]:
        out: List[float] = []
        i = 0
        while i < count:
            n = min(20, count - i)
            refs = ", ".join(f"{name}[{j}]" for j in range(i, i + n))
            resp = self.cmd("MG " + refs)
            out.extend(parse_number_list(resp))
            i += n
        return out[:count]

    def write_array(self, name: str, updates: dict[int, float]) -> None:
        # Chunk to approximately 300 chars per command line
        items = sorted((idx, val) for idx, val in updates.items())
        line = ""
        for idx, val in items:
            cmd = f"{name}[{idx}]={val}"
            if len(line) + len(cmd) + 1 < 300:
                line = (line + ";" + cmd) if line else cmd
            else:
                self.cmd(line)
                line = cmd
        if line:
            self.cmd(line)

