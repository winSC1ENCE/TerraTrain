import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from terratrain.api.v1.router import router as v1_router
from terratrain.config import get_settings
from terratrain.db.engine import create_db_and_tables

logger = structlog.get_logger()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="TerraTrain",
        description="AI-powered terrain-aware endurance training coach",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router, prefix="/api/v1")

    @app.on_event("startup")
    async def startup() -> None:
        logger.info("terratrain.startup", env=settings.app_env)

    @app.on_event("shutdown")
    async def shutdown() -> None:
        logger.info("terratrain.shutdown")

    return app


app = create_app()
