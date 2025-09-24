from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from .utils.fmt import clamp, parse_number_list
#get logger for messages
log = logging.getLogger(__name__)
# Try to import gclib at module level, but don't fail if it's not available
try:
    import gclib  # type: ignore
    GCLIB_AVAILABLE = True
except ImportError:
    gclib = None  # type: ignore
    GCLIB_AVAILABLE = False
# Create the global handle lazily/safely
if GCLIB_AVAILABLE:
    try:
        globalDMC = gclib.py()
    except Exception as e:  # pragma: no cover
        log.error("Failed to create gclib handle: %s", e)
        globalDMC = None  # type: ignore
else:
    globalDMC = None  # type: ignore


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


class ControllerNotReady(Exception):
    pass


class IndexOutOfRange(Exception):
    pass


class ParseError(Exception):
    pass


FLOAT_CHARS = set("0123456789+-.eE")


def _parse_float_str(s: str) -> float:
    t = s.strip()
    if not t or any(ch not in FLOAT_CHARS for ch in t):
        # Fall back to robust list parsing if there are commas/spaces
        try:
            nums = parse_number_list(t)
            if not nums:
                raise ValueError("no numbers found")
            return float(nums[0])
        except Exception as e:
            raise ParseError(f"Non-numeric: '{s}' ({e})")
    try:
        return float(t)
    except Exception as e:
        raise ParseError(f"Parse error for '{s}': {e}")


MAX_EDGES_DEFAULT = 150


