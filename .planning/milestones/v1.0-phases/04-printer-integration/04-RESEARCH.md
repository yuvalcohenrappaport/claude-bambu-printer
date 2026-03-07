# Phase 4: Printer Integration - Research

**Researched:** 2026-03-07
**Domain:** BambuLab Cloud API integration (authentication, file upload, print control, status monitoring)
**Confidence:** MEDIUM

## Summary

Phase 4 connects the existing 3MF pipeline to a BambuLab printer via the Cloud API. The primary library is `bambu-lab-cloud-api` (v1.0.5), an unofficial but well-documented Python package that wraps BambuLab's Cloud HTTP API and Cloud MQTT for real-time monitoring and print control. The library handles authentication (email/password + 2FA), file upload to BambuLab's S3 cloud storage, starting cloud prints, and MQTT-based status monitoring with pause/resume/stop commands.

**Critical finding:** BambuLab printers require **sliced** 3MF files (containing G-code), not raw mesh-only 3MF. Our pipeline currently produces unsliced 3MF files. Two paths exist: (1) "send to printer" via cloud requires slicing first using BambuStudio CLI (`--slice 0 --export-3mf`), or (2) "open in BambuStudio" lets the user slice manually. Both are in scope per the CONTEXT.md decisions.

**Primary recommendation:** Use `bambu-lab-cloud-api` for cloud auth + upload + print + MQTT monitoring. Use BambuStudio CLI for automated slicing before cloud print. Store credentials in `~/.claude/bambu-config.json`. Implement two scripts: `printer_setup.py` (guided auth + printer selection) and `printer_control.py` (send/status/pause/resume/cancel).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Authenticate via BambuLab Cloud API (not LAN/IP)
- Credentials stored in a config file (e.g., `~/.claude/bambu-config.json`)
- First-time guided setup flow: login -> select printer -> save config
- If multiple printers on account, always show list and let user pick (no default)
- Always show confirmation summary before sending (file, printer, settings)
- Can print any .3mf file from disk, not just session-generated models
- Two send options: "send to printer" (cloud print) or "open in BambuStudio" (local slicer)
- After successful send, automatically start polling for status updates
- Detailed status: state (idle/printing/error), progress %, ETA, temperatures, speed, current layer, filament used
- Auto-monitor after send: poll periodically for updates, show inline
- Full print control: pause, resume, stop/cancel from Claude Code
- On printer error: notify with error details and suggest next steps (resume, cancel, troubleshoot)
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

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRNT-01 | User can send 3MF to BambuLab printer for printing | `bambu-lab-cloud-api` upload_file + start_cloud_print; BambuStudio CLI for slicing; BambuStudio open command as alternative |
| PRNT-02 | User can check printer status | `bambu-lab-cloud-api` MQTTClient for real-time status (gcode_state, progress, temps, ETA, layers, filament) |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **bambu-lab-cloud-api** | 1.0.5 | Cloud auth, file upload, MQTT monitoring, print control | Only maintained Python library for BambuLab Cloud API. Handles auth (incl. 2FA), S3 upload, cloud print, MQTT status/commands. Documented as of Oct 2025. |
| **BambuStudio CLI** | system install | Slice 3MF files before cloud upload | BambuLab's own slicer. CLI supports `--slice 0 --export-3mf` for headless slicing. Required because cloud print needs sliced 3MF. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **paho-mqtt** | (transitive) | MQTT protocol for printer communication | Pulled in by bambu-lab-cloud-api. No direct usage needed. |
| **requests** | (transitive) | HTTP client for Cloud API | Pulled in by bambu-lab-cloud-api. No direct usage needed. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| bambu-lab-cloud-api | bambulabs-api (v2.6.6) | bambulabs-api uses LOCAL MQTT (port 8883 on LAN). User decision locks us to Cloud API. bambulabs-api cannot do cloud auth/upload. |
| bambu-lab-cloud-api | bambu-connect | Newer, less documented, fewer users. bambu-lab-cloud-api has better cloud API coverage. |
| BambuStudio CLI slicing | OrcaSlicer CLI | OrcaSlicer has similar CLI. BambuStudio is the official BambuLab slicer, more likely already installed. |

**Installation:**
```bash
pip install bambu-lab-cloud-api
# BambuStudio must be installed as system app (user likely already has it)
```

## Architecture Patterns

### Recommended Project Structure
```
.claude/skills/print/scripts/
  printer_setup.py     # Auth + printer selection + config save
  printer_control.py   # Send print, status, pause/resume/cancel
  printer_presets.py    # Preset management (CRUD)
```

