"""Tests for the MCP tool functions (called directly, not over the protocol)."""

from pathlib import Path

from conftest import AVG_MAN, needs_seamly2d

from pattern_forge.mcp_server import (
    _friendly_hint,
    describe_recipe,
    draft_pattern,
    export_pattern_file,
    list_recipes,
    render_preview,
)

DATA = Path(__file__).parent / "data"


def test_list_recipes_contains_trousers():
    names = [r["name"] for r in list_recipes()]
    assert "trousers" in names and "aline_skirt" in names


def test_describe_recipe_trousers():
    info = describe_recipe("trousers")
    assert any(s["name"] == "waist_circ" for s in info["required_measurements"])
    assert any(o["name"] == "knee_circ" for o in info["options"])


def test_describe_unknown_recipe():
    result = describe_recipe("cape")
    assert result["ok"] is False
    assert any("cape" in e for e in result["errors"])
    assert "trousers" in result["available"]


def test_draft_rejects_bad_measurements():
    result = draft_pattern("trousers", AVG_MAN | {"waist_circ": 20})
    assert result["ok"] is False
    assert any("waist_circ" in e for e in result["errors"])


def test_error_result_shapes_are_safe_to_index():
    """Error returns carry their data key (empty) so callers can't KeyError."""
    assert export_pattern_file("does_not_exist.sm2d", "pdf")["files"] == []
    assert export_pattern_file("x.sm2d", "xyz")["files"] == []
    assert render_preview("does_not_exist.sm2d")["preview_files"] == []


def test_every_failure_carries_errors_list():
    """Uniform contract: every ok=false result has a non-empty errors list of strings."""
    failures = [
        describe_recipe("cape"),
        draft_pattern("cape", {}),
        draft_pattern("trousers", {"waist_circ": 20}),
        render_preview("does_not_exist.sm2d"),
        export_pattern_file("does_not_exist.sm2d", "pdf"),
        export_pattern_file("x.sm2d", "not_a_format"),
    ]
    for result in failures:
        assert result["ok"] is False, result
        assert result["errors"], result
        assert all(isinstance(e, str) for e in result["errors"]), result


def test_guard_converts_unexpected_exception(monkeypatch):
    """The MCP boundary must never leak a raw exception — it becomes ok=false."""
    from pattern_forge import mcp_server

    def boom(*args, **kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(mcp_server.RECIPES["trousers"], "draft", boom)
    result = draft_pattern("trousers", {"waist_circ": 84})
    assert result["ok"] is False
    assert any("RuntimeError" in e and "kaboom" in e for e in result["errors"])


def test_missing_measurements_file_is_structured_error():
    result = export_pattern_file(str(DATA / "trousers.sm2d"), "pdf",
                                 measurements="does_not_exist.smis")
    assert result["ok"] is False
    assert any("measurements file not found" in e for e in result["errors"])
    assert result["files"] == []


@needs_seamly2d
def test_render_preview_with_measurements(tmp_path, monkeypatch):
    """REGRESSION (review finding): patterns referencing an external .smis
    could not be previewed through the MCP surface (no -m pass-through)."""
    monkeypatch.setenv("PATTERN_FORGE_WORKSPACE", str(tmp_path))
    result = render_preview(str(DATA / "trousers.sm2d"),
                            measurements=str(DATA / "trousers.smis"))
    assert result["ok"], result
    assert result["preview_files"]


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
