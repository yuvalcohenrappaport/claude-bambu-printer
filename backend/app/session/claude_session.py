import asyncio

from fastapi import WebSocket
from loguru import logger

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
)
from claude_agent_sdk.types import StreamEvent

from app.config import settings


class ClaudeSession:
    """Wraps a ClaudeSDKClient subprocess lifecycle for one user session."""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.client: ClaudeSDKClient | None = None
        self._idle_timer: asyncio.Task | None = None
        self.session_id: str | None = None

    async def start(self):
        """Spawn Claude Code subprocess immediately."""
        options = ClaudeAgentOptions(
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": (
                    "You are controlling a 3D printer dashboard. "
                    "Help the user with 3D printing tasks including "
                    "model search, slicing, and print management."
                ),
            },
            permission_mode="acceptEdits",
            cwd=str(settings.project_root),
            allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep"],
            setting_sources=["user", "project"],
            include_partial_messages=True,
        )
        self.client = ClaudeSDKClient(options=options)
        try:
            await asyncio.wait_for(
                self.client.connect(),
                timeout=settings.claude_connect_timeout,
            )
        except TimeoutError:
            logger.error("Claude Code connect timed out after {}s", settings.claude_connect_timeout)
            self.client = None
            raise

        info = await self.client.get_server_info()
        if info:
            self.session_id = info.get("session_id")
        logger.info("Claude session started: {}", self.session_id)
        self._reset_idle_timer()

    async def send_message(self, text: str):
        """Send user message and stream response back via WebSocket."""
        if not self.client:
            logger.warning("send_message called with no active client")
            return

        self._reset_idle_timer()
        try:
            await self.client.query(text)
            async for message in self.client.receive_response():
                if isinstance(message, StreamEvent):
                    event = message.event
                    if event.get("type") == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            await self.websocket.send_json({
                                "type": "assistant_delta",
                                "text": delta.get("text", ""),
                            })
                elif isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            await self.websocket.send_json({
                                "type": "assistant_text",
                                "text": block.text,
                            })
                elif isinstance(message, ResultMessage):
                    await self.websocket.send_json({
                        "type": "turn_complete",
                        "session_id": message.session_id,
                        "cost_usd": message.total_cost_usd,
                    })
        except Exception as e:
            logger.error("Error during send_message: {}", e)
            await self._recover(str(e))

    async def _recover(self, error_msg: str):
        """Auto-restart subprocess on crash."""
        logger.warning("Recovering session after error: {}", error_msg)
        try:
            if self.client:
                await self.client.disconnect()
        except Exception:
            pass
        self.client = None

        try:
            await self.start()
            await self.websocket.send_json({
                "type": "session_recovered",
                "message": "Session recovered after an error.",
            })
        except Exception as e:
            logger.error("Recovery failed: {}", e)
            await self.websocket.send_json({
                "type": "error",
                "message": f"Session recovery failed: {e}",
            })

    def _reset_idle_timer(self):
        """Cancel existing idle timer and start a new one."""
        if self._idle_timer and not self._idle_timer.done():
            self._idle_timer.cancel()
        self._idle_timer = asyncio.create_task(self._idle_timeout())

    def pause_idle_timer(self):
        """Cancel idle timer during grace period."""
        if self._idle_timer and not self._idle_timer.done():
            self._idle_timer.cancel()
            self._idle_timer = None

    async def _idle_timeout(self):
        """Warn at idle_warning seconds, expire at idle_timeout seconds."""
        try:
            await asyncio.sleep(settings.idle_warning)
            await self.websocket.send_json({
                "type": "idle_warning",
                "message": "Session will expire in 3 minutes due to inactivity.",
            })
            remaining = settings.idle_timeout - settings.idle_warning
            await asyncio.sleep(remaining)
            await self.websocket.send_json({"type": "session_expired"})
            await self.stop()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug("Idle timeout error (likely disconnected): {}", e)

    async def stop(self):
        """Stop the Claude subprocess and cancel timers."""
        if self._idle_timer and not self._idle_timer.done():
            self._idle_timer.cancel()
            self._idle_timer = None
        if self.client:
            try:
                await self.client.disconnect()
            except Exception as e:
                logger.debug("Error disconnecting client: {}", e)
            self.client = None
        logger.info("Claude session stopped: {}", self.session_id)

    async def interrupt(self):
        """Interrupt the current Claude Code operation."""
        if self.client:
            try:
                await self.client.interrupt()
                logger.debug("Claude session interrupted")
            except Exception as e:
                logger.debug("Error interrupting: {}", e)
