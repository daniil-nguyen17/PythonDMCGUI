"""Centralized controller poller for Phase 10.

ControllerPoller reads all controller state at 10 Hz and writes to MachineState.
It is the single app-wide poller — per-screen polling is replaced by this module.

Threading model:
- _on_tick() fires on the Kivy main thread (Clock.schedule_interval callback)
- _on_tick() submits _do_read() to the FIFO jobs worker thread
- _do_read() does all blocking cmd() calls on the worker thread
- _do_read() posts _apply() / _on_disconnect() back to main thread via Clock.schedule_once
- _apply() and _on_disconnect() run on main thread — the ONLY place that mutates MachineState

CRITICAL: _do_read() must NEVER call state.notify() directly.
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

from kivy.clock import Clock

from .dmc_vars import HMI_STATE_VAR, CT_SES_KNI, CT_STN_KNI
from ..utils import jobs

if TYPE_CHECKING:
    from ..app_state import MachineState
    from ..controller import GalilController

POLL_HZ: int = 10
DISCONNECT_THRESHOLD: int = 3


class ControllerPoller:
    """Reads controller state at POLL_HZ and writes to MachineState.

    Lifecycle:
        poller = ControllerPoller(controller, state)
        poller.start()   # begin polling
        poller.stop()    # stop polling (e.g., on disconnect or shutdown)

    Reconnect flow:
        When DISCONNECT_THRESHOLD consecutive failures occur, _on_disconnect() fires:
          - state.connected is set to False
          - controller.disconnect() is called to close the handle (enabling clean reconnect)
        On the next tick, _do_read() checks controller.is_connected():
          - If False, tries controller.connect(state.connected_address)
          - If connect succeeds, proceeds with reads and eventually calls _apply()
            which sets state.connected = True again
    """

    def __init__(self, controller: GalilController, state: MachineState) -> None:
        self._controller = controller
        self._state = state
        self._fail_count: int = 0
        self._disconnect_start: Optional[float] = None
        self._clock_event = None

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start polling at POLL_HZ. Safe to call multiple times (noop if already running)."""
        if self._clock_event is not None:
            return
        self._clock_event = Clock.schedule_interval(self._on_tick, 1.0 / POLL_HZ)

    def stop(self) -> None:
        """Stop polling. Safe to call even if not started."""
        if self._clock_event is not None:
            self._clock_event.cancel()
            self._clock_event = None

    # ------------------------------------------------------------------
    # Tick — called on main thread by Clock
    # ------------------------------------------------------------------

    def _on_tick(self, dt: float) -> None:
        """Main-thread tick: submit background read to jobs worker."""
        jobs.submit(self._do_read)

    # ------------------------------------------------------------------
    # Background read — runs on jobs worker thread
    # ------------------------------------------------------------------

    def _do_read(self) -> None:
        """Background thread: read 7 values from controller.

        On success: reset fail count, post _apply() to main thread.
        On exception: increment fail count; if >= DISCONNECT_THRESHOLD, post _on_disconnect().

        Reconnect attempt: when state.connected is False (poller still running after
        disconnect), try controller.connect() before reading.
        """
        ctrl = self._controller
        state = self._state

        # Attempt reconnect if handle was closed by a previous disconnect
        if not ctrl.is_connected():
            addr = state.connected_address
            if addr:
                try:
                    ok = ctrl.connect(addr)
                except Exception:
                    ok = False
                if not ok:
                    self._fail_count += 1
                    if self._fail_count >= DISCONNECT_THRESHOLD:
                        Clock.schedule_once(self._on_disconnect)
                    return
                # Connect succeeded — fall through to reads below
            else:
                # No address to reconnect to; nothing to do
                return

        try:
            dmc_state = int(float(ctrl.cmd(f"MG {HMI_STATE_VAR}").strip()))
            a = float(ctrl.cmd("MG _TPA").strip())
            b = float(ctrl.cmd("MG _TPB").strip())
            c = float(ctrl.cmd("MG _TPC").strip())
            d = float(ctrl.cmd("MG _TPD").strip())
            ses_kni = int(float(ctrl.cmd(f"MG {CT_SES_KNI}").strip()))
            stn_kni = int(float(ctrl.cmd(f"MG {CT_STN_KNI}").strip()))
        except Exception:
            self._fail_count += 1
            if self._fail_count >= DISCONNECT_THRESHOLD:
                Clock.schedule_once(self._on_disconnect)
            return

        # All reads succeeded — reset failure counter
        self._fail_count = 0

        # Post state update to main thread
        Clock.schedule_once(
            lambda dt: self._apply(dmc_state, a, b, c, d, ses_kni, stn_kni)
        )

    # ------------------------------------------------------------------
    # Main-thread state writers
    # ------------------------------------------------------------------

    def _apply(
        self,
        dmc_state: int,
        a: float,
        b: float,
        c: float,
        d: float,
        ses_kni: int,
        stn_kni: int,
    ) -> None:
        """Main thread: write all polled values to MachineState and notify listeners.

        If the state was previously disconnected (auto-reconnect), set connected=True
        and clear _disconnect_start.
        """
        state = self._state

        # Auto-reconnect: successful read after disconnect
        if not state.connected:
            state.connected = True
            self._disconnect_start = None

        state.dmc_state = dmc_state
        state.pos["A"] = a
        state.pos["B"] = b
        state.pos["C"] = c
        state.pos["D"] = d
        state.session_knife_count = ses_kni
        state.stone_knife_count = stn_kni

        state.notify()

    def _on_disconnect(self, dt: float = 0) -> None:
        """Main thread: handle loss of connection.

        Guard against double-firing — if already disconnected, do nothing.
        Closes the controller handle via jobs so cmd() raises on next attempt,
        enabling a clean reconnect path.
        """
        state = self._state

        if not state.connected:
            return  # already disconnected — guard

        state.connected = False
        self._disconnect_start = time.monotonic()
        state.notify()

        # Close the handle on the worker thread so connect() creates a fresh one
        jobs.submit(self._controller.disconnect)
