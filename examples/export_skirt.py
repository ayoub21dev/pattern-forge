"""Generate the skirt WITH a piece and export it to SVG + PNG (Phase 1 piece test)."""

from pathlib import Path

from pattern_forge.recipes import AlineSkirt
from pattern_forge.seamly_cli import ExportFormat, export_pattern, validate_pattern

OUT = Path(__file__).resolve().parents[1] / "out"


def main() -> None:
    doc = AlineSkirt().draft({"waist_circ": 90})
    path = doc.save(OUT / "skirt_piece.sm2d")
    r = validate_pattern(path)
    print("validate:", r.exit_code, r.meaning)
    for fmt in (ExportFormat.SVG, ExportFormat.PNG):
        e = export_pattern(path, OUT, "skirt_preview", fmt)
        print(f"export {fmt.name}:", e.exit_code, e.meaning, [f.name for f in e.produced])


if __name__ == "__main__":
    main()
