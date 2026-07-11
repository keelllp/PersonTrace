import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from app.storage import Storage, job_key


def test_job_key_builds_scoped_path():
    assert job_key("u1", "j1", "video.mp4") == "users/u1/jobs/j1/video.mp4"
    assert (
        job_key("u1", "j1", "persons/p1", "photo_0.jpg")
        == "users/u1/jobs/j1/persons/p1/photo_0.jpg"
    )


@pytest.fixture()
def storage():
    with mock_aws():
        s = Storage(
            endpoint=None,  # moto intercepts default AWS endpoint
            access_key="test",
            secret_key="test",
            bucket="persontrace-test",
        )
        s.ensure_bucket()
        yield s


def test_put_get_roundtrip(storage):
    storage.put_bytes("users/u1/jobs/j1/a.txt", b"hello", content_type="text/plain")
    assert storage.get_bytes("users/u1/jobs/j1/a.txt") == b"hello"


def test_head_returns_size_and_raises_on_missing(storage):
    storage.put_bytes("k", b"12345")
    assert storage.head("k") == 5
    with pytest.raises(KeyError):
        storage.head("missing")


def test_stream_supports_byte_ranges(storage):
    storage.put_bytes("k", b"0123456789")
    assert b"".join(storage.stream("k", start=2, end=5)) == b"2345"
    assert b"".join(storage.stream("k")) == b"0123456789"


def test_delete_prefix_removes_all_objects_under_it(storage):
    storage.put_bytes("users/u1/jobs/j1/a", b"x")
    storage.put_bytes("users/u1/jobs/j1/sub/b", b"y")
    storage.put_bytes("users/u1/jobs/j2/c", b"z")
    storage.delete_prefix("users/u1/jobs/j1/")
    with pytest.raises(KeyError):
        storage.head("users/u1/jobs/j1/a")
    assert storage.head("users/u1/jobs/j2/c") == 1


def _client_error(code, op):
    return ClientError({"Error": {"Code": code, "Message": code}}, op)


def test_non_missing_client_errors_propagate(storage, monkeypatch):
    def boom(**kwargs):
        raise _client_error("SlowDown", "GetObject")

    monkeypatch.setattr(storage.client, "get_object", boom)
    with pytest.raises(ClientError):
        storage.get_bytes("k")
    with pytest.raises(ClientError):
        list(storage.stream("k"))

    monkeypatch.setattr(storage.client, "head_object", boom)
    with pytest.raises(ClientError):
        storage.head("k")
