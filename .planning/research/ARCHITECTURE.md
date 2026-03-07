# Architecture Patterns

**Domain:** Web dashboard for Claude-powered 3D printing (v2.0)
**Researched:** 2026-03-08
**Supersedes:** v1.0 architecture (CLI skill with script-per-action pattern)

## System Overview

The v2.0 architecture adds a web layer on top of the existing v1.0 scripts. The key challenge is bridging three async communication channels: browser WebSocket, Claude Code subprocess stdio, and printer MQTT -- all through a single FastAPI backend.

```
Browser (React + Three.js)
    |
    | WebSocket (bidirectional)
    |
FastAPI Backend
    |
    +-- Claude Code subprocess (via claude-agent-sdk)
    |       |
    |       +-- Uses existing v1.0 scripts (printer_control.py, etc.)
    |       +-- Calls MCP tools to push UI updates back
    |
    +-- MCP Server (in-process, registered with Claude Code)
    |       |
    |       +-- update_preview(file_path)
    |       +-- update_status(message)
    |       +-- show_search_results(results)
    |       +-- request_confirmation(prompt, options)
    |
    +-- MQTT Bridge (persistent connection to BambuLab cloud)
            |
            +-- Streams printer status to all connected WebSocket clients
```

## Component Architecture

### Component 1: FastAPI Backend (New)

**Responsibility:** Central hub. Manages WebSocket connections, Claude Code subprocess lifecycle, MCP server registration, and MQTT bridging.

**File:** `backend/server.py`

```python
# Core structure
from fastapi import FastAPI, WebSocket
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk import tool, create_sdk_mcp_server

app = FastAPI()

# State per WebSocket connection
class Session:
    websocket: WebSocket
    claude_client: ClaudeSDKClient | None
    session_id: str
```

**Key endpoints:**
- `GET /` -- Serve React SPA
- `WS /ws` -- Main WebSocket for chat + UI updates
- `WS /ws/printer` -- Dedicated WebSocket for MQTT printer status stream

### Component 2: Claude Code Subprocess Manager (New)

**Responsibility:** Manages ClaudeSDKClient lifecycle per browser session. Relays user messages to Claude Code, streams responses back.

**Why ClaudeSDKClient over query():** Users have multi-turn conversations. ClaudeSDKClient maintains session context across exchanges, supports interrupts (for canceling long-running operations), and provides explicit lifecycle control.

**Confidence:** HIGH -- Official Python SDK documentation confirms ClaudeSDKClient is designed for "interactive applications, chat interfaces" with session continuity.

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import StreamEvent

class ClaudeManager:
    """One instance per browser session."""

    def __init__(self, websocket: WebSocket, mcp_server):
        self.ws = websocket
        self.client: ClaudeSDKClient | None = None
        self.mcp_server = mcp_server

    async def start(self):
        options = ClaudeAgentOptions(
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": "You are controlling a 3D printer through a web dashboard. "
                          "Use MCP tools to update the UI."
            },
            permission_mode="acceptEdits",
            cwd="/path/to/project",
            mcp_servers={"dashboard": self.mcp_server},
            allowed_tools=[
                "Bash", "Read", "Write", "Glob", "Grep",
                "mcp__dashboard__update_preview",
                "mcp__dashboard__update_status",
                "mcp__dashboard__show_search_results",
                "mcp__dashboard__request_confirmation",
            ],
            include_partial_messages=True,
            setting_sources=["user", "project"],  # Load CLAUDE.md + skills
        )
        self.client = ClaudeSDKClient(options=options)
        await self.client.connect()

    async def send_message(self, user_message: str):
        """Send user message and stream response back via WebSocket."""
        await self.client.query(user_message)

        async for message in self.client.receive_response():
            if isinstance(message, StreamEvent):
                event = message.event
                if event.get("type") == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        await self.ws.send_json({
                            "type": "assistant_text",
                            "text": delta.get("text", "")
                        })

    async def interrupt(self):
        if self.client:
            await self.client.interrupt()

    async def stop(self):
        if self.client:
            await self.client.disconnect()
