"""MCP server: lets an AI assistant draft, validate, and export garment patterns.

The AI never draws geometry — it configures validated recipes (see recipes/) and
the real Seamly2D binary is the authoritative validator behind every result.

Run standalone:  python -m pattern_forge.mcp_server   (stdio transport)
"""

from __future__ import annotations

import functools
import os
import re
import subprocess
import xml.etree.ElementTree as ET
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
    friendly_hint as _friendly_hint,  # canonical home is seamly_cli; alias kept for tests
    validate_measurements,
    validate_pattern,
)
from .smis import MeasurementsFile
from .validators import validate_pattern_xml, validate_smis_xml


def _guarded(fn):
    """MCP boundary: an unexpected exception must become a structured error,
    never a raw protocol-level tool failure."""
    @functools.wraps(fn)  # FastMCP registers tools from function name+docstring
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — deliberate boundary catch
            return {"ok": False, "errors": [f"{type(exc).__name__}: {exc}"]}
    return wrapper


def _cli_failure(result: CliResult) -> dict[str, Any]:
    """Failure payload for a failed CliResult: errors + stderr tail (+ hint)."""
    payload: dict[str, Any] = {
        "errors": [f"seamly2d: {result.meaning}"],
        "stderr": result.stderr[-2000:],
    }
    if result.hint:
        payload["hint"] = result.hint
        payload["errors"].append(result.hint)
    return payload


