import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.session.manager import SessionManager
from app.ws.handler import websocket_endpoint

# Configure logging
logger.remove()
logger.add(sys.stdout, level="INFO")

# Resolve log path relative to project root
log_path = settings.project_root / settings.log_file
log_path.parent.mkdir(parents=True, exist_ok=True)

logger.add(
    str(log_path),
    rotation="50 MB",
    retention="7 days",
    level="DEBUG",
)

session_manager = SessionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Backend starting up")
    await session_manager.cleanup_orphans()
    yield
    logger.info("Backend shutting down")
    await session_manager.shutdown()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "active_session": session_manager.active_session is not None,
    }


@app.websocket("/ws")
async def ws_route(websocket: WebSocket):
    await websocket_endpoint(websocket, session_manager)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
