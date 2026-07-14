"""Tests for the MCP tool functions (called directly, not over the protocol)."""

import pytest

from pattern_forge.config import find_seamly2d
from pattern_forge.mcp_server import (
    describe_recipe,
    draft_pattern,
    export_pattern_file,
    list_recipes,
    render_preview,
)

needs_seamly2d = pytest.mark.skipif(find_seamly2d() is None, reason="seamly2d.exe not found")

AVG_MAN = {
    "waist_circ": 84,
    "hip_circ": 100,
    "height_waist_side": 107,
    "leg_crotch_to_floor": 83,
    "height_knee": 50,
}


def test_list_recipes_contains_trousers():
    names = [r["name"] for r in list_recipes()]
    assert "trousers" in names and "aline_skirt" in names


def test_describe_recipe_trousers():
    info = describe_recipe("trousers")
    assert any(s["name"] == "waist_circ" for s in info["required_measurements"])
    assert any(o["name"] == "knee_circ" for o in info["options"])


def test_describe_unknown_recipe():
    assert "error" in describe_recipe("cape")


def test_draft_rejects_bad_measurements():
    result = draft_pattern("trousers", AVG_MAN | {"waist_circ": 20})
    assert result["ok"] is False
    assert any("waist_circ" in e for e in result["errors"])


@needs_seamly2d
def test_full_flow_draft_preview_export(tmp_path, monkeypatch):
    monkeypatch.setenv("PATTERN_FORGE_WORKSPACE", str(tmp_path))
    drafted = draft_pattern("trousers", AVG_MAN, name="test_client")
    assert drafted["ok"], drafted
    assert drafted["seamly2d_validation"]["ok"]

    preview = render_preview(drafted["pattern_path"])
    assert preview["ok"], preview
    assert preview["preview_files"]

    exported = export_pattern_file(drafted["pattern_path"], "dxf")
    assert exported["ok"], exported
    assert exported["files"]
