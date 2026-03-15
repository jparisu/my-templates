import threading
from pathlib import Path

from {{ package_name }}.utilizing.watching import FileWatcher


def test_file_watcher_calls_callback_when_file_changes(tmp_path: Path) -> None:
    watched_file = tmp_path / "watched.txt"
    watched_file.write_text("initial content", encoding="utf-8")

    callback_event = threading.Event()
    callback_paths: list[Path] = []

    def _on_change(path: Path) -> None:
        callback_paths.append(path)
        callback_event.set()

    watcher = FileWatcher(watched_file, _on_change, poll_interval=0.01)
    watcher.start()

    try:
        watched_file.write_text("updated content", encoding="utf-8")

        assert callback_event.wait(timeout=1.0)
        assert callback_paths == [watcher.path]
    finally:
        watcher.stop(timeout=1.0)

    assert not watcher.is_running()
