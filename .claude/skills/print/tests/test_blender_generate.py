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
