# Feature Landscape: v2.0 Web Dashboard

**Domain:** Web-based 3D printing dashboard with AI chat, 3D preview, printer monitoring, and model search
**Researched:** 2026-03-08
**Scope:** NEW features only -- v1.0 CLI capabilities (generation, search, scaling, printing) already exist

## Table Stakes

Features users expect from a web-based 3D printing dashboard. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Depends On (v1.0) | Notes |
|---------|--------------|------------|-------------------|-------|
| Chat input with streaming response | Core interaction model -- user types, sees progressive AI response | Medium | Claude Code subprocess | Token-by-token streaming via WebSocket. Every AI-powered web app does this now (ChatGPT, v0, Claude). No streaming = feels broken. |
| 3D model viewer (STL/3MF) | Users must see what they're about to print before committing | Medium | OpenSCAD generation output | Three.js ThreeMFLoader + STLLoader exist. Orbit controls, zoom, pan are baseline. |
| Auto-updating preview | When Claude generates/modifies a model, viewer must refresh without manual reload | Medium | MCP server push | File watcher or MCP event push triggers re-render. Critical for "chat drives everything" UX. |
| Print job controls (start/pause/cancel) | Already exists in CLI -- removing it from web would be a regression | Low | printer_control.py | Button wrappers around existing Python functions. WebSocket relay. |
| Printer connection status | User needs to know if printer is reachable before sending jobs | Low | printer_setup.py | Simple connected/disconnected indicator. |
| Print progress bar | "How far along is my print?" is the #1 question during printing | Low | MQTT status stream | Percentage + ETA. OctoPrint, Fluidd, Mainsail, Bambu Studio all show this. |
| MakerWorld search results display | v1.0 returns text results -- web must show them visually | Medium | makerworld_search.py | Card grid with thumbnail, name, author, download count. |
| Model download + print flow | Click a search result, download it, send to printer | Low | Existing download pipeline | Button chain: Download -> Preview -> Print. |
| Chat history in session | Users scroll back to see what they asked and what was generated | Low | WebSocket message log | Standard chat UX. Persist in session, not across sessions (for now). |
| Responsive layout | Must work on laptop and desktop screens | Low | -- | Not mobile-first (out of scope per PROJECT.md), but don't break on common viewport sizes. |

## Differentiators

Features that set this apart from OctoPrint/Fluidd/Mainsail/Bambu Studio. Not expected, but valued.

| Feature | Value Proposition | Complexity | Depends On | Notes |
|---------|-------------------|------------|------------|-------|
| Chat-driven model generation | "Make me a phone stand" -> 3D model appears in viewer | Already built (v1.0) | MCP push to update viewer | The differentiator is seeing it appear live in the browser, not the generation itself. |
| Live temperature gauges | Real-time nozzle + bed temp via MQTT | Medium | MQTT WebSocket bridge | Fluidd/Mainsail have this. For us it's a differentiator because we combine it with chat-driven workflow. Spline chart or gauge widget. |
| Layer progress visualization | Current layer / total layers with visual indicator | Low | MQTT layer data | Bambu Studio shows this. Useful for estimating quality issues. |
| MakerWorld split-view (card grid + 3D preview) | Browse models visually, preview selected model in 3D before downloading | High | makerworld_search.py + ThreeMFLoader | This is the "MakerWorld but better" experience. Left panel = card grid, right panel = 3D preview of selected model. Requires downloading model to show preview. |
| Inline model modification | "Add a hole" or "Make walls thicker" and see changes live | Already built (v1.0) | MCP push + auto-preview | Chat message -> Claude modifies .scad -> re-renders -> pushes new 3MF -> viewer updates. The web makes this magical vs CLI. |
| Print settings recommendation with visual feedback | Claude suggests settings, user sees them applied to the model metadata | Low | Existing settings logic | Show infill %, layer height, etc. as editable chips before printing. |
| Contextual actions in chat | AI messages include clickable action buttons (Print, Scale, Modify) | Medium | Custom message rendering | Goes beyond text bubbles. Claude's response includes structured actions the user can click. Like tool invocation results in assistant-ui. |
| AMS/filament status | Show which filament is loaded, remaining amount | Low | MQTT AMS data | BambuLab AMS data is available via MQTT. Nice visual touch. |
| Print queue | Queue multiple models for sequential printing | High | New backend logic | Not in v1.0. Would need job queue management. Defer unless demand is clear. |

## Anti-Features

Features to explicitly NOT build for v2.0.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| In-browser model editing (CAD) | Enormous scope. OpenSCAD Desktop, Fusion360 exist. | Show preview only. Editing happens through chat ("make it wider") which triggers Claude Code. |
| Multi-printer management | Adds complexity, not core to the single-user workflow | Support one printer connection. Multi-printer is a v3+ concern. |
| User accounts / auth system | Single user, local tool. Adding auth is premature. | Store printer credentials in local config. Session-based chat. |
| Mobile-optimized UI | Explicitly out of scope per PROJECT.md. Desktop-first. | Use responsive CSS that doesn't break on tablets, but don't optimize for phones. |
| Webcam/camera feed | Requires additional hardware setup, streaming infrastructure | Link to Bambu Handy or BambuCAM for camera. Focus on data-driven monitoring. |
| G-code visualization | We generate 3MF, not G-code. BambuStudio handles slicing. | Show 3D model preview, not toolpath. |
| Model marketplace / sharing | Legal complexity, hosting costs, not core value | Link to MakerWorld. We search, not host. |
| Persistent chat history across sessions | Adds database requirement, storage management | Session-only chat. If users want history, that's a later feature. |
| Direct Claude API integration | PROJECT.md specifies Claude Code subprocess architecture | Stick with Claude Code subprocess via WebSocket relay. Simpler, leverages existing skills. |
| Slicing configuration UI | BambuStudio handles slicing. Replicating its UI is massive. | Expose only the key settings Claude recommends (infill, layer height, speed). |

