"""Pagination bar with prev/next, page info, and items-per-page control."""

import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class PaginationBar(QWidget):
    """Bottom bar: [◀ Prev] Page X/Y [Next ▶] | 每页: [dropdown] | 共 N 个视频."""

    page_changed = Signal(int)
    items_per_page_changed = Signal(int)

    ITEMS_OPTIONS = [3, 6, 9, 12, 15, 21, 30]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_page = 1
        self._total_pages = 1
        self._total_videos = 0
        self._items_per_page = 6
        self._updating_combo = False  # guard against re-entrant signals
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(8)

        self.btn_prev = QPushButton("◀ 上一页")
        self.btn_prev.setEnabled(False)

        self.page_label = QLabel("第 1/1 页")
        self.page_label.setStyleSheet("color: #ccc; font-size: 13px;")

        self.btn_next = QPushButton("下一页 ▶")
        self.btn_next.setEnabled(False)

        layout.addWidget(self.btn_prev)
        layout.addWidget(self.page_label)
        layout.addWidget(self.btn_next)

        layout.addStretch()

        self.total_label = QLabel("共 0 个视频")
        self.total_label.setStyleSheet("color: #999; font-size: 12px;")

        per_page_label = QLabel("每页:")
        per_page_label.setStyleSheet("color: #999; font-size: 12px;")

        self.combo_per_page = QComboBox()
        self.combo_per_page.addItems([str(n) for n in self.ITEMS_OPTIONS])
        self.combo_per_page.setCurrentText(str(self._items_per_page))
        self.combo_per_page.setFixedWidth(64)
        self.combo_per_page.setEditable(True)
        self.combo_per_page.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.combo_per_page.lineEdit().setReadOnly(True)

        layout.addWidget(self.total_label)
        layout.addWidget(per_page_label)
        layout.addWidget(self.combo_per_page)

    def _connect_signals(self):
        self.btn_prev.clicked.connect(self._go_prev)
        self.btn_next.clicked.connect(self._go_next)
        self.combo_per_page.currentTextChanged.connect(self._on_items_per_page_changed)

    def _ensure_option(self, value: int):
        """Add a custom value to the combo if not already present."""
        text = str(value)
        for i in range(self.combo_per_page.count()):
            if self.combo_per_page.itemText(i) == text:
                return
        self.combo_per_page.insertItem(0, text)

    def set_data(self, total_videos: int, current_page: int = 1):
        """Update pagination state. Call whenever total videos or items_per_page changes."""
        self._total_videos = total_videos
        self._items_per_page = int(self.combo_per_page.currentText() or self._items_per_page or 6)
        self._total_pages = max(1, math.ceil(total_videos / self._items_per_page) if self._items_per_page > 0 else 1)
        self._current_page = max(1, min(current_page, self._total_pages))
        self._update_ui()

    def set_items_per_page(self, value: int):
        """Programmatically set items per page without triggering change signal."""
        self._ensure_option(value)
        self._updating_combo = True
        self.combo_per_page.setCurrentText(str(value))
        self._updating_combo = False
        self._items_per_page = value

    def go_to_page(self, page: int):
        """Navigate to a specific page."""
        self._current_page = max(1, min(page, self._total_pages))
        self._update_ui()
        self.page_changed.emit(self._current_page)

    def current_page(self) -> int:
        return self._current_page

    def items_per_page(self) -> int:
        return self._items_per_page

    def _update_ui(self):
        self.page_label.setText(f"第 {self._current_page}/{self._total_pages} 页")
        self.btn_prev.setEnabled(self._current_page > 1)
        self.btn_next.setEnabled(self._current_page < self._total_pages)
        self.total_label.setText(f"共 {self._total_videos} 个视频")

    def _go_prev(self):
        if self._current_page > 1:
            self.go_to_page(self._current_page - 1)

    def _go_next(self):
        if self._current_page < self._total_pages:
            self.go_to_page(self._current_page + 1)

    def _on_items_per_page_changed(self, text: str):
        if self._updating_combo:
            return
        try:
            new_val = int(text)
        except ValueError:
            return
        if new_val != self._items_per_page:
            self._items_per_page = new_val
            self.items_per_page_changed.emit(new_val)
