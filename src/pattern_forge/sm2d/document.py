"""In-memory model + XML writer for Seamly2D pattern files (.sm2d).

Targets format version 0.6.8 — the same version as the sample patterns shipped
with Seamly2D, which the application converts up to its current format
automatically on open.

Design notes:
- Object ids are assigned by the Document (one global increasing counter),
  exactly like Seamly2D does. Recipes never manage ids by hand: creation
  methods return a PointRef which is passed to later calls.
- Formula attributes (length, angle, ...) are strings and may reference
  increments ("#WaistCirc/4 + 1") or measurement names ("waist_circ/4").
  Plain numbers are accepted and formatted.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

FORMAT_VERSION = "0.6.8"

#: line types Seamly2D accepts for construction lines
LINE_TYPES = {"none", "solidLine", "dashLine", "dotLine", "dashDotLine", "dashDotDotLine"}


@dataclass(frozen=True)
class PointRef:
    """Reference to a created point: what recipes pass around instead of raw ids."""

    id: int
    name: str


def _fmt(value: str | int | float) -> str:
    """Format a formula/number attribute: numbers rendered compactly, strings kept as-is."""
    if isinstance(value, str):
        return value
    return format(value, "g")


def _check_line_type(line_type: str) -> str:
    if line_type not in LINE_TYPES:
        raise ValueError(f"unknown lineType {line_type!r}; expected one of {sorted(LINE_TYPES)}")
    return line_type


class DraftBlock:
    """One draft block (a named drawing) inside a pattern document."""

    def __init__(self, name: str, next_id: Callable[[], int]):
        self.name = name
        self._next_id = next_id
        self._calculation: list[ET.Element] = []

    # ----------------------------------------------------------------- points

    def add_base_point(
        self,
        name: str,
        x: float = 0.0,
        y: float = 0.0,
        mx: float = 0.5,
        my: float = -1.5,
    ) -> PointRef:
        """The first, freely-placed point of a block (type="single"). x/y in pattern units."""
        pid = self._next_id()
        self._calculation.append(
            ET.Element(
                "point",
                {
                    "id": str(pid),
                    "mx": _fmt(mx),
                    "my": _fmt(my),
                    "name": name,
                    "type": "single",
                    "x": _fmt(x),
                    "y": _fmt(y),
                },
            )
        )
        return PointRef(pid, name)

    def add_end_line_point(
        self,
        name: str,
        base: PointRef,
        angle: str | float,
        length: str | float,
        line_type: str = "none",
        line_color: str = "black",
        mx: float = 0.5,
        my: float = -1.5,
    ) -> PointRef:
        """Point at angle+length from a base point (type="endLine").

        Angle convention: 0 = right, 90 = up, 180 = left, 270 = down.
        """
        pid = self._next_id()
        self._calculation.append(
            ET.Element(
                "point",
                {
                    "angle": _fmt(angle),
                    "basePoint": str(base.id),
                    "id": str(pid),
                    "length": _fmt(length),
                    "lineColor": line_color,
                    "lineType": _check_line_type(line_type),
                    "mx": _fmt(mx),
                    "my": _fmt(my),
                    "name": name,
                    "type": "endLine",
                },
            )
        )
        return PointRef(pid, name)

    def add_along_line_point(
        self,
        name: str,
        first: PointRef,
        second: PointRef,
        length: str | float,
        line_type: str = "none",
        line_color: str = "black",
        mx: float = 0.5,
        my: float = -1.5,
    ) -> PointRef:
        """Point on the line first->second at the given length from `first` (type="alongLine")."""
        pid = self._next_id()
        self._calculation.append(
            ET.Element(
                "point",
                {
                    "firstPoint": str(first.id),
                    "id": str(pid),
                    "length": _fmt(length),
                    "lineColor": line_color,
                    "lineType": _check_line_type(line_type),
                    "mx": _fmt(mx),
                    "my": _fmt(my),
                    "name": name,
                    "secondPoint": str(second.id),
                    "type": "alongLine",
                },
            )
        )
        return PointRef(pid, name)

    def add_normal_point(
        self,
        name: str,
        first: PointRef,
        second: PointRef,
        length: str | float,
        angle: str | float = 0,
        line_type: str = "none",
        line_color: str = "black",
        mx: float = 0.5,
        my: float = -1.5,
    ) -> PointRef:
        """Point on the normal (perpendicular) of line first->second at `first` (type="normal").

        `angle` is an extra rotation added to the perpendicular (0 keeps the true normal).
        """
        pid = self._next_id()
        self._calculation.append(
            ET.Element(
                "point",
                {
                    "angle": _fmt(angle),
                    "firstPoint": str(first.id),
                    "id": str(pid),
                    "length": _fmt(length),
                    "lineColor": line_color,
                    "lineType": _check_line_type(line_type),
                    "mx": _fmt(mx),
                    "my": _fmt(my),
                    "name": name,
                    "secondPoint": str(second.id),
                    "type": "normal",
                },
            )
        )
        return PointRef(pid, name)

    # ------------------------------------------------------------ lines/curves

    def add_line(
        self,
        first: PointRef,
        second: PointRef,
        line_type: str = "solidLine",
        line_color: str = "black",
    ) -> int:
        """Visible construction line between two points. Returns the element id."""
        lid = self._next_id()
        self._calculation.append(
            ET.Element(
                "line",
                {
                    "firstPoint": str(first.id),
                    "id": str(lid),
                    "lineColor": line_color,
                    "lineType": _check_line_type(line_type),
                    "secondPoint": str(second.id),
                },
            )
        )
        return lid

    def add_simple_spline(
        self,
        p1: PointRef,
        p4: PointRef,
        angle1: str | float,
        angle2: str | float,
        length1: str | float,
        length2: str | float,
        color: str = "black",
    ) -> int:
        """Cubic curve between two points (type="simpleInteractive").

        angle1/length1 describe the control handle leaving p1; angle2/length2 the
        handle at p4 (pointing back along the curve, usually ~travel angle + 180).
        Returns the element id.
        """
        sid = self._next_id()
        self._calculation.append(
            ET.Element(
                "spline",
                {
                    "angle1": _fmt(angle1),
                    "angle2": _fmt(angle2),
                    "color": color,
                    "id": str(sid),
                    "length1": _fmt(length1),
                    "length2": _fmt(length2),
                    "point1": str(p1.id),
                    "point4": str(p4.id),
                    "type": "simpleInteractive",
                },
            )
        )
        return sid

    # ---------------------------------------------------------------- output

    def to_element(self) -> ET.Element:
        block = ET.Element("draftBlock", {"name": self.name})
        calculation = ET.SubElement(block, "calculation")
        calculation.extend(self._calculation)
        ET.SubElement(block, "modeling")
        ET.SubElement(block, "pieces")
        return block


class Document:
    """A whole .sm2d pattern file."""

    def __init__(self, unit: str = "cm", description: str = "", notes: str = ""):
        if unit not in ("mm", "cm", "inch"):
            raise ValueError(f"unit must be mm/cm/inch, got {unit!r}")
        self.unit = unit
        self.description = description
        self.notes = notes
        #: path to a .smis/.smms measurements file (as stored in the pattern), "" = none
        self.measurements = ""
        self._increments: list[tuple[str, str, str]] = []
        self._blocks: list[DraftBlock] = []
        self._id_counter = 0

    def _next_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    def add_increment(self, name: str, formula: str | int | float, description: str = "") -> str:
        """Add a custom variable (increment). Name must start with '#'. Returns the name."""
        if not name.startswith("#"):
            raise ValueError(f"increment names must start with '#', got {name!r}")
        self._increments.append((name, _fmt(formula), description))
        return name

    def add_draft_block(self, name: str) -> DraftBlock:
        block = DraftBlock(name, self._next_id)
        self._blocks.append(block)
        return block

    # ---------------------------------------------------------------- output

    def to_element(self) -> ET.Element:
        root = ET.Element("pattern")
        root.append(ET.Comment("Pattern created with pattern-forge (Seamly2D-compatible)."))
        ET.SubElement(root, "version").text = FORMAT_VERSION
        ET.SubElement(root, "unit").text = self.unit
        ET.SubElement(root, "description").text = self.description or None
        ET.SubElement(root, "notes").text = self.notes or None
        ET.SubElement(root, "measurements").text = self.measurements or None
        increments = ET.SubElement(root, "increments")
        for name, formula, description in self._increments:
            ET.SubElement(
                increments,
                "increment",
                {"description": description, "formula": formula, "name": name},
            )
        for block in self._blocks:
            root.append(block.to_element())
        return root

    def to_string(self) -> str:
        root = self.to_element()
        ET.indent(root, space="    ")
        body = ET.tostring(root, encoding="unicode")
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{body}\n'

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_string(), encoding="utf-8")
        return path
