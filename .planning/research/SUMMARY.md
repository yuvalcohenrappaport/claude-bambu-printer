# Project Research Summary

**Project:** Claude BambuLab Printer Interface -- v2.0 Web Dashboard
**Domain:** Web dashboard for AI-powered 3D printing (CLI-to-web migration)
**Researched:** 2026-03-08
**Confidence:** HIGH

## Executive Summary

The v2.0 web dashboard layers a React + Three.js frontend and FastAPI backend on top of the proven v1.0 CLI skill. The core integration is the Claude Agent SDK (`claude-agent-sdk`), which manages Claude Code as a persistent subprocess with session continuity, streaming responses, and in-process MCP tools that push UI updates (3D preview, search results, status messages) to the browser via WebSocket. A separate MQTT bridge relays real-time printer status from BambuLab's cloud. The existing v1.0 scripts (printer_control.py, makerworld_search.py, OpenSCAD generation) remain completely unchanged -- Claude Code wraps them as it does today, just with a web frontend instead of a terminal.

The recommended approach is a strict dependency-driven build order: start with the FastAPI + WebSocket + subprocess foundation (solving session isolation, process lifecycle, and disconnect handling up front), then add the chat UI and Claude Code integration, then 3D preview via MCP push, then MQTT monitoring. The research is clear that the foundation phase is load-bearing -- every critical pitfall (zombie processes, pipe deadlocks, global state bleed, silent WebSocket drops) lives in this layer. Getting it wrong means rebuilding everything on top.

The primary risks are Claude Code subprocess memory leaks (documented up to 120GB in long sessions) and the MQTT bridge's thread-to-asyncio synchronization. Both are manageable with proper lifecycle management and the patterns documented in the architecture research. A secondary risk is BambuStudio CLI headless slicing reliability (LOW confidence) -- OrcaSlicer CLI is the recommended fallback.

## Key Findings

### Recommended Stack

The stack splits cleanly: Python backend (FastAPI + claude-agent-sdk + aiomqtt) and TypeScript frontend (React 19 + Vite 6 + Three.js/R3F). No database needed -- chat is session-scoped, printer status is real-time, models are files. The claude-agent-sdk is the most critical new dependency, providing `ClaudeSDKClient` for persistent subprocess management and `create_sdk_mcp_server()` for in-process MCP tools.

**Core technologies:**
- **FastAPI + uvicorn**: HTTP + WebSocket server -- async-first, native WebSocket, Pydantic integration
- **claude-agent-sdk 0.1.48**: Claude Code subprocess lifecycle, streaming, in-process MCP server -- replaces raw subprocess management
- **aiomqtt 2.5.1**: Async MQTT client for BambuLab printer status -- wraps paho-mqtt for asyncio compatibility
- **React 19 + Vite 6**: Frontend SPA -- fast HMR, TypeScript, familiar to the developer
- **Three.js 0.183 + @react-three/fiber 9**: 3D model viewing -- built-in STLLoader and ThreeMFLoader, declarative React components
- **zustand 5**: Client state management -- selector-based updates prevent re-renders from frequent WebSocket messages

### Expected Features

**Must have (table stakes):**
- Chat input with streaming response (core interaction model)
- 3D model viewer with auto-updating preview (visual proof of generation)
- Print job controls (start/pause/cancel) -- regression if missing
- Printer connection status and print progress bar
- MakerWorld search results as visual card grid
- Session-scoped chat history

**Should have (differentiators):**
- Live temperature gauges via MQTT
- Contextual action buttons in chat messages (Print, Scale, Modify)
- MakerWorld split-view with 3D preview of selected model
- AMS/filament status display
- Print settings recommendation with visual feedback

**Defer (v3+):**
- Print queue (high complexity, unclear demand)
- Multi-printer management
- Persistent chat history across sessions
- Webcam/camera feed

### Architecture Approach

Six components with clear boundaries: React Frontend, FastAPI Server (WebSocket hub), ClaudeManager (subprocess lifecycle), in-process MCP Server (UI update tools), MQTTBridge (printer status relay), and the unchanged v1.0 scripts. Two separate WebSocket endpoints -- `/ws` for chat/UI updates and `/ws/printer` for high-frequency MQTT status -- prevent backpressure issues. The MCP tools use closures to access WebSocket connections directly, avoiding cross-process communication.

**Major components:**
1. **FastAPI Backend** -- Central hub: WebSocket management, session lifecycle, file serving
2. **ClaudeManager** -- One ClaudeSDKClient per browser session with streaming and interrupt support
3. **MCP Server (in-process)** -- Tools Claude Code calls to push preview updates, search results, status messages, and confirmation dialogs to the browser
4. **MQTTBridge** -- Persistent MQTT connection in daemon thread, bridged to asyncio via `run_coroutine_threadsafe()`
5. **React Frontend** -- Chat panel, Three.js 3D preview, printer status, search results
6. **v1.0 Scripts** -- Unchanged CLI tools that Claude Code wraps via Bash

