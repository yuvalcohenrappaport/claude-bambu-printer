# Blender MCP Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the `/print` skill with Blender-backed generation (organic shapes), photo-quality hero renders, and mesh audit/repair on downloaded files, while keeping OpenSCAD as the default generation path and preserving the current skill's UX.

**Architecture:** Blender runs in background mode only (`blender --background --python <script> -- <args>`), invoked either via the official Blender MCP server's `execute_blender_background` tool or via direct CLI fallback. Every operation is one-shot: a `bpy` script is passed in, produces output (JSON, PNG, or 3MF), and the subprocess exits. Python orchestrator scripts in `scripts/` are called from SKILL.md via Bash, mirroring the existing `makerworld_search.py` / `printer_control.py` pattern.

**Tech Stack:** Blender 5.1 (already installed at `/Applications/Blender.app/Contents/MacOS/Blender`), `blender_mcp` Python package (installed in a dedicated venv at `~/.claude/skills/print/.venv-blender/`), Python 3 with `pytest` for orchestrator tests, `bmesh` + `bpy` for Blender-side logic.

**Repo context:** The `/print` skill lives in the `~/Documents/claude-bambulab-printer/` repo, exposed via symlink at `~/.claude/skills/print/`. All paths in this plan are relative to that repo root. There are uncommitted changes on `SKILL.md` and reference files at plan creation time — **execute this plan in a git worktree** so those changes stay untouched.

**Spec:** `.claude/skills/print/docs/specs/2026-04-12-blender-mcp-integration-design.md`

---

## Phase 1 — Foundation

Goal: install flow works, Blender can be invoked from Python, reference guide is in place, fixtures exist for the later phases. After Phase 1, no user-facing skill behavior has changed — it's groundwork.

### Task 1.1: Create `blender-guide.md` reference file

**Files:**
- Create: `.claude/skills/print/reference/blender-guide.md`

- [ ] **Step 1: Write the reference file**

Create `.claude/skills/print/reference/blender-guide.md` with the following content:

````markdown
# Blender Guide for the /print Skill

This file is loaded by SKILL.md via `@reference/blender-guide.md`. Use it when generating `model.py` files for Blender-backed models, or when writing ad-hoc `bpy` scripts for audit / repair / render.

## Invocation

Blender is invoked in background mode exclusively:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
    --background \
    --factory-startup \
    --python <script.py> \
    -- <arg1> <arg2> ...
```

Args after `--` are passed to the script as `sys.argv[sys.argv.index("--") + 1:]`. Blender's own args (file to open, `--factory-startup`) come before `--`.

Prefer `--factory-startup` to ignore the user's preferences and get a clean environment.

## Unit scale gotcha

Blender's default unit scale is **1 unit = 1 meter**. 3D printing files use millimeters. Two options:

1. **Leave the scene at default and multiply dimensions**: a 120mm cube becomes a 0.120 Blender-unit cube. Less code, but mental-model friction.
2. **Set unit scale to 0.001 at the top of every script**:

```python
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 0.001
```

With option 2, you write dimensions in mm directly. **This plan uses option 2 everywhere** for consistency with OpenSCAD.

## Scene reset pattern

Every one-shot script starts by clearing the default scene so it's idempotent:

```python
import bpy

# Delete everything
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Also clear orphaned data
for collection in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
    for item in collection:
        collection.remove(item)
```

## Importing files

| Format | Operator | Notes |
|---|---|---|
| STL | `bpy.ops.wm.stl_import(filepath=...)` | Blender 4.0+ moved this from `import_mesh.stl` (available in 5.x as well) |
| OBJ | `bpy.ops.wm.obj_import(filepath=...)` | Blender 5.1 name |
| 3MF | Varies by Blender version — verified at runtime by `scripts/bpy/probe_3mf.py` | May require a bundled extension enable |

If a 3MF operator is unavailable, convert the 3MF to STL externally (e.g., `meshio`) or ask the user to export as STL from BambuStudio.

## Exporting 3MF

Blender 5.1 ships a 3MF exporter but the operator name has changed across versions. Use the probe script result (stored at `~/.claude/skills/print/.blender-3mf-op.txt` after Phase 4 Task 4.1 runs) rather than hardcoding. If the cache file does not exist (e.g., the probe hasn't run yet in Phase 1 or 2), treat the operator as unavailable and use the STL fallback below. Fallback: export STL via `bpy.ops.wm.stl_export(filepath=...)` and convert externally with `meshio` if a 3MF is strictly required.

## Organic shape patterns

### Loft (skin a series of curve cross-sections)

```python
import bpy, bmesh
from math import cos, sin, pi

# Prerequisite: ensure unit scale is set before this block — see "Unit scale gotcha" section above.
# Dimensions below (z, r) are written in mm and assume scale_length = 0.001 has been applied.

bm = bmesh.new()
# Create 8 rings stacked along Z, each a circle of varying radius
rings = []
for i in range(8):
    z = i * 10  # mm
    r = 20 + 5 * sin(i * pi / 7)  # mm
    ring = []
    for j in range(24):
        theta = j * 2 * pi / 24
        v = bm.verts.new((r * cos(theta), r * sin(theta), z))
        ring.append(v)
    rings.append(ring)

# Side faces: quads between consecutive rings
for i in range(len(rings) - 1):
    a, b = rings[i], rings[i + 1]
    for j in range(24):
        bm.faces.new([a[j], a[(j + 1) % 24], b[(j + 1) % 24], b[j]])

# Cap top and bottom with a fan triangulation (avoids n-gons, stays manifold)
def cap_ring(ring, reverse=False):
    cx = sum(v.co.x for v in ring) / len(ring)
    cy = sum(v.co.y for v in ring) / len(ring)
    cz = sum(v.co.z for v in ring) / len(ring)
    center = bm.verts.new((cx, cy, cz))
    for j in range(len(ring)):
        tri = [center, ring[j], ring[(j + 1) % len(ring)]]
        if reverse:
            tri.reverse()
        bm.faces.new(tri)

cap_ring(rings[0], reverse=True)   # bottom — normal points -Z
cap_ring(rings[-1], reverse=False) # top — normal points +Z

me = bpy.data.meshes.new("loft")
bm.to_mesh(me)
bm.free()
obj = bpy.data.objects.new("loft", me)
bpy.context.collection.objects.link(obj)
```

### Subdivision-surface for smoothness

```python
bpy.context.view_layer.objects.active = obj
mod = obj.modifiers.new("subsurf", 'SUBSURF')
mod.levels = 2
mod.render_levels = 3
bpy.ops.object.modifier_apply(modifier="subsurf")
```

### Boolean CSG (faster than OpenSCAD for complex meshes)

```python
bpy.context.view_layer.objects.active = obj
mod = obj.modifiers.new("bool", 'BOOLEAN')
mod.object = other_obj
mod.operation = 'DIFFERENCE'
bpy.ops.object.modifier_apply(modifier="bool")
bpy.data.objects.remove(other_obj, do_unlink=True)
```

### Bevel edges (fillets for organic transitions)

```python
bpy.context.view_layer.objects.active = obj
mod = obj.modifiers.new("bevel", 'BEVEL')
mod.width = 1.0  # mm (with unit scale 0.001)
mod.segments = 4
bpy.ops.object.modifier_apply(modifier="bevel")
```

## Common error patterns

| Error text | Cause | Fix |
|---|---|---|
| `AttributeError: Calling operator "bpy.ops.wm.stl_import" error, could not be found` | Old operator name | Use `bpy.ops.import_mesh.stl` on Blender <4.0 |
| `RuntimeError: Operator bpy.ops.object.modifier_apply.poll() failed, context is incorrect` | No active object | `bpy.context.view_layer.objects.active = obj` before calling |
| `bmesh: vertices ... share an edge` (when creating faces) | Duplicate vert | Use `bmesh.ops.remove_doubles` first |
| Script runs but produces no output file | Missing `-- <output>` arg | Check `sys.argv` parsing |
| Non-manifold after boolean | Coplanar faces | Offset one object by 0.001mm before boolean |

## Exit codes and stdout

`bpy` scripts should:
1. Print a machine-readable success marker as the last stdout line, e.g., `BLENDER_OK <output_path>`.
2. Print errors to stderr (not stdout).
3. Call `sys.exit(1)` on unrecoverable errors so the subprocess returns non-zero.

Orchestrators in `scripts/` parse stdout for the marker and fall back to the returncode for error detection.
````

- [ ] **Step 2: Verify the file exists and is loadable**

Run: `ls -la .claude/skills/print/reference/blender-guide.md && head -5 .claude/skills/print/reference/blender-guide.md`
Expected: file exists, first few lines are the markdown header.

- [ ] **Step 3: Commit**

```bash
cd ~/Documents/claude-bambulab-printer
git add .claude/skills/print/reference/blender-guide.md
git commit -m "docs(print): add blender-guide.md reference for MCP integration"
```

---

### Task 1.2: Create `blender_bridge.py` helper module

**Files:**
- Create: `.claude/skills/print/scripts/blender_bridge.py`
- Create: `.claude/skills/print/tests/test_blender_bridge.py`
- Create: `.claude/skills/print/tests/__init__.py` (empty)

This module is the single place that knows how to invoke Blender. Every Blender-using orchestrator imports it. It handles MCP-vs-direct-CLI selection, path discovery, and subprocess exit/stdout parsing.

- [ ] **Step 1: Write the failing tests**

Create `.claude/skills/print/tests/__init__.py` (empty file) and `.claude/skills/print/tests/test_blender_bridge.py`:

```python
"""Unit tests for blender_bridge.py — mocked subprocess, no real Blender calls."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Path fudge so tests can import the script without installing it
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import blender_bridge  # noqa: E402


def test_find_blender_returns_macos_app_when_present(tmp_path, monkeypatch):
    fake_blender = tmp_path / "Blender.app/Contents/MacOS/Blender"
    fake_blender.parent.mkdir(parents=True)
    fake_blender.write_text("#!/bin/bash\necho fake\n")
    fake_blender.chmod(0o755)
    monkeypatch.setattr(blender_bridge, "MACOS_BLENDER_PATH", str(fake_blender))
    assert blender_bridge.find_blender() == str(fake_blender)


def test_find_blender_raises_when_not_installed(monkeypatch):
    monkeypatch.setattr(blender_bridge, "MACOS_BLENDER_PATH", "/nonexistent/Blender")
    with patch("shutil.which", return_value=None):
        with pytest.raises(blender_bridge.BlenderNotFoundError):
            blender_bridge.find_blender()


def test_run_bpy_script_success_parses_stdout_marker(tmp_path):
    script = tmp_path / "fake.py"
    script.write_text("print('BLENDER_OK /tmp/out.json')")

    fake_result = MagicMock(returncode=0,
                            stdout="some logs\nBLENDER_OK /tmp/out.json\n",
                            stderr="")
    with patch.object(blender_bridge, "find_blender", return_value="/fake/blender"):
        with patch("subprocess.run", return_value=fake_result) as mock_run:
            result = blender_bridge.run_bpy_script(str(script), ["/tmp/out.json"])

    assert result.success is True
    assert result.marker_path == "/tmp/out.json"
    assert result.returncode == 0
    called_cmd = mock_run.call_args[0][0]
    assert "--background" in called_cmd
    assert "--python" in called_cmd
    assert "--" in called_cmd
    assert "/tmp/out.json" in called_cmd


def test_run_bpy_script_nonzero_returncode_sets_success_false(tmp_path):
    script = tmp_path / "fake.py"
    script.write_text("import sys; sys.exit(1)")

    fake_result = MagicMock(returncode=1,
                            stdout="",
                            stderr="Traceback: ValueError: nope")
    with patch.object(blender_bridge, "find_blender", return_value="/fake/blender"):
        with patch("subprocess.run", return_value=fake_result):
            result = blender_bridge.run_bpy_script(str(script), [])

    assert result.success is False
    assert result.returncode == 1
    assert "ValueError: nope" in result.stderr


def test_run_bpy_script_missing_script_raises():
    with patch.object(blender_bridge, "find_blender", return_value="/fake/blender"):
        with pytest.raises(FileNotFoundError):
            blender_bridge.run_bpy_script("/nonexistent/script.py", [])


def test_json_marker_loads_output_file(tmp_path):
    out = tmp_path / "out.json"
    out.write_text(json.dumps({"k": "v"}))

    fake_result = MagicMock(returncode=0,
                            stdout=f"BLENDER_OK {out}\n",
                            stderr="")
    script = tmp_path / "s.py"
    script.write_text("# noop")
    with patch.object(blender_bridge, "find_blender", return_value="/fake/b"):
        with patch("subprocess.run", return_value=fake_result):
            result = blender_bridge.run_bpy_script(str(script), [str(out)])

    assert result.load_json() == {"k": "v"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/Documents/claude-bambulab-printer && python3 -m pytest .claude/skills/print/tests/test_blender_bridge.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'blender_bridge'` (or similar import error).

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/print/scripts/blender_bridge.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Documents/claude-bambulab-printer && python3 -m pytest .claude/skills/print/tests/test_blender_bridge.py -v`
Expected: all 6 tests PASS.

Also run the smoke test: `python3 .claude/skills/print/scripts/blender_bridge.py`
Expected: JSON output with `"status": "ok"` and the real Blender path.

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/claude-bambulab-printer
git add .claude/skills/print/scripts/blender_bridge.py .claude/skills/print/tests/__init__.py .claude/skills/print/tests/test_blender_bridge.py
git commit -m "feat(print): add blender_bridge.py with subprocess wrapper and tests"
```

---

### Task 1.3: Create `blender_setup.py` (install check + MCP registration)

**Files:**
- Create: `.claude/skills/print/scripts/blender_setup.py`
- Create: `.claude/skills/print/tests/test_blender_setup.py`

- [ ] **Step 1: Write the failing tests**

Create `.claude/skills/print/tests/test_blender_setup.py`:

```python
"""Unit tests for blender_setup.py — mocked filesystem and subprocess."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import blender_setup  # noqa: E402


