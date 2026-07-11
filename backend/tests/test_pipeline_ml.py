import cv2
import numpy as np
import pytest
from skimage import data

from app.pipeline.ml import (
    PersonDetector,
    get_body_embedder,
    get_face_engine,
)


@pytest.fixture(scope="module")
def astronaut_bgr():
    return cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR)


def test_person_detector_finds_astronaut(astronaut_bgr):
    detections = PersonDetector().detect(astronaut_bgr)
    assert len(detections) >= 1
    box, conf = detections[0]
    assert conf > 0.3
    x1, y1, x2, y2 = box
    assert x2 > x1 and y2 > y1


def test_face_engine_embeds_astronaut_deterministically(astronaut_bgr):
    engine = get_face_engine()
    emb1 = engine.best_embedding(astronaut_bgr)
    emb2 = engine.best_embedding(astronaut_bgr)
    assert emb1 is not None
    assert emb1.shape == (512,)
    assert abs(float(np.linalg.norm(emb1)) - 1.0) < 1e-3
    assert float(np.dot(emb1, emb2)) > 0.999


def test_face_engine_finds_no_face_in_noise():
    noise = np.random.default_rng(0).integers(0, 255, (512, 512, 3)).astype(np.uint8)
    assert get_face_engine().best_embedding(noise) is None


def test_validate_photo_bytes(astronaut_bgr):
    engine = get_face_engine()
    ok, jpg = cv2.imencode(".jpg", astronaut_bgr)
    assert ok
    assert engine.validate_photo_bytes(jpg.tobytes()) is True
    assert engine.validate_photo_bytes(b"not an image") is False


def test_body_embedder_contract(astronaut_bgr):
    embedder = get_body_embedder()
    crop = astronaut_bgr[:400, 100:350]
    emb = embedder.embed_crop(crop)
    assert emb.shape == (512,)
    assert abs(float(np.linalg.norm(emb)) - 1.0) < 1e-3
    emb2 = embedder.embed_crop(crop)
    assert float(np.dot(emb, emb2)) > 0.999


def test_tracker_assigns_stable_ids(astronaut_bgr):
    detector = PersonDetector()
    frame = cv2.resize(astronaut_bgr, (640, 480))
    ids = set()
    for _ in range(3):
        tracks = detector.track(frame)
        assert len(tracks) >= 1
        ids.add(tracks[0][0])
    assert len(ids) == 1  # same person, same id across frames