### Config File Structure
```json
// ~/.claude/bambu-config.json
{
  "region": "global",
  "token": "eyJhbGc...",
  "user_id": "u_12345",
  "printer": {
    "device_id": "01P00A000000000",
    "name": "My Printer",
    "model": "A1"
  },
  "presets": {
    "draft": {"layer_height": 0.28, "infill": 15, "speed": 100},
    "quality": {"layer_height": 0.12, "infill": 20, "speed": 60},
    "strong": {"layer_height": 0.20, "infill": 50, "speed": 80}
  }
}
```

### Pattern 1: Guided Setup Flow
**What:** Interactive first-time setup via CLI prompts (email, password, 2FA code, printer selection).
**When to use:** First run or when config file is missing/invalid.
**Example:**
```python
from bambulab import BambuAuthenticator, BambuClient
import json

# Step 1: Authenticate
auth = BambuAuthenticator()
token = auth.login(email, password, lambda: input("Enter 2FA code: "))

# Step 2: Get user info for MQTT username
client = BambuClient(token=token)
user_info = client.get_user_info()  # contains UID

# Step 3: List printers, user picks one
devices = client.get_devices()
# Present numbered list, user picks

# Step 4: Save config
config = {"token": token, "user_id": user_info["uid"], "printer": selected_device}
with open(config_path, "w") as f:
    json.dump(config, f, indent=2)
```

### Pattern 2: Cloud Print Flow (Sliced)
**What:** Slice with BambuStudio CLI, upload to cloud, start print.
**When to use:** "Send to printer" option.
**Example:**
```python
import subprocess
from bambulab import BambuClient

# Step 1: Slice 3MF using BambuStudio CLI
bambu_cli = "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"
subprocess.run([
    bambu_cli, "--slice", "0", "--export-3mf", "sliced_output.3mf",
    "input.3mf"
], check=True)

# Step 2: Upload sliced file to cloud
client = BambuClient(token=config["token"])
client.upload_file(file_path="sliced_output.3mf")

# Step 3: Start cloud print
result = client.start_cloud_print(
    device_id=config["printer"]["device_id"],
    filename="sliced_output.3mf"
)
```

### Pattern 3: MQTT Status Monitoring
**What:** Subscribe to printer MQTT for real-time status updates.
**When to use:** After sending print, or when user asks for status.
**Example:**
```python
from bambulab import MQTTClient

def on_status(device_id, data):
    print_data = data.get("print", {})
    return {
        "state": print_data.get("gcode_state"),      # IDLE/RUNNING/PAUSE/FAILED/FINISH
        "progress": print_data.get("mc_percent"),      # 0-100
        "eta_minutes": print_data.get("mc_remaining_time"),
        "layer": print_data.get("layer_num"),
        "total_layers": print_data.get("total_layer_num"),
        "nozzle_temp": print_data.get("nozzle_temper"),
        "bed_temp": print_data.get("bed_temper"),
        "subtask": print_data.get("subtask_name"),
    }

mqtt = MQTTClient(
    username=f"u_{config['user_id']}",
    access_token=config["token"],
    device_id=config["printer"]["device_id"],
    on_message=on_status
)
mqtt.connect(blocking=False)
mqtt.request_full_status()
```

### Pattern 4: Print Control Commands
**What:** Pause, resume, or cancel a running print via MQTT.
**When to use:** User requests print control.
**Example:**
```python
# Pause
mqtt.publish_command({
    "print": {"sequence_id": "0", "command": "pause", "param": ""}
})

# Resume
mqtt.publish_command({
    "print": {"sequence_id": "0", "command": "resume", "param": ""}
})

# Stop/Cancel
mqtt.publish_command({
    "print": {"sequence_id": "0", "command": "stop", "param": ""}
})
```

### Pattern 5: Open in BambuStudio
**What:** Launch BambuStudio with the 3MF file for manual slicing/printing.
**When to use:** "Open in BambuStudio" option.
**Example:**
```python
import subprocess
# macOS: use 'open' command which handles app association
subprocess.run(["open", "-a", "BambuStudio", "model.3mf"])
# Alternative direct path:
# subprocess.run(["/Applications/BambuStudio.app/Contents/MacOS/BambuStudio", "model.3mf"])
```

