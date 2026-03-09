# Phase 5: Backend Foundation - Research

**Researched:** 2026-03-09
**Domain:** FastAPI + WebSocket + Claude Code subprocess lifecycle management
**Confidence:** HIGH

## Summary

Phase 5 builds the backend skeleton: a FastAPI server with WebSocket support, Claude Code subprocess management via `claude-agent-sdk`, and session lifecycle (spawn on connect, grace period on disconnect, idle timeout, single-session enforcement). No chat UI, no 3D viewer, no printer features -- just the foundation.

The claude-agent-sdk `ClaudeSDKClient` class is the core integration point. It manages a persistent Claude Code subprocess per session, supports multi-turn conversations, streaming, interrupts, and in-process MCP servers. The API is well-documented and stable at v0.1.48. FastAPI's native WebSocket support plus application-level heartbeat gives us reliable connection detection.

**Primary recommendation:** Use `ClaudeSDKClient` as async context manager per WebSocket session, with a `SessionManager` singleton enforcing single-session-at-a-time and handling grace periods. Poetry for dependency management, Vite proxy for dev experience.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Claude Code subprocess spawns immediately on page load (not on first message)
- 30-second grace period on disconnect before killing subprocess (handles accidental close/refresh)
- Idle timeout with warning -- warn user after idle period, kill subprocess if no response
- One session at a time -- opening a new tab takes over the existing session
- Monorepo: frontend and backend in the same repo alongside existing skill files
- Top-level split: `/frontend` and `/backend` as top-level folders
- Frontend: npm (not bun)
- Backend: Poetry for dependency management
- Separate terminals for frontend and backend (not a single command)
- Backend port: 8000 (FastAPI default)
- Backend auto-reload: uvicorn --reload in development
- Frontend dev server on default Vite port (5173)
- Claude Code crash: auto-restart subprocess silently, show "Session recovered" message
- WebSocket drop: auto-reconnect with exponential backoff, show "Reconnecting..." indicator
- Backend down: full-page error screen ("Cannot connect to server" + retry button)
- Logging: stdout + file (for post-hoc debugging)

### Claude's Discretion
- Dev proxy configuration (Vite proxy vs direct URLs)
- Exact idle timeout duration
- Log file location and rotation
- WebSocket heartbeat interval
- Grace period implementation details

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFR-01 | FastAPI backend manages Claude Code subprocess via claude-agent-sdk with WebSocket communication | ClaudeSDKClient API verified (connect/query/receive_response/interrupt/disconnect). FastAPI WebSocket endpoint pattern documented. Session lifecycle management pattern with grace period and idle timeout designed. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135.x | HTTP + WebSocket server | Native WebSocket via ASGI, async-first, Pydantic integration |
| uvicorn | 0.34.x | ASGI server | Standard FastAPI production server, supports `--reload` for dev |
| claude-agent-sdk | 0.1.48 | Claude Code subprocess management | Official SDK. ClaudeSDKClient for persistent sessions with streaming, interrupts, MCP |
| pydantic | 2.x | WebSocket message schemas | Already a FastAPI dependency. Type-safe message definitions |
| Poetry | latest | Python dependency management | User decision. Manages virtualenv and lockfile for growing backend |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | latest | Environment variable loading | Load .env for development config (ports, log paths) |
| loguru | latest | Structured logging | Stdout + file logging with rotation. Simpler than stdlib logging |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| loguru | stdlib logging | stdlib is lighter but requires more boilerplate for file rotation and formatting |
| python-dotenv | pydantic-settings | pydantic-settings is more powerful but heavier for simple env loading |

### Discretion Recommendations

**Dev proxy:** Use Vite proxy. Configure `vite.config.ts` to proxy `/ws` and `/api` to `localhost:8000`. This avoids CORS issues in development and matches production (same-origin). The frontend code uses relative paths (`/ws`, `/api/health`) that work in both dev and production without environment-specific URLs.

