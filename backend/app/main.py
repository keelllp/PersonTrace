from fastapi import FastAPI


def create_app(storage=None, processor=None) -> FastAPI:
    app = FastAPI(title="PersonTrace API")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
