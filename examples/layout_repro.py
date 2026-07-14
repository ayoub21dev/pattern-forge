"""Minimal repro: do TWO simple rectangle pieces from our writer nest correctly?"""

from pathlib import Path

from pattern_forge.sm2d import Document
from pattern_forge.seamly_cli import ExportFormat, export_pattern, validate_pattern

OUT = Path(__file__).resolve().parents[1] / "out"


def rect_block(doc, name, w, h):
    b = doc.add_draft_block(name)
    a = b.add_base_point(f"{name}A", x=0, y=0)
    p2 = b.add_end_line_point(f"{name}B", a, 0, w, line_type="solidLine")
    p3 = b.add_end_line_point(f"{name}C", p2, 270, h, line_type="solidLine")
    p4 = b.add_end_line_point(f"{name}D", a, 270, h, line_type="solidLine")
    b.add_line(p3, p4)
    b.add_piece(f"{name}Piece", nodes=[a, p2, p3, p4])
    return b


doc = Document(unit="cm", description="layout repro: two rectangles")
rect_block(doc, "R1", 30, 20)
rect_block(doc, "R2", 25, 15)
path = doc.save(OUT / "layout_repro.sm2d")
print("validate:", validate_pattern(path).exit_code)
r = export_pattern(path, OUT, "layout_repro", ExportFormat.PNG)
print("export:", r.exit_code, [f.name for f in r.produced])