### Anti-Patterns to Avoid
- **Using bambulabs-api for this phase:** It connects via local MQTT, not cloud. User decided on Cloud API.
- **Sending unsliced 3MF to cloud print:** Will fail. BambuLab printers need sliced 3MF with G-code. Always slice first.
- **Storing password in config:** Store only the JWT token. Re-authenticate when token expires (24h).
- **Polling MQTT too frequently:** The pushall command should not be sent more often than every 5 minutes on P1P models. Regular status updates arrive every 0.5-2 seconds automatically via subscription.
- **Blocking MQTT connection in script:** Use `blocking=False` so the script can return status and exit. Claude can call the script again for updates.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cloud authentication + 2FA | Custom HTTP auth flow | `BambuAuthenticator` from bambu-lab-cloud-api | 2FA flow is multi-step, token storage needs secure permissions, JWT validation is tricky |
| S3 file upload | Custom S3 signed URL handling | `client.upload_file()` from bambu-lab-cloud-api | S3 signed URLs fail with modified headers; library handles this correctly |
| MQTT connection + TLS | Custom paho-mqtt setup | `MQTTClient` from bambu-lab-cloud-api | Cloud MQTT requires specific username format, TLS config, topic patterns |
| 3MF slicing | Any Python-based slicer | BambuStudio CLI | Slicing is enormously complex; BambuStudio is purpose-built for BambuLab printers |
| Print settings presets | Complex settings engine | Simple JSON dict in config file | Presets are just key-value mappings to CLI flags; no need for a framework |

**Key insight:** The bambu-lab-cloud-api library handles the hardest parts (auth, upload, MQTT). Our scripts are thin wrappers that orchestrate the library calls and manage config.

## Common Pitfalls

### Pitfall 1: Sending Unsliced 3MF to Printer
**What goes wrong:** User sends a raw 3MF (mesh only, no G-code) via cloud print. Printer rejects it or behaves unpredictably.
**Why it happens:** Our pipeline produces unsliced 3MF. The cloud API accepts the upload but the printer cannot execute it.
**How to avoid:** Always slice via BambuStudio CLI before cloud upload. Detect whether a 3MF is sliced by checking for Metadata/plate_*.gcode inside the 3MF zip.
**Warning signs:** Print starts but immediately fails. Printer shows 0% and errors.

### Pitfall 2: Token Expiration (24h)
**What goes wrong:** Saved token expires. API calls return 401 Unauthorized.
**Why it happens:** BambuLab JWT tokens expire after ~24 hours. No refresh token mechanism documented.
**How to avoid:** Catch 401 errors and prompt user to re-authenticate. Store token creation timestamp in config. Proactively warn if token is old.
**Warning signs:** 401 HTTP responses. MQTT connection refused.

### Pitfall 3: 2FA Required for All Accounts
**What goes wrong:** Setup flow tries to login with just email/password but BambuLab enforces 2FA via email.
**Why it happens:** All BambuLab accounts require email verification code, not just those with 2FA "enabled."
**How to avoid:** Always implement the 2FA flow: submit credentials -> request verification code -> prompt user for code -> complete login.
**Warning signs:** Login response contains `loginType: "verifyCode"` instead of a token.

### Pitfall 4: MQTT Pushall Rate Limit
**What goes wrong:** Sending `pushall` command too frequently causes printer to become unresponsive or disconnect.
**Why it happens:** P1P and some models have limited processing power for MQTT.
**How to avoid:** Send pushall only once on connect. After that, rely on automatic status updates (arrive every 0.5-2s during printing). Poll no more often than every 5 minutes for idle printers.
**Warning signs:** MQTT disconnect, printer lag, no response to commands.

### Pitfall 5: BambuStudio CLI Not Installed or Wrong Path
**What goes wrong:** Slicing step fails because BambuStudio is not installed or not at the expected path.
**Why it happens:** BambuStudio is a system app, not a pip package. Path varies by install method.
**How to avoid:** Check common paths: `/Applications/BambuStudio.app/Contents/MacOS/BambuStudio`, `which bambu-studio`. Fail fast with install instructions if not found.
**Warning signs:** FileNotFoundError on subprocess call.

### Pitfall 6: Cloud File Registration Delay
**What goes wrong:** After upload, immediately calling start_cloud_print fails because file hasn't registered yet.
**Why it happens:** Uploaded files take 1-2 seconds to appear in cloud listings.
**How to avoid:** Add a short retry loop (3 attempts, 2s apart) when starting cloud print after upload.
**Warning signs:** start_cloud_print returns file-not-found error right after successful upload.

### Pitfall 7: BambuStudio CLI Slicing Without Proper Settings
**What goes wrong:** BambuStudio CLI slices with default/wrong settings (wrong printer profile, wrong filament).
**Why it happens:** CLI needs explicit `--load-settings` and `--load-filaments` JSON files to know the target printer and material.
**How to avoid:** Ship default settings JSON files for common BambuLab printers (A1, P1S, X1C). Query printer for installed filaments and match to settings files.
**Warning signs:** Sliced file has wrong nozzle temp, wrong bed adhesion, wrong print speed.

