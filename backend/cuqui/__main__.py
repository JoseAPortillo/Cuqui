from cuqui.adapters.api_fastapi import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("cuqui.__main__:app", host="0.0.0.0", port=8000, reload=True)
