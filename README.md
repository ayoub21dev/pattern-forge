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

- `src/pattern_forge/sm2d/` — writer for Seamly2D pattern XML (`.sm2d`, format v0.6.8)
- `src/pattern_forge/smis/` — writer for individual measurement files (`.smis`)
- `src/pattern_forge/recipes/` — parametric garment recipes (the actual patternmaking knowledge)
- `src/pattern_forge/seamly_cli.py` — wrapper around the Seamly2D binary (validate / export)
- `src/pattern_forge/validators/` — XSD validation of generated files
- `schemas/` — XSD schemas copied from the Seamly2D project (GPLv3, unmodified)
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

## Example

```bash
uv run python examples/generate_skirt.py
```

Generates `out/demo_skirt.sm2d`, validates it with the real Seamly2D binary, and (if pieces are
defined) exports a preview.
