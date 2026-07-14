"""MCP server: lets an AI assistant draft, validate, and export garment patterns.

The AI never draws geometry — it configures validated recipes (see recipes/) and
the real Seamly2D binary is the authoritative validator behind every result.

Run standalone:  python -m pattern_forge.mcp_server   (stdio transport)
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import PROJECT_ROOT, find_seamly2d, find_seamlyme
from .recipes import AlineSkirt, Trousers
from .recipes.base import Recipe
from .seamly_cli import (
    ExportFormat,
    export_pattern,
    validate_measurements,
    validate_pattern,
)
from .smis import MeasurementsFile
from .validators import validate_pattern_xml

RECIPES: dict[str, Recipe] = {r.name: r for r in (AlineSkirt(), Trousers())}

EXPORT_FORMATS: dict[str, ExportFormat] = {
    "svg": ExportFormat.SVG,
    "pdf": ExportFormat.PDF,
    "png": ExportFormat.PNG,
    "obj": ExportFormat.OBJ,
    "ps": ExportFormat.PS,
    "eps": ExportFormat.EPS,
    "tif": ExportFormat.TIF,
    # factory CAD/cutter interchange
    "dxf": ExportFormat.DXF_AAMA_2000,
    "dxf_aama_2013": ExportFormat.DXF_AAMA_2013,
}

mcp = FastMCP(
    "pattern-forge",
    instructions=(
        "Garment pattern generation on top of Seamly2D. Typical flow: "
        "list_recipes -> describe_recipe -> draft_pattern (with the client's "
        "measurements in cm) -> open_in_seamly2d (shows the result in the real "
        "app, no manual import) and/or render_preview (PNGs viewable with Read) "
        "-> export_pattern_file (pdf for print, dxf for factory cutters). "
        "After editing options and re-drafting, call open_in_seamly2d again — "
        "it refreshes the window with the updated pattern. "
        "If draft_pattern reports input errors, relay them to the user — they "
        "describe implausible measurements or unsafe style options."
    ),
)


def _workspace() -> Path:
    ws = Path(os.environ.get("PATTERN_FORGE_WORKSPACE", str(PROJECT_ROOT / "out")))
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def _safe_name(name: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return cleaned or fallback


@mcp.tool()
def list_recipes() -> list[dict[str, str]]:
    """List the available garment recipes (name + what they produce)."""
    return [{"name": r.name, "description": r.description} for r in RECIPES.values()]


@mcp.tool()
def describe_recipe(recipe: str) -> dict[str, Any]:
    """Show what a recipe needs: required body measurements (cm, with plausible
    ranges) and its style options (with defaults and safe bounds)."""
    r = RECIPES.get(recipe)
    if r is None:
        return {"error": f"unknown recipe {recipe!r}", "available": sorted(RECIPES)}
    return {
        "name": r.name,
        "description": r.description,
        "required_measurements": [
            {
                "name": s.name,
                "min": s.min_value,
                "max": s.max_value,
                "description": s.description,
            }
            for s in r.required_measurements
        ],
        "options": [
            {
                "name": o.name,
                "default": o.default,
                "min": o.min_value,
                "max": o.max_value,
                "description": o.description,
            }
            for o in r.options
        ],
    }


@mcp.tool()
def draft_pattern(
    recipe: str,
    measurements: dict[str, float],
    options: dict[str, float] | None = None,
    name: str = "",
) -> dict[str, Any]:
    """Draft a garment pattern from body measurements (cm) and style options.

    Returns the .sm2d file path (openable in Seamly2D) plus two validation
    results: offline XSD, and the real Seamly2D recalculation (authoritative).
    On invalid inputs returns ok=false with human-readable errors instead of a file.
    """
    r = RECIPES.get(recipe)
    if r is None:
        return {"ok": False, "errors": [f"unknown recipe {recipe!r}"], "available": sorted(RECIPES)}

    try:
        doc = r.draft(measurements, options)
    except ValueError as exc:
        return {"ok": False, "errors": str(exc).splitlines()[1:] or [str(exc)]}

    path = doc.save(_workspace() / f"{_safe_name(name, r.name)}.sm2d")
    xsd_errors = validate_pattern_xml(path)

    result: dict[str, Any] = {
        "ok": not xsd_errors,
        "pattern_path": str(path),
        "xsd_valid": not xsd_errors,
        "xsd_errors": xsd_errors,
    }
    if find_seamly2d() is not None:
        check = validate_pattern(path)
        result["seamly2d_validation"] = {
            "ok": check.ok,
            "exit_code": check.exit_code,
            "meaning": check.meaning,
        }
        result["ok"] = result["ok"] and check.ok
        if not check.ok:
            result["seamly2d_stderr"] = check.stderr[-2000:]
    else:
        result["seamly2d_validation"] = "skipped: seamly2d.exe not found"
    return result


@mcp.tool()
def create_measurements_file(measurements: dict[str, float], name: str = "client") -> dict[str, Any]:
    """Save a client's body measurements (cm) as a SeamlyMe .smis file.

    Measurement names must be Seamly2D codes (waist_circ, hip_circ,
    height_waist_side, leg_crotch_to_floor, height_knee, ...)."""
    m = MeasurementsFile(unit="cm")
    try:
        m.set_many(measurements)
    except ValueError as exc:
        return {"ok": False, "errors": [str(exc)]}
    path = m.save(_workspace() / f"{_safe_name(name, 'client')}.smis")
    result: dict[str, Any] = {"ok": True, "measurements_path": str(path)}
    if find_seamlyme() is not None:
        check = validate_measurements(path)
        result["ok"] = check.ok
        result["seamlyme_validation"] = {
            "ok": check.ok,
            "exit_code": check.exit_code,
            "meaning": check.meaning,
        }
    else:
        result["seamlyme_validation"] = "skipped: seamlyme.exe not found"
    return result


@mcp.tool()
def render_preview(pattern_path: str) -> dict[str, Any]:
    """Export PNG previews of a pattern's pieces (one page per layout sheet).

    View the returned files with the Read tool to visually check the pattern."""
    path = Path(pattern_path).resolve()
    if not path.is_file():
        return {"ok": False, "errors": [f"pattern file not found: {path}"]}
    result = export_pattern(path, _workspace(), f"{path.stem}_preview", ExportFormat.PNG)
    return {
        "ok": result.ok,
        "exit_code": result.exit_code,
        "meaning": result.meaning,
        "preview_files": [str(f) for f in result.produced],
    }


@mcp.tool()
def export_pattern_file(pattern_path: str, format: str = "pdf") -> dict[str, Any]:
    """Export production files from a pattern.

    Formats: pdf (print), svg, png, tif, obj, ps, eps, and dxf / dxf_aama_2013
    (DXF-AAMA — what factory marker/cutting systems import)."""
    fmt = EXPORT_FORMATS.get(format.lower())
    if fmt is None:
        return {"ok": False, "errors": [f"unknown format {format!r}"],
                "available": sorted(EXPORT_FORMATS)}
    path = Path(pattern_path).resolve()
    if not path.is_file():
        return {"ok": False, "errors": [f"pattern file not found: {path}"]}
    result = export_pattern(path, _workspace(), f"{path.stem}_{format.lower()}", fmt)
    return {
        "ok": result.ok,
        "exit_code": result.exit_code,
        "meaning": result.meaning,
        "files": [str(f) for f in result.produced],
    }


# handle of the Seamly2D GUI window we launched (so refresh only ever closes OUR window)
_gui_process: subprocess.Popen | None = None


@mcp.tool()
def open_in_seamly2d(pattern_path: str) -> dict[str, Any]:
    """Open a pattern in the Seamly2D GUI so the user sees it immediately.

    Call this after draft_pattern so the user never has to import anything by
    hand. Calling it again after a re-draft REFRESHES the view: the previously
    opened window (only the one this server launched) is closed and the updated
    file is reopened. For quick visual checks prefer render_preview; use this
    when the user wants the real application."""
    global _gui_process
    exe = find_seamly2d()
    if exe is None:
        return {"ok": False, "errors": ["seamly2d.exe not found (see config.py lookup order)"]}
    # ALWAYS absolute: Seamly2D remembers the path it was given (recent files,
    # session restore) and a relative path breaks once its working dir differs.
    path = Path(pattern_path).resolve()
    if not path.is_file():
        return {"ok": False, "errors": [f"pattern file not found: {path}"]}

    refreshed = False
    if _gui_process is not None and _gui_process.poll() is None:
        _gui_process.terminate()
        try:
            _gui_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _gui_process.kill()
        refreshed = True

    _gui_process = subprocess.Popen([str(exe), str(path)])
    return {
        "ok": True,
        "refreshed": refreshed,
        "note": "Seamly2D window opened with the pattern"
        + (" (previous window closed to show the update)" if refreshed else ""),
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
