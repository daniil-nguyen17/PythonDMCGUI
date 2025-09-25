from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Sequence
from .utils.transport import GalilTransport, CommError


# Optional transport layer (may reference driver protocol defined below)

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



MAX_EDGES_DEFAULT = 250

FLOAT_CHARS = set("0123456789+-.eE")


class GalilController:
    
    def __init__(self, driver: Optional[GalilDriverProtocol] = None) -> None:
        self._driver = driver
        self._connected = False
        self._logger: Optional[callable] = None
        self._max_edges: int = MAX_EDGES_DEFAULT

    #logging
    def set_logger(self, fn: Optional[callable]) -> None:
        self._logger = fn

    # Populates and discovers a list of connected addresses
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

    # Establishes connection to controller
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
    
    #disconnects from controller
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
   
    # used to check if connected in active paths
    def is_connected(self) -> bool:
        return self._connected

    # Used to input commands to the controller, ESTOP uses this
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

# used to determine if a working connection exists at startup
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

       
    #used to get the array from controller to the GUI
    def upload_array(self, name: str, first: int, last: int) -> List[float]:
        # """Read controller array [first..last] as floats.

        # Prefers gclib GArrayUpload when available; falls back to chunked MG reads.
        # """
        print(f"[CTRL] upload_array called: name={name}, first={first}, last={last}")
        
        if first > last:
            print(f"[CTRL] first > last, returning empty list")
            return []
        if not self._driver or not self._connected:
            print(f"[CTRL] Not connected: driver={self._driver is not None}, connected={self._connected}")
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
        print(f"[CTRL] Using MG fallback method")
        out: List[float] = []
        i = first
        while i <= last:
            count = min(32, last - i + 1)
            refs = ", ".join(f"{name}[{j}]" for j in range(i, i + count))
            cmd = "MG " + refs
            print(f"[CTRL] Sending command: {cmd}")
            resp = self.cmd(cmd).strip()
            print(f"[CTRL] Response: '{resp}'")
            
            if resp == "?":
                print(f"[CTRL] Got '?' response - array {name} not available")
                raise ControllerNotReady(f"Array {name} not available")
            
            parts = resp.replace("\r", " ").replace("\n", " ").split()
            print(f"[CTRL] Parsed parts: {parts}")
            out.extend(float(p) for p in parts)
            i += count
        
        result = out[: (last - first + 1)]
        print(f"[CTRL] Returning {len(result)} values: {result}")
        return result
    
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

    def _parse_float_str(s: str) -> float:
        t = s.strip()
        if not t:
            raise ParseError(f"Empty string: '{s}'")
        
        # Try direct float conversion first
        try:
            return float(t)
        except ValueError:
            pass
        
        # Fall back to parsing comma/space separated values and take first
        try:
            # Split on common delimiters and take first numeric value
            parts = t.replace(',', ' ').split()
            for part in parts:
                part = part.strip()
                if part and all(ch in FLOAT_CHARS for ch in part):
                    return float(part)
            raise ValueError("no numeric values found")
        except Exception as e:
            raise ParseError(f"Parse error for '{s}': {e}")

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

    def diagnose_controller_state(self) -> None:
        """Diagnose controller state and available arrays."""
        print(f"[CTRL] === Controller Diagnostics ===")
        
        try:
            if not self.is_connected():
                print(f"[CTRL] Not connected")
                return
            
            # Check basic controller status
            print(f"[CTRL] Checking basic controller status...")
            try:
                resp = self.cmd("MG _TPA")
                print(f"[CTRL] Controller time: {resp.strip()}")
            except Exception as e:
                print(f"[CTRL] Failed to get controller time: {e}")
            
            # Check if DMC program is running
            try:
                resp = self.cmd("MG _XQ")
                print(f"[CTRL] Program execution status: {resp.strip()}")
            except Exception as e:
                print(f"[CTRL] Failed to get execution status: {e}")
            
            # Try to probe some common array patterns
            test_arrays = ["EdgeB", "EdgeC", "EDGEB", "EDGEC", "edgeb", "edgec"]
            for array_name in test_arrays:
                try:
                    resp = self.cmd(f"MG {array_name}[0]").strip()
                    if resp != "?":
                        print(f"[CTRL] Found array {array_name}[0] = {resp}")
                    else:
                        print(f"[CTRL] Array {array_name} not available")
                except Exception as e:
                    print(f"[CTRL] Error checking {array_name}: {e}")
            
            print(f"[CTRL] === End Diagnostics ===")
            
        except Exception as e:
            print(f"[CTRL] Diagnostics failed: {e}")
    def get_array_len(self, name: str) -> int:
        #"""Return the DM-defined length of array `name` (MG name[-1])."""
        if not self._driver or not self._connected:
            raise RuntimeError("No controller connected")
        raw = self._driver.GCommand(f"MG {name}[-1]").strip()
        # MG returns a float-formatted string (e.g., "150.0000")
        try:
            return int(float(raw))
        except Exception as e:
            raise RuntimeError(f"Failed to read length of {name}: {raw!r}") from e

    def upload_array_auto(self, name: str) -> List[float]:
        #"""Upload the entire array without knowing its size in advance."""
        if not self._driver or not self._connected:
            raise RuntimeError("No controller connected")

        # Fast path: try GArrayUpload(name, -1, -1) if wrapper supports it
        fn = getattr(self._driver, "GArrayUpload", None)
        if callable(fn):
            try:
                # Some wrappers return a list already; others return a CSV/text
                data = fn(name, -1, -1)
                if isinstance(data, list):
                    return [float(x) for x in data]
                text = str(data).replace("\r", " ").replace("\n", " ")
                toks = [t for t in (tok.strip() for tok in text.split(",")) if t]
                return [float(t) for t in toks]
            except Exception:
                pass  # fall back to length+MG

        # Fallback: query length, then read 0..len-1 in chunks
        n = self.get_array_len(name)
        if n <= 0:
            return []
        return self.upload_array(name, 0, n - 1)  # your working method
    
    def download_array_full(self, name: str, values: Sequence[float]) -> int:
        #"""Write `values` into name[0..len(values)-1] without passing indices."""
        if not self._driver or not self._connected:
            raise RuntimeError("No controller connected")
        if not values:
            return 0

        # Prefer native GArrayDownload if available
        fn = getattr(self._driver, "GArrayDownload", None)
        if callable(fn):
            ascii_payload = ",".join(str(v) for v in values)
            try:
                fn(name, ascii_payload)                 # (name, data)
                return len(values)
            except Exception:
                try:
                    fn(name, 0, len(values) - 1, 1, ascii_payload)  # (name, first,last,delim,data)
                    return len(values)
                except Exception:
                    try:
                        import struct
                        buf = struct.pack("<" + "d"*len(values), *values)
                        fn(name, 0, len(values) - 1, buf)  # (name, first,last,bytes)
                        return len(values)
                    except Exception:
                        pass  # fall through to command-assignments

        # Fallback: chunked assignments via command line
        return self.download_array(name, 0, values)  # reuse your existing writer

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
        for idx, val in items:
            cmd = f"{name}[{idx}]={val}"
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
