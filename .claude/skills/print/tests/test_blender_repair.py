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


def test_repair_catches_blender_not_found_error(tmp_path, capsys):
    """If Blender isn't installed, repair_file returns structured error, not a crash."""
    target = tmp_path / "model.stl"
    target.write_bytes(b"fake")

    with patch.object(
        blender_bridge, "run_bpy_script",
        side_effect=blender_bridge.BlenderNotFoundError("Blender not found"),
    ):
        result = blender_repair.repair_file(str(target))

    assert result["status"] == "error"
    assert "Blender not found" in result["error"]


def test_repair_catches_file_not_found_from_bridge(tmp_path, capsys):
    """If the bpy repair script path doesn't exist, return structured error."""
    target = tmp_path / "model.stl"
    target.write_bytes(b"fake")

    with patch.object(
        blender_bridge, "run_bpy_script",
        side_effect=FileNotFoundError("bpy script not found: /bogus/repair.py"),
    ):
        result = blender_repair.repair_file(str(target))

    assert result["status"] == "error"
    assert "not found" in result["error"].lower()
