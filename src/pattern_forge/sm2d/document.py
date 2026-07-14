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

from ..xmlio import fmt_value as _fmt
from ..xmlio import save_xml, serialize_xml

FORMAT_VERSION = "0.6.8"

#: horizontal pitch (cm) between auto-placed pieces in details mode
PIECE_PLACEMENT_PITCH = 80.0

#: line types Seamly2D accepts for construction lines
LINE_TYPES = {"none", "solidLine", "dashLine", "dotLine", "dashDotLine", "dashDotDotLine"}


@dataclass(frozen=True)
class PointRef:
    """Reference to a created point: what recipes pass around instead of raw ids."""

    id: int
    name: str


@dataclass(frozen=True)
class CurveRef:
    """Reference to a created curve.

    kind: "spline" (simpleInteractive / cubicBezier) or "splinePath"
    (pathInteractive) — pieces need to know which node type to emit.
    """

    id: int
    kind: str  # "spline" | "splinePath"


@dataclass(frozen=True)
class PieceNode:
    """One boundary node of a piece: a point, or a curve with direction."""

    ref: PointRef | CurveRef
    reverse: bool = False


def _check_line_type(line_type: str) -> str:
    if line_type not in LINE_TYPES:
        raise ValueError(f"unknown lineType {line_type!r}; expected one of {sorted(LINE_TYPES)}")
    return line_type


