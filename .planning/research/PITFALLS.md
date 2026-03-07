# Domain Pitfalls: Web Dashboard for CLI 3D Printing Tool

**Domain:** Adding web dashboard to existing Claude Code CLI skill
**Researched:** 2026-03-08
**Focus:** CLI-to-web migration, subprocess management, real-time communication

---

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Claude Code Subprocess Zombie Processes and Memory Leaks

**What goes wrong:** Claude Code subprocess is spawned per user session but never properly terminated. Orphaned processes accumulate, each consuming ~45 MB RSS. On macOS, after hours of operation the backend exhausts memory and crashes.

**Why it happens:** Claude Code has documented memory leak issues (processes growing to 120+ GB in long sessions). When the parent FastAPI process crashes, gets SIGKILL'd, or a WebSocket disconnects unexpectedly, the Claude Code child process's PPID becomes 1 (adopted by init) and continues running indefinitely. The claude-code-sdk uses `anyio.open_process()` which doesn't guarantee cleanup on all exit paths.

**Consequences:** Server becomes unresponsive. Other users' sessions degrade. Requires manual process cleanup or server restart.

**Prevention:**
- Use `async with` context manager for Claude Code SDK sessions -- never spawn without cleanup guarantee.
- Implement a process reaper: on each new session start, check for orphaned `claude` processes owned by the server user and kill them.
- Set a maximum session lifetime (e.g., 30 minutes). Force-terminate and restart the subprocess on timeout.
- Track subprocess PIDs in a registry. On WebSocket disconnect, explicitly `SIGTERM` then `SIGKILL` after 5s grace.
- Add a health check endpoint that reports active subprocess count and total memory usage.
- Consider the claude-code-sdk's in-process MCP server mode (no subprocess for tools) to reduce process count.

**Detection:** Monitor process count: `pgrep -f "claude"`. Alert if count exceeds expected sessions. Track RSS per process.

