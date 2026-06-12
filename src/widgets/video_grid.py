"""Grid layout displaying animated video preview cards with scrollbars."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from ..core.scanner import VideoInfo
from .video_card import VideoCard


class VideoGrid(QScrollArea):
    """Scrollable grid of animated video preview cards.

    Cards flow left-to-right, then wrap to next row.
    Scrollbars appear when content exceeds viewport.
    """

    video_double_clicked = Signal(str)
    copy_path_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: list[VideoCard] = []
        self._columns = 3
        self._build_ui()

    def _build_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet("""
            QScrollArea { border: none; background: #1e1e1e; }
            QScrollBar:horizontal { background: #1e1e1e; height: 10px; }
            QScrollBar::handle:horizontal { background: #444; border-radius: 5px; min-width: 20px; }
            QScrollBar::handle:horizontal:hover { background: #555; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
        """)

        self._container = QWidget()
        self._container.setStyleSheet("background: #1e1e1e;")

        self._grid_layout = QGridLayout(self._container)
        self._grid_layout.setContentsMargins(8, 8, 8, 8)
        self._grid_layout.setSpacing(10)

        self._placeholder = QLabel("选择一个文件夹以查看视频预览")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #666; font-size: 18px;")
        self._grid_layout.addWidget(self._placeholder, 0, 0, 1, self._columns)
        self._grid_layout.setRowStretch(0, 1)
        for c in range(self._columns):
            self._grid_layout.setColumnStretch(c, 1)

        self.setWidget(self._container)

    def set_columns(self, columns: int):
        self._columns = max(1, columns)

    def clear(self):
        """Remove all video cards, leaving only the placeholder."""
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            w = item.widget()
            if w is not None and w is not self._placeholder:
                w.deleteLater()
        self._cards.clear()

        self._placeholder.setText("选择一个文件夹以查看视频预览")
        self._placeholder.show()
        self._grid_layout.addWidget(self._placeholder, 0, 0, 1, self._columns)
        self._grid_layout.setRowStretch(0, 1)
        for c in range(self._columns):
            self._grid_layout.setColumnStretch(c, 1)

    def populate(self, videos: list[VideoInfo]):
        """Fill the grid with video cards. Placeholder is removed."""
        self._grid_layout.removeWidget(self._placeholder)
        self._placeholder.hide()

        for card in self._cards:
            self._grid_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        # Reset all row/column stretches
        for r in range(self._grid_layout.rowCount()):
            self._grid_layout.setRowStretch(r, 0)
        for c in range(self._grid_layout.columnCount()):
            self._grid_layout.setColumnStretch(c, 0)

        if not videos:
            self._placeholder.setText("当前目录没有视频文件")
            self._placeholder.show()
            self._grid_layout.addWidget(self._placeholder, 0, 0, 1, self._columns)
            self._grid_layout.setRowStretch(0, 1)
            self._container.updateGeometry()
            return

        for i, vinfo in enumerate(videos):
            card = VideoCard(vinfo)
            card.copy_btn.clicked.connect(lambda checked=False, p=vinfo.path: self._copy_path(p))
            card.double_clicked.connect(self._on_video_double_clicked)

            row = i // self._columns
            col = i % self._columns
            self._grid_layout.addWidget(card, row, col, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            self._cards.append(card)

        # Add spacer column to push cards left, spacer row to push up
        self._grid_layout.setColumnStretch(self._columns, 1)
        last_row = (len(videos) - 1) // self._columns
        self._grid_layout.setRowStretch(last_row + 1, 1)

        self._container.updateGeometry()

    def update_card_thumbnail(self, video_path: str, gif_path: str):
        for card in self._cards:
            if card.video_info.path == video_path:
                card.set_preview_gif(gif_path)
                return

    def mark_card_error(self, video_path: str):
        for card in self._cards:
            if card.video_info.path == video_path:
                card.set_error()
                return

    def _copy_path(self, path: str):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(path)
        self.copy_path_requested.emit(path)

    def _on_video_double_clicked(self, path: str):
        self.video_double_clicked.emit(path)
