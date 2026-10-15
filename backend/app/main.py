"""Orbit Coordinator Backend — Application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.engine import init_db
from app.api import devices, pairing, layout, health, ws_controller, ws_agent
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    await init_db()
    yield
    # Shutdown: connection manager cleanup happens via websocket close handlers


def create_app() -> FastAPI:
    app = FastAPI(
        title="Orbit Coordinator",
        version="1.0.0",
        description="Backend coordinator for the Orbit multi-laptop remote-control system.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # REST routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(devices.router, prefix="/api/v1/devices", tags=["devices"])
    app.include_router(pairing.router, prefix="/api/v1/pairing", tags=["pairing"])
    app.include_router(layout.router, prefix="/api/v1/layout", tags=["layout"])

    # WebSocket endpoints
    app.include_router(ws_controller.router, prefix="/ws", tags=["websocket"])
    app.include_router(ws_agent.router, prefix="/ws", tags=["websocket"])

    return app


app = create_app()
