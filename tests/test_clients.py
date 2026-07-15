"""Tests for the client-profile MCP tools and the .smis reader."""

from conftest import AVG_MAN

from pattern_forge.mcp_server import get_client, list_clients, save_client
from pattern_forge.smis import MeasurementsFile, load_measurements


def test_smis_roundtrip(tmp_path):
    m = MeasurementsFile(unit="cm")
    m.set_many(AVG_MAN)
    path = m.save(tmp_path / "x.smis")
    assert load_measurements(path) == {k: float(v) for k, v in AVG_MAN.items()}


def test_client_save_get_list(tmp_path, monkeypatch):
    monkeypatch.setenv("PATTERN_FORGE_WORKSPACE", str(tmp_path))
    saved = save_client("Ahmed Test", AVG_MAN)
    assert saved["ok"], saved
    listed = list_clients()
    assert any(c["name"] == "Ahmed_Test" for c in listed)
    loaded = get_client("Ahmed Test")
    assert loaded["ok"]
    assert loaded["measurements"]["waist_circ"] == 84


def test_get_unknown_client(tmp_path, monkeypatch):
    monkeypatch.setenv("PATTERN_FORGE_WORKSPACE", str(tmp_path))
    result = get_client("nobody")
    assert result["ok"] is False and "available" in result
