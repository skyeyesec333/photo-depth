# photo-depth

Gives a single photo or painting real depth on a website, so it looks like a view through a window instead of a flat poster.

It came out of a 3D website where two painted city skylines sat in a portal and looked flat until they had depth.

## Good for

- Backdrops, portals and painted skies that should not look like flat prints when the camera moves
- Finding where things are in a picture, like a wall or sign, to place a 3D object or screen on it
- Getting depth from a picture with a model that is cleared for commercial use

## Install

In Claude Code, run:

```
/plugin marketplace add skyeyesec333/photo-depth
/plugin install photo-depth@photo-depth
```

Or copy the skill into your own skills folder:

```sh
git clone https://github.com/skyeyesec333/photo-depth
cp -r photo-depth/skills/photo-depth ~/.claude/skills/
```

You can also copy it into one project's `.claude/skills/` folder instead.

## Try asking Claude

- "Make the skyline picture in the portal feel like a real window"
- "Give this matte painting depth so the camera can drift a little"
- "Where in this picture is the big sign on the right tower? I want to put a screen on it"

## You'll need

- [Claude Code](https://claude.com/claude-code)
- Python 3.11-3.13 and git
- About 1 GB of disk for the environment and 1.3 GB for the model weights. Claude asks before anything is downloaded.
- An NVIDIA GPU or Apple Silicon is fast; a CPU works, slowly
- Optional: `cwebp` (sharper WebP than Pillow)
- For the window effect: three.js r155 or newer

## How it works

```
picture → MoGe-2 depth → a three.js "window" with real parallax  |  planes and points to place things in the picture
```

1. **Sets up MoGe-2** (Microsoft's depth model, MIT licence for code and weights) in a folder you choose, after asking. It pins exact commits of MoGe and its helpers (`scripts/setup.sh`).
2. **Estimates depth** (`scripts/depth.py`). It writes a small nearness map for the web (10-25 KB). It can also write a 16-bit distance map with the camera's field of view, and raw depth for measuring. It never downloads weights unless told to.
3. **Makes the picture a window** (`examples/portal.js`, three.js). The far skyline holds its direction while the frame slides over it. Near things cover far things, and edges don't tear. A one-file demo page is included.
4. **Places things in the picture** (`scripts/fit_plane.py`). It fits a flat plane to a wall, sign or the ground, and gives its corners in three.js coordinates. It can also give the 3D point under any pixel.
5. **Knows the failure modes**: an effect too weak to see, depth backwards, smears when the camera moves far, and model licences that forbid commercial use.

By hand, where `S` is the skill's `scripts/` folder and `~/depth-env` the environment from `setup.sh`:

```sh
"$S/setup.sh" ~/depth-env --yes                                           # once; downloads ~1 GB of packages
~/depth-env/.venv/bin/python "$S/depth.py" city.jpg --out public/depth --allow-download   # first run fetches ~1.3 GB of weights
~/depth-env/.venv/bin/python "$S/depth.py" city.jpg --out depth-work --npz                 # raw depth stays out of public/
~/depth-env/.venv/bin/python "$S/fit_plane.py" plane depth-work/city-depth.npz --box 410,120,520,260
```

## Licence

MIT. See [LICENSE](LICENSE). MoGe-2 is MIT. Other depth models have their own terms, and some forbid commercial use: see `references/setup.md`.
