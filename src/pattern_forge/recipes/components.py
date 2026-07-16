"""Shared garment components used by multiple recipes.

A component draws a complete draft block into a Document using the increments
the calling recipe has already declared — one implementation, so garments can
never drift apart on a shared piece.
"""

from __future__ import annotations

from ..sm2d import Document, Grainline, PieceLabel


def add_waistband_block(doc: Document, block_name: str, piece_name: str) -> None:
    """Rectangular waistband, cut 1 on fold.

    Requires increments: #WaistCircumference (+ 4 cm button-stand overlap) and
    #WaistBandWidth (doubled — the band folds over).
    """
    wb = doc.add_draft_block(block_name)
    wb_a = wb.add_base_point("WbA", x=0, y=0)
    wb_b = wb.add_end_line_point("WbB", wb_a, 0, "#WaistCircumference + 4",
                                 line_type="solidLine")
    wb_c = wb.add_end_line_point("WbC", wb_b, 270, "#WaistBandWidth*2",
                                 line_type="solidLine")
    wb_d = wb.add_end_line_point("WbD", wb_a, 270, "#WaistBandWidth*2",
                                 line_type="solidLine")
    wb.add_line(wb_c, wb_d)
    wb.add_piece(
        piece_name,
        nodes=[wb_a, wb_b, wb_c, wb_d],
        label=PieceLabel(("Waistband", "cut 1 on fold"), letter="W",
                         on_fold=True, mx=20, my=1.5, height=4),
        grainline=Grainline(mx=5, my=6, rotation=0, length=20),
    )
