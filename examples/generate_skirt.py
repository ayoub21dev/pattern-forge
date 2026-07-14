"""Generate the demo A-line skirt and validate it with the real Seamly2D binary.

Run:  uv run python examples/generate_skirt.py
"""

from pathlib import Path

from pattern_forge.recipes import AlineSkirt
from pattern_forge.seamly_cli import SeamlyNotFoundError, validate_pattern
from pattern_forge.validators import validate_pattern_xml

OUT = Path(__file__).resolve().parents[1] / "out"


def main() -> None:
    # 1. draft the pattern from measurements + options
    recipe = AlineSkirt()
    doc = recipe.draft({"waist_circ": 90}, {"skirt_length": 60, "flare": 8})
    path = doc.save(OUT / "demo_skirt.sm2d")
    print(f"[1/3] generated {path}")

    # 2. offline XSD validation
    errors = validate_pattern_xml(path)
    print(f"[2/3] XSD validation: {'OK' if not errors else errors}")

    # 3. authoritative check: real Seamly2D recalculates the pattern
    try:
        result = validate_pattern(path)
        print(f"[3/3] seamly2d --test: {result.meaning} (exit {result.exit_code})")
    except SeamlyNotFoundError as exc:
        print(f"[3/3] skipped: {exc}")

    print(f"\nOpen it in Seamly2D: {path}")


if __name__ == "__main__":
    main()
