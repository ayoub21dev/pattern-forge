"""Simulate the EXACT tool-call sequence an AI assistant makes over MCP.

Scenario: client asks for a t-shirt (not available -> honest refusal path),
then slim trousers for real measurements, then an edit ("relax the ankle")
with the live GUI refresh. Every step prints the tool result.
"""

import time

from pattern_forge.mcp_server import (
    create_measurements_file,
    describe_recipe,
    draft_pattern,
    export_pattern_file,
    list_recipes,
    open_in_seamly2d,
    render_preview,
)

FATIMA = {
    "waist_circ": 72,
    "hip_circ": 98,
    "height_waist_side": 104,
    "leg_crotch_to_floor": 77,
    "height_knee": 47,
}


def step(n: int, label: str, result) -> None:
    print(f"\n[{n}] {label}")
    print(f"    -> {result}")


def main() -> None:
    # user: "make me a t-shirt"
    recipes = list_recipes()
    step(1, "list_recipes (user asked for a t-shirt)", recipes)
    names = [r["name"] for r in recipes]
    assert "tshirt" not in names, "no t-shirt recipe should exist yet"
    print("    AI would answer: 'No t-shirt recipe yet — I can draft: " + ", ".join(names) + "'")

    # user: "ok, the trousers then — slim"
    info = describe_recipe("trousers")
    step(2, "describe_recipe('trousers')", {k: len(v) if isinstance(v, list) else v
                                            for k, v in info.items() if k != "description"})

    saved = create_measurements_file(FATIMA, name="fatima")
    step(3, "create_measurements_file (client record)", saved)
    assert saved["ok"]

    drafted = draft_pattern(
        "trousers", FATIMA,
        options={"knee_circ": 44, "ankle_circ": 34, "waist_ease": 1},
        name="fatima_slim_trousers",
    )
    step(4, "draft_pattern (slim: knee 44, ankle 34, ease 1)", drafted)
    assert drafted["ok"], "draft must pass both validations"

    preview = render_preview(drafted["pattern_path"])
    step(5, "render_preview (AI would now LOOK at these PNGs)", preview)
    assert preview["ok"] and preview["preview_files"]

    opened = open_in_seamly2d(drafted["pattern_path"])
    step(6, "open_in_seamly2d (user sees it live)", opened)
    assert opened["ok"]

    # user: "relax the ankle a bit"
    time.sleep(3)  # user looks at the window for a moment
    redrafted = draft_pattern(
        "trousers", FATIMA,
        options={"knee_circ": 46, "ankle_circ": 38, "waist_ease": 1},
        name="fatima_slim_trousers",  # same file -> true edit
    )
    step(7, "draft_pattern EDIT (ankle 34 -> 38)", redrafted)
    assert redrafted["ok"]

    refreshed = open_in_seamly2d(redrafted["pattern_path"])
    step(8, "open_in_seamly2d again (must REFRESH the window)", refreshed)
    assert refreshed["ok"] and refreshed["refreshed"], "second open must refresh"

    pdf = export_pattern_file(redrafted["pattern_path"], "pdf")
    step(9, "export_pattern_file pdf (for the client)", pdf)
    assert pdf["ok"] and pdf["files"]

    dxf = export_pattern_file(redrafted["pattern_path"], "dxf")
    step(10, "export_pattern_file dxf (DXF-AAMA, for a factory)", dxf)
    assert dxf["ok"] and dxf["files"]

    # bonus: the guardrail path — impossible measurements must NOT produce a file
    bad = draft_pattern("trousers", FATIMA | {"waist_circ": 300})
    step(11, "draft_pattern with waist=300 (guardrail check)", bad)
    assert not bad["ok"] and bad["errors"]

    print("\nALL 11 WORKFLOW STEPS PASSED")


if __name__ == "__main__":
    main()
