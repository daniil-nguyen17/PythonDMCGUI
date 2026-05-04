from __future__ import annotations

import logging
import sys as _sys
import time
from typing import Any, Dict, List, Optional, Sequence

from .utils.transport import CommError

# Optional transport layer (may reference driver protocol defined below)

#get logger for messages
logger = logging.getLogger(__name__)
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
        global_dmc = gclib.py()
    except Exception as e:  # pragma: no cover
        logger.error("Failed to create gclib handle: %s", e)
        global_dmc = None  # type: ignore
else:
    global_dmc = None  # type: ignore


class GalilDriverProtocol:
    """Minimal protocol so we can mock in tests.

    Real implementation is gclib.py handle with GOpen/GClose/GCommand.
    """

    def GOpen(self, address: str) -> None:  # noqa: N802 (Galil API name)
        """Open connection to a Galil controller at *address*."""
        ...

    def GClose(self) -> None:  # noqa: N802
        """Close the controller connection."""
        ...

    def GCommand(self, cmd: str) -> str:  # noqa: N802
        """Send *cmd* to the controller and return the response string."""
        ...


class ControllerNotReadyError(Exception):
    """Raised when the controller is not ready to respond to array or status reads."""

# Backward-compat aliases — external code may catch these names
ControllerNotReady = ControllerNotReadyError


class IndexOutOfRangeError(Exception):
    """Raised when an array index exceeds the declared max edges limit."""

# Backward-compat alias
IndexOutOfRange = IndexOutOfRangeError


class ParseError(Exception):
    """Raised when a controller response cannot be parsed as a float."""



MAX_EDGES_DEFAULT = 250

# Flags appended to every GOpen address string for the primary command handle.
# --direct: bypass gclib connection broker for a direct low-latency channel.
# --timeout 1000: allow 1 second before raising a communication error.
# -MG 0: do NOT subscribe to MG (message) output on this handle (Linux gclib
#   does not support this flag — only append on Windows).
PRIMARY_FLAGS: str = (
    "--direct --timeout 1000 -MG 0" if _sys.platform == "win32"
    else "--direct --timeout 1000"
)

FLOAT_CHARS = set("0123456789+-.eE")


