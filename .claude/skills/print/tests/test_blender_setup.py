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
