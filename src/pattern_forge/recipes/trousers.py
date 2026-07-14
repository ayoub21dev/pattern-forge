"""Classic trouser block — front panel, back panel, waistband.

Drafting method: see docs/trousers-blueprint.md. The construction follows the
professional trousers draft shipped with Seamly2D (decoded point by point),
reduced to the classic block (no pockets/pleats/zipper — those are style
modules for a later phase).

Key properties:
- All geometry formulas reference increments (#...), so the pattern stays
  editable inside Seamly2D's Variables table.
- The back crotch point is placed using the *front* inseam length
  (`Line_KneeFIn_CrotchPointF`), so front and back inseams match by
  construction — the sample's own seam-matching trick.
- Curves are cubicBezier with formula-placed control points: fully parametric.
- Numeric sanity checks run in Python before drawing (a measurement set that
  produces impossible geometry is rejected with a clear message).
"""

from __future__ import annotations

import math

from ..sm2d import Document, PieceNode
from .base import MeasurementSpec, OptionSpec, Recipe

#: front/back difference: the back panel is this much wider at knee and hem (cm)
FB_DIFF = 1.0


class Trousers(Recipe):
    name = "trousers"
    description = (
        "Classic trouser block: front + back panels with darts, matched inseams, "
        "waistband. Unit: cm."
    )

    required_measurements = [
        MeasurementSpec("waist_circ", 50, 150, "waist circumference"),
        MeasurementSpec("hip_circ", 60, 170, "hip circumference"),
        MeasurementSpec("height_waist_side", 80, 130, "waist to floor, side"),
        MeasurementSpec("leg_crotch_to_floor", 55, 100, "crotch to floor"),
        MeasurementSpec("height_knee", 35, 65, "knee to floor"),
    ]

    options = [
        OptionSpec("waist_ease", 2, 0, 8, "ease added to waist"),
        OptionSpec("hip_ease", 0, 0, 8, "ease added to hip"),
        OptionSpec("knee_circ", 52, 30, 90, "finished knee circumference (style)"),
        OptionSpec("ankle_circ", 42, 20, 70, "finished hem circumference (style)"),
        OptionSpec("front_dart_width", 2, 0, 4, "front dart intake"),
        OptionSpec("back_dart_width", 3, 0, 5, "back dart intake"),
        OptionSpec("back_center_shift", 2, 0, 4, "CB shift from crease at waist"),
        OptionSpec("back_rise", 2, 0, 4, "CB raise above waist line"),
        OptionSpec("waistband_width", 4, 2, 8, "finished waistband width"),
    ]

    # ------------------------------------------------------------ validation

    def check_inputs(self, measurements: dict[str, float], options: dict[str, float]) -> list[str]:
        errors = super().check_inputs(measurements, options)
        if errors:
            return errors
        m, o = measurements, options

        # frame must stack: knee < crotch < hip line < waist
        hip_line = m["leg_crotch_to_floor"] + m["hip_circ"] / 20 + 3
        if not (m["height_knee"] < m["leg_crotch_to_floor"] < hip_line < m["height_waist_side"]):
            errors.append(
                "vertical frame is impossible: expected knee < crotch < hip line < waist "
                f"(got {m['height_knee']:g} / {m['leg_crotch_to_floor']:g} / "
                f"{hip_line:g} / {m['height_waist_side']:g})"
            )

        waist = m["waist_circ"] + o["waist_ease"]
        fpwf = m["waist_circ"] / 10 + 1.5  # crease->CF at hip
        if waist / 4 + o["front_dart_width"] - fpwf < 1:
            errors.append("front waist too small vs hip frame (waist/4 + dart barely reaches CF)")

        bpw = (m["hip_circ"] + o["hip_ease"]) / 4 + 2
        if waist / 4 + o["back_dart_width"] - o["back_center_shift"] < 1:
            errors.append("back waist too small vs back center shift")
        if bpw - bpw / 4 <= (o["knee_circ"] / 2 + FB_DIFF) / 2:
            errors.append("knee circumference too large for this hip (side seam would invert)")

        # Back crotch trick: CrotchPointB sits at the FRONT inseam length along the
        # direction back-knee-inner -> hip CB point. Verify numerically that it
        # lands near crotch height (the whole point of the construction).
        front_inseam = math.dist(
            ((o["knee_circ"] / 2 - FB_DIFF) / 2, m["height_knee"]),
            (fpwf + m["hip_circ"] / 20 + 1, m["leg_crotch_to_floor"]),
        )
        knee_b_in = ((o["knee_circ"] / 2 + FB_DIFF) / 2, m["height_knee"])
        hip_b_cb = (bpw / 4, hip_line)
        direction_len = math.dist(knee_b_in, hip_b_cb)
        ratio = front_inseam / direction_len
        landing_y = m["height_knee"] + ratio * (hip_line - m["height_knee"])
        if abs(landing_y - m["leg_crotch_to_floor"]) > 5:
            errors.append(
                "back crotch point lands too far from the crotch line "
                f"({landing_y:.1f} vs {m['leg_crotch_to_floor']:g} cm) — unusual proportions"
            )
        return errors

    # ------------------------------------------------------------ drafting

    def build(self, measurements: dict[str, float], options: dict[str, float]) -> Document:
        m, o = measurements, options
        doc = Document(
            unit="cm",
            description=(
                "Classic trouser block generated by pattern-forge. "
                "Variables (Ctrl+T) drive the geometry."
            ),
        )

        # ---- increments (numeric values computed here; geometry references them)
        def inc(name: str, value: float, desc: str) -> str:
            return doc.add_increment(name, round(value, 3), desc)

        waist = inc("#WaistCircumference", m["waist_circ"] + o["waist_ease"], "waist + ease")
        hip = inc("#HipCircumference", m["hip_circ"] + o["hip_ease"], "hip + ease")
        inc("#WaistHeight", m["height_waist_side"], "waist to floor")
        inc("#CrotchHeight", m["leg_crotch_to_floor"], "crotch to floor")
        inc("#KneeHeight", m["height_knee"], "knee to floor")
        inc("#HipLineHeight", m["leg_crotch_to_floor"] + m["hip_circ"] / 20 + 3,
            "hip line height (crotch + hip/20 + 3)")
        inc("#FrontPanelWidth", (m["hip_circ"] + o["hip_ease"]) / 4, "front width at hip")
        inc("#FrontPanelWidthFront", m["waist_circ"] / 10 + 1.5, "crease to CF at hip")
        inc("#FrontCrotchHookWidth", m["hip_circ"] / 20 + 1, "front crotch extension")
        bpw_val = (m["hip_circ"] + o["hip_ease"]) / 4 + 2
        inc("#BackPanelWidth", bpw_val, "back width at hip")
        inc("#BackPanelWidthBack", bpw_val / 4, "crease to CB at hip")
        inc("#KneeCircumference", o["knee_circ"], "knee circumference (style)")
        inc("#AnkleCircumfence", o["ankle_circ"], "hem circumference (style)")
        inc("#FrontDartWidth", o["front_dart_width"], "front dart intake")
        inc("#FrontDartDepth", 6, "front dart length")
        inc("#BackDartWidth", o["back_dart_width"], "back dart intake")
        inc("#BackDartDepth", 11, "back dart length")
        inc("#BackCenterShift", o["back_center_shift"], "CB shift at waist")
        inc("#BackRise", o["back_rise"], "CB rise above waist line")
        inc("#WaistBandWidth", o["waistband_width"], "waistband width")

        block = doc.add_draft_block("Trousers")

        # ---- vertical frame on the crease line (angle 90 = up; +x = CF/CB side)
        heel = block.add_base_point("Heel", x=0, y=0, my=1.0)
        waist_pt = block.add_end_line_point("WaistLine", heel, 90, "#WaistHeight",
                                            line_type="dashLine")
        crotch = block.add_along_line_point("CrotchLine", heel, waist_pt, "#CrotchHeight")
        hip_pt = block.add_along_line_point("HipLine", heel, waist_pt, "#HipLineHeight")
        knee = block.add_along_line_point("KneeLine", heel, waist_pt, "#KneeHeight")

        # =================================================== FRONT PANEL
        hem_f_in = block.add_end_line_point(
            "HemFIn", heel, 0, f"(#AnkleCircumfence/2 - {FB_DIFF:g})/2")
        hem_f_out = block.add_end_line_point(
            "HemFOut", heel, 180, f"(#AnkleCircumfence/2 - {FB_DIFF:g})/2")
        knee_f_in = block.add_end_line_point(
            "KneeFIn", knee, 0, f"(#KneeCircumference/2 - {FB_DIFF:g})/2")
        knee_f_out = block.add_end_line_point(
            "KneeFOut", knee, 180, f"(#KneeCircumference/2 - {FB_DIFF:g})/2")
        hip_f_cf = block.add_end_line_point("HipFCF", hip_pt, 0, "#FrontPanelWidthFront")
        hip_f_side = block.add_end_line_point(
            "HipFSide", hip_pt, 180, "#FrontPanelWidth - #FrontPanelWidthFront")
        crotch_point_f = block.add_end_line_point(
            "CrotchPointF", crotch, 0, "#FrontPanelWidthFront + #FrontCrotchHookWidth")
        waist_f_cf = block.add_intersect_xy_point("WaistFCF", hip_f_cf, waist_pt)
        waist_f_side = block.add_end_line_point(
            "WaistFSide", waist_pt, 180,
            "#WaistCircumference/4 + #FrontDartWidth - #FrontPanelWidthFront")

        # front dart (middle of the waist segment, V in the boundary)
        block.add_line(waist_f_side, waist_f_cf, line_type="dotLine", line_color="green")
        dart_center_f = block.add_along_line_point(
            "DartCenterF", waist_f_side, waist_f_cf, "Line_WaistFSide_WaistFCF/2")
        dart_f_l1 = block.add_along_line_point(
            "DartFL1", dart_center_f, waist_f_side, "#FrontDartWidth/2")
        dart_f_l2 = block.add_along_line_point(
            "DartFL2", dart_center_f, waist_f_cf, "#FrontDartWidth/2")
        dart_tip_f = block.add_normal_point(
            "DartTipF", dart_center_f, waist_f_cf, "#FrontDartDepth", angle=180)

        # front crotch curve: CF hip -> crotch point, controls formula-placed
        ctrl_f1 = block.add_end_line_point(
            "CtrlFCrotch1", hip_f_cf, 270, "(#HipLineHeight - #CrotchHeight)/2")
        ctrl_f2 = block.add_end_line_point(
            "CtrlFCrotch2", crotch_point_f, 180, "#FrontCrotchHookWidth/1.5")
        crotch_curve_f = block.add_cubic_bezier(hip_f_cf, ctrl_f1, ctrl_f2, crotch_point_f)

        # front side curve: waist -> hip
        ctrl_fs1 = block.add_end_line_point(
            "CtrlFSide1", waist_f_side, 270, "(#WaistHeight - #HipLineHeight)/2")
        ctrl_fs2 = block.add_end_line_point(
            "CtrlFSide2", hip_f_side, 90, "(#WaistHeight - #HipLineHeight)/3")
        side_curve_f = block.add_cubic_bezier(waist_f_side, ctrl_fs1, ctrl_fs2, hip_f_side)

        # visible seam lines (straight parts) — also creates Line_* variables
        block.add_line(waist_f_cf, hip_f_cf)                       # CF
        inseam_f = block.add_line(knee_f_in, crotch_point_f)       # -> Line_KneeFIn_CrotchPointF
        block.add_line(hip_f_side, knee_f_out)
        block.add_line(knee_f_out, hem_f_out)
        block.add_line(hem_f_out, hem_f_in)
        block.add_line(hem_f_in, knee_f_in)
        assert inseam_f  # documented: the back construction depends on this line's variable

        # mx offsets spread the pieces apart in details mode — pieces stacked at
        # the same origin confuse the auto-layout nesting (overlapping layouts)
        block.add_piece(
            "TrousersFront",
            nodes=[
                waist_f_cf,
                dart_f_l2, dart_tip_f, dart_f_l1,
                waist_f_side,
                side_curve_f,
                hip_f_side,
                knee_f_out, hem_f_out, hem_f_in, knee_f_in,
                crotch_point_f,
                PieceNode(crotch_curve_f, reverse=True),
                hip_f_cf,
            ],
            mx=-60,
        )

        # =================================================== BACK PANEL
        hem_b_in = block.add_end_line_point(
            "HemBIn", heel, 0, f"(#AnkleCircumfence/2 + {FB_DIFF:g})/2")
        hem_b_out = block.add_end_line_point(
            "HemBOut", heel, 180, f"(#AnkleCircumfence/2 + {FB_DIFF:g})/2")
        knee_b_in = block.add_end_line_point(
            "KneeBIn", knee, 0, f"(#KneeCircumference/2 + {FB_DIFF:g})/2")
        knee_b_out = block.add_end_line_point(
            "KneeBOut", knee, 180, f"(#KneeCircumference/2 + {FB_DIFF:g})/2")
        hip_b_cb = block.add_end_line_point("HipBCB", hip_pt, 0, "#BackPanelWidthBack")
        hip_b_side = block.add_end_line_point(
            "HipBSide", hip_pt, 180, "#BackPanelWidth - #BackPanelWidthBack")
        # the seam-matching trick (from the sample): back crotch point sits at the
        # FRONT inseam length along the direction knee -> hip CB point, so the
        # back inseam == front inseam by construction and lands ~on the crotch line
        crotch_point_b = block.add_along_line_point(
            "CrotchPointB", knee_b_in, hip_b_cb, "Line_KneeFIn_CrotchPointF")

        # back rise: CB shifted at the waist and raised
        back_waist_base = block.add_end_line_point(
            "BackWaistBase", waist_pt, 0, "#BackCenterShift", line_type="dotLine")
        waist_b_cb = block.add_end_line_point("WaistBCB", back_waist_base, 90, "#BackRise")
        waist_b_side = block.add_end_line_point(
            "WaistBSide", waist_pt, 180,
            "#WaistCircumference/4 + #BackDartWidth - #BackCenterShift")

        # back dart
        back_waist_line = block.add_line(waist_b_side, waist_b_cb)  # the tilted back waist
        assert back_waist_line
        dart_center_b = block.add_along_line_point(
            "DartCenterB", waist_b_side, waist_b_cb, "Line_WaistBSide_WaistBCB/2")
        dart_b_l1 = block.add_along_line_point(
            "DartBL1", dart_center_b, waist_b_side, "#BackDartWidth/2")
        dart_b_l2 = block.add_along_line_point(
            "DartBL2", dart_center_b, waist_b_cb, "#BackDartWidth/2")
        dart_tip_b = block.add_normal_point(
            "DartTipB", dart_center_b, waist_b_cb, "#BackDartDepth", angle=180)

        # back crotch curve
        ctrl_b1 = block.add_end_line_point(
            "CtrlBCrotch1", hip_b_cb, 270, "(#HipLineHeight - #CrotchHeight)/2")
        ctrl_b2 = block.add_end_line_point(
            "CtrlBCrotch2", crotch_point_b, 180, "#FrontCrotchHookWidth/1.2")
        crotch_curve_b = block.add_cubic_bezier(hip_b_cb, ctrl_b1, ctrl_b2, crotch_point_b)

        # back side curve waist -> hip
        ctrl_bs1 = block.add_end_line_point(
            "CtrlBSide1", waist_b_side, 270, "(#WaistHeight - #HipLineHeight)/2")
        ctrl_bs2 = block.add_end_line_point(
            "CtrlBSide2", hip_b_side, 90, "(#WaistHeight - #HipLineHeight)/3")
        side_curve_b = block.add_cubic_bezier(waist_b_side, ctrl_bs1, ctrl_bs2, hip_b_side)

        # visible seam lines
        block.add_line(waist_b_cb, hip_b_cb)                       # CB
        block.add_line(knee_b_in, crotch_point_b)                  # back inseam
        block.add_line(hip_b_side, knee_b_out)
        block.add_line(knee_b_out, hem_b_out)
        block.add_line(hem_b_out, hem_b_in)
        block.add_line(hem_b_in, knee_b_in)

        block.add_piece(
            "TrousersBack",
            nodes=[
                waist_b_cb,
                dart_b_l2, dart_tip_b, dart_b_l1,
                waist_b_side,
                side_curve_b,
                hip_b_side,
                knee_b_out, hem_b_out, hem_b_in, knee_b_in,
                crotch_point_b,
                PieceNode(crotch_curve_b, reverse=True),
                hip_b_cb,
            ],
            mx=60,
        )

        # =================================================== WAISTBAND
        wb = doc.add_draft_block("Waistband")
        wb_a = wb.add_base_point("WbA", x=0, y=0)
        wb_b = wb.add_end_line_point("WbB", wb_a, 0, "#WaistCircumference + 4",
                                     line_type="solidLine")
        wb_c = wb.add_end_line_point("WbC", wb_b, 270, "#WaistBandWidth*2",
                                     line_type="solidLine")
        wb_d = wb.add_end_line_point("WbD", wb_a, 270, "#WaistBandWidth*2",
                                     line_type="solidLine")
        wb.add_line(wb_c, wb_d)
        wb.add_piece("Waistband", nodes=[wb_a, wb_b, wb_c, wb_d], my=40)

        return doc
