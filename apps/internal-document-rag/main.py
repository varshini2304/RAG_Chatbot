"""FastAPI application server entry point for the Internal Document RAG Chatbot."""

from __future__ import annotations

import uvicorn


def main() -> None:
    """Run the FastAPI application via Uvicorn."""
    uvicorn.run("app.api.api_app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
