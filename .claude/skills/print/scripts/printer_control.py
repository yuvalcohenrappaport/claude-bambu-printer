#!/usr/bin/env python3
"""BambuLab printer control script for the /print skill.

Standalone CLI with subcommands:
  send       - Send a 3MF file to the printer (auto-slices if needed)
  open       - Open a file in BambuStudio for manual slicing/printing
  status     - Get detailed printer status via MQTT
  pause      - Pause a running print
  resume     - Resume a paused print
  cancel     - Cancel/stop a running print
  filaments  - Query loaded filaments (AMS slots)

All output is JSON to stdout (for skill parsing). Debug/errors go to stderr.
Loads config from ~/.claude/bambu-config.json (created by printer_setup.py).
"""

import argparse
import json
import os
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

CONFIG_PATH = os.path.expanduser("~/.claude/bambu-config.json")

# BambuStudio CLI paths to search (macOS)
BAMBU_STUDIO_PATHS = [
    "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio",
    "/Applications/BambuStudio.app/Contents/MacOS/bambu-studio",
]

# Token age warning threshold (hours)
TOKEN_WARNING_HOURS = 20


def eprint(*args, **kwargs):
    """Print to stderr for debug/error messages."""
    print(*args, file=sys.stderr, **kwargs)


def output_json(data: dict):
    """Print JSON to stdout."""
    print(json.dumps(data, indent=2))


def output_error(error: str, **extra):
    """Print error JSON to stdout and exit."""
    result = {"status": "error", "error": error}
    result.update(extra)
    output_json(result)
    sys.exit(1)


def load_config() -> dict:
    """Load config file. Exit with error if missing."""
    if not os.path.exists(CONFIG_PATH):
        output_error(
            "No config found. Run 'printer_setup.py setup' first.",
            reauth=True,
        )
    with open(CONFIG_PATH) as f:
        return json.load(f)


def check_token_age(config: dict) -> str | None:
    """Check token age and return warning message if old."""
    token_created = config.get("token_created")
    if not token_created:
        return "Token age unknown (no timestamp). Run setup again if you get auth errors."
    try:
        created = datetime.fromisoformat(token_created)
        age_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600
        if age_hours > TOKEN_WARNING_HOURS:
            return f"Token is {age_hours:.0f}h old (limit ~24h). Run printer_setup.py setup to re-authenticate if you get auth errors."
    except (ValueError, TypeError):
        return "Could not parse token timestamp."
    return None


