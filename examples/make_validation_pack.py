"""Build the Phase-3 validation pack: patterns across sizes + PDFs + questionnaire.

Output: out/validation_pack/ — ready to zip and post on forum.seamly.io for
professional pattern makers to review.

Run:  uv run python examples/make_validation_pack.py
"""

from pathlib import Path

from _bodies import AVG_MAN

from pattern_forge.recipes import Skirt, Trousers
from pattern_forge.seamly_cli import ExportFormat, export_pattern, validate_pattern

PACK = Path(__file__).resolve().parents[1] / "out" / "validation_pack"

TROUSER_BODIES = [
    ("woman_S", {"waist_circ": 66, "hip_circ": 92, "height_waist_side": 102,
                 "leg_crotch_to_floor": 76, "height_knee": 46}),
    ("woman_L", {"waist_circ": 84, "hip_circ": 108, "height_waist_side": 105,
                 "leg_crotch_to_floor": 77, "height_knee": 47}),
    ("man_M", AVG_MAN),
    ("man_XL", {"waist_circ": 104, "hip_circ": 114, "height_waist_side": 109,
                "leg_crotch_to_floor": 82, "height_knee": 50}),
]

SKIRT_BODIES = [
    ("woman_S", {"waist_circ": 66, "hip_circ": 92}),
    ("woman_L", {"waist_circ": 84, "hip_circ": 108}),
]

QUESTIONNAIRE = """\
# pattern-forge — validation pack for pattern makers

These patterns were generated automatically (parametric recipes on top of the
Seamly2D format) from the body measurements listed in each folder name.
The trousers follow the classic trouser-block construction (documented in
docs/trousers-blueprint.md of the project); the skirt is a classic A-line block.

We would be grateful for your professional judgment:

1. **Proportions** — do the panels look correctly proportioned for the stated
   measurements (crotch depth, hip placement, knee/hem widths)?
2. **Crotch curves** — front and back: acceptable shape? Where would you adjust?
3. **Darts** — placement, intake, and length: what would you change?
4. **Balance** — is the back/front relationship (rise, widths) sound?
5. **Sewability** — inseams and side seams are matched by construction; do you
   see anything that would fight the sewist?
6. **Known v1 simplifications** (told upfront): straight hems, fixed 2/2 cm back
   rise slant, no pockets/pleats/fly. Beyond these — what is missing for you to
   call the block professional?
7. Would you drape/sew a muslin from these as-is? If not, what must change first?

Each folder contains: the .sm2d (editable in Seamly2D), a PDF, and a PNG preview.
Thank you! Feedback goes to the pattern-forge project.
"""


def build(recipe, label: str, bodies) -> list[str]:
    lines = []
    for body_label, measurements in bodies:
        folder = PACK / f"{label}_{body_label}"
        doc = recipe.draft(measurements)
        pattern = doc.save(folder / f"{label}_{body_label}.sm2d")
        check = validate_pattern(pattern)
        pdf = export_pattern(pattern, folder, f"{label}_{body_label}", ExportFormat.PDF)
        png = export_pattern(pattern, folder, f"{label}_{body_label}", ExportFormat.PNG)
        status = "OK" if (check.ok and pdf.ok and png.ok) else "FAILED"
        sizes = ", ".join(f"{k}={v:g}" for k, v in measurements.items())
        lines.append(f"{label}_{body_label}: {status}  ({sizes})")
        print(lines[-1])
    return lines


def main() -> None:
    PACK.mkdir(parents=True, exist_ok=True)
    results = build(Trousers(), "trousers", TROUSER_BODIES)
    results += build(Skirt(), "skirt", SKIRT_BODIES)
    (PACK / "README.md").write_text(
        QUESTIONNAIRE + "\n## Generated sets\n\n" + "\n".join(f"- {r}" for r in results) + "\n",
        encoding="utf-8",
    )
    failed = [r for r in results if "FAILED" in r]
    print(f"\nPack ready: {PACK}")
    print(f"{len(results) - len(failed)}/{len(results)} sets OK" + (f" — FAILURES: {failed}" if failed else ""))


if __name__ == "__main__":
    main()