### Critical Pitfalls

1. **Zombie Claude Code subprocesses** -- Orphaned processes consume ~45MB each and can grow to 120GB+. Use `async with` context manager, implement a process reaper, set 30-minute session timeouts, track PIDs in a registry.
2. **Stdin/stdout pipe deadlock** -- Large messages in both directions fill OS pipe buffers (16KB on macOS). Use the claude-agent-sdk (handles this internally), never roll custom pipe management. Add 30-second per-message timeouts.
3. **Global state bleed between sessions** -- v1.0 scripts write to fixed paths. Create per-session workspace directories (`/tmp/bambu-dashboard/{session_id}/`), set each subprocess's `cwd` to its workspace.
4. **Silent WebSocket disconnects** -- Backend doesn't detect browser disconnects for minutes. Implement 15-second ping/pong heartbeat, run WebSocket read and subprocess read as concurrent asyncio tasks, clean up resources on disconnect.
5. **Three.js 3MF loader failures** -- Large or non-standard 3MF files crash the browser. Convert to binary STL on the backend for preview (keep 3MF for printing). Set 10MB file size limits for browser loading.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Backend Foundation + WebSocket Infrastructure

**Rationale:** All four critical pitfalls (#1-#4) live in this layer. The entire dashboard depends on reliable subprocess management and WebSocket communication. Nothing else can be built or tested without this.
**Delivers:** FastAPI server with WebSocket endpoint, session isolation (per-session workspaces), ClaudeManager with proper lifecycle (connect, disconnect, interrupt, cleanup), ConnectionManager with heartbeat ping/pong, health check endpoint.
**Addresses:** Printer connection status (table stakes), session-scoped state management.
**Avoids:** Zombie processes (pitfall #1), pipe deadlock (pitfall #2), state bleed (pitfall #3), silent disconnects (pitfall #4).

### Phase 2: Chat Interface + Claude Code Streaming

**Rationale:** Once the subprocess foundation is stable, add the primary user interaction. Chat is the entry point for everything -- model generation, search, printing. Streaming text is a table-stakes expectation.
**Delivers:** React chat panel with streaming response display, message routing between browser and Claude Code, interrupt support (cancel button), basic layout skeleton.
**Addresses:** Chat input with streaming response (table stakes), chat history in session (table stakes).
**Uses:** ClaudeSDKClient with `include_partial_messages=True`, zustand for message state.

### Phase 3: MCP Server + 3D Preview

**Rationale:** The "wow moment" -- user types a prompt, a 3D model appears in the browser. Depends on Phase 2 (Claude Code must be working) and the MCP tool mechanism for push updates. This is the core differentiator.
**Delivers:** In-process MCP server with `update_preview`, `update_status`, `show_search_results`, `request_confirmation` tools. Three.js viewer with STL loading, auto-update on MCP events, orbit controls, Z-up to Y-up correction, cache-busting URLs.
**Addresses:** 3D model viewer (table stakes), auto-updating preview (table stakes), inline model modification (differentiator).
**Avoids:** 3MF loader failures (pitfall #5) by using STL for preview. Event loop blocking (pitfall #7) by keeping MCP handlers thin.

### Phase 4: Print Controls + Confirmation Flow

**Rationale:** With chat and preview working, add the ability to actually send prints. Needs the `request_confirmation` MCP tool from Phase 3 for the "Send to printer?" dialog.
**Delivers:** Print start/pause/cancel buttons, confirmation dialog component, print status display, basic error handling for print failures.
**Addresses:** Print job controls (table stakes), model download + print flow (table stakes).

### Phase 5: MQTT Printer Monitoring

**Rationale:** Independent of the Claude Code chain -- can be built in parallel with Phase 3/4 if resources allow. Adds real-time monitoring that makes the dashboard feel like a complete tool.
**Delivers:** MQTTBridge with daemon thread, printer status WebSocket endpoint (`/ws/printer`), live progress bar, temperature gauges, layer count, AMS/filament status.
**Addresses:** Print progress bar (table stakes), live temperature gauges (differentiator), AMS/filament status (differentiator).
**Avoids:** MQTT message drops/duplicates (pitfall #6) via unique client IDs, QoS 0, frontend dedup.

### Phase 6: MakerWorld Search UI

**Rationale:** Depends on the `show_search_results` MCP tool (Phase 3). Transforms text search results into a visual browsing experience.
**Delivers:** Card grid with thumbnails, model details. Contextual action buttons (Download, Preview, Print). Server-side search cache with rate limiting.
**Addresses:** MakerWorld search results display (table stakes), contextual actions in chat (differentiator).
**Avoids:** Increased Cloudflare blocking (pitfall #13) via caching and rate limiting.

### Phase 7: Polish + Split-View

**Rationale:** All core functionality is in place. This phase enhances the MakerWorld experience and adds visual polish.
**Delivers:** MakerWorld split-view (card grid + 3D preview of selected model), print settings visual editor, responsive layout refinements, toast notifications for print events.
**Addresses:** MakerWorld split-view (differentiator), print settings recommendation (differentiator), responsive layout (table stakes).

### Phase Ordering Rationale

- **Phases 1-3 are strictly sequential** -- each depends on the previous. No parallelization possible.
- **Phase 4 depends on Phase 3** (MCP confirmation tool) but is small.
- **Phase 5 is independent** of Phases 3-4 and can be parallelized if desired.
- **Phase 6 depends on Phase 3** (MCP search results tool) but not on Phase 5.
- **Phase 7 depends on Phase 6** (extends MakerWorld UI).
- The critical path is: Phase 1 -> 2 -> 3 -> 6 -> 7. Phases 4 and 5 branch off after Phase 3 and Phase 1 respectively.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** Claude Agent SDK subprocess lifecycle details -- verify `ClaudeSDKClient` cleanup behavior on unexpected disconnect. The SDK's Transport class is marked "low-level internal API."
- **Phase 3:** Three.js + OpenSCAD output compatibility -- verify ThreeMFLoader/STLLoader works with OpenSCAD-generated files. May need to test early.
- **Phase 5:** bambu-lab-cloud-api MQTT long-running connection stability -- the library's internal reconnection behavior is not fully documented.

Phases with standard patterns (skip research-phase):
- **Phase 2:** Streaming chat UI is well-documented (ChatGPT, AI SDK patterns). Standard WebSocket + React.
- **Phase 4:** Print controls are thin wrappers around existing Python functions. Straightforward.
- **Phase 6:** Card grid UI is standard React. Search caching is a solved problem.
- **Phase 7:** Split-view layout is standard CSS/React. No novel technical challenges.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies have official docs, verified versions, confirmed compatibility. claude-agent-sdk is the newest but has official Anthropic documentation. |
| Features | HIGH | Clear table-stakes vs. differentiator distinction. Competitive landscape well-mapped against OctoPrint, Fluidd, Mainsail, Bambu Studio. |
| Architecture | HIGH | Patterns are well-documented (FastAPI WebSocket, in-process MCP, streaming). Only MEDIUM confidence on MQTT bridge threading. |
| Pitfalls | HIGH | Critical pitfalls backed by specific GitHub issues with documented reproductions. Prevention strategies are concrete. |

**Overall confidence:** HIGH

### Gaps to Address

- **BambuStudio CLI headless slicing reliability (LOW confidence):** Flagged in v1.0 research. If automated slicing fails, the print-from-dashboard flow breaks. Validate early or commit to OrcaSlicer CLI as fallback. Not blocking any phase directly -- slicing is handled by existing v1.0 scripts.
- **claude-agent-sdk Transport API stability:** The SDK's internal Transport class may change between versions. Pin to 0.1.48 and avoid using internal APIs. Monitor for breaking changes.
- **OpenSCAD output file compatibility with Three.js loaders:** Need to test actual OpenSCAD-generated STL/3MF files in the Three.js viewer early in Phase 3. STL is the safer format for preview.
- **MQTT token expiry handling:** BambuLab JWT tokens expire after ~24h. The MQTT bridge needs auto-reconnection with token refresh. This is an existing v1.0 problem that becomes more visible in a persistent web dashboard.

## Sources

### Primary (HIGH confidence)
- [Claude Agent SDK Python Reference](https://platform.claude.com/docs/en/agent-sdk/python) -- ClaudeSDKClient, MCP server creation, tool decorator
- [claude-agent-sdk PyPI v0.1.48](https://pypi.org/project/claude-agent-sdk/) -- latest version, March 2026
- [FastAPI WebSocket docs](https://fastapi.tiangolo.com/advanced/websockets/) -- native WebSocket patterns
- [Three.js STLLoader/ThreeMFLoader](https://threejs.org/docs/) -- built-in 3D format support
- [React Three Fiber v9 docs](https://r3f.docs.pmnd.rs/) -- useLoader pattern, declarative Three.js
- [Claude Code memory leak issues](https://github.com/anthropics/claude-code/issues/4953) -- subprocess lifecycle risks

### Secondary (MEDIUM confidence)
- [aiomqtt v2.5.1](https://pypi.org/project/aiomqtt/) -- async MQTT client
- [bambu-lab-cloud-api](https://pypi.org/project/bambu-lab-cloud-api/) -- unofficial BambuLab library
- [OpenBambuAPI MQTT protocol](https://github.com/Doridian/OpenBambuAPI/blob/main/mqtt.md) -- MQTT topic structure
- [Inside the Claude Agent SDK](https://buildwithaws.substack.com/p/inside-the-claude-agent-sdk-from) -- subprocess architecture details

### Tertiary (LOW confidence)
- BambuStudio CLI headless slicing -- needs validation, no official documentation
- Three.js 3MFLoader compatibility with OpenSCAD output -- needs testing

---
*Research completed: 2026-03-08*
*Ready for roadmap: yes*
