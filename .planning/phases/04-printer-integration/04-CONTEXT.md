# Phase 4: Printer Integration - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Send 3MF files to a BambuLab printer and monitor print status from within Claude Code. Users can send any 3MF file (session-generated or from disk), check detailed printer status, and control running prints (pause/resume/cancel). Connection is via the BambuLab Cloud API.

</domain>

<decisions>
## Implementation Decisions

### Connection setup
- Authenticate via BambuLab Cloud API (not LAN/IP)
- Credentials stored in a config file (e.g., `~/.claude/bambu-config.json`)
- First-time guided setup flow: login -> select printer -> save config
- If multiple printers on account, always show list and let user pick (no default)

### Send-to-print flow
- Always show confirmation summary before sending (file, printer, settings)
- Can print any .3mf file from disk, not just session-generated models
- Two send options: "send to printer" (cloud print) or "open in BambuStudio" (local slicer)
- After successful send, automatically start polling for status updates

### Status monitoring
- Detailed status: state (idle/printing/error), progress %, ETA, temperatures, speed, current layer, filament used
- Auto-monitor after send: poll periodically for updates, show inline
- Full print control: pause, resume, stop/cancel from Claude Code
- On printer error: notify with error details and suggest next steps (resume, cancel, troubleshoot)

### Print settings
- Allow overrides at send time: show current 3MF settings, let user change before sending
- Query printer for available filaments and plate types, offer as selectable options
- Named presets (e.g., "draft", "quality", "strong") mapping to infill/speed/layer combos
- Presets are user-editable, stored in the config file

### Claude's Discretion
- Polling interval for status monitoring
- Exact confirmation summary format
- BambuStudio launch mechanism (CLI, open command, etc.)
- Preset defaults (what ships built-in)
- Error suggestion wording and troubleshooting steps

</decisions>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 04-printer-integration*
*Context gathered: 2026-03-06*