```

**Critical design decisions:**

1. **One ClaudeSDKClient per browser session** -- Not shared. Each user gets their own Claude Code subprocess with its own conversation context.

2. **include_partial_messages=True** -- Required for streaming text tokens to the browser in real-time rather than waiting for complete responses.

3. **setting_sources includes "project"** -- This loads the existing SKILL.md so Claude Code knows how to use the printer scripts. The v1.0 scripts work unchanged.

4. **Permission mode "acceptEdits"** -- Auto-approves file edits (model generation writes .scad files). In a web context, the user can't respond to permission prompts.

### Component 3: MCP Server for UI Updates (New)

**Responsibility:** Provides tools that Claude Code calls to push updates to the browser. This is the "reverse channel" -- Claude Code decides when to update the UI.

**Why in-process MCP (not stdio/HTTP):** The claude-agent-sdk provides `create_sdk_mcp_server()` which runs the MCP server in the same Python process as the backend. No separate process management needed. The tools have direct access to the WebSocket connection to push updates.

**Confidence:** HIGH -- Official SDK docs show `create_sdk_mcp_server()` + `@tool` decorator for exactly this pattern.

```python
from claude_agent_sdk import tool, create_sdk_mcp_server

# Each tool handler receives the WebSocket reference via closure
def create_dashboard_mcp(websocket_sender):
    """Create MCP server with tools that push to browser."""

    @tool(
        "update_preview",
        "Update the 3D preview in the browser. Call after generating or modifying a model.",
        {"file_path": str, "file_type": str}
    )
    async def update_preview(args):
        await websocket_sender({
            "type": "preview_update",
            "file_path": args["file_path"],
            "file_type": args["file_type"],  # "scad", "3mf", "stl"
        })
        return {"content": [{"type": "text", "text": "Preview updated in browser."}]}

    @tool(
        "update_status",
        "Show a status message to the user in the dashboard.",
        {"message": str, "level": str}
    )
    async def update_status(args):
        await websocket_sender({
            "type": "status_update",
            "message": args["message"],
            "level": args.get("level", "info"),  # info, success, warning, error
        })
        return {"content": [{"type": "text", "text": "Status shown."}]}

    @tool(
        "show_search_results",
        "Display MakerWorld search results in the browser with thumbnails and details.",
        {"results": str}  # JSON string of search results
    )
    async def show_search_results(args):
        await websocket_sender({
            "type": "search_results",
            "results": args["results"],
        })
        return {"content": [{"type": "text", "text": "Search results displayed."}]}

    @tool(
        "request_confirmation",
        "Ask the user to confirm an action (e.g., send to printer, cancel print).",
        {"prompt": str, "options": str}  # JSON string of options
    )
    async def request_confirmation(args):
        await websocket_sender({
            "type": "confirmation_request",
            "prompt": args["prompt"],
            "options": args["options"],
        })
        return {"content": [{"type": "text", "text": "Waiting for user confirmation..."}]}

    return create_sdk_mcp_server(
        name="dashboard",
        version="1.0.0",
        tools=[update_preview, update_status, show_search_results, request_confirmation],
    )
```

**How the MCP tools work in practice:**

1. User types "find me a phone stand" in the web chat
2. Backend relays to Claude Code subprocess
3. Claude Code runs `makerworld_search.py` (existing v1.0 script)
4. Claude Code calls `mcp__dashboard__show_search_results` with the results
5. The MCP tool handler pushes results to browser via WebSocket
6. Browser renders the card grid UI
7. Claude Code also responds with text: "I found 3 models on MakerWorld..."

### Component 4: MQTT Bridge (New)

**Responsibility:** Maintains a persistent MQTT connection to BambuLab cloud and relays printer status to all connected WebSocket clients.

**Why separate from Claude Code:** MQTT status streaming is continuous and independent of Claude Code conversations. It should run as a background task in the FastAPI process, not through Claude Code.

**Confidence:** MEDIUM -- The bambu-lab-cloud-api MQTTClient works with `blocking=False` and callback-based messages, but it's synchronous (paho-mqtt). Need to bridge to asyncio.

```python
import asyncio
import threading
from bambulab import MQTTClient

