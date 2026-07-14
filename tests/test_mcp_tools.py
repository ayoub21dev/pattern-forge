"""Tests for the MCP tool functions (called directly, not over the protocol)."""

from conftest import AVG_MAN, needs_seamly2d

from pattern_forge.mcp_server import (
    _friendly_hint,
    describe_recipe,
    draft_pattern,
    export_pattern_file,
    list_recipes,
    render_preview,
)


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


def test_error_result_shapes_are_safe_to_index():
    """Error returns carry their data key (empty) so callers can't KeyError."""
    assert export_pattern_file("does_not_exist.sm2d", "pdf")["files"] == []
    assert export_pattern_file("x.sm2d", "xyz")["files"] == []
    assert render_preview("does_not_exist.sm2d")["preview_files"] == []


def test_friendly_hint_translates_unknown_variable():
    stderr = 'Message:     Unexpected token "#DoesNotExist" found at position 0.'
    hint = _friendly_hint(stderr)
    assert hint is not None and "#DoesNotExist" in hint


def test_friendly_hint_unknown_error_returns_none():
    assert _friendly_hint("some completely novel failure") is None


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
