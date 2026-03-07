---
phase: 04-printer-integration
plan: 01
subsystem: printer
tags: [bambulab, cloud-api, mqtt, 3mf, slicing, bambu-studio]

requires:
  - phase: 03-makerworld-search-download
    provides: "Downloaded 3MF files that can be sent to printer"
provides:
  - "printer_setup.py: guided auth + printer selection + config persistence"
  - "printer_control.py: send, status, pause/resume/cancel, filaments"
  - "bambu-config.json config file format with presets"
affects: [04-02-PLAN, SKILL.md]

tech-stack:
  added: [bambu-lab-cloud-api, paho-mqtt]
  patterns: [argparse-CLI-with-JSON-stdout, MQTT-connect-read-disconnect, token-expiry-warning]

key-files:
  created:
    - ".claude/skills/print/scripts/printer_setup.py"
    - ".claude/skills/print/scripts/printer_control.py"
  modified: []

key-decisions:
  - "Used library's built-in pause_print/resume_print/stop_print methods instead of raw MQTT publish"
  - "Token age check at 20h threshold with warning in JSON output"
  - "Merged preset management into printer_setup.py (not separate script) for simpler interface"

patterns-established:
  - "MQTT connect-read-disconnect pattern: non-blocking connect, request status, wait up to 5s, disconnect"
  - "Token expiry warning injected into every JSON response when token > 20h old"
  - "Sliced 3MF detection via zipfile gcode filename check"

requirements-completed: [PRNT-01, PRNT-02]

duration: 3min
completed: 2026-03-07
---

# Phase 4 Plan 1: Printer Integration Scripts Summary

**BambuLab Cloud API scripts for auth/setup and print control (send with auto-slicing, MQTT status, pause/resume/cancel, AMS filaments)**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-07T12:50:56Z
- **Completed:** 2026-03-07T12:54:46Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created printer_setup.py with guided auth flow (email + password + 2FA), printer selection, and config persistence
- Created printer_control.py with 7 subcommands: send, open, status, pause, resume, cancel, filaments
- Send command auto-detects sliced vs unsliced 3MF and slices via BambuStudio CLI when needed
- MQTT-based status returns all detailed fields (state, progress, temps, ETA, layers, error details)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create printer_setup.py** - `2881384` (feat)
2. **Task 2: Create printer_control.py** - `bc596ee` (feat)

## Files Created/Modified
- `.claude/skills/print/scripts/printer_setup.py` - Auth setup, printer selection, preset CRUD (231 lines)
- `.claude/skills/print/scripts/printer_control.py` - Print send/status/control (386 lines)

## Decisions Made
- Used bambulab library's built-in `pause_print()`, `resume_print()`, `stop_print()` methods on MQTTClient rather than raw MQTT publish -- cleaner and less error-prone
- Merged preset management into printer_setup.py as a subcommand rather than a separate script (research suggested 3 scripts, plan consolidated to 2)
- Token expiry warning at 20h (library tokens expire at ~24h) -- proactive warning in every JSON response

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed bambu-lab-cloud-api system-wide**
- **Found during:** Task 1 (pre-task setup)
- **Issue:** bambu-lab-cloud-api not installed, pip refused due to PEP 668
- **Fix:** Installed with `pip3 install --break-system-packages bambu-lab-cloud-api`
- **Files modified:** None (system package)
- **Verification:** `from bambulab import BambuAuthenticator, BambuClient, MQTTClient` imports successfully

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary dependency installation. No scope creep.

## Issues Encountered
None beyond the dependency installation above.

## User Setup Required

Before using printer scripts, user must:
1. Have a BambuLab account (bambulab.com)
2. Run `python3 printer_setup.py setup` to authenticate (email + password + 2FA code from email)
3. Have BambuStudio installed for auto-slicing (optional -- can use `open` command instead)

## Next Phase Readiness
- Both scripts ready for SKILL.md integration (Plan 04-02)
- Config file format established at `~/.claude/bambu-config.json`
- All subcommands output JSON to stdout, matching established pattern from makerworld_search.py

---
*Phase: 04-printer-integration*
*Completed: 2026-03-07*
