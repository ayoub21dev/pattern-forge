"""Classic A-line skirt — front block, back block, waistband.

Construction (classic straight-skirt-to-A-line method):
- Vertical frame per panel: waist at the top, hip line #HipHeight below the
  waist, hem at #SkirtLength. Center front/back on the fold (vertical axis).
- Panel width at hip = circumference/4 (+ ease/4). Waist = waist/4 + dart.
- One waist dart per panel (deeper in the back, as bodies curve more there).
- A-line flare added at the hem from the hip line down; side seam curves
  waist->hip (cubicBezier with formula-placed controls), straight hip->hem.
- Front and back share the construction; the back gets a wider/deeper dart.

v1 simplifications (documented for the Phase-3 review): straight hem line
(no hem sweep curve), no zipper/vent, side seams equal within small tolerance.
"""

from __future__ import annotations

from ..sm2d import Document, Grainline, PieceLabel
from .base import MeasurementSpec, OptionSpec, Recipe


class Skirt(Recipe):
    name = "skirt"
    description = (
        "Classic A-line skirt: front + back blocks with waist darts, waistband. "
        "CF/CB cut on fold. Unit: cm."
    )

    required_measurements = [
        MeasurementSpec("waist_circ", 40, 160, "waist circumference"),
        MeasurementSpec("hip_circ", 60, 180, "hip circumference"),
    ]

    options = [
        OptionSpec("skirt_length", 60, 25, 120, "waist to hem"),
        OptionSpec("waist_ease", 1, 0, 6, "ease added to waist"),
        OptionSpec("hip_ease", 2, 0, 8, "ease added to hip"),
        OptionSpec("hip_height", 20, 15, 28, "waist to hip line"),
        OptionSpec("flare", 6, 0, 30, "extra hem width per half-panel (A-line)"),
        OptionSpec("front_dart_width", 2, 0, 4, "front dart intake"),
        OptionSpec("back_dart_width", 3.5, 0, 6, "back dart intake"),
        OptionSpec("waistband_width", 4, 2, 8, "finished waistband width"),
    ]

    def check_inputs(
        self, measurements: dict[str, float], options: dict[str, float] | None = None
    ) -> list[str]:
        errors = super().check_inputs(measurements, options)
        if errors:
            return errors
        m, o = measurements, self.merged_options(options)
        if o["hip_height"] >= o["skirt_length"]:
            errors.append("skirt_length must be greater than hip_height")
        # waist quarter + dart must stay narrower than the hip quarter,
        # otherwise the side seam would lean outward above the hip
        waist_q = (m["waist_circ"] + o["waist_ease"]) / 4
        hip_q = (m["hip_circ"] + o["hip_ease"]) / 4
        if waist_q + max(o["front_dart_width"], o["back_dart_width"]) > hip_q + 1:
            errors.append(
                "waist is too large relative to hip for this block "
                "(waist/4 + dart exceeds hip/4) — reduce dart width or ease"
            )
        return errors

    def _panel(self, doc: Document, side: str, dart_width: str, dart_depth: str) -> None:
        """Draw one panel (front or back) — identical construction, different dart."""
        block = doc.add_draft_block(f"Skirt{side}")
        prefix = side[0]  # F / B

        waist_cf = block.add_base_point(f"Waist{prefix}CF", x=0, y=0, my=-2)
        hip_cf = block.add_end_line_point(
            f"Hip{prefix}CF", waist_cf, 270, "#HipHeight", line_type="dashLine")
        hem_cf = block.add_end_line_point(
            f"Hem{prefix}CF", waist_cf, 270, "#SkirtLength", line_type="solidLine")

        hip_side = block.add_end_line_point(
            f"Hip{prefix}Side", hip_cf, 180, "#HipCircumference/4")
        hem_side = block.add_end_line_point(
            f"Hem{prefix}Side", hem_cf, 180, "#HipCircumference/4 + #Flare")
        waist_side = block.add_end_line_point(
            f"Waist{prefix}Side", waist_cf, 180,
            f"#WaistCircumference/4 + {dart_width}")

        # dart in the middle of the waist segment (V in the boundary)
        block.add_line(waist_side, waist_cf, line_type="dotLine", line_color="green")
        dart_center = block.add_along_line_point(
            f"DartCenter{prefix}", waist_side, waist_cf,
            f"Line_Waist{prefix}Side_Waist{prefix}CF/2")
        dart_l1 = block.add_along_line_point(
            f"Dart{prefix}L1", dart_center, waist_side, f"{dart_width}/2")
        dart_l2 = block.add_along_line_point(
            f"Dart{prefix}L2", dart_center, waist_cf, f"{dart_width}/2")
        dart_tip = block.add_normal_point(
            f"DartTip{prefix}", dart_center, waist_cf, dart_depth, angle=180)

        # side seam: curved waist->hip, straight hip->hem
        ctrl1 = block.add_end_line_point(
            f"Ctrl{prefix}Side1", waist_side, 270, "#HipHeight/2")
        ctrl2 = block.add_end_line_point(
            f"Ctrl{prefix}Side2", hip_side, 90, "#HipHeight/3")
        side_curve = block.add_cubic_bezier(waist_side, ctrl1, ctrl2, hip_side)

        block.add_line(hip_side, hem_side)
        block.add_line(hem_side, hem_cf)

        block.add_piece(
            f"Skirt{side}",
            nodes=[
                waist_cf,
                dart_l2, dart_tip, dart_l1,
                waist_side,
                side_curve,
                hip_side,
                hem_side,
                hem_cf,
            ],
            label=PieceLabel(
                (f"Skirt {side}", "cut 1 on fold"),
                letter=prefix, quantity=1, on_fold=True, mx=-14, my=25,
            ),
            grainline=Grainline(mx=-6, my=18, rotation=90, length=25),
        )

    def build(self, measurements: dict[str, float], options: dict[str, float]) -> Document:
        m, o = measurements, options
        doc = Document(
            unit="cm",
            description=(
                "Classic A-line skirt generated by pattern-forge. "
                "Variables (Ctrl+T) drive the geometry."
            ),
        )

        def inc(name: str, value: float, desc: str) -> str:
            return doc.add_increment(name, round(value, 3), desc)

        inc("#WaistCircumference", m["waist_circ"] + o["waist_ease"], "waist + ease")
        inc("#HipCircumference", m["hip_circ"] + o["hip_ease"], "hip + ease")
        inc("#SkirtLength", o["skirt_length"], "waist to hem")
        inc("#HipHeight", o["hip_height"], "waist to hip line")
        inc("#Flare", o["flare"], "extra hem width per half-panel")
        inc("#FrontDartWidth", o["front_dart_width"], "front dart intake")
        inc("#FrontDartDepth", 9, "front dart length")
        inc("#BackDartWidth", o["back_dart_width"], "back dart intake")
        inc("#BackDartDepth", 13, "back dart length")
        inc("#WaistBandWidth", o["waistband_width"], "waistband width")

        self._panel(doc, "Front", "#FrontDartWidth", "#FrontDartDepth")
        self._panel(doc, "Back", "#BackDartWidth", "#BackDartDepth")

        wb = doc.add_draft_block("SkirtWaistband")
        wb_a = wb.add_base_point("WbA", x=0, y=0)
        wb_b = wb.add_end_line_point("WbB", wb_a, 0, "#WaistCircumference + 4",
                                     line_type="solidLine")
        wb_c = wb.add_end_line_point("WbC", wb_b, 270, "#WaistBandWidth*2",
                                     line_type="solidLine")
        wb_d = wb.add_end_line_point("WbD", wb_a, 270, "#WaistBandWidth*2",
                                     line_type="solidLine")
        wb.add_line(wb_c, wb_d)
        wb.add_piece(
            "SkirtWaistband",
            nodes=[wb_a, wb_b, wb_c, wb_d],
            label=PieceLabel(("Waistband", "cut 1 on fold"), letter="W",
                             on_fold=True, mx=20, my=1.5, height=4),
            grainline=Grainline(mx=5, my=6, rotation=0, length=20),
        )

        return doc
