# pattern-forge

AI-driven parametric garment pattern generation on top of [Seamly2D](https://seamly.io).

The core idea: **AI configures validated drafting recipes — it never invents geometry freehand.**
Recipes encode professional patternmaking methods as parametric templates. This engine turns
(measurements + options) into valid Seamly2D files, then uses the real Seamly2D binary headlessly
to validate and export them.

## What it does

```
measurements (client / factory)         recipe (e.g. trousers)
              \                          /
               pattern_forge engine
                     |
        .sm2d pattern file  +  .smis measurements file
                     |
        seamly2d.exe --test        → validation (exit code 0 = pattern computes)
        seamly2d.exe -b … -f 3     → PNG / PDF / SVG / DXF-AAMA export
```

## Layout

- `src/pattern_forge/sm2d/` — writer for Seamly2D pattern XML (`.sm2d`, format v0.6.8),
  including full **pieces/modeling** support (what makes patterns exportable)
- `src/pattern_forge/smis/` — writer for individual measurement files (`.smis`)
- `src/pattern_forge/recipes/` — parametric garment recipes (the actual patternmaking knowledge)
  - `aline_skirt` — demo recipe (Phase 0)
  - `skirt` — full A-line skirt: front + back blocks with waist darts, waistband,
    piece labels + grainlines, CF/CB on fold
  - `trousers` — classic trouser block: front + back + waistband, darts, matched
    inseams, labeled pieces (Phase 1; see `docs/trousers-blueprint.md`)
- `src/pattern_forge/seamly_cli.py` — wrapper around the Seamly2D binary (validate / export)
- `src/pattern_forge/validators/` — XSD validation of generated files
- `docs/` — drafting blueprints (the decoded patternmaking methods)
- `src/pattern_forge/schemas/` — XSD schemas copied from the Seamly2D project
  (GPLv3, unmodified; shipped inside the package so installs stay self-contained)
- `vendor/` — (gitignored) the Seamly2D application binaries

## Setup

```bash
uv sync
uv run pytest
```

The Seamly2D binary is looked up in this order:
1. `PATTERN_FORGE_SEAMLY2D` environment variable (full path to `seamly2d.exe`)
2. `vendor/**/seamly2d.exe`
3. `C:\Program Files\Seamly2D\seamly2d.exe`
4. `PATH`

## MCP server (talk to it from Claude)

The engine is exposed as an MCP server (`.mcp.json` is included — Claude Code will offer to
enable it when you open this folder). Tools:

| tool | what it does |
|---|---|
| `draft_and_show` | **one-shot**: draft + validate + preview + open in Seamly2D |
| `list_recipes` / `describe_recipe` | discover recipes, their measurements + options |
| `draft_pattern` | measurements (cm) → validated `.sm2d` pattern |
| `save_client` / `get_client` / `list_clients` | reusable client measurement profiles |
| `create_measurements_file` | client data → `.smis` file |
| `render_preview` | pattern → PNG pages (viewable in the conversation) |
| `export_pattern_file` | pattern → PDF / SVG / **DXF-AAMA** (factory cutters) |
| `open_in_seamly2d` | open (or refresh) the pattern in the real app |

Failed tools return a plain-language `hint` translating Seamly2D's raw errors.

Note on exports: pieces are exported at their (auto-spread) detail positions
(`--exportOnlyDetails`) rather than Seamly2D's auto-nesting, which was observed
to overlap large concave pieces. Factory marker software re-nests DXF pieces anyway.

Example conversation: *"Client: waist 84, hips 100, waist-to-floor 107, crotch 83, knee 50.
Make him classic trousers, slightly relaxed."* → Claude calls `draft_pattern`, shows you the
preview, exports the PDF.

Run it manually: `uv run pattern-forge-mcp` (stdio).

## Example scripts

```bash
uv run python examples/generate_skirt.py    # draft + validate the demo skirt
uv run python examples/export_skirt.py      # ...and export SVG/PNG
uv run python examples/export_trousers.py   # full trouser block -> SVG/PNG/PDF
```