## Code Examples

### Complete Setup Flow
```python
# Source: bambu-lab-cloud-api README + API_AUTHENTICATION.md
import json, os, sys
from bambulab import BambuAuthenticator, BambuClient

CONFIG_PATH = os.path.expanduser("~/.claude/bambu-config.json")

def setup():
    email = input("BambuLab email: ")
    password = input("BambuLab password: ")

    auth = BambuAuthenticator()
    token = auth.login(email, password, lambda: input("Enter 2FA code from email: "))

    client = BambuClient(token=token)
    user_info = client.get_user_info()
    devices = client.get_devices()

    if not devices:
        print("No printers found on this account.")
        sys.exit(1)

    print("\nYour printers:")
    for i, d in enumerate(devices):
        print(f"  {i+1}. {d['name']} ({d['dev_id']})")

    choice = int(input("Select printer number: ")) - 1
    selected = devices[choice]

    config = {
        "region": "global",
        "token": token,
        "user_id": user_info.get("uid"),
        "printer": {
            "device_id": selected["dev_id"],
            "name": selected["name"],
            "model": selected.get("dev_model_name", "unknown")
        },
        "presets": {
            "draft": {"layer_height": 0.28, "infill": 15, "speed": 100},
            "quality": {"layer_height": 0.12, "infill": 20, "speed": 60},
            "strong": {"layer_height": 0.20, "infill": 50, "speed": 80}
        }
    }

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(CONFIG_PATH, 0o600)

    print(json.dumps({"status": "ok", "printer": selected["name"]}))
```

### Check Printer Status (Non-Blocking)
```python
# Source: bambu-lab-cloud-api MQTT docs + OpenBambuAPI/mqtt.md
import json, time
from bambulab import MQTTClient

def get_status(config):
    status_data = {}

    def on_message(device_id, data):
        nonlocal status_data
        p = data.get("print", {})
        if p:
            status_data = {
                "state": p.get("gcode_state", "UNKNOWN"),
                "progress": p.get("mc_percent", 0),
                "eta_minutes": p.get("mc_remaining_time", 0),
                "layer": p.get("layer_num", 0),
                "total_layers": p.get("total_layer_num", 0),
                "nozzle_temp": p.get("nozzle_temper", 0),
                "bed_temp": p.get("bed_temper", 0),
                "task_name": p.get("subtask_name", ""),
                "print_error": p.get("print_error", 0),
            }

    mqtt = MQTTClient(
        username=f"u_{config['user_id']}",
        access_token=config["token"],
        device_id=config["printer"]["device_id"],
        on_message=on_message
    )
    mqtt.connect(blocking=False)
    mqtt.request_full_status()
    time.sleep(3)  # Wait for response
    mqtt.disconnect()

    return status_data
```

