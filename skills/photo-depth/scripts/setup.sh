#!/usr/bin/env bash
# setup.sh: make a Python environment for depth.py (MoGe-2 and its dependencies) in a folder of your choice.
#
#   setup.sh <folder> --yes
#
# DOWNLOADS (ask the user before running): PyTorch and friends from PyPI (about 1 GB installed on macOS, more with
# CUDA on Linux), two small helper libraries and MoGe's source from GitHub (a few MB, pinned commits). The model
# weights (about 1.3 GB, Hugging Face) are fetched later, by `depth.py --allow-download`, only when asked.
# Nothing is installed system-wide; delete <folder> to remove it all.
set -euo pipefail

die() { echo "setup.sh: $*" >&2; exit 2; }
[ $# -ge 1 ] || die "usage: setup.sh <folder> --yes"
DEST=$1; shift
YES=0; for a in "$@"; do case $a in --yes) YES=1;; *) die "unknown option $a";; esac; done
[ "$YES" = 1 ] || die "this downloads about 1 GB of packages. Ask the user, then re-run with --yes."
case $DEST in -*) die "folder may not start with -";; esac

PY=""
for c in python3.12 python3.13 python3.11 python3; do
  if command -v "$c" >/dev/null && "$c" -c 'import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,14) else 1)' 2>/dev/null; then PY=$c; break; fi
done
[ -n "$PY" ] || die "needs Python 3.11-3.13 (PyTorch wheels lag new Pythons)"
command -v git >/dev/null || die "needs git"

# Pinned: MoGe's own installer asks for a Linux-only GPU package, so its dependencies are installed by hand.
MOGE_REPO=https://github.com/microsoft/MoGe.git
MOGE_COMMIT=74fbce054ebed49800de42d0ad0e83495065719a
UTILS3D="git+https://github.com/EasternJournalist/utils3d-moge.git@62f09d5"
PIPELINE="git+https://github.com/EasternJournalist/pipeline.git@1c51139"

mkdir -p -- "$DEST"
DEST=$(cd -- "$DEST" && pwd)
echo "== environment in $DEST (using $($PY --version))"
[ -x "$DEST/.venv/bin/python" ] || "$PY" -m venv "$DEST/.venv"
PIP=("$DEST/.venv/bin/python" -m pip --disable-pip-version-check)
"${PIP[@]}" install --upgrade pip
"${PIP[@]}" install torch torchvision "numpy>=2" opencv-python-headless scipy pillow trimesh huggingface-hub tqdm click \
  "$UTILS3D" "$PIPELINE"
if [ ! -d "$DEST/moge-src/.git" ]; then git clone --quiet -- "$MOGE_REPO" "$DEST/moge-src"; fi
git -C "$DEST/moge-src" fetch --quiet origin "$MOGE_COMMIT" 2>/dev/null || true
git -C "$DEST/moge-src" -c advice.detachedHead=false checkout --quiet "$MOGE_COMMIT"
"${PIP[@]}" install --no-deps -e "$DEST/moge-src"
"$DEST/.venv/bin/python" -c 'import moge, torch; print("ok  moge + torch", torch.__version__, "| GPU:", "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "none (CPU)")'
echo "== done. Run depth.py with $DEST/.venv/bin/python"
