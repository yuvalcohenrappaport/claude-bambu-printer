#!/usr/bin/env python3
"""BambuLab printer setup script for the /print skill.

Standalone CLI with subcommands:
  setup          - Guided auth (email + password + 2FA) + printer selection + config save
  switch-printer - Re-select printer using saved token
  presets        - Manage print presets (list/set/remove)

All output is JSON to stdout (for skill parsing). Debug/errors go to stderr.
Config is saved to ~/.claude/bambu-config.json with 0o600 permissions.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

CONFIG_PATH = os.path.expanduser("~/.claude/bambu-config.json")

DEFAULT_PRESETS = {
    "draft": {"layer_height": 0.28, "infill": 15, "speed": 100},
    "standard": {"layer_height": 0.20, "infill": 20, "speed": 80},
    "quality": {"layer_height": 0.12, "infill": 20, "speed": 60},
    "strong": {"layer_height": 0.20, "infill": 50, "speed": 80},
}


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
    """Load existing config file. Exit with error if missing."""
    if not os.path.exists(CONFIG_PATH):
        output_error(
            "No config found. Run 'printer_setup.py setup' first.",
            reauth=True,
        )
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(config: dict):
    """Save config to file with restricted permissions."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(CONFIG_PATH, 0o600)
    eprint(f"[setup] Config saved to {CONFIG_PATH}")


def select_printer(devices: list) -> dict:
    """Show numbered list of printers and let user pick one."""
    if not devices:
        output_error("No printers found on this BambuLab account.")

    print("\nYour printers:", file=sys.stderr)
    for i, d in enumerate(devices):
        name = d.get("name") or d.get("dev_name", "Unknown")
        dev_id = d.get("dev_id", "?")
        model = d.get("dev_model_name", "unknown")
        print(f"  {i + 1}. {name} ({model}) [{dev_id}]", file=sys.stderr)

    while True:
        try:
            choice = int(input(f"\nSelect printer (1-{len(devices)}): "))
            if 1 <= choice <= len(devices):
                return devices[choice - 1]
            print(f"Please enter a number between 1 and {len(devices)}.", file=sys.stderr)
        except (ValueError, EOFError):
            print("Invalid input. Enter a number.", file=sys.stderr)


def cmd_setup(args):
    """Guided setup: authenticate, select printer, save config."""
    from bambulab import BambuAuthenticator, BambuClient

    # Warn if config already exists
    if os.path.exists(CONFIG_PATH):
        print("Existing config found at:", CONFIG_PATH, file=sys.stderr)
        overwrite = input("Overwrite? (y/N): ").strip().lower()
        if overwrite != "y":
            output_json({"status": "cancelled", "message": "Setup cancelled by user."})
            return

    # Step 1: Authenticate
    email = input("BambuLab email: ").strip()
    password = input("BambuLab password: ").strip()

    if not email or not password:
        output_error("Email and password are required.")

    eprint("[setup] Authenticating with BambuLab...")
    try:
        auth = BambuAuthenticator()
        token = auth.login(
            email,
            password,
            lambda: input("Enter 2FA verification code from email: ").strip(),
        )
    except Exception as e:
        err_str = str(e).lower()
        if "401" in err_str or "unauthorized" in err_str or "invalid" in err_str:
            output_error(
                "Authentication failed. Check your email and password.",
                reauth=True,
            )
        else:
            output_error(f"Authentication error: {e}")

    eprint("[setup] Authentication successful.")

    # Step 2: Get user info
    try:
        client = BambuClient(token=token)
        user_info = client.get_user_info()
        user_id = user_info.get("uid") or user_info.get("id") or user_info.get("userId")
        if not user_id:
            eprint(f"[setup] Warning: Could not extract UID from user_info: {list(user_info.keys())}")
            user_id = "unknown"
    except Exception as e:
        output_error(f"Failed to get user info: {e}")

    # Step 3: List printers
    try:
        devices = client.get_devices()
    except Exception as e:
        output_error(f"Failed to list printers: {e}")

    # Step 4: Select printer
    selected = select_printer(devices)
    printer_name = selected.get("name") or selected.get("dev_name", "Unknown")
    printer_id = selected.get("dev_id", "")
    printer_model = selected.get("dev_model_name", "unknown")

    # Step 5: Save config
    config = {
        "region": "global",
        "token": token,
        "token_created": datetime.now(timezone.utc).isoformat(),
        "user_id": str(user_id),
        "printer": {
            "device_id": printer_id,
            "name": printer_name,
            "model": printer_model,
        },
        "presets": DEFAULT_PRESETS,
    }
    save_config(config)

    output_json({
        "status": "ok",
        "printer": printer_name,
        "model": printer_model,
        "message": f"Setup complete. Printer '{printer_name}' configured.",
    })


