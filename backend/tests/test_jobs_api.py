import json

from app.models import Job, Person, Sighting


def create_job(client, n_persons=1):
    files = [("video", ("clip.mp4", b"fake-video-bytes", "video/mp4"))]
    persons = [{"name": f"Person{i}"} for i in range(n_persons)]
    for i in range(n_persons):
        files.append((f"photos_{i}", (f"p{i}.jpg", b"fake-jpg", "image/jpeg")))
    r = client.post("/api/jobs", data={"persons": json.dumps(persons)}, files=files)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_job_uploads_blobs_and_enqueues(auth_client, fake_storage, processor_calls):
    client = auth_client()
    body = create_job(client, n_persons=2)
    job_id = body["job_id"]

    video_keys = [k for k in fake_storage.objects if k.endswith("video.mp4")]
    photo_keys = [k for k in fake_storage.objects if "/persons/" in k]
    assert len(video_keys) == 1 and job_id in video_keys[0]
    assert len(photo_keys) == 2
    assert processor_calls == [job_id]


def test_create_job_requires_auth(client):
    r = client.post("/api/jobs", data={"persons": "[]"})
    assert r.status_code == 401


def test_create_job_rejects_bad_payloads(auth_client):
    client = auth_client()
    # no persons
    r = client.post(
        "/api/jobs",
        data={"persons": "[]"},
        files=[("video", ("c.mp4", b"x", "video/mp4"))],
    )
    assert r.status_code == 422
    # person without photos
    r = client.post(
        "/api/jobs",
        data={"persons": json.dumps([{"name": "A"}])},
        files=[("video", ("c.mp4", b"x", "video/mp4"))],
    )
    assert r.status_code == 422
    # bad video extension
    r = client.post(
        "/api/jobs",
        data={"persons": json.dumps([{"name": "A"}])},
        files=[
            ("video", ("c.exe", b"x", "application/octet-stream")),
            ("photos_0", ("p.jpg", b"x", "image/jpeg")),
        ],
    )
    assert r.status_code == 422


def test_photo_validator_warnings_surface(app, auth_client):
    app.state.photo_validator = lambda data: False
    client = auth_client()
    body = create_job(client)
    assert len(body["warnings"]) == 1
    assert "Person0" in body["warnings"][0]


def test_list_and_get_scoped_to_owner(auth_client, client):
    c = auth_client(email="owner@test.com")
    job_id = create_job(c)["job_id"]

    listing = c.get("/api/jobs").json()
    assert [j["id"] for j in listing] == [job_id]
    person = listing[0]["persons"][0]
    assert person["name"] == "Person0"
    assert person["color"].startswith("#")
    assert person["photo_url"].startswith(f"/api/media/{job_id}/persons/")
    assert "duration_s" in listing[0]

    c.post("/api/auth/logout")
    c.post("/api/auth/register", json={"email": "other@test.com", "password": "secret123"})
    assert c.get("/api/jobs").json() == []
    assert c.get(f"/api/jobs/{job_id}").status_code == 404
    assert c.delete(f"/api/jobs/{job_id}").status_code == 404


def test_upload_over_size_cap_413(auth_client):
    import json as _json

    from app.config import settings

    client = auth_client()
    original = settings.max_upload_mb
    settings.max_upload_mb = 1
    try:
        big = b"x" * (1024 * 1024 + 1)
        r = client.post(
            "/api/jobs",
            data={"persons": _json.dumps([{"name": "A"}])},
            files=[
                ("video", ("c.mp4", big, "video/mp4")),
                ("photos_0", ("p.jpg", b"x", "image/jpeg")),
            ],
        )
        assert r.status_code == 413
    finally:
        settings.max_upload_mb = original


def test_cancel_processing_returns_cancelling(auth_client, session_factory):
    client = auth_client()
    job_id = create_job(client)["job_id"]
    with session_factory() as db:
        db.get(Job, job_id).status = "processing"
        db.commit()
    r = client.post(f"/api/jobs/{job_id}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelling"


def test_results_409_until_done_then_returns_sightings(auth_client, session_factory):
    client = auth_client()
    job_id = create_job(client)["job_id"]

    with session_factory() as db:
        job = db.get(Job, job_id)
        job.status = "processing"
        db.commit()
    assert client.get(f"/api/jobs/{job_id}/results").status_code == 409

    with session_factory() as db:
        job = db.get(Job, job_id)
        job.status = "done"
        job.duration_s, job.fps, job.width, job.height = 10.0, 30.0, 1920, 1080
        person = job.persons[0]
        person.sightings.append(
            Sighting(
                start_s=1.0, end_s=2.5, confidence=0.9, match_type="face",
                screenshot_key=f"users/{job.user_id}/jobs/{job_id}/screenshots/s.jpg",
                thumbnail_key=f"users/{job.user_id}/jobs/{job_id}/screenshots/t.jpg",
                box={"x": 1, "y": 2, "w": 3, "h": 4, "frame_s": 1.5},
            )
        )
        db.commit()

    r = client.get(f"/api/jobs/{job_id}/results")
    assert r.status_code == 200
    body = r.json()
    assert body["video"]["duration_s"] == 10.0
    sighting = body["persons"][0]["sightings"][0]
    assert sighting["match_type"] == "face"
    assert sighting["screenshot_url"] == f"/api/media/{job_id}/screenshots/s.jpg"


def test_cancel_queued_job(auth_client, session_factory):
    client = auth_client()
    job_id = create_job(client)["job_id"]
    with session_factory() as db:
        db.get(Job, job_id).status = "queued"
        db.commit()
    r = client.post(f"/api/jobs/{job_id}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_delete_job_removes_rows_and_blobs(auth_client, fake_storage, session_factory):
    client = auth_client()
    job_id = create_job(client)["job_id"]
    assert client.delete(f"/api/jobs/{job_id}").status_code == 204
    assert all(job_id not in k for k in fake_storage.objects)
    with session_factory() as db:
        assert db.get(Job, job_id) is None


def test_failed_create_leaves_no_blobs(auth_client, fake_storage):
    client = auth_client()
    files = [
        ("video", ("c.mp4", b"x", "video/mp4")),
        ("photos_0", ("p.jpg", b"x", "image/jpeg")),
        ("photos_0", ("bad.exe", b"x", "application/octet-stream")),
    ]
    r = client.post(
        "/api/jobs", data={"persons": json.dumps([{"name": "A"}])}, files=files
    )
    assert r.status_code == 422
    assert fake_storage.objects == {}


def test_delete_processing_job_409(auth_client, session_factory):
    client = auth_client()
    job_id = create_job(client)["job_id"]
    with session_factory() as db:
        db.get(Job, job_id).status = "processing"
        db.commit()
    assert client.delete(f"/api/jobs/{job_id}").status_code == 409


def test_cancel_terminal_job_409(auth_client):
    client = auth_client()
    job_id = create_job(client)["job_id"]  # inline processor marks it done
    assert client.post(f"/api/jobs/{job_id}/cancel").status_code == 409
