"""Video preview generator - extracts frames and creates animated GIF / frame strip images."""

import hashlib
import os
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image


PREVIEW_MAX_WIDTH = 240
PREVIEW_MAX_HEIGHT = 180
GIF_FPS = 5  # frames per second for animated GIF


def generate_animated_gif(
    video_path: str,
    start_sec: float,
    duration_sec: float,
    cache_dir: Optional[str] = None,
) -> Optional[str]:
    """Generate an animated GIF preview from a video segment.

    Tries OpenCV first. If all frames are black (codec issue), falls back
    to system ffmpeg for frame extraction.
    """
    cache_key = _cache_key(video_path, start_sec, duration_sec, 0)
    cache_name = f"{cache_key}_gif.gif"
    if cache_dir:
        cached = _check_cache(cache_dir, cache_name)
        if cached:
            return cached

    frames = _extract_animation_frames(video_path, start_sec, duration_sec)

    # Detect all-black output (OpenCV decoder failure for this codec)
    if frames and _all_frames_dark(frames):
        frames = _extract_frames_ffmpeg(video_path, start_sec, duration_sec)

    if not frames:
        return None

    frame_duration_ms = int(1000.0 / GIF_FPS)

    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        out_path = os.path.join(cache_dir, cache_name)
    else:
        import tempfile
        fd, out_path = tempfile.mkstemp(suffix=".gif", prefix="pv_")
        os.close(fd)

    frames[0].save(
        out_path,
        save_all=True,
        append_images=frames[1:],
        duration=frame_duration_ms,
        loop=0,
        optimize=False,
        disposal=2,
    )
    return out_path


def generate_frame_strip(
    video_path: str,
    start_sec: float,
    duration_sec: float,
    frame_count: int,
    strip_width: int = 400,
    cache_dir: Optional[str] = None,
) -> Optional[str]:
    """Generate a horizontal frame strip (static) - kept as fallback."""
    cache_key = _cache_key(video_path, start_sec, duration_sec, frame_count)
    cache_name = f"{cache_key}.png"
    if cache_dir:
        cached = _check_cache(cache_dir, cache_name)
        if cached:
            return cached

    frames = _extract_frames(video_path, start_sec, duration_sec, frame_count)
    if not frames:
        return None

    strip = _composite_frames(frames, strip_width)

    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        out_path = os.path.join(cache_dir, cache_name)
        strip.save(out_path, "PNG")
        return out_path

    import tempfile
    fd, out_path = tempfile.mkstemp(suffix=".png", prefix="pvstrip_")
    os.close(fd)
    strip.save(out_path, "PNG")
    return out_path


