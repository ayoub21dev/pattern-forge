# Architecture

## How it works

```
measurements (client / factory)      recipe (trousers, skirt, ...)
              \                       /
               pattern_forge engine
                     |
        .sm2d pattern file  +  .smis measurements file
                     |
        seamly2d.exe --test          → validation (exit 0 = pattern computes)
        seamly2d.exe -b ... -f N     → PNG / PDF / SVG / DXF-AAMA export
```

The AI never draws. It fills **recipes** (parametric templates encoding
professional drafting methods) with client data. The real Seamly2D binary is
the authoritative validator behind every result.

## Code layout

| path | responsibility |
|---|---|
| `src/pattern_forge/sm2d/` | `.sm2d` XML writer: points, curves, pieces, labels, grainlines |
| `src/pattern_forge/smis/` | `.smis` measurements writer + reader |
| `src/pattern_forge/recipes/` | the patternmaking knowledge (one module per garment) |
| `src/pattern_forge/seamly_cli.py` | headless wrapper around `seamly2d.exe` |
| `src/pattern_forge/validators/` | offline XSD validation (cached schemas) |
| `src/pattern_forge/mcp_server.py` | MCP server: the AI-facing tools |
| `src/pattern_forge/schemas/` | XSDs from Seamly2D (GPLv3, unmodified, shipped in the package) |
| `tests/` | 65 tests incl. end-to-end gates against the real binary |
| `examples/` | runnable demos + the validation-pack generator |
| `vendor/` | (gitignored) the Seamly2D binaries |

## Binary lookup order

1. `PATTERN_FORGE_SEAMLY2D` env var (error if set but wrong)
2. `vendor/**/seamly2d.exe`
3. `C:\Program Files\Seamly2D\`
4. `PATH`

Result is cached per process.

## Design decisions (and why)

| decision | why |
|---|---|
| Pattern format **v0.6.8** | same as Seamly2D's shipped samples; the app auto-converts on open |
| **Numeric increments** (not measurement-name formulas) | self-contained files; regeneration happens in Python anyway |
| Exports use **`--exportOnlyDetails`** + auto-spread piece positions | Seamly2D's auto-nesting overlaps large concave pieces; factory marker software re-nests DXF anyway |
| Every CLI path is **absolute** (`seamly_cli._abs`) | seamly2d.exe changes its own cwd and remembers given paths |
| Output files matched by **exact naming contract** (`_layout_NN` / `_pieces`) | a loose prefix glob deleted/claimed other patterns' files |
| Back crotch point placed at **front-inseam length** | inseams match by construction, not by luck (the pro sample's trick) |
| Recipes **reject implausible inputs before drawing** | clear errors instead of broken geometry |

## Exit codes (seamly2d)

| code | meaning |
|---|---|
| 0 | ok |
| 64 | bad command line |
| 65 | pattern data / formula error |
| 66 | input file missing or unreadable |
| -1 | (ours) process killed on timeout |
