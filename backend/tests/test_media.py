from .test_jobs_api import create_job


def put_media(fake_storage, client, job_id, rel_path, data):
    # keys are users/{uid}/jobs/{jid}/... — find uid from the video key
    video_key = next(k for k in fake_storage.objects if f"/jobs/{job_id}/" in k)
    prefix = video_key.split(f"/jobs/{job_id}/")[0] + f"/jobs/{job_id}/"
    fake_storage.objects[prefix + rel_path] = data
    return rel_path


def test_full_read_200_with_content_type(auth_client, fake_storage):
    client = auth_client()
    job_id = create_job(client)["job_id"]
    put_media(fake_storage, client, job_id, "screenshots/s.jpg", b"jpegbytes")

    r = client.get(f"/api/media/{job_id}/screenshots/s.jpg")
    assert r.status_code == 200
    assert r.content == b"jpegbytes"
    assert r.headers["content-type"] == "image/jpeg"
    assert r.headers["accept-ranges"] == "bytes"


def test_range_request_returns_206_with_content_range(auth_client, fake_storage):
    client = auth_client()
    job_id = create_job(client)["job_id"]

    r = client.get(
        f"/api/media/{job_id}/video.mp4", headers={"Range": "bytes=2-5"}
    )
    assert r.status_code == 206
    assert r.content == b"ke-v"  # b"fake-video-bytes"[2:6]
    assert r.headers["content-range"] == "bytes 2-5/16"


def test_open_ended_range(auth_client):
    client = auth_client()
    job_id = create_job(client)["job_id"]
    r = client.get(f"/api/media/{job_id}/video.mp4", headers={"Range": "bytes=10-"})
    assert r.status_code == 206
    assert r.content == b"-bytes"


def test_unsatisfiable_range_416(auth_client):
    client = auth_client()
    job_id = create_job(client)["job_id"]
    r = client.get(f"/api/media/{job_id}/video.mp4", headers={"Range": "bytes=99-"})
    assert r.status_code == 416


def test_suffix_range(auth_client):
    client = auth_client()
    job_id = create_job(client)["job_id"]
    r = client.get(f"/api/media/{job_id}/video.mp4", headers={"Range": "bytes=-5"})
    assert r.status_code == 206
    assert r.content == b"bytes"
    assert r.headers["content-range"] == "bytes 11-15/16"


def test_unsupported_range_syntax_falls_back_to_200(auth_client):
    client = auth_client()
    job_id = create_job(client)["job_id"]
    for header in ("bytes=0-1,4-5", "chars=0-5", "bytes=abc"):
        r = client.get(f"/api/media/{job_id}/video.mp4", headers={"Range": header})
        assert r.status_code == 200, header
        assert r.content == b"fake-video-bytes"


def test_missing_blob_404(auth_client):
    client = auth_client()
    job_id = create_job(client)["job_id"]
    assert client.get(f"/api/media/{job_id}/nope.jpg").status_code == 404


def test_foreign_job_404(auth_client, client):
    c = auth_client(email="owner2@test.com")
    job_id = create_job(c)["job_id"]
    c.post("/api/auth/logout")
    c.post("/api/auth/register", json={"email": "thief@test.com", "password": "secret123"})
    assert c.get(f"/api/media/{job_id}/video.mp4").status_code == 404
