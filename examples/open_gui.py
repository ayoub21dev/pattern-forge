"""Open the generated trousers block in the Seamly2D GUI (auto-open demo)."""

from pathlib import Path

from pattern_forge.mcp_server import open_in_seamly2d

PATTERN = Path(__file__).resolve().parents[1] / "out" / "trousers_block.sm2d"

result = open_in_seamly2d(str(PATTERN))
print(result)
