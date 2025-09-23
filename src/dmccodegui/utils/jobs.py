from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from queue import Queue, Empty
from typing import Any, Callable, Optional


JobFn = Callable[..., Any]


class JobThread:
    """Single worker thread processing FIFO jobs.

    Use submit() to enqueue work. Use schedule() for periodic callbacks that
    are executed on the worker thread; the provided function should be thread-safe.
    UI updates must be posted back to the main thread (e.g., Kivy Clock).
    """

    def __init__(self) -> None:
        self._queue: Queue[tuple[JobFn, tuple[Any, ...], dict[str, Any]]] = Queue()
        self._thread = threading.Thread(target=self._run, name="jobs-worker", daemon=True)
        self._stop_event = threading.Event()
        self._thread.start()

    def stop(self, timeout: float | None = 2.0) -> None:
        self._stop_event.set()
        # put a no-op to unblock
        self._queue.put((lambda: None, (), {}))
        self._thread.join(timeout=timeout)

    def submit(self, fn: JobFn, *args: Any, **kwargs: Any) -> None:
        self._queue.put((fn, args, kwargs))

    def schedule(self, interval_s: float, fn: JobFn, *args: Any, **kwargs: Any) -> Callable[[], None]:
        """Schedule a periodic job; returns a cancel function."""

        cancelled = threading.Event()

        def loop() -> None:
            next_time = time.monotonic()
            while not (self._stop_event.is_set() or cancelled.is_set()):
                now = time.monotonic()
                if now < next_time:
                    time.sleep(min(0.05, next_time - now))
                    continue
                try:
                    fn(*args, **kwargs)
                finally:
                    next_time += interval_s

        t = threading.Thread(target=loop, name="jobs-schedule", daemon=True)
        t.start()

        def cancel() -> None:
            cancelled.set()

        return cancel

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                fn, args, kwargs = self._queue.get(timeout=0.25)
            except Empty:
                continue
            try:
                fn(*args, **kwargs)
            except Exception:
                # Intentionally swallow exceptions to keep the worker alive; callers should handle their own logging.
                pass


_global_jobs: Optional[JobThread] = None


def get_jobs() -> JobThread:
    global _global_jobs
    if _global_jobs is None:
        _global_jobs = JobThread()
    return _global_jobs


def submit(fn: JobFn, *args: Any, **kwargs: Any) -> None:
    get_jobs().submit(fn, *args, **kwargs)


def schedule(interval_s: float, fn: JobFn, *args: Any, **kwargs: Any) -> Callable[[], None]:
    return get_jobs().schedule(interval_s, fn, *args, **kwargs)


def shutdown() -> None:
    global _global_jobs
    if _global_jobs is not None:
        _global_jobs.stop()
        _global_jobs = None

