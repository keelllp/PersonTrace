import numpy as np
import pytest

from app.jobs import JobCancelled
from app.models import Job, Person, Sighting, User
from app.pipeline.runner import PipelineModels, run_pipeline
from app.storage import job_key

from .fakes import FakeStorage
from .video_utils import make_test_video


def unit(seed):
    rng = np.random.default_rng(seed)
    v = rng.normal(size=512).astype(np.float32)
    return v / np.linalg.norm(v)


FACE_VEC = unit(1)
BODY_VEC = unit(2)


class FakeDetector:
    """Reports one person track covering the middle of every frame."""

    def track(self, frame):
        h, w = frame.shape[:2]
        return [(1, (w * 0.3, h * 0.2, w * 0.6, h * 0.9), 0.9)]

    def detect(self, image):
        h, w = image.shape[:2]
        return [((w * 0.25, h * 0.1, w * 0.75, h * 0.95), 0.9)]


class FakeFace:
    def best_embedding(self, bgr):
        return FACE_VEC.copy()

    def faces(self, bgr):
        return [((0.0, 0.0, 50.0, 50.0), 0.99, FACE_VEC.copy())]


class FakeBody:
    def embed_crop(self, crop):
        return BODY_VEC.copy()


@pytest.fixture()
def pipeline_env(session_factory, tmp_path):
    storage = FakeStorage()
    video_bytes = make_test_video(tmp_path / "clip.mp4", seconds=2.0).read_bytes()

    with session_factory() as db:
        user = User(email="p@test.com", password_hash="x")
        job = Job(user=user, video_key="", video_filename="clip.mp4", status="processing")
        db.add(user)
        db.flush()
        job.video_key = job_key(user.id, job.id, "video.mp4")
        person = Person(job_id=job.id, name="Alice", color="#e05252", photo_keys=[])
        db.add(person)
        db.flush()
        photo_key = job_key(user.id, job.id, f"persons/{person.id}/photo_0.jpg")
        person.photo_keys = [photo_key]
        db.commit()
        job_id, person_id, user_id = job.id, person.id, user.id

    storage.put_bytes(job_key(user_id, job_id, "video.mp4"), video_bytes)
    import cv2

    photo = np.random.default_rng(0).integers(0, 255, (300, 200, 3)).astype(np.uint8)
    ok, jpg = cv2.imencode(".jpg", photo)
    storage.put_bytes(job_key(user_id, job_id, f"persons/{person_id}/photo_0.jpg"), jpg.tobytes())

    models = PipelineModels(detector=FakeDetector(), face=FakeFace(), body=FakeBody())
    return storage, job_id, person_id, models


def test_pipeline_produces_sightings_and_screenshots(pipeline_env, session_factory):
    storage, job_id, person_id, models = pipeline_env
    run_pipeline(job_id, lambda: False, storage=storage,
                 session_factory=session_factory, models=models)

    with session_factory() as db:
        job = db.get(Job, job_id)
        assert job.duration_s == pytest.approx(2.0, abs=0.2)
        assert job.fps == pytest.approx(24, abs=1)
        assert job.width == 320 and job.height == 240
        assert job.stage == "render"

        person = db.get(Person, person_id)
        assert person.face_gallery_ok is True

        sightings = db.query(Sighting).filter_by(person_id=person_id).all()
        assert len(sightings) >= 1
        s = sightings[0]
        assert 0.0 <= s.start_s <= s.end_s <= 2.2
        assert s.match_type == "face"
        assert s.confidence > 0.9
        assert set(s.box) == {"x", "y", "w", "h", "frame_s"}
        assert storage.head(s.screenshot_key) > 0
        assert storage.head(s.thumbnail_key) > 0


def test_pipeline_cancellation_raises_jobcancelled(pipeline_env, session_factory):
    storage, job_id, _, models = pipeline_env
    with pytest.raises(JobCancelled):
        run_pipeline(job_id, lambda: True, storage=storage,
                     session_factory=session_factory, models=models)


def test_pipeline_corrupt_video_raises_readable_error(pipeline_env, session_factory):
    storage, job_id, _, models = pipeline_env
    with session_factory() as db:
        video_key = db.get(Job, job_id).video_key
    storage.put_bytes(video_key, b"garbage bytes, not a video")
    with pytest.raises(Exception, match="unsupported or corrupt"):
        run_pipeline(job_id, lambda: False, storage=storage,
                     session_factory=session_factory, models=models)


def test_pipeline_below_threshold_yields_no_sightings(pipeline_env, session_factory):
    """No face in the reference photo, and body embeddings that never agree:
    the person ends with a body-only gallery and zero sightings."""
    storage, job_id, person_id, models = pipeline_env

    class NoFace:
        def best_embedding(self, bgr):
            return None

        def faces(self, bgr):
            return []

    class DisjointBody:
        def __init__(self):
            self.calls = 0

        def embed_crop(self, crop):
            self.calls += 1
            return unit(100 + self.calls)  # every embedding dissimilar to all others

    models = PipelineModels(
        detector=models.detector, face=NoFace(), body=DisjointBody()
    )
    run_pipeline(job_id, lambda: False, storage=storage,
                 session_factory=session_factory, models=models)
    with session_factory() as db:
        person = db.get(Person, person_id)
        assert person.face_gallery_ok is False
        assert person.body_gallery_ok is True  # photo still yielded a body crop
        assert db.query(Sighting).filter_by(person_id=person_id).all() == []
