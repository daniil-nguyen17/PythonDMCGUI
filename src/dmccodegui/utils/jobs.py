from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from queue import Queue, Empty
from typing import Any, Callable, Optional


JobFn = Callable[..., Any]

# This file is used to run tasks asynchronously as to not freeze the app
class JobThread:
    """Single worker thread processing FIFO jobs.

    Use submit() to enqueue work. Use schedule() for periodic callbacks that
    are executed on the worker thread; the provided function should be thread-safe.
    UI updates must be posted back to the main thread (e.g., Kivy Clock).
    """

    def __init__(self) -> None:
        self._queue: Queue[tuple[JobFn, tuple[Any, ...], dict[str, Any]]] = Queue()
        self._urgent_queue: Queue[tuple[JobFn, tuple[Any, ...], dict[str, Any]]] = Queue(maxsize=1)
        self._cancel_event = threading.Event()
        self._thread = threading.Thread(target=self._run, name="jobs-worker", daemon=True)
        self._stop_event = threading.Event()
        self._thread.start()

    def stop(self, timeout: float | None = 2.0) -> None:
        self._stop_event.set()
        # put a no-op to unblock
        self._queue.put((lambda: None, (), {}))
        self._thread.join(timeout=timeout)

    @property
    def cancel_event(self) -> threading.Event:
        """Read-only access to cancel event for in-flight normal jobs to check."""
        return self._cancel_event

    def submit(self, fn: JobFn, *args: Any, **kwargs: Any) -> None:
        self._queue.put((fn, args, kwargs))

    def submit_urgent(self, fn: JobFn, *args: Any, **kwargs: Any) -> None:
        """Submit an urgent job that preempts queued normal jobs.

        Sets the cancel_event so in-flight normal jobs can check and yield early.
        Drains any stale entry from the urgent queue before placing the new one.
        """
        self._cancel_event.set()
        # Drain any stale urgent entry to make room (maxsize=1)
        try:
            self._urgent_queue.get_nowait()
        except Empty:
            pass
        self._urgent_queue.put((fn, args, kwargs))

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
            # Check urgent queue first — preempts normal jobs
            try:
                fn, args, kwargs = self._urgent_queue.get_nowait()
                self._cancel_event.clear()
                try:
                    fn(*args, **kwargs)
                except Exception:
                    pass
                continue
            except Empty:
                pass

            try:
                fn, args, kwargs = self._queue.get(timeout=0.25)
            except Empty:
                continue
            try:
                fn(*args, **kwargs)
            except Exception:
                # Intentionally swallow exceptions to keep the worker alive; callers should handle their own logging.
                pass

            # After normal job, check urgent queue again in case submit_urgent fired mid-job
            try:
                ufn, uargs, ukwargs = self._urgent_queue.get_nowait()
                self._cancel_event.clear()
                try:
                    ufn(*uargs, **ukwargs)
                except Exception:
                    pass
            except Empty:
                pass


_global_jobs: Optional[JobThread] = None


def get_jobs() -> JobThread:
    global _global_jobs
    if _global_jobs is None:
        _global_jobs = JobThread()
    return _global_jobs


def submit(fn: JobFn, *args: Any, **kwargs: Any) -> None:
    get_jobs().submit(fn, *args, **kwargs)


def submit_urgent(fn: JobFn, *args: Any, **kwargs: Any) -> None:
    """Module-level convenience: submit an urgent job to the global JobThread."""
    get_jobs().submit_urgent(fn, *args, **kwargs)


def schedule(interval_s: float, fn: JobFn, *args: Any, **kwargs: Any) -> Callable[[], None]:
    return get_jobs().schedule(interval_s, fn, *args, **kwargs)


def shutdown() -> None:
    global _global_jobs
    if _global_jobs is not None:
        _global_jobs.stop()
        _global_jobs = None

