"""Generate the classic trouser block for an average man and export a preview."""

from pathlib import Path

from pattern_forge.recipes import Trousers
from pattern_forge.seamly_cli import ExportFormat, export_pattern, validate_pattern

OUT = Path(__file__).resolve().parents[1] / "out"


def main() -> None:
    doc = Trousers().draft(
        {
            "waist_circ": 84,
            "hip_circ": 100,
            "height_waist_side": 107,
            "leg_crotch_to_floor": 83,
            "height_knee": 50,
        }
    )
    path = doc.save(OUT / "trousers_block.sm2d")
    r = validate_pattern(path)
    print("validate:", r.exit_code, r.meaning)
    for fmt in (ExportFormat.SVG, ExportFormat.PNG, ExportFormat.PDF):
        e = export_pattern(path, OUT, "trousers_preview", fmt)
        print(f"export {fmt.name}:", e.exit_code, e.meaning, [f.name for f in e.produced])
    print(f"\nOpen it in Seamly2D: {path}")


if __name__ == "__main__":
    main()
