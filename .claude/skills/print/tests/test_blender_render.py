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
