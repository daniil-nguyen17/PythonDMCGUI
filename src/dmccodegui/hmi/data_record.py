"""DataRecordListener — UDP-based data record streaming from Galil DMC-4000.

Replaces ControllerPoller (MG-based TCP polling) with Data Record (DR)
streaming over a separate UDP socket.  The TCP command channel is never
used for polling — only for button presses and parameter changes.

Background
----------
Galil support (case #767944) confirmed that MG-based polling at 10 Hz
causes race conditions: button commands queue behind polls on the shared
TCP handle.  The DR approach streams a binary status packet over UDP,
eliminating all command-channel contention.

Setup requirements
------------------
The DMC program must run a #ZALOOP thread that continuously copies user
variables into ZA slots::

    #ZALOOP
    ZAA=hmiState
    ZAB=ctSesKni
    ZAC=ctStnKni
    ZAD=startPtC
    WT 10
    JP#ZALOOP

This thread must be started in #AUTO: ``XQ#ZALOOP,3``

Threading model
---------------
- ``start()`` sends IH + DR commands over TCP (one-shot, via controller.cmd)
- Background thread blocks on ``socket.recv()`` with 4 s timeout
- Parsed values are posted to the Kivy main thread via ``Clock.schedule_once``
- ``_apply_to_state()`` runs on main thread — the ONLY place that writes MachineState
- ``stop()`` sends DR 0 + IH close over TCP, then joins the thread

Data record format
------------------
Binary little-endian packet.  Byte offsets are calculated dynamically from
the QZ command at start time.  See ``calculate_offsets()`` for the formula
and ``docs/data-record-migration.md`` for the full byte map.
"""
from __future__ import annotations

import logging
import socket
import struct
import threading
import time
from typing import TYPE_CHECKING, Optional

from kivy.clock import Clock

from .dmc_vars import (
    DR_DISCONNECT_TIMEOUT,
    DR_RATE_GRIND,
    DR_RATE_NORMAL,
    DR_UDP_PORT,
    STATE_GRINDING,
)
from ..utils import jobs