**Idle timeout:** 15 minutes. Long enough that a user stepping away briefly does not lose their session. Short enough that forgotten sessions do not waste resources indefinitely. Send a warning at 12 minutes ("Session will expire in 3 minutes due to inactivity").

**Log file location:** `backend/logs/` directory, gitignored. Use `app.log` with daily rotation, 7-day retention, max 50MB per file.

**WebSocket heartbeat:** 20-second ping interval. Server sends ping, client must respond with pong within 10 seconds. This is below the typical 30-120 second proxy/firewall timeout window.

**Grace period implementation:** Use `asyncio.create_task` with a 30-second sleep. If the same session reconnects (identified by a session token cookie or query param), cancel the cleanup task and reattach the WebSocket to the existing ClaudeSDKClient.

**Installation:**
```bash
# Backend setup
cd backend
poetry init
poetry add fastapi uvicorn claude-agent-sdk pydantic python-dotenv loguru
poetry add --group dev pytest ruff

# Frontend setup (minimal for phase 5 -- just enough to test WebSocket)
cd frontend
npm create vite@latest . -- --template react-swc-ts
npm install
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
  pyproject.toml
  poetry.lock
  logs/                    # gitignored
  app/
    __init__.py
    main.py                # FastAPI app, startup/shutdown, CORS
    config.py              # Settings from env vars
    session/
      __init__.py
      manager.py           # SessionManager singleton
      claude_session.py    # ClaudeSession wrapping ClaudeSDKClient
    ws/
      __init__.py
      handler.py           # WebSocket endpoint + message routing
      heartbeat.py         # Ping/pong heartbeat logic
    models/
      __init__.py
      messages.py          # Pydantic WebSocket message schemas
frontend/
  package.json
  vite.config.ts           # Proxy config for /ws and /api
  src/
    App.tsx                # Minimal -- just connection status display
    hooks/
      useWebSocket.ts      # WebSocket hook with reconnect + heartbeat
```

### Pattern 1: SessionManager Singleton (Single-Session Enforcement)
**What:** A global `SessionManager` that tracks the one active session. When a new tab connects, it sends a "session_takeover" message to the old WebSocket and transfers the ClaudeSDKClient to the new connection.
**When:** Always -- this is the core of phase 5.
**Example:**
```python
# Source: Derived from claude-agent-sdk official docs + user requirements
import asyncio
from fastapi import WebSocket

class SessionManager:
    """Enforces one session at a time. Manages lifecycle."""

    def __init__(self):
        self.active_session: ClaudeSession | None = None
        self._cleanup_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket) -> ClaudeSession:
        """Handle new WebSocket connection."""
        # Cancel any pending cleanup from a previous disconnect
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            self._cleanup_task = None

        if self.active_session:
            # Take over existing session (new tab replaces old)
            old_ws = self.active_session.websocket
            self.active_session.websocket = websocket
            try:
                await old_ws.send_json({"type": "session_takeover"})
                await old_ws.close(code=4000, reason="Session taken over by new tab")
            except Exception:
                pass  # Old WS may already be dead
            return self.active_session

        # No existing session -- create new
        session = ClaudeSession(websocket)
        await session.start()  # Spawns Claude Code subprocess
        self.active_session = session
        return session

    async def disconnect(self, session: ClaudeSession):
        """Start grace period on disconnect."""
        self._cleanup_task = asyncio.create_task(
            self._grace_period_cleanup(session)
        )

    async def _grace_period_cleanup(self, session: ClaudeSession):
        """Wait 30s, then kill subprocess if no reconnect."""
        await asyncio.sleep(30)
        await session.stop()
        self.active_session = None
```