def cmd_switch_printer(args):
    """Switch to a different printer using saved token."""
    from bambulab import BambuClient

    config = load_config()
    token = config.get("token")
    if not token:
        output_error("No token in config. Run 'printer_setup.py setup' first.", reauth=True)

    eprint("[switch-printer] Listing printers...")
    try:
        client = BambuClient(token=token)
        devices = client.get_devices()
    except Exception as e:
        err_str = str(e).lower()
        if "401" in err_str or "unauthorized" in err_str:
            output_error(
                "Token expired. Run 'printer_setup.py setup' to re-authenticate.",
                reauth=True,
            )
        output_error(f"Failed to list printers: {e}")

    selected = select_printer(devices)
    printer_name = selected.get("name") or selected.get("dev_name", "Unknown")
    printer_id = selected.get("dev_id", "")
    printer_model = selected.get("dev_model_name", "unknown")

    config["printer"] = {
        "device_id": printer_id,
        "name": printer_name,
        "model": printer_model,
    }
    save_config(config)

    output_json({
        "status": "ok",
        "printer": printer_name,
        "model": printer_model,
        "message": f"Switched to printer '{printer_name}'.",
    })


def cmd_presets(args):
    """Manage print presets."""
    config = load_config()
    presets = config.get("presets", {})

    if args.presets_command == "list" or args.presets_command is None:
        output_json({"status": "ok", "presets": presets})

    elif args.presets_command == "set":
        name = args.name
        preset = {}
        if args.layer_height is not None:
            preset["layer_height"] = args.layer_height
        if args.infill is not None:
            preset["infill"] = args.infill
        if args.speed is not None:
            preset["speed"] = args.speed

        if not preset:
            output_error("Provide at least one setting: --layer-height, --infill, or --speed")

        # Merge with existing preset if it exists
        if name in presets:
            presets[name].update(preset)
        else:
            presets[name] = preset

        config["presets"] = presets
        save_config(config)
        output_json({
            "status": "ok",
            "message": f"Preset '{name}' saved.",
            "preset": presets[name],
        })

    elif args.presets_command == "remove":
        name = args.name
        if name not in presets:
            output_error(f"Preset '{name}' not found.")
        if len(presets) <= 1:
            output_error("Cannot remove the last preset. At least one preset must remain.")
        del presets[name]
        config["presets"] = presets
        save_config(config)
        output_json({
            "status": "ok",
            "message": f"Preset '{name}' removed.",
        })


def main():
    parser = argparse.ArgumentParser(
        description="BambuLab printer setup CLI for the /print skill",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # setup subcommand
    subparsers.add_parser(
        "setup",
        help="Guided auth + printer selection + config save",
    )

    # switch-printer subcommand
    subparsers.add_parser(
        "switch-printer",
        help="Switch to a different printer using saved token",
    )

    # presets subcommand
    presets_parser = subparsers.add_parser(
        "presets",
        help="Manage print presets (list/set/remove)",
    )
    presets_sub = presets_parser.add_subparsers(dest="presets_command")

    presets_sub.add_parser("list", help="List all presets")

    set_parser = presets_sub.add_parser("set", help="Add or update a preset")
    set_parser.add_argument("name", help="Preset name")
    set_parser.add_argument("--layer-height", type=float, help="Layer height in mm")
    set_parser.add_argument("--infill", type=int, help="Infill percentage")
    set_parser.add_argument("--speed", type=int, help="Speed percentage")

    remove_parser = presets_sub.add_parser("remove", help="Remove a preset")
    remove_parser.add_argument("name", help="Preset name to remove")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "setup":
        cmd_setup(args)
    elif args.command == "switch-printer":
        cmd_switch_printer(args)
    elif args.command == "presets":
        cmd_presets(args)


if __name__ == "__main__":
    # Check bambulab library only for commands that need it
    has_command = len(sys.argv) > 1 and sys.argv[1] in ("setup", "switch-printer")
    has_help = "--help" in sys.argv or "-h" in sys.argv
    if has_command and not has_help:
        try:
            import importlib
            importlib.import_module("bambulab")
        except ImportError:
            output_error(
                "bambu-lab-cloud-api not installed.",
                fix="Run: pip install bambu-lab-cloud-api",
            )

    main()
