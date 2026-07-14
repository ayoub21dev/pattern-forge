"""Repro 2: the two trouser panels WITHOUT the dart V's — does the layout nest them?"""

from pathlib import Path

from pattern_forge.recipes import Trousers
from pattern_forge.sm2d import PieceNode
from pattern_forge.seamly_cli import ExportFormat, export_pattern, validate_pattern

OUT = Path(__file__).resolve().parents[1] / "out"

FATIMA = {
    "waist_circ": 72,
    "hip_circ": 98,
    "height_waist_side": 104,
    "leg_crotch_to_floor": 77,
    "height_knee": 47,
}


class NoDartTrousers(Trousers):
    """Same drafting, but the piece boundaries skip the dart V's."""

    def build(self, measurements, options):
        doc = super().build(measurements, options)
        block = doc._blocks[0]
        # rebuild both leg pieces without the dart nodes (indexes 1..3 are the V)
        for piece_el in list(block._pieces):
            name = piece_el.get("name")
            if name in ("TrousersFront", "TrousersBack"):
                nodes = piece_el.find("nodes")
                dart_nodes = list(nodes)[1:4]
                for n in dart_nodes:
                    nodes.remove(n)
        return doc


doc = NoDartTrousers().draft(FATIMA, {"knee_circ": 46, "ankle_circ": 38, "waist_ease": 1})
path = doc.save(OUT / "layout_repro2.sm2d")
print("validate:", validate_pattern(path).exit_code)
r = export_pattern(path, OUT, "layout_repro2", ExportFormat.PNG)
print("export:", r.exit_code, [f.name for f in r.produced])