class MQTTBridge:
    """Bridges BambuLab MQTT to WebSocket clients."""

    def __init__(self):
        self.subscribers: set[WebSocket] = set()
        self.mqtt: MQTTClient | None = None
        self.latest_status: dict = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self, config: dict, loop: asyncio.AbstractEventLoop):
        """Start MQTT in background thread, push to asyncio loop."""
        self._loop = loop
        printer = config.get("printer", {})

        def on_message(dev_id, data):
            p = data.get("print", {})
            if not p:
                return
            status = {
                "state": p.get("gcode_state", "UNKNOWN"),
                "progress": p.get("mc_percent", 0),
                "eta_minutes": p.get("mc_remaining_time", 0),
                "layer": p.get("layer_num", 0),
                "total_layers": p.get("total_layer_num", 0),
                "nozzle_temp": p.get("nozzle_temper", 0),
                "nozzle_target": p.get("nozzle_target_temper", 0),
                "bed_temp": p.get("bed_temper", 0),
                "bed_target": p.get("bed_target_temper", 0),
                "speed": p.get("spd_lvl", 100),
                "task_name": p.get("subtask_name", ""),
            }
            self.latest_status = status
            # Schedule async broadcast from sync callback
            asyncio.run_coroutine_threadsafe(
                self._broadcast(status), self._loop
            )

        self.mqtt = MQTTClient(
            username=f"u_{config['user_id']}",
            access_token=config["token"],
            device_id=printer.get("device_id"),
            on_message=on_message,
        )

        # Run MQTT in background thread (paho-mqtt is synchronous)
        thread = threading.Thread(target=self._run_mqtt, daemon=True)
        thread.start()

    def _run_mqtt(self):
        self.mqtt.connect(blocking=True)

    async def _broadcast(self, status: dict):
        dead = set()
        for ws in self.subscribers:
            try:
                await ws.send_json({"type": "printer_status", **status})
            except Exception:
                dead.add(ws)
        self.subscribers -= dead

    def subscribe(self, ws: WebSocket):
        self.subscribers.add(ws)
        # Send current status immediately on connect
        if self.latest_status:
            asyncio.create_task(
                ws.send_json({"type": "printer_status", **self.latest_status})
            )

    def unsubscribe(self, ws: WebSocket):
        self.subscribers.discard(ws)
```

**Threading concern:** The bambu-lab-cloud-api MQTTClient uses paho-mqtt internally, which is synchronous. The bridge runs MQTT in a daemon thread and uses `asyncio.run_coroutine_threadsafe()` to safely push messages into the FastAPI event loop.

### Component 5: React Frontend (New)

**Responsibility:** Chat interface, 3D preview, printer status panel, MakerWorld search results.

**File structure:**
```
frontend/
  src/
    App.tsx
    components/
      ChatPanel.tsx          -- Message input + streaming response display
      PreviewPanel.tsx        -- Three.js 3D model viewer
      PrinterStatus.tsx       -- Live printer metrics
      SearchResults.tsx       -- MakerWorld card grid
      ConfirmationDialog.tsx  -- Modal for user confirmations
    hooks/
      useWebSocket.ts         -- Main WS connection + message routing
      usePrinterStatus.ts     -- Printer WS connection
    services/
      websocket.ts            -- WebSocket client singleton
      modelLoader.ts          -- Load .3mf/.stl into Three.js
    types/
      messages.ts             -- WebSocket message type definitions
```

### Component 6: Existing v1.0 Scripts (Unchanged)

**No modifications needed.** Claude Code runs the existing scripts via Bash tool exactly as in v1.0:
- `printer_control.py` -- send, status, pause, resume, cancel
- `printer_setup.py` -- auth flow
- `makerworld_search.py` -- search and download
- OpenSCAD CLI -- model generation and rendering

The scripts remain CLI tools that output JSON to stdout. Claude Code wraps them.

## Data Flow Diagrams

### Flow 1: User sends chat message

```
Browser                    FastAPI                  Claude Code Subprocess
   |                          |                           |
   |--WS: {type: "chat",---->|                           |
   |   text: "make a box"}   |                           |
   |                          |--client.query("make..")->|
   |                          |                           |
   |                          |<--StreamEvent (text)------|
   |<--WS: {type:             |                           |
   |   "assistant_text",      |                           |
   |   text: "I'll..."}------|                           |
   |                          |                           |
   |                          |  (Claude runs OpenSCAD)   |
   |                          |                           |
   |                          |<--MCP: update_preview-----|
   |<--WS: {type:             |                           |
   |   "preview_update",      |                           |
   |   file_path: "..."}------|                           |
   |                          |                           |
   |  (Three.js loads model)  |                           |
