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

from .config import find_seamly2d, find_seamlyme
from .recipes import AlineSkirt, Skirt, Trousers
from .recipes.base import Recipe
from .smis import load_measurements
from .seamly_cli import (
    CliResult,
    ExportFormat,
    export_pattern,
    validate_measurements,
    validate_pattern,
)
from .smis import MeasurementsFile
from .validators import validate_pattern_xml

#: raw Seamly2D error patterns -> plain-language hints the AI can relay
_ERROR_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r'Unexpected token "?([#\w]+)"?'),
     "a formula references an unknown variable: {0}"),
    (re.compile(r"Error creating or updating"),
     "a drafting step failed to compute — usually impossible geometry for these values"),
    (re.compile(r"empty scene", re.IGNORECASE),
     "the pattern has no pieces, so there is nothing to export"),
    (re.compile(r"doesn't exist or is not readable"),
     "an input or output folder path was wrong"),
    (re.compile(r"process killed after \d+s timeout"),
     "Seamly2D hung and was stopped — retry; if it repeats, the pattern may be too complex"),
]


def _friendly_hint(stderr: str) -> str | None:
    """Translate raw Seamly2D stderr into one plain-language hint, if we know it."""
    for pattern, template in _ERROR_HINTS:
        match = pattern.search(stderr)
        if match:
            return template.format(*match.groups())
    return None


def _files_result(result: CliResult, files_key: str) -> dict[str, Any]:
    """Uniform dict shape for tools that run an export-style CLI call."""
    payload: dict[str, Any] = {
        "ok": result.ok,
        "exit_code": result.exit_code,
        "meaning": result.meaning,
        files_key: [str(f) for f in result.produced],
    }
    if not result.ok:
        payload["stderr"] = result.stderr[-2000:]
        hint = _friendly_hint(result.stderr)
        if hint:
            payload["hint"] = hint
    return payload

RECIPES: dict[str, Recipe] = {r.name: r for r in (AlineSkirt(), Skirt(), Trousers())}

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
        "Garment pattern generation on top of Seamly2D. Fast path: "
        "draft_and_show (draft + validate + preview + open in the app, one call). "
        "Discovery: list_recipes -> describe_recipe. Building blocks: "
        "draft_pattern, render_preview (PNGs viewable with Read), "
        "open_in_seamly2d (re-calling it refreshes the window after an edit), "
        "export_pattern_file (pdf for print, dxf for factory cutters). "
        "If a tool reports errors or a 'hint', relay it to the user — hints "
        "translate Seamly2D's raw errors into plain language."
    ),
)


def _workspace() -> Path:
    # cwd-based (not install-location-based) so it works for editable checkouts,
    # built wheels, and MCP launches alike; override with the env var
    ws = Path(os.environ.get("PATTERN_FORGE_WORKSPACE", str(Path.cwd() / "out")))
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
            hint = _friendly_hint(check.stderr)
            if hint:
                result["hint"] = hint
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
        return {"ok": False, "errors": [f"pattern file not found: {path}"], "preview_files": []}
    result = export_pattern(path, _workspace(), f"{path.stem}_preview", ExportFormat.PNG)
    return _files_result(result, "preview_files")


@mcp.tool()
def export_pattern_file(pattern_path: str, format: str = "pdf") -> dict[str, Any]:
    """Export production files from a pattern.

    Formats: pdf (print), svg, png, tif, obj, ps, eps, and dxf / dxf_aama_2013
    (DXF-AAMA — what factory marker/cutting systems import)."""
    fmt = EXPORT_FORMATS.get(format.lower())
    if fmt is None:
        return {"ok": False, "errors": [f"unknown format {format!r}"],
                "available": sorted(EXPORT_FORMATS), "files": []}
    path = Path(pattern_path).resolve()
    if not path.is_file():
        return {"ok": False, "errors": [f"pattern file not found: {path}"], "files": []}
    result = export_pattern(path, _workspace(), f"{path.stem}_{format.lower()}", fmt)
    return _files_result(result, "files")


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


def _clients_dir() -> Path:
    d = _workspace() / "clients"
    d.mkdir(parents=True, exist_ok=True)
    return d


@mcp.tool()
def save_client(name: str, measurements: dict[str, float]) -> dict[str, Any]:
    """Save a client's body measurements (cm) as a reusable profile.

    Afterwards 'draft trousers for <name>' works via get_client without
    re-typing the measurements. Overwrites an existing profile of the same name."""
    m = MeasurementsFile(unit="cm")
    try:
        m.set_many(measurements)
    except ValueError as exc:
        return {"ok": False, "errors": [str(exc)]}
    path = m.save(_clients_dir() / f"{_safe_name(name, 'client')}.smis")
    return {"ok": True, "client": _safe_name(name, "client"), "path": str(path),
            "measurements_saved": len(measurements)}


@mcp.tool()
def get_client(name: str) -> dict[str, Any]:
    """Load a saved client profile: returns their measurements dict (cm),
    ready to pass to draft_pattern / draft_and_show."""
    path = _clients_dir() / f"{_safe_name(name, 'client')}.smis"
    if not path.is_file():
        return {"ok": False, "errors": [f"no client named {name!r}"],
                "available": [p.stem for p in _clients_dir().glob("*.smis")]}
    return {"ok": True, "client": path.stem, "measurements": load_measurements(path)}


@mcp.tool()
def list_clients() -> list[dict[str, Any]]:
    """List all saved client profiles."""
    return [
        {"name": p.stem, "measurements": len(load_measurements(p))}
        for p in sorted(_clients_dir().glob("*.smis"))
    ]


@mcp.tool()
def draft_and_show(
    recipe: str,
    measurements: dict[str, float],
    options: dict[str, float] | None = None,
    name: str = "",
    open_gui: bool = True,
) -> dict[str, Any]:
    """One-shot convenience: draft + validate + render preview + open in Seamly2D.

    Equivalent to draft_pattern -> render_preview -> open_in_seamly2d in a
    single call. Returns the combined result; on drafting errors it stops
    early and returns them (nothing is opened)."""
    drafted = draft_pattern(recipe, measurements, options, name)
    if not drafted.get("ok"):
        return drafted
    result = dict(drafted)
    result["preview"] = render_preview(drafted["pattern_path"])
    if open_gui:
        result["gui"] = open_in_seamly2d(drafted["pattern_path"])
    return result


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
