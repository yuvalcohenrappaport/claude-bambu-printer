#!/usr/bin/env python3
"""Blender setup / install check script for the /print skill.

Standalone CLI with subcommands:
  status   - JSON report of Blender app, venv, and MCP registration state
  install  - Create venv and install blender_mcp package
  register - Add mcpServers.blender_mcp entry to ~/.claude/settings.json

All output is JSON to stdout (for skill parsing). Debug/errors go to stderr.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import venv
from pathlib import Path
from typing import List, Optional

MACOS_BLENDER_PATH = "/Applications/Blender.app/Contents/MacOS/Blender"
VENV_DIR = os.path.expanduser("~/.claude/skills/print/.venv-blender")
CLAUDE_SETTINGS_PATH = os.path.expanduser("~/.claude/settings.json")
MCP_GIT_URL = "git+https://projects.blender.org/lab/blender_mcp.git"


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def check_blender_app() -> bool:
    return os.path.isfile(MACOS_BLENDER_PATH) and os.access(MACOS_BLENDER_PATH, os.X_OK)


def check_mcp_venv() -> bool:
    entry = Path(VENV_DIR) / "bin" / "blender-mcp"
    return entry.is_file() and os.access(entry, os.X_OK)


def check_mcp_registration() -> bool:
    if not os.path.isfile(CLAUDE_SETTINGS_PATH):
        return False
    try:
        with open(CLAUDE_SETTINGS_PATH) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False
    return "blender_mcp" in (data.get("mcpServers") or {})


def create_venv() -> None:
    """Create the venv if it doesn't exist. Raises on failure."""
    vdir = Path(VENV_DIR)
    if not vdir.exists():
        vdir.parent.mkdir(parents=True, exist_ok=True)
        venv.create(str(vdir), with_pip=True, clear=False)


def install_mcp_package() -> None:
    """pip install the blender_mcp package into the venv. Raises on failure."""
    create_venv()
    pip = Path(VENV_DIR) / "bin" / "pip"
    subprocess.run(
        [str(pip), "install", "--upgrade", MCP_GIT_URL],
        check=True,
    )


def register_mcp() -> None:
    """Add mcpServers.blender_mcp entry to ~/.claude/settings.json."""
    cfg_path = Path(CLAUDE_SETTINGS_PATH)
    if cfg_path.is_file():
        with open(cfg_path) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
    else:
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        data = {}

    mcp_servers = data.setdefault("mcpServers", {})
    mcp_servers["blender_mcp"] = {
        "command": str(Path(VENV_DIR) / "bin" / "blender-mcp"),
        "args": [],
        "env": {},
    }

    with open(cfg_path, "w") as f:
        json.dump(data, f, indent=2)


def cmd_status() -> int:
    result = {
        "blender_installed": check_blender_app(),
        "blender_path": MACOS_BLENDER_PATH if check_blender_app() else None,
        "mcp_venv": check_mcp_venv(),
        "venv_path": VENV_DIR,
        "mcp_registered": check_mcp_registration(),
        "settings_path": CLAUDE_SETTINGS_PATH,
    }
    print(json.dumps(result, indent=2))
    return 0


def cmd_install() -> int:
    if not check_blender_app():
        print(json.dumps({
            "status": "error",
            "error": "Blender.app not found. Install via: brew install --cask blender",
        }))
        return 1
    try:
        install_mcp_package()
    except subprocess.CalledProcessError as e:
        print(json.dumps({"status": "error", "error": f"pip install failed: {e}"}))
        return 1
    print(json.dumps({"status": "ok", "venv": VENV_DIR}))
    return 0


def cmd_register() -> int:
    try:
        register_mcp()
    except OSError as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        return 1
    print(json.dumps({"status": "ok", "settings": CLAUDE_SETTINGS_PATH}))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Blender setup for /print skill")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("install")
    sub.add_parser("register")
    args = parser.parse_args(argv)

    if args.cmd == "status":
        return cmd_status()
    if args.cmd == "install":
        return cmd_install()
    if args.cmd == "register":
        return cmd_register()
    return 2


if __name__ == "__main__":
    sys.exit(main())
