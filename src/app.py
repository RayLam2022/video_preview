"""Main application window - assembles all widgets and manages navigation/preview logic."""

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .config import AppConfig
from .core.scanner import scan_videos, normalize_path
from .core.thumbnail_worker import ThumbnailWorker
from .widgets.folder_bar import FolderBar
from .widgets.folder_tree import FolderTree
from .widgets.video_grid import VideoGrid
from .widgets.pagination_bar import PaginationBar
from .widgets.settings_dialog import SettingsDialog


def _log(msg: str):
    """Write a debug message to both stdout and a log file."""
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "debug.log"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _open_file_default(path: str):
    """Open a file with the system default application (cross-platform)."""
    import shutil
    import subprocess
    import sys

    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        opener = shutil.which("xdg-open") or shutil.which("open")
        if opener:
            subprocess.run([opener, path], check=False)
        else:
            raise RuntimeError("No file opener found")


class MainWindow(QMainWindow):
    """Video Preview GUI main window."""

    def __init__(self, config: AppConfig):
        super().__init__()
        _log("=== MainWindow init ===")
        self.config = config
        self._all_videos: list = []
        self._current_page_videos: list = []
        self._worker: ThumbnailWorker | None = None
        self._cache_dir = ""

        self._setup_cache()
        self._build_ui()
        self._setup_menu()
        self._connect_signals()
        self._restore_state()
        _log("MainWindow init done")

    def _setup_cache(self):
        import tempfile
        self._cache_dir = os.path.join(tempfile.gettempdir(), "preview_gui_cache")
        os.makedirs(self._cache_dir, exist_ok=True)
        _log(f"Cache dir: {self._cache_dir}")

    def _build_ui(self):
        self.setWindowTitle("视频预览工具 — Video Preview GUI")
        self.setMinimumSize(900, 600)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.folder_bar = FolderBar()
        main_layout.addWidget(self.folder_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.folder_tree = FolderTree()
        self.folder_tree.setMinimumWidth(140)

        self.video_grid = VideoGrid()
        self.video_grid.set_columns(self.config.columns_per_row)

        splitter.addWidget(self.folder_tree)
        splitter.addWidget(self.video_grid)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 1060])

        main_layout.addWidget(splitter, 1)

        self.pagination = PaginationBar()
        main_layout.addWidget(self.pagination)

        self.status_bar = QStatusBar()
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #999; padding: 2px 8px;")
        self.status_bar.addWidget(self.status_label)
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet("QStatusBar { background: #252525; border-top: 1px solid #333; }")

        self._apply_dark_theme()
        _log("UI built")

    def _setup_menu(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("QMenuBar { background: #2b2b2b; color: #ddd; } QMenuBar::item:selected { background: #444; }")

        file_menu = menubar.addMenu("文件(&F)")
        open_action = QAction("打开文件夹...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.folder_bar._browse)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        settings_menu = menubar.addMenu("设置(&S)")
        pref_action = QAction("预览参数...", self)
        pref_action.triggered.connect(self._open_settings)
        settings_menu.addAction(pref_action)

        help_menu = menubar.addMenu("帮助(&H)")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _connect_signals(self):
        self.folder_bar.directory_changed.connect(self._on_directory_changed)
        self.folder_tree.directory_selected.connect(self._on_folder_tree_selected)
        self.pagination.page_changed.connect(self._on_page_changed)
        self.pagination.items_per_page_changed.connect(self._on_items_per_page_changed)
        self.video_grid.video_double_clicked.connect(self._open_video_default)
        self.video_grid.copy_path_requested.connect(self._on_path_copied)
        _log("Signals connected")

    def _restore_state(self):
        self.resize(self.config.window_width, self.config.window_height)
        start_dir = self.config.last_directory if (self.config.last_directory and os.path.isdir(self.config.last_directory)) else os.path.expanduser("~")
        _log(f"Restore state, navigate to: {start_dir}")
        self._navigate_to(start_dir)

    # ─── Navigation ────────────────────────────────────────

    def _navigate_to(self, path: str):
        normalized = normalize_path(path)
        _log(f"Navigate to: {normalized}")

        self.folder_bar.set_directory(normalized)
        self.folder_tree.set_directory(normalized)
        self.config.last_directory = normalized
        self.config.save()

        self._cancel_worker()

        self.status_label.setText("正在扫描视频文件...")
        QApplication.processEvents()

        self._all_videos = scan_videos(normalized)
        _log(f"Scanned {len(self._all_videos)} videos")

        self.video_grid.clear()

        if not self._all_videos:
            msg = f"当前目录无视频 — {normalized}"
            self.status_label.setText(msg)
            _log(f"No videos: {msg}")
            self.pagination.set_data(0)
            return

        self.status_label.setText(f"找到 {len(self._all_videos)} 个视频")

        # Sync pagination with current config (no signal triggering)
        self.pagination.set_items_per_page(self.config.items_per_page)
        self.pagination.set_data(len(self._all_videos))

        self._load_page(1)

    def _on_directory_changed(self, path: str):
        self._navigate_to(path)

    def _on_folder_tree_selected(self, path: str):
        self._navigate_to(path)

    # ─── Pagination ────────────────────────────────────────

    def _on_page_changed(self, page: int):
        self._load_page(page)

    def _on_items_per_page_changed(self, value: int):
        _log(f"Items per page changed: {value}")
        self.config.items_per_page = value
        self.config.save()
        self.video_grid.set_columns(self.config.columns_per_row)
        self.pagination.set_data(len(self._all_videos), 1)
        self._load_page(1)

    def _get_page_videos(self, page: int) -> list:
        per_page = self.pagination.items_per_page()
        start = (page - 1) * per_page
        end = start + per_page
        return self._all_videos[start:end]

    def _load_page(self, page: int):
        _log(f"Load page {page}, total videos: {len(self._all_videos)}")
        self._cancel_worker()

        self._current_page_videos = self._get_page_videos(page)
        _log(f"Page {page} has {len(self._current_page_videos)} videos")

        self.pagination.set_data(len(self._all_videos), page)

        if not self._current_page_videos:
            _log("No videos on this page, returning")
            return

        self.video_grid.set_columns(self.config.columns_per_row)
        self.video_grid.populate(self._current_page_videos)
        _log(f"Grid populated with {len(self._current_page_videos)} cards")

        self.status_label.setText(
            f"正在生成预览... (第 {page}/{self.pagination._total_pages} 页, "
            f"{len(self._current_page_videos)} 个视频)"
        )

        video_paths = [v.path for v in self._current_page_videos]
        _log(f"Creating worker for {len(video_paths)} videos")
        _log(f"  start={self.config.preview_start_sec}s dur={self.config.preview_duration_sec}s")

        self._worker = ThumbnailWorker()
        self._worker.setup(
            video_paths=video_paths,
            start_sec=self.config.preview_start_sec,
            duration_sec=self.config.preview_duration_sec,
            cache_dir=self._cache_dir,
        )
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.thumbnail_ready.connect(self._on_thumbnail_ready)
        self._worker.thumbnail_failed.connect(self._on_thumbnail_failed)
        self._worker.all_done.connect(self._on_worker_done)
        self._worker.start()
        _log("Worker started")

    def _cancel_worker(self):
        if self._worker:
            if self._worker.isRunning():
                _log("Cancelling running worker...")
                self._worker.cancel()
                self._worker.wait(3000)
                _log("Worker cancelled")
            # Disconnect to avoid stale signals
            try:
                self._worker.progress.disconnect()
                self._worker.thumbnail_ready.disconnect()
                self._worker.thumbnail_failed.disconnect()
                self._worker.all_done.disconnect()
            except Exception:
                pass
            self._worker = None

    # ─── Worker Callbacks ──────────────────────────────────

    def _on_worker_progress(self, current: int, total: int):
        self.status_label.setText(f"生成预览中... {current}/{total}")

    def _on_thumbnail_ready(self, video_path: str, strip_path: str):
        _log(f"Thumbnail ready: {os.path.basename(video_path)} -> {strip_path}")
        self.video_grid.update_card_thumbnail(video_path, strip_path)

    def _on_thumbnail_failed(self, video_path: str):
        _log(f"Thumbnail FAILED: {os.path.basename(video_path)}")
        self.video_grid.mark_card_error(video_path)

    def _on_worker_done(self):
        _log("Worker ALL DONE")
        self.status_label.setText(
            f"就绪 — {len(self._all_videos)} 个视频, "
            f"第 {self.pagination.current_page()}/{self.pagination._total_pages} 页"
        )

    # ─── Actions ───────────────────────────────────────────

    def _open_video_default(self, path: str):
        try:
            _open_file_default(path)
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"无法打开视频文件:\n{path}\n\n{e}")

    def _on_path_copied(self, path: str):
        self.status_label.setText(f"✅ 已复制路径: {path}")
        QTimer.singleShot(3000, self._reset_status)

    def _reset_status(self):
        self.status_label.setText(
            f"就绪 — {len(self._all_videos)} 个视频, "
            f"第 {self.pagination.current_page()}/{self.pagination._total_pages} 页"
        )

    def _open_settings(self):
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            _log("Settings applied, reloading page")
            self.video_grid.set_columns(self.config.columns_per_row)
            # Use set_items_per_page to handle custom values gracefully
            self.pagination.set_items_per_page(self.config.items_per_page)
            self.pagination.set_data(len(self._all_videos), 1)
            self._load_page(1)

    def _show_about(self):
        QMessageBox.about(
            self,
            "关于 视频预览工具",
            "<h3>Video Preview GUI v0.1</h3>"
            "<p>批量视频预览帧条生成工具。</p>"
            "<p>支持多种视频格式，可按目录浏览、翻页查看，"
            "自定义预览起始时间和时长。</p>"
            "<p>快捷键: Ctrl+O 打开文件夹 | ← → 翻页</p>",
        )

    # ─── Theme ─────────────────────────────────────────────

    def _apply_dark_theme(self):
        dark = """
            QMainWindow { background: #1e1e1e; }
            QWidget { color: #ddd; font-size: 13px; }
            QLineEdit {
                background: #333; color: #ddd; border: 1px solid #555;
                border-radius: 4px; padding: 4px 8px;
            }
            QLineEdit:focus { border: 1px solid #6af; }
            QPushButton {
                background: #3a3a3a; color: #ddd; border: 1px solid #555;
                border-radius: 4px; padding: 4px 12px;
            }
            QPushButton:hover { background: #4a4a4a; border: 1px solid #6af; }
            QPushButton:pressed { background: #555; }
            QPushButton:disabled { background: #2a2a2a; color: #666; }
            QListWidget {
                background: #252525; color: #ccc;
                border: 1px solid #333; border-radius: 4px;
            }
            QListWidget::item { padding: 6px 8px; }
            QListWidget::item:selected { background: #3a5a8c; color: #fff; }
            QListWidget::item:hover { background: #333; }
            QScrollBar:vertical {
                background: #1e1e1e; width: 10px;
            }
            QScrollBar::handle:vertical {
                background: #444; border-radius: 5px; min-height: 20px;
            }
            QScrollBar::handle:vertical:hover { background: #555; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QComboBox {
                background: #333; color: #ddd; border: 1px solid #555;
                border-radius: 4px; padding: 2px 6px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #333; color: #ddd; selection-background-color: #3a5a8c;
            }
            QGroupBox {
                color: #ccc; border: 1px solid #444; border-radius: 6px;
                margin-top: 12px; padding-top: 16px; font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 12px; padding: 0 4px;
            }
            QMenu {
                background: #2b2b2b; color: #ddd; border: 1px solid #444;
            }
            QMenu::item:selected { background: #3a5a8c; }
            QSplitter::handle { background: #555; width: 4px; }
            QSplitter::handle:hover { background: #6af; }
        """
        self.setStyleSheet(dark)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Left:
            self.pagination._go_prev()
        elif event.key() == Qt.Key.Key_Right:
            self.pagination._go_next()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self._cancel_worker()
        self.config.window_width = self.width()
        self.config.window_height = self.height()
        self.config.save()
        _log("Window closing")
        super().closeEvent(event)
