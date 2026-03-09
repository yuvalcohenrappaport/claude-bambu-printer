import asyncio

from fastapi import WebSocket
from loguru import logger

from app.config import settings


async def heartbeat(websocket: WebSocket):
    """Send ping every heartbeat_interval seconds. Detects dead connections."""
    while True:
        await asyncio.sleep(settings.heartbeat_interval)
        try:
            await websocket.send_json({"type": "ping"})
        except Exception:
            logger.debug("Heartbeat failed -- connection dead")
            break
