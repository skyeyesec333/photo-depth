# photo-depth

A Claude Code skill that gives a single photo, painting or AI-generated picture real depth on the web:

```
picture → MoGe-2 depth → a three.js "window" with real parallax  |  planes and points to place things in the picture
```

It came out of a production three.js site where two painted city skylines sat in a portal: as flat prints they slid with
the frame like posters; with depth they behave like a view through glass.

## What the skill does

1. **Sets up MoGe-2** (Microsoft, MIT licence for code and weights) in a folder of your choice, after asking, with
   pinned commits of MoGe and its helpers (`scripts/setup.sh`).
2. **Estimates depth** (`scripts/depth.py`): a small nearness map for the web (10-25 KB), optionally a 16-bit
   distance map with the camera's field of view, and raw depth for measuring. It never downloads weights unless told to.
3. **Makes the picture a window** (`examples/portal.js`, three.js): the far skyline holds its direction while the frame
   slides over it, near things cover far things, and edges don't tear. A one-file demo page is included.
4. **Places things in the picture** (`scripts/fit_plane.py`): fits a plane to a wall, sign or the ground and gives its
   corners in three.js coordinates, or the 3D point under any pixel.
5. **Knows the failure modes:** an effect too weak to see, depth backwards, smears when the camera moves far, model
   licences that forbid commercial use.

## Install

**As a Claude Code plugin** (from inside Claude Code):

```
/plugin marketplace add skyeyesec333/photo-depth
/plugin install photo-depth@photo-depth
```

**Or as a plain skill:**

```sh
git clone https://github.com/skyeyesec333/photo-depth
cp -r photo-depth/skills/photo-depth ~/.claude/skills/
```

## Use

Just ask:

- "Make the skyline picture in the portal feel like a real window"
- "Give this matte painting depth so the camera can drift a little"
- "Where in this picture is the big sign on the right tower? I want to put a screen on it"

By hand (`S` is the skill's `scripts/` folder, `ENV` the environment from `setup.sh`):

```sh
"$S/setup.sh" ~/depth-env --yes                                           # once; downloads ~1 GB of packages
~/depth-env/.venv/bin/python "$S/depth.py" city.jpg --out public/depth --allow-download   # first run fetches ~1.3 GB of weights
~/depth-env/.venv/bin/python "$S/depth.py" city.jpg --out depth-work --npz                 # raw depth stays out of public/
~/depth-env/.venv/bin/python "$S/fit_plane.py" plane depth-work/city-depth.npz --box 410,120,520,260
```

## Requirements

- [Claude Code](https://claude.com/claude-code)
- Python 3.11-3.13, git; about 1 GB for the environment and 1.3 GB for the model weights
- An NVIDIA GPU or Apple Silicon is fast; a CPU works, slowly
- Optional: `cwebp` (sharper WebP than Pillow)
- For the window effect: three.js r155 or newer

## Licence

MIT. See [LICENSE](LICENSE). MoGe-2 is MIT; other depth models have their own terms (see `references/setup.md`).