class GalilController:
    """High-level interface to a Galil DMC controller.

    Wraps the gclib handle with connection management, command dispatch,
    array upload/download, and edge-array APIs. All public methods are safe
    to call from the jobs worker thread; they must NOT be called from the
    Kivy main thread during active polling (TCP contention).

    Inject a mock GalilDriverProtocol in tests to avoid requiring gclib.
    """

    def __init__(self, driver: Optional[GalilDriverProtocol] = None) -> None:
        self._driver = driver
        self._connected = False
        self._logger: Optional[callable] = None
        self._max_edges: int = MAX_EDGES_DEFAULT
        self._transport = None
        self._address: str = ""

    #logging
    def set_logger(self, fn: Optional[callable]) -> None:
        """Register a callable for user-visible log messages from the controller.

        Args:
            fn: Callable(message: str) that receives log output, or None to disable.
        """
        self._logger = fn

    # Populates and discovers a list of connected addresses
    def list_addresses(self) -> Dict[str, str]:
        """Return mapping of address -> description/revision if available.

        Uses gclib GAddresses when the underlying driver implements it.
        """
        drv = self._driver
        if drv is None:
            if not GCLIB_AVAILABLE:
                logger.error("GAddresses unavailable: gclib not installed")
                return {}
            try:
                drv = gclib.py()
            except Exception as e:  # pragma: no cover
                logger.error("GAddresses unavailable: %s", e)
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
            logger.error("list_addresses error: %s", e)
            return {}

    @staticmethod
    def _strip_flags(address: str) -> str:
        """Extract the bare IP/hostname from an address that may include gclib flags.

        GAddresses() returns strings like '100.100.100.2 -d' where '-d' is the
        --direct flag.  We append our own PRIMARY_FLAGS, so any existing flags
        must be stripped to avoid duplicates or conflicts.
        """
        parts = address.strip().split()
        # Keep only the first token (IP or hostname); drop anything starting with '-'
        bare = parts[0] if parts else address.strip()
        return bare

    # Establishes connection to controller
    def connect(self, address: str) -> bool:
        """Open a gclib handle to the controller at *address*.

        Strips any existing flags from *address* (e.g. "-d") before appending
        PRIMARY_FLAGS. Sends ``CW2,1`` after connect to put the controller in
        third-party device mode so MG output does not stall program execution.

        Args:
            address: Controller IP/hostname, optionally with gclib flags.

        Returns:
            True on success; False if gclib is unavailable or GOpen fails.
        """
        if self._driver is None:
            if not GCLIB_AVAILABLE:
                logger.error("Failed to connect: gclib not installed")
                return False
            try:
                self._driver = gclib.py()
            except Exception as e:  # pragma: no cover
                logger.error("Failed to create gclib driver: %s", e)
                return False
        bare_addr = self._strip_flags(address)
        try:
            self._driver.GOpen(f"{bare_addr} {PRIMARY_FLAGS}")
            self._connected = True
            self._address = bare_addr  # Store bare address (without flags) for reset_handle / MG handle
            # CW2,1: third-party device mode + continue on buffer full.
            #   n0=2: normal ASCII on unsolicited messages (no MSB mangling).
            #   n1=1: controller continues executing the DMC program even if
            #         the message output buffer fills up (drops characters
            #         instead of stalling the program).
            # Without this the controller defaults to CW1,0 — Galil Driver
            # mode where MSB is set on MG output AND program execution pauses
            # when the buffer is full, causing commands to queue until #AUTO
            # re-enters its polling loop.
            try:
                self._driver.GCommand("CW2,1")
            except Exception:
                pass  # best-effort; some firmware revisions may not need it
            if self._logger:
                try:
                    self._logger(f"[CTRL] Connected to {address} --direct, timeout=1000ms")
                except Exception:
                    pass
            return True
        except Exception as e:
            logger.error("connect error: %s", e)
            self._connected = False
            return False

    #disconnects from controller
    def disconnect(self) -> None:
        """Close the gclib handle and reset connected state.

        Safe to call when already disconnected. After disconnect, the next
        call to connect() creates a fresh driver handle.
        """
        if self._driver is None:
            return
        try:
            self._driver.GClose()
        except Exception:
            pass
        finally:
            self._connected = False
            self._driver = None  # allow connect() to create a fresh handle on reconnect
            if self._logger:
                try:
                    self._logger("Disconnected")
                except Exception:
                    pass

    def reset_handle(self, address: Optional[str] = None) -> bool:
        """Close and reopen the gclib handle without going through a full disconnect/reconnect.

        Used by E-STOP recovery path to reset controller state while preserving the
        connection to the same address. Does NOT call disconnect() — the handle stays
        associated with the same GalilController instance.

        Args:
            address: Controller address. If None, uses the last connected address.

        Returns:
            True on success (_connected stays/becomes True).
            False on failure (_connected set to False).
        """
        addr = address or self._address
        if not addr:
            return False
        try:
            self._driver.GClose()
            self._driver.GOpen(f"{addr} {PRIMARY_FLAGS}")
            self._connected = True
            # Re-issue CW2,1 after handle reset (see connect() for rationale).
            try:
                self._driver.GCommand("CW2,1")
            except Exception:
                pass
            return True
        except Exception as e:
            logger.error("reset_handle error: %s", e)
            self._connected = False
            return False

    # used to check if connected in active paths
    def is_connected(self) -> bool:
        """Return True if the controller handle is currently open."""
        return self._connected

    def read_status(self) -> Dict[str, Any]:
        """Read controller status including position and speed information."""
        if not self._driver or not self._connected:
            raise RuntimeError("No controller connected")

        try:
            # Read position for all axes (reduced debug output)
            pos = {}
            for axis in ['A', 'B', 'C', 'D']:
                try:
                    resp = self.cmd(f"MG _TP{axis}")
                    pos[axis] = float(resp.strip())
                except Exception:
                    pos[axis] = 0.0

            # Read speed (using _TSA as an example - adjust based on your controller setup)
            try:
                speed_resp = self.cmd("MG _TSA")
                speed = float(speed_resp.strip())
            except Exception:
                speed = 0.0

            return {
                "pos": pos,
                "speeds": speed
            }
        except Exception as e:
            if self._logger:
                try:
                    self._logger(f"Status read error: {e}")
                except Exception:
                    pass
            raise RuntimeError(f"Failed to read status: {e}")

    # Used to input commands to the controller, ESTOP uses this
    def cmd(self, command: str) -> str:
        """Send a DMC command and return the response string.

        Status-polling commands (MG _TP*, MG hmi*, etc.) are not logged to
        avoid flooding the log at 10 Hz. All other commands are logged at DEBUG.
        On error, attempts ``TC1`` to retrieve the controller error code before
        raising RuntimeError.

        Args:
            command: DMC command string (e.g. ``"MG _TPA"`` or ``"ST ABCD"``).

        Returns:
            Raw response string from the controller.

        Raises:
            RuntimeError: If the controller is not connected or the command fails.
        """
        if not self._driver or not self._connected:
            # Surface a clear message to UI when called while disconnected
            if self._logger:
                try:
                    self._logger("No controller connected")
                except Exception:
                    pass
            raise RuntimeError("No controller connected")
        try:
            # Completely suppress debug output for status polling commands
            # Also suppress poller-frequency MG commands to avoid 10 Hz log flood
            is_status_command = (command.startswith("MG _TP") or command.startswith("MG _TS")
                                 or command.startswith("MG hmi") or command.startswith("MG ct")
                                 or command.startswith("MG _XQ")
                                 or command.startswith("MG aPos") or command.startswith("MG bPos")
                                 or command.startswith("MG cPos") or command.startswith("MG dPos"))
            if not is_status_command:
                logger.debug("Sending command: %s", command)
            resp = self._driver.GCommand(command)
            if not is_status_command:
                logger.debug("Response: %s", resp.strip())
                if self._logger:
                    try:
                        self._logger(f"CMD {command} -> {resp.strip()}")
                    except Exception:
                        pass
            return resp
        except Exception as e:
            logger.warning("Command failed: %s -> %s", command, e)
            # Try to fetch error string
            try:
                tc1 = self._driver.GCommand("TC1")
                logger.warning("TC1 error code: %s", tc1)
            except Exception:
                tc1 = str(e)
                logger.warning("Could not get TC1: %s", tc1)
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
        """Read controller array *name*[first..last] as a list of floats.

        Prefers gclib GArrayUpload when available; falls back to chunked MG reads
        with adaptive chunk-size reduction on parse errors.

        Args:
            name: Controller array variable name (e.g. ``"EdgeB"``).
            first: First index to read (inclusive).
            last: Last index to read (inclusive).

        Returns:
            List of floats with at most (last - first + 1) elements.

        Raises:
            RuntimeError: If not connected.
            ControllerNotReadyError: If the array is not declared on the controller.
        """
        logger.debug("upload_array called: name=%s, first=%d, last=%d", name, first, last)

        if first > last:
            logger.debug("upload_array: first > last, returning empty list")
            return []
        if not self._driver or not self._connected:
            logger.debug("upload_array: not connected: driver=%s, connected=%s",
                      self._driver is not None, self._connected)
            raise RuntimeError("No controller connected")

        # Prefer GArrayUpload if available on the driver
        if hasattr(self._driver, "GArrayUpload"):
            try:
                text = getattr(self._driver, "GArrayUpload")(name, first, last, 1)
                normalized = str(text).replace("\r", " ").replace("\n", " ")
                tokens = [tok.strip() for tok in normalized.split(",") if tok.strip()]
                return [float(tok) for tok in tokens][: (last - first + 1)]
            except Exception:
                # Fall through to MG-based approach
                pass

        # Fallback: use MG in safe chunks with adaptive sizing
        logger.debug("upload_array: using MG fallback method for %s[%d:%d]", name, first, last)
        out: List[float] = []
        i = first
        chunk_size = 1  # Start with 1 element at a time

        while i <= last:
            count = min(chunk_size, last - i + 1)
            refs = ", ".join(f"{name}[{j}]" for j in range(i, i + count))
            cmd = "MG " + refs

            try:
                resp = self.cmd(cmd).strip()

                if resp == "?":
                    logger.warning("upload_array: got '?' response — array %s not available", name)
                    raise ControllerNotReadyError(f"Array {name} not available")

                parts = resp.replace("\r", " ").replace("\n", " ").split()
                out.extend(float(p) for p in parts)
                i += count

                # If successful with current chunk size, try to increase it for efficiency
                if chunk_size == 1 and count == 1:
                    chunk_size = 2  # Try 2 elements next time

                # Small delay to avoid overwhelming the controller
                import time
                time.sleep(0.01)  # 10ms delay

            except Exception as e:
                if "question mark" in str(e).lower():
                    # Reduce chunk size and retry
                    if chunk_size > 1:
                        chunk_size = max(1, chunk_size // 2)
                        logger.debug("upload_array: reducing chunk size to %d due to error", chunk_size)
                        continue
                    else:
                        # Even 1 element failed, this is a real error
                        raise e
                else:
                    raise e

        result = out[: (last - first + 1)]
        logger.debug("upload_array: returning %d values from %s", len(result), name)
        return result

    #used to get the array from GUI to controller
    def download_array(self, name: str, first: int, values: Sequence[float]) -> int:
        """Write Python values into controller array *name* starting at index *first*.

        Attempts GArrayDownload (three calling conventions) before falling back to
        chunked ``name[idx]=value`` assignments via GCommand. Each chunk is kept
        under 300 characters to fit within DMC parser limits.

        Args:
            name: Controller array variable name (e.g. ``"deltaC"``).
            first: Starting index for the write.
            values: Sequence of floats to write.

        Returns:
            Number of elements written.

        Raises:
            RuntimeError: If not connected.
        """
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
        """Wait until controller is responsive.

        1) Probe a cheap numeric like _TPA
        2) Optionally check for arrays if they exist
        """
        self.ensure_connected()
        end = (time.monotonic() + timeout_s)
        last_err: Optional[Exception] = None
        logger.info("Waiting for controller ready...")
        while time.monotonic() < end:
            try:
                _ = self._parse_float_str(self.cmd("MG _TPA"))
                logger.info("Ready: controller responding")
                return

            except Exception as e:
                last_err = e
                logger.debug("Controller not ready: %s", e)
            time.sleep(poll_s)
        raise ControllerNotReadyError(f"Controller not ready within {timeout_s}s: {last_err}")

    def test_basic_connectivity(self) -> bool:
        """Test if controller responds to basic commands without requiring arrays."""
        try:
            self.ensure_connected()
            _ = self._parse_float_str(self.cmd("MG _TPA"))
            return True
        except Exception as e:
            logger.debug("Basic connectivity test failed: %s", e)
            return False

    def _parse_float_str(self, s: str) -> float:
        """Parse the first numeric token from a controller response string.

        Tries direct float() conversion first, then splits on commas/spaces and
        validates each token against FLOAT_CHARS before converting.

        Args:
            s: Raw response string from GCommand (may have trailing whitespace or commas).

        Returns:
            Parsed float value.

        Raises:
            ParseError: If the string is empty or contains no parsable numeric token.
        """
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
        """Set the maximum array index the edge APIs will read (clamped to >=1).

        Args:
            n: Upper bound on array size. Values below 1 are clamped to 1.
        """
        self._max_edges = max(1, n)

    def ensure_connected(self) -> None:
        """Raise CommError if the controller handle is not currently open."""
        if not self._connected or not self._driver:
            raise CommError("Not connected")

    def _validate_index(self, idx: int) -> None:
        if idx < 0 or idx >= self._max_edges:
            raise IndexOutOfRangeError(f"index {idx} out of range (0..{self._max_edges-1})")

    def read_array_elem(self, var_name: str, idx: int) -> float:
        """Read a single element from a controller array.

        Args:
            var_name: Array variable name on the controller (e.g. ``"EdgeB"``).
            idx: Element index (validated against _max_edges).

        Returns:
            Float value of the element.

        Raises:
            CommError: If not connected.
            IndexOutOfRangeError: If idx is out of bounds.
            ControllerNotReadyError: If the array is not declared or returns ``?``.
        """
        self.ensure_connected()
        self._validate_index(idx)
        cmd = f"MG {var_name}[{idx}]"
        try:
            resp = self.cmd(cmd)
            if resp.strip() == "?":
                logger.warning("read_array_elem: '?' response for %s", cmd)
                raise ControllerNotReadyError(f"Array {var_name} not available")
            return self._parse_float_str(resp)
        except RuntimeError as e:
            # Check if this is a "Bad function or array" error
            if "Bad function or array" in str(e) or "57" in str(e):
                raise ControllerNotReadyError(f"Array {var_name} is not declared on the controller")
            else:
                raise e

    def read_array_slice(self, var_name: str, start: int, count: int) -> List[float]:
        """Read a contiguous slice of a controller array.

        Args:
            var_name: Array variable name.
            start: First index to read.
            count: Number of elements.

        Returns:
            List of floats with exactly *count* elements.

        Raises:
            CommError: If not connected.
            IndexOutOfRangeError: If slice exceeds _max_edges.
        """
        self.ensure_connected()
        if start < 0 or count <= 0:
            raise IndexOutOfRangeError("start/count must be non-negative and count>0")
        if start + count > self._max_edges:
            raise IndexOutOfRangeError(f"slice {start}+{count} exceeds max {self._max_edges}")
        out: List[float] = []
        logger.debug("Reading slice %s[%d:%d]", var_name, start, start + count)
        for i in range(start, start + count):
            out.append(self.read_array_elem(var_name, i))
        return out

    def read_edge_b(self, idx: int) -> float:
        """Read EdgeB[idx] (B-axis segment boundary position in counts).

        Args:
            idx: Segment index.

        Returns:
            Float value of EdgeB[idx].
        """
        return self.read_array_elem("EdgeB", idx)

    def read_edge_c(self, idx: int) -> float:
        """Read EdgeC[idx] (C-axis stone height at the corresponding segment boundary).

        Args:
            idx: Segment index.

        Returns:
            Float value of EdgeC[idx].
        """
        return self.read_array_elem("EdgeC", idx)

    def discover_length(self, var_name: str, probe_max: Optional[int] = None, zero_run: int = 5) -> int:
        """Probe an array to discover how many elements contain non-zero data.

        Reads indices sequentially until *zero_run* consecutive near-zero values
        are found, then returns last_nonzero + 1. Stops at min(_max_edges, probe_max).

        Args:
            var_name: Array name to probe.
            probe_max: Optional upper bound (defaults to _max_edges).
            zero_run: Number of consecutive near-zero values that signals end-of-data.

        Returns:
            Estimated number of populated elements (0 if all zeros).
        """
        self.ensure_connected()
        limit = min(self._max_edges, probe_max or self._max_edges)
        last_nonzero = -1
        zeros = 0
        for i in range(0, limit):
            try:
                val = self.read_array_elem(var_name, i)
            except ControllerNotReadyError:
                break
            if abs(val) < 1e-9:
                zeros += 1
                if zeros >= zero_run and i > 0:
                    logger.debug("discover_length: hit %d zeros at index %d", zero_run, i)
                    break
            else:
                last_nonzero = i
                zeros = 0
        length = max(0, last_nonzero + 1)
        logger.debug("discover_length(%s) -> %d", var_name, length)
        return length

    def get_edges_window(self, var_name: str, start: int, count: int) -> List[float]:
        """Wait for controller ready, then return a slice of an edge array.

        Args:
            var_name: Edge array name (e.g. ``"EdgeB"``).
            start: First index.
            count: Number of elements to read.

        Returns:
            List of float values.
        """
        self.wait_for_ready()
        return self.read_array_slice(var_name, start, count)

    def get_edges_default_window(self, var_name: str = "EdgeB", preferred: int = 10) -> List[float]:
        """Wait for ready, discover array length, and return up to *preferred* elements.

        Args:
            var_name: Edge array name (defaults to ``"EdgeB"``).
            preferred: Maximum number of elements to return.

        Returns:
            List of floats, empty if array has no non-zero data.
        """
        self.wait_for_ready()
        n = self.discover_length(var_name)
        if n == 0:
            return []
        count = min(preferred, n)
        return self.read_array_slice(var_name, 0, count)

    def diagnose_controller_state(self) -> None:
        """Log a diagnostic snapshot of controller state and available arrays.

        Queries _TPA, _XQ, and common array names (EdgeB, EdgeC, etc.) via MG
        and writes results to the module logger at INFO/DEBUG level. Used during
        development and troubleshooting; not called in normal operation.
        """
        logger.info("=== Controller Diagnostics ===")

        try:
            if not self.is_connected():
                logger.info("diagnose: not connected")
                return

            # Check basic controller status
            try:
                resp = self.cmd("MG _TPA")
                logger.info("diagnose: TPA = %s", resp.strip())
            except Exception as e:
                logger.warning("diagnose: failed to get TPA: %s", e)

            # Check if DMC program is running
            try:
                resp = self.cmd("MG _XQ")
                logger.info("diagnose: program execution status = %s", resp.strip())
            except Exception as e:
                logger.warning("diagnose: failed to get execution status: %s", e)

            # Try to probe some common array patterns
            test_arrays = ["EdgeB", "EdgeC", "EDGEB", "EDGEC", "edgeb", "edgec"]
            for array_name in test_arrays:
                try:
                    resp = self.cmd(f"MG {array_name}[0]").strip()
                    if resp != "?":
                        logger.info("diagnose: found array %s[0] = %s", array_name, resp)
                    else:
                        logger.debug("diagnose: array %s not available", array_name)
                except Exception as e:
                    logger.warning("diagnose: error checking %s: %s", array_name, e)

            logger.info("=== End Diagnostics ===")

        except Exception as e:
            logger.error("diagnose: diagnostics failed: %s", e)
    def get_array_len(self, name: str) -> int:
        """Return the DM-defined length of array *name* using ``MG name[-1]``.

        Args:
            name: Controller array variable name.

        Returns:
            Integer length as declared by the DM (Dimension) command.

        Raises:
            RuntimeError: If not connected or the response cannot be parsed.
        """
        if not self._driver or not self._connected:
            raise RuntimeError("No controller connected")
        raw = self._driver.GCommand(f"MG {name}[-1]").strip()
        # MG returns a float-formatted string (e.g., "150.0000")
        try:
            return int(float(raw))
        except Exception as e:
            raise RuntimeError(f"Failed to read length of {name}: {raw!r}") from e

    def upload_array_auto(self, name: str) -> List[float]:
        """Upload the entire array without knowing its size in advance.

        Queries the array length via get_array_len, then reads all elements.
        Prefers GArrayUpload(-1,-1) if the driver wrapper supports it.

        Args:
            name: Controller array variable name.

        Returns:
            List of floats containing all declared array elements.

        Raises:
            RuntimeError: If not connected.
        """
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
        """Write *values* into name[0..len(values)-1] without passing explicit indices.

        Convenience wrapper over download_array. Tries GArrayDownload first
        (three calling conventions), then falls back to chunked GCommand writes.

        Args:
            name: Controller array variable name.
            values: Sequence of floats to write starting at index 0.

        Returns:
            Number of elements written.

        Raises:
            RuntimeError: If not connected.
        """
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

    def write_array(self, name: str, updates: dict[int, float]) -> int:
        # Chunk to approximately 300 chars per command line
        items = sorted((idx, val) for idx, val in updates.items())
        line = ""
        written = 0
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
