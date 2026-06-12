"""Background worker for generating video preview thumbnails (animated GIFs)."""

import os
import traceback
from datetime import datetime

from PySide6.QtCore import QThread, Signal

from .previewer import generate_animated_gif


def _worker_log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}] [Worker] {msg}"
    print(line, flush=True)


class ThumbnailWorker(QThread):
    """Processes video files in background to generate animated GIF previews."""

    progress = Signal(int, int)
    thumbnail_ready = Signal(str, str)  # video_path, gif_path
    thumbnail_failed = Signal(str)
    all_done = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._video_paths: list[str] = []
        self._start_sec: float = 0.0
        self._duration_sec: float = 3.0
        self._cache_dir: str = ""
        self._cancelled: bool = False

    def setup(
        self,
        video_paths: list[str],
        start_sec: float,
        duration_sec: float,
        cache_dir: str,
    ):
        self._video_paths = list(video_paths)
        self._start_sec = start_sec
        self._duration_sec = duration_sec
        self._cache_dir = cache_dir
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        total = len(self._video_paths)
        _worker_log(f"Started: {total} videos, start={self._start_sec}s, dur={self._duration_sec}s")

        for i, vpath in enumerate(self._video_paths):
            if self._cancelled:
                _worker_log("Cancelled")
                break

            self.progress.emit(i + 1, total)
            fname = os.path.basename(vpath)

            try:
                _worker_log(f"Processing [{i+1}/{total}]: {fname}")
                result = generate_animated_gif(
                    video_path=vpath,
                    start_sec=self._start_sec,
                    duration_sec=self._duration_sec,
                    cache_dir=self._cache_dir,
                )
                if result:
                    _worker_log(f"  OK: {fname} -> {result}")
                    self.thumbnail_ready.emit(vpath, result)
                else:
                    _worker_log(f"  FAILED (None): {fname}")
                    self.thumbnail_failed.emit(vpath)
            except Exception:
                _worker_log(f"  EXCEPTION: {fname}\n{traceback.format_exc()}")
                self.thumbnail_failed.emit(vpath)

        _worker_log("All done")
        self.all_done.emit()
