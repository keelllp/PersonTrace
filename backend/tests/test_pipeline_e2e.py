"""Full pipeline against REAL models (yolo11n + buffalo_l + osnet).
Run explicitly: python -m pytest -m slow -v   (takes ~1-3 minutes on CPU)"""
import cv2
import numpy as np
import pytest
from skimage import data

from app.models import Job, Person, Sighting, User
from app.pipeline.runner import default_models, run_pipeline
from app.storage import job_key

from .fakes import FakeStorage
from .video_utils import make_person_video

pytestmark = pytest.mark.slow


def test_finds_astronaut_in_video(session_factory, tmp_path):
    storage = FakeStorage()
    video_bytes = make_person_video(tmp_path / "clip.mp4").read_bytes()

    astronaut = cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR)
    ok, photo_jpg = cv2.imencode(".jpg", astronaut)
    assert ok

    with session_factory() as db:
        user = User(email="e2e@test.com", password_hash="x")
        job = Job(user=user, video_key="", video_filename="clip.mp4",
                  status="processing")
        db.add(user)
        db.flush()
        job.video_key = job_key(user.id, job.id, "video.mp4")
        person = Person(job_id=job.id, name="Eileen", color="#4f9cf0", photo_keys=[])
        db.add(person)
        db.flush()
        photo_key = job_key(user.id, job.id, f"persons/{person.id}/photo_0.jpg")
        person.photo_keys = [photo_key]
        db.commit()
        job_id, person_id, user_id = job.id, person.id, user.id

    storage.put_bytes(job_key(user_id, job_id, "video.mp4"), video_bytes)
    storage.put_bytes(photo_key, photo_jpg.tobytes())

    run_pipeline(job_id, lambda: False, storage=storage,
                 session_factory=session_factory, models=default_models())

    with session_factory() as db:
        person = db.get(Person, person_id)
        assert person.face_gallery_ok is True

        sightings = db.query(Sighting).filter_by(person_id=person_id).all()
        assert len(sightings) >= 1, "pipeline failed to find the person at all"
        total_covered = sum(s.end_s - s.start_s for s in sightings)
        assert total_covered >= 2.0, f"only covered {total_covered:.1f}s of ~5s"
        for s in sightings:
            assert s.match_type in ("face", "body")
            assert s.confidence > 0.3
            assert storage.head(s.screenshot_key) > 1000  # a real jpeg, not a stub
