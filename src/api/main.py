"""Main FastAPI application module."""

from fastapi import FastAPI

app = FastAPI(title="Tributum", version="0.1.0")


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint returning a hello world message.

    Returns:
        dict: A dictionary containing a welcome message.
    """
    return {"message": "Hello from Tributum!"}
