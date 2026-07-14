"""Locate external resources: the Seamly2D binaries and the XSD schemas."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VENDOR_DIR = PROJECT_ROOT / "vendor"
SCHEMA_DIR = PROJECT_ROOT / "schemas"

# Format versions this engine writes (they match the samples shipped with Seamly2D;
# the app converts them up to its current format automatically on open).
PATTERN_FORMAT_VERSION = "0.6.8"
SMIS_FORMAT_VERSION = "0.3.4"

PATTERN_SCHEMA = SCHEMA_DIR / "pattern" / f"v{PATTERN_FORMAT_VERSION}.xsd"
SMIS_SCHEMA = SCHEMA_DIR / "individual_size_measurements" / f"v{SMIS_FORMAT_VERSION}.xsd"


def _find_binary(exe_name: str, env_var: str) -> Path | None:
    """Shared lookup: env var, vendor dir, standard install locations, PATH."""
    env = os.environ.get(env_var)
    if env and Path(env).is_file():
        return Path(env)

    if VENDOR_DIR.is_dir():
        for candidate in sorted(VENDOR_DIR.glob(f"**/{exe_name}")):
            return candidate

    for candidate in (
        Path(r"C:\Program Files\Seamly2D") / exe_name,
        Path(r"C:\Program Files (x86)\Seamly2D") / exe_name,
    ):
        if candidate.is_file():
            return candidate

    which = shutil.which(exe_name.removesuffix(".exe"))
    return Path(which) if which else None


def find_seamly2d() -> Path | None:
    """Full path to seamly2d.exe, or None if not installed anywhere we know."""
    return _find_binary("seamly2d.exe", "PATTERN_FORGE_SEAMLY2D")


def find_seamlyme() -> Path | None:
    """Full path to seamlyme.exe, or None if not installed anywhere we know."""
    return _find_binary("seamlyme.exe", "PATTERN_FORGE_SEAMLYME")
