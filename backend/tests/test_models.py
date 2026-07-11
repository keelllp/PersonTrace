from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models import Base, User, Job, Person, Sighting


def make_engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return engine


def test_full_object_graph_roundtrip():
    engine = make_engine()
    with Session(engine) as s:
        user = User(email="a@b.com", password_hash="hash")
        job = Job(user=user, video_key="users/x/jobs/y/video.mp4", video_filename="clip.mp4")
        person = Person(job=job, name="Alice", color="#e05252", photo_keys=["k1", "k2"])
        person.sightings.append(
            Sighting(
                start_s=12.4, end_s=31.0, confidence=0.87, match_type="face",
                screenshot_key="s.jpg", thumbnail_key="t.jpg",
                box={"x": 412, "y": 96, "w": 180, "h": 420, "frame_s": 15.2},
            )
        )
        s.add(user)
        s.commit()

        loaded = s.scalars(select(Job)).one()
        assert loaded.status == "queued"
        assert loaded.progress_pct == 0.0
        assert len(loaded.user.id) == 32
        assert loaded.persons[0].photo_keys == ["k1", "k2"]
        assert loaded.persons[0].sightings[0].box["frame_s"] == 15.2


def test_cascade_delete_job_removes_persons_and_sightings():
    engine = make_engine()
    with Session(engine) as s:
        user = User(email="a@b.com", password_hash="hash")
        job = Job(user=user, video_key="k", video_filename="v.mp4")
        person = Person(job=job, name="Bob", color="#4f9cf0", photo_keys=[])
        person.sightings.append(
            Sighting(start_s=0, end_s=1, confidence=0.5, match_type="body",
                     screenshot_key="s", thumbnail_key="t", box={})
        )
        s.add(user)
        s.commit()
        s.delete(job)
        s.commit()
        assert s.scalars(select(Person)).all() == []
        assert s.scalars(select(Sighting)).all() == []