### Pattern 2: ClaudeSession Wrapping ClaudeSDKClient
**What:** A wrapper class that owns a `ClaudeSDKClient`, handles subprocess spawn on page load, crash recovery, and idle timeout.
**When:** One instance per active session.
**Example:**
```python
# Source: claude-agent-sdk official Python reference (platform.claude.com)
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock, ResultMessage, StreamEvent
import asyncio

class ClaudeSession:
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
                "append": "You are controlling a 3D printer through a web dashboard."
            },
            permission_mode="acceptEdits",
            cwd="/path/to/project",
            setting_sources=["user", "project"],  # Load SKILL.md
            allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep"],
        )
        self.client = ClaudeSDKClient(options=options)
        await self.client.connect()
        # Get session_id from server info
        info = await self.client.get_server_info()
        if info:
            self.session_id = info.get("session_id")
        self._reset_idle_timer()

    async def send_message(self, text: str):
        """Send user message and stream response back."""
        self._reset_idle_timer()
        try:
            await self.client.query(text)
            async for message in self.client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            await self.websocket.send_json({
                                "type": "assistant_text",
                                "text": block.text,
                            })
                elif isinstance(message, StreamEvent):
                    # Forward streaming deltas for real-time display
                    event = message.event
                    if event.get("type") == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            await self.websocket.send_json({
                                "type": "assistant_delta",
                                "text": delta.get("text", ""),
                            })
                elif isinstance(message, ResultMessage):
                    await self.websocket.send_json({
                        "type": "turn_complete",
                        "session_id": message.session_id,
                        "cost_usd": message.total_cost_usd,
                    })
        except Exception as e:
            # Claude Code crash -- auto-restart
            await self._recover(str(e))

    async def _recover(self, error_msg: str):
        """Auto-restart subprocess on crash."""
        try:
            if self.client:
                await self.client.disconnect()
        except Exception:
            pass
        await self.start()
        await self.websocket.send_json({
            "type": "session_recovered",
            "message": "Session recovered after an error.",
        })

    def _reset_idle_timer(self):
        if self._idle_timer and not self._idle_timer.done():
            self._idle_timer.cancel()
        self._idle_timer = asyncio.create_task(self._idle_timeout())

    async def _idle_timeout(self):
        await asyncio.sleep(12 * 60)  # 12 min warning
        await self.websocket.send_json({
            "type": "idle_warning",
            "message": "Session will expire in 3 minutes due to inactivity.",
        })
        await asyncio.sleep(3 * 60)  # 3 more min
        await self.websocket.send_json({"type": "session_expired"})
        await self.stop()

    async def stop(self):
        if self._idle_timer and not self._idle_timer.done():
            self._idle_timer.cancel()
        if self.client:
            await self.client.disconnect()
            self.client = None

    async def interrupt(self):
        if self.client:
            await self.client.interrupt()
```

### Pattern 3: WebSocket Endpoint with Heartbeat
**What:** FastAPI WebSocket endpoint that accepts connections, routes messages, and runs a concurrent heartbeat task.
**When:** The single `/ws` endpoint for all browser communication.
**Example:**
```python
# Source: FastAPI WebSocket docs + heartbeat best practices
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import json

app = FastAPI()
session_manager = SessionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session = await session_manager.connect(websocket)

    # Send initial connected state
    await websocket.send_json({
        "type": "connected",
        "session_id": session.session_id,
    })

    # Start heartbeat as concurrent task
    heartbeat_task = asyncio.create_task(heartbeat(websocket))

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "chat":
                await session.send_message(data["text"])
            elif msg_type == "interrupt":
                await session.interrupt()
            elif msg_type == "pong":
                pass  # Heartbeat response -- connection alive
            elif msg_type == "idle_response":
                session._reset_idle_timer()  # User responded to warning
    except WebSocketDisconnect:
        heartbeat_task.cancel()
        await session_manager.disconnect(session)

async def heartbeat(websocket: WebSocket):
    """Send ping every 20s. If send fails, connection is dead."""
    while True:
        await asyncio.sleep(20)
        try:
            await websocket.send_json({"type": "ping"})
        except Exception:
            break  # Connection dead
```

