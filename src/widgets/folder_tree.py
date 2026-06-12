"""Sidebar folder list showing subdirectories of the current directory."""

import os
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)


class FolderTree(QWidget):
    """Shows subdirectories of the current directory. Double-click to enter."""

    directory_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_dir = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self.label = QLabel("📂 子文件夹")
        self.label.setStyleSheet("font-weight: bold; padding: 2px 0;")

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)

        layout.addWidget(self.label)
        layout.addWidget(self.list_widget, 1)

    def set_directory(self, path: str):
        """Refresh the folder list for a given directory."""
        self._current_dir = str(Path(path).resolve())
        self.list_widget.clear()

        if not os.path.isdir(self._current_dir):
            return

        try:
            entries = sorted(
                [e for e in os.scandir(self._current_dir) if e.is_dir() and not e.name.startswith(".")],
                key=lambda e: e.name.lower(),
            )
        except PermissionError:
            return

        for entry in entries:
            item = QListWidgetItem(f"📁 {entry.name}")
            item.setData(1, entry.path)  # store full path
            self.list_widget.addItem(item)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        path = item.data(1)
        if path and os.path.isdir(path):
            self.directory_selected.emit(path)