def _extract_animation_frames(
    video_path: str,
    start_sec: float,
    duration_sec: float,
) -> list[Image.Image]:
    """Extract frames at GIF_FPS rate. Handles short videos and bad seeking."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if fps <= 0 or total_frames <= 0:
            return []

        video_duration = total_frames / fps

        # ── Edge cases ──
        effective_start, effective_duration = _resolve_time_window(
            start_sec, duration_sec, video_duration
        )
        if effective_duration <= 0:
            return []

        # Number of frames to sample
        num_frames = max(3, int(effective_duration * GIF_FPS))

        # Time positions (evenly spaced)
        if num_frames <= 1:
            positions_sec = [effective_start + effective_duration / 2]
        else:
            step = effective_duration / (num_frames - 1)
            positions_sec = [effective_start + i * step for i in range(num_frames)]

        frames: list[Image.Image] = []
        last_good_frame: Image.Image | None = None

        for pos_sec in positions_sec:
            img = _read_frame_at_time(cap, pos_sec, fps, total_frames)

            if img is None and last_good_frame is not None:
                # Reuse last good frame (video might have bad frame at boundary)
                img = last_good_frame.copy()

            if img is not None:
                last_good_frame = img
                frames.append(img)

        # Fallback: if all frames are black/empty, read sequentially from start
        if not frames or _all_frames_dark(frames):
            frames = _read_sequential_frames(cap, fps, total_frames, num_frames)

        return frames
    finally:
        cap.release()


def _read_frame_at_time(
    cap: cv2.VideoCapture,
    time_sec: float,
    fps: float,
    total_frames: int,
) -> Optional[Image.Image]:
    """Read a single frame at a specific time, with multi-method fallback."""
    target_ms = time_sec * 1000.0
    best: np.ndarray | None = None

    # Method 1: time-based seeking (most reliable for h264/mp4)
    cap.set(cv2.CAP_PROP_POS_MSEC, target_ms)
    for attempt in range(6):
        ret, bgr = cap.read()
        if not ret or bgr is None:
            continue
        if not _is_black_frame(bgr):
            best = bgr
            break
        if best is None:
            best = bgr  # keep first non-None even if dark

    if best is not None and not _is_black_frame(best):
        return _bgr_to_thumbnail(best)

    # Method 2: frame-based seeking with neighbor scan
    frame_idx = max(0, min(int(time_sec * fps), total_frames - 1))
    for offset in range(0, min(30, total_frames - frame_idx)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx + offset)
        ret, bgr = cap.read()
        if ret and bgr is not None and not _is_black_frame(bgr):
            return _bgr_to_thumbnail(bgr)

    # Method 3: reset to start and read sequentially
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    for _ in range(min(60, total_frames)):
        ret, bgr = cap.read()
        if ret and bgr is not None and not _is_black_frame(bgr):
            return _bgr_to_thumbnail(bgr)

    # Method 4: accept anything
    if best is not None:
        return _bgr_to_thumbnail(best)

    return None


def _read_sequential_frames(
    cap: cv2.VideoCapture,
    fps: float,
    total_frames: int,
    num_frames: int,
) -> list[Image.Image]:
    """Fallback: read frames sequentially from the start of the video."""
    frames = []
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    if num_frames >= total_frames:
        # Read all frames
        step = 1
        indices = list(range(total_frames))
    else:
        step = total_frames // num_frames
        indices = [i * step for i in range(num_frames)]

    for target_idx in indices:
        # Seek to approximate position
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_idx)
        ret, bgr = cap.read()
        if ret and bgr is not None:
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            img.thumbnail((PREVIEW_MAX_WIDTH, PREVIEW_MAX_HEIGHT), Image.LANCZOS)
            frames.append(img)

    return frames


def _is_black_frame(bgr: np.ndarray) -> bool:
    """Check if a frame is essentially black (all pixels near zero)."""
    if bgr is None:
        return True
    return np.mean(bgr) < 5.0


def _bgr_to_thumbnail(bgr: np.ndarray) -> Image.Image:
    """Convert BGR numpy frame to thumbnail PIL Image."""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(rgb)
    img.thumbnail((PREVIEW_MAX_WIDTH, PREVIEW_MAX_HEIGHT), Image.LANCZOS)
    return img


def _all_frames_dark(frames: list[Image.Image]) -> bool:
    """Check if all extracted frames are too dark."""
    if not frames:
        return True
    for f in frames:
        arr = np.array(f)
        if np.mean(arr) > 10.0:
            return False
    return True


def _extract_frames_ffmpeg(
    video_path: str,
    start_sec: float,
    duration_sec: float,
) -> list[Image.Image]:
    """Fallback: use system ffmpeg to extract frames when OpenCV fails.

    Uses ffmpeg fps filter to extract frames at GIF_FPS rate in a single pass.
    """
    import shutil
    import subprocess
    import tempfile
    from pathlib import Path

    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        return []

    # Probe video duration
    ffprobe_bin = shutil.which("ffprobe")
    cmd_probe = [
        ffprobe_bin or ffmpeg_bin,
        "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        video_path,
    ] if ffprobe_bin else None

    video_duration = start_sec + duration_sec
    if cmd_probe:
        try:
            result = subprocess.run(cmd_probe, capture_output=True, text=True, timeout=15)
            video_duration = float(result.stdout.strip())
        except Exception:
            pass

    effective_start, effective_duration = _resolve_time_window(
        start_sec, duration_sec, video_duration
    )
    if effective_duration <= 0:
        return []

    num_frames = max(3, int(effective_duration * GIF_FPS))
    frames: list[Image.Image] = []

    with tempfile.TemporaryDirectory(prefix="pv_ff_") as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Single ffmpeg pass: trim + fps filter → N PNG files
        cmd = [
            ffmpeg_bin,
            "-ss", str(effective_start),
            "-i", video_path,
            "-t", str(effective_duration),
            "-vf", f"fps={GIF_FPS}",
            "-loglevel", "error",
            str(tmpdir_path / "frame_%04d.png"),
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=60)
        except Exception:
            pass

        # Read all generated frames
        png_files = sorted(tmpdir_path.glob("frame_*.png"))
        if png_files:
            for png in png_files[:num_frames]:
                try:
                    img = Image.open(png)
                    img.thumbnail((PREVIEW_MAX_WIDTH, PREVIEW_MAX_HEIGHT), Image.LANCZOS)
                    frames.append(img)
                except Exception:
                    continue

    return frames


def _resolve_time_window(
    start_sec: float,
    duration_sec: float,
    video_duration: float,
) -> tuple[float, float]:
    """Resolve start time and duration considering video length.

    Returns (effective_start, effective_duration).
    """
    # If video is shorter than start_sec: use last possible segment
    if start_sec >= video_duration:
        # Use the last `duration_sec` of the video
        effective_start = max(0.0, video_duration - duration_sec)
        effective_duration = min(duration_sec, video_duration - effective_start)
        return effective_start, effective_duration

    # Normal case: start is within video
    remaining = video_duration - start_sec
    effective_duration = min(duration_sec, remaining)
    effective_start = start_sec
    return effective_start, effective_duration


def _extract_frames(
    video_path: str,
    start_sec: float,
    duration_sec: float,
    frame_count: int,
) -> list[Image.Image]:
    """Extract evenly-spaced frames from a video segment (for static strip)."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if fps <= 0 or total_frames <= 0:
            return []

        video_duration = total_frames / fps
        effective_start, effective_duration = _resolve_time_window(
            start_sec, duration_sec, video_duration
        )
        if effective_duration <= 0:
            return []

        if frame_count <= 1:
            positions_sec = [effective_start + effective_duration / 2]
        else:
            step = effective_duration / (frame_count - 1)
            positions_sec = [effective_start + i * step for i in range(frame_count)]

        frames: list[Image.Image] = []
        for pos_sec in positions_sec:
            img = _read_frame_at_time(cap, pos_sec, fps, total_frames)
            if img is not None:
                frames.append(img)

        return frames
    finally:
        cap.release()


def _composite_frames(frames: list[Image.Image], strip_width: int) -> Image.Image:
    if not frames:
        raise ValueError("No frames to composite")

    total_frames = len(frames)
    gap = 2
    available_width = strip_width - gap * (total_frames - 1)
    frame_width = max(1, available_width // total_frames)

    first = frames[0]
    aspect = first.height / max(1, first.width)
    frame_height = max(1, int(frame_width * aspect))

    resized = [f.resize((frame_width, frame_height), Image.LANCZOS) for f in frames]

    total_width = frame_width * total_frames + gap * (total_frames - 1)
    composite = Image.new("RGB", (total_width, frame_height), color=(30, 30, 30))

    x = 0
    for img in resized:
        composite.paste(img, (x, 0))
        x += frame_width + gap

    return composite


def _cache_key(video_path: str, start_sec: float, duration_sec: float, frame_count: int) -> str:
    raw = f"{video_path}|{start_sec:.2f}|{duration_sec:.2f}|{frame_count}"
    return hashlib.md5(raw.encode()).hexdigest()


def _check_cache(cache_dir: str, key: str) -> Optional[str]:
    """Check if a cached preview file exists."""
    path = os.path.join(cache_dir, key)
    if os.path.isfile(path):
        return path
    return None