def test_check_blender_app_present(tmp_path, monkeypatch):
    fake = tmp_path / "Blender.app/Contents/MacOS/Blender"
    fake.parent.mkdir(parents=True)
    fake.write_text("")
    fake.chmod(0o755)
    monkeypatch.setattr(blender_setup, "MACOS_BLENDER_PATH", str(fake))
    assert blender_setup.check_blender_app() is True


def test_check_blender_app_missing(monkeypatch):
    monkeypatch.setattr(blender_setup, "MACOS_BLENDER_PATH", "/nope")
    assert blender_setup.check_blender_app() is False


def test_check_mcp_venv_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(blender_setup, "VENV_DIR", str(tmp_path / "nonexistent"))
    assert blender_setup.check_mcp_venv() is False


def test_check_mcp_venv_present(tmp_path, monkeypatch):
    venv = tmp_path / "v"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "blender-mcp").write_text("")
    (venv / "bin" / "blender-mcp").chmod(0o755)
    monkeypatch.setattr(blender_setup, "VENV_DIR", str(venv))
    assert blender_setup.check_mcp_venv() is True


def test_check_mcp_registration_absent(tmp_path, monkeypatch):
    cfg = tmp_path / "settings.json"
    cfg.write_text(json.dumps({"other": "stuff"}))
    monkeypatch.setattr(blender_setup, "CLAUDE_SETTINGS_PATH", str(cfg))
    assert blender_setup.check_mcp_registration() is False


def test_check_mcp_registration_present(tmp_path, monkeypatch):
    cfg = tmp_path / "settings.json"
    cfg.write_text(json.dumps({"mcpServers": {"blender_mcp": {"command": "x"}}}))
    monkeypatch.setattr(blender_setup, "CLAUDE_SETTINGS_PATH", str(cfg))
    assert blender_setup.check_mcp_registration() is True


def test_check_mcp_registration_no_config_file(tmp_path, monkeypatch):
    monkeypatch.setattr(blender_setup, "CLAUDE_SETTINGS_PATH", str(tmp_path / "nope.json"))
    assert blender_setup.check_mcp_registration() is False


def test_register_mcp_adds_entry_to_existing_config(tmp_path, monkeypatch):
    cfg = tmp_path / "settings.json"
    cfg.write_text(json.dumps({"other": "stuff"}))
    monkeypatch.setattr(blender_setup, "CLAUDE_SETTINGS_PATH", str(cfg))
    monkeypatch.setattr(blender_setup, "VENV_DIR", "/fake/venv")

    blender_setup.register_mcp()

    data = json.loads(cfg.read_text())
    assert "mcpServers" in data
    assert "blender_mcp" in data["mcpServers"]
    assert data["mcpServers"]["blender_mcp"]["command"] == "/fake/venv/bin/blender-mcp"
    # Pre-existing keys preserved
    assert data["other"] == "stuff"


def test_register_mcp_creates_config_if_missing(tmp_path, monkeypatch):
    cfg = tmp_path / "settings.json"
    # File does not exist yet
    monkeypatch.setattr(blender_setup, "CLAUDE_SETTINGS_PATH", str(cfg))
    monkeypatch.setattr(blender_setup, "VENV_DIR", "/fake/venv")

    blender_setup.register_mcp()

    assert cfg.exists()
    data = json.loads(cfg.read_text())
    assert data["mcpServers"]["blender_mcp"]["command"] == "/fake/venv/bin/blender-mcp"


