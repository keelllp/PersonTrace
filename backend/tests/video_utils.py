import cv2
import numpy as np


def make_test_video(path, seconds=2.0, fps=24, size=(320, 240)):
    """Write an mp4 of a white rectangle sliding across a black background."""
    width, height = size
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )
    if not writer.isOpened():
        raise RuntimeError("cv2.VideoWriter failed to open (mp4v codec missing?)")
    total = int(seconds * fps)
    for i in range(total):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        x = int((width - 60) * i / max(total - 1, 1))
        cv2.rectangle(frame, (x, 60), (x + 60, 180), (255, 255, 255), -1)
        writer.write(frame)
    writer.release()
    return path
