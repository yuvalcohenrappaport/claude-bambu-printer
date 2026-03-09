# Phase 5: Backend Foundation - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

FastAPI server with WebSocket infrastructure and Claude Code subprocess lifecycle management. Users connect to the dashboard and get a stable, isolated session with Claude Code running behind the scenes. No chat UI, no 3D viewer, no printer features — just the foundation layer.

</domain>

<decisions>
## Implementation Decisions

### Session Lifecycle
- Claude Code subprocess spawns immediately on page load (not on first message)
- 30-second grace period on disconnect before killing subprocess (handles accidental close/refresh)
- Idle timeout with warning — warn user after idle period, kill subprocess if no response
- One session at a time — opening a new tab takes over the existing session

### Project Structure
- Monorepo: frontend and backend in the same repo alongside existing skill files
- Top-level split: `/frontend` and `/backend` as top-level folders
- Frontend: npm (not bun)
- Backend: Poetry for dependency management (growing backend warrants it)

### Dev Experience
- Separate terminals for frontend and backend (not a single command)
- Backend port: 8000 (FastAPI default)
- Backend auto-reload: uvicorn --reload in development
- Frontend dev server on default Vite port (5173)

### Error Handling
- Claude Code crash: auto-restart subprocess silently, show "Session recovered" message in chat
- WebSocket drop: auto-reconnect with exponential backoff, show "Reconnecting..." indicator
- Backend down: full-page error screen ("Cannot connect to server" + retry button)
- Logging: stdout + file (for post-hoc debugging)

### Claude's Discretion
- Dev proxy configuration (Vite proxy vs direct URLs)
- Exact idle timeout duration
- Log file location and rotation
- WebSocket heartbeat interval
- Grace period implementation details

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. This is infrastructure, so standard FastAPI + WebSocket patterns apply.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-backend-foundation*
*Context gathered: 2026-03-09*
