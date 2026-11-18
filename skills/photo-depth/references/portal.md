# The window effect, in detail

## The idea

A flat picture on a plane reads as a print: move the camera and the whole picture slides with the frame. A real window
does something else: the far skyline keeps its direction (it stays put in the world while the frame slides over it),
near things shift with the frame more, and near things hide what is behind them.

`examples/portal.js` does that with one picture and its nearness map:

1. **The rest point.** The picture is the scene as seen from one point in front of the glass: usually the camera's
   default position. `portal.setRest(point)`. If the site has several camera presets, set the rest point to the
   current preset's resting position (without mouse drift), and move it when the preset changes.
2. **Where the sky is.** For a pixel of the glass, the line of sight from the camera through it meets "infinity" at the
   same direction the rest view would see: `sky = ref + rn * (uv - cam) / cn` in window units.
3. **The walk.** Between the glass (q = 1) and the sky (q = 0) the line of sight passes through every depth. The shader
   samples the nearness map at 16 points along it, from near to far, and takes the first point where the map says
   "there is something at least this near here". It then interpolates between the two samples around that crossing,
   so steps don't show as bands.
4. **Easing.** Far from the rest point the shift would run off the picture. `uEase` (0.2: a fifth of the window) makes
   the shift grow ever more slowly beyond that.
5. **Past the edge** the picture is mirrored, so a big shift shows plausible scenery instead of a smear or a hard edge.
   `uZoom` < 1 (0.86 default) keeps a margin so the mirror is rarely seen.

## Tuning

| Uniform | Default | Meaning |
|---|---|---|
| `uQ.x` | 0.0 | where the farthest thing (sky) sits: 0 = infinitely far |
| `uQ.y` | 0.6 | where the nearest thing sits: 1 = on the glass, 0.6 = 40% of the way to infinity |
| `uEase` | 0.2 | fraction of the window after which the shift is eased off |
| `uZoom` | 0.86 | how much of the picture fills the glass |

A first attempt on a real site set the effect so gently that the owner's screenshot "still read as a print". Judge it
from the views the site really uses, not from the front.

## Failure modes

- **Depth backwards:** near things move most against the frame while the sky slides with it. The map is distance, not
  nearness. `depth.py`'s `-near.webp` is already nearness; a map from another tool may need `1 - value`.
- **Edges tear** (a near tower stretches into the sky behind it): the nearness map's edges sit inside the object.
  `depth.py --grow 2` (the default) moves them out by 2 px; try 3-4 for soft or noisy pictures.
- **Smears and doubled objects** when the camera moves far: there is nothing in a single picture behind a near
  object. Keep moves small, ease them off, or paint a back layer (placing.md).
- **Banding:** fewer than ~12 steps shows as stepped edges on slopes. 16 is cheap: it ran within noise of the flat
  version on a real site's frame time.

## Cost

Seventeen texture reads per pixel of the window, one extra 8-bit texture (10-25 KB). Measured on a real site, the
frame time was within noise of a plain textured plane.

## Extras that worked

- Masks in the picture's alpha (e.g. water) to animate only that part (waver, glints): read them at the shifted `uv`,
  and save the picture losslessly with exact RGB (see SKILL.md's rules).
- Two pictures cross-faded (day/night, two cities): blend both the colours and the nearness maps with the same factor.
