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

import subprocess
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

from .config import find_seamly2d, find_seamlyme

EXIT_MEANINGS = {
    0: "ok",
    64: "usage error (bad command line)",
    65: "pattern data error (formula / measurement / empty scene)",
    66: "input file missing or unreadable",
    70: "internal software error",
}


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
    produced: list[Path]

    def raise_for_error(self) -> "CliResult":
        if not self.ok:
            detail = self.stderr.strip() or self.stdout.strip()
            raise RuntimeError(f"seamly2d failed ({self.meaning})\n{detail}")
        return self


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
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def validate_pattern(
    pattern: str | Path,
    measurements: str | Path | None = None,
    exe: Path | None = None,
    timeout: int = 180,
) -> CliResult:
    """Run `seamly2d <pattern> --test [-m measurements]` and report the outcome."""
    exe = _require(exe, find_seamly2d, "seamly2d.exe")
    cmd = [str(exe), str(Path(pattern)), "--test"]
    if measurements is not None:
        cmd += ["-m", str(Path(measurements))]
    code, out, err = _run(cmd, timeout)
    return CliResult(
        ok=code == 0,
        exit_code=code,
        meaning=EXIT_MEANINGS.get(code, f"unknown exit code {code}"),
        stdout=out,
        stderr=err,
        produced=[],
    )


def export_pattern(
    pattern: str | Path,
    out_dir: str | Path,
    basename: str,
    fmt: ExportFormat = ExportFormat.SVG,
    measurements: str | Path | None = None,
    page_template: int = 0,
    exe: Path | None = None,
    timeout: int = 300,
) -> CliResult:
    """Run a headless layout export. Requires the pattern to contain pieces."""
    exe = _require(exe, find_seamly2d, "seamly2d.exe")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(exe),
        str(Path(pattern)),
        "-p",
        str(page_template),
        "-d",
        str(out_dir),
        "-b",
        basename,
        "-f",
        str(int(fmt)),
    ]
    if measurements is not None:
        cmd += ["-m", str(Path(measurements))]
    code, out, err = _run(cmd, timeout)
    produced = sorted(out_dir.glob(f"{basename}*.{fmt.extension}"))
    return CliResult(
        ok=code == 0,
        exit_code=code,
        meaning=EXIT_MEANINGS.get(code, f"unknown exit code {code}"),
        stdout=out,
        stderr=err,
        produced=produced,
    )


def validate_measurements(
    measurements: str | Path,
    exe: Path | None = None,
    timeout: int = 120,
) -> CliResult:
    """Run `seamlyme <file> --test` to validate a .smis/.smms measurements file."""
    exe = _require(exe, find_seamlyme, "seamlyme.exe")
    cmd = [str(exe), str(Path(measurements)), "--test"]
    code, out, err = _run(cmd, timeout)
    return CliResult(
        ok=code == 0,
        exit_code=code,
        meaning=EXIT_MEANINGS.get(code, f"unknown exit code {code}"),
        stdout=out,
        stderr=err,
        produced=[],
    )
