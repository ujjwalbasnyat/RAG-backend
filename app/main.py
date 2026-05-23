from fastapi import FastAPI
from app.api.v1 import api_router
from app.core.logging import configure_logging

def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="RAG Backend", version="1.0.0")
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app

app = create_app()