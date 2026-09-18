"""
backend/main.py

FastAPI application entry point.

Run with:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

Interactive docs:
    http://localhost:8000/docs      (Swagger UI)
    http://localhost:8000/redoc     (ReDoc)
"""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.routers import units, reference, columns
# ── Hydrocarbon Recovery Router Imports ───────────────────────────────────────
from backend.routers.hc_recovery import feed, condensation, adsorption, membrane, compare


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Pre-warm the lru_cache loaders on startup so the first API
    request doesn't pay the file-read cost.
    """
    from simulation.data.loader import (
        _load_components,
        _load_u_values,
        _load_steam_tables,
    )
    _load_components()
    _load_u_values()
    _load_steam_tables()
    print("✓  Reference data loaded and cached.")
    yield
    print("✓  Shutdown complete.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="chemsyslab Platform API",
    version="1.0.0",
    description="Process Engineering, Simulation Framework, and Unit Operations Analytics Platform Engine.",
    lifespan=lifespan,
)


# ── CORS Middleware ───────────────────────────────────────────────────────────

cors_origins = os.getenv(
    "CORS_ALLOW_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,https://chem-sys-lab-chirok-0407.vercel.app",
)
allow_origins = [origin.strip().rstrip("/") for origin in cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Process Time Header Middleware ────────────────────────────────────────────

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to every response (ms)."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time"] = f"{elapsed_ms:.2f}ms"
    return response


# ── Global exception handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all for any unhandled exception.
    Returns a clean JSON error instead of a 500 HTML page.
    """
    return JSONResponse(
        status_code=500,
        content={
            "error_type": type(exc).__name__,
            "message": str(exc),
            "path": str(request.url),
        },
    )


# ── Core Routers ──────────────────────────────────────────────────────────────

app.include_router(units.router)
app.include_router(reference.router)
app.include_router(columns.router)

# ── HC Recovery Router Registrations ──────────────────────────────────────────

app.include_router(feed.router, prefix="/api", tags=["HC Recovery"])
app.include_router(condensation.router, prefix="/api", tags=["HC Recovery"])
app.include_router(adsorption.router, prefix="/api", tags=["HC Recovery"])
app.include_router(membrane.router, prefix="/api", tags=["HC Recovery"])
app.include_router(compare.router, prefix="/api", tags=["HC Recovery"])


# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"], summary="API health check")
async def health() -> dict:
    """Returns API status and version. Used by frontend to verify connectivity."""
    return {
        "status": "ok",
        "version": app.version,
        "title": app.title,
    }