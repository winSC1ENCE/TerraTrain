import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from terratrain.api.v1.router import router as v1_router
from terratrain.config import get_settings
from terratrain.db.migrate import run_migrations
from terratrain.rate_limit import limiter
from terratrain.services.admin_seed import seed_initial_admin

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

    app.state.limiter = limiter
    # slowapi's handler predates Starlette's typed exception-handler signature.
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # Allow both localhost and 127.0.0.1 on any port for local development.
    # The regex covers browsers that reach the app via either host; the
    # explicit list stays as an allow-list for anything non-local (e.g. the
    # production domain).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router, prefix="/api/v1")

    @app.on_event("startup")
    async def startup() -> None:
        logger.info("terratrain.startup", env=settings.app_env)
        await run_migrations()
        await seed_initial_admin()

    @app.on_event("shutdown")
    async def shutdown() -> None:
        logger.info("terratrain.shutdown")

    return app


app = create_app()