```

### Flow 2: Live printer status

```
BambuLab Cloud MQTT        FastAPI (MQTTBridge)      Browser
       |                          |                      |
       |--MQTT: print status----->|                      |
       |  (paho-mqtt thread)      |                      |
       |                          |--asyncio.run_       |
       |                          |  coroutine_         |
       |                          |  threadsafe()       |
       |                          |                      |
       |                          |--WS: {type:--------->|
       |                          |  "printer_status",   |
       |                          |  progress: 45, ...}  |
       |                          |                      |
       |                          |  (React updates UI)  |
```

### Flow 3: Confirmation dialog (e.g., send to printer)

```
Browser                    FastAPI                  Claude Code
   |                          |                        |
   |                          |<--MCP: request_        |
   |                          |  confirmation(         |
   |                          |  "Send to printer?",   |
   |                          |  ["Send", "Cancel"])---|
   |                          |                        |
   |<--WS: {type:             |                        |
   |  "confirmation_request", |                        |
   |  prompt: "Send...",      |                        |
   |  options: [...]}---------|                        |
   |                          |                        |
   |  (User clicks "Send")   |                        |
   |                          |                        |
   |--WS: {type: "chat",---->|                        |
   |  text: "Send"}          |                        |
   |                          |--client.query("Send")->|
   |                          |                        |
   |                          | (Claude calls          |
   |                          |  printer_control.py)   |
