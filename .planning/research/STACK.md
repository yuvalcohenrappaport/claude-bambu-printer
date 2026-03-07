# Stack Research: v2.0 Web Dashboard Additions

**Domain:** Web dashboard for Claude Code-backed 3D printing (React frontend, FastAPI backend, real-time communication)
**Researched:** 2026-03-08
**Confidence:** HIGH
**Scope:** NEW technologies only. Existing v1.0 stack (OpenSCAD, Playwright, bambu-lab-cloud-api, Python scripts) is validated and unchanged.

## Recommended Stack

### Backend — Python (FastAPI + Claude Agent SDK)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **FastAPI** | 0.135.x | HTTP + WebSocket server | Native WebSocket support via ASGI, async-first, Pydantic integration for typed messages. Matches existing Python codebase. | HIGH |
| **uvicorn** | 0.34.x | ASGI server | Standard production server for FastAPI. Supports WebSocket upgrade out of the box. | HIGH |
| **claude-agent-sdk** | 0.1.48 | Claude Code integration | Official Anthropic Python SDK. `ClaudeSDKClient` provides bidirectional conversation with session continuity, streaming responses, interrupt support, and in-process MCP server via `create_sdk_mcp_server()`. Replaces raw subprocess management. | HIGH |
| **aiomqtt** | 2.5.1 | Async MQTT client | Wraps paho-mqtt with async/await. Needed to subscribe to BambuLab printer MQTT topics and relay status to browser via WebSocket. Only dependency is paho-mqtt. | HIGH |
| **pydantic** | 2.x | Message/event validation | Already a FastAPI dependency. Use for typed WebSocket message schemas (chat messages, printer events, model updates). | HIGH |

### Frontend — React + Vite + Three.js

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **React** | 19.x | UI framework | Latest stable. Required by @react-three/fiber v9. User knows React (Any-button project). | HIGH |
| **Vite** | 6.x | Build tool + dev server | Fast HMR, TypeScript out of the box, `react-ts` template. Standard for new React projects. | HIGH |
| **TypeScript** | 5.x | Type safety | Catches WebSocket message shape errors at build time. User preference (from CLAUDE.md). | HIGH |
| **Three.js** | 0.183.x | 3D rendering engine | Built-in `STLLoader` and `ThreeMFLoader` in `three/addons/loaders/`. Both are official addons — no third-party viewer needed. | HIGH |
| **@react-three/fiber** | 9.x | React renderer for Three.js | Declarative Three.js in JSX. `useLoader(STLLoader, url)` and `useLoader(ThreeMFLoader, url)` for loading models. Massive ecosystem (drei helpers). | HIGH |
| **@react-three/drei** | 10.x | R3F helper components | `OrbitControls`, `Stage`, `Center`, `Grid` — all needed for a model viewer. Saves building camera controls from scratch. | HIGH |

### MCP Server (Claude Code -> UI updates)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **claude-agent-sdk** (built-in) | 0.1.48 | In-process MCP server | `create_sdk_mcp_server()` + `@tool` decorator defines MCP tools that Claude Code can call. Tools push events to FastAPI which relays to browser via WebSocket. No separate MCP server process needed. | HIGH |

**Key insight:** The Claude Agent SDK bundles MCP server creation. You define Python functions as MCP tools, register them with `create_sdk_mcp_server()`, and pass to `ClaudeAgentOptions.mcp_servers`. When Claude calls a tool (e.g., `update_3d_preview`), your Python handler fires, pushes the update through FastAPI WebSocket to the browser. No `mcp` PyPI package needed separately.

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **websockets** | 14.x | WebSocket protocol (FastAPI dep) | Installed automatically with FastAPI. No explicit install needed. |
| **python-multipart** | 0.0.x | File upload parsing | When user uploads STL/3MF files through the web UI for preview or printing. |
| **aiofiles** | 24.x | Async file I/O | Serving generated 3MF/STL files to the browser for Three.js preview. |
| **zustand** | 5.x | React state management | Client-side state: chat messages, printer status, current model, WebSocket connection. User already knows zustand (Any-button). |
| **react-hot-toast** | 2.x | Toast notifications | Print started/completed/failed notifications. Lightweight. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **Vite** (dev server) | Frontend dev with HMR | Proxy `/api` and `/ws` to FastAPI backend in `vite.config.ts` |
| **ruff** | Python linting + formatting | Already used in v1.0 |
| **pytest** | Python testing | Test WebSocket handlers, MCP tool handlers, MQTT relay |
| **vitest** | Frontend testing | Vite-native test runner, faster than Jest for Vite projects |

## Architecture: How These Connect

