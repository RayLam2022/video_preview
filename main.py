"""Video Preview GUI — entry point."""

import os
import sys
from pathlib import Path

# Suppress noisy OpenCV/FFmpeg warnings BEFORE any cv2 import
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8"

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from src.config import AppConfig
from src.app import MainWindow


def main():
    config = AppConfig()
    config.load()

    app = QApplication(sys.argv)
    app.setApplicationName("VideoPreviewGUI")

    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
