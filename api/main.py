"""
Metalcore Index API -- FastAPI application.
Serves pre-computed artist scores, network graph data, and dashboard endpoints.
"""
import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# Ensure project root is on path (for pipeline imports in seed endpoint)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from database import Base, engine  # noqa: E402
from routers import health, artists, scores, network, seed, events  # noqa: E402

logger = logging.getLogger(__name__)


def _run_migrations(eng):
    """Add columns that create_all won't add to existing tables."""
    migrations = [
        ("artists", "booking_agent", "VARCHAR(200)"),
        ("artists", "bandsintown_id", "VARCHAR(200)"),
    ]
    with eng.connect() as conn:
        for table, col, col_type in migrations:
            try:
                conn.execute(text(
                    f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"
                ))
                conn.commit()
                logger.info("Added column %s.%s", table, col)
            except Exception:
                conn.rollback()  # column already exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_migrations(engine)
    yield


app = FastAPI(
    title="Metalcore Index API",
    version="0.1.0",
    description="Artist momentum scoring and network visualization for heavy music.",
    lifespan=lifespan,
)

# CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(artists.router)
app.include_router(scores.router)
app.include_router(network.router)
app.include_router(seed.router)
app.include_router(events.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
