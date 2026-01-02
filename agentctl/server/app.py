"""FastAPI application."""
from fastapi import FastAPI
from contextlib import asynccontextmanager

from agentctl.server.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup."""
    init_db()
    yield


app = FastAPI(
    title="AgentCtl Master",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}
