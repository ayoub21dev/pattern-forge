"""Shared XML serialization helpers used by both file writers (.sm2d and .smis).

Single source of truth for the on-disk contract: number formatting, indent
width, XML declaration, and encoding. Both writers delegate here so the two
file formats can never drift apart.
"""

from __future__ import annotations

import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


def fmt_value(value: str | int | float) -> str:
    """Format a formula/number attribute: numbers rendered compactly, strings as-is."""
    if isinstance(value, str):
        return value
    return format(value, "g")


def serialize_xml(root: ET.Element) -> str:
    """Pretty-print an element tree with the project's standard XML declaration."""
    ET.indent(root, space="    ")
    body = ET.tostring(root, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{body}\n'


def save_xml(root: ET.Element, path: str | Path) -> Path:
    """Serialize and write to disk (UTF-8), creating parent folders as needed.

    Atomic: written to a temp file in the same folder, then renamed over the
    destination — a crash mid-write can never leave a truncated pattern or
    measurements file behind.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(serialize_xml(root))
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return path
