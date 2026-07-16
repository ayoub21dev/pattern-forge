"""Wrapper around the real Seamly2D binaries, used headlessly.

Verified CLI contract (from Seamly2D sources, src/app/seamly2d/core/vcmdexport.cpp):

- Validation:  seamly2d <file.sm2d> --test [-m <file.smis>]
  Loads the pattern, recalculates every formula, exits without showing a window.
- Export:      seamly2d <file.sm2d> -p 0 -d <outdir> -b <basename> -f <format> [-m <file.smis>]
  Exports the pattern pieces layout. NOTE: patterns without pieces export as an
  "empty scene" and fail with exit code 65 — validation still works for them.

Exit codes (src/libs/vmisc/vsysexits.h):
  0  = OK
  64 = usage error (bad flags)
  65 = data error (formula/parse/measurement problem, or empty scene on export)
  66 = input file missing or unreadable
  70 = internal software error
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

from .config import find_seamly2d, find_seamlyme

#: synthetic exit code used when the process had to be killed on timeout
EXIT_TIMEOUT = -1

EXIT_MEANINGS = {
    0: "ok",
    64: "usage error (bad command line)",
    65: "pattern data error (formula / measurement / empty scene)",
    66: "input file missing or unreadable",
    70: "internal software error",
    EXIT_TIMEOUT: "timed out (process killed)",
}

#: raw Seamly2D error patterns -> plain-language hints any consumer can relay
ERROR_HINTS: list[tuple[re.Pattern[str], str]] = [
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


def friendly_hint(stderr: str) -> str | None:
    """Translate raw Seamly2D stderr into one plain-language hint, if we know it."""
    for pattern, template in ERROR_HINTS:
        match = pattern.search(stderr)
        if match:
            return template.format(*match.groups())
    return None


def _abs(path: str | Path) -> str:
    """Absolute form of a path argument — the ONE invariant of this module:
    Seamly2D binaries change their own cwd and remember the paths they're given,
    so every filesystem path on the command line must be absolute."""
    return str(Path(path).resolve())


class ExportFormat(IntEnum):
    """Values of the -f flag (LayoutExportFormat enum in src/libs/vmisc/def.h)."""

    SVG = 0
    PDF = 1
    PDF_TILED = 2
    PNG = 3
    JPG = 4
    BMP = 5
    PPM = 6
    OBJ = 7
    PS = 8   # needs pdftops next to seamly2d.exe
    EPS = 9  # needs pdftops next to seamly2d.exe
    DXF_FLAT_R10 = 10
    DXF_FLAT_2013 = 18
    DXF_AAMA_R10 = 19
    DXF_AAMA_2000 = 23
    DXF_AAMA_2013 = 27
    TIF = 37

    @property
    def extension(self) -> str:
        if self.name.startswith("DXF"):
            return "dxf"
        if self in (ExportFormat.PDF_TILED,):
            return "pdf"
        return self.name.lower().split("_")[0]


@dataclass
class CliResult:
    ok: bool
    exit_code: int
    meaning: str
    stdout: str
    stderr: str
    produced: list[Path] = field(default_factory=list)

    @classmethod
    def from_run(cls, code: int, out: str, err: str, produced: list[Path] | None = None) -> "CliResult":
        """Single owner of the exit-code contract (ok + meaning derivation)."""
        return cls(
            ok=code == 0,
            exit_code=code,
            meaning=EXIT_MEANINGS.get(code, f"unknown exit code {code}"),
            stdout=out,
            stderr=err,
            produced=produced or [],
        )

    @property
    def hint(self) -> str | None:
        """Plain-language translation of stderr, if we recognize the error."""
        return friendly_hint(self.stderr)


class SeamlyNotFoundError(RuntimeError):
    pass


def _require(exe: Path | None, finder, what: str) -> Path:
    exe = exe or finder()
    if exe is None:
        raise SeamlyNotFoundError(
            f"{what} not found. Set the env var or put the app under vendor/. See config.py."
        )
    return exe


def _run(cmd: list[str], timeout: int) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        # a hung binary (modal dialog, giant pattern) must surface as a normal
        # failed CliResult, not as an exception crashing the caller/MCP tool
        out = exc.stdout if isinstance(exc.stdout, str) else ""
        err = exc.stderr if isinstance(exc.stderr, str) else ""
        return EXIT_TIMEOUT, out, f"{err}\nprocess killed after {timeout}s timeout".strip()
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def validate_pattern(
    pattern: str | Path,
    measurements: str | Path | None = None,
    exe: Path | None = None,
    timeout: int = 180,
) -> CliResult:
    """Run `seamly2d <pattern> --test [-m measurements]` and report the outcome."""
    exe = _require(exe, find_seamly2d, "seamly2d.exe")
    cmd = [str(exe), _abs(pattern), "--test"]
    if measurements is not None:
        cmd += ["-m", _abs(measurements)]
    return CliResult.from_run(*_run(cmd, timeout))


def export_pattern(
    pattern: str | Path,
    out_dir: str | Path,
    basename: str,
    fmt: ExportFormat = ExportFormat.SVG,
    measurements: str | Path | None = None,
    page_template: int = 0,
    gap_width: float = 2.0,
    details_only: bool = True,
    exe: Path | None = None,
    timeout: int = 300,
) -> CliResult:
    """Run a headless layout export. Requires the pattern to contain pieces.

    details_only=True exports pieces at their details-mode positions (our
    recipes set spread-out positions) instead of Seamly2D's auto-nesting —
    the auto-layout was observed to overlap large concave pieces (two slim
    trouser legs). Factory marker software re-nests DXF pieces anyway.
    gap_width (cm) applies only to the auto-layout path (details_only=False).
    """
    exe = _require(exe, find_seamly2d, "seamly2d.exe")
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    # Seamly2D's output naming contract: <basename>_layout_NN.<ext> (auto-layout,
    # one per sheet) or <basename>_pieces.<ext> (details mode). Matching that
    # contract EXACTLY (with the basename escaped) is what makes the stale-file
    # cleanup and the `produced` list safe: a plain prefix glob would delete or
    # claim files of another pattern whose name merely starts the same.
    output_name = re.compile(
        rf"^{re.escape(basename)}(_layout_\d+|_pieces)\.{re.escape(fmt.extension)}$"
    )
    # Export into a temp dir inside out_dir (same volume) so a failed re-export
    # never destroys the last good files; only a successful run replaces them.
    tmp_dir = Path(tempfile.mkdtemp(dir=out_dir, prefix=".export-"))
    try:
        cmd = [
            str(exe),
            _abs(pattern),
            "-p",
            str(page_template),
            "-d",
            str(tmp_dir),
            "-b",
            basename,
            "-f",
            str(int(fmt)),
        ]
        if details_only:
            cmd += ["--exportOnlyDetails"]
        else:
            # gap between pieces: Seamly2D requires the full chain -s + -l + -G
            # (shift length, layout units, gap width) to be set together
            cmd += ["-s", "0", "-l", "cm", "-G", str(gap_width)]
        if measurements is not None:
            cmd += ["-m", _abs(measurements)]
        code, out, err = _run(cmd, timeout)
        new_files = sorted(
            f for f in tmp_dir.iterdir() if f.is_file() and output_name.match(f.name)
        )
        produced: list[Path] = []
        if code == 0 and new_files:
            # success: NOW clear the previous run's outputs, then move the new ones in
            for stale in out_dir.iterdir():
                if stale.is_file() and output_name.match(stale.name):
                    stale.unlink()
            for f in new_files:
                target = out_dir / f.name
                os.replace(f, target)
                produced.append(target)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    result = CliResult.from_run(code, out, err, produced)
    if result.ok and not result.produced:
        # exit 0 with nothing written (e.g. PS/EPS without pdftops) is NOT success
        result.ok = False
        result.meaning = "exit 0 but no output files were produced"
    return result


def validate_measurements(
    measurements: str | Path,
    exe: Path | None = None,
    timeout: int = 120,
) -> CliResult:
    """Run `seamlyme <file> --test` to validate a .smis/.smms measurements file."""
    exe = _require(exe, find_seamlyme, "seamlyme.exe")
    cmd = [str(exe), _abs(measurements), "--test"]
    return CliResult.from_run(*_run(cmd, timeout))
