"""Shared XML serialization helpers used by both file writers (.sm2d and .smis).

Single source of truth for the on-disk contract: number formatting, indent
width, XML declaration, and encoding. Both writers delegate here so the two
file formats can never drift apart.
"""

from __future__ import annotations

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
    """Serialize and write to disk (UTF-8), creating parent folders as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_xml(root), encoding="utf-8")
    return path