### Detect Sliced vs Unsliced 3MF
```python
import zipfile

def is_sliced_3mf(filepath):
    """Check if a 3MF file contains sliced G-code data."""
    try:
        with zipfile.ZipFile(filepath, 'r') as z:
            names = z.namelist()
            # Sliced 3MF files contain gcode in Metadata/
            return any('gcode' in n.lower() for n in names)
    except zipfile.BadZipFile:
        return False
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| bambulabs-api (local MQTT only) | bambu-lab-cloud-api (cloud + local) | Oct 2025 | Cloud auth eliminates need for local network access, IP, access code |
| Manual BambuStudio slicing | BambuStudio CLI `--slice` | BambuStudio v1.8+ | Enables automated slicing pipeline from CLI |
| Developer Mode required for local API | bambu-lab-cloud-api compatibility layer | Oct 2025 | Cloud API works without developer mode on printer |

**Deprecated/outdated:**
- **bambulabs-api for cloud printing**: Only supports local MQTT. Use bambu-lab-cloud-api for cloud.
- **Manual token extraction**: bambu-lab-cloud-api handles auth flow including 2FA programmatically.

## Open Questions

1. **BambuStudio CLI slicing reliability**
   - What we know: CLI supports `--slice 0 --export-3mf`. Settings can be loaded via `--load-settings` and `--load-filaments`.
   - What's unclear: How reliable is headless slicing? Some GitHub issues report failures with certain flag combinations. Settings JSON format is not well-documented.
   - Recommendation: Test thoroughly during implementation. Fall back to "open in BambuStudio" if CLI slicing proves unreliable. Start with the simpler "open in BambuStudio" path first.
   - **Confidence: LOW**

2. **Print settings override at send time**
   - What we know: Cloud API accepts optional settings (layer_height, infill, speed, temperature, etc.). BambuStudio CLI accepts settings via `--load-settings`.
   - What's unclear: Whether cloud API settings override the sliced 3MF settings, or if settings must be baked in during slicing.
   - Recommendation: Implement overrides at the BambuStudio CLI slicing step, not at cloud upload time. This guarantees settings are correctly applied.
   - **Confidence: MEDIUM**

3. **Querying printer for available filaments**
   - What we know: MQTT status includes `ams` array with material type, color, temperature ranges. This represents physically loaded filaments.
   - What's unclear: Exact format of the AMS data and how to map it to BambuStudio filament profiles.
   - Recommendation: Parse AMS data from MQTT status. Display material type and color to user. Map to closest BambuStudio filament preset.
   - **Confidence: MEDIUM**

4. **Token refresh mechanism**
   - What we know: JWT tokens expire after ~24 hours. No refresh endpoint documented.
   - What's unclear: Whether there's an undocumented refresh flow, or if re-login is always required.
   - Recommendation: Detect 401 errors, prompt re-authentication. Store token timestamp, proactively warn when approaching expiry.
   - **Confidence: MEDIUM**

## Polling Interval Recommendation (Claude's Discretion)

| Printer State | Recommended Interval | Rationale |
|---------------|---------------------|-----------|
| Active print | 30 seconds | MQTT auto-pushes every 0.5-2s; script just needs to reconnect and read latest |
| Idle/checking | Single request | No ongoing poll needed; user asks when they want status |
| After send | 10 seconds for first 2 min | Catch early failures fast, then slow to 30s |

**Approach:** Don't run a persistent background daemon. Each status check is a connect-read-disconnect cycle. Claude calls the script when showing status to the user.

## BambuStudio Launch Recommendation (Claude's Discretion)

Use macOS `open` command: `open -a "BambuStudio" model.3mf`. This is the most reliable cross-install approach (works regardless of whether BambuStudio was installed via DMG or Homebrew).

## Default Presets Recommendation (Claude's Discretion)

| Preset | Layer Height | Infill | Speed | Use Case |
|--------|-------------|--------|-------|----------|
| draft | 0.28mm | 15% | 100% | Fast prototypes, test fits |
| standard | 0.20mm | 20% | 80% | General purpose |
| quality | 0.12mm | 20% | 60% | Visible/decorative parts |
| strong | 0.20mm | 50% | 80% | Load-bearing, functional parts |

## Sources

### Primary (HIGH confidence)
- [bambu-lab-cloud-api GitHub README](https://github.com/coelacant1/Bambu-Lab-Cloud-API/blob/main/bambulab/README.md) - Library API, classes, methods, code examples
- [API_FILES_PRINTING.md](https://github.com/coelacant1/Bambu-Lab-Cloud-API/blob/main/API_FILES_PRINTING.md) - File upload and cloud print workflow
- [API_AUTHENTICATION.md](https://github.com/coelacant1/Bambu-Lab-Cloud-API/blob/main/API_AUTHENTICATION.md) - Auth flow, 2FA, token management
- [OpenBambuAPI/mqtt.md](https://github.com/Doridian/OpenBambuAPI/blob/main/mqtt.md) - MQTT commands (pause/resume/stop), status fields
- [BambuStudio CLI Wiki](https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage) - CLI slicing options and examples

### Secondary (MEDIUM confidence)
- [bambu-lab-cloud-api PyPI](https://pypi.org/project/bambu-lab-cloud-api/) - v1.0.5, dependencies: requests, paho-mqtt, flask, flask-cors
- [BambuLab Third-party Integration Wiki](https://wiki.bambulab.com/en/software/third-party-integration) - Official integration guidance
- [BambuLab Forum - MQTT discussions](https://forum.bambulab.com/t/how-to-use-bambulab-api/112196) - Community experience reports

### Tertiary (LOW confidence)
- BambuStudio CLI headless slicing reliability - community reports mixed results (GitHub issues #2930, #9636)
- Cloud API print settings override behavior - not explicitly documented whether settings can override post-slice

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - bambu-lab-cloud-api is unofficial, v1.0.5, documented as of Oct 2025. Core API calls (auth, upload, print, MQTT) are well-documented with examples. Risk: library may break with firmware updates.
- Architecture: HIGH - Script-per-action pattern is established from prior phases. Config file pattern is straightforward.
- Pitfalls: HIGH - Sliced-vs-unsliced 3MF issue is well-documented. Token expiry and 2FA are documented in library.
- BambuStudio CLI slicing: LOW - Community reports mixed reliability. May need fallback.

**Research date:** 2026-03-07
**Valid until:** 2026-04-07 (30 days - library is unofficial and may change with BambuLab firmware updates)
