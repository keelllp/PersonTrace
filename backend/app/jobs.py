import logging
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Callable

from .db import SessionLocal
from .models import Job

logger = logging.getLogger(__name__)

Processor = Callable[[str, Callable[[], bool]], None]


class JobCancelled(Exception):
    pass


class JobQueue:
    def __init__(self, processor: Processor, session_factory=SessionLocal):
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._processor = processor
        self._session_factory = session_factory
        self._cancel_flags: set[str] = set()
        self._lock = threading.Lock()

    def submit(self, job_id: str) -> None:
        self._executor.submit(self._run, job_id)

    def request_cancel(self, job_id: str) -> None:
        with self._lock:
            self._cancel_flags.add(job_id)

    def _is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._cancel_flags

    def _run(self, job_id: str) -> None:
        db = self._session_factory()
        try:
            job = db.get(Job, job_id)
            if job is None or job.status == "cancelled":
                return
            job.status = "processing"
            db.commit()

            try:
                self._processor(job_id, lambda: self._is_cancelled(job_id))
            except JobCancelled:
                final_status, error = "cancelled", None
            except Exception as exc:
                logger.error("Job %s failed:\n%s", job_id, traceback.format_exc())
                final_status, error = "failed", str(exc)
            else:
                final_status, error = "done", None

            db.refresh(job)
            job.status = final_status
            job.error = error
            if final_status == "done":
                job.progress_pct = 100.0
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()
            with self._lock:
                self._cancel_flags.discard(job_id)
