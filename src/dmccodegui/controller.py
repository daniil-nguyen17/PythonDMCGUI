from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

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

MAX_EDGES_DEFAULT = 150


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