def test_status_subcommand_returns_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(blender_setup, "MACOS_BLENDER_PATH", "/nope")
    monkeypatch.setattr(blender_setup, "VENV_DIR", str(tmp_path / "v"))
    monkeypatch.setattr(blender_setup, "CLAUDE_SETTINGS_PATH", str(tmp_path / "s.json"))

    rc = blender_setup.main(["status"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["blender_installed"] is False
    assert data["mcp_venv"] is False
    assert data["mcp_registered"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/Documents/claude-bambulab-printer && python3 -m pytest .claude/skills/print/tests/test_blender_setup.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'blender_setup'`.

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/print/scripts/blender_setup.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Documents/claude-bambulab-printer && python3 -m pytest .claude/skills/print/tests/test_blender_setup.py -v`
Expected: all 10 tests PASS.

Smoke check against real system: `python3 .claude/skills/print/scripts/blender_setup.py status`
Expected: JSON with `blender_installed: true`, `mcp_venv: false`, `mcp_registered: false`.

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/claude-bambulab-printer
git add .claude/skills/print/scripts/blender_setup.py .claude/skills/print/tests/test_blender_setup.py
git commit -m "feat(print): add blender_setup.py for install check and MCP registration"
```

---

### Task 1.4: Create test fixtures and add Step 0a to SKILL.md

**Files:**
- Create: `.claude/skills/print/tests/fixtures/__init__.py` (empty)
- Create: `.claude/skills/print/tests/fixtures/make_fixtures.py`
- Create: `.claude/skills/print/tests/fixtures/cube.stl` (generated)
- Create: `.claude/skills/print/tests/fixtures/non_manifold.stl` (generated)
- Modify: `.claude/skills/print/SKILL.md` (add Step 0a)

- [ ] **Step 1: Write the fixture generator**

Create `.claude/skills/print/tests/fixtures/make_fixtures.py`:

```python
#!/usr/bin/env python3
"""Generate test fixtures for Blender audit/repair tests.

Outputs:
  cube.stl         — 20mm manifold cube (12 triangles)
  non_manifold.stl — same cube with one face removed (non-manifold edges)
  large.stl        — 1000 triangle "organic" blob for triangle-count tests
"""
from pathlib import Path
import struct

FIXTURES_DIR = Path(__file__).parent


def write_binary_stl(path: Path, triangles: list[tuple[tuple[float, float, float], ...]]) -> None:
    """Write a binary STL file from a list of (v1, v2, v3) triangles."""
    with open(path, "wb") as f:
        f.write(b"\x00" * 80)  # 80-byte header
        f.write(struct.pack("<I", len(triangles)))
        for tri in triangles:
            # Normal = (0, 0, 0) — slicer will recompute
            f.write(struct.pack("<fff", 0.0, 0.0, 0.0))
            for v in tri:
                f.write(struct.pack("<fff", *v))
            f.write(b"\x00\x00")  # attribute byte count


def cube_triangles(size: float = 20.0) -> list[tuple[tuple[float, float, float], ...]]:
    """12 triangles forming a manifold cube of the given edge length."""
    s = size
    # 8 corners
    v = [
        (0, 0, 0), (s, 0, 0), (s, s, 0), (0, s, 0),
        (0, 0, s), (s, 0, s), (s, s, s), (0, s, s),
    ]
    # 6 faces, 2 triangles each, CCW-from-outside
    return [
        # bottom (z=0)
        (v[0], v[2], v[1]), (v[0], v[3], v[2]),
        # top (z=s)
        (v[4], v[5], v[6]), (v[4], v[6], v[7]),
        # front (y=0)
        (v[0], v[1], v[5]), (v[0], v[5], v[4]),
        # right (x=s)
        (v[1], v[2], v[6]), (v[1], v[6], v[5]),
        # back (y=s)
        (v[2], v[3], v[7]), (v[2], v[7], v[6]),
        # left (x=0)
        (v[3], v[0], v[4]), (v[3], v[4], v[7]),
    ]


def make_cube():
    write_binary_stl(FIXTURES_DIR / "cube.stl", cube_triangles())


def make_non_manifold_cube():
    tris = cube_triangles()
    # Remove top face (2 triangles) — leaves 4 edges with only 1 linked face
    tris_open = [t for i, t in enumerate(tris) if i not in (2, 3)]
    write_binary_stl(FIXTURES_DIR / "non_manifold.stl", tris_open)


def make_large():
    # Generate a high-triangle-count "blob": subdivided icosphere-ish cube
    # Simple approach: 10x10x10 grid of tiny cubes = 6000 triangles
    tris = []
    for ix in range(10):
        for iy in range(10):
            for iz in range(10):
                ox, oy, oz = ix * 2.5, iy * 2.5, iz * 2.5
                for tri in cube_triangles(2.0):
                    shifted = tuple(
                        (v[0] + ox, v[1] + oy, v[2] + oz) for v in tri
                    )
                    tris.append(shifted)
    write_binary_stl(FIXTURES_DIR / "large.stl", tris)


if __name__ == "__main__":
    FIXTURES_DIR.mkdir(exist_ok=True)
    make_cube()
    make_non_manifold_cube()
    make_large()
    print(f"Fixtures written to {FIXTURES_DIR}")
```

- [ ] **Step 2: Run the fixture generator**

Run:
```bash
cd ~/Documents/claude-bambulab-printer
touch .claude/skills/print/tests/fixtures/__init__.py
python3 .claude/skills/print/tests/fixtures/make_fixtures.py
ls -la .claude/skills/print/tests/fixtures/
```
Expected: `cube.stl` (~684 bytes), `non_manifold.stl` (~584 bytes), `large.stl` (~500KB) files present.

- [ ] **Step 3: Edit SKILL.md to add Step 0a**

Open `.claude/skills/print/SKILL.md` and find the line `## Step 0: Detect Intent` (around line 26). Insert a new section **immediately before** it:

```markdown
## Step 0a: Check Blender Setup (runs lazily)

This step is **triggered on demand** — only when the user's request hits a Blender-backed branch (organic generation, hero render, or mesh audit/repair). It is NOT run at the start of every conversation.

Run the setup status script:

```bash
python3 ~/.claude/skills/print/scripts/blender_setup.py status
```

Parse the JSON output. Three flags:

1. `blender_installed: false` → Tell user: "Blender isn't installed. Install via `brew install --cask blender`?" If yes, run `brew install --cask blender` and re-check. If no, fall back to the OpenSCAD path for the current request.

2. `mcp_venv: false` → Tell user: "The Blender MCP Python package isn't installed yet. I'll create a venv at `~/.claude/skills/print/.venv-blender/` and install it — proceed?" If yes, run `python3 ~/.claude/skills/print/scripts/blender_setup.py install`. If no, continue without MCP (direct CLI fallback — still works, just no prompts.yml grounding).

3. `mcp_registered: false` → Tell user: "I can register the Blender MCP server in `~/.claude/settings.json` so future conversations can use `execute_python` / `execute_blender_background` tools directly. Proceed?" If yes, run `python3 ~/.claude/skills/print/scripts/blender_setup.py register`. If no, continue without registration (direct CLI fallback).

**Important:** flags 2 and 3 are **optional** — the skill's Blender branches work via direct CLI even when both are false. Only flag 1 (Blender itself) is a hard requirement.

After handling any missing pieces, continue to the step that triggered the check (generation, render, or validate).

---

```

- [ ] **Step 4: Verify SKILL.md still parses**

Run: `head -60 .claude/skills/print/SKILL.md | tail -40`
Expected: the new Step 0a section appears between the IMPORTANT RULES and `## Step 0: Detect Intent`.

Also re-run the existing tests to confirm nothing broke:
```bash
python3 -m pytest .claude/skills/print/tests/ -v
```
Expected: all tests still pass.

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/claude-bambulab-printer
git add .claude/skills/print/tests/fixtures/ .claude/skills/print/SKILL.md
git commit -m "feat(print): add test fixtures and Step 0a install check to SKILL.md"
```

---

## Phase 2 — Mesh Validation & Repair

Goal: Users can audit any 3MF/STL/OBJ file, downloaded MakerWorld models are audited automatically, and repairs are offered with a confirmation gate and backup.

### Task 2.1: Create `bpy/audit.py` and smoke-test it

**Files:**
- Create: `.claude/skills/print/scripts/bpy/__init__.py` (empty)
- Create: `.claude/skills/print/scripts/bpy/audit.py`
- Create: `.claude/skills/print/tests/test_bpy_audit_integration.py`

- [ ] **Step 1: Write the integration test**

Create `.claude/skills/print/tests/test_bpy_audit_integration.py`:

```python
"""Integration tests for bpy/audit.py — runs real Blender against fixture STLs.

Marked @pytest.mark.integration so they're opt-in: run with `pytest -m integration`.
Each test is ~5-15s because Blender startup is slow.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
BPY_AUDIT = ROOT / "scripts" / "bpy" / "audit.py"
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"


def run_audit(input_file: Path, output_json: Path) -> subprocess.CompletedProcess:
    cmd = [
        BLENDER,
        "--background",
        "--factory-startup",
        "--python",
        str(BPY_AUDIT),
        "--",
        str(input_file),
        str(output_json),
    ]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)


@pytest.mark.integration
def test_audit_cube_is_manifold(tmp_path):
    out = tmp_path / "audit.json"
    proc = run_audit(FIXTURES / "cube.stl", out)
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    assert "BLENDER_OK" in proc.stdout

    result = json.loads(out.read_text())
    assert result["non_manifold_edges"] == 0
    assert result["triangle_count"] == 12
    # Cube is 20mm on a side
    dims = result["dimensions_mm"]
    assert all(abs(d - 20.0) < 0.01 for d in dims), f"dims: {dims}"
    assert result["issues"] == []


@pytest.mark.integration
def test_audit_non_manifold_flags_edges(tmp_path):
    out = tmp_path / "audit.json"
    proc = run_audit(FIXTURES / "non_manifold.stl", out)
    assert proc.returncode == 0

    result = json.loads(out.read_text())
    # Cube with top face removed → 4 edges now have only 1 linked face
    assert result["non_manifold_edges"] == 4
    assert result["triangle_count"] == 10
    assert any("non-manifold" in issue for issue in result["issues"])


@pytest.mark.integration
def test_audit_large_triangle_count_reported(tmp_path):
    out = tmp_path / "audit.json"
    proc = run_audit(FIXTURES / "large.stl", out)
    assert proc.returncode == 0

    result = json.loads(out.read_text())
    assert result["triangle_count"] == 12000  # 1000 cubes * 12 tris
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd ~/Documents/claude-bambulab-printer && python3 -m pytest .claude/skills/print/tests/test_bpy_audit_integration.py -v -m integration`
Expected: FAIL — `BPY_AUDIT` file does not exist, Blender returns non-zero with "Cannot find python file" error.

- [ ] **Step 3: Write the bpy audit script**

Create `.claude/skills/print/scripts/bpy/__init__.py` (empty file), then create `.claude/skills/print/scripts/bpy/audit.py`:

```python
"""Headless Blender mesh audit script.

Run via: blender --background --python audit.py -- <input_file> <output_json>

Imports the mesh file, runs checks, writes a JSON report to <output_json>,
and prints `BLENDER_OK <output_json>` to stdout on success.

Checks:
  - non_manifold_edges: count of edges with != 2 linked faces
  - triangle_count: total triangles after triangulation
  - dimensions_mm: [x, y, z] bounding box in millimeters
  - flipped_normals: best-effort count of faces with inverted normals
  - issues: list of human-readable problem descriptions
"""

import json
import sys
from pathlib import Path

import bpy
import bmesh


def parse_args():
    """Extract args passed after `--` on the blender CLI."""
    if "--" not in sys.argv:
        raise SystemExit("Usage: blender -b -P audit.py -- <input> <output_json>")
    idx = sys.argv.index("--")
    args = sys.argv[idx + 1 :]
    if len(args) < 2:
        raise SystemExit("Usage: ... -- <input> <output_json>")
    return args[0], args[1]


def reset_scene():
    """Clear default scene and all data blocks."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for item in list(coll):
            coll.remove(item)


def set_mm_units():
    """Switch scene to 1 unit = 1 mm."""
    u = bpy.context.scene.unit_settings
    u.system = "METRIC"
    u.scale_length = 0.001


def import_mesh_file(filepath: str):
    """Dispatch to the right importer based on extension."""
    ext = filepath.lower().rsplit(".", 1)[-1]
    if ext == "stl":
        # Blender 5.1 operator
        try:
            bpy.ops.wm.stl_import(filepath=filepath)
        except AttributeError:
            bpy.ops.import_mesh.stl(filepath=filepath)
    elif ext == "obj":
        try:
            bpy.ops.wm.obj_import(filepath=filepath)
        except AttributeError:
            bpy.ops.import_scene.obj(filepath=filepath)
    elif ext == "3mf":
        # 3MF import is version-dependent; try several known operator names
        importers = [
            lambda: bpy.ops.import_mesh.threemf(filepath=filepath),
            lambda: bpy.ops.wm.threemf_import(filepath=filepath),
        ]
        last_err = None
        for fn in importers:
            try:
                fn()
                break
            except AttributeError as e:
                last_err = e
                continue
        else:
            raise RuntimeError(
                f"No 3MF import operator available in this Blender. "
                f"Last error: {last_err}"
            )
    else:
        raise ValueError(f"Unsupported format: .{ext}")


def join_mesh_objects():
    """If multiple mesh objects were imported, join them into one."""
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("No mesh objects found after import")
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.select_all(action="DESELECT")
    for m in meshes:
        m.select_set(True)
    if len(meshes) > 1:
        bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def count_flipped_normals(bm: bmesh.types.BMesh) -> int:
    """Count faces whose normal was flipped when recalculated-outside was applied.

    Strategy: record pre-recalc normals, run recalc, compare dot-products.
    """
    pre_normals = [f.normal.copy() for f in bm.faces]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    flipped = 0
    for f, pre in zip(bm.faces, pre_normals):
        if f.normal.dot(pre) < 0:
            flipped += 1
    return flipped


def audit(filepath: str) -> dict:
    reset_scene()
    set_mm_units()
    import_mesh_file(filepath)
    obj = join_mesh_objects()

    # Ensure we're in object mode and mesh data is fresh
    bpy.ops.object.mode_set(mode="OBJECT")

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)

    non_manifold_edges = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    triangle_count = len(bm.faces)
    flipped_normals = count_flipped_normals(bm)

    # obj.dimensions is in scene units (mm, since we set scale_length = 0.001
    # AND the STL importer reads the file's raw numbers as units — so a 20mm
    # cube in the STL becomes 20 Blender-units, which is 20mm after scale).
    dims = [round(obj.dimensions[i], 3) for i in range(3)]

    bm.free()

    issues = []
    if non_manifold_edges > 0:
        issues.append(f"{non_manifold_edges} non-manifold edges")
    if flipped_normals > 0:
        issues.append(f"{flipped_normals} flipped normals")
    if triangle_count > 500_000:
        issues.append(f"high triangle count ({triangle_count}) — slicer may be slow")

    return {
        "file": filepath,
        "dimensions_mm": dims,
        "triangle_count": triangle_count,
        "non_manifold_edges": non_manifold_edges,
        "flipped_normals": flipped_normals,
        "issues": issues,
    }


def main():
    input_file, output_json = parse_args()
    try:
        result = audit(input_file)
    except Exception as e:
        # Any exception: write error JSON and exit non-zero.
        err_result = {"file": input_file, "error": str(e)}
        Path(output_json).write_text(json.dumps(err_result, indent=2))
        print(f"BLENDER_ERROR {e}", file=sys.stderr)
        sys.exit(1)

    Path(output_json).write_text(json.dumps(result, indent=2))
    print(f"BLENDER_OK {output_json}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the integration test to verify it passes**

Run:
```bash
cd ~/Documents/claude-bambulab-printer
python3 -m pytest .claude/skills/print/tests/test_bpy_audit_integration.py -v -m integration
```
Expected: 3 tests PASS. Each takes ~5-15s because of Blender startup.

**If the 3MF import test fails** (when we eventually feed it a 3MF): that's the expected "operator name not yet verified" gap — Phase 4 Task 4.1 resolves this with an explicit probe. For Phase 2, STL fixtures are enough.

**If the dimensions test fails**: the STL import's unit scale interpretation differs between Blender versions. Check `obj.dimensions` in the actual output JSON — if it reports 0.02 instead of 20.0, the fix is multiplying by 1000 in `audit()` (the scene unit scale doesn't affect raw STL numbers, only display). Update the `dims = ...` line to:

```python
dims = [round(obj.dimensions[i] * 1000, 3) for i in range(3)]
```

Then re-run the test.

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/claude-bambulab-printer
git add .claude/skills/print/scripts/bpy/__init__.py .claude/skills/print/scripts/bpy/audit.py .claude/skills/print/tests/test_bpy_audit_integration.py
git commit -m "feat(print): add bpy audit script with integration tests"
```

---

### Task 2.2: Create `blender_audit.py` orchestrator

**Files:**
- Create: `.claude/skills/print/scripts/blender_audit.py`
- Create: `.claude/skills/print/tests/test_blender_audit.py`

The orchestrator is a thin CLI around `blender_bridge.run_bpy_script` that the SKILL.md calls from Bash. It handles arg parsing, tmpfile management, and JSON formatting.

- [ ] **Step 1: Write the failing tests**

Create `.claude/skills/print/tests/test_blender_audit.py`:

```python
"""Unit tests for blender_audit.py — mocked blender_bridge, no real Blender."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import blender_audit  # noqa: E402
import blender_bridge  # noqa: E402


def make_fake_result(success=True, data=None, stderr=""):
    """Build a BlenderRunResult-like object with a load_json that returns `data`."""
    r = MagicMock()
    r.success = success
    r.returncode = 0 if success else 1
    r.stdout = "BLENDER_OK /tmp/x.json\n" if success else ""
    r.stderr = stderr
    r.marker_path = "/tmp/x.json" if success else None
    r.load_json = MagicMock(return_value=data or {})
    return r


def test_audit_returns_ok_json_on_clean_cube(tmp_path, capsys):
    fake = make_fake_result(success=True, data={
        "file": "/tmp/cube.stl",
        "dimensions_mm": [20.0, 20.0, 20.0],
        "triangle_count": 12,
        "non_manifold_edges": 0,
        "flipped_normals": 0,
        "issues": [],
    })
    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        rc = blender_audit.main(["/tmp/cube.stl"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"
    assert out["result"]["triangle_count"] == 12
    assert out["needs_repair"] is False


def test_audit_sets_needs_repair_when_issues_present(tmp_path, capsys):
    fake = make_fake_result(success=True, data={
        "file": "/tmp/bad.stl",
        "dimensions_mm": [20.0, 20.0, 20.0],
        "triangle_count": 10,
        "non_manifold_edges": 4,
        "flipped_normals": 0,
        "issues": ["4 non-manifold edges"],
    })
    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        rc = blender_audit.main(["/tmp/bad.stl"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"
    assert out["needs_repair"] is True
    assert out["result"]["non_manifold_edges"] == 4


def test_audit_returns_error_on_blender_failure(tmp_path, capsys):
    fake = make_fake_result(success=False, stderr="ImportError: bpy not found")
    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        rc = blender_audit.main(["/tmp/x.stl"])
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"
    assert "ImportError" in out["error"]


def test_audit_missing_input_file_returns_error(capsys):
    rc = blender_audit.main(["/nonexistent/file.stl"])
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"
    assert "not found" in out["error"].lower()


def test_needs_repair_flags_only_fixable_issues():
    # Advisory-only issues (triangle count, thin walls) should NOT trigger repair
    assert blender_audit.needs_repair({
        "non_manifold_edges": 0,
        "flipped_normals": 0,
        "issues": ["high triangle count (800000)"],
    }) is False
    # Non-manifold should
    assert blender_audit.needs_repair({
        "non_manifold_edges": 4,
        "flipped_normals": 0,
        "issues": ["4 non-manifold edges"],
    }) is True
    # Flipped normals should
    assert blender_audit.needs_repair({
        "non_manifold_edges": 0,
        "flipped_normals": 2,
        "issues": ["2 flipped normals"],
    }) is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/Documents/claude-bambulab-printer && python3 -m pytest .claude/skills/print/tests/test_blender_audit.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'blender_audit'`.

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/print/scripts/blender_audit.py`:

```python
#!/usr/bin/env python3
"""Mesh audit orchestrator for the /print skill.

Usage: blender_audit.py <input_file>

Wraps scripts/bpy/audit.py. Parses Blender's JSON output and emits a
skill-friendly JSON report with a top-level status flag and `needs_repair`
boolean that the SKILL.md uses to decide whether to offer repair.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

SCRIPT_DIR = Path(__file__).parent
BPY_AUDIT = SCRIPT_DIR / "bpy" / "audit.py"

sys.path.insert(0, str(SCRIPT_DIR))
import blender_bridge  # noqa: E402


def needs_repair(result: dict) -> bool:
    """Return True if the audit found fixable issues that warrant offering repair.

    Advisory-only issues (triangle count, bounding box, thin walls) do NOT
    count — those are informational and the file is still printable.
    """
    if result.get("non_manifold_edges", 0) > 0:
        return True
    if result.get("flipped_normals", 0) > 0:
        return True
    # self-intersection will be added in a future iteration
    return False


def audit_file(input_file: str) -> dict:
    """Run the bpy audit on a file. Returns a skill-ready JSON dict."""
    if not os.path.isfile(input_file):
        return {
            "status": "error",
            "error": f"Input file not found: {input_file}",
        }

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        output_json = tf.name

    try:
        run = blender_bridge.run_bpy_script(
            str(BPY_AUDIT),
            [input_file, output_json],
            timeout=60,
        )
        if not run.success:
            return {
                "status": "error",
                "error": run.stderr.strip() or f"Blender exited {run.returncode}",
            }
        result = run.load_json()
        return {
            "status": "ok",
            "result": result,
            "needs_repair": needs_repair(result),
        }
    finally:
        try:
            os.unlink(output_json)
        except OSError:
            pass


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a 3D mesh file for print readiness")
    parser.add_argument("input", help="Path to .stl, .obj, or .3mf file")
    args = parser.parse_args(argv)

    report = audit_file(args.input)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Documents/claude-bambulab-printer && python3 -m pytest .claude/skills/print/tests/test_blender_audit.py -v`
Expected: all 5 tests PASS.

End-to-end smoke (real Blender on real fixture):
```bash
python3 .claude/skills/print/scripts/blender_audit.py .claude/skills/print/tests/fixtures/cube.stl
```
Expected: JSON with `"status": "ok"`, `"needs_repair": false`, dimensions around 20×20×20.

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/claude-bambulab-printer
git add .claude/skills/print/scripts/blender_audit.py .claude/skills/print/tests/test_blender_audit.py
git commit -m "feat(print): add blender_audit.py orchestrator with unit tests"
```

---

### Task 2.3: Create `bpy/repair.py` and `blender_repair.py` orchestrator

**Files:**
- Create: `.claude/skills/print/scripts/bpy/repair.py`
- Create: `.claude/skills/print/scripts/blender_repair.py`
- Create: `.claude/skills/print/tests/test_blender_repair.py`
- Create: `.claude/skills/print/tests/test_bpy_repair_integration.py`

- [ ] **Step 1: Write the failing tests**

Create `.claude/skills/print/tests/test_blender_repair.py`:

```python
"""Unit tests for blender_repair.py — mocked subprocess, no real Blender."""

import json
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import blender_repair  # noqa: E402
import blender_bridge  # noqa: E402


def test_repair_creates_backup_before_editing(tmp_path):
    target = tmp_path / "model.stl"
    target.write_bytes(b"original binary stl data")

    fake = MagicMock()
    fake.success = True
    fake.returncode = 0
    fake.stderr = ""
    fake.marker_path = None  # repair writes in place, no JSON

    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        result = blender_repair.repair_file(str(target))

    assert result["status"] == "ok"
    backup = target.with_suffix(target.suffix + ".original")
    assert backup.exists()
    assert backup.read_bytes() == b"original binary stl data"


def test_repair_does_not_double_backup(tmp_path):
    target = tmp_path / "model.stl"
    target.write_bytes(b"v2 content")
    backup = target.with_suffix(target.suffix + ".original")
    backup.write_bytes(b"original v1 content")

    fake = MagicMock(success=True, returncode=0, stderr="", marker_path=None)
    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        blender_repair.repair_file(str(target))

    # Backup should still hold the v1 content, not v2 — we preserve the first original
    assert backup.read_bytes() == b"original v1 content"


def test_repair_propagates_blender_error(tmp_path, capsys):
    target = tmp_path / "model.stl"
    target.write_bytes(b"data")

    fake = MagicMock(success=False, returncode=1,
                     stderr="RuntimeError: cannot repair non-mesh",
                     marker_path=None)
    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        result = blender_repair.repair_file(str(target))

    assert result["status"] == "error"
    assert "cannot repair" in result["error"]


def test_cli_missing_input_returns_error(capsys):
    rc = blender_repair.main(["/nonexistent/x.stl"])
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"
```

Create `.claude/skills/print/tests/test_bpy_repair_integration.py`:

```python
"""Integration test: repair a non-manifold cube and verify it becomes manifold."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
BPY_REPAIR = ROOT / "scripts" / "bpy" / "repair.py"
BPY_AUDIT = ROOT / "scripts" / "bpy" / "audit.py"
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"


def run_bpy(script: Path, *args) -> subprocess.CompletedProcess:
    cmd = [BLENDER, "--background", "--factory-startup", "--python", str(script), "--", *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)


@pytest.mark.integration
def test_repair_closes_non_manifold_cube(tmp_path):
    # Copy fixture so we don't mutate the checked-in file
    work = tmp_path / "non_manifold.stl"
    shutil.copy(FIXTURES / "non_manifold.stl", work)

    # Pre-audit: should find non-manifold edges
    audit_out = tmp_path / "pre.json"
    proc = run_bpy(BPY_AUDIT, str(work), str(audit_out))
    assert proc.returncode == 0, f"pre-audit failed: {proc.stderr}"
    pre = json.loads(audit_out.read_text())
    assert pre["non_manifold_edges"] > 0

    # Run repair
    proc = run_bpy(BPY_REPAIR, str(work))
    assert proc.returncode == 0, f"repair failed: {proc.stderr}"
    assert "BLENDER_OK" in proc.stdout

    # Post-audit: should be manifold
    post_out = tmp_path / "post.json"
    proc = run_bpy(BPY_AUDIT, str(work), str(post_out))
    assert proc.returncode == 0, f"post-audit failed: {proc.stderr}"
    post = json.loads(post_out.read_text())
    assert post["non_manifold_edges"] == 0, f"still non-manifold: {post}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/Documents/claude-bambulab-printer && python3 -m pytest .claude/skills/print/tests/test_blender_repair.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'blender_repair'`.

- [ ] **Step 3: Write `bpy/repair.py` and `blender_repair.py`**

Create `.claude/skills/print/scripts/bpy/repair.py`:

```python
"""Headless Blender mesh repair script.

Run via: blender --background --python repair.py -- <input_file>

Imports the mesh, runs a sequence of cleanup operations, and writes the
repaired result back to <input_file> in the same format.

Operations:
  1. Merge by distance (threshold 0.001mm) — remove duplicate verts
  2. Recalculate normals outside — fix flipped normals
  3. Fill holes (max edges 4) — close small gaps that cause non-manifold
  4. Delete loose geometry — isolated verts/edges that aren't part of any face

The caller is responsible for backing up the original file before invoking
this script.
"""

import sys
from pathlib import Path

import bpy
import bmesh


def parse_args():
    if "--" not in sys.argv:
        raise SystemExit("Usage: blender -b -P repair.py -- <input_file>")
    idx = sys.argv.index("--")
    args = sys.argv[idx + 1 :]
    if len(args) < 1:
        raise SystemExit("Usage: ... -- <input_file>")
    return args[0]


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for item in list(coll):
            coll.remove(item)


def import_mesh(filepath: str):
    ext = filepath.lower().rsplit(".", 1)[-1]
    if ext == "stl":
        try:
            bpy.ops.wm.stl_import(filepath=filepath)
        except AttributeError:
            bpy.ops.import_mesh.stl(filepath=filepath)
    elif ext == "obj":
        try:
            bpy.ops.wm.obj_import(filepath=filepath)
        except AttributeError:
            bpy.ops.import_scene.obj(filepath=filepath)
    elif ext == "3mf":
        try:
            bpy.ops.import_mesh.threemf(filepath=filepath)
        except AttributeError:
            raise RuntimeError("3MF import not available — convert to STL first")
    else:
        raise ValueError(f"Unsupported format: .{ext}")


def export_mesh(filepath: str):
    ext = filepath.lower().rsplit(".", 1)[-1]
    # Select the mesh object(s)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for m in meshes:
        m.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]

    if ext == "stl":
        try:
            bpy.ops.wm.stl_export(filepath=filepath, export_selected_objects=True)
        except AttributeError:
            bpy.ops.export_mesh.stl(filepath=filepath, use_selection=True)
    elif ext == "obj":
        try:
            bpy.ops.wm.obj_export(filepath=filepath, export_selected_objects=True)
        except AttributeError:
            bpy.ops.export_scene.obj(filepath=filepath, use_selection=True)
    elif ext == "3mf":
        # version-dependent — fail loudly rather than silently corrupting
        raise RuntimeError("3MF export for repaired files not supported yet — STL only")
    else:
        raise ValueError(f"Unsupported format: .{ext}")


def join_mesh_objects():
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("No mesh to repair")
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.select_all(action="DESELECT")
    for m in meshes:
        m.select_set(True)
    if len(meshes) > 1:
        bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def repair_mesh(obj):
    """Apply the repair operations in order. Must be called in object mode."""
    # Enter edit mode to use mesh operators
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")

    # 1. Merge by distance (threshold 1 micrometer in scene units)
    bpy.ops.mesh.remove_doubles(threshold=0.001)

    # 2. Recalculate normals outside
    bpy.ops.mesh.normals_make_consistent(inside=False)

    # 3. Fill holes (max 4-edge holes)
    bpy.ops.mesh.fill_holes(sides=4)

    # 4. Delete loose geometry (verts/edges not part of any face)
    bpy.ops.mesh.delete_loose()

    bpy.ops.object.mode_set(mode="OBJECT")


def main():
    filepath = parse_args()
    try:
        reset_scene()
        import_mesh(filepath)
        obj = join_mesh_objects()
        repair_mesh(obj)
        export_mesh(filepath)
    except Exception as e:
        print(f"BLENDER_ERROR {e}", file=sys.stderr)
        sys.exit(1)
    print(f"BLENDER_OK {filepath}")


if __name__ == "__main__":
    main()
```

Create `.claude/skills/print/scripts/blender_repair.py`:

```python
#!/usr/bin/env python3
"""Mesh repair orchestrator for the /print skill.

Usage: blender_repair.py <input_file>

Backs up the input file as `<input>.original` (only if no backup exists yet),
then runs scripts/bpy/repair.py against the file in place.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import List, Optional

SCRIPT_DIR = Path(__file__).parent
BPY_REPAIR = SCRIPT_DIR / "bpy" / "repair.py"

sys.path.insert(0, str(SCRIPT_DIR))
import blender_bridge  # noqa: E402


def backup_original(filepath: str) -> str:
    """Copy `filepath` to `<filepath>.original` if no backup exists. Return backup path."""
    backup = f"{filepath}.original"
    if not os.path.exists(backup):
        shutil.copy2(filepath, backup)
    return backup


def repair_file(filepath: str) -> dict:
    if not os.path.isfile(filepath):
        return {"status": "error", "error": f"Input file not found: {filepath}"}

    backup = backup_original(filepath)

    run = blender_bridge.run_bpy_script(str(BPY_REPAIR), [filepath], timeout=120)
    if run.returncode != 0:
        return {
            "status": "error",
            "error": run.stderr.strip() or f"Blender exited {run.returncode}",
            "backup": backup,
        }

    return {
        "status": "ok",
        "file": filepath,
        "backup": backup,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Repair a 3D mesh file in place")
    parser.add_argument("input", help="Path to .stl or .obj file")
    args = parser.parse_args(argv)

    result = repair_file(args.input)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run unit tests:
```bash
cd ~/Documents/claude-bambulab-printer
python3 -m pytest .claude/skills/print/tests/test_blender_repair.py -v
```
Expected: 4 tests PASS.

Run integration test (real Blender):
```bash
python3 -m pytest .claude/skills/print/tests/test_bpy_repair_integration.py -v -m integration
```
Expected: 1 test PASSES — non-manifold cube becomes manifold after repair.

End-to-end smoke:
```bash
cp .claude/skills/print/tests/fixtures/non_manifold.stl /tmp/bad.stl
python3 .claude/skills/print/scripts/blender_repair.py /tmp/bad.stl
ls -la /tmp/bad.stl /tmp/bad.stl.original
python3 .claude/skills/print/scripts/blender_audit.py /tmp/bad.stl
```
Expected: repair returns ok, backup exists, post-repair audit shows `non_manifold_edges: 0`.

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/claude-bambulab-printer
git add .claude/skills/print/scripts/bpy/repair.py .claude/skills/print/scripts/blender_repair.py .claude/skills/print/tests/test_blender_repair.py .claude/skills/print/tests/test_bpy_repair_integration.py
git commit -m "feat(print): add bpy repair script and orchestrator with tests"
```

---

### Task 2.4: Integrate audit/repair into SKILL.md (Step S3 hook + Step V1/V2)

**Files:**
- Modify: `.claude/skills/print/SKILL.md`

- [ ] **Step 1: Add validate intent to Step 0**

Open `.claude/skills/print/SKILL.md`. Find the `## Step 0: Detect Intent` section. Inside it, locate the `**Printer indicators**` block and add a new **Validate indicators** block immediately after it:

Insert after the printer indicators list (before the "Ambiguous" block):

```markdown
**Validate indicators** (trigger validate flow -- Steps V1-V2):
- "check", "audit", "validate", "inspect", "is this printable", "is this file ok", "mesh check", "non-manifold", "will this print"
```

Then in the **Routing:** list at the bottom of Step 0, add a new line:

```markdown
- Validate intent detected --> go to **Step V1** (validate flow). Requires Step 0a (Blender setup check) first.
```

And in the existing printer routing block, the routing table should have `validate` as a fifth option.

- [ ] **Step 2: Add Step S3 audit hook**

Find the `### Step S3: Download Selected Model` heading in SKILL.md. At the **end** of that section, after the "Notes for downloaded models:" block, insert:

```markdown
**Automatic mesh audit (new):** Before proceeding to Step 8, run the audit on the first 3MF/STL file that was downloaded:

1. Trigger Step 0a (Blender setup check) if not already completed in this session.
2. Run: `python3 ~/.claude/skills/print/scripts/blender_audit.py "<downloaded_file_path>"`
3. Parse the JSON. The `result` object has `dimensions_mm`, `triangle_count`, `non_manifold_edges`, `flipped_normals`, and `issues`.

Present the audit inline with the download summary:

```
Mesh audit:
  Dimensions: 118 × 76 × 44 mm
  Triangles:  84,230
  Manifold:   ✓ yes
  Normals:    ✓ consistent
```

If the JSON has `"needs_repair": true`, show the issues and immediately offer repair (go to **Step V2**). If `needs_repair` is false but there are advisory-only issues (high triangle count, etc.), list them as informational and continue to Step 8.

**If the audit fails** (status: error): do NOT block the download flow. Show a one-line warning: "Couldn't audit this file — [error]. Proceeding anyway." and continue to Step 8.
```

- [ ] **Step 3: Add Step V1 and Step V2 to SKILL.md**

Find the end of the Printer Flow section (after Step P5). Insert a new section:

````markdown
---

## Validate Flow (Steps V1-V2)

### Step V1: Run Mesh Audit

Triggered by validate intent in Step 0, or automatically from the Step S3 download hook.

**Prerequisites:** Step 0a (Blender setup check) must have been run. If not, run it now — audit needs Blender installed, but MCP/venv are optional.

**Determine the target file:**
- If invoked from S3: use the downloaded file path.
- If invoked by user intent: parse the file path from their message, or ask: "Which file should I audit? (.stl, .obj, or .3mf path)"

**Run the audit:**
```bash
python3 ~/.claude/skills/print/scripts/blender_audit.py "<file_path>"
```

Parse the JSON output.

**If status is "error":** Show the error to the user. Offer to try a different file. Stop.

**If status is "ok":** Present the audit as a formatted summary:

```
Mesh audit: <filename>
  Dimensions: <x> × <y> × <z> mm  [fits build plate: 256 × 256 × 256]
  Triangles:  <count>
  Manifold:   ✓ yes  (or ⚠ N non-manifold edges)
  Normals:    ✓ consistent  (or ⚠ N flipped)
```

Build-plate fit check: compare each dimension to 256mm (Bambu A1). If any dim > 256, add a line: `⚠ Exceeds Bambu A1 build plate — rotate or scale before printing.`

**If `needs_repair` is true:** go to **Step V2** automatically (but still confirm with user first).

**If `needs_repair` is false but issues list is non-empty:** show issues as advisory, do not offer repair.

**If no issues at all:** say "This file looks clean — manifold, consistent normals, fits the build plate."

### Step V2: Repair (conditional)

Only offered when Step V1 / Step S3 audit flagged fixable issues (non-manifold edges, flipped normals).

Show the repair prompt:

```
Found: <N> non-manifold edges, <M> flipped normals.

Want me to run Blender's cleanup on this file?
  • merge-by-distance (threshold 0.001mm)
  • recalculate normals outside
  • fill holes (max 4 edges)
  • delete loose geometry
Original file will be preserved as `<filename>.original`.
```

**Wait for user confirmation.** Do not auto-repair.

If user confirms:

1. Run: `python3 ~/.claude/skills/print/scripts/blender_repair.py "<file_path>"`
2. Parse JSON. If status is "error", show the error and stop.
3. If status is "ok", re-run the audit (Step V1) on the now-repaired file to show before/after.
4. Present the diff:

```
Repair complete. Backup: <filename>.original

Before:  4 non-manifold edges, 0 flipped normals
After:   0 non-manifold edges, 0 flipped normals
```

If the user declines repair: do nothing, just leave the advisory in place.
````

- [ ] **Step 4: Update the reference files list at the bottom of SKILL.md**

Find the `## Reference Files` section. Append new entries after the existing `@scripts/printer_control.py` line:

```markdown
- @reference/blender-guide.md -- Blender bpy patterns for organic shapes, 3MF export incantation, CLI reference, common error patterns
- @scripts/blender_setup.py -- Blender install check, venv management, MCP registration
- @scripts/blender_bridge.py -- Shared Blender subprocess wrapper used by all Blender orchestrators
- @scripts/blender_audit.py -- Mesh audit CLI (manifold check, normals, dimensions, triangles)
- @scripts/blender_repair.py -- Mesh repair CLI with backup
```

- [ ] **Step 5: Smoke test end-to-end and commit**

Verify the SKILL.md edits parse and scripts still work:

```bash
cd ~/Documents/claude-bambulab-printer

# Verify the new sections are present
grep -A 2 "Step V1" .claude/skills/print/SKILL.md | head -20
grep -A 2 "Step V2" .claude/skills/print/SKILL.md | head -10
grep "blender_audit.py" .claude/skills/print/SKILL.md
grep "blender_repair.py" .claude/skills/print/SKILL.md

# Re-run all unit tests to confirm nothing broke
python3 -m pytest .claude/skills/print/tests/ -v --ignore=.claude/skills/print/tests/test_bpy_audit_integration.py --ignore=.claude/skills/print/tests/test_bpy_repair_integration.py

# End-to-end smoke: audit a real file
python3 .claude/skills/print/scripts/blender_audit.py .claude/skills/print/tests/fixtures/non_manifold.stl
```
Expected: all unit tests pass; end-to-end audit shows `"needs_repair": true` for non_manifold.stl.

```bash
git add .claude/skills/print/SKILL.md
git commit -m "feat(print): integrate mesh audit/repair into SKILL.md (S3 hook, V1, V2)"
```

---

## Phase 3 — Hero Render (opt-in)

Goal: After a successful generation or download, users can request a photo-quality Blender render written to `render.png` alongside the existing `preview.png`.

### Task 3.1: Create `bpy/render_hero.py`

**Files:**
- Create: `.claude/skills/print/scripts/bpy/render_hero.py`
- Create: `.claude/skills/print/tests/test_bpy_render_integration.py`

- [ ] **Step 1: Write the failing integration test**

Create `.claude/skills/print/tests/test_bpy_render_integration.py`:

```python
"""Integration test: render a cube and verify render.png is created."""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
BPY_RENDER = ROOT / "scripts" / "bpy" / "render_hero.py"
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"


@pytest.mark.integration
def test_render_hero_produces_png(tmp_path):
    out = tmp_path / "render.png"
    cmd = [
        BLENDER, "--background", "--factory-startup",
        "--python", str(BPY_RENDER),
        "--", str(FIXTURES / "cube.stl"), str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    assert "BLENDER_OK" in proc.stdout
    assert out.exists()
    assert out.stat().st_size > 1000  # non-empty PNG
    # PNG magic bytes
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd ~/Documents/claude-bambulab-printer && python3 -m pytest .claude/skills/print/tests/test_bpy_render_integration.py -v -m integration`
Expected: FAIL — script does not exist.

- [ ] **Step 3: Write the bpy render script**

Create `.claude/skills/print/scripts/bpy/render_hero.py`:

```python
"""Headless Blender hero-render script.

Run via: blender --background --python render_hero.py -- <input_mesh> <output_png>

Imports the mesh, centers it, adds a neutral ground plane, a 3-point light
rig, and a 35mm camera at 30° elevation, then renders with Eevee at 1280x960.

This is the OPT-IN photo-quality render. Step 5b (fast preview during
generation) uses a simpler render pass.
"""

import math
import sys
from pathlib import Path

import bpy


def parse_args():
    if "--" not in sys.argv:
        raise SystemExit("Usage: ... -- <input_mesh> <output_png>")
    idx = sys.argv.index("--")
    args = sys.argv[idx + 1 :]
    if len(args) < 2:
        raise SystemExit("Usage: ... -- <input_mesh> <output_png>")
    return args[0], args[1]


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for item in list(coll):
            coll.remove(item)


def import_mesh(filepath: str):
    ext = filepath.lower().rsplit(".", 1)[-1]
    if ext == "stl":
        try:
            bpy.ops.wm.stl_import(filepath=filepath)
        except AttributeError:
            bpy.ops.import_mesh.stl(filepath=filepath)
    elif ext == "obj":
        try:
            bpy.ops.wm.obj_import(filepath=filepath)
        except AttributeError:
            bpy.ops.import_scene.obj(filepath=filepath)
    elif ext == "3mf":
        try:
            bpy.ops.import_mesh.threemf(filepath=filepath)
        except AttributeError:
            raise RuntimeError("3MF import not available — export as STL first")
    else:
        raise ValueError(f"Unsupported format: .{ext}")


def center_and_get_bbox():
    """Join all meshes, center at origin, return (bbox_size, bbox_center_z_offset)."""
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("No mesh to render")
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.select_all(action="DESELECT")
    for m in meshes:
        m.select_set(True)
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active

    # Set origin to bounding box center, then move origin to world origin
    bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_VOLUME")
    obj.location = (0, 0, 0)

    return obj, max(obj.dimensions)


def add_ground_plane(size: float):
    bpy.ops.mesh.primitive_plane_add(size=size * 10, location=(0, 0, -size / 2))
    plane = bpy.context.active_object
    mat = bpy.data.materials.new(name="ground")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.85, 0.85, 0.85, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.6
    plane.data.materials.append(mat)


def add_three_point_lights(size: float):
    # Key light (strong, front-right, above)
    bpy.ops.object.light_add(type="AREA", location=(size * 1.5, -size * 1.5, size * 2))
    key = bpy.context.active_object
    key.data.energy = 800
    key.data.size = size * 2
    key.rotation_euler = (math.radians(45), 0, math.radians(45))

    # Fill light (softer, front-left)
    bpy.ops.object.light_add(type="AREA", location=(-size * 1.5, -size * 1.5, size))
    fill = bpy.context.active_object
    fill.data.energy = 300
    fill.data.size = size * 3

    # Back light (rim, above-behind)
    bpy.ops.object.light_add(type="AREA", location=(0, size * 2, size * 2.5))
    rim = bpy.context.active_object
    rim.data.energy = 500
    rim.data.size = size * 1.5


def add_camera(size: float):
    # 35mm lens, 30° elevation, looking at origin
    distance = size * 3.0
    elevation = math.radians(30)
    bpy.ops.object.camera_add(
        location=(
            distance * math.cos(elevation) * 0.7,
            -distance * math.cos(elevation),
            distance * math.sin(elevation),
        )
    )
    cam = bpy.context.active_object
    cam.data.lens = 35
    # Point camera at origin: compute look-at rotation
    import mathutils
    direction = mathutils.Vector((0, 0, 0)) - cam.location
    rot_quat = direction.to_track_quat("-Z", "Y")
    cam.rotation_euler = rot_quat.to_euler()
    bpy.context.scene.camera = cam


def setup_render(output_png: str):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in scene.bl_rna.properties["render"].fixed_type.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 960
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = output_png


def main():
    input_mesh, output_png = parse_args()
    try:
        reset_scene()
        obj, size = center_and_get_bbox()
        add_ground_plane(size)
        add_three_point_lights(size)
        add_camera(size)
        setup_render(output_png)
        bpy.ops.render.render(write_still=True)
    except Exception as e:
        print(f"BLENDER_ERROR {e}", file=sys.stderr)
        sys.exit(1)

    if not Path(output_png).exists():
        print(f"BLENDER_ERROR render completed but output missing: {output_png}", file=sys.stderr)
        sys.exit(1)

    print(f"BLENDER_OK {output_png}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the integration test to verify it passes**

Run:
```bash
cd ~/Documents/claude-bambulab-printer
python3 -m pytest .claude/skills/print/tests/test_bpy_render_integration.py -v -m integration
```
Expected: 1 test PASSES. Render takes ~15-30s. If `BLENDER_EEVEE_NEXT` isn't recognized in Blender 5.1 (it should be), fall back to `"BLENDER_EEVEE"` — the render engine probing inside `setup_render` handles this.

Manually inspect the output:
```bash
# The test writes to tmp_path which is cleaned up — do a manual run
OUT=/tmp/render_smoke.png
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
    --python .claude/skills/print/scripts/bpy/render_hero.py \
    -- .claude/skills/print/tests/fixtures/cube.stl $OUT
open $OUT
```
Expected: a photo-quality Blender render of the cube on a neutral floor with soft shadows.

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/claude-bambulab-printer
git add .claude/skills/print/scripts/bpy/render_hero.py .claude/skills/print/tests/test_bpy_render_integration.py
git commit -m "feat(print): add bpy render_hero.py for photo-quality renders"
```

---

### Task 3.2: Create `blender_render.py` orchestrator and integrate into SKILL.md Step 8.3

**Files:**
- Create: `.claude/skills/print/scripts/blender_render.py`
- Create: `.claude/skills/print/tests/test_blender_render.py`
- Modify: `.claude/skills/print/SKILL.md`

- [ ] **Step 1: Write the failing tests**

Create `.claude/skills/print/tests/test_blender_render.py`:

```python
"""Unit tests for blender_render.py — mocked blender_bridge."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import blender_render  # noqa: E402
import blender_bridge  # noqa: E402


def test_render_ok_returns_output_path(tmp_path, capsys):
    input_file = tmp_path / "model.3mf"
    input_file.write_bytes(b"fake")
    output_png = tmp_path / "render.png"

    fake = MagicMock(success=True, returncode=0, stdout=f"BLENDER_OK {output_png}\n",
                     stderr="", marker_path=str(output_png))
    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        rc = blender_render.main([str(input_file), str(output_png)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"
    assert out["output"] == str(output_png)


def test_render_fails_when_input_missing(tmp_path, capsys):
    rc = blender_render.main(["/nonexistent.3mf", str(tmp_path / "r.png")])
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"


def test_render_propagates_blender_error(tmp_path, capsys):
    input_file = tmp_path / "x.stl"
    input_file.write_bytes(b"")
    out_png = tmp_path / "r.png"

    fake = MagicMock(success=False, returncode=1,
                     stderr="Import failed", marker_path=None)
    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        rc = blender_render.main([str(input_file), str(out_png)])
    assert rc == 1
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "error"
    assert "Import failed" in data["error"]


def test_render_auto_output_path(tmp_path, capsys):
    """When --output is omitted, writes render.png next to the input file."""
    input_file = tmp_path / "model.3mf"
    input_file.write_bytes(b"fake")
    expected = tmp_path / "render.png"

    fake = MagicMock(success=True, returncode=0,
                     stdout=f"BLENDER_OK {expected}\n",
                     stderr="", marker_path=str(expected))
    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        rc = blender_render.main([str(input_file)])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["output"] == str(expected)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/Documents/claude-bambulab-printer && python3 -m pytest .claude/skills/print/tests/test_blender_render.py -v`
Expected: FAIL — `ModuleNotFoundError: blender_render`.

- [ ] **Step 3: Write the orchestrator**

Create `.claude/skills/print/scripts/blender_render.py`:

```python
#!/usr/bin/env python3
"""Hero-render orchestrator for the /print skill.

Usage: blender_render.py <input_mesh> [<output_png>]

If output_png is omitted, writes render.png next to the input file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

SCRIPT_DIR = Path(__file__).parent
BPY_RENDER = SCRIPT_DIR / "bpy" / "render_hero.py"

sys.path.insert(0, str(SCRIPT_DIR))
import blender_bridge  # noqa: E402


def render_file(input_file: str, output_png: Optional[str] = None) -> dict:
    if not os.path.isfile(input_file):
        return {"status": "error", "error": f"Input file not found: {input_file}"}

    if output_png is None:
        output_png = str(Path(input_file).parent / "render.png")

    run = blender_bridge.run_bpy_script(
        str(BPY_RENDER),
        [input_file, output_png],
        timeout=180,
    )
    if run.returncode != 0:
        return {
            "status": "error",
            "error": run.stderr.strip() or f"Blender exited {run.returncode}",
        }

    return {"status": "ok", "output": output_png}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a photo-quality render of a 3D model")
    parser.add_argument("input", help="Path to .stl/.obj/.3mf file")
    parser.add_argument("output", nargs="?", default=None, help="Output PNG path (default: <input_dir>/render.png)")
    args = parser.parse_args(argv)

    result = render_file(args.input, args.output)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, integrate into SKILL.md, verify**

Run unit tests:
```bash
cd ~/Documents/claude-bambulab-printer
python3 -m pytest .claude/skills/print/tests/test_blender_render.py -v
```
Expected: 4 tests PASS.

Now edit SKILL.md. Find `## Step 8: Offer BambuStudio or Send to Printer`. Replace the existing menu block:

**OLD:**
```
What would you like to do next?
1. Open in BambuStudio (for manual slicing and printing)
2. Send directly to your printer (cloud print)
3. Done for now
```

**NEW:**
```
What would you like to do next?
1. Open in BambuStudio (for manual slicing and printing)
2. Send directly to your printer (cloud print)
3. Generate a photo-quality render (Blender)
4. Done for now
```

Then add a new `### Step 8.3: Hero Render` subsection immediately after Step 8:

````markdown
### Step 8.3: Hero Render (option 3)

Triggered by option 3 from the Step 8 menu, or mid-conversation by keywords: "render it nicely", "show me what it looks like", "hero shot", "photo-quality", "pretty picture".

**Prerequisites:** Step 0a (Blender setup check). Requires Blender installed; MCP/venv are optional.

**Determine target file:**
- If a model was just generated/downloaded in this session: use its `.3mf` (or `.stl` fallback).
- Otherwise ask: "Which file should I render?"

**Run the render:**
```bash
python3 ~/.claude/skills/print/scripts/blender_render.py "<input_file>"
```

This writes `render.png` next to the input file (keeping the existing `preview.png` untouched).

Takes ~15-30s on Apple Silicon. Tell the user the render is running before starting so they're not left wondering.

**If status is "error":** show the error. Offer to retry or skip.

**If status is "ok":** present:

```
Hero render saved: <output_path>
(preview.png is still available for the fast matte view)
```

Then ask if they want to do anything else (return to the Step 8 menu).
````

Update the final `## Reference Files` section to add:

```markdown
- @scripts/blender_render.py -- Photo-quality render CLI (Eevee, 1280x960, 3-point lighting)
```

Verify:
```bash
grep "blender_render.py" .claude/skills/print/SKILL.md
grep "Step 8.3" .claude/skills/print/SKILL.md
# End-to-end smoke
python3 .claude/skills/print/scripts/blender_render.py .claude/skills/print/tests/fixtures/cube.stl /tmp/cube_render.png && open /tmp/cube_render.png
```
Expected: grep finds the new entries, the render script produces a real PNG.

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/claude-bambulab-printer
git add .claude/skills/print/scripts/blender_render.py .claude/skills/print/tests/test_blender_render.py .claude/skills/print/SKILL.md
git commit -m "feat(print): add hero render orchestrator and integrate Step 8.3"
```

---

## Phase 4 — Blender Generation Path

Goal: Claude can propose Blender over OpenSCAD for organic shapes, generate a `model.py` bpy script, execute it to produce `model.3mf` + `preview.png`, and handle modify/scale/retry identically to the OpenSCAD flow.

### Task 4.1: Probe 3MF export operator and document

**Files:**
- Create: `.claude/skills/print/scripts/bpy/probe_3mf.py`
- Create: `.claude/skills/print/scripts/blender_probe.py`
- Create: `.claude/skills/print/tests/test_blender_probe.py`
- Result stored in: `~/.claude/skills/print/.blender-3mf-op.txt`

Blender 5.1's 3MF export operator name is version-dependent. Rather than hardcoding one name and hoping, this task discovers the correct operator at setup time and writes the result to a file other scripts read.

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/print/tests/test_blender_probe.py`:

```python
"""Unit tests for blender_probe.py — mocked blender_bridge."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import blender_probe  # noqa: E402
import blender_bridge  # noqa: E402


def test_probe_stores_discovered_operator(tmp_path, monkeypatch):
    cache = tmp_path / "cache.txt"
    monkeypatch.setattr(blender_probe, "CACHE_PATH", str(cache))

    fake = MagicMock(success=True, returncode=0,
                     stdout=f"BLENDER_OK {cache}\n",
                     stderr="", marker_path=str(cache))
    # The bpy script writes the operator name into cache directly
    cache.write_text("bpy.ops.wm.threemf_export")

    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        result = blender_probe.probe()

    assert result["status"] == "ok"
    assert result["operator"] == "bpy.ops.wm.threemf_export"


def test_probe_returns_none_when_no_3mf_operator_found(tmp_path, monkeypatch):
    cache = tmp_path / "cache.txt"
    monkeypatch.setattr(blender_probe, "CACHE_PATH", str(cache))

    fake = MagicMock(success=True, returncode=0,
                     stdout=f"BLENDER_OK {cache}\n",
                     stderr="", marker_path=str(cache))
    cache.write_text("NONE")

    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        result = blender_probe.probe()

    assert result["status"] == "ok"
    assert result["operator"] is None
    assert "stl" in result["fallback"].lower()


def test_probe_caches_result(tmp_path, monkeypatch):
    cache = tmp_path / "cache.txt"
    cache.write_text("bpy.ops.wm.threemf_export")
    monkeypatch.setattr(blender_probe, "CACHE_PATH", str(cache))

    # Should NOT invoke Blender — read from cache
    with patch.object(blender_bridge, "run_bpy_script") as mock_run:
        result = blender_probe.get_cached_operator()
    mock_run.assert_not_called()
    assert result == "bpy.ops.wm.threemf_export"


def test_get_cached_operator_returns_none_when_cache_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(blender_probe, "CACHE_PATH", str(tmp_path / "nope.txt"))
    assert blender_probe.get_cached_operator() is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/Documents/claude-bambulab-printer && python3 -m pytest .claude/skills/print/tests/test_blender_probe.py -v`
Expected: FAIL — `blender_probe` module missing.

- [ ] **Step 3: Write the bpy probe and orchestrator**

Create `.claude/skills/print/scripts/bpy/probe_3mf.py`:

```python
"""Probe which 3MF export operator is available in this Blender.

Writes the operator name (or the literal string "NONE") to <output_path>.
"""
import sys
from pathlib import Path

import bpy


CANDIDATES = [
    "bpy.ops.wm.threemf_export",
    "bpy.ops.export_mesh.threemf",
    "bpy.ops.export_scene.threemf",
]


def parse_args():
    if "--" not in sys.argv:
        raise SystemExit("Usage: ... -- <output_path>")
    idx = sys.argv.index("--")
    args = sys.argv[idx + 1 :]
    if not args:
        raise SystemExit("Usage: ... -- <output_path>")
    return args[0]


def resolve_op(path: str):
    """Walk bpy.ops.<a>.<b> attribute chain; return True if callable, False otherwise."""
    parts = path.split(".")[1:]  # drop "bpy"
    obj = bpy
    for p in parts:
        obj = getattr(obj, p, None)
        if obj is None:
            return False
    return True


def main():
    output = parse_args()
    found = next((c for c in CANDIDATES if resolve_op(c)), None)
    Path(output).write_text(found if found else "NONE")
    print(f"BLENDER_OK {output}")


if __name__ == "__main__":
    main()
```

Create `.claude/skills/print/scripts/blender_probe.py`:

```python
#!/usr/bin/env python3
"""Probe & cache the Blender 3MF export operator name.

Usage: blender_probe.py [--force]

Stores the result at ~/.claude/skills/print/.blender-3mf-op.txt so other
scripts can read it without re-running Blender.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

SCRIPT_DIR = Path(__file__).parent
BPY_PROBE = SCRIPT_DIR / "bpy" / "probe_3mf.py"
CACHE_PATH = os.path.expanduser("~/.claude/skills/print/.blender-3mf-op.txt")

sys.path.insert(0, str(SCRIPT_DIR))
import blender_bridge  # noqa: E402


def get_cached_operator() -> Optional[str]:
    """Return the cached operator name, or None if no cache exists."""
    if not os.path.isfile(CACHE_PATH):
        return None
    content = Path(CACHE_PATH).read_text().strip()
    return None if content == "NONE" else content


def probe() -> dict:
    """Run the bpy probe script and update the cache."""
    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    run = blender_bridge.run_bpy_script(str(BPY_PROBE), [CACHE_PATH], timeout=60)
    if run.returncode != 0:
        return {
            "status": "error",
            "error": run.stderr.strip() or f"probe exited {run.returncode}",
        }

    content = Path(CACHE_PATH).read_text().strip()
    if content == "NONE":
        return {
            "status": "ok",
            "operator": None,
            "fallback": "Export as STL via bpy.ops.wm.stl_export and convert externally",
        }
    return {"status": "ok", "operator": content}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="Re-probe even if cache exists")
    args = parser.parse_args(argv)

    if not args.force:
        cached = get_cached_operator()
        if cached:
            print(json.dumps({"status": "ok", "operator": cached, "from_cache": True}))
            return 0

    result = probe()
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, then run real probe against Blender**

Run unit tests:
```bash
cd ~/Documents/claude-bambulab-printer
python3 -m pytest .claude/skills/print/tests/test_blender_probe.py -v
```
Expected: 4 tests PASS.

Now run the real probe to discover the actual operator on this system:
```bash
python3 .claude/skills/print/scripts/blender_probe.py --force
cat ~/.claude/skills/print/.blender-3mf-op.txt
```
Expected: JSON with an operator name, and the cache file contains either `bpy.ops.wm.threemf_export` (or similar) or `NONE`. **Note which it is** — the result determines whether Phase 4 Task 4.2 uses the discovered operator or the STL-fallback path.

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/claude-bambulab-printer
git add .claude/skills/print/scripts/bpy/probe_3mf.py .claude/skills/print/scripts/blender_probe.py .claude/skills/print/tests/test_blender_probe.py
git commit -m "feat(print): add 3MF export operator probe with cache"
```

---

### Task 4.2: Create `blender_generate.py` orchestrator and generation template

**Files:**
- Create: `.claude/skills/print/scripts/blender_generate.py`
- Create: `.claude/skills/print/scripts/bpy/preview.py`
- Create: `.claude/skills/print/tests/test_blender_generate.py`
- Create: `.claude/skills/print/reference/blender-template.py` (example user can reference)

The orchestrator runs a user-supplied `model.py` to export a 3MF. It also exposes a "preview" command that imports a mesh and renders a fast matte PNG (distinct from the hero render).

- [ ] **Step 1: Write the failing tests**

Create `.claude/skills/print/tests/test_blender_generate.py`:

```python
"""Unit tests for blender_generate.py — mocked subprocess."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import blender_generate  # noqa: E402
import blender_bridge  # noqa: E402


def test_execute_ok_writes_3mf(tmp_path, capsys):
    script = tmp_path / "model.py"
    script.write_text("import bpy  # minimal")
    out = tmp_path / "model.3mf"
    out.write_bytes(b"fake 3mf")  # simulate bpy script created it

    fake = MagicMock(success=True, returncode=0,
                     stdout=f"BLENDER_OK {out}\n",
                     stderr="", marker_path=str(out))
    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        rc = blender_generate.main(["execute", str(script), str(out)])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "ok"
    assert data["output"] == str(out)


def test_execute_missing_script_is_error(tmp_path, capsys):
    rc = blender_generate.main(["execute", "/nonexistent.py", str(tmp_path / "m.3mf")])
    assert rc == 1
    assert "not found" in json.loads(capsys.readouterr().out)["error"].lower()


def test_execute_bpy_error_is_returned(tmp_path, capsys):
    script = tmp_path / "bad.py"
    script.write_text("import bpy")

    fake = MagicMock(success=False, returncode=1,
                     stderr="AttributeError: no such operator",
                     marker_path=None)
    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        rc = blender_generate.main(["execute", str(script), str(tmp_path / "m.3mf")])
    assert rc == 1
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "error"
    assert "AttributeError" in data["error"]


def test_preview_ok_writes_png(tmp_path, capsys):
    mesh = tmp_path / "m.3mf"
    mesh.write_bytes(b"")
    out = tmp_path / "preview.png"

    fake = MagicMock(success=True, returncode=0,
                     stdout=f"BLENDER_OK {out}\n",
                     stderr="", marker_path=str(out))
    with patch.object(blender_bridge, "run_bpy_script", return_value=fake):
        rc = blender_generate.main(["preview", str(mesh), str(out)])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["output"] == str(out)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/Documents/claude-bambulab-printer && python3 -m pytest .claude/skills/print/tests/test_blender_generate.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write the preview bpy script, orchestrator, and template**

Create `.claude/skills/print/scripts/bpy/preview.py`:

```python
"""Fast matte preview render — NOT the hero render.

Run via: blender --background --python preview.py -- <input_mesh> <output_png>

Goal: a 3-5 second shape-check render that replaces the OpenSCAD DeepOcean PNG
for Blender-generated models. Minimal lighting (1 sun lamp), default camera,
800x600 Eevee.
"""

import math
import sys
from pathlib import Path

import bpy


def parse_args():
    if "--" not in sys.argv:
        raise SystemExit("Usage: ... -- <input> <output>")
    args = sys.argv[sys.argv.index("--") + 1 :]
    if len(args) < 2:
        raise SystemExit("Usage: ... -- <input> <output>")
    return args[0], args[1]


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for item in list(coll):
            coll.remove(item)


def import_mesh(filepath: str):
    ext = filepath.lower().rsplit(".", 1)[-1]
    if ext == "stl":
        try:
            bpy.ops.wm.stl_import(filepath=filepath)
        except AttributeError:
            bpy.ops.import_mesh.stl(filepath=filepath)
    elif ext == "3mf":
        try:
            bpy.ops.import_mesh.threemf(filepath=filepath)
        except AttributeError:
            raise RuntimeError("3MF import unavailable")
    else:
        raise ValueError(f"Unsupported: .{ext}")


def main():
    input_file, output_png = parse_args()
    try:
        reset_scene()
        import_mesh(input_file)

        # Join + center
        meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
        if not meshes:
            raise RuntimeError("No mesh")
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.select_all(action="DESELECT")
        for m in meshes:
            m.select_set(True)
        if len(meshes) > 1:
            bpy.ops.object.join()
        obj = bpy.context.view_layer.objects.active
        bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_VOLUME")
        obj.location = (0, 0, 0)
        size = max(obj.dimensions) or 1.0

        # One sun lamp
        bpy.ops.object.light_add(type="SUN", location=(size, -size, size * 2))
        bpy.context.active_object.data.energy = 3.0

        # Camera
        import mathutils
        cam_loc = (size * 2, -size * 2, size * 1.5)
        bpy.ops.object.camera_add(location=cam_loc)
        cam = bpy.context.active_object
        cam.data.lens = 50
        direction = mathutils.Vector((0, 0, 0)) - cam.location
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.camera = cam

        # Render settings — fast
        scene = bpy.context.scene
        scene.render.engine = "BLENDER_EEVEE_NEXT" if hasattr(bpy.types, "SceneEEVEE") else "BLENDER_EEVEE"
        scene.render.resolution_x = 800
        scene.render.resolution_y = 600
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = output_png
        bpy.ops.render.render(write_still=True)
    except Exception as e:
        print(f"BLENDER_ERROR {e}", file=sys.stderr)
        sys.exit(1)

    if not Path(output_png).exists():
        print(f"BLENDER_ERROR no output file", file=sys.stderr)
        sys.exit(1)
    print(f"BLENDER_OK {output_png}")


if __name__ == "__main__":
    main()
```

Create `.claude/skills/print/scripts/blender_generate.py`:

```python
#!/usr/bin/env python3
"""Blender generation orchestrator for the /print skill.

Subcommands:
  execute <model.py> <output.3mf>   — run a user bpy script, exporting a 3MF
  preview <mesh>     <preview.png>  — render a fast matte preview of a mesh

The 'execute' subcommand runs the user's model.py directly (it's a full bpy
script), passing the output 3MF path as the argument after --. The user script
is responsible for calling bpy.ops.{op}(filepath=...) itself, using the
operator name cached by blender_probe.py (read from the cache file).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

SCRIPT_DIR = Path(__file__).parent
BPY_PREVIEW = SCRIPT_DIR / "bpy" / "preview.py"

sys.path.insert(0, str(SCRIPT_DIR))
import blender_bridge  # noqa: E402


def cmd_execute(script: str, output: str) -> dict:
    if not os.path.isfile(script):
        return {"status": "error", "error": f"Script not found: {script}"}

    # Ensure output directory exists
    Path(output).parent.mkdir(parents=True, exist_ok=True)

    run = blender_bridge.run_bpy_script(script, [output], timeout=180)
    if run.returncode != 0:
        return {
            "status": "error",
            "error": run.stderr.strip() or f"Blender exited {run.returncode}",
            "stdout": run.stdout,
        }
    if not os.path.isfile(output):
        return {
            "status": "error",
            "error": f"Script exited 0 but output file not created: {output}",
            "stdout": run.stdout,
        }
    return {"status": "ok", "output": output}


def cmd_preview(mesh: str, output: str) -> dict:
    if not os.path.isfile(mesh):
        return {"status": "error", "error": f"Mesh not found: {mesh}"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    run = blender_bridge.run_bpy_script(
        str(BPY_PREVIEW),
        [mesh, output],
        timeout=60,
    )
    if run.returncode != 0:
        return {
            "status": "error",
            "error": run.stderr.strip() or f"Blender exited {run.returncode}",
        }
    return {"status": "ok", "output": output}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Blender generation orchestrator")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ex = sub.add_parser("execute")
    ex.add_argument("script")
    ex.add_argument("output")

    pv = sub.add_parser("preview")
    pv.add_argument("mesh")
    pv.add_argument("output")

    args = parser.parse_args(argv)

    if args.cmd == "execute":
        result = cmd_execute(args.script, args.output)
    else:
        result = cmd_preview(args.mesh, args.output)

    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
```

Create `.claude/skills/print/reference/blender-template.py` (referenced from blender-guide.md as a starting skeleton):

```python
"""Blender generation template — copied and filled in for organic models.

Usage: blender --background --python model.py -- <output_3mf_path>

Replace the PARAMETERS block and the BUILD_MODEL function with your shape.
Keeps the same parametric discipline as OpenSCAD model.scad files.
"""

import math
import sys
from pathlib import Path

import bpy
import bmesh


# ---- PARAMETERS ----
OBJECT_NAME = "example_vase"
MATERIAL = "PLA"
WALL = 1.2  # mm
HEIGHT = 120.0
BASE_RADIUS = 30.0
TOP_RADIUS = 45.0
# --------------------


def parse_args():
    if "--" not in sys.argv:
        raise SystemExit("Usage: ... -- <output_3mf>")
    args = sys.argv[sys.argv.index("--") + 1 :]
    if not args:
        raise SystemExit("Usage: ... -- <output_3mf>")
    return args[0]


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for item in list(coll):
            coll.remove(item)


def set_mm_units():
    u = bpy.context.scene.unit_settings
    u.system = "METRIC"
    u.scale_length = 0.001


def build_model():
    """Construct the mesh. Replace this with your shape."""
    # Example: lofted vase via bmesh
    bm = bmesh.new()
    n_rings = 16
    n_segments = 32
    rings = []
    for i in range(n_rings):
        t = i / (n_rings - 1)
        z = t * HEIGHT
        r = BASE_RADIUS + (TOP_RADIUS - BASE_RADIUS) * t + 3.0 * math.sin(t * math.pi * 2)
        ring = []
        for j in range(n_segments):
            theta = j * 2 * math.pi / n_segments
            v = bm.verts.new((r * math.cos(theta), r * math.sin(theta), z))
            ring.append(v)
        rings.append(ring)

    # Side faces
    for i in range(n_rings - 1):
        for j in range(n_segments):
            a = rings[i][j]
            b = rings[i][(j + 1) % n_segments]
            c = rings[i + 1][(j + 1) % n_segments]
            d = rings[i + 1][j]
            bm.faces.new([a, b, c, d])

    # Bottom cap
    bm.faces.new(list(reversed(rings[0])))

    me = bpy.data.meshes.new(OBJECT_NAME)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(OBJECT_NAME, me)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Solidify modifier for wall thickness (vase interior)
    mod = obj.modifiers.new("solidify", "SOLIDIFY")
    mod.thickness = WALL
    mod.offset = -1  # inward
    bpy.ops.object.modifier_apply(modifier="solidify")

    return obj


def export_3mf_or_stl(obj, output_path: str):
    """Try 3MF export, fall back to STL if 3MF operator isn't available."""
    # Read cached operator name
    cache = Path.home() / ".claude/skills/print/.blender-3mf-op.txt"
    op_path = None
    if cache.is_file():
        content = cache.read_text().strip()
        if content and content != "NONE":
            op_path = content

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    if op_path:
        # Walk the operator path to resolve it
        parts = op_path.split(".")[1:]
        op = bpy
        for p in parts:
            op = getattr(op, p)
        op(filepath=output_path)
        return output_path

    # Fallback: export STL next to the requested 3MF path
    stl_path = output_path.rsplit(".", 1)[0] + ".stl"
    try:
        bpy.ops.wm.stl_export(filepath=stl_path, export_selected_objects=True)
    except AttributeError:
        bpy.ops.export_mesh.stl(filepath=stl_path, use_selection=True)
    print(f"NOTE: 3MF operator not available, exported STL instead: {stl_path}", file=sys.stderr)
    return stl_path


def main():
    output = parse_args()
    try:
        reset_scene()
        set_mm_units()
        obj = build_model()
        actual_output = export_3mf_or_stl(obj, output)
    except Exception as e:
        print(f"BLENDER_ERROR {e}", file=sys.stderr)
        sys.exit(1)

    print(f"BLENDER_OK {actual_output}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests and smoke-test**

Run unit tests:
```bash
cd ~/Documents/claude-bambulab-printer
python3 -m pytest .claude/skills/print/tests/test_blender_generate.py -v
```
Expected: 4 tests PASS.

Smoke-test the real generation flow against the template vase:
```bash
mkdir -p /tmp/vase-test
python3 .claude/skills/print/scripts/blender_generate.py execute \
    .claude/skills/print/reference/blender-template.py \
    /tmp/vase-test/model.3mf
ls -la /tmp/vase-test/
```
Expected: the template runs, produces either `model.3mf` or `model.stl` (depending on 3MF operator availability), exits 0.

Preview test:
```bash
# Use whichever file was produced above
VASE=$(ls /tmp/vase-test/model.* 2>/dev/null | head -1)
python3 .claude/skills/print/scripts/blender_generate.py preview \
    "$VASE" \
    /tmp/vase-test/preview.png
open /tmp/vase-test/preview.png
```
Expected: 800×600 matte preview of the vase.

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/claude-bambulab-printer
git add .claude/skills/print/scripts/bpy/preview.py .claude/skills/print/scripts/blender_generate.py .claude/skills/print/tests/test_blender_generate.py .claude/skills/print/reference/blender-template.py
git commit -m "feat(print): add blender_generate.py orchestrator and generation template"
```

---

### Task 4.3: Integrate Blender generation path into SKILL.md

**Files:**
- Modify: `.claude/skills/print/SKILL.md`

This is the biggest SKILL.md edit of the plan. It adds the organic-detection routing (Step 2b), the Blender generation steps (3b, 5b, 6b), and updates the modify/scale steps to handle `model.py` files. No new code — only markdown.

- [ ] **Step 1: Add the IMPORTANT RULES line for Blender**

Find the `**IMPORTANT RULES -- follow these without exception:**` block near the top of SKILL.md. Add these lines at the end of the list:

```markdown
- Do NOT use Blender for mechanical/parametric shapes. OpenSCAD is the default — Blender is only proposed when the organic-shape heuristic fires (Step 2b).
- Do NOT hardcode the 3MF export operator in generated model.py files. Always read from the cache at ~/.claude/skills/print/.blender-3mf-op.txt (see reference/blender-template.py).
```

- [ ] **Step 2: Insert Step 2b (organic detection routing)**

Find the end of `## Step 2: Clarify the Request` section. Immediately after the "Once you have answers..." paragraph but BEFORE the `## Step 3: Generate OpenSCAD Code` heading, insert:

````markdown
## Step 2b: Choose Generator (OpenSCAD or Blender)

After Step 2 confirms dimensions/use-case/material, run a silent organic-shape check against the request. Do NOT ask the user to choose unless the check fires.

**Organic-shape heuristic** — any of the following signal Blender is a better fit:

- **Shape vocabulary:** curve, organic, smooth, ergonomic, flowing, sculpted, fairing, shell, hood, pod, lofted, swept, natural, blob, wavy, rounded
- **Object type:** grip, handle, figurine, miniature, decorative vase, planter with curves, cosplay prop, sculpture, toy, drone aerodynamic part, ergonomic mouse/tool body
- **Geometric signal:** the shape cannot be expressed as a combination of boxes, cylinders, linear extrusions, or simple revolutions

**If none fire:** proceed silently to Step 3 (OpenSCAD) as today. No mention of Blender.

**If any fire:** run Step 0a (Blender setup check) if not already done, then ask ONE line:

> "This shape sounds organic — Blender handles curves and sculpted surfaces better than OpenSCAD. Want me to use Blender instead? (y/n)"

- `y` or any variant → go to **Step 3b**.
- `n` or any variant → go to **Step 3** (OpenSCAD) as today.

**User override at any time:** if the user's original request contained "use blender" / "in blender" / "as a mesh", skip the heuristic and go straight to Step 3b. If they said "use openscad" / "parametric", skip to Step 3.

````

- [ ] **Step 3: Insert Steps 3b, 5b, 6b (Blender generation flow)**

Immediately after `## Step 3: Generate OpenSCAD Code` and its content, but BEFORE `## Step 4: Save Files`, insert three new sections:

````markdown
## Step 3b: Generate Blender bpy Script (model.py)

Reference @reference/blender-guide.md for bpy patterns, @reference/blender-template.py for a complete worked example, @reference/materials.md for material parameters, and @reference/design-patterns.md for tolerances/fits.

Generate a self-contained bpy script following these rules:

1. **Comment header:**
   ```python
   # [Object Name]
   # Material: [PLA/PETG/...] | Wall: [X]mm
   # Description: [what the user asked for]
   ```

2. **Parameters block** at the top — ALL dimensions as uppercase constants. No magic numbers in the body.

3. **Scene reset** — clear default cube/light/camera so the script is idempotent.

4. **Unit scale to mm** — `bpy.context.scene.unit_settings.scale_length = 0.001`

5. **Arg parsing** — the script must accept the output path as the single arg after `--`:
   ```python
   if "--" not in sys.argv:
       raise SystemExit("Usage: ... -- <output>")
   output = sys.argv[sys.argv.index("--") + 1:][0]
   ```

6. **Construction** — use bmesh for custom geometry, modifiers (subsurf, bevel, solidify, mirror, boolean) for standard ops.

7. **Export** — DO NOT hardcode the 3MF operator. Read `~/.claude/skills/print/.blender-3mf-op.txt`. If it contains a valid operator name, walk the `bpy.ops.*` attribute chain to resolve and call it. If it contains `NONE` or the cache is missing, fall back to STL export via `bpy.ops.wm.stl_export`. See `reference/blender-template.py` for the exact fallback pattern.

8. **Success marker** — print `BLENDER_OK <output_path>` to stdout as the last line on success; call `sys.exit(1)` with a stderr error on failure.

9. **Material-appropriate defaults** from @reference/materials.md:
   - PLA/ABS/ASA: wall >= 1.2mm, clearance = 0.3mm
   - PETG/Nylon: wall >= 1.2mm, clearance = 0.35mm
   - TPU: wall >= 1.6mm, clearance = 0.4mm

**Show the generated bpy code to the user** so they can review and learn from it, same as Step 3.

**Complex-model warning:** same language as Step 3 — if the shape is at the edge of reliable generation, warn the user that it may need manual adjustment.

## Step 4b: Save Files (parallel to Step 4)

```bash
OUTPUT_DIR="$HOME/3d-prints/<descriptive-name>"
mkdir -p "$OUTPUT_DIR"
```

Save the generated bpy script as `$OUTPUT_DIR/model.py`.

## Step 5b: Validate, Preview, Export (Blender)

Three stages, same pattern as Step 5.

### Validate

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
    --python "$OUTPUT_DIR/model.py" -- /dev/null 2>"$OUTPUT_DIR/blender.log"
```

Catches bpy errors before the full export run. If this fails, go to Step 6b.

### Export 3MF

```bash
python3 ~/.claude/skills/print/scripts/blender_generate.py execute \
    "$OUTPUT_DIR/model.py" "$OUTPUT_DIR/model.3mf" 2>>"$OUTPUT_DIR/blender.log"
```

Note: if the 3MF operator isn't available in the installed Blender, the template's fallback will produce `model.stl` instead. Both are valid for BambuStudio import.

### Fast Preview PNG

```bash
# Use whichever file was produced above (prefer .3mf, fall back to .stl)
OUTPUT_FILE="$OUTPUT_DIR/model.3mf"
[ -f "$OUTPUT_FILE" ] || OUTPUT_FILE="$OUTPUT_DIR/model.stl"

python3 ~/.claude/skills/print/scripts/blender_generate.py preview \
    "$OUTPUT_FILE" "$OUTPUT_DIR/preview.png" 2>>"$OUTPUT_DIR/blender.log"
```

This is the **fast** matte preview for shape-check during iteration. It is NOT the hero render (Step 8.3). Takes ~3-5s.

## Step 6b: Error Handling and Retry (Blender)

Identical pattern to Step 6:

1. Read `cat "$OUTPUT_DIR/blender.log"`
2. Analyze the error (use @reference/blender-guide.md "Common error patterns" section).
3. Fix the `.py` code based on the error.
4. Save the fixed version to `$OUTPUT_DIR/model.py`.
5. Explain to the user what was wrong and what you fixed.
6. Retry Step 5b.

**Retry up to 3 total attempts.** On each retry, explain the error and fix.

**After 3 failed attempts:**
- Show the error and the current `.py` to the user.
- Explain: "I wasn't able to fix this automatically. You can edit the .py file directly at `$OUTPUT_DIR/model.py` and run `python3 ~/.claude/skills/print/scripts/blender_generate.py execute ...` manually."

````

- [ ] **Step 4: Update Steps 7, 9, 10 to handle both model.scad and model.py**

**Step 7 (Output Summary):** Find the `## Step 7: Output Summary` section. Replace the "OpenSCAD source" line in the "File path" block:

**OLD:**
```
3MF file: $OUTPUT_DIR/model.3mf
OpenSCAD source: $OUTPUT_DIR/model.scad
```

**NEW:**
```
3MF file: $OUTPUT_DIR/model.3mf (or model.stl if 3MF operator unavailable in Blender)
Source: $OUTPUT_DIR/model.scad (OpenSCAD) OR $OUTPUT_DIR/model.py (Blender)
```

Also in Step 7 item 6 ("OpenSCAD code"), change the heading:

**OLD:** `6. **OpenSCAD code**: Show the complete generated code so the user can review...`

**NEW:** `6. **Source code**: Show the complete generated OpenSCAD or bpy code so the user can review, learn, or modify it.`

**Step 9 (Modify Existing Model):** Find `### 1. Locate the Model` under Step 9. Add a bullet:

```markdown
- The source file is either `model.scad` (OpenSCAD) or `model.py` (Blender). Check both.
```

In `### 2. Create Versioned Backup Before ANY Edit`, replace the `cp` command:

**OLD:**
```bash
cp "$OUTPUT_DIR/model.scad" "$OUTPUT_DIR/model_v${NEXT_VER}.scad"
```

**NEW:**
```bash
# Detect source format
SRC=""
[ -f "$OUTPUT_DIR/model.scad" ] && SRC="$OUTPUT_DIR/model.scad"
[ -f "$OUTPUT_DIR/model.py" ] && SRC="$OUTPUT_DIR/model.py"
EXT="${SRC##*.}"

NEXT_VER=1
while [ -f "$OUTPUT_DIR/model_v${NEXT_VER}.${EXT}" ]; do
    NEXT_VER=$((NEXT_VER + 1))
done
cp "$SRC" "$OUTPUT_DIR/model_v${NEXT_VER}.${EXT}"
```

In `### 6. Render After User Confirms`, add:

```markdown
- For `.scad`: use the OpenSCAD commands from Step 5.
- For `.py`: use the commands from Step 5b.
```

**Step 10 (Scale/Resize Model):** Find `### 2. Preferred Approach: Modify Parametric Variables`. Add a note at the top:

```markdown
> **Applies to both `.scad` and `.py` files.** For `.py`, the parameters are uppercase constants at the top of the file (see `@reference/blender-template.py` for the convention).
```

- [ ] **Step 5: Update Reference Files section and commit**

Find the `## Reference Files` section. Add these entries:

```markdown
- @scripts/blender_generate.py -- Blender generation orchestrator (execute model.py + fast preview)
- @scripts/blender_probe.py -- 3MF export operator discovery
- @reference/blender-template.py -- Worked example bpy script (copy and fill in)
```

Verify everything:

```bash
cd ~/Documents/claude-bambulab-printer
# Check new sections exist
grep -c "Step 2b" .claude/skills/print/SKILL.md   # expect: 1+
grep -c "Step 3b" .claude/skills/print/SKILL.md   # expect: 1+
grep -c "Step 5b" .claude/skills/print/SKILL.md   # expect: 1+
grep -c "Step 6b" .claude/skills/print/SKILL.md   # expect: 1+
grep -c "blender_generate.py" .claude/skills/print/SKILL.md  # expect: 3+

# All tests still pass (skip integration tests for speed)
python3 -m pytest .claude/skills/print/tests/ -v \
    --ignore=.claude/skills/print/tests/test_bpy_audit_integration.py \
    --ignore=.claude/skills/print/tests/test_bpy_repair_integration.py \
    --ignore=.claude/skills/print/tests/test_bpy_render_integration.py
```

Expected: all grep results ≥ 1, all unit tests pass.

```bash
git add .claude/skills/print/SKILL.md
git commit -m "feat(print): integrate Blender generation flow (Steps 2b, 3b, 5b, 6b)"
```

---

## Phase-end Smoke Test (run after all 4 phases)

After Phase 4 is complete, run the full integration suite as a final check:

```bash
cd ~/Documents/claude-bambulab-printer

# Unit tests (fast, ~5s)
python3 -m pytest .claude/skills/print/tests/ -v \
    --ignore=.claude/skills/print/tests/test_bpy_audit_integration.py \
    --ignore=.claude/skills/print/tests/test_bpy_repair_integration.py \
    --ignore=.claude/skills/print/tests/test_bpy_render_integration.py

# Integration tests (slow, each test spawns Blender)
python3 -m pytest .claude/skills/print/tests/ -v -m integration

# End-to-end smoke test of the full generation-preview-audit-repair chain
mkdir -p /tmp/e2e-test
cp .claude/skills/print/tests/fixtures/non_manifold.stl /tmp/e2e-test/
python3 .claude/skills/print/scripts/blender_audit.py /tmp/e2e-test/non_manifold.stl
python3 .claude/skills/print/scripts/blender_repair.py /tmp/e2e-test/non_manifold.stl
python3 .claude/skills/print/scripts/blender_audit.py /tmp/e2e-test/non_manifold.stl
python3 .claude/skills/print/scripts/blender_render.py /tmp/e2e-test/non_manifold.stl
ls -la /tmp/e2e-test/
```

Expected: unit tests all pass; integration tests all pass; e2e shows non-manifold → repaired → clean audit → render.png produced.

## Plan Self-Review Notes

**Spec coverage verified:**

| Spec section | Task(s) implementing |
|---|---|
| Install check / Step 0a | Task 1.3 (blender_setup.py), Task 1.4 (SKILL.md edit) |
| Blender-guide.md reference | Task 1.1 |
| Invocation via background mode / CLI fallback | Task 1.2 (blender_bridge.py) |
| Step 2b organic detection | Task 4.3 |
| Step 3b bpy generation | Task 4.2 (orchestrator), Task 4.3 (SKILL.md integration) |
| Step 5b validate/preview/export | Task 4.2, Task 4.3 |
| Step 6b retry loop | Task 4.3 |
| Hero render Step 8.3 | Task 3.1 (bpy), Task 3.2 (orchestrator + SKILL.md) |
| render.png vs preview.png distinction | Task 3.2, Task 4.2 (preview is separate script) |
| Step S3 audit hook | Task 2.4 |
| Step V1 audit entry | Task 2.4 |
| Step V2 repair entry | Task 2.4 |
| Audit function reused both places | Task 2.2 (single blender_audit.py called from both) |
| Modify/scale for Blender-generated models | Task 4.3 (SKILL.md edits to Steps 9 and 10) |
| Non-goals: no live Blender, no auto-repair, no Cycles, no render during iteration | Preserved across all tasks |
| Test fixtures | Task 1.4 |
| Open question: 3MF operator name | Task 4.1 (probe script) — resolved at install time, not hardcoded |
| Open question: venv conflict with Playwright | Task 1.3 uses a dedicated venv at `.venv-blender/` distinct from any Playwright install |
| Open question: MCP command path portability | Task 1.3 writes the absolute venv path into settings.json; re-running `blender_setup.py register` regenerates it |

**Placeholder scan:** none found — every step has concrete code, commands, or markdown edits.

**Type consistency:** verified — `BlenderRunResult` fields match across `blender_bridge.py` usage in `blender_audit.py`, `blender_repair.py`, `blender_render.py`, `blender_generate.py`, `blender_probe.py`. `needs_repair` function signature matches its caller in `blender_audit.py`. `STDOUT_MARKER = "BLENDER_OK"` used consistently across all bpy scripts and parsed by `blender_bridge._parse_marker`.
