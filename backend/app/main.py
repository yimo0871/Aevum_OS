"""Aevum Backend - FastAPI Application Entry Point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    # Startup
    settings.logger.info("Starting Aevum Backend...")
    yield
    # Shutdown
    settings.logger.info("Shutting down Aevum Backend...")


app = FastAPI(
    title="Aevum / 薪火 OS",
    description="Experience never fades. It compounds. 经验不熄，代代相传。",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": "Aevum / 薪火 OS",
        "version": "0.1.0",
        "tagline": "Experience never fades. It compounds.",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


# API v1 routes
from app.api.v1 import api_router

app.include_router(api_router, prefix="/api/v1")