### Pattern 4: Vite Proxy Configuration
**What:** Dev proxy so frontend uses relative URLs that work identically in dev and production.
**When:** Development only. In production, a reverse proxy or same-origin serving handles this.
**Example:**
```typescript
// vite.config.ts
// Source: Vite official docs (vite.dev/config/server-options)
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

### Anti-Patterns to Avoid
- **Spawning a new Claude Code per message:** Use `ClaudeSDKClient` for session persistence. `query()` creates a new session each time -- wrong for chat.
- **Global mutable state for session tracking:** Use a `SessionManager` class, not module-level dicts. Makes testing and lifecycle management explicit.
- **Synchronous subprocess management:** Never use `subprocess.Popen` for Claude Code. The SDK handles stdin/stdout pipe management, JSON reassembly, and deadlock prevention.
- **Skipping `include_partial_messages=True`:** Without this, you only get complete AssistantMessages. Streaming requires this flag to receive `StreamEvent` objects with text deltas.
- **Breaking out of `receive_response()` with `break`:** Official docs warn this causes asyncio cleanup issues. Use flags to skip processing instead.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Claude Code subprocess lifecycle | Raw subprocess.Popen with pipe management | claude-agent-sdk ClaudeSDKClient | Handles stdin/stdout deadlocks, JSON reassembly, process cleanup, interrupt protocol |
| WebSocket message serialization | Manual JSON string building | Pydantic models with `.model_dump()` | Type safety, validation, consistent message shapes |
| WebSocket reconnect (frontend) | Custom retry logic | Standard exponential backoff pattern with jitter | Well-understood pattern, avoids thundering herd |
| Python dependency management | requirements.txt | Poetry with pyproject.toml | Lockfile ensures reproducible installs, user decision |
| Dev proxy | Environment-specific URL constants | Vite server.proxy | Same code paths dev and prod, no conditional logic |

## Common Pitfalls

### Pitfall 1: Zombie Claude Code Subprocesses
**What goes wrong:** Claude Code subprocess survives after session ends (FastAPI crash, unclean shutdown, missed disconnect).
**Why it happens:** SIGKILL to parent does not propagate to children. ClaudeSDKClient.disconnect() may not be called on all exit paths.
**How to avoid:** Always use `async with ClaudeSDKClient()` or explicit try/finally with disconnect(). Add a startup reaper that kills orphaned `claude` processes. Track PIDs in the SessionManager.
**Warning signs:** `pgrep -f claude` shows more processes than active sessions.

### Pitfall 2: Silent WebSocket Drops
**What goes wrong:** Browser disconnects (laptop sleep, network change) but backend does not detect it for minutes. Claude Code keeps running.
**Why it happens:** TCP keepalive defaults are 2+ hours. FastAPI only raises WebSocketDisconnect when you attempt send/receive.
**How to avoid:** Application-level ping/pong every 20 seconds. Run WebSocket read and subprocess read as concurrent asyncio tasks so a disconnect on either side is detected promptly.
**Warning signs:** Process count grows over time. Sessions never clean up.

### Pitfall 3: Idle Timer Race with Grace Period
**What goes wrong:** User disconnects (starts grace period), then idle timer fires during the grace period and kills the session before the 30-second reconnect window expires.
**Why it happens:** The idle timer and grace period timer are independent asyncio tasks.
**How to avoid:** Cancel the idle timer when entering the grace period. Only restart the idle timer after a successful reconnect.

### Pitfall 4: Session Takeover Message Delivery
**What goes wrong:** New tab connects, old tab should receive "session_takeover" but the old WebSocket is already dead. The send raises an exception that crashes the connect handler.
**Why it happens:** The old tab may have closed without a clean WebSocket disconnect.
**How to avoid:** Wrap the takeover notification in try/except. Log but do not raise. The old connection is best-effort notification only.

### Pitfall 5: ClaudeSDKClient.connect() Hangs
**What goes wrong:** Subprocess fails to start (Claude Code not installed, permission error). `connect()` blocks indefinitely waiting for the CLI process.
**Why it happens:** The SDK spawns `claude` CLI as a child process. If the binary is missing or crashes on startup, the transport may not report an error cleanly.
**How to avoid:** Add a timeout to the connect call: `asyncio.wait_for(client.connect(), timeout=30)`. Catch `TimeoutError` and report to the frontend. Add a health check on startup that verifies `claude --version` runs successfully.

## Code Examples

### Minimal FastAPI + WebSocket Server
```python
# backend/app/main.py
# Source: FastAPI docs + claude-agent-sdk official reference
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import sys