def find_bambu_studio() -> str | None:
    """Find BambuStudio CLI executable."""
    for path in BAMBU_STUDIO_PATHS:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    # Try which
    try:
        result = subprocess.run(
            ["which", "bambu-studio"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


def is_sliced_3mf(filepath: str) -> bool:
    """Check if a 3MF file contains sliced G-code data."""
    try:
        with zipfile.ZipFile(filepath, "r") as z:
            names = z.namelist()
            return any("gcode" in n.lower() for n in names)
    except (zipfile.BadZipFile, FileNotFoundError):
        return False


def cmd_send(args):
    """Send a 3MF file to the printer for cloud printing."""
    from bambulab import BambuClient

    config = load_config()
    token_warning = check_token_age(config)

    file_path = os.path.abspath(args.file)
    if not os.path.isfile(file_path):
        output_error(f"File not found: {file_path}")
    if not file_path.lower().endswith(".3mf"):
        output_error(f"File must be a .3mf file, got: {file_path}")

    printer = config.get("printer", {})
    device_id = printer.get("device_id")
    printer_name = printer.get("name", "Unknown")

    # Determine if slicing is needed
    sliced = is_sliced_3mf(file_path)
    sliced_path = file_path
    did_slice = False

    if args.no_slice:
        eprint("[send] Skipping slice check (--no-slice)")
        sliced = True  # Trust the user
    elif not sliced:
        eprint("[send] File is not sliced. Looking for BambuStudio CLI...")
        bambu_cli = find_bambu_studio()
        if not bambu_cli:
            output_error(
                "3MF file is not sliced and BambuStudio CLI was not found. "
                "Install BambuStudio (https://bambulab.com/en/download/studio) "
                "or use the 'open' command to slice manually in BambuStudio.",
                suggestion="Use 'printer_control.py open <file>' to open in BambuStudio instead.",
            )

        # Slice the file
        base = Path(file_path)
        sliced_path = str(base.parent / f"{base.stem}_sliced.3mf")
        eprint(f"[send] Slicing with BambuStudio: {bambu_cli}")
        try:
            result = subprocess.run(
                [bambu_cli, "--slice", "0", "--export-3mf", sliced_path, file_path],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                eprint(f"[send] Slicer stderr: {result.stderr}")
                output_error(
                    f"BambuStudio slicing failed (exit code {result.returncode}). "
                    "Use 'printer_control.py open <file>' to slice manually.",
                    slicer_stderr=result.stderr[:500],
                )
            did_slice = True
            eprint(f"[send] Sliced to: {sliced_path}")
        except subprocess.TimeoutExpired:
            output_error("BambuStudio slicing timed out after 120 seconds.")
        except Exception as e:
            output_error(f"Slicing error: {e}")

    # Dry run: show summary and exit
    if args.dry_run:
        result = {
            "status": "ok",
            "dry_run": True,
            "file": os.path.basename(file_path),
            "sliced": sliced or did_slice,
            "printer": printer_name,
            "device_id": device_id,
        }
        if args.preset:
            presets = config.get("presets", {})
            if args.preset in presets:
                result["preset"] = {args.preset: presets[args.preset]}
            else:
                result["preset_warning"] = f"Preset '{args.preset}' not found."
        if token_warning:
            result["token_warning"] = token_warning
        output_json(result)
        return

    # Upload and start cloud print
    eprint(f"[send] Uploading to BambuLab cloud...")
    try:
        client = BambuClient(token=config["token"])
        upload_result = client.upload_file(file_path=sliced_path)
        eprint(f"[send] Upload result: {upload_result}")
    except Exception as e:
        err_str = str(e).lower()
        if "401" in err_str or "unauthorized" in err_str:
            output_error(
                "Token expired. Run 'printer_setup.py setup' to re-authenticate.",
                reauth=True,
            )
        output_error(f"Upload failed: {e}")

    # Start cloud print with retry (Pitfall 6: cloud file registration delay)
    filename = os.path.basename(sliced_path)
    eprint(f"[send] Starting cloud print: {filename} on {printer_name}...")
    last_error = None
    for attempt in range(1, 4):
        try:
            print_result = client.start_cloud_print(
                device_id=device_id,
                filename=filename,
            )
            eprint(f"[send] Print started: {print_result}")

            result = {
                "status": "ok",
                "message": "Print started",
                "file": os.path.basename(file_path),
                "printer": printer_name,
                "sliced": sliced or did_slice,
            }
            if token_warning:
                result["token_warning"] = token_warning
            output_json(result)
            return

        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if "401" in err_str or "unauthorized" in err_str:
                output_error(
                    "Token expired. Run 'printer_setup.py setup' to re-authenticate.",
                    reauth=True,
                )
            eprint(f"[send] Attempt {attempt}/3 failed: {e}")
            if attempt < 3:
                time.sleep(2)

    output_error(f"Failed to start print after 3 attempts: {last_error}")


def cmd_open(args):
    """Open a file in BambuStudio."""
    file_path = os.path.abspath(args.file)
    if not os.path.isfile(file_path):
        output_error(f"File not found: {file_path}")

    try:
        subprocess.run(["open", "-a", "BambuStudio", file_path], check=True, timeout=10)
        output_json({
            "status": "ok",
            "message": "Opened in BambuStudio",
            "file": os.path.basename(file_path),
        })
    except FileNotFoundError:
        output_error(
            "BambuStudio not found. Install from https://bambulab.com/en/download/studio"
        )
    except subprocess.CalledProcessError as e:
        output_error(f"Failed to open BambuStudio: {e}")
    except subprocess.TimeoutExpired:
        # open command may return slowly but app still opens
        output_json({
            "status": "ok",
            "message": "Opened in BambuStudio (launch may take a moment)",
            "file": os.path.basename(file_path),
        })


def cmd_status(args):
    """Get detailed printer status via MQTT."""
    from bambulab import MQTTClient

    config = load_config()
    token_warning = check_token_age(config)
    printer = config.get("printer", {})
    device_id = printer.get("device_id")

    status_data = {}

    def on_message(dev_id, data):
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
                "nozzle_target": p.get("nozzle_target_temper", 0),
                "bed_temp": p.get("bed_temper", 0),
                "bed_target": p.get("bed_target_temper", 0),
                "speed": p.get("spd_lvl", 100),
                "task_name": p.get("subtask_name", ""),
                "filament": p.get("subtask_name", ""),  # Will be enriched from AMS
                "print_error": p.get("print_error", 0),
            }
            # Try to get filament info from AMS
            ams = p.get("ams", {})
            if isinstance(ams, dict):
                ams_list = ams.get("ams", [])
                if ams_list and isinstance(ams_list, list):
                    tray = ams_list[0].get("tray", []) if ams_list[0] else []
                    if tray:
                        active = tray[0] if tray else {}
                        status_data["filament"] = active.get("tray_type", "Unknown")

    eprint("[status] Connecting to printer via MQTT...")
    try:
        mqtt = MQTTClient(
            username=f"u_{config['user_id']}",
            access_token=config["token"],
            device_id=device_id,
            on_message=on_message,
        )
        mqtt.connect(blocking=False)
        mqtt.request_full_status()

        # Wait up to 5 seconds for a response
        for _ in range(10):
            time.sleep(0.5)
            if status_data:
                break

        mqtt.disconnect()
    except Exception as e:
        err_str = str(e).lower()
        if "401" in err_str or "unauthorized" in err_str or "auth" in err_str:
            output_error(
                "Token expired. Run 'printer_setup.py setup' to re-authenticate.",
                reauth=True,
            )
        output_error(f"MQTT connection failed: {e}")

    if not status_data:
        result = {
            "status": "ok",
            "printer": {"state": "UNREACHABLE"},
            "message": "No status received from printer within 5 seconds. Printer may be off or unreachable.",
        }
        if token_warning:
            result["token_warning"] = token_warning
        output_json(result)
        return

    # Add error details and suggestions if there's a print error
    if status_data.get("print_error", 0) != 0 or status_data.get("state") == "FAILED":
        status_data["error_details"] = f"Error code: {status_data.get('print_error', 'unknown')}"
        status_data["suggestions"] = [
            "Check for filament tangle or runout",
            "Check if nozzle is clogged",
            "Resume print if error is recoverable",
            "Cancel and restart if print is damaged or shifted",
            "Check bed adhesion if first layer failed",
        ]

    result = {"status": "ok", "printer": status_data}
    if token_warning:
        result["token_warning"] = token_warning
    output_json(result)


def _mqtt_command(action: str, method_name: str):
    """Execute an MQTT print control command (pause/resume/stop)."""
    from bambulab import MQTTClient

    config = load_config()
    printer = config.get("printer", {})
    device_id = printer.get("device_id")
    printer_name = printer.get("name", "Unknown")

    eprint(f"[{action}] Connecting to printer via MQTT...")
    try:
        mqtt = MQTTClient(
            username=f"u_{config['user_id']}",
            access_token=config["token"],
            device_id=device_id,
            on_message=lambda *a: None,
        )
        mqtt.connect(blocking=False)
        time.sleep(1)  # Wait for connection

        # Call the appropriate method
        getattr(mqtt, method_name)()
        eprint(f"[{action}] Command sent.")
        time.sleep(0.5)  # Brief wait for acknowledgment
        mqtt.disconnect()

        output_json({
            "status": "ok",
            "message": f"Print {action} command sent to {printer_name}.",
            "printer": printer_name,
        })
    except Exception as e:
        err_str = str(e).lower()
        if "401" in err_str or "unauthorized" in err_str or "auth" in err_str:
            output_error(
                "Token expired. Run 'printer_setup.py setup' to re-authenticate.",
                reauth=True,
            )
        output_error(f"Failed to send {action} command: {e}")


def cmd_pause(args):
    """Pause a running print."""
    _mqtt_command("pause", "pause_print")


def cmd_resume(args):
    """Resume a paused print."""
    _mqtt_command("resume", "resume_print")


def cmd_cancel(args):
    """Cancel/stop a running print."""
    _mqtt_command("cancel", "stop_print")


def cmd_filaments(args):
    """Query loaded filaments from AMS."""
    from bambulab import MQTTClient

    config = load_config()
    token_warning = check_token_age(config)
    printer = config.get("printer", {})
    device_id = printer.get("device_id")

    ams_data = {}

    def on_message(dev_id, data):
        nonlocal ams_data
        p = data.get("print", {})
        if p:
            ams_data = p.get("ams", {})

    eprint("[filaments] Connecting to printer via MQTT...")
    try:
        mqtt = MQTTClient(
            username=f"u_{config['user_id']}",
            access_token=config["token"],
            device_id=device_id,
            on_message=on_message,
        )
        mqtt.connect(blocking=False)
        mqtt.request_full_status()

        for _ in range(10):
            time.sleep(0.5)
            if ams_data:
                break

        mqtt.disconnect()
    except Exception as e:
        err_str = str(e).lower()
        if "401" in err_str or "unauthorized" in err_str or "auth" in err_str:
            output_error(
                "Token expired. Run 'printer_setup.py setup' to re-authenticate.",
                reauth=True,
            )
        output_error(f"MQTT connection failed: {e}")

    # Parse AMS data into filament list
    filaments = []
    ams_list = ams_data.get("ams", []) if isinstance(ams_data, dict) else []
    for unit_idx, unit in enumerate(ams_list):
        trays = unit.get("tray", []) if isinstance(unit, dict) else []
        for tray_idx, tray in enumerate(trays):
            if isinstance(tray, dict) and tray.get("tray_type"):
                slot_num = unit_idx * 4 + tray_idx + 1  # AMS slots 1-16
                filaments.append({
                    "slot": slot_num,
                    "type": tray.get("tray_type", "Unknown"),
                    "color": tray.get("tray_color", ""),
                    "nozzle_temp_min": tray.get("nozzle_temp_min", 0),
                    "nozzle_temp_max": tray.get("nozzle_temp_max", 0),
                })

    result = {"status": "ok", "filaments": filaments}
    if not filaments:
        result["message"] = "No filaments detected. AMS may not be connected or no filaments loaded."
    if token_warning:
        result["token_warning"] = token_warning
    output_json(result)


def main():
    parser = argparse.ArgumentParser(
        description="BambuLab printer control CLI for the /print skill",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # send subcommand
    send_parser = subparsers.add_parser(
        "send",
        help="Send a 3MF file to the printer for cloud printing",
    )
    send_parser.add_argument("file", help="Path to .3mf file")
    send_parser.add_argument(
        "--preset", help="Apply a named preset before sending",
    )
    send_parser.add_argument(
        "--no-slice", action="store_true",
        help="Skip slicing (for already-sliced files)",
    )
    send_parser.add_argument(
        "--dry-run", action="store_true",
        help="Show confirmation summary without sending",
    )

    # open subcommand
    open_parser = subparsers.add_parser(
        "open",
        help="Open a file in BambuStudio",
    )
    open_parser.add_argument("file", help="Path to file to open")

    # status subcommand
    subparsers.add_parser(
        "status",
        help="Get detailed printer status",
    )

    # pause subcommand
    subparsers.add_parser(
        "pause",
        help="Pause a running print",
    )

    # resume subcommand
    subparsers.add_parser(
        "resume",
        help="Resume a paused print",
    )

    # cancel subcommand
    subparsers.add_parser(
        "cancel",
        help="Cancel/stop a running print",
    )

    # filaments subcommand
    subparsers.add_parser(
        "filaments",
        help="Query loaded filaments (AMS slots)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "send": cmd_send,
        "open": cmd_open,
        "status": cmd_status,
        "pause": cmd_pause,
        "resume": cmd_resume,
        "cancel": cmd_cancel,
        "filaments": cmd_filaments,
    }
    commands[args.command](args)


if __name__ == "__main__":
    # Check bambulab library only for commands that need it
    mqtt_commands = {"status", "pause", "resume", "cancel", "filaments"}
    api_commands = {"send"}
    needs_lib = len(sys.argv) > 1 and sys.argv[1] in (mqtt_commands | api_commands)
    has_help = "--help" in sys.argv or "-h" in sys.argv
    if needs_lib and not has_help:
        try:
            import importlib
            importlib.import_module("bambulab")
        except ImportError:
            output_error(
                "bambu-lab-cloud-api not installed.",
                fix="Run: pip install bambu-lab-cloud-api",
            )

    main()
