from fastapi import FastAPI

from . import auth


def create_app(storage=None, processor=None) -> FastAPI:
    app = FastAPI(title="PersonTrace API")
    app.include_router(auth.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
