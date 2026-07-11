import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import auth, routes_jobs, routes_media
from .jobs import JobQueue, recover_interrupted_jobs


def _default_processor(job_id, cancel_check):
    from .pipeline.runner import run_pipeline

    run_pipeline(job_id, cancel_check)


def _default_photo_validator(data: bytes) -> bool:
    from .pipeline.ml import get_face_engine

    return get_face_engine().validate_photo_bytes(data)


def create_app(storage=None, processor=None, photo_validator=None) -> FastAPI:
    built_from_settings = storage is None
    if built_from_settings:
        from .storage import Storage

        storage = Storage.from_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if built_from_settings:
            storage.ensure_bucket()
            recovered = recover_interrupted_jobs()
            if recovered:
                logging.getLogger(__name__).warning(
                    "Marked %d interrupted job(s) as failed", recovered
                )

            import threading

            def _warm_face_engine():
                try:
                    from .pipeline.ml import get_face_engine

                    get_face_engine()
                except Exception:
                    logging.getLogger(__name__).exception("Face engine warm-up failed")

            threading.Thread(target=_warm_face_engine, daemon=True).start()
        yield
        app.state.job_queue.shutdown()

    app = FastAPI(title="PersonTrace API", lifespan=lifespan)
    app.state.storage = storage
    app.state.job_queue = JobQueue(processor or _default_processor)
    app.state.photo_validator = photo_validator or _default_photo_validator

    app.include_router(auth.router)
    app.include_router(routes_jobs.router)
    app.include_router(routes_media.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
