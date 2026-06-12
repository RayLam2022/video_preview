"""Individual video preview card with animated GIF, path, and copy button."""

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMovie
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.scanner import VideoInfo

# Card dimensions (uniform across all cards)
CARD_W = 260
PREVIEW_W = 240
PREVIEW_H = 180


class VideoCard(QWidget):
    """A card showing a video's animated GIF preview, file path, and copy button.

    Cards are fixed-width with uniform height. Videos display at native
    aspect ratio within the preview area (letterboxed).
    """

    double_clicked = Signal(str)

    STYLE = """
        QWidget#VideoCard {
            background: #2b2b2b;
            border: 1px solid #444;
            border-radius: 6px;
        }
        QWidget#VideoCard:hover {
            border: 1px solid #6af;
        }
    """

    def __init__(self, video_info: VideoInfo, parent=None):
        super().__init__(parent)
        self.video_info = video_info
        self._movie: QMovie | None = None
        self.setObjectName("VideoCard")
        self.setStyleSheet(self.STYLE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(self._build_tooltip())
        self.setFixedWidth(CARD_W)
        self._build_ui()

    def _build_tooltip(self) -> str:
        v = self.video_info
        return (
            f"文件名: {v.filename}\n"
            f"分辨率: {v.width}x{v.height}\n"
            f"时长: {v.duration_sec:.1f} 秒\n"
            f"编码: {v.codec}\n"
            f"大小: {v.size_mb:.1f} MB\n"
            f"\n双击用默认播放器打开"
        )

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Preview area — fixed size container, GIF centers inside with native ratio
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(PREVIEW_W, PREVIEW_H)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background: #1a1a1a; border-radius: 4px;")
        self.preview_label.setText("⏳\n加载中...")

        # File path row
        path_layout = QHBoxLayout()
        path_layout.setSpacing(4)

        self.path_label = QLabel(self.video_info.path)
        self.path_label.setStyleSheet("color: #aaa; font-size: 11px;")
        self.path_label.setWordWrap(False)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.copy_btn = QPushButton("📋")
        self.copy_btn.setFixedSize(28, 22)
        self.copy_btn.setToolTip("复制文件路径")
        self.copy_btn.setStyleSheet(
            "QPushButton { border: none; font-size: 12px; } "
            "QPushButton:hover { background: #555; border-radius: 3px; }"
        )

        path_layout.addWidget(self.path_label, 1)
        path_layout.addWidget(self.copy_btn)

        # Center the preview area horizontally
        preview_wrapper = QHBoxLayout()
        preview_wrapper.addStretch()
        preview_wrapper.addWidget(self.preview_label)
        preview_wrapper.addStretch()

        layout.addLayout(preview_wrapper)
        layout.addLayout(path_layout)
        layout.addStretch()

    def set_preview_gif(self, gif_path: str):
        """Set the animated GIF preview. Plays at native size, centered."""
        if not os.path.isfile(gif_path):
            self.set_error("⚠ GIF 文件不存在")
            return

        self._movie = QMovie(gif_path)
        if not self._movie.isValid():
            self.set_error("⚠ GIF 无效")
            return

        self._movie.setCacheMode(QMovie.CacheMode.CacheAll)
        self.preview_label.setMovie(self._movie)
        self._movie.start()

    def set_error(self, message: str = "⚠ 预览生成失败"):
        self._movie = None
        self.preview_label.setMovie(None)
        self.preview_label.setText(message)
        self.preview_label.setStyleSheet("background: #1a1a1a; color: #e55; border-radius: 4px;")

    def enterEvent(self, event):
        if self._movie and self._movie.state() == QMovie.MovieState.NotRunning:
            self._movie.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit(self.video_info.path)
        super().mouseDoubleClickEvent(event)
