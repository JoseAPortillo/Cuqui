import os

from cuqui.adapters.api_fastapi import create_app

# Serve the production frontend build when not in dev mode
serve_frontend = os.getenv("CUQUI_SERVE_FRONTEND", "0") == "1"

app = create_app(serve_frontend=serve_frontend)

if __name__ == "__main__":
    import uvicorn

    reload_enabled = os.getenv("CUQUI_RELOAD", "0") == "1"
    uvicorn.run(
        "cuqui.__main__:app",
        host="0.0.0.0",
        port=int(os.getenv("CUQUI_PORT", "8000")),
        reload=reload_enabled,
    )