```

## WebSocket Message Protocol

All messages are JSON with a `type` field for routing.

### Browser -> Backend

| Type | Fields | Description |
|------|--------|-------------|
| `chat` | `text: string` | User message to relay to Claude Code |
| `interrupt` | -- | Cancel current Claude Code operation |
| `printer_subscribe` | -- | Start receiving MQTT printer updates |

### Backend -> Browser

| Type | Fields | Description |
|------|--------|-------------|
| `assistant_text` | `text: string` | Streaming text chunk from Claude |
| `assistant_complete` | `message_id: string` | Claude finished responding |
| `preview_update` | `file_path: string, file_type: string` | New/updated 3D model to display |
| `status_update` | `message: string, level: string` | Toast/status message |
| `search_results` | `results: SearchResult[]` | MakerWorld search results |
| `confirmation_request` | `prompt: string, options: string[]` | Needs user decision |
| `printer_status` | `state, progress, temps, ...` | Live printer metrics |
| `error` | `message: string` | Error from backend |

## Patterns to Follow

### Pattern 1: In-Process MCP Server via SDK

**What:** Use `claude-agent-sdk`'s `create_sdk_mcp_server()` to register MCP tools that run inside the FastAPI process, with direct access to WebSocket connections.

**When:** Always. This is how Claude Code pushes UI updates.

**Why:** No separate MCP server process to manage. Tools are Python functions with closure access to the WebSocket. The SDK handles all MCP protocol details.

**Confidence:** HIGH -- Official SDK API.

### Pattern 2: Streaming Text via StreamEvent

**What:** Enable `include_partial_messages=True` and filter for `content_block_delta` events with `text_delta` type. Forward each chunk as a WebSocket message.

**When:** For all chat responses.

**Why:** Users expect to see text appear incrementally, not wait for the full response. This is the same pattern used by ChatGPT-style interfaces.

**Confidence:** HIGH -- Official SDK streaming docs.

### Pattern 3: Threaded MQTT with asyncio Bridge

**What:** Run paho-mqtt in a daemon thread, use `asyncio.run_coroutine_threadsafe()` to push messages into the FastAPI event loop.

**When:** For MQTT printer status.

**Why:** paho-mqtt (used by bambu-lab-cloud-api) is synchronous. Can't run it in the asyncio event loop without blocking. The thread bridge is the standard pattern.

**Confidence:** MEDIUM -- Standard asyncio pattern, but bambu-lab-cloud-api's internal MQTT behavior not fully verified for long-running connections.

### Pattern 4: File Serving for 3D Preview

**What:** When Claude generates a model, the MCP tool sends the file path. The frontend fetches the file via an HTTP endpoint (e.g., `GET /api/files/{path}`).

**When:** For preview updates.

**Why:** WebSocket is for messages, not file transfer. Three.js loaders expect HTTP URLs. The backend serves files from `~/3d-prints/` via a static file mount or dynamic endpoint.

```python
from fastapi.staticfiles import StaticFiles
app.mount("/prints", StaticFiles(directory=os.path.expanduser("~/3d-prints")), name="prints")
```

### Pattern 5: Graceful Session Lifecycle

**What:** Create ClaudeSDKClient on WebSocket connect, disconnect on WebSocket close. Handle reconnection by resuming the session.

**When:** Always.

**Why:** Each Claude Code subprocess consumes resources. Must clean up on disconnect. Session ID allows resumption.

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    manager = ClaudeManager(websocket, mcp_server)
    try:
        await manager.start()
        while True:
            data = await websocket.receive_json()
            if data["type"] == "chat":
                await manager.send_message(data["text"])
            elif data["type"] == "interrupt":
                await manager.interrupt()
    except WebSocketDisconnect:
        await manager.stop()
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Running Claude Code via CLI subprocess directly

**What:** Spawning `claude -p "message"` as a new subprocess for each user message.

**Why bad:** Each invocation creates a new session (50K+ tokens of context loading). No conversation continuity. Massive latency and cost.

**Instead:** Use `ClaudeSDKClient` which maintains a persistent subprocess with session state.

### Anti-Pattern 2: Separate stdio MCP server process

**What:** Running a standalone MCP server as a separate process and configuring Claude Code to connect to it.

**Why bad:** Unnecessary process management complexity. The MCP server needs access to WebSocket connections (which live in the FastAPI process). Cross-process communication adds latency and failure modes.

**Instead:** Use `create_sdk_mcp_server()` for an in-process MCP server.

### Anti-Pattern 3: Polling printer status through Claude Code

**What:** Having Claude Code periodically run `printer_control.py status` and relay results.

**Why bad:** Wastes Claude Code tokens/turns on repetitive status checks. MQTT provides push-based updates. Claude Code should be reserved for user-initiated actions.

**Instead:** Dedicated MQTT bridge independent of Claude Code.

### Anti-Pattern 4: Single WebSocket for everything

**What:** Mixing chat messages and high-frequency printer status on one WebSocket.

**Why bad:** Printer status updates every 1-2 seconds. Chat messages need reliable ordering. Mixing them complicates client-side routing and can cause backpressure issues.

**Instead:** Separate WebSocket endpoints: `/ws` for chat/UI updates, `/ws/printer` for MQTT stream. Frontend connects to both.

### Anti-Pattern 5: Modifying v1.0 scripts for web integration

**What:** Refactoring printer_control.py or makerworld_search.py to work differently for the web dashboard.

**Why bad:** Breaks the working v1.0 CLI skill. The scripts are designed as CLI tools with JSON stdout -- this is exactly how Claude Code calls them.

**Instead:** Keep scripts unchanged. The web layer wraps Claude Code, which wraps the scripts. Same chain, new frontend.

## Component Boundaries

| Component | Responsibility | Communicates With | New/Modified |
|-----------|---------------|-------------------|--------------|
| **React Frontend** | UI rendering, Three.js preview, user input | FastAPI (WebSocket) | NEW |
| **FastAPI Server** | WebSocket hub, session management, file serving | Frontend, Claude Code, MQTT | NEW |
| **ClaudeManager** | Claude Code subprocess lifecycle, message relay | FastAPI, MCP Server | NEW |
| **MCP Server (in-process)** | UI update tools for Claude Code | ClaudeManager, FastAPI | NEW |
| **MQTTBridge** | Persistent printer MQTT connection | BambuLab Cloud, FastAPI | NEW |
| **SKILL.md** | Claude Code instructions | Claude Code runtime | MINOR UPDATE (add MCP tool descriptions) |
| **printer_control.py** | Send, status, pause, resume, cancel | BambuLab Cloud API | UNCHANGED |
| **printer_setup.py** | Auth flow, config management | BambuLab Cloud API | UNCHANGED |
| **makerworld_search.py** | Search + download from MakerWorld | MakerWorld (Playwright) | UNCHANGED |

## Build Order (Dependency-Driven)

Build order follows strict dependency chains:

1. **Backend skeleton + WebSocket** -- Foundation for everything else
2. **Frontend skeleton + chat UI** -- Can test WebSocket relay immediately
3. **Claude Code subprocess integration** -- Depends on backend skeleton
4. **MCP server + UI update tools** -- Depends on Claude Code integration
5. **3D preview panel** -- Depends on MCP preview_update tool
6. **MQTT bridge** -- Independent of Claude Code, can parallelize with 4-5
7. **Search results UI** -- Depends on MCP show_search_results tool
8. **Confirmation dialogs** -- Depends on MCP request_confirmation tool

## Scalability Considerations

| Concern | 1 User | 5 Users | 10+ Users |
|---------|--------|---------|-----------|
| Claude Code subprocesses | 1 process, ~50MB | 5 processes, ~250MB | Consider subprocess pooling or queuing |
| WebSocket connections | Trivial | Trivial | Use connection manager with heartbeat |
| MQTT connections | 1 persistent connection (shared) | 1 shared | 1 shared (MQTT is per-printer) |
| File storage | ~/3d-prints/ | Same | Same (local machine) |
| Token cost | Per-conversation | 5x cost | Budget limits via max_budget_usd |

**Note:** This is a personal/local tool. Multi-user scaling is out of scope for v2.0 but the architecture supports it naturally since each WebSocket gets its own Claude Code session.

## Key Technical Risks

1. **claude-agent-sdk stability** -- The SDK's Transport class is marked as "low-level internal API" that may change. Pin the SDK version. (MEDIUM risk)

2. **MQTT token expiry** -- BambuLab JWT tokens expire after ~24h. The MQTT bridge needs auto-reconnection with token refresh. (MEDIUM risk, existing problem from v1.0)

3. **Claude Code subprocess resource usage** -- Each subprocess loads the full Claude Code runtime. With `include_partial_messages=True`, it streams continuously. Monitor memory. (LOW risk for single user)

4. **3MF file serving for Three.js** -- Three.js needs to load 3MF files via HTTP. The `three/examples/jsm/loaders/3MFLoader` exists but may have limitations. STL fallback is simpler. (LOW risk)

## Sources

- [Claude Agent SDK - Python Reference](https://platform.claude.com/docs/en/agent-sdk/python) -- ClaudeSDKClient, query(), create_sdk_mcp_server(), @tool decorator, ClaudeAgentOptions (HIGH confidence)
- [Claude Agent SDK - Streaming Output](https://platform.claude.com/docs/en/agent-sdk/streaming-output) -- StreamEvent, include_partial_messages, text_delta streaming (HIGH confidence)
- [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference) -- CLI flags, --output-format, --mcp-config (HIGH confidence)
- [Claude Code MCP Docs](https://code.claude.com/docs/en/mcp) -- MCP server configuration, transport types, scopes (HIGH confidence)
- [FastAPI WebSocket Docs](https://fastapi.tiangolo.com/advanced/websockets/) -- WebSocket endpoint patterns (HIGH confidence)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) -- FastMCP, stdio transport, @mcp.tool() (HIGH confidence)
- [bambu-lab-cloud-api](https://pypi.org/project/bambu-lab-cloud-api/) -- MQTTClient, BambuClient (MEDIUM confidence -- unofficial library)
- [fastapi-mqtt](https://github.com/sabuhish/fastapi-mqtt) -- MQTT + FastAPI integration patterns (MEDIUM confidence)
- [Inside the Claude Agent SDK](https://buildwithaws.substack.com/p/inside-the-claude-agent-sdk-from) -- Subprocess architecture details (MEDIUM confidence)
