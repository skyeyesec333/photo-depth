---
name: photo-depth
description: Give a single photo, painting or AI-generated picture real depth on the web. Estimates a depth map with MoGe-2 (MIT licence), then either makes the picture behave like a window in a three.js scene (parallax that holds up as the camera moves, without tearing at edges) or finds where things are in it (fit a plane to a wall or sign to place a billboard, the ground under a character, the 3D point under a pixel). Use when the user wants a backdrop, portal, skybox picture or matte painting to stop looking like a flat print, mentions depth maps, parallax, 2.5D, MoGe, Depth Anything or monocular depth, or needs to place 3D objects into a picture.
---

# Photo depth: a picture that behaves like a place

```
0. setup     a Python env with MoGe-2 (once; asks before downloading)        scripts/setup.sh
1. depth     picture → nearness map (+ 16-bit distance, camera, raw npz)       scripts/depth.py
2a. window   the picture as a window in three.js                              examples/portal.js
2b. place    planes and points in the picture's own 3D                       scripts/fit_plane.py
3. check     look at it from the extreme views you will really use
```

`scripts/` and `examples/` mean the folders **in this skill's own directory** (`${CLAUDE_SKILL_DIR}`, for a plugin
or a copied skill alike), not the user's project. Set `S` to that `scripts/` folder and run
`"$S/depth.py"` and the others by full path.

## 0. Setup (once)

Check first: an existing env with `import moge` working can be reused (ask the user where they keep one). Otherwise
**ask the user before downloading**, naming what comes down: PyTorch and helpers from PyPI (about 1 GB installed),
MoGe's source and two small libraries from GitHub (pinned commits, a few MB), and later the model weights (about
1.3 GB, `Ruicheng/moge-2-vitl` on Hugging Face). Then:

```sh
"$S/setup.sh" <folder-for-the-env> --yes
```

Details, GPU notes and other models: [references/setup.md](references/setup.md).

## 1. Depth

```sh
<env>/.venv/bin/python "$S/depth.py" picture.jpg --out public/depth/ [--dist16] [--npz]
```

- Always writes `<stem>-near.webp`: nearness (disparity), 0 the sky, 1 the nearest thing, near edges grown 2 px so an
  object's edge moves with it. 10-25 KB for a 1-2K picture.
- `--dist16`: `<stem>-dist16.webp` (log distance in 16 bits, R high G low, lossless) and `<stem>-camera.json` (the
  estimated intrinsics). For rebuilding the picture as a surface.
- `--npz`: raw metric depth for `fit_plane.py`.
- It refuses to download weights unless `--allow-download` is passed: ask the user first.
- It prints the valid fraction, depth percentiles and the estimated field of view. Read them: "valid 20%" or a
  field of view of 150° means the model did not understand the picture.

Re-run it whenever the picture changes: a depth map from an older version of the picture misplaces every edge.

## 2a. The window

`examples/portal.js` is a self-contained three.js material (copy it into the project). The picture is the scene as
seen from a **rest point** (your default camera position). From anywhere else each pixel of the glass shows what lies
along the line of sight through it, found by walking the nearness map in 16 steps, so near things cover far things
and edges don't tear. Details, tuning and the failure modes: [references/portal.md](references/portal.md).

```js
import { makePortal } from "./portal.js";
const portal = makePortal({ map, near, width: 4, height: 2.5 });
scene.add(portal.mesh); portal.setRest(defaultCameraPosition);
// every frame: portal.update(camera);
```

`examples/portal.html` is a one-file demo: serve a folder with the picture, its nearness map, `portal.js` and the page,
open `portal.html?pic=<file>&near=<file>`, and move the pointer.

**Check it the way it will be seen:** hold the camera at the leftmost, rightmost, highest and lowest positions the
site really uses (for an automated check, the demo honours `window.__view = [x, y]`) and look at each:

- Can't see any depth? The first version of this effect on a real site was too weak to notice: lower `uQ.y` (0.6 → 0.4).
- Near things move most against the frame, or the sky swims? The depth is backwards (distance used as nearness).
- Smears or doubled objects at big moves: a single picture has nothing behind its near objects. Keep camera moves
  small, or ease them off (`uEase`), or paint a back layer (references/placing.md).

## 2b. Placing things in the picture

```sh
<env>/.venv/bin/python "$S/fit_plane.py" plane out/city-depth.npz --box 410,120,520,260
<env>/.venv/bin/python "$S/fit_plane.py" plane out/city-depth.npz --box 410,120,520,260 --corners 415,128 515,124 516,250 414,255
<env>/.venv/bin/python "$S/fit_plane.py" point out/city-depth.npz 640,700
```

Pixels are the picture's own (`--norm` for 0..1). Output is JSON in three.js camera space (camera at the origin
looking down -Z, metres). `flatness_rms_m` says how flat the region really is: a few centimetres on a wall 40 m away
is flat. Pick corners **inside** a panel's own edges (not a box round it) and the billboard follows the panel's real
shape instead of looking lopsided. Rebuilding the whole picture as a 3D surface, torn edges, back layers:
[references/placing.md](references/placing.md).

## Rules

- **Licences:** MoGe-2's code and weights are MIT. Several popular depth models are **not** cleared for commercial
  use (see references/setup.md): check before switching models for a client or a portfolio that sells work.
- **The picture's own licence** still applies to everything made from it.
- **Masks in alpha:** if a picture carries a mask in its alpha channel (water, sky), save the WebP losslessly with
  exact RGB (`cwebp -lossless -exact`, Pillow `exact=True`). Lossy alpha zeroes the colour under transparent pixels
  and smears it.
- **Ask before downloading anything** (packages, weights), naming what, from where and how big.