def _files_result(result: CliResult, files_key: str) -> dict[str, Any]:
    """Uniform dict shape for tools that run an export-style CLI call."""
    payload: dict[str, Any] = {
        "ok": result.ok,
        "exit_code": result.exit_code,
        "meaning": result.meaning,
        files_key: [str(f) for f in result.produced],
    }
    if not result.ok:
        payload.update(_cli_failure(result))
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
    # home-based, NOT cwd-based: MCP hosts launch the server from arbitrary
    # (sometimes read-only) working directories, and client profiles must land
    # in the same place across sessions; override with the env var
    ws = Path(os.environ.get("PATTERN_FORGE_WORKSPACE",
                             str(Path.home() / ".pattern-forge" / "out")))
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def _safe_name(name: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return cleaned or fallback


@mcp.tool()
@_guarded
def list_recipes() -> list[dict[str, str]]:
    """List the available garment recipes (name + what they produce)."""
    return [{"name": r.name, "description": r.description} for r in RECIPES.values()]


@mcp.tool()
@_guarded
def describe_recipe(recipe: str) -> dict[str, Any]:
    """Show what a recipe needs: required body measurements (cm, with plausible
    ranges) and its style options (with defaults and safe bounds)."""
    r = RECIPES.get(recipe)
    if r is None:
        return {"ok": False, "errors": [f"unknown recipe {recipe!r}"], "available": sorted(RECIPES)}
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
@_guarded
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

    # validate the in-memory XML (no re-read of the file we are about to write)
    xsd_errors = validate_pattern_xml(doc.to_string())
    path = doc.save(_workspace() / f"{_safe_name(name, r.name)}.sm2d")

    result: dict[str, Any] = {
        "ok": not xsd_errors,
        "pattern_path": str(path),
        "xsd_valid": not xsd_errors,
        "xsd_errors": xsd_errors,
    }
    if xsd_errors:
        result["errors"] = list(xsd_errors)
    if find_seamly2d() is not None:
        check = validate_pattern(path)
        result["seamly2d_validation"] = {
            "ok": check.ok,
            "exit_code": check.exit_code,
            "meaning": check.meaning,
        }
        result["ok"] = result["ok"] and check.ok
        if not check.ok:
            failure = _cli_failure(check)
            failure["errors"] = result.get("errors", []) + failure["errors"]
            result.update(failure)
    else:
        result["seamly2d_validation"] = "skipped: seamly2d.exe not found"
    return result


def _save_smis(measurements: dict[str, float], path: Path) -> dict[str, Any]:
    """Single save path for .smis files: sanity-check values, XSD-validate the
    in-memory XML, then write. Both measurement tools go through here so their
    guarantees can never drift apart."""
    m = MeasurementsFile(unit="cm")
    try:
        m.set_many(measurements)
    except ValueError as exc:
        return {"ok": False, "errors": [str(exc)]}
    xsd_errors = validate_smis_xml(m.to_string())
    if xsd_errors:
        return {"ok": False, "errors": list(xsd_errors), "xsd_errors": xsd_errors}
    saved = m.save(path)
    return {"ok": True, "measurements_path": str(saved), "xsd_valid": True}


@mcp.tool()
@_guarded
def create_measurements_file(measurements: dict[str, float], name: str = "client") -> dict[str, Any]:
    """Save a client's body measurements (cm) as a SeamlyMe .smis file.

    Measurement names must be Seamly2D codes (waist_circ, hip_circ,
    height_waist_side, leg_crotch_to_floor, height_knee, ...)."""
    result = _save_smis(measurements, _workspace() / f"{_safe_name(name, 'client')}.smis")
    if not result["ok"]:
        return result
    if find_seamlyme() is not None:
        check = validate_measurements(result["measurements_path"])
        result["ok"] = check.ok
        result["seamlyme_validation"] = {
            "ok": check.ok,
            "exit_code": check.exit_code,
            "meaning": check.meaning,
        }
        if not check.ok:
            result.update(_cli_failure(check))
    else:
        result["seamlyme_validation"] = "skipped: seamlyme.exe not found"
    return result


def _resolve_measurements(measurements: str | None) -> Path | None | dict[str, Any]:
    """Resolve an optional .smis path argument; error dict if it doesn't exist."""
    if measurements is None:
        return None
    m_path = Path(measurements).resolve()
    if not m_path.is_file():
        return {"ok": False, "errors": [f"measurements file not found: {m_path}"]}
    return m_path


@mcp.tool()
@_guarded
def render_preview(pattern_path: str, measurements: str | None = None) -> dict[str, Any]:
    """Export PNG previews of a pattern's pieces (one page per layout sheet).

    View the returned files with the Read tool to visually check the pattern.
    Pass `measurements` (an .smis path) for patterns that reference an
    external measurements file."""
    path = Path(pattern_path).resolve()
    if not path.is_file():
        return {"ok": False, "errors": [f"pattern file not found: {path}"], "preview_files": []}
    m_path = _resolve_measurements(measurements)
    if isinstance(m_path, dict):
        return m_path | {"preview_files": []}
    result = export_pattern(path, _workspace(), f"{path.stem}_preview", ExportFormat.PNG,
                            measurements=m_path)
    return _files_result(result, "preview_files")


@mcp.tool()
@_guarded
def export_pattern_file(pattern_path: str, format: str = "pdf",
                        measurements: str | None = None) -> dict[str, Any]:
    """Export production files from a pattern.

    Formats: pdf (print), svg, png, tif, obj, ps, eps, and dxf / dxf_aama_2013
    (DXF-AAMA — what factory marker/cutting systems import). Pass
    `measurements` (an .smis path) for patterns that reference an external
    measurements file."""
    fmt = EXPORT_FORMATS.get(format.lower())
    if fmt is None:
        return {"ok": False, "errors": [f"unknown format {format!r}"],
                "available": sorted(EXPORT_FORMATS), "files": []}
    path = Path(pattern_path).resolve()
    if not path.is_file():
        return {"ok": False, "errors": [f"pattern file not found: {path}"], "files": []}
    m_path = _resolve_measurements(measurements)
    if isinstance(m_path, dict):
        return m_path | {"files": []}
    result = export_pattern(path, _workspace(), f"{path.stem}_{format.lower()}", fmt,
                            measurements=m_path)
    return _files_result(result, "files")


# handle of the Seamly2D GUI window we launched (so refresh only ever closes OUR window)
_gui_process: subprocess.Popen | None = None


@mcp.tool()
@_guarded
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
            # short wait: a slow-closing window must not stall the whole server
            _gui_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            _gui_process.kill()
        refreshed = True

    _gui_process = subprocess.Popen([str(exe), str(path)])
    return {
        "ok": True,
        "refreshed": refreshed,
        "note": "Seamly2D window opened with the pattern"
        + (" (previous window was closed to show the update — any unsaved manual"
           " edits in it were discarded)" if refreshed else ""),
    }


def _clients_dir() -> Path:
    d = _workspace() / "clients"
    d.mkdir(parents=True, exist_ok=True)
    return d


@mcp.tool()
@_guarded
def save_client(name: str, measurements: dict[str, float]) -> dict[str, Any]:
    """Save a client's body measurements (cm) as a reusable profile.

    Afterwards 'draft trousers for <name>' works via get_client without
    re-typing the measurements. Overwrites an existing profile of the same name."""
    result = _save_smis(measurements, _clients_dir() / f"{_safe_name(name, 'client')}.smis")
    if not result["ok"]:
        return result
    result["client"] = _safe_name(name, "client")
    result["measurements_saved"] = len(measurements)
    return result


@mcp.tool()
@_guarded
def get_client(name: str) -> dict[str, Any]:
    """Load a saved client profile: returns their measurements dict (cm),
    ready to pass to draft_pattern / draft_and_show."""
    path = _clients_dir() / f"{_safe_name(name, 'client')}.smis"
    if not path.is_file():
        return {"ok": False, "errors": [f"no client named {name!r}"],
                "available": [p.stem for p in _clients_dir().glob("*.smis")]}
    try:
        measurements = load_measurements(path)
    except (ET.ParseError, ValueError, OSError) as exc:
        return {"ok": False,
                "errors": [f"profile {name!r} is unreadable ({exc}) — re-save it"]}
    return {"ok": True, "client": path.stem, "measurements": measurements}


@mcp.tool()
@_guarded
def list_clients() -> list[dict[str, Any]]:
    """List all saved client profiles."""
    entries: list[dict[str, Any]] = []
    for p in sorted(_clients_dir().glob("*.smis")):
        try:
            entries.append({"name": p.stem, "measurements": len(load_measurements(p))})
        except (ET.ParseError, ValueError, OSError) as exc:
            # one corrupt profile must not hide all the others
            entries.append({"name": p.stem, "error": f"unreadable profile: {exc}"})
    return entries


@mcp.tool()
@_guarded
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
    # draft_pattern's --test run stays even though the preview export would also
    # catch data errors: --test is the authoritative validator, and export exit
    # codes conflate "formula error" with "valid but piece-less pattern".
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