if TYPE_CHECKING:
    from ..app_state import MachineState
    from ..controller import GalilController

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_hmi_ip(controller_ip: str) -> str:
    """Find local IP address on the same subnet as the controller.

    Opens a UDP socket "connected" to the controller (no traffic sent),
    then reads the local address the OS chose for routing.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((controller_ip, 80))
        return s.getsockname()[0]
    finally:
        s.close()


def calculate_offsets(qz_response: str, actual_packet: bytes | None = None) -> dict[str, int]:
    """Parse QZ response and return byte offsets for data record fields.

    QZ returns: ``num_axes, general_bytes, coord_bytes, axis_bytes``
    Example:    ``4, 52, 26, 36``

    The actual packet size is read from header bytes 2-3 of the first DR
    packet (little-endian UW).  The axis blocks start at
    ``total_size - n_axes * axis_bytes``.  This avoids guessing how many
    coordinate-plane blocks (S/T) are present in the general section.

    If *actual_packet* is None, total_size is estimated from the QZ fields.

    Returns a dict with keys like ``'sample_num'``, ``'thread_status'``,
    ``'A_aux_pos'`` (_TDA), ``'A_za'`` (ZAA), etc.
    """
    parts = [s.strip() for s in qz_response.split(",")]
    n_axes = int(parts[0])
    general_bytes = int(parts[1])
    coord_bytes = int(parts[2])
    axis_bytes = int(parts[3])

    header_size = 4
    offsets: dict[str, int] = {}

    # Determine total size from actual packet header (bytes 2-3) if available
    if actual_packet is not None and len(actual_packet) >= 4:
        total_size = struct.unpack_from("<H", actual_packet, 2)[0]
    else:
        # Estimate — may be wrong if only one coord plane is present
        total_size = header_size + general_bytes + 2 * coord_bytes + n_axes * axis_bytes

    # Axis blocks are always at the END of the record
    axis_base = total_size - n_axes * axis_bytes

    # Sample number is always at bytes 4-5
    offsets["sample_num"] = header_size

    # Thread status is at a fixed position within the general block
    offsets["thread_status"] = 51

    axis_letters = ["A", "B", "C", "D", "E", "F", "G", "H"][:n_axes]
    for i, axis in enumerate(axis_letters):
        base = axis_base + i * axis_bytes
        offsets[f"{axis}_status"] = base          # UW (2 bytes)
        offsets[f"{axis}_switches"] = base + 2    # UB
        offsets[f"{axis}_stop_code"] = base + 3   # UB
        offsets[f"{axis}_ref_pos"] = base + 4     # SL (_RP)
        offsets[f"{axis}_mot_pos"] = base + 8     # SL (_TP)
        offsets[f"{axis}_pos_err"] = base + 12    # SL (_TE)
        offsets[f"{axis}_aux_pos"] = base + 16    # SL (_TD) — we read this
        offsets[f"{axis}_velocity"] = base + 20   # SL
        offsets[f"{axis}_torque"] = base + 24     # SL
        offsets[f"{axis}_analog"] = base + 28     # SW/UW
        offsets[f"{axis}_hall"] = base + 30        # UB
        offsets[f"{axis}_za"] = base + 32         # SL (user variable)

    offsets["total_size"] = total_size
    offsets["n_axes"] = n_axes
    offsets["axis_bytes"] = axis_bytes

    return offsets


def find_available_handle(th_response: str) -> tuple[str, int]:
    """Parse TH output and return the first available handle.

    TH output contains lines like:
        IHA TCP PORT 1050 TO IP ADDRESS ...
        IHG AVAILABLE
        IHH AVAILABLE

    Returns (letter, index) e.g. ("G", 6).
    Raises RuntimeError if no handle is available.
    """
    for line in th_response.strip().split("\n"):
        line = line.strip()
        if "AVAILABLE" in line.upper():
            # Extract handle letter: "IHG AVAILABLE" → "G"
            for i, ch in enumerate(line):
                if ch == "H" and i > 0 and line[i - 1] == "I":
                    letter = line[i + 1]
                    index = ord(letter.upper()) - ord("A")
                    return letter.upper(), index
    raise RuntimeError("No available Ethernet handle on controller (all 8 in use)")


def _ip_to_bytes_str(ip: str) -> str:
    """Convert '192.168.0.10' → '192,168,0,10' for IH command."""
    return ip.replace(".", ",")


# ---------------------------------------------------------------------------
# DataRecordListener
# ---------------------------------------------------------------------------

class DataRecordListener:
    """UDP listener for DMC-4000 data record streaming.

    Replaces ControllerPoller entirely.  The controller pushes binary
    data record packets over UDP; this class receives, parses, and
    writes to MachineState on the Kivy main thread.

    Lifecycle::

        listener = DataRecordListener(state)
        listener.start(controller, hmi_ip)   # sends IH + DR commands
        listener.stop(controller)             # sends DR 0 + IH close

    The TCP command channel is never used for polling — only for the
    one-shot IH/DR setup commands and adaptive rate changes.
    """

    def __init__(self, state: MachineState, port: int = DR_UDP_PORT) -> None:
        self._state = state
        self._port = port
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Discovered at start() time
        self._handle_letter: str = ""
        self._handle_index: int = -1
        self._offsets: dict[str, int] = {}
        self._qz_raw: str = ""  # Stored for recalculating offsets from first packet
        self._offsets_calibrated: bool = False
        self._current_rate: int = DR_RATE_NORMAL
        self._controller_ref: Optional[GalilController] = None

        # Track state for grind-end detection
        self._prev_dmc_state: int = 0

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------

    def is_running(self) -> bool:
        """Return True if the listener thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    def start(self, controller: GalilController, hmi_ip: str) -> None:
        """Open UDP socket, send IH + DR commands, start listener thread.

        Args:
            controller: GalilController with an active TCP connection.
            hmi_ip: Local IP address of the HMI on the controller's subnet.
        """
        if self.is_running():
            logger.warning("[DR] start() called while already running")
            return

        self._controller_ref = controller
        self._stop_event.clear()

        # 1. Query QZ for dynamic byte offsets (will be recalibrated from first packet)
        try:
            qz_raw = controller.cmd("QZ").strip()
            self._qz_raw = qz_raw
            self._offsets = calculate_offsets(qz_raw)
            self._offsets_calibrated = False
            logger.info("[DR] QZ response: %s → %d axes, estimated %d bytes",
                        qz_raw, self._offsets["n_axes"],
                        self._offsets["total_size"])
        except Exception as e:
            logger.error("[DR] Failed to query QZ: %s", e)
            return

        # 2. Find an available handle
        try:
            th_raw = controller.cmd("TH")
            self._handle_letter, self._handle_index = find_available_handle(th_raw)
            logger.info("[DR] Using handle %s (index %d) for DR streaming",
                        self._handle_letter, self._handle_index)
        except Exception as e:
            logger.error("[DR] Failed to find available handle: %s", e)
            return

        # 3. Open UDP socket
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind(("0.0.0.0", self._port))
            self._sock.settimeout(DR_DISCONNECT_TIMEOUT)
            logger.info("[DR] UDP socket bound to 0.0.0.0:%d", self._port)
        except Exception as e:
            logger.error("[DR] Failed to open UDP socket: %s", e)
            self._sock = None
            return

        # 4. Send IH command: open UDP handle on controller → HMI
        ip_bytes = _ip_to_bytes_str(hmi_ip)
        ih_cmd = f"IH{self._handle_letter}={ip_bytes}<{self._port}>1"
        try:
            controller.cmd(ih_cmd)
            logger.info("[DR] Sent: %s", ih_cmd)
        except Exception as e:
            logger.error("[DR] IH command failed: %s", e)
            self._close_socket()
            return

        # Small delay for controller to establish UDP handle
        time.sleep(0.3)

        # 5. Send DR command: start streaming
        self._current_rate = DR_RATE_NORMAL
        dr_cmd = f"DR {self._current_rate},{self._handle_index}"
        try:
            controller.cmd(dr_cmd)
            logger.info("[DR] Sent: %s (%.0f Hz)", dr_cmd,
                        1000.0 / self._current_rate)
        except Exception as e:
            logger.error("[DR] DR command failed: %s", e)
            self._close_socket()
            return

        # 6. Start listener thread
        self._thread = threading.Thread(
            target=self._listener_loop,
            name="dr-listener",
            daemon=True,
        )
        self._thread.start()

    def stop(self, controller: GalilController) -> None:
        """Send DR 0 + close IH, stop listener thread, close socket."""
        # Signal thread to stop
        self._stop_event.set()

        # Send DR 0 to stop streaming (best-effort)
        if controller.is_connected():
            try:
                controller.cmd("DR 0")
                logger.info("[DR] Sent: DR 0 (stop streaming)")
            except Exception:
                pass

            # Close the IH handle
            if self._handle_letter:
                try:
                    controller.cmd(f"IH{self._handle_letter}=>-1")
                    logger.info("[DR] Closed handle %s", self._handle_letter)
                except Exception:
                    pass

        # Join thread
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None

        self._close_socket()
        self._controller_ref = None

    # ------------------------------------------------------------------
    # Adaptive rate
    # ------------------------------------------------------------------

    def _check_rate_change(self, dmc_state: int) -> None:
        """Switch DR rate when grinding state changes.

        Called from _parse_and_apply on the listener thread.
        Sends DR command via jobs.submit (TCP, one-shot, no contention).
        """
        grinding = dmc_state == STATE_GRINDING
        target_rate = DR_RATE_GRIND if grinding else DR_RATE_NORMAL

        if target_rate != self._current_rate:
            self._current_rate = target_rate
            handle_idx = self._handle_index

            def _set_rate():
                ctrl = self._controller_ref
                if ctrl and ctrl.is_connected():
                    try:
                        ctrl.cmd(f"DR {target_rate},{handle_idx}")
                        logger.info("[DR] Rate changed to DR %d (%.0f Hz)",
                                    target_rate, 1000.0 / target_rate)
                    except Exception as e:
                        logger.warning("[DR] Rate change failed: %s", e)

            jobs.submit(_set_rate)

    # ------------------------------------------------------------------
    # Listener thread
    # ------------------------------------------------------------------

    def _listener_loop(self) -> None:
        """Background thread: receive UDP packets, parse, update state."""
        logger.info("[DR] Listener thread started")
        while not self._stop_event.is_set():
            try:
                data = self._sock.recv(1024)
                if data:
                    self._parse_and_apply(data)
            except socket.timeout:
                if not self._stop_event.is_set():
                    self._handle_disconnect()
            except OSError:
                # Socket closed (e.g., during stop)
                if not self._stop_event.is_set():
                    logger.warning("[DR] Socket error in listener loop")
                    self._handle_disconnect()
                break
        logger.info("[DR] Listener thread exiting")

    def _parse_and_apply(self, data: bytes) -> None:
        """Parse binary data record and post state update to main thread."""
        # Recalibrate offsets from the first real packet's header (bytes 2-3)
        if not self._offsets_calibrated and len(data) >= 4:
            self._offsets = calculate_offsets(self._qz_raw, actual_packet=data)
            self._offsets_calibrated = True
            logger.info("[DR] Calibrated from packet header: %d bytes, axis base at %d",
                        self._offsets["total_size"],
                        self._offsets["total_size"] - self._offsets["n_axes"] * self._offsets["axis_bytes"])

        offsets = self._offsets
        expected = offsets.get("total_size", 0)

        if len(data) < expected:
            logger.debug("[DR] Short packet: %d bytes (expected %d)",
                         len(data), expected)
            return

        try:
            # Axis positions (_TD — auxiliary/dual encoder)
            a = struct.unpack_from("<i", data, offsets["A_aux_pos"])[0]
            b = struct.unpack_from("<i", data, offsets["B_aux_pos"])[0]
            c = struct.unpack_from("<i", data, offsets["C_aux_pos"])[0]
            d = struct.unpack_from("<i", data, offsets["D_aux_pos"])[0]

            # User variables from ZA slots
            dmc_state = struct.unpack_from("<i", data, offsets["A_za"])[0]   # ZAA = hmiState
            ses_kni = struct.unpack_from("<i", data, offsets["B_za"])[0]     # ZAB = ctSesKni
            stn_kni = struct.unpack_from("<i", data, offsets["C_za"])[0]     # ZAC = ctStnKni
            start_pt_c = struct.unpack_from("<i", data, offsets["D_za"])[0]  # ZAD = startPtC

            # Thread status — bit 0 = thread 0 running → program_running
            thread_status = struct.unpack_from("<B", data, offsets["thread_status"])[0]
            program_running = bool(thread_status & 0x01)

        except (struct.error, KeyError) as e:
            logger.debug("[DR] Parse error: %s", e)
            return

        # Check for adaptive rate change
        self._check_rate_change(dmc_state)

        # Post to main thread
        Clock.schedule_once(
            lambda dt: self._apply_to_state(
                a, b, c, d, dmc_state, ses_kni, stn_kni,
                start_pt_c, program_running
            )
        )

    def _apply_to_state(
        self,
        a: float, b: float, c: float, d: float,
        dmc_state: int,
        ses_kni: int,
        stn_kni: int,
        start_pt_c: int,
        program_running: bool,
    ) -> None:
        """Main thread: write parsed values to MachineState and notify.

        Mirrors ControllerPoller._apply() exactly, plus start_pt_c.
        """
        state = self._state

        # Auto-reconnect: first successful packet after disconnect
        if not state.connected:
            state.connected = True
            logger.info("[DR] Connection restored (receiving packets)")

        # Only update dmc_state from DR if ZAA has a valid value (1-4).
        # ZAA=0 means #ZALOOP isn't running or hmiState is uninitialized —
        # in that case, let setup screens manage dmc_state directly via
        # _apply_dmc_state() and one-shot MG reads.
        if dmc_state != 0:
            state.dmc_state = dmc_state

        state.pos["A"] = float(a)
        state.pos["B"] = float(b)
        state.pos["C"] = float(c)
        state.pos["D"] = float(d)
        state.session_knife_count = ses_kni
        state.stone_knife_count = stn_kni
        state.program_running = program_running
        state.start_pt_c = start_pt_c

        state.notify()

    # ------------------------------------------------------------------
    # Disconnect / reconnect
    # ------------------------------------------------------------------

    def _handle_disconnect(self) -> None:
        """Called on recv timeout.  Set disconnected, attempt reconnect loop."""
        logger.warning("[DR] No packet for %.0f s — declaring disconnect",
                       DR_DISCONNECT_TIMEOUT)

        # Notify main thread of disconnect
        def _set_disconnected(dt):
            state = self._state
            if state.connected:
                state.connected = False
                state.notify()

        Clock.schedule_once(_set_disconnected)

        # Close current socket
        self._close_socket()

        # Reconnect loop
        while not self._stop_event.is_set():
            time.sleep(2.0)
            if self._stop_event.is_set():
                break

            ctrl = self._controller_ref
            if ctrl is None:
                break

            # Try to reconnect TCP handle
            addr = self._state.connected_address
            if not addr:
                continue

            if not ctrl.is_connected():
                try:
                    ok = ctrl.connect(addr)
                except Exception:
                    ok = False
                if not ok:
                    logger.debug("[DR] Reconnect attempt failed for %s", addr)
                    continue

            # TCP is back — re-open UDP socket and re-send IH + DR
            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._sock.bind(("0.0.0.0", self._port))
                self._sock.settimeout(DR_DISCONNECT_TIMEOUT)

                hmi_ip = get_hmi_ip(addr)
                ip_bytes = _ip_to_bytes_str(hmi_ip)
                ih_cmd = f"IH{self._handle_letter}={ip_bytes}<{self._port}>1"
                ctrl.cmd(ih_cmd)
                time.sleep(0.3)

                dr_cmd = f"DR {self._current_rate},{self._handle_index}"
                ctrl.cmd(dr_cmd)

                logger.info("[DR] Reconnected — IH + DR re-sent")
                return  # Back to recv loop in _listener_loop

            except Exception as e:
                logger.debug("[DR] Reconnect IH/DR failed: %s", e)
                self._close_socket()
                continue

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _close_socket(self) -> None:
        """Close the UDP socket if open."""
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
