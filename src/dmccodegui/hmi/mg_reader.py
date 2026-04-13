"""MgReader — app-wide DMC MG message subscriber and dispatcher.

Opens a separate gclib handle with ``--subscribe MG`` and routes incoming
messages to registered handlers on the Kivy main thread.

Message classification
----------------------
- ``STATE:N`` integer messages  → state_handlers(int)
- Position prefix messages      → position_handlers(dict)
- Everything else               → log_handlers(str)

State and position messages are explicitly excluded from log_handlers so
the operator log stays clean (only freeform MG text appears there).

Handler registration
--------------------
All ``add_*_handler()`` methods return an unregister callable::

    unreg = reader.add_log_handler(my_fn)
    unreg()  # removes my_fn from the handler list

Thread lifecycle
----------------
``start(address)`` spawns the background loop thread.
``stop()`` signals the loop and joins with a 2-second timeout.
Calling ``start()`` while already running is a no-op.
Calling ``stop()`` before ``start()`` is safe.

DMC connection string format
-----------------------------
``"{address} --direct --subscribe MG --timeout 500"``

GTimeout(500) is called immediately after GOpen so the GMessage() loop
wakes every 500 ms to check the stop event regardless of DMC activity.
"""
from __future__ import annotations

import re
import threading
from typing import Any, Callable

from kivy.clock import Clock

# ---------------------------------------------------------------------------
# Message classification constants
# ---------------------------------------------------------------------------

#: Position message prefixes (from DMC #SHOWPOS / #MAIN MG output)
_POSITION_PREFIXES: tuple[str, ...] = (
    "IDLING FOR INPUT",
    "PRE-LI",
    "RUNNING",
    "END REACHED",
)

#: Prefix for controller-state integer messages
STATE_PREFIX: str = "STATE:"

#: Regex that matches a single KEY:VALUE pair in a position message.
#: Keys are one or more word-characters (letters, digits, underscore).
#: Values are optional minus sign followed by digits and optional decimal point.
_AXIS_PATTERN: re.Pattern = re.compile(r'([A-Za-z]\w*):(-?[\d.]+)')


# ---------------------------------------------------------------------------
# MgReader
# ---------------------------------------------------------------------------

