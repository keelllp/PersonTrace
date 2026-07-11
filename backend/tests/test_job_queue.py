from app.jobs import JobCancelled, JobQueue
from app.models import Job, User


def test_recover_interrupted_jobs_fails_stuck_and_spares_done(session_factory):
    from app.jobs import recover_interrupted_jobs

    ids = {}
    with session_factory() as db:
        user = User(email="r@test.com", password_hash="x")
        db.add(user)
        for status in ("processing", "queued", "done"):
            job = Job(user=user, video_key="k", video_filename="v.mp4", status=status)
            db.add(job)
            db.flush()
            ids[status] = job.id
        db.commit()

    assert recover_interrupted_jobs(session_factory) == 2

    with session_factory() as db:
        assert db.get(Job, ids["processing"]).status == "failed"
        assert db.get(Job, ids["queued"]).status == "failed"
        assert "restart" in db.get(Job, ids["processing"]).error
        assert db.get(Job, ids["done"]).status == "done"


def make_job(session_factory):
    with session_factory() as db:
        user = User(email="q@test.com", password_hash="x")
        job = Job(user=user, video_key="k", video_filename="v.mp4")
        db.add(user)
        db.commit()
        return job.id


def get_job(session_factory, job_id):
    with session_factory() as db:
        return db.get(Job, job_id)


def test_successful_run_marks_done(session_factory):
    job_id = make_job(session_factory)
    calls = []

    def processor(jid, cancel_check):
        calls.append(jid)

    queue = JobQueue(processor, session_factory=session_factory)
    queue._run(job_id)

    job = get_job(session_factory, job_id)
    assert calls == [job_id]
    assert job.status == "done"
    assert job.progress_pct == 100.0
    assert job.finished_at is not None


def test_processor_exception_marks_failed_with_error(session_factory):
    job_id = make_job(session_factory)

    def processor(jid, cancel_check):
        raise RuntimeError("model exploded")

    queue = JobQueue(processor, session_factory=session_factory)
    queue._run(job_id)

    job = get_job(session_factory, job_id)
    assert job.status == "failed"
    assert "model exploded" in job.error


def test_cancel_flag_reaches_processor_and_marks_cancelled(session_factory):
    job_id = make_job(session_factory)

    def processor(jid, cancel_check):
        assert cancel_check() is True
        raise JobCancelled()

    queue = JobQueue(processor, session_factory=session_factory)
    queue.request_cancel(job_id)
    queue._run(job_id)

    job = get_job(session_factory, job_id)
    assert job.status == "cancelled"


def test_run_does_not_process_cancelled_job(session_factory):
    job_id = make_job(session_factory)
    with session_factory() as db:
        db.get(Job, job_id).status = "cancelled"
        db.commit()
    calls = []
    queue = JobQueue(lambda j, c: calls.append(j), session_factory=session_factory)
    queue._run(job_id)
    assert calls == []
    with session_factory() as db:
        assert db.get(Job, job_id).status == "cancelled"