class DraftBlock:
    """One draft block (a named drawing) inside a pattern document."""

    def __init__(self, name: str, next_id: Callable[[], int], next_piece_slot: Callable[[], int]):
        self.name = name
        self._next_id = next_id
        self._next_piece_slot = next_piece_slot
        self._calculation: list[ET.Element] = []
        self._modeling: list[ET.Element] = []
        self._pieces: list[ET.Element] = []

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

    def add_intersect_xy_point(
        self,
        name: str,
        first: PointRef,
        second: PointRef,
        line_type: str = "none",
        line_color: str = "black",
        mx: float = 0.5,
        my: float = -1.5,
    ) -> PointRef:
        """Point at (x of `first`, y of `second`) — type="intersectXY"."""
        pid = self._next_id()
        self._calculation.append(
            ET.Element(
                "point",
                {
                    "firstPoint": str(first.id),
                    "id": str(pid),
                    "lineColor": line_color,
                    "lineType": _check_line_type(line_type),
                    "mx": _fmt(mx),
                    "my": _fmt(my),
                    "name": name,
                    "secondPoint": str(second.id),
                    "type": "intersectXY",
                },
            )
        )
        return PointRef(pid, name)

    def add_line_intersect_point(
        self,
        name: str,
        line1: tuple[PointRef, PointRef],
        line2: tuple[PointRef, PointRef],
        mx: float = 0.5,
        my: float = -1.5,
    ) -> PointRef:
        """Intersection of the lines line1 and line2 — type="lineIntersect"."""
        pid = self._next_id()
        self._calculation.append(
            ET.Element(
                "point",
                {
                    "id": str(pid),
                    "mx": _fmt(mx),
                    "my": _fmt(my),
                    "name": name,
                    "p1Line1": str(line1[0].id),
                    "p1Line2": str(line1[1].id),
                    "p2Line1": str(line2[0].id),
                    "p2Line2": str(line2[1].id),
                    "type": "lineIntersect",
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
    ) -> CurveRef:
        """Cubic curve between two points (type="simpleInteractive").

        angle1/length1 describe the control handle leaving p1; angle2/length2 the
        handle at p4 (pointing back along the curve, usually ~travel angle + 180).
        NOTE: handle angles/lengths here are numbers; for fully parametric curves
        prefer add_cubic_bezier with formula-placed control points.
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
        return CurveRef(sid, "spline")

    def add_cubic_bezier(
        self,
        p1: PointRef,
        control1: PointRef,
        control2: PointRef,
        p4: PointRef,
        color: str = "black",
    ) -> CurveRef:
        """Cubic Bézier whose control handles are real points (type="cubicBezier").

        Because the control points are constructed with formulas, the curve is
        fully parametric — it re-adapts when measurements change. This is the
        technique the professional trousers sample uses for its waist curves.
        """
        sid = self._next_id()
        self._calculation.append(
            ET.Element(
                "spline",
                {
                    "color": color,
                    "id": str(sid),
                    "point1": str(p1.id),
                    "point2": str(control1.id),
                    "point3": str(control2.id),
                    "point4": str(p4.id),
                    "type": "cubicBezier",
                },
            )
        )
        return CurveRef(sid, "spline")

    # ---------------------------------------------------------------- pieces

    def add_piece(
        self,
        name: str,
        nodes: list[PointRef | CurveRef | PieceNode],
        seam_allowance_width: float = 1.0,
        mx: float | None = None,
        my: float | None = None,
    ) -> int:
        """Define a pattern piece from an ordered boundary of points and curves.

        This is what makes the pattern exportable (PDF/DXF layouts are built
        from pieces). For each boundary object a "modeling proxy" element is
        created automatically, exactly as Seamly2D does when the user builds a
        piece in the GUI. Pass PieceNode(curve, reverse=True) when the curve
        must be walked backwards along the boundary.

        Placement: pieces are auto-spread horizontally (one document-wide slot
        per piece, PIECE_PLACEMENT_PITCH apart) so details-mode exports never
        stack pieces on top of each other. Pass mx/my to override.
        """
        slot = self._next_piece_slot()
        if mx is None:
            mx = PIECE_PLACEMENT_PITCH * slot
        if my is None:
            my = 0.0
        normalized = [n if isinstance(n, PieceNode) else PieceNode(n) for n in nodes]
        if len(normalized) < 3:
            raise ValueError("a piece needs at least 3 boundary nodes")

        proxies: list[ET.Element] = []
        node_elements: list[ET.Element] = []
        for node in normalized:
            proxy_id = self._next_id()
            if isinstance(node.ref, PointRef):
                proxies.append(
                    ET.Element(
                        "point",
                        {
                            "id": str(proxy_id),
                            "idObject": str(node.ref.id),
                            "inUse": "true",
                            "mx": "0.1",
                            "my": "0.2",
                            "type": "modeling",
                        },
                    )
                )
                node_elements.append(
                    ET.Element("node", {"idObject": str(proxy_id), "type": "NodePoint"})
                )
            else:
                is_path = node.ref.kind == "splinePath"
                proxies.append(
                    ET.Element(
                        "spline",
                        {
                            "id": str(proxy_id),
                            "idObject": str(node.ref.id),
                            "inUse": "true",
                            "type": "modelingPath" if is_path else "modelingSpline",
                        },
                    )
                )
                node_elements.append(
                    ET.Element(
                        "node",
                        {
                            "idObject": str(proxy_id),
                            "reverse": "1" if node.reverse else "0",
                            "type": "NodeSplinePath" if is_path else "NodeSpline",
                        },
                    )
                )

        piece_id = self._next_id()
        piece = ET.Element(
            "piece",
            {
                "closed": "1",
                "id": str(piece_id),
                "mx": _fmt(mx),
                "my": _fmt(my),
                "name": name,
                "seamAllowance": "1",
                "version": "2",
                "width": _fmt(seam_allowance_width),
            },
        )
        ET.SubElement(
            piece,
            "data",
            {
                "annotation": "", "foldPosition": "", "fontSize": "0", "height": "",
                "letter": "", "mx": "0", "my": "0", "onFold": "false", "orientation": "",
                "quantity": "1", "rotation": "", "rotationWay": "", "tilt": "",
                "visible": "false", "width": "",
            },
        )
        ET.SubElement(
            piece,
            "patternInfo",
            {"fontSize": "0", "height": "", "mx": "0", "my": "0", "rotation": "",
             "visible": "false", "width": ""},
        )
        ET.SubElement(
            piece,
            "grainline",
            {"arrows": "0", "length": "", "mx": "0", "my": "0", "rotation": "",
             "visible": "false"},
        )
        nodes_el = ET.SubElement(piece, "nodes")
        nodes_el.extend(node_elements)

        self._modeling.extend(proxies)
        self._pieces.append(piece)
        return piece_id

    # ---------------------------------------------------------------- output

    def to_element(self) -> ET.Element:
        block = ET.Element("draftBlock", {"name": self.name})
        calculation = ET.SubElement(block, "calculation")
        calculation.extend(self._calculation)
        modeling = ET.SubElement(block, "modeling")
        modeling.extend(self._modeling)
        pieces = ET.SubElement(block, "pieces")
        pieces.extend(self._pieces)
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
        self._piece_counter = 0

    def _next_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    def _next_piece_slot(self) -> int:
        """Document-wide piece index used for automatic details-mode placement."""
        slot = self._piece_counter
        self._piece_counter += 1
        return slot

    def add_increment(self, name: str, formula: str | int | float, description: str = "") -> str:
        """Add a custom variable (increment). Name must start with '#'. Returns the name."""
        if not name.startswith("#"):
            raise ValueError(f"increment names must start with '#', got {name!r}")
        self._increments.append((name, _fmt(formula), description))
        return name

    def add_draft_block(self, name: str) -> DraftBlock:
        block = DraftBlock(name, self._next_id, self._next_piece_slot)
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
        return serialize_xml(self.to_element())

    def save(self, path: str | Path) -> Path:
        return save_xml(self.to_element(), path)
