"""Video file scanner - discovers video files and reads metadata."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".webm", ".flv", ".wmv", ".m4v", ".ts", ".3gp"}


@dataclass
class VideoInfo:
    """Metadata about a discovered video file."""

    path: str
    filename: str
    size_bytes: int
    duration_sec: float
    width: int
    height: int
    fps: float
    codec: str = ""
    mtime: float = 0.0

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)


def scan_videos(directory: str, sort_by: str = "name") -> list[VideoInfo]:
    """Scan a directory for video files (non-recursive).

    Args:
        directory: Path to scan.
        sort_by: Sort key - "name", "date", "size", "duration".

    Returns:
        List of VideoInfo objects.
    """
    videos: list[VideoInfo] = []
    dir_path = Path(directory)

    if not dir_path.is_dir():
        return videos

    for entry in dir_path.iterdir():
        if not entry.is_file():
            continue
        if entry.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        info = _probe_video(str(entry))
        if info is not None:
            videos.append(info)

    return _sort_videos(videos, sort_by)


def scan_subdirs(directory: str) -> list[str]:
    """List subdirectories in a directory.

    Returns:
        Sorted list of subdirectory absolute paths.
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        return []

    subdirs = []
    for entry in dir_path.iterdir():
        if entry.is_dir() and not entry.name.startswith("."):
            subdirs.append(str(entry))
    return sorted(subdirs, key=lambda p: p.lower())


def normalize_path(path_str: str) -> str:
    """Normalize a path string for display and comparison."""
    return str(Path(path_str).resolve())


def _probe_video(filepath: str) -> Optional[VideoInfo]:
    """Probe a video file for metadata using OpenCV."""
    cap = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        return None

    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        duration = frame_count / fps if fps > 0 else 0.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        codec_int = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec = "".join(chr((codec_int >> (8 * i)) & 0xFF) for i in range(4)).strip()
    finally:
        cap.release()

    path = Path(filepath)
    stat = path.stat()
    return VideoInfo(
        path=filepath,
        filename=path.name,
        size_bytes=stat.st_size,
        duration_sec=duration,
        width=width,
        height=height,
        fps=fps,
        codec=codec,
        mtime=stat.st_mtime,
    )


def _sort_videos(videos: list[VideoInfo], sort_by: str) -> list[VideoInfo]:
    match sort_by:
        case "date":
            return sorted(videos, key=lambda v: v.mtime, reverse=True)
        case "size":
            return sorted(videos, key=lambda v: v.size_bytes, reverse=True)
        case "duration":
            return sorted(videos, key=lambda v: v.duration_sec, reverse=True)
        case _:
            return sorted(videos, key=lambda v: v.filename.lower())