```
Browser (React + Three.js)
  |
  |-- WebSocket /ws/chat ---------> FastAPI
  |                                    |
  |                                    +-- ClaudeSDKClient (Agent SDK)
  |                                    |     |
  |                                    |     +-- MCP tools (in-process)
  |                                    |           |
  |                                    |           +-- update_preview(model_path)
  |                                    |           +-- show_search_results(results)
  |                                    |           +-- update_printer_status(status)
  |                                    |           |
  |                                    |           +-- Each tool handler pushes
  |                                    |               event back through WebSocket
  |                                    |
  |-- WebSocket /ws/printer ------> FastAPI
  |                                    |
  |                                    +-- aiomqtt subscriber
  |                                          |
  |                                          +-- BambuLab printer (MQTT 8883)
  |
  |-- HTTP GET /api/models/:id ----> FastAPI
  |     (serves .stl/.3mf files        |
  |      for Three.js loader)          +-- Local filesystem
```

## Installation

```bash
# Backend (from project root)
python -m venv .venv
source .venv/bin/activate

# Core backend
pip install fastapi uvicorn claude-agent-sdk aiomqtt pydantic

# File handling
pip install python-multipart aiofiles

# Dev
pip install pytest ruff

# Frontend (from web/ directory)
npm create vite@latest web -- --template react-swc-ts
cd web
npm install three @react-three/fiber @react-three/drei zustand react-hot-toast
npm install -D @types/three vitest
```

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| **FastAPI** | Django Channels | Django is overkill — no ORM/admin/templates needed. FastAPI is lighter, async-native, better WebSocket DX. |
| **FastAPI** | Flask + SocketIO | Flask-SocketIO uses polling fallback. FastAPI native WebSocket is cleaner and faster. |
| **claude-agent-sdk** | Raw `subprocess.Popen` with stream-json | Agent SDK handles all subprocess lifecycle, message parsing, MCP integration, interrupts. Raw subprocess would require reimplementing all of this. |
| **claude-agent-sdk** | Claude API directly (no Claude Code) | Loses all Claude Code capabilities: file editing, bash execution, tool use, skills. The whole point is Claude Code as the brain. |
| **@react-three/fiber** | Raw Three.js | R3F gives declarative React components. Raw Three.js requires imperative scene management, manual cleanup, no React integration. |
| **@react-three/fiber** | react-stl-viewer (npm) | Unmaintained (2+ years). Only supports STL, not 3MF. R3F with Three.js loaders handles both formats with full control. |
| **aiomqtt** | paho-mqtt (sync) | paho-mqtt is callback-based and synchronous. aiomqtt wraps it for async/await, which is essential inside FastAPI's async event loop. |
| **aiomqtt** | fastapi-mqtt | fastapi-mqtt is a thin wrapper. aiomqtt is more mature and doesn't couple MQTT to FastAPI lifecycle. |
| **zustand** | Redux Toolkit | Zustand is simpler, less boilerplate, no providers. Perfect for medium-complexity state. User already uses it. |
| **zustand** | React Context | Context causes re-renders on every update. WebSocket messages arrive frequently — zustand's selector-based updates prevent unnecessary re-renders. |
| **Vite** | Next.js | No SSR needed. No routing complexity. Single-page dashboard with WebSocket. Vite is lighter and simpler. |
| **react-swc-ts template** | react-ts template | SWC is faster than Babel for transpilation. Same output, faster builds. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Socket.IO** | Adds unnecessary abstraction over WebSocket. FastAPI has native WebSocket support. Socket.IO's fallback to polling is not needed in 2026. | FastAPI native WebSocket |
| **django-channels** | Pulls in Django ORM, migrations, admin. Massive overhead for a WebSocket relay server. | FastAPI |
| **claude-code-sdk** (PyPI) | Deprecated. Superseded by `claude-agent-sdk`. | `claude-agent-sdk` |
| **subprocess.Popen** for Claude | Manual process management, no MCP integration, no typed messages, no interrupt support. | `claude-agent-sdk` ClaudeSDKClient |
| **react-3d-model-viewer** (npm) | Thin wrapper over Three.js, limited customization, small community. | @react-three/fiber + Three.js loaders directly |
| **mqtt.js** (browser MQTT) | Would require exposing MQTT broker to internet or running a broker with WebSocket support. Security risk. | Backend MQTT relay via aiomqtt -> WebSocket |
| **Separate MCP server process** | The `mcp` PyPI package runs as a separate stdio process. Unnecessary complexity when claude-agent-sdk has `create_sdk_mcp_server()` for in-process MCP. | claude-agent-sdk in-process MCP |
| **PostgreSQL/SQLite** | No persistent data needed. Chat history lives in Claude Code session. Printer status is real-time. Models are files. | Filesystem + in-memory state |

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| claude-agent-sdk 0.1.48 | Python 3.10+ | Bundles Claude Code CLI. Requires Claude Code to be installed (`npm install -g @anthropic-ai/claude-code`). |
| FastAPI 0.135.x | Python 3.8+ | No conflicts with claude-agent-sdk. Both async-first. |
| aiomqtt 2.5.1 | Python 3.8+, paho-mqtt 1.x/2.x | Compatible with existing bambu-lab-cloud-api which also uses paho-mqtt. |
| @react-three/fiber 9.x | React 19.x, Three.js 0.160+ | Must pin React 19 and Three.js together. drei 10.x is compatible. |
| Three.js 0.183.x | STLLoader, ThreeMFLoader | Both loaders are in `three/addons/loaders/` — no separate package needed. |
| Vite 6.x | React 19.x, TypeScript 5.x | react-swc-ts template includes all config. |

