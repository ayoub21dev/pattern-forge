# A-line skirt — drafting blueprint

Classic straight-skirt-to-A-line method. Front and back share one construction;
only the dart differs.

## Measurements & key options (cm)

| input | default | role |
|---|---|---|
| `waist_circ` (measured) | — | waist |
| `hip_circ` (measured) | — | hip |
| `skirt_length` | 60 | waist → hem |
| `hip_height` | 20 | waist → hip line |
| `flare` | 6 | extra hem width per half-panel |
| `front_dart_width` / depth | 2 / 9 | front dart |
| `back_dart_width` / depth | 3.5 / 13 | back dart (bodies curve more in back) |

## Construction (per panel, CF/CB on the fold)

```
WaistCF ──────── WaistSide          waist = waist/4 + dart, dart V mid-waist
   |                \
HipCF ─────────── HipSide           hip line at #HipHeight, width = hip/4
   |                 \              side seam: curve waist→hip, straight below
HemCF ──────────── HemSide          hem width = hip/4 + #Flare
```

- Side seam: cubicBezier waist→hip (formula-placed controls), straight hip→hem.
- Dart: V in the piece boundary (leg → tip → leg), tip perpendicular to waist.
- Waistband: rectangle, `waist + 4` × `2 × band width`, cut on fold.

## Guards (checked before drawing)

- `skirt_length > hip_height`
- `waist/4 + dart ≤ hip/4 + 1` (side seam must not lean outward above hip)

## v1 simplifications (for the Phase-3 review)

1. Straight hem (no hem sweep curve).
2. No zipper / vent.
3. Side seams front/back equal within small tolerance (not by construction).
