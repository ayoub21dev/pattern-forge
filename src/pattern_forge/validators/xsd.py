"""XSD validation of generated XML against the official Seamly2D schemas.

The schemas in ../schemas/ are copied unmodified from the Seamly2D repository
(src/libs/ifc/schema/). This is the first validation gate — cheap and offline;
the authoritative check stays `seamly2d --test` (see seamly_cli.py).
"""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from ..config import PATTERN_SCHEMA, SMIS_SCHEMA


def validate_xml(xml: str | Path, xsd_path: Path) -> list[str]:
    """Validate XML (a string or a file path) against an XSD. Returns error list; [] = valid."""
    schema = etree.XMLSchema(etree.parse(str(xsd_path)))
    if isinstance(xml, Path):
        doc = etree.parse(str(xml))
    else:
        doc = etree.fromstring(xml.encode("utf-8"))
    if schema.validate(doc):
        return []
    return [f"line {e.line}: {e.message}" for e in schema.error_log]


def validate_pattern_xml(xml: str | Path) -> list[str]:
    """Validate a .sm2d document against the pattern schema. [] = valid."""
    return validate_xml(xml, PATTERN_SCHEMA)


def validate_smis_xml(xml: str | Path) -> list[str]:
    """Validate a .smis document against the individual-measurements schema. [] = valid."""
    return validate_xml(xml, SMIS_SCHEMA)
