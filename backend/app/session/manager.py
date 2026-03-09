import asyncio

from fastapi import WebSocket
from loguru import logger

from app.config import settings
from app.session.claude_session import ClaudeSession


class SessionManager:
    """Enforces single session at a time. Manages lifecycle."""

    def __init__(self):
        self.active_session: ClaudeSession | None = None
        self._cleanup_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket) -> ClaudeSession:
        """Handle new WebSocket connection. Returns a ClaudeSession."""
        # Cancel any pending grace-period cleanup (user reconnected in time)
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            self._cleanup_task = None
            logger.info("Grace period cancelled -- client reconnected")

        if self.active_session:
            # Takeover: swap websocket, notify old connection
            old_ws = self.active_session.websocket
            self.active_session.websocket = websocket
            try:
                await old_ws.send_json({"type": "session_takeover"})
                await old_ws.close(code=4000, reason="Session taken over by new tab")
            except Exception:
                pass  # Old WS may already be dead (Pitfall 4)
            logger.info("Session takeover -- reattached existing session")
            self.active_session._reset_idle_timer()
            return self.active_session

        # No existing session -- create new
        session = ClaudeSession(websocket)
        await session.start()
        self.active_session = session
        return session

    async def disconnect(self, session: ClaudeSession):
        """Start grace period on disconnect."""
        session.pause_idle_timer()  # Pitfall 3: cancel idle timer during grace
        self._cleanup_task = asyncio.create_task(
            self._grace_period_cleanup(session)
        )
        logger.info(
            "Disconnect -- grace period started ({}s)",
            settings.grace_period,
        )

    async def _grace_period_cleanup(self, session: ClaudeSession):
        """Wait grace_period seconds, then kill subprocess if no reconnect."""
        try:
            await asyncio.sleep(settings.grace_period)
            await session.stop()
            if self.active_session is session:
                self.active_session = None
            logger.info("Grace period expired -- session cleaned up")
        except asyncio.CancelledError:
            pass

    async def shutdown(self):
        """Kill active session immediately (for server shutdown)."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
        if self.active_session:
            await self.active_session.stop()
            self.active_session = None
        logger.info("SessionManager shutdown complete")

    async def cleanup_orphans(self):
        """Best-effort check for orphaned claude processes on startup."""
        try:
            process = await asyncio.create_subprocess_exec(
                "pgrep", "-f", "claude",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            if stdout.strip():
                pids = stdout.decode().strip().split("\n")
                logger.warning(
                    "Found {} potential orphaned claude process(es): {}",
                    len(pids),
                    pids,
                )
        except Exception as e:
            logger.debug("Orphan check skipped: {}", e)
