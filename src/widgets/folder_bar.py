"""Folder navigation bar with address input, browse button, and up button."""

import os
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)


class FolderBar(QWidget):
    """Top bar for folder navigation: [Up] [Browse...] [Address Bar]."""

    directory_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_dir = ""
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        self.btn_up = QPushButton("⬆ 上级")
        self.btn_up.setToolTip("返回上级目录")
        self.btn_up.setFixedWidth(60)

        self.btn_browse = QPushButton("📁 浏览...")
        self.btn_browse.setToolTip("选择文件夹")
        self.btn_browse.setFixedWidth(80)

        self.addr_bar = QLineEdit()
        self.addr_bar.setPlaceholderText("输入文件夹路径后按回车进入...")
        self.addr_bar.setClearButtonEnabled(True)

        layout.addWidget(self.btn_up)
        layout.addWidget(self.btn_browse)
        layout.addWidget(self.addr_bar, 1)  # stretch

    def _connect_signals(self):
        self.btn_up.clicked.connect(self._go_up)
        self.btn_browse.clicked.connect(self._browse)
        self.addr_bar.returnPressed.connect(self._on_enter)

    def set_directory(self, path: str):
        """Update the bar to reflect a new directory."""
        normalized = str(Path(path).resolve())
        self._current_dir = normalized
        self.addr_bar.setText(normalized)
        self.btn_up.setEnabled(normalized != str(Path(normalized).anchor))

    def current_directory(self) -> str:
        return self._current_dir

    def _go_up(self):
        parent = str(Path(self._current_dir).parent)
        if parent != self._current_dir and os.path.isdir(parent):
            self._navigate_to(parent)

    def _browse(self):
        from PySide6.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(
            self, "选择视频所在文件夹", self._current_dir or os.path.expanduser("~")
        )
        if folder:
            self._navigate_to(folder)

    def _on_enter(self):
        path = self.addr_bar.text().strip().strip('"')
        expanded = str(Path(os.path.expandvars(os.path.expanduser(path))).resolve())
        if os.path.isdir(expanded):
            self._navigate_to(expanded)
        else:
            self.addr_bar.setText(self._current_dir)
            self.addr_bar.selectAll()

    def _navigate_to(self, path: str):
        normalized = str(Path(path).resolve())
        if normalized != self._current_dir:
            self._current_dir = normalized
            self.addr_bar.setText(normalized)
            self.btn_up.setEnabled(normalized != str(Path(normalized).anchor))
            self.directory_changed.emit(normalized)
