"""Settings dialog for preview parameters."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)


class SettingsDialog(QDialog):
    """Dialog to configure preview start time, duration, and grid layout."""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._block_signals = False
        self.setWindowTitle("预览设置")
        self.setMinimumWidth(380)
        self._build_ui()
        self._load_config()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Preview group
        preview_group = QGroupBox("视频预览参数")
        preview_form = QFormLayout(preview_group)

        self.spin_start = QDoubleSpinBox()
        self.spin_start.setRange(0, 99999)
        self.spin_start.setDecimals(1)
        self.spin_start.setSuffix(" 秒")
        self.spin_start.setToolTip("从视频的哪个时间点开始生成预览")

        self.spin_duration = QDoubleSpinBox()
        self.spin_duration.setRange(0.5, 99999)
        self.spin_duration.setDecimals(1)
        self.spin_duration.setSuffix(" 秒")
        self.spin_duration.setToolTip("预览片段的总时长（动画GIF播放时长）")

        hint_label = QLabel("💡 预览以动画GIF形式播放，约5fps，循环播放\n短视频会自动适配时长，不会黑屏")
        hint_label.setStyleSheet("color: #888; font-size: 11px;")
        hint_label.setWordWrap(True)

        preview_form.addRow("起始时间:", self.spin_start)
        preview_form.addRow("预览时长:", self.spin_duration)
        preview_form.addRow("", hint_label)

        # Grid layout group
        grid_group = QGroupBox("每页网格（行×列 = 每页总数）")
        grid_form = QFormLayout(grid_group)

        self.spin_rows = QSpinBox()
        self.spin_rows.setRange(1, 20)
        self.spin_rows.setSuffix(" 行")
        self.spin_rows.setToolTip("每页显示的行数")
        self.spin_rows.valueChanged.connect(self._update_total)

        self.spin_cols = QSpinBox()
        self.spin_cols.setRange(1, 10)
        self.spin_cols.setSuffix(" 列")
        self.spin_cols.setToolTip("每页显示的列数")
        self.spin_cols.valueChanged.connect(self._update_total)

        self.label_total = QLabel()
        self.label_total.setStyleSheet("color: #6af; font-weight: bold;")

        grid_form.addRow("行数:", self.spin_rows)
        grid_form.addRow("列数:", self.spin_cols)
        grid_form.addRow("每页视频数:", self.label_total)

        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(preview_group)
        layout.addWidget(grid_group)
        layout.addStretch()
        layout.addWidget(self.button_box)

    def _load_config(self):
        self.spin_start.setValue(self.config.preview_start_sec)
        self.spin_duration.setValue(self.config.preview_duration_sec)
        self.spin_cols.setValue(self.config.columns_per_row)
        # Derive rows from items_per_page / columns
        rows = max(1, self.config.items_per_page // self.config.columns_per_row)
        self.spin_rows.setValue(rows)
        self._update_total()

    def _update_total(self):
        total = self.spin_rows.value() * self.spin_cols.value()
        self.label_total.setText(f"共 {total} 个视频")

    def _on_accept(self):
        self.config.preview_start_sec = self.spin_start.value()
        self.config.preview_duration_sec = self.spin_duration.value()
        self.config.columns_per_row = self.spin_cols.value()
        self.config.items_per_page = self.spin_rows.value() * self.spin_cols.value()
        self.config.save()
        self.accept()
