# pattern-forge

AI-driven garment patterns on top of [Seamly2D](https://seamly.io).
**AI configures validated drafting recipes — it never invents geometry freehand.**

## Quick start

```bash
uv sync                                      # install (Python managed by uv)
uv run pytest                                # verify: all green
uv run python examples/export_trousers.py    # generate your first pattern
```

Open this folder in Claude Code → enable the `pattern-forge` MCP server → say:

> *"Client: waist 84, hips 100, waist-to-floor 107, crotch 83, knee 50 — make classic trousers and show me."*

## MCP tools

| tool | what it does |
|---|---|
| `draft_and_show` | **one-shot**: draft + validate + preview + open in Seamly2D |
| `list_recipes` / `describe_recipe` | discover recipes, measurements + options |
| `draft_pattern` | measurements (cm) → validated `.sm2d` |
| `save_client` / `get_client` / `list_clients` | reusable client profiles |
| `create_measurements_file` | client data → `.smis` |
| `render_preview` | pattern → PNG pages |
| `export_pattern_file` | pattern → PDF / SVG / **DXF-AAMA** |
| `open_in_seamly2d` | open or refresh the pattern in the real app |

Outputs (patterns, exports, client profiles) go to `~/.pattern-forge/out` by
default; set `PATTERN_FORGE_WORKSPACE` to choose another folder.

## Recipes

| recipe | pieces | status |
|---|---|---|
| `trousers` | front + back + waistband, darts, matched inseams | ✅ validated on 8 body types |
| `skirt` | A-line front + back + waistband, darts, on fold | ✅ validated |
| `aline_skirt` | single-piece demo | ✅ (Phase-0 demo) |

All pieces print with **labels, cutting instructions, and grainlines**.

## Documentation

| doc | content |
|---|---|
| [docs/architecture.md](docs/architecture.md) | how the engine works, design decisions, layout |
| [docs/trousers-blueprint.md](docs/trousers-blueprint.md) | the trouser drafting method, decoded |
| [docs/skirt-blueprint.md](docs/skirt-blueprint.md) | the A-line skirt drafting method |
| [docs/roadmap.md](docs/roadmap.md) | phases: done / next |

## License

Engine code: proprietary. `src/pattern_forge/schemas/` contains unmodified XSD
files from the Seamly2D project (GPLv3). The Seamly2D application is used as an
external binary, unmodified.
