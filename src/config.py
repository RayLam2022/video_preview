"""Application configuration with QSettings persistence."""

from PySide6.QtCore import QSettings, QStandardPaths
from dataclasses import dataclass, field


@dataclass
class AppConfig:
    """Application settings with persistence via QSettings."""

    preview_start_sec: float = 0.0
    preview_duration_sec: float = 3.0
    frame_count: int = 5
    items_per_page: int = 6
    columns_per_row: int = 3
    last_directory: str = ""
    window_width: int = 1280
    window_height: int = 800

    _settings: QSettings = field(default_factory=lambda: QSettings("PreviewGUI", "VideoPreview"))

    def load(self) -> "AppConfig":
        s = self._settings
        self.preview_start_sec = float(s.value("preview_start_sec", 0.0))
        self.preview_duration_sec = float(s.value("preview_duration_sec", 3.0))
        self.frame_count = int(s.value("frame_count", 5))
        self.items_per_page = int(s.value("items_per_page", 6))
        self.columns_per_row = int(s.value("columns_per_row", 3))
        self.last_directory = str(s.value("last_directory", ""))
        self.window_width = int(s.value("window_width", 1280))
        self.window_height = int(s.value("window_height", 800))
        return self

    def save(self):
        s = self._settings
        s.setValue("preview_start_sec", self.preview_start_sec)
        s.setValue("preview_duration_sec", self.preview_duration_sec)
        s.setValue("frame_count", self.frame_count)
        s.setValue("items_per_page", self.items_per_page)
        s.setValue("columns_per_row", self.columns_per_row)
        s.setValue("last_directory", self.last_directory)
        s.setValue("window_width", self.window_width)
        s.setValue("window_height", self.window_height)
        s.sync()
