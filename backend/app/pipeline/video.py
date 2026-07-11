"""OpenCV video I/O and screenshot rendering. No ML, no app imports."""
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np


class VideoProbeError(Exception):
    pass


@dataclass
class VideoInfo:
    duration_s: float
    fps: float
    width: int
    height: int
    frame_count: int


def probe_video(path) -> VideoInfo:
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise VideoProbeError("Could not open video — unsupported or corrupt file")
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
            raise VideoProbeError("Video has no readable frames")
        return VideoInfo(frame_count / fps, fps, width, height, frame_count)
    finally:
        cap.release()


def iter_frames(path, stride: int) -> Iterator[tuple[int, float, np.ndarray]]:
    cap = cv2.VideoCapture(str(path))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        index = 0
        while True:
            if index % stride == 0:
                ok, frame = cap.read()
                if not ok:
                    return
                yield index, index / fps, frame
            else:
                if not cap.grab():
                    return
            index += 1
    finally:
        cap.release()


def downscale(frame: np.ndarray, max_width: int) -> tuple[np.ndarray, float]:
    height, width = frame.shape[:2]
    if width <= max_width:
        return frame, 1.0
    scale = width / max_width
    new_size = (max_width, round(height / scale))
    return cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA), scale


def extract_frame_at(path, time_s: float) -> np.ndarray | None:
    cap = cv2.VideoCapture(str(path))
    try:
        cap.set(cv2.CAP_PROP_POS_MSEC, time_s * 1000.0)
        ok, frame = cap.read()
        return frame if ok else None
    finally:
        cap.release()


def _hex_to_bgr(color_hex: str) -> tuple[int, int, int]:
    value = color_hex.lstrip("#")
    r, g, b = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return (b, g, r)


def annotate(frame, box_xyxy, label: str, color_hex: str) -> np.ndarray:
    out = frame.copy()
    color = _hex_to_bgr(color_hex)
    x1, y1, x2, y2 = (int(v) for v in box_xyxy)
    thickness = max(2, out.shape[1] // 640)
    cv2.rectangle(out, (x1, y1), (x2, y2), color, thickness)

    font, font_scale = cv2.FONT_HERSHEY_SIMPLEX, max(0.5, out.shape[1] / 1600)
    (tw, th), baseline = cv2.getTextSize(label, font, font_scale, thickness)
    frame_h, frame_w = out.shape[:2]
    ty = y1 - 8 if y1 - th - baseline - 8 >= 0 else y2 + th + baseline + 8
    ty = min(max(ty, th + baseline), frame_h - baseline - 2)
    bx = min(max(x1, 0), max(frame_w - tw - 8, 0))
    cv2.rectangle(
        out, (bx, ty - th - baseline), (bx + tw + 8, ty + baseline), color, -1
    )
    cv2.putText(
        out, label, (bx + 4, ty), font, font_scale, (255, 255, 255), thickness,
        cv2.LINE_AA,
    )
    return out


def save_jpeg_pair(frame, screenshot_path, thumbnail_path, thumb_width: int = 320):
    for path in (screenshot_path, thumbnail_path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(screenshot_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 90]):
        raise IOError(f"Failed to write screenshot: {screenshot_path}")
    height, width = frame.shape[:2]
    thumb_height = max(1, round(height * thumb_width / width))
    thumb = cv2.resize(frame, (thumb_width, thumb_height), interpolation=cv2.INTER_AREA)
    if not cv2.imwrite(str(thumbnail_path), thumb, [cv2.IMWRITE_JPEG_QUALITY, 80]):
        raise IOError(f"Failed to write thumbnail: {thumbnail_path}")
