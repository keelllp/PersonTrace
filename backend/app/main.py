from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import auth, routes_jobs
from .jobs import JobQueue


def _pipeline_unavailable(job_id, cancel_check):
    raise RuntimeError("Processing pipeline is not installed")


def create_app(storage=None, processor=None) -> FastAPI:
    built_from_settings = storage is None
    if built_from_settings:
        from .storage import Storage

        storage = Storage.from_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if built_from_settings:
            storage.ensure_bucket()
        yield

    app = FastAPI(title="PersonTrace API", lifespan=lifespan)
    app.state.storage = storage
    app.state.job_queue = JobQueue(processor or _pipeline_unavailable)
    app.state.photo_validator = lambda data: True

    app.include_router(auth.router)
    app.include_router(routes_jobs.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
