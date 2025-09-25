from __future__ import annotations

import time
from typing import Optional

# Define CommError here to avoid circular imports
class CommError(Exception):
    pass


# Import protocol from parent module
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..controller import GalilDriverProtocol
else:
    # Runtime fallback
    try:
        from ..controller import GalilDriverProtocol
    except ImportError:
        GalilDriverProtocol = None  # type: ignore


class GalilTransport:
    """Thin transport over a Galil driver, with retries/backoff.

    - open/close lifecycle
    - command() with retries and optional overall timeout
    """

    def __init__(self, driver: Optional[GalilDriverProtocol] = None) -> None:
        self._driver: Optional[GalilDriverProtocol] = driver
        self._connected: bool = False

    def open(self, address: str) -> None:
        drv = self._ensure_driver()
        # "-d" instructs gclib to disable acceleration (optional, preserve user's prior behavior if present)
        drv.GOpen(address)
        self._connected = True

    def close(self) -> None:
        if not self._driver:
            return
        try:
            self._driver.GClose()
        finally:
            self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def command(self, cmd: str, *, retries: int = 2, backoff_s: float = 0.1, timeout_s: Optional[float] = None) -> str:
        if not self._connected or not self._driver:
            raise CommError("Not connected")
        deadline = (time.monotonic() + timeout_s) if timeout_s else None
        attempt = 0
        last_err: Optional[Exception] = None
        while True:
            try:
                return self._driver.GCommand(cmd)
            except Exception as e:  # pragma: no cover - actual driver only in integration
                last_err = e
                attempt += 1
                print(f"[TRANSPORT] command failed (attempt {attempt}/{retries+1}): {cmd} -> {e}")
                if attempt > retries:
                    break
                if deadline is not None and time.monotonic() >= deadline:
                    break
                # short backoff
                time.sleep(backoff_s)
        err_msg = str(last_err) if last_err else "transport error"
        print(f"[TRANSPORT] giving up on: {cmd} err={err_msg}")
        raise CommError(err_msg)

    def _ensure_driver(self) -> GalilDriverProtocol:
        if self._driver is None:
            # Lazy import to keep module importable without gclib present
            import gclib  # type: ignore

            self._driver = gclib.py()
        return self._driver