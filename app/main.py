"""FastAPI application entry point.

Run with:  python -m app.main
       or: uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI

from app.config import settings

app = FastAPI(
    title=settings.app_name,
    description="REST API exposing public company knowledge: products, FAQs, company info and documents.",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Simple liveness check: returns 200 OK when the server is running."""
    return {"status": "ok", "service": settings.app_name}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=True)
