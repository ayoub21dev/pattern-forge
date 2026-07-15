# Roadmap

## Done

| phase | delivered |
|---|---|
| 0 — Foundation | XML writers, CLI wrapper, XSD validators, demo recipe |
| 1 — Trousers | classic block (front/back/waistband), 8-body validation matrix |
| 2 — MCP server | 11 tools, GUI auto-open/refresh, friendly error hints |
| — Review | 8-angle code review, 10 findings fixed |
| — Upgrades | piece labels + grainlines, full skirt recipe, client profiles, validation pack |

## Next

| step | what | owner |
|---|---|---|
| **3 — Human validation** | post `out/validation_pack/` on [forum.seamly.io](https://forum.seamly.io), collect pattern-maker feedback, fix findings, sew a muslin | **Ayoub** (post) + engine fixes |
| 4a — More recipes | bodice, sleeve, shirt (~2 weeks each with the established method) | engine |
| 4b — Style modules | pockets, pleats, cuffs, fly — composable on top of blocks | engine |
| 4c — Factory tier | multi-size `.smms`, batch grading (`--gsize/--gheight`), DXF bundles | engine |
| 4d — Web SaaS | chat UI + preview + download, accounts, billing | product |

## Watch items

- **Seamly2D upstream** (commit `678d3deacc`): next release gates seam allowance
  in exports behind the GUI setting `showSeamAllowances` (default ON). When the
  `vendor/` binary is updated: re-run the visual export check and consider
  forcing that setting before exports.
