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


def test_corrupt_profile_does_not_break_listing(tmp_path, monkeypatch):
    """REGRESSION (review finding): one truncated .smis must not fail the whole
    client list or crash get_client."""
    monkeypatch.setenv("PATTERN_FORGE_WORKSPACE", str(tmp_path))
    save_client("Good", AVG_MAN)
    (tmp_path / "clients" / "Broken.smis").write_text("<smis><unclosed", encoding="utf-8")

    listed = list_clients()
    good = next(c for c in listed if c["name"] == "Good")
    broken = next(c for c in listed if c["name"] == "Broken")
    assert good["measurements"] == len(AVG_MAN)
    assert "error" in broken

    result = get_client("Broken")
    assert result["ok"] is False
    assert any("unreadable" in e for e in result["errors"])


def test_save_client_rejects_garbage_values(tmp_path, monkeypatch):
    """REGRESSION (review finding): NaN/negative values must not be saved ok=true."""
    monkeypatch.setenv("PATTERN_FORGE_WORKSPACE", str(tmp_path))
    result = save_client("bad", {"waist_circ": -80, "hip_circ": float("nan")})
    assert result["ok"] is False
    assert result["errors"]
    assert not (tmp_path / "clients" / "bad.smis").exists()


def test_save_client_validates_against_xsd(tmp_path, monkeypatch):
    monkeypatch.setenv("PATTERN_FORGE_WORKSPACE", str(tmp_path))
    result = save_client("Good", AVG_MAN)
    assert result["ok"] and result["xsd_valid"]


def test_save_xml_atomic_leaves_no_tmp(tmp_path):
    """Atomic save: overwrite works and no *.tmp files remain."""
    m = MeasurementsFile(unit="cm")
    m.set_many(AVG_MAN)
    path = m.save(tmp_path / "x.smis")
    m.set("waist_circ", 90)
    m.save(path)  # overwrite
    assert load_measurements(path)["waist_circ"] == 90
    assert not list(tmp_path.glob("*.tmp")), "temp file left behind"
