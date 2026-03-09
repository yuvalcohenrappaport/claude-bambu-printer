import asyncio

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from app.models.messages import ConnectedMessage, ErrorMessage
from app.session.manager import SessionManager
from app.ws.heartbeat import heartbeat


async def websocket_endpoint(websocket: WebSocket, session_manager: SessionManager):
    """WebSocket endpoint with message routing and heartbeat."""
    await websocket.accept()

    session = await session_manager.connect(websocket)

    # Send connected message
    connected = ConnectedMessage(session_id=session.session_id)
    await websocket.send_json(connected.model_dump())

    # Start heartbeat as concurrent task
    heartbeat_task = asyncio.create_task(heartbeat(websocket))

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "chat":
                text = data.get("text", "")
                if text:
                    await session.send_message(text)
            elif msg_type == "interrupt":
                await session.interrupt()
            elif msg_type == "pong":
                pass  # Heartbeat response -- connection alive
            elif msg_type == "idle_response":
                session._reset_idle_timer()
            else:
                error = ErrorMessage(message=f"Unknown message type: {msg_type}")
                await websocket.send_json(error.model_dump())

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        heartbeat_task.cancel()
        await session_manager.disconnect(session)
    except Exception as e:
        logger.error("WebSocket error: {}", e)
        heartbeat_task.cancel()
        try:
            await websocket.close()
        except Exception:
            pass
        await session_manager.disconnect(session)