## Feature Dependencies

```
                        WebSocket Server (FastAPI)
                               |
                    +----------+-----------+
                    |                      |
              Claude Code             MQTT Bridge
              Subprocess                   |
                    |              +-------+-------+
              MCP Server           |       |       |
                    |           Temps   Progress  AMS
           +-------+-------+
           |       |       |
        Generate  Search  Print
        Preview   Results  Control
           |       |       |
           +---+---+       |
               |           |
         Three.js Viewer   |
               |           |
               +-----------+
                     |
              Web Dashboard UI
```

**Critical path:** WebSocket Server -> Claude Code Subprocess -> MCP Server -> Three.js Viewer

The entire value of the web dashboard flows through this chain. If any link is broken, the dashboard is just a static page.

**Parallel work streams:**
- MQTT bridge for printer monitoring (independent of Claude Code chain)
- MakerWorld search UI (depends on existing search script, not on MCP)
- Chat UI (depends on WebSocket, not on 3D viewer)

## MVP Recommendation

**Phase 1 -- Chat + Preview (the "wow" moment):**
1. Chat interface with streaming response (table stakes, core UX)
2. Three.js 3D model viewer with auto-update (table stakes, visual proof)
3. MCP server for Claude Code -> UI push (enables auto-update)
4. Basic print controls (start, status) (table stakes, minimum viable printer integration)

**Phase 2 -- Monitoring + Search:**
5. Live MQTT printer status (temps, progress, layer count)
6. MakerWorld search with card grid display
7. Contextual action buttons in chat messages

**Phase 3 -- Polish + Split-View:**
8. MakerWorld split-view (card grid + 3D preview)
9. Print settings visual editor
10. AMS/filament status display

**Defer to v3+:**
- Print queue (High complexity, unclear demand)
- Multi-printer support
- Persistent chat history

**Rationale:** Phase 1 delivers the core "chat and see it appear" experience that no other 3D printing tool offers. Phase 2 makes it a complete monitoring dashboard. Phase 3 polishes the MakerWorld search into something better than the website itself.

## Competitive Landscape

| Feature | OctoPrint | Fluidd | Mainsail | Bambu Studio | This Dashboard |
|---------|-----------|--------|----------|-------------|---------------|
| Chat-driven model gen | No | No | No | No | YES -- core differentiator |
| 3D model preview | Plugin | No | No | Yes | Yes |
| Print monitoring | Yes | Yes | Yes | Yes | Yes (MQTT) |
| Temperature charts | Yes | Yes | Yes | Yes | Yes |
| MakerWorld search | No | No | No | Integrated | Yes + 3D preview |
| Model generation | No | No | No | No | Yes (OpenSCAD) |
| AI assistance | Plugin | No | No | No | Yes (Claude Code) |
| Camera feed | Yes | Yes | Yes | Yes | No (anti-feature) |
| Multi-printer | Plugin | Yes | Yes | Yes | No (deferred) |

The positioning is clear: this is NOT a printer management tool (OctoPrint/Fluidd territory). This is an AI-powered creation-to-print tool that happens to include monitoring. The chat + generation + preview loop is the unique value.

## Sources

- [OctoPrint Dashboard plugin](https://plugins.octoprint.org/plugins/dashboard/) -- baseline printer monitoring features
- [Fluidd vs Mainsail comparison](https://www.obico.io/blog/mainsail-vs-fluidd-vs-octoprint/) -- Klipper web interface feature sets
- [Three.js ThreeMFLoader](https://threejs.org/docs/pages/ThreeMFLoader.html) -- confirmed 3MF loading in browser
- [Three.js STLLoader](https://threejs.org/docs/pages/STLLoader.html) -- STL loading capability
- [React Three Fiber model loading](https://r3f.docs.pmnd.rs/tutorials/loading-models) -- R3F approach to 3D models
- [jschobben/modelview](https://github.com/jschobben/modelview) -- reference 3MF viewer implementation
- [BambuBoard](https://github.com/t0nyz0/BambuBoard) -- community BambuLab web dashboard
- [Bambu-Farm](https://github.com/TFyre/bambu-farm) -- multi-printer BambuLab web interface
- [Bambu Studio Remote Control](https://wiki.bambulab.com/en/software/bambu-studio/remote-control) -- official monitoring features
- [AI UI Design Patterns (Smashing Magazine)](https://www.smashingmagazine.com/2025/07/design-patterns-ai-interfaces/) -- chat + artifact split-panel patterns
- [assistant-ui](https://www.assistant-ui.com/) -- React library for AI chat with tool invocation rendering
- [Shape of AI](https://www.shapeof.ai/) -- UX patterns for AI interfaces
- [AI SDK Chatbot docs](https://ai-sdk.dev/docs/ai-sdk-ui/chatbot) -- streaming chat implementation patterns
- [MakerWorld](https://makerworld.com/en) -- model search/browse UI reference
