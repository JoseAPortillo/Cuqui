"""FastAPI adapter — REST and WebSocket endpoints for the Cuqui timer API."""

from cuqui.adapters.api_fastapi.routes import create_app, router

__all__ = [
    "create_app",
    "router",
]