## Critical Technical Notes

### Claude Agent SDK — The Core Integration

The `claude-agent-sdk` is the most important new dependency. It provides:

1. **ClaudeSDKClient** — Maintains a bidirectional conversation with Claude Code across multiple exchanges. Async context manager with `connect()`, `query()`, `receive_response()`, `interrupt()`.

2. **In-process MCP server** — `create_sdk_mcp_server()` + `@tool` decorator. Define Python functions as MCP tools that Claude Code can call. This is how Claude Code pushes UI updates:

```python
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeSDKClient, ClaudeAgentOptions

@tool("update_preview", "Update the 3D preview in the browser", {"model_path": str})
async def update_preview(args):
    # Push update through WebSocket to browser
    await websocket_manager.broadcast({"type": "preview_update", "path": args["model_path"]})
    return {"content": [{"type": "text", "text": "Preview updated"}]}

mcp_server = create_sdk_mcp_server("printer-ui", tools=[update_preview])

options = ClaudeAgentOptions(
    mcp_servers={"ui": mcp_server},
    allowed_tools=["mcp__ui__update_preview", "Bash", "Read", "Write", "Edit"],
    permission_mode="acceptEdits",
    cwd="/path/to/project",
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Generate a phone stand model")
    async for message in client.receive_response():
        # Stream Claude's text responses to browser via WebSocket
        pass
```

3. **Custom permission handler** — `can_use_tool` callback controls which tools Claude can execute. Essential for sandboxing in a web-facing context.

### Three.js 3MF Loading

Three.js has a built-in `ThreeMFLoader` in addons. Import pattern:

```typescript
import { useLoader } from '@react-three/fiber'
import { STLLoader } from 'three/addons/loaders/STLLoader.js'
import { ThreeMFLoader } from 'three/addons/loaders/3MFLoader.js'

// In component:
const geometry = useLoader(STLLoader, '/api/models/phone-stand.stl')
// or
const group = useLoader(ThreeMFLoader, '/api/models/phone-stand.3mf')
```

The backend serves model files via HTTP GET. The frontend loads them with Three.js loaders. No file conversion needed.

### MQTT Relay Pattern

BambuLab printers publish status over MQTT (port 8883, TLS). The browser cannot connect directly (no TLS MQTT in browser, credentials exposure). Pattern:

```python
# Backend subscribes to printer MQTT, relays to browser WebSocket
async def mqtt_relay(websocket_manager):
    async with aiomqtt.Client(
        hostname=printer_ip,
        port=8883,
        tls_context=ssl_context,
        username="bblp",
        password=access_code,
    ) as client:
        await client.subscribe(f"device/{serial}/report")
        async for message in client.messages:
            status = parse_bambu_status(message.payload)
            await websocket_manager.broadcast({"type": "printer_status", **status})
```

### WebSocket Message Protocol

Two WebSocket endpoints, typed with Pydantic:

```python
# /ws/chat — User <-> Claude Code conversation
class ChatMessage(BaseModel):
    type: Literal["user_message", "assistant_message", "tool_use", "preview_update", "search_results"]
    content: str | dict

# /ws/printer — Real-time printer status
class PrinterEvent(BaseModel):
    type: Literal["status", "progress", "temperature", "error"]
    data: dict
```

## Sources

- [Claude Agent SDK Python Reference](https://platform.claude.com/docs/en/agent-sdk/python) -- ClaudeSDKClient API, MCP server creation, tool decorator (HIGH confidence)
- [claude-agent-sdk PyPI](https://pypi.org/project/claude-agent-sdk/) -- v0.1.48, March 7 2026 (HIGH confidence)
- [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference) -- stream-json flags, MCP config (HIGH confidence)
- [FastAPI WebSocket docs](https://fastapi.tiangolo.com/advanced/websockets/) -- native WebSocket support (HIGH confidence)
- [Three.js ThreeMFLoader docs](https://threejs.org/docs/pages/ThreeMFLoader.html) -- built-in 3MF support (HIGH confidence)
- [Three.js STLLoader docs](https://threejs.org/docs/pages/STLLoader.html) -- built-in STL support (HIGH confidence)
- [React Three Fiber docs](https://r3f.docs.pmnd.rs/) -- v9, useLoader pattern (HIGH confidence)
- [@react-three/drei npm](https://www.npmjs.com/package/@react-three/drei) -- v10.7.7 (HIGH confidence)
- [aiomqtt PyPI](https://pypi.org/project/aiomqtt/) -- v2.5.1, async MQTT client (HIGH confidence)
- [MCP Python SDK](https://pypi.org/project/mcp/) -- v1.26.0, referenced by claude-agent-sdk internally (MEDIUM confidence)
- [Three.js npm](https://www.npmjs.com/package/three) -- v0.183.2 (HIGH confidence)

---
*Stack research for: v2.0 Web Dashboard — Claude BambuLab Printer Interface*
*Researched: 2026-03-08*
