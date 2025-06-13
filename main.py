"""Main entry point for running the Tributum FastAPI application."""

import uvicorn

from src.api.main import app


def main() -> None:
    """Main entry point for the Tributum application."""
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