class GalilController:
    
    def __init__(self, driver: Optional[GalilDriverProtocol] = None) -> None:
        self._driver = driver
        self._connected = False
        self._logger: Optional[callable] = None
        self._transport: Optional[GalilTransport] = None
        self._max_edges: int = MAX_EDGES_DEFAULT

    def set_logger(self, fn: Optional[callable]) -> None:
        self._logger = fn

    # Discovery
    def list_addresses(self) -> Dict[str, str]:
        """Return mapping of address -> description/revision if available.

        Uses gclib GAddresses when the underlying driver implements it.
        """
        drv = self._driver
        if drv is None:
            if not GCLIB_AVAILABLE:
                log.error("GAddresses unavailable: gclib not installed")
                return {}
            try:
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
            if not GCLIB_AVAILABLE:
                log.error("Failed to connect: gclib not installed")
                return False
            try:
                self._driver = gclib.py()
            except Exception as e:  # pragma: no cover
                log.error("Failed to create gclib driver: %s", e)
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

    # ===================== Robust Edge array APIs =====================
    def set_max_edges(self, n: int) -> None:
        self._max_edges = max(1, n)

    def ensure_connected(self) -> None:
        if not self._connected or not self._transport or not self._transport.is_connected():
            raise CommError("Not connected")

    def wait_for_ready(self, *, timeout_s: float = 5.0, poll_s: float = 0.1) -> None:
        """Wait until controller is responsive and arrays declared.

        1) Probe a cheap numeric like _TPA
        2) Probe EdgeB[0] and EdgeC[0]
        """
        self.ensure_connected()
        end = (time.monotonic() + timeout_s)
        last_err: Optional[Exception] = None
        print("[CTRL] Waiting for controller ready...")
        while time.monotonic() < end:
            try:
                _ = _parse_float_str(self.cmd("MG{Z10.0} _TPA"))
                # If _TPA is ok, try arrays
                b0 = self.cmd("MG EdgeB[0]").strip()
                c0 = self.cmd("MG EdgeC[0]").strip()
                if b0 != "?" and c0 != "?":
                    # parse to confirm numeric
                    _ = _parse_float_str(b0)
                    _ = _parse_float_str(c0)
                    print("[CTRL] Ready: arrays declared and numeric")
                    return
            except Exception as e:
                last_err = e
            time.sleep(poll_s)
        raise ControllerNotReady(f"Controller arrays not ready within {timeout_s}s: {last_err}")

    def _validate_index(self, idx: int) -> None:
        if idx < 0 or idx >= self._max_edges:
            raise IndexOutOfRange(f"index {idx} out of range (0..{self._max_edges-1})")

    def read_array_elem(self, var_name: str, idx: int) -> float:
        self.ensure_connected()
        self._validate_index(idx)
        cmd = f"MG {var_name}[{idx}]"
        resp = self.cmd(cmd)
        if resp.strip() == "?":
            print(f"[CTRL] READ ELEM '?' for {cmd}")
            raise ControllerNotReady(f"Array {var_name} not available")
        return _parse_float_str(resp)

    def read_array_slice(self, var_name: str, start: int, count: int) -> List[float]:
        self.ensure_connected()
        if start < 0 or count <= 0:
            raise IndexOutOfRange("start/count must be non-negative and count>0")
        if start + count > self._max_edges:
            raise IndexOutOfRange(f"slice {start}+{count} exceeds max {self._max_edges}")
        out: List[float] = []
        print(f"[CTRL] Reading slice {var_name}[{start}:{start+count}]")
        for i in range(start, start + count):
            out.append(self.read_array_elem(var_name, i))
        return out

    def read_edge_b(self, idx: int) -> float:
        return self.read_array_elem("EdgeB", idx)

    def read_edge_c(self, idx: int) -> float:
        return self.read_array_elem("EdgeC", idx)

    def discover_length(self, var_name: str, probe_max: Optional[int] = None, zero_run: int = 5) -> int:
        self.ensure_connected()
        limit = min(self._max_edges, probe_max or self._max_edges)
        last_nonzero = -1
        zeros = 0
        for i in range(0, limit):
            try:
                val = self.read_array_elem(var_name, i)
            except ControllerNotReady:
                break
            if abs(val) < 1e-9:
                zeros += 1
                if zeros >= zero_run and i > 0:
                    print(f"[CTRL] discover_length: hit {zero_run} zeros at {i}")
                    break
            else:
                last_nonzero = i
                zeros = 0
        length = max(0, last_nonzero + 1)
        print(f"[CTRL] discover_length({var_name}) -> {length}")
        return length

    def get_edges_window(self, var_name: str, start: int, count: int) -> List[float]:
        self.wait_for_ready()
        return self.read_array_slice(var_name, start, count)

    def get_edges_default_window(self, var_name: str = "EdgeB", preferred: int = 10) -> List[float]:
        self.wait_for_ready()
        n = self.discover_length(var_name)
        if n == 0:
            return []
        count = min(preferred, n)
        return self.read_array_slice(var_name, 0, count)

       
    #used to get the array from controller to the GUI
    def upload_array(self, name: str, first: int, last: int) -> List[float]:
        # """Read controller array [first..last] as floats.

        # Prefers gclib GArrayUpload when available; falls back to chunked MG reads.
        # """
        if first > last:
            return []
        if not self._driver or not self._connected:
            raise RuntimeError("No controller connected")

        # Prefer GArrayUpload if available on the driver
        if hasattr(self._driver, "GArrayUpload"):
            try:
                text = getattr(self._driver, "GArrayUpload")(name, first, last, 1)
                tokens = [tok.strip() for tok in str(text).replace("\r", " ").replace("\n", " ").split(",") if tok.strip()]
                return [float(tok) for tok in tokens][: (last - first + 1)]
            except Exception:
                # Fall through to MG-based approach
                pass

        # Fallback: use MG in safe chunks
        out: List[float] = []
        i = first
        while i <= last:
            count = min(32, last - i + 1)
            refs = ", ".join(f"{name}[{j}]" for j in range(i, i + count))
            resp = self.cmd("MG " + refs).strip()
            parts = resp.replace("\r", " ").replace("\n", " ").split()
            out.extend(float(p) for p in parts)
            i += count
        return out[: (last - first + 1)]
    
    #used to get the array from GUI to controller
    def download_array(self, name: str, first: int, values: Sequence[float]) -> int:
        # """
        # Write Python values → controller array starting at index `first`.

        # Prefers gclib GArrayDownload when available; falls back to chunked assignments.
        # Returns the number of elements written.
        # """
        if not values:
            return 0
        if not self._driver or not self._connected:
            raise RuntimeError("No controller connected")

        n = len(values)
        last = first + n - 1

        # --- Fast path: try GArrayDownload on the driver ----------------------
        fn = getattr(self._driver, "GArrayDownload", None)
        if callable(fn):
            ascii_payload = ",".join(str(v) for v in values)
            # Try common Python wrapper variants in order:
            #  - Some wrappers accept ASCII directly: (name, first, last, ascii_payload)
            #  - Some accept a delimiter flag too:     (name, first, last, 1, ascii_payload)
            #  - Some want raw binary doubles buffer:  (name, first, last, bytes)
            # We attempt these patterns; if all fail, we fall back to GCommand.
            try:
                fn(name, first, last, ascii_payload)  # ASCII, no delimiter arg
                return n
            except Exception:
                try:
                    fn(name, first, last, 1, ascii_payload)  # ASCII with delimiter flag
                    return n
                except Exception:
                    try:
                        import struct
                        buf = struct.pack("<" + "d" * n, *values)  # little-endian doubles
                        fn(name, first, last, buf)  # binary buffer
                        return n
                    except Exception:
                        pass  # fall through to MG-based approach

        # --- Fallback: send assignments via GCommand in safe chunks ----------
        # Build assignments like:  Arr[0]=1.23;Arr[1]=4.56;...
        written = 0
        line = ""
        for i, v in enumerate(values):
            cmd = f"{name}[{first + i}]={v}"
            # keep command lines comfortably short for the DMC parser
            if len(line) + len(cmd) + 1 < 300:
                line = f"{line};{cmd}" if line else cmd
            else:
                self.cmd(line)
                written += line.count("=")  # number of assignments we just sent
                line = cmd
        if line:
            self.cmd(line)
            written += line.count("=")
        return written    


if __name__ == "__main__":  # Minimal integration demo
    import os
    addr = os.environ.get("DMC_ADDRESS", "")
    c = GalilController()
    if not addr:
        print("Set DMC_ADDRESS to controller address (e.g., 192.168.0.2)")
    else:
        if c.connect(addr):
            try:
                c.wait_for_ready()
                b0 = c.read_edge_b(0)
                c0 = c.read_edge_c(0)
                print(f"EdgeB[0]={b0}, EdgeC[0]={c0}")
                window_b = c.get_edges_default_window("EdgeB")
                window_c = c.get_edges_default_window("EdgeC")
                print("EdgeB[0:10]", window_b)
                print("EdgeC[0:10]", window_c)
            finally:
                c.disconnect()

    def write_array(self, name: str, updates: dict[int, float]) -> None:
        # Chunk to approximately 300 chars per command line
        items = sorted((idx, val) for idx, val in updates.items())
        line = ""
        for i, v in enumerate(values):
            cmd = f"{name}[{first + i}]={v}"
            # keep command lines comfortably short for the DMC parser
            if len(line) + len(cmd) + 1 < 300:
                line = f"{line};{cmd}" if line else cmd
            else:
                self.cmd(line)
                written += line.count("=")  # number of assignments we just sent
                line = cmd
        if line:
            self.cmd(line)
            written += line.count("=")
        return written 
