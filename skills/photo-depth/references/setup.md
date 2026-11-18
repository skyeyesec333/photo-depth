# Setup

## What `scripts/setup.sh` does

Creates `<folder>/.venv` with Python 3.11-3.13, installs PyTorch, torchvision, NumPy 2, OpenCV (headless), SciPy,
Pillow, trimesh, huggingface-hub, tqdm and click from PyPI, two small libraries MoGe needs from GitHub at pinned
commits (`utils3d-moge@62f09d5`, `pipeline@1c51139`), clones MoGe itself into `<folder>/moge-src` at a pinned commit and
installs it with `--no-deps` (MoGe's own requirements name a Linux-only GPU package that fails on a Mac). It refuses to
run without `--yes`: ask the user first, naming about 1 GB of packages.

Remove everything by deleting `<folder>` (and the weights from the Hugging Face cache, `~/.cache/huggingface/hub`,
if wanted).

## Weights

`depth.py` runs with Hugging Face in offline mode unless `--allow-download` is passed, so a missing model fails with a
message instead of a surprise download. The default, `Ruicheng/moge-2-vitl`, is about 1.3 GB. Smaller MoGe-2 variants
exist on the same account (`-vitb-normal`, `-vits-normal`): pass `--model`, and ask before downloading.

## Hardware

- **NVIDIA GPU (Linux/Windows):** fastest. Install the CUDA build of PyTorch (pytorch.org's selector) instead of the
  default wheel if the default comes without CUDA.
- **Apple Silicon:** uses Metal (MPS); the script sets `PYTORCH_ENABLE_MPS_FALLBACK=1` for the few ops MPS lacks.
  A 2K picture takes seconds.
- **CPU:** works, slowly (a minute or more at the finest level). `--level 5` is several times faster and coarser.
- A shared GPU box works well for batches: copy the picture over, run, copy the maps back.

## Other models, and their licences

Check the licence of both the code and the weights, and check again before you rely on this table: terms change.

| Model | Gives | Licence (as published when this was written) |
|---|---|---|
| MoGe-2 (Microsoft) | metric depth, camera intrinsics, mask | MIT, code and weights |
| Depth Anything V2 Small | relative depth | Apache-2.0 |
| Depth Anything V2 Base / Large | relative depth | CC BY-NC 4.0: non-commercial |
| Apple Depth Pro, Apple SHARP | metric depth / 3D | Apple's own terms; weights not for commercial use |
| LaMa (inpainting, for back layers) | fills painted-out areas | Apache-2.0 |

MoGe-2 is the default here because it is cleared for commercial use, gives the camera's field of view (needed to place
things), and handles paintings and AI pictures well.