from app.config import settings
from app.session.manager import SessionManager

# Configure logging
logger.remove()
logger.add(sys.stdout, level="INFO")
logger.add(
    settings.log_file,
    rotation="50 MB",
    retention="7 days",
    level="DEBUG",
)

session_manager = SessionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Backend starting up")
    # Cleanup orphaned claude processes on startup
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
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session = await session_manager.connect(websocket)
    # ... message loop as shown in Pattern 3
```

### Pydantic WebSocket Message Schemas
```python
# backend/app/models/messages.py
from pydantic import BaseModel
from typing import Literal

# Client -> Server
class ChatMessage(BaseModel):
    type: Literal["chat"]
    text: str

class InterruptMessage(BaseModel):
    type: Literal["interrupt"]

class PongMessage(BaseModel):
    type: Literal["pong"]

class IdleResponseMessage(BaseModel):
    type: Literal["idle_response"]

# Server -> Client
class ConnectedMessage(BaseModel):
    type: Literal["connected"] = "connected"
    session_id: str | None = None

class AssistantDeltaMessage(BaseModel):
    type: Literal["assistant_delta"] = "assistant_delta"
    text: str

class AssistantTextMessage(BaseModel):
    type: Literal["assistant_text"] = "assistant_text"
    text: str

class TurnCompleteMessage(BaseModel):
    type: Literal["turn_complete"] = "turn_complete"
    session_id: str
    cost_usd: float | None = None

class SessionRecoveredMessage(BaseModel):
    type: Literal["session_recovered"] = "session_recovered"
    message: str

class IdleWarningMessage(BaseModel):
    type: Literal["idle_warning"] = "idle_warning"
    message: str

class SessionExpiredMessage(BaseModel):
    type: Literal["session_expired"] = "session_expired"

class SessionTakeoverMessage(BaseModel):
    type: Literal["session_takeover"] = "session_takeover"

class PingMessage(BaseModel):
    type: Literal["ping"] = "ping"

class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    message: str
```

### Frontend WebSocket Hook (Minimal)
```typescript
// frontend/src/hooks/useWebSocket.ts
import { useEffect, useRef, useState, useCallback } from 'react'

type ConnectionStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected' | 'error'

interface UseWebSocketReturn {
  status: ConnectionStatus
  sessionId: string | null
  sendMessage: (text: string) => void
  lastMessage: any | null
}