class MgReader:
    """App-wide MG message subscriber.

    Instantiate once (e.g., in the App class) and keep for the application
    lifetime.  Individual screens register handlers on ``on_pre_enter`` and
    unregister on ``on_leave`` via the returned callables.
    """

    def __init__(self) -> None:
        self._log_handlers: list[Callable[[str], None]] = []
        self._state_handlers: list[Callable[[int], None]] = []
        self._position_handlers: list[Callable[[dict], None]] = []

        self._mg_thread: threading.Thread | None = None
        self._mg_stop_event: threading.Event | None = None

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def add_log_handler(self, fn: Callable[[str], None]) -> Callable[[], None]:
        """Register *fn* to receive freeform MG log messages.

        Returns an unregister callable that removes *fn* from the list.
        """
        self._log_handlers.append(fn)
        return lambda: self._log_handlers.remove(fn) if fn in self._log_handlers else None

    def add_state_handler(self, fn: Callable[[int], None]) -> Callable[[], None]:
        """Register *fn* to receive STATE:N integers.

        Returns an unregister callable.
        """
        self._state_handlers.append(fn)
        return lambda: self._state_handlers.remove(fn) if fn in self._state_handlers else None

    def add_position_handler(self, fn: Callable[[dict], None]) -> Callable[[], None]:
        """Register *fn* to receive position dicts (axis keys + "prefix").

        Returns an unregister callable.
        """
        self._position_handlers.append(fn)
        return lambda: self._position_handlers.remove(fn) if fn in self._position_handlers else None

    # ------------------------------------------------------------------
    # Message classification (static — no thread machinery)
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_line(line: str) -> tuple[str, Any]:
        """Classify a single DMC MG output line.

        Returns
        -------
        ``("state", int)``
            For ``STATE:N`` messages.
        ``("position", dict)``
            For position prefix messages.  Dict has axis-letter keys mapped
            to float values plus a ``"prefix"`` key with the matched prefix.
        ``("log", str)``
            For any other freeform text.
        """
        # STATE:N — integer state transition message
        if line.startswith(STATE_PREFIX):
            try:
                value = int(line[len(STATE_PREFIX):].strip())
                return ("state", value)
            except ValueError:
                # Malformed STATE: line — fall through to log
                return ("log", line)

        # Position prefixes
        for prefix in _POSITION_PREFIXES:
            if line.startswith(prefix):
                axes: dict[str, Any] = {"prefix": prefix}
                for match in _AXIS_PATTERN.finditer(line):
                    key = match.group(1)
                    axes[key] = float(match.group(2))
                return ("position", axes)

        # Freeform log text
        return ("log", line)

    # ------------------------------------------------------------------
    # Dispatch (called from background thread, posts to Kivy main thread)
    # ------------------------------------------------------------------

    def _dispatch_message(self, line: str) -> None:
        """Classify *line* and schedule dispatch to appropriate handlers.

        ALL messages are sent to log_handlers so the controller log shows
        everything. State and position messages are additionally routed to
        their specialized handlers for structured processing.
        """
        kind, value = self._classify_line(line)

        # Always send raw line to log handlers (controller log shows everything)
        for fn in list(self._log_handlers):
            Clock.schedule_once(lambda dt, _fn=fn, _v=line: _fn(_v))

        # Additionally route to specialized handlers
        if kind == "state":
            for fn in list(self._state_handlers):
                Clock.schedule_once(lambda dt, _fn=fn, _v=value: _fn(_v))
        elif kind == "position":
            for fn in list(self._position_handlers):
                Clock.schedule_once(lambda dt, _fn=fn, _v=value: _fn(_v))

    # ------------------------------------------------------------------
    # Background loop
    # ------------------------------------------------------------------

    def _loop(self, address: str, stop_event: threading.Event) -> None:
        """Background thread: subscribe to MG via UDP and drain messages.

        Opens a separate gclib handle with ``--direct --subscribe MG --timeout 500``.
        GTimeout(500) ensures GMessage() wakes every 500 ms regardless of DMC
        activity so the stop_event check is timely.
        """
        try:
            import gclib  # type: ignore
        except ImportError:
            print("[MgReader] gclib not available — MG reader disabled")
            return

        handle = None
        try:
            handle = gclib.py()
            connection_string = f"{address} --direct --subscribe MG --timeout 500"
            handle.GOpen(connection_string)
            handle.GTimeout(500)
            print(f"[MgReader] connected: {connection_string}")
        except Exception as exc:
            print(f"[MgReader] GOpen failed: {exc}")
            if handle:
                try:
                    handle.GClose()
                except Exception:
                    pass
            return

        try:
            while not stop_event.is_set():
                try:
                    msg = handle.GMessage()
                    if msg:
                        for raw_line in msg.strip().split("\n"):
                            raw_line = raw_line.strip()
                            if raw_line:
                                self._dispatch_message(raw_line)
                except Exception:
                    # GMessage timeout or read error — normal, just retry
                    pass
        finally:
            try:
                handle.GClose()
            except Exception:
                pass
            print("[MgReader] handle closed")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, address: str) -> None:
        """Start the MG reader background thread.

        Parameters
        ----------
        address:
            Bare controller IP/hostname (e.g. ``"192.168.1.100"``).
            The connection flags are appended internally.

        If already running, this is a no-op.
        """
        if self._mg_thread is not None:
            return

        self._mg_stop_event = threading.Event()
        self._mg_thread = threading.Thread(
            target=self._loop,
            args=(address, self._mg_stop_event),
            daemon=True,
            name="MgReaderLoop",
        )
        self._mg_thread.start()

    def stop(self) -> None:
        """Signal the MG reader thread to stop and join within 2 seconds.

        Safe to call before ``start()`` or after already stopped.
        """
        if self._mg_stop_event is not None:
            self._mg_stop_event.set()
        if self._mg_thread is not None:
            self._mg_thread.join(timeout=2.0)
            self._mg_thread = None
        self._mg_stop_event = None
