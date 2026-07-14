# Trousers recipe — drafting blueprint (Phase 1)

Source of knowledge: the professional trousers draft shipped with Seamly2D
(`tests/data/trousers.sm2d`, by Timo Virtaneva, GPL) — decoded point by point —
cross-read with the classic trouser-block construction found in published
drafting systems (Aldrich, Müller & Sohn style). This document is the blueprint
the `TrousersRecipe` code implements.

## Scope of v1 (deliberate)

**IN:** the classic trouser *block* — front panel, back panel, waistband; one
front dart, one back dart; matched inseams; correct crotch curves; full
parametrization by measurements.

**OUT (Phase 4 style modules):** pockets, pleats, zipper panel, cuffs, stripe
shift. The sample implements these with rotation operations and cut-spline
points; they layer on top of the block later.

## Required measurements (cm)

| name | meaning | plausible range |
|---|---|---|
| `waist_circ` | waist circumference | 50–150 |
| `hip_circ` | hip circumference | 60–170 |
| `height_waist_side` | waist to floor (side) | 80–130 |
| `leg_crotch_to_floor` | crotch to floor | 55–100 |
| `height_knee` | knee to floor | 35–65 |

Optional-with-defaults: `leg_ankle_circ` (hem width driver).

## Derived variables (increments) — from the sample's logic

| increment | formula | role |
|---|---|---|
| `#WaistCircumference` | `waist_circ + waist_ease` | fitted waist |
| `#HipCircumference` | `hip_circ + hip_ease` | fitted hip |
| `#WaistHeight` | `height_waist_side` | vertical frame |
| `#CrotchHeight` | `leg_crotch_to_floor` | vertical frame |
| `#KneeHeight` | `height_knee` | vertical frame |
| `#HipLineHeight` | `hip_circ/20 + 3 + leg_crotch_to_floor` | hip line above crotch (sample's rule) |
| `#FrontPanelWidth` | `#HipCircumference/4` | front hip width |
| `#FrontPanelWidthFront` | `waist_circ/10 + 1.5` | crease→CF at hip (sample's rule) |
| `#FrontCrotchHookWidth` | `hip_circ/20 + 1` | front crotch extension (sample's rule) |
| `#BackPanelWidth` | `#HipCircumference/4 + 2` | back hip width |
| `#BackPanelWidthBack` | `#BackPanelWidth/4` | crease→CB at hip (sample's rule) |
| `#KneeCircumference` | option (default 52) | knee width driver |
| `#AnkleCircumfence` | option (default 42) | hem width driver |
| `#FrontDartDepth` / `#BackDartDepth` | 6 / 11 | dart lengths (sample defaults) |
| `#FrontDartWidth` / `#BackDartWidth` | options (2 / 3) | dart intake |
| `#WaistBandWidth` | option (default 4) | waistband |

## Construction — vertical frame (both panels)

All on the **crease line** (vertical axis), exactly like the sample:

```
Waist ── height #WaistHeight above Heel
Hip   ── #HipLineHeight above Heel
Crotch── #CrotchHeight above Heel
Knee  ── #KneeHeight above Heel
Heel  ── base point (hem sits here in v1; hem shortening is an option later)
```

Direction convention (sample's): **+x (angle 0) = toward center front/back,
−x (angle 180) = toward side seam**, crease vertical.

## Front panel

- Hem half-widths around crease: `(#AnkleCircumfence/2 − 1)/2` each side
  (the −1 is the front/back difference from the sample, `#HemLineFrontBackDiffrence`).
- Knee half-widths: `(#KneeCircumference/2 − 1)/2` each side.
- Hip line: `HipF_CF` at `#FrontPanelWidthFront` toward CF;
  `HipF_Side` at `#FrontPanelWidth − #FrontPanelWidthFront` toward side.
- Crotch corner `CrotchF_CF`: same x as `HipF_CF`, at crotch height (intersectXY).
- **Crotch point** `CrotchPointF`: `#FrontCrotchHookWidth` beyond the corner,
  on the crotch line.
- Waist: CF sits above `HipF_CF`; side point gives front waist =
  `#WaistCircumference/4 + #FrontDartWidth` measured CF→side.
- **Front dart** at the middle of the waist segment: width `#FrontDartWidth`,
  length `#FrontDartDepth`, drawn as a V in the piece boundary
  (same technique as the sample's `Front` pieces).
- Curves (all cubicBezier with formula-placed control points → fully parametric):
  - crotch curve: `HipF_CF → CrotchPointF`, control at the crotch corner
    (this is the sample's exact topology, its `spline 43`)
  - side seam waist→hip gentle curve; hip→knee→hem straight in v1
  - inseam: `CrotchPointF → KneeF` slight curve, knee→hem straight

## Back panel

- Same frame; hem/knee half-widths use `+1` (the back is wider by the
  front/back difference).
- Hip line: `HipB_CB` at `#BackPanelWidthBack` toward CB;
  `HipB_Side` at `#BackPanelWidth − #BackPanelWidthBack` toward side.
- **Back rise**: CB tilts outward — waist CB point is shifted and raised
  (sample uses shoulder/intersect constructions; v1 uses a simple slant:
  2 cm shift, 2 cm rise, then `#BackDartWidth` intake in the dart).
- **Crotch point back — the seam-matching trick from the sample**: the back
  crotch point is placed along the knee→hip-inner direction at length
  `Line_KneeF_In_CrotchPointF` (the *front* inseam crotch→knee length).
  → back inseam = front inseam **by construction**, not by luck.
  (Sample: `CrotchPointBack length="Line_A7_CrotchPointFront"`.)
- Back dart: middle of back waist, width `#BackDartWidth`, length `#BackDartDepth`,
  V in the boundary.
- Crotch curve: `HipB_CB → CrotchPointB` control at back crotch corner.

## Waistband (separate draft block, like the sample)

Rectangle: length `#WaistCircumference + overlap (4)`, height `2 × #WaistBandWidth`
(cut on fold). Four corners, one piece.

## Pieces (what makes export possible)

Each panel = one `piece` whose boundary is an ordered node list
(points and curves), each node referencing a *modeling proxy* of a drawing
object — the writer creates the proxies automatically. `seamAllowance=1`,
width 1 cm (sample's defaults).

## Known v1 limitations (honest list — for the Phase 3 patternmaker review)

1. Side seams front/back are equal only within a small tolerance (straight
   segments match exactly; the waist→hip curves differ slightly). Books ease
   this in sewing; a future refinement can equalize by construction.
2. Back rise slant is simplified (fixed 2/2 cm instead of angle-from-shape).
3. No hem shortening/cuff logic yet (`#HemlineHeight/#HemlineAddition` in the
   sample) — hem sits at heel height.
4. Knee/ankle circumferences are style options, not body measurements
   (the sample does the same — `*** CHECK ***` values).