export function useWebSocket(): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null)
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [lastMessage, setLastMessage] = useState<any>(null)
  const retriesRef = useRef(0)
  const maxRetries = 10

  const connect = useCallback(() => {
    const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws`)
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('connected')
      retriesRef.current = 0
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'connected') {
        setSessionId(data.session_id)
      } else if (data.type === 'ping') {
        ws.send(JSON.stringify({ type: 'pong' }))
      } else if (data.type === 'session_takeover') {
        setStatus('disconnected')
        ws.close()
        return
      }
      setLastMessage(data)
    }

    ws.onclose = (event) => {
      if (event.code === 4000) return // Takeover, don't reconnect
      if (retriesRef.current < maxRetries) {
        setStatus('reconnecting')
        const delay = Math.min(1000 * 2 ** retriesRef.current, 30000)
        const jitter = Math.random() * 1000
        setTimeout(() => {
          retriesRef.current++
          connect()
        }, delay + jitter)
      } else {
        setStatus('error')
      }
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'chat', text }))
    }
  }, [])

  return { status, sessionId, sendMessage, lastMessage }
}
```

### Config Pattern
```python
# backend/app/config.py
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    project_root: Path = Path(__file__).parent.parent.parent  # repo root
    log_file: str = "backend/logs/app.log"
    heartbeat_interval: int = 20  # seconds
    heartbeat_timeout: int = 10   # seconds
    grace_period: int = 30        # seconds
    idle_warning: int = 720       # 12 minutes in seconds
    idle_timeout: int = 900       # 15 minutes in seconds
    claude_connect_timeout: int = 30  # seconds

    class Config:
        env_prefix = "BAMBU_"
        env_file = ".env"

settings = Settings()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| claude-code-sdk (PyPI) | claude-agent-sdk (PyPI) | 2026 | claude-code-sdk is deprecated. Use claude-agent-sdk for ClaudeSDKClient |
| query() per message | ClaudeSDKClient session | claude-agent-sdk 0.1.x | query() creates new subprocess per call. ClaudeSDKClient maintains one. |
| Manual subprocess pipes | SDK Transport layer | claude-agent-sdk 0.1.x | SDK handles JSON reassembly, deadlock prevention, buffering |
| requirements.txt | Poetry pyproject.toml | User decision | Lockfile, dependency groups, virtual env management |

**Deprecated/outdated:**
- `claude-code-sdk` PyPI package: Superseded by `claude-agent-sdk`. Do not use.
- `subprocess.Popen` for Claude Code: The SDK handles all process management. Manual pipe management risks deadlocks.

## Open Questions

1. **Claude Code binary availability**
   - What we know: claude-agent-sdk bundles Claude Code CLI. Can also specify custom path via `cli_path`.
   - What's unclear: Whether the bundled CLI works on macOS without separate `npm install -g @anthropic-ai/claude-code`.
   - Recommendation: Test during implementation. Add a startup health check that runs `claude --version`. If it fails, log a clear error message.

2. **Session resumption across ClaudeSDKClient restarts**
   - What we know: `ClaudeAgentOptions.resume` accepts a session_id to resume a previous session. `continue_conversation=True` continues the most recent.
   - What's unclear: Whether resume works after the subprocess has been fully terminated (vs. just disconnected).
   - Recommendation: For crash recovery, try `resume=session_id` first. If it fails, start fresh and notify the user.

3. **pydantic-settings vs python-dotenv**
   - What we know: pydantic-settings is more type-safe but adds a dependency.
   - Recommendation: Use pydantic-settings since Pydantic is already installed via FastAPI. Shown in config example above.

## Sources

### Primary (HIGH confidence)
- [Claude Agent SDK Python Reference](https://platform.claude.com/docs/en/agent-sdk/python) -- ClaudeSDKClient, ClaudeAgentOptions, @tool, create_sdk_mcp_server, Message types, StreamEvent
- [claude-agent-sdk PyPI](https://pypi.org/project/claude-agent-sdk/) -- v0.1.48, March 7 2026, Python 3.10+
- [FastAPI WebSocket Docs](https://fastapi.tiangolo.com/advanced/websockets/) -- WebSocket endpoint patterns
- [Vite Server Options](https://vite.dev/config/server-options) -- Proxy configuration with `ws: true`

### Secondary (MEDIUM confidence)
- [WebSocket Heartbeat Patterns](https://oneuptime.com/blog/post/2026-01-27-websocket-heartbeat/view) -- Ping/pong implementation
- [Inside the Claude Agent SDK](https://buildwithaws.substack.com/p/inside-the-claude-agent-sdk-from) -- Subprocess architecture details
- [websockets keepalive docs](https://websockets.readthedocs.io/en/stable/topics/keepalive.html) -- Protocol-level vs application-level keepalive

### Tertiary (LOW confidence)
- None -- all findings verified against primary or secondary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All libraries verified against official docs and PyPI
- Architecture: HIGH -- Patterns derived from official SDK examples and documented FastAPI patterns
- Pitfalls: HIGH -- Documented in prior v2.0 research with GitHub issue references
- Claude Agent SDK API: HIGH -- Full API reference fetched from official docs on 2026-03-09

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (claude-agent-sdk is fast-moving; recheck if SDK version changes)
