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
from typing import NamedTuple

from ..sm2d import Document, Grainline, PieceLabel, PieceNode
from ..sm2d.document import DraftBlock, PointRef
from .base import MeasurementSpec, OptionSpec, Recipe
from .components import add_waistband_block

#: front/back difference: the back panel is this much wider at knee and hem (cm)
FB_DIFF = 1.0


class _Frame(NamedTuple):
    """The shared vertical construction frame on the crease line."""

    heel: PointRef
    waist_pt: PointRef
    crotch: PointRef
    hip_pt: PointRef
    knee: PointRef


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

    def check_inputs(
        self, measurements: dict[str, float], options: dict[str, float] | None = None
    ) -> list[str]:
        errors = super().check_inputs(measurements, options)
        if errors:
            return errors
        # merged_options keeps the never-raise contract even for a partial dict
        m, o = measurements, self.merged_options(options)

        # frame must stack: knee < crotch < hip line < waist
        hip_line = m["leg_crotch_to_floor"] + m["hip_circ"] / 20 + 3
        if not (m["height_knee"] < m["leg_crotch_to_floor"] < hip_line < m["height_waist_side"]):
            errors.append(
                "vertical frame is impossible: expected knee < crotch < hip line < waist "
                f"(got {m['height_knee']:g} / {m['leg_crotch_to_floor']:g} / "
                f"{hip_line:g} / {m['height_waist_side']:g})"
            )
            # every check below assumes a sane frame (the crotch-landing
            # simulation would even divide by zero on a degenerate one)
            return errors

        waist = m["waist_circ"] + o["waist_ease"]
        fpwf = m["waist_circ"] / 10 + 1.5  # crease->CF at hip
        if waist / 4 + o["front_dart_width"] - fpwf < 1:
            errors.append("front waist too small vs hip frame (waist/4 + dart barely reaches CF)")

        fpw = (m["hip_circ"] + o["hip_ease"]) / 4
        bpw = fpw + 2
        if waist / 4 + o["back_dart_width"] - o["back_center_shift"] < 1:
            errors.append("back waist too small vs back center shift")
        # the FRONT panel is narrower at the hip than the back, so it inverts first
        if fpw - fpwf <= (o["knee_circ"] / 2 - FB_DIFF) / 2:
            errors.append("knee circumference too large for this hip (front side seam would invert)")
        if bpw - bpw / 4 <= (o["knee_circ"] / 2 + FB_DIFF) / 2:
            errors.append("knee circumference too large for this hip (back side seam would invert)")

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

    def _leg_panel(
        self,
        block: DraftBlock,
        frame: _Frame,
        *,
        back: bool,
        prefix: str,
        center: str,
        hip_center_len: str,
        hip_side_len: str,
        waist_side_len: str,
        dart_width: str,
        dart_depth: str,
        crotch_ctrl_div: str,
        label_title: str,
        label_letter: str,
    ) -> None:
        """Draw one leg panel (front or back) — same construction, three
        asymmetries handled by `back`: the FB width term flips sign, the crotch
        point is placed differently, and the waist center is built differently.
        """
        sign = "+" if back else "-"
        hem_in = block.add_end_line_point(
            f"Hem{prefix}In", frame.heel, 0, f"(#AnkleCircumference/2 {sign} {FB_DIFF:g})/2")
        hem_out = block.add_end_line_point(
            f"Hem{prefix}Out", frame.heel, 180, f"(#AnkleCircumference/2 {sign} {FB_DIFF:g})/2")
        knee_in = block.add_end_line_point(
            f"Knee{prefix}In", frame.knee, 0, f"(#KneeCircumference/2 {sign} {FB_DIFF:g})/2")
        knee_out = block.add_end_line_point(
            f"Knee{prefix}Out", frame.knee, 180, f"(#KneeCircumference/2 {sign} {FB_DIFF:g})/2")
        hip_center = block.add_end_line_point(
            f"Hip{prefix}{center}", frame.hip_pt, 0, hip_center_len)
        hip_side = block.add_end_line_point(
            f"Hip{prefix}Side", frame.hip_pt, 180, hip_side_len)

        if back:
            # the seam-matching trick (from the sample): back crotch point sits at
            # the FRONT inseam length along the direction knee -> hip CB point, so
            # the back inseam == front inseam by construction and lands ~on the
            # crotch line
            crotch_point = block.add_along_line_point(
                f"CrotchPoint{prefix}", knee_in, hip_center, "Line_KneeFIn_CrotchPointF")
            # back rise: CB shifted at the waist and raised
            back_waist_base = block.add_end_line_point(
                "BackWaistBase", frame.waist_pt, 0, "#BackCenterShift", line_type="dotLine")
            waist_center = block.add_end_line_point(
                f"Waist{prefix}{center}", back_waist_base, 90, "#BackRise")
        else:
            crotch_point = block.add_end_line_point(
                f"CrotchPoint{prefix}", frame.crotch, 0,
                "#FrontPanelWidthFront + #FrontCrotchHookWidth")
            waist_center = block.add_intersect_xy_point(
                f"Waist{prefix}{center}", hip_center, frame.waist_pt)
        waist_side = block.add_end_line_point(
            f"Waist{prefix}Side", frame.waist_pt, 180, waist_side_len)

        # dart (middle of the waist segment, V in the boundary) — the guide line
        # also creates the Line_* variable the dart-center formula references
        if back:
            block.add_line(waist_side, waist_center)
        else:
            block.add_line(waist_side, waist_center, line_type="dotLine", line_color="green")
        dart_center = block.add_along_line_point(
            f"DartCenter{prefix}", waist_side, waist_center,
            f"Line_Waist{prefix}Side_Waist{prefix}{center}/2")
        dart_l1 = block.add_along_line_point(
            f"Dart{prefix}L1", dart_center, waist_side, f"{dart_width}/2")
        dart_l2 = block.add_along_line_point(
            f"Dart{prefix}L2", dart_center, waist_center, f"{dart_width}/2")
        dart_tip = block.add_normal_point(
            f"DartTip{prefix}", dart_center, waist_center, dart_depth, angle=180)

        # crotch curve: center hip -> crotch point, controls formula-placed
        ctrl_c1 = block.add_end_line_point(
            f"Ctrl{prefix}Crotch1", hip_center, 270, "(#HipLineHeight - #CrotchHeight)/2")
        ctrl_c2 = block.add_end_line_point(
            f"Ctrl{prefix}Crotch2", crotch_point, 180,
            f"#FrontCrotchHookWidth/{crotch_ctrl_div}")
        crotch_curve = block.add_cubic_bezier(hip_center, ctrl_c1, ctrl_c2, crotch_point)

        # side curve: waist -> hip
        ctrl_s1 = block.add_end_line_point(
            f"Ctrl{prefix}Side1", waist_side, 270, "(#WaistHeight - #HipLineHeight)/2")
        ctrl_s2 = block.add_end_line_point(
            f"Ctrl{prefix}Side2", hip_side, 90, "(#WaistHeight - #HipLineHeight)/3")
        side_curve = block.add_cubic_bezier(waist_side, ctrl_s1, ctrl_s2, hip_side)

        # visible seam lines (straight parts) — also creates Line_* variables.
        # NOTE: the front inseam line creates Line_KneeFIn_CrotchPointF, which
        # the back crotch construction references by name — keep it.
        block.add_line(waist_center, hip_center)                   # CF / CB
        block.add_line(knee_in, crotch_point)                      # inseam
        block.add_line(hip_side, knee_out)
        block.add_line(knee_out, hem_out)
        block.add_line(hem_out, hem_in)
        block.add_line(hem_in, knee_in)

        # piece positions are auto-spread by the writer (details-mode safe)
        block.add_piece(
            f"Trousers{'Back' if back else 'Front'}",
            nodes=[
                waist_center,
                dart_l2, dart_tip, dart_l1,
                waist_side,
                side_curve,
                hip_side,
                knee_out, hem_out, hem_in, knee_in,
                crotch_point,
                PieceNode(crotch_curve, reverse=True),
                hip_center,
            ],
            label=PieceLabel((label_title, "cut 2"), letter=label_letter, quantity=2,
                             mx=-10, my=-70),
            grainline=Grainline(mx=-4, my=-75, rotation=90, length=30),
        )

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
        inc = doc.add_increment  # rounding policy lives in add_increment
        inc("#WaistCircumference", m["waist_circ"] + o["waist_ease"], "waist + ease")
        inc("#HipCircumference", m["hip_circ"] + o["hip_ease"], "hip + ease")
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
        inc("#AnkleCircumference", o["ankle_circ"], "hem circumference (style)")
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
        frame = _Frame(heel, waist_pt, crotch, hip_pt, knee)

        # ---- the two leg panels share one construction (front drawn first:
        # the back crotch references the front inseam's Line_* variable)
        self._leg_panel(
            block, frame, back=False,
            prefix="F", center="CF",
            hip_center_len="#FrontPanelWidthFront",
            hip_side_len="#FrontPanelWidth - #FrontPanelWidthFront",
            waist_side_len="#WaistCircumference/4 + #FrontDartWidth - #FrontPanelWidthFront",
            dart_width="#FrontDartWidth", dart_depth="#FrontDartDepth",
            crotch_ctrl_div="1.5",
            label_title="Trousers Front", label_letter="F",
        )
        self._leg_panel(
            block, frame, back=True,
            prefix="B", center="CB",
            hip_center_len="#BackPanelWidthBack",
            hip_side_len="#BackPanelWidth - #BackPanelWidthBack",
            waist_side_len="#WaistCircumference/4 + #BackDartWidth - #BackCenterShift",
            dart_width="#BackDartWidth", dart_depth="#BackDartDepth",
            crotch_ctrl_div="1.2",
            label_title="Trousers Back", label_letter="B",
        )

        # =================================================== WAISTBAND
        add_waistband_block(doc, "Waistband", "Waistband")

        return doc
