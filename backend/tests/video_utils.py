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


def make_person_video(path, seconds=5.0, fps=24):
    """A real person (skimage astronaut, public-domain NASA photo) sliding
    across a gray background — detectable by YOLO and face-recognizable."""
    from skimage import data

    person = cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR)
    person = cv2.resize(person, (300, 300))
    width, height = 640, 480
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )
    if not writer.isOpened():
        raise RuntimeError("cv2.VideoWriter failed to open")
    total = int(seconds * fps)
    for i in range(total):
        frame = np.full((height, width, 3), 96, dtype=np.uint8)
        x = 40 + int(240 * i / max(total - 1, 1))
        frame[90:390, x : x + 300] = person
        writer.write(frame)
    writer.release()
    return path
