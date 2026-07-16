"""Locate external resources: the Seamly2D binaries and the XSD schemas."""

from __future__ import annotations

import os
import shutil
import warnings
from pathlib import Path

# Format versions come from the writers (single source of truth) so the emitted
# XML version and the schema used for validation can never diverge.
from .sm2d.document import FORMAT_VERSION as PATTERN_FORMAT_VERSION
from .smis.writer import FORMAT_VERSION as SMIS_FORMAT_VERSION

#: package directory — valid for editable installs AND built wheels
PACKAGE_DIR = Path(__file__).resolve().parent

#: repo root — only meaningful in a source checkout (used for vendor/ lookup)
PROJECT_ROOT = PACKAGE_DIR.parents[1]
VENDOR_DIR = PROJECT_ROOT / "vendor"

#: schemas ship inside the package (copied unmodified from Seamly2D, GPLv3)
SCHEMA_DIR = PACKAGE_DIR / "schemas"
PATTERN_SCHEMA = SCHEMA_DIR / "pattern" / f"v{PATTERN_FORMAT_VERSION}.xsd"
SMIS_SCHEMA = SCHEMA_DIR / "individual_size_measurements" / f"v{SMIS_FORMAT_VERSION}.xsd"


#: positive-only cache: found binaries are remembered for the process lifetime
#: (the vendor tree walk is not free); a miss is re-checked on every call so a
#: long-running server notices a binary installed mid-session.
_found: dict[str, Path] = {}


def _find_binary(exe_name: str, env_var: str) -> Path | None:
    cached = _found.get(exe_name)
    if cached is not None:
        return cached
    result = _locate(exe_name, env_var)
    if result is not None:
        _found[exe_name] = result
    return result


def _locate(exe_name: str, env_var: str) -> Path | None:
    """Shared lookup: env var, vendor dir, standard install locations, PATH."""
    env = os.environ.get(env_var)
    if env:
        env_path = Path(env)
        if not env_path.is_file():
            # an explicit override pointing nowhere is a configuration error —
            # falling back silently would run a different binary than requested,
            # but raising here would break every None-guarding caller. Warn and
            # report "not found" instead (no silent fallback down the chain).
            warnings.warn(
                f"{env_var} is set to {env!r} but that file does not exist; "
                "treating the binary as not found (no fallback to other locations)",
                stacklevel=3,
            )
            return None
        return env_path

    if VENDOR_DIR.is_dir():
        candidate = next(VENDOR_DIR.glob(f"**/{exe_name}"), None)
        if candidate is not None:
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
