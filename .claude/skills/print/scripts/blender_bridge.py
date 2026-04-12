#!/usr/bin/env python3
"""Blender invocation bridge for the /print skill.

Single place that knows how to launch Blender in background mode. Used by every
Blender-backed orchestrator (blender_audit.py, blender_repair.py, blender_render.py,
blender_generate.py).

Invocation modes (preference order):
  1. Direct CLI via subprocess: `blender --background --python <script> -- <args>`
     — always available if Blender is installed
  2. MCP server's execute_blender_background tool — future enhancement, not used
     from this module directly (the MCP call path is handled by the LLM via
     tool use, not by Python). This module is the CLI fallback.

The blender_mcp package, when registered in ~/.claude/settings.json, gives the
LLM `execute_python` / `execute_blender_background` / `get_summary` tools
directly. Orchestrator scripts in this skill use the CLI path so they work
with or without MCP registration.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

MACOS_BLENDER_PATH = "/Applications/Blender.app/Contents/MacOS/Blender"
STDOUT_MARKER = "BLENDER_OK"


class BlenderNotFoundError(RuntimeError):
    """Raised when no Blender executable can be located."""


@dataclass
class BlenderRunResult:
    success: bool
    returncode: int
    stdout: str
    stderr: str
    marker_path: Optional[str]  # path parsed from the STDOUT_MARKER line

    def load_json(self) -> dict:
        """Read the marker path as JSON. Raises if marker is missing."""
        if not self.marker_path:
            raise RuntimeError("No marker path available")
        with open(self.marker_path) as f:
            return json.load(f)


def find_blender() -> str:
    """Return path to the Blender executable. Raises BlenderNotFoundError."""
    if os.path.isfile(MACOS_BLENDER_PATH) and os.access(MACOS_BLENDER_PATH, os.X_OK):
        return MACOS_BLENDER_PATH
    which = shutil.which("blender")
    if which:
        return which
    raise BlenderNotFoundError(
        "Blender not found. Install via: brew install --cask blender"
    )


def run_bpy_script(
    script_path: str,
    args: List[str],
    timeout: int = 120,
) -> BlenderRunResult:
    """Run a bpy script in headless Blender and return a result object.

    Args:
        script_path: path to a .py file containing bpy code
        args: list of positional args passed after `--` to the script
        timeout: subprocess timeout in seconds (default 120)

    Returns:
        BlenderRunResult with success flag, returncode, stdout, stderr,
        and (if found) marker_path parsed from the STDOUT_MARKER line.
    """
    if not os.path.isfile(script_path):
        raise FileNotFoundError(f"bpy script not found: {script_path}")

    blender = find_blender()
    cmd = [
        blender,
        "--background",
        "--factory-startup",
        "--python",
        script_path,
        "--",
        *args,
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        return BlenderRunResult(
            success=False,
            returncode=-1,
            stdout=e.stdout or "",
            stderr=(e.stderr or "") + f"\n[timeout after {timeout}s]",
            marker_path=None,
        )

    marker = _parse_marker(proc.stdout)
    success = proc.returncode == 0 and marker is not None

    return BlenderRunResult(
        success=success,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        marker_path=marker,
    )


def _parse_marker(stdout: str) -> Optional[str]:
    """Extract the path from the last `BLENDER_OK <path>` line in stdout."""
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith(STDOUT_MARKER + " "):
            return line[len(STDOUT_MARKER) + 1 :].strip()
    return None


if __name__ == "__main__":
    # Smoke test: just check that Blender is findable.
    try:
        path = find_blender()
        print(json.dumps({"status": "ok", "blender": path}))
    except BlenderNotFoundError as e:
        print(json.dumps({"status": "error", "error": str(e)}))
