# Requirements: Claude BambuLab Printer Interface

**Defined:** 2026-03-08
**Core Value:** Any 3D printer owner can go from "I want to print X" to a physical print through natural language -- no CAD skills required.

## v2.0 Requirements

Requirements for web dashboard release. Each maps to roadmap phases.

### Chat & AI Interface

- [ ] **CHAT-01**: User can type messages in a web chat interface and receive streaming AI responses
- [ ] **CHAT-02**: User can scroll back through conversation history within the current session
- [ ] **CHAT-03**: User can click contextual action buttons in AI messages (Print, Scale, Modify) instead of typing commands

### 3D Viewer

- [ ] **VIEW-01**: User can view 3D models (STL/3MF) in the browser with orbit, zoom, and pan controls
- [ ] **VIEW-02**: User sees the 3D preview auto-update when Claude generates or modifies a model
- [ ] **VIEW-03**: User can preview a selected MakerWorld search result in 3D (split-view)

### Printer Monitoring

- [ ] **MNTR-01**: User can start, pause, resume, and cancel prints from the dashboard
- [ ] **MNTR-02**: User can see live print progress (percentage + ETA) during a print
- [ ] **MNTR-03**: User can see real-time nozzle and bed temperatures via MQTT streaming
- [ ] **MNTR-04**: User can see current layer / total layers during a print
- [ ] **MNTR-05**: User can see AMS filament status (loaded filament, remaining amount)

### MakerWorld Search

- [ ] **SRCH-01**: User can browse MakerWorld search results as a visual card grid with thumbnails
- [ ] **SRCH-02**: User can select a search result and see its 3D preview alongside the grid (split-view)
- [ ] **SRCH-03**: User can download a search result and send it to print in one flow

### Infrastructure

- [ ] **INFR-01**: FastAPI backend manages Claude Code subprocess via claude-agent-sdk with WebSocket communication
- [ ] **INFR-02**: MCP server lets Claude Code push UI updates (model preview, status, search results) to the browser
- [ ] **INFR-03**: MQTT bridge relays printer status to browser via WebSocket for live monitoring
- [ ] **INFR-04**: User can view and adjust key print settings (infill, layer height, speed) in a visual editor before printing

## Future Requirements

### v3.0 Candidates

- **QUEUE-01**: User can queue multiple models for sequential printing
- **MULTI-01**: User can manage multiple printers from one dashboard
- **HIST-01**: User can access chat history across sessions

## Out of Scope

| Feature | Reason |
|---------|--------|
| In-browser CAD editing | Enormous scope; editing via chat is the differentiator |
| Mobile-optimized UI | Desktop-first; responsive but not mobile-optimized |
| Webcam/camera feed | Requires hardware setup; use Bambu Handy instead |
| G-code visualization | We generate 3MF, not G-code; BambuStudio handles slicing |
| User accounts / auth | Single user, local tool; auth is premature |
| Model marketplace | Legal complexity; we search MakerWorld, not host |
| Persistent chat history | Adds database requirement; session-only for now |
| Direct Claude API | Using Claude Code subprocess; simpler, leverages existing skills |
| Full slicing UI | BambuStudio handles slicing; expose only key settings |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CHAT-01 | Phase 6 | Pending |
| CHAT-02 | Phase 6 | Pending |
| CHAT-03 | Phase 11 | Pending |
| VIEW-01 | Phase 7 | Pending |
| VIEW-02 | Phase 7 | Pending |
| VIEW-03 | Phase 11 | Pending |
| MNTR-01 | Phase 8 | Pending |
| MNTR-02 | Phase 9 | Pending |
| MNTR-03 | Phase 9 | Pending |
| MNTR-04 | Phase 9 | Pending |
| MNTR-05 | Phase 9 | Pending |
| SRCH-01 | Phase 10 | Pending |
| SRCH-02 | Phase 10 | Pending |
| SRCH-03 | Phase 10 | Pending |
| INFR-01 | Phase 5 | Pending |
| INFR-02 | Phase 7 | Pending |
| INFR-03 | Phase 9 | Pending |
| INFR-04 | Phase 8 | Pending |

**Coverage:**
- v2.0 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0

---
*Requirements defined: 2026-03-08*
*Last updated: 2026-03-08 after roadmap creation*
