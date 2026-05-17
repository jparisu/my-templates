from __future__ import annotations

import hashlib
import logging
import threading
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class FileWatcher:
    """
    Watch a single file and invoke a callback when its contents change.

    The watcher polls the file in a daemon thread and compares each observed
    version against the last known content digest.
    """

    def __init__(
        self,
        path: str | Path,
        callback: Callable[[Path], None],
        poll_interval: float = 0.1,
    ) -> None:
        """
        Configure a watcher for a single file path.

        Args:
            path: File to monitor for modifications.
            callback: Function called with the normalized file path each time a
                change is detected.
            poll_interval: Delay, in seconds, between filesystem checks when
                the watcher runs continuously.
        """
        if poll_interval <= 0:
            raise ValueError("poll_interval must be greater than zero")

        self._path = Path(path).expanduser().resolve(strict=False)
        self._callback = callback
        self._poll_interval = poll_interval
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_snapshot = self._capture_snapshot()

    @property
    def path(self) -> Path:
        """Return the normalized file path associated with this watcher."""
        return self._path

    @property
    def poll_interval(self) -> float:
        """Return the configured polling interval in seconds."""
        return self._poll_interval

    def start(self) -> None:
        """
        Start watching the configured file in the background.

        Repeated calls are safe and do not create duplicate watcher threads.
        """
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return

            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._watch_loop,
                name=f"{self.__class__.__name__}:{self._path.name}",
                daemon=True,
            )
            self._thread.start()

    def stop(self, timeout: float | None = None) -> None:
        """
        Stop the background watcher and wait for shutdown if needed.

        Args:
            timeout: Maximum number of seconds to wait for the background
                watcher loop to finish. ``None`` means wait without a timeout.
        """
        with self._lock:
            thread = self._thread
            self._stop_event.set()

        if thread is None:
            return

        if thread is threading.current_thread():
            with self._lock:
                if self._thread is thread:
                    self._thread = None
            return

        thread.join(timeout=timeout)
        if not thread.is_alive():
            with self._lock:
                if self._thread is thread:
                    self._thread = None

    def check_for_changes(self) -> bool:
        """
        Inspect the watched file once and trigger the callback on change.

        Returns:
            ``True`` when a new change is detected and the callback is invoked,
            otherwise ``False``.
        """
        current_snapshot = self._capture_snapshot()

        with self._lock:
            if current_snapshot == self._last_snapshot:
                return False

            self._last_snapshot = current_snapshot
            callback = self._callback

        callback(self._path)
        return True

    def is_running(self) -> bool:
        """
        Return whether the watcher currently has an active background loop.

        This reflects the state of the internal watcher thread managed by
        ``start()`` and ``stop()``.
        """
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def _capture_snapshot(self) -> bytes | None:
        """Return a stable digest for the file's current content or ``None`` if absent."""
        try:
            data = self._path.read_bytes()
        except FileNotFoundError:
            return None

        return hashlib.blake2b(data, digest_size=16).digest()

    def _watch_loop(self) -> None:
        """Poll the watched file until ``stop()`` requests shutdown."""
        current_thread = threading.current_thread()
        try:
            while not self._stop_event.is_set():
                try:
                    self.check_for_changes()
                except Exception:
                    logger.exception("File watcher callback failed for %s", self._path)

                if self._stop_event.wait(self._poll_interval):
                    break
        finally:
            with self._lock:
                if self._thread is current_thread:
                    self._thread = None