**Confidence:** HIGH -- multiple documented GitHub issues (#4953, #19045, #18859, #11377, #11315).

### Pitfall 2: Stdin/Stdout Pipe Deadlock with Claude Code Subprocess

**What goes wrong:** The FastAPI backend writes a large message to Claude Code's stdin while Claude Code simultaneously writes a large response to stdout. Both OS pipe buffers fill (typically 64KB on Linux, 16KB on macOS). Both processes block waiting for the other to read. Complete deadlock -- the session hangs forever.

**Why it happens:** Python's subprocess documentation explicitly warns about this. The Claude Code SDK uses a JSON-lines protocol over stdio. If a user sends a long message (e.g., pasting a model description) while Claude is mid-response, the write to stdin blocks because nobody is reading stdout, and stdout blocks because nobody is reading stdin.

**Consequences:** Session hangs permanently. User sees spinner forever. Only fix is killing the subprocess.

**Prevention:**
- Use `asyncio.create_subprocess_exec` with separate reader/writer coroutines -- never do synchronous read/write on pipes.
- The claude-code-sdk handles this internally with `_write_lock` and a JSON reassembly state machine. Use the SDK, do NOT roll your own subprocess pipe management.
- Set `max_buffer_size` on the SDK transport to prevent unbounded buffering.
- Add a per-message timeout (30s). If no response within timeout, assume deadlock and restart subprocess.
- Use `process.communicate()` pattern rather than manual `stdin.write()` / `stdout.read()` when possible.

**Detection:** Session-level watchdog timer. If no stdout data for 30 seconds after a stdin write, flag as potential deadlock.

**Confidence:** HIGH -- well-documented Python subprocess issue, confirmed by Python 3.14 docs.

### Pitfall 3: Global State Bleeds Between Users

**What goes wrong:** The v1.0 CLI scripts use global state -- files written to fixed paths (`model.scad`, `output.3mf`), environment variables, working directory assumptions. When two users run simultaneously, User A's model overwrites User B's. Print commands send the wrong file.

**Why it happens:** CLI tools assume single-user, single-session operation. The existing scripts write to hardcoded relative paths. There's no session isolation.

**Consequences:** Users receive wrong models. Print jobs send incorrect files. Data loss. Possible security issue if models contain identifying info.

**Prevention:**
- Create a unique workspace directory per session: `/tmp/bambu-dashboard/{session_id}/`. All file operations happen inside this directory.
- Pass workspace path as parameter to every script invocation. Never use relative paths.
- Each Claude Code subprocess should have its own `cwd` set to the session workspace.
- On session cleanup, archive or delete the workspace directory.
- Never store state in Python module-level globals. Use session-scoped state objects.
- The MCP server tools should accept `session_id` as a required parameter.

**Detection:** Integration test: run two sessions in parallel with different models, verify no cross-contamination.

**Confidence:** HIGH -- fundamental CLI-to-web architectural issue.

### Pitfall 4: WebSocket Drops Silently, Backend Doesn't Know

**What goes wrong:** The browser WebSocket disconnects (network change, laptop sleep, browser tab closed) but the FastAPI backend doesn't detect it for minutes. The Claude Code subprocess keeps running, consuming resources. When the user reconnects, they get a fresh session and lose all context.

**Why it happens:** TCP keepalive defaults are too slow (often 2+ hours). WebSocket has no built-in heartbeat unless you implement one. FastAPI raises `WebSocketDisconnect` only when you try to send/receive -- if the backend is waiting on Claude Code subprocess output, it never attempts a WebSocket operation and never discovers the disconnect.

**Consequences:** Resource leak (orphaned Claude sessions). Lost user context on reconnect. Users must restart their workflow.

**Prevention:**
- Implement application-level ping/pong: server sends ping every 15s, client must respond within 5s or connection is considered dead.
- Run WebSocket read and subprocess read as concurrent `asyncio.Task`s. When WebSocket read raises `WebSocketDisconnect`, cancel the subprocess task.
- Use a `ConnectionManager` class that tracks active connections and cleans up associated resources on disconnect.
- On reconnect, allow session resumption: store last N messages in Redis/memory keyed by session token. Client sends session token on reconnect to resume.
- Cancel any `asyncio.Task` background work tied to the WebSocket when disconnecting -- orphaned tasks are a common FastAPI pitfall.

**Detection:** Log WebSocket connect/disconnect events with timestamps. Alert if disconnect count >> connect count (indicating silent drops).

**Confidence:** HIGH -- documented FastAPI issue (GitHub discussion #9031).

---

## Moderate Pitfalls

### Pitfall 5: Three.js 3MF Loader Fails on Large or Non-Standard Files

**What goes wrong:** The Three.js `3MFLoader` chokes on large 3MF files (50MB+) or files generated by certain tools. Browser tab crashes with out-of-memory, or the loader throws XML parsing errors ("extra content at end of document"). OpenSCAD-generated 3MF files may use features the loader doesn't support.

**Why it happens:** 3MF is a ZIP archive containing XML. The Three.js loader parses the entire XML into memory. Large files (200MB+) exceed browser memory limits. Some 3MF generators produce non-standard XML that the parser rejects. The Three.js 3MFLoader has known compatibility issues with files from certain software.

**Prevention:**
- Convert to binary STL on the backend before sending to browser for preview. STL is simpler and loads 4-6x faster than 3MF in Three.js.
- Keep the 3MF for printing, use STL for preview: `trimesh.load("model.3mf").export("preview.stl")`.
- Set a file size limit for browser loading (10MB max for 3MF, 30MB for binary STL).
- For very large models, decimate on the backend first: `mesh.simplify_quadric_decimation(target_faces=50000)`.
- Use `STLLoader` (more mature, fewer edge cases) instead of `3MFLoader` for the preview component.
- Load models via `URL.createObjectURL(blob)` from a fetch response, not by pointing the loader at a static file URL -- this gives you control over loading progress and error handling.

**Detection:** Wrap Three.js loader in try/catch. Monitor browser memory via `performance.memory` API. Test with real-world OpenSCAD output files.

**Confidence:** MEDIUM -- Three.js GitHub issues #13540, forum thread on 3MF loading. Specific compatibility with OpenSCAD output needs validation.

### Pitfall 6: MQTT-to-WebSocket Bridge Drops Messages or Duplicates

**What goes wrong:** BambuLab printer publishes MQTT status updates at ~1Hz. The bridge relays these to the browser via WebSocket. Under load or network issues: messages queue up and arrive in bursts, messages are duplicated after reconnection, or the MQTT client disconnects silently and stops receiving updates.

**Why it happens:** paho-mqtt's `on_disconnect` callback fires asynchronously. If the MQTT broker connection drops (printer goes to sleep, network blip), the client doesn't auto-reconnect by default in v2.x. Duplicate messages occur because MQTT QoS 1 guarantees at-least-once delivery. The bridge may relay stale messages after reconnection if it replays the retained message.

**Prevention:**
- Use paho-mqtt with `reconnect_on_failure=True` (v2.x) or implement manual reconnection with exponential backoff.
- Deduplicate on the frontend: each MQTT message has a timestamp. Ignore messages with timestamps older than the latest received.
- Use QoS 0 for status updates (acceptable to lose one update since the next arrives in 1 second). Reserve QoS 1 for commands (start/stop print).
- Don't relay raw MQTT messages to the browser. Parse on backend, extract only changed fields, send delta updates to reduce bandwidth.
- Give each MQTT client a unique `client_id` per session: `f"dashboard-{session_id}"`. Duplicate client IDs cause forced disconnection.
- Handle retained messages: on subscription, the broker sends the last retained message. Flag this as "initial state" not "new update".

**Detection:** Frontend displays "last update: X seconds ago". If >5s stale, show warning. Log MQTT disconnect/reconnect events on backend.

**Confidence:** MEDIUM -- standard MQTT patterns, BambuLab-specific MQTT topics confirmed via OpenBambuAPI docs.

### Pitfall 7: MCP Server Tool Calls Block the Event Loop

**What goes wrong:** Claude Code calls an MCP tool (e.g., `update_preview`, `show_search_results`) that needs to push data to the browser via WebSocket. The MCP tool handler does synchronous work (file I/O, mesh processing) inside the async event loop, blocking all other WebSocket connections and MQTT relay.

**Why it happens:** MCP tool handlers in the claude-code-sdk run in the same event loop as FastAPI. If a tool handler calls `trimesh.load()` (CPU-bound, can take seconds for large meshes) synchronously, the entire server freezes.

**Consequences:** All connected clients experience lag. MQTT updates stop flowing. WebSocket pings time out, triggering false disconnects.

**Prevention:**
- Run CPU-bound work in `asyncio.get_event_loop().run_in_executor(None, sync_function)` -- this offloads to a thread pool.
- For heavy mesh operations, use `ProcessPoolExecutor` instead of the default `ThreadPoolExecutor` (Python GIL makes threads useless for CPU-bound work).
- Keep MCP tool handlers thin: accept the request, queue the work, return immediately. Push results to the browser asynchronously when done.
- Profile tool handler execution time. Any handler taking >100ms should be offloaded.
- Consider using the SDK's in-process tool mode to avoid subprocess overhead for simple UI-push tools.

**Detection:** Add timing middleware to MCP tool handlers. Log any handler taking >500ms. Monitor event loop lag.

**Confidence:** MEDIUM -- standard asyncio pitfall, specific to this architecture's MCP + FastAPI combination.

### Pitfall 8: File Watcher Fires Duplicates or Misses Changes

**What goes wrong:** The file watcher monitoring the workspace for model changes (to auto-update the 3D preview) fires multiple events for a single file save, misses changes entirely, or triggers on temporary files.

**Why it happens:** On macOS (FSEvents), a single file save can trigger CREATE + MODIFY + MODIFY events. Editors like VS Code and OpenSCAD write to a temp file then atomically rename, which the watcher sees as a deletion of the original file (losing the watch). OpenSCAD writes output progressively, triggering MODIFY events before the file is complete.

**Prevention:**
- Debounce file change events: wait 500ms after the last event before triggering a preview update.
- Watch the parent directory, not individual files. Filter events by filename.
- After detecting a change, verify the file is complete: check file size is stable (read size, wait 200ms, read again, compare).
- Use `watchfiles` (Python library, Rust-based, handles edge cases) instead of raw `watchdog`.
- Ignore temporary files: filter out `*.tmp`, `*.swp`, files starting with `.`.
- For OpenSCAD renders, don't use file watching at all. Instead, have the render script signal completion by writing a sentinel file or calling a callback.

**Detection:** Log every file event. If you see 3+ events within 100ms for the same file, your debounce is missing.

**Confidence:** MEDIUM -- standard file watching pitfall, macOS FSEvents behavior confirmed.

### Pitfall 9: BambuStudio CLI Headless Slicing Unreliable

**What goes wrong:** The automated slicing step (converting raw 3MF to sliced 3MF with G-code) using BambuStudio CLI fails intermittently. BambuStudio may not have a stable headless mode, require a display server, or crash on certain model geometries.

**Why it happens:** BambuStudio is primarily a GUI application. CLI/headless slicing support is unofficial and poorly documented. On macOS, it may attempt to initialize GUI frameworks even in "CLI" mode.

**Consequences:** The print-from-dashboard flow breaks at the slicing step. Users must manually open BambuStudio.

**Prevention:**
- Use OrcaSlicer CLI instead -- it has better headless support and is BambuStudio-compatible.
- Test headless slicing thoroughly before building the pipeline around it. This is the v1.0 research finding with LOW confidence.
- Have a fallback: if automated slicing fails, open BambuStudio with the file pre-loaded and let the user click "Slice".
- Consider pre-sliced profiles: store a set of common slicer profiles and use them with OrcaSlicer CLI.
- The cloud API path (bambu-lab-cloud-api) may handle slicing server-side -- investigate as alternative.

**Detection:** Wrap CLI call with timeout (120s). Check exit code and stderr for GUI-related errors.

**Confidence:** LOW -- flagged in v1.0 research. Needs validation before building the phase.

---

## Minor Pitfalls

### Pitfall 10: CORS and Cookie Issues Between Frontend and Backend

**What goes wrong:** React dev server runs on `localhost:5173`, FastAPI on `localhost:8000`. WebSocket connections fail with CORS errors. Session cookies don't propagate cross-origin.

**Prevention:**
- Configure FastAPI CORS middleware with `allow_origins=["http://localhost:5173"]` for dev.
- For WebSocket, CORS headers aren't enough -- the browser doesn't enforce CORS on WebSocket `ws://` connections, but the initial HTTP upgrade request does need proper headers.
- Use `credentials: "include"` on fetch requests and `withCredentials: true` on WebSocket if using cookies.
- In production, serve frontend and backend from the same origin via a reverse proxy (nginx/Caddy).

**Confidence:** HIGH -- standard web dev issue.

### Pitfall 11: Three.js Model Orientation and Scale Wrong

**What goes wrong:** Models appear tiny, huge, or rotated 90 degrees in the 3D preview. OpenSCAD uses Z-up convention, Three.js uses Y-up.

**Prevention:**
- Apply a standard rotation on load: `mesh.rotation.x = -Math.PI / 2` to convert Z-up to Y-up.
- Auto-fit camera to model bounding box: compute bounding sphere, set camera distance to `radius / Math.sin(fov/2)`.
- Set a consistent scale: models should be in millimeters. If bounding box > 1000mm in any axis, auto-scale to fit viewport.

**Confidence:** HIGH -- standard Three.js + CAD integration issue.

### Pitfall 12: Backend Serves Stale Model Files

**What goes wrong:** Browser caches the STL/3MF file URL. After Claude regenerates the model, the preview shows the old version because the browser serves from cache.

**Prevention:**
- Append a hash or timestamp to file URLs: `/api/preview/{session_id}/model.stl?v={file_hash}`.
- Set `Cache-Control: no-cache` headers on model file responses.
- Use unique filenames per generation: `model_v3.stl` instead of overwriting `model.stl`.

**Confidence:** HIGH -- standard caching issue.

### Pitfall 13: MakerWorld Cloudflare Blocks Increase Under Web Dashboard Load

**What goes wrong:** The CLI had one user making occasional searches. The web dashboard may have multiple users searching simultaneously, hitting MakerWorld more frequently and triggering more aggressive Cloudflare blocking.

**Prevention:**
- Implement a server-side search cache with 24h TTL. Same query = cached result, no outbound request.
- Rate-limit outbound MakerWorld requests to 1/second globally (not per-user).
- Queue search requests and process sequentially to avoid bursts.
- This was already flagged in v1.0 PITFALLS -- severity increases with multiple users.

**Confidence:** HIGH -- already observed in v1.0.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Severity | Mitigation |
|---|---|---|---|
| Claude Code subprocess setup | Zombie processes, memory leaks (#1) | CRITICAL | Process registry + reaper + session timeouts |
| Claude Code subprocess comms | Stdin/stdout deadlock (#2) | CRITICAL | Use claude-code-sdk, never roll own pipe management |
| FastAPI + WebSocket foundation | Silent disconnects (#4) | CRITICAL | Heartbeat ping/pong + ConnectionManager + session resume |
| Session isolation | Global state bleed (#3) | CRITICAL | Per-session workspace directories, no shared paths |
| MCP server integration | Event loop blocking (#7) | MODERATE | Offload CPU work to executor, thin tool handlers |
| Three.js model viewer | Large file crashes, orientation (#5, #11) | MODERATE | Convert to STL for preview, Z-up to Y-up rotation |
| MQTT printer status | Message drops/duplicates (#6) | MODERATE | Unique client IDs, QoS 0 for status, dedup on frontend |
| File watching for preview | Duplicate/missed events (#8) | MODERATE | Debounce + watchfiles library + completion signals |
| Automated slicing | BambuStudio CLI unreliable (#9) | MODERATE | Validate early, fallback to OrcaSlicer CLI or manual |
| Multi-user MakerWorld search | Increased Cloudflare blocking (#13) | MINOR | Server-side cache + global rate limiting |
| Frontend-backend integration | CORS, caching (#10, #12) | MINOR | Standard middleware config, cache-busting URLs |

---

## Key Ordering Insight for Roadmap

The first phase MUST solve pitfalls #1, #2, #3, and #4 together -- they are all foundational infrastructure. If any of these is wrong, everything built on top breaks. Specifically:

1. **Session isolation (#3) first** -- without per-session workspaces, nothing else is safe to test.
2. **Subprocess lifecycle (#1, #2) second** -- without reliable Claude Code process management, the backend is unstable.
3. **WebSocket reliability (#4) third** -- without disconnect detection, resource cleanup never triggers.

Do NOT start on Three.js viewer or MQTT bridge until the subprocess + WebSocket foundation is proven stable.

---

## Sources

- [Claude Code memory leak - 120GB RAM (GitHub #4953)](https://github.com/anthropics/claude-code/issues/4953)
- [Task tool subagent processes not terminated (GitHub #19045)](https://github.com/anthropics/claude-code/issues/19045)
- [Memory leak in long-running sessions (GitHub #18859)](https://github.com/anthropics/claude-code/issues/18859)
- [Memory leak 23GB RAM 143% CPU (GitHub #11377)](https://github.com/anthropics/claude-code/issues/11377)
- [Worker daemon zombie subprocesses (GitHub #1089)](https://github.com/thedotmack/claude-mem/issues/1089)
- [Python asyncio subprocess deadlock docs](https://docs.python.org/3/library/asyncio-subprocess.html)
- [Python subprocess pipe deadlock warning](https://docs.python.org/3/library/subprocess.html)
- [Three.js STL loader OOM with large files (GitHub #13540)](https://github.com/mrdoob/three.js/issues/13540)
- [Three.js 3MF loading issues (forum)](https://discourse.threejs.org/t/problem-loading-large-3mf-files-in-three-js/38463)
- [FastAPI WebSocket disconnect propagation (GitHub #9031)](https://github.com/fastapi/fastapi/discussions/9031)
- [FastAPI WebSocket disconnect handling patterns](https://hexshift.medium.com/handling-websocket-disconnections-gracefully-in-fastapi-9f0a1de365da)
- [OpenBambuAPI MQTT protocol](https://github.com/Doridian/OpenBambuAPI/blob/main/mqtt.md)
- [paho-mqtt duplicate client ID issue](https://www.emqx.com/en/blog/how-to-use-mqtt-in-python)
- [Claude Code SDK subprocess architecture](https://buildwithaws.substack.com/p/inside-the-claude-agent-sdk-from)
- [Claude Code SDK PyPI](https://pypi.org/project/claude-code-sdk/)
- [Claude Code MCP integration docs](https://code.claude.com/docs/en/mcp)
