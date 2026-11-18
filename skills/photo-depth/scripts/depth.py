#!/usr/bin/env python3
"""depth.py: one picture in, its depth out, ready for the web.

MoGe-2 (Microsoft, MIT licence for code and weights) estimates, from a single photo or painting, the distance to every
pixel and the camera's field of view. This script turns that into the files a web scene reads:

  <stem>-near.webp    nearness, 8-bit: 0 = sky / farthest, 1 = nearest thing. What parallax follows (it is disparity,
                      1/distance, normalised). Grown by a few pixels so a near object's own edge moves with it. For the
                      "window" portal shader (references/portal.md).
  <stem>-dist16.webp  (--dist16) distance on a log scale, 16 bits split R high / G low, lossless. For rebuilding the
                      picture as a surface or placing things in it (references/placing.md).
  <stem>-camera.json  (--dist16) the camera's normalised intrinsics (fx, fy, cx, cy) and the near/far of the log scale.
  <stem>-depth.npz    (--npz) raw metric depth, mask and intrinsics, for fit_plane.py.

Usage:
  depth.py <picture> --out <folder> [--dist16] [--npz] [--grow PX] [--quality Q] [--level L]
           [--near-m M] [--far-m M] [--model ID] [--allow-download]

Weights are NOT downloaded unless --allow-download is given (about 1.3 GB for the default model, from Hugging Face):
the agent asks the user first. Setup: references/setup.md.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile


def die(msg, code=2):
    print(f"depth.py: {msg}", file=sys.stderr)
    sys.exit(code)


def args():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("picture")
    p.add_argument("--out", required=True, help="folder to write into (created if missing)")
    p.add_argument("--dist16", action="store_true", help="also write 16-bit log distance + camera.json")
    p.add_argument("--npz", action="store_true", help="also write raw depth/mask/intrinsics (for fit_plane.py)")
    p.add_argument("--grow", type=int, default=2, help="grow near edges by this many pixels (0-8, default 2)")
    p.add_argument("--quality", type=int, default=95, help="WebP quality for the nearness map (50-100, default 95)")
    p.add_argument("--level", type=int, default=9, help="MoGe resolution level (0-9, default 9: finest)")
    p.add_argument("--near-m", type=float, default=3.0, help="nearest distance on the 16-bit scale, metres (default 3)")
    p.add_argument("--far-m", type=float, default=4000.0, help="farthest distance on the 16-bit scale (default 4000)")
    p.add_argument("--model", default="Ruicheng/moge-2-vitl", help="Hugging Face model id (default Ruicheng/moge-2-vitl)")
    p.add_argument("--allow-download", action="store_true", help="let Hugging Face download the weights if not cached")
    a = p.parse_args()
    if not os.path.isfile(a.picture):
        die(f"no such picture: {a.picture}")
    if not 0 <= a.grow <= 8: die("--grow must be 0-8")
    if not 50 <= a.quality <= 100: die("--quality must be 50-100")
    if not 0 <= a.level <= 9: die("--level must be 0-9")
    if not (0 < a.near_m < a.far_m): die("--near-m must be > 0 and below --far-m")
    if not re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", a.model): die("--model must look like owner/name")
    return a


def stem_of(path):
    s = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.splitext(os.path.basename(path))[0]).strip("._") or "picture"
    return s[:80]


def save_webp(png_path, out_path, lossless, quality):
    """cwebp if present (sharper), else Pillow. Lossless saves keep exact RGB under transparent pixels."""
    if shutil.which("cwebp"):
        cmd = ["cwebp", "-quiet"] + (["-lossless", "-exact"] if lossless else ["-q", str(quality), "-sharp_yuv"]) + [png_path, "-o", out_path]
        subprocess.run(cmd, check=True, timeout=300)
    else:
        from PIL import Image
        im = Image.open(png_path)
        if lossless: im.save(out_path, "WEBP", lossless=True, exact=True, quality=100)
        else: im.save(out_path, "WEBP", quality=quality)


def main():
    a = args()
    if not a.allow_download:
        os.environ["HF_HUB_OFFLINE"] = "1"  # fail closed: never fetch weights unless asked
    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    try:
        import numpy as np, cv2, torch
        from moge.model.v2 import MoGeModel
    except ImportError as e:
        die(f"missing package ({e.name}): set up the environment first (references/setup.md)")

    os.makedirs(a.out, exist_ok=True)
    out_dir = os.path.realpath(a.out)
    stem = stem_of(a.picture)

    img = cv2.imread(a.picture, cv2.IMREAD_UNCHANGED)
    if img is None: die(f"could not read {a.picture} as an image")
    if img.ndim == 2: img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    img = cv2.cvtColor(img[..., :3], cv2.COLOR_BGR2RGB)
    h, w = img.shape[:2]
    if w * h > 40_000_000: die(f"picture is {w}x{h}: resize it below 40 megapixels first")

    dev = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    try:
        model = MoGeModel.from_pretrained(a.model).to(dev).eval()
    except Exception as e:  # offline and not cached, or a bad id
        die(f"could not load {a.model} ({type(e).__name__}). If the weights are not downloaded yet, ask the user, then "
            f"re-run with --allow-download (about 1.3 GB from huggingface.co for the default model).")
    with torch.no_grad():
        o = model.infer(torch.tensor(img / 255, dtype=torch.float32, device=dev).permute(2, 0, 1),
                        resolution_level=a.level, use_fp16=False)
    d = o["depth"].float().cpu().numpy()
    m = o["mask"].cpu().numpy().astype(bool) & np.isfinite(d) & (d > 0)
    K = o["intrinsics"].float().cpu().numpy()
    if m.mean() < 0.02: die("the model found almost no valid depth in this picture", 1)

    written = []
    with tempfile.TemporaryDirectory() as tmp:
        # nearness: disparity, robustly normalised, near edges grown so they move as one with their object
        disp = np.where(m, 1.0 / np.maximum(d, 1e-3), 0.0)
        lo, hi = np.percentile(disp[m], 2), np.percentile(disp[m], 99.7)
        n = np.clip((disp - lo) / max(hi - lo, 1e-9), 0, 1)
        if a.grow: n = cv2.dilate(n, np.ones((2 * a.grow + 1, 2 * a.grow + 1), np.uint8))
        png = os.path.join(tmp, "near.png")
        cv2.imwrite(png, (n * 255 + 0.5).astype(np.uint8))
        dst = os.path.join(out_dir, f"{stem}-near.webp"); save_webp(png, dst, False, a.quality); written.append(dst)

        if a.dist16:
            dd = np.where(m, d, a.far_m).astype(np.float32)
            lo, hi = np.log(a.near_m), np.log(a.far_m)
            v = np.round(np.clip((np.log(np.maximum(dd, a.near_m)) - lo) / (hi - lo), 0, 1) * 65535).astype(np.uint16)
            rgb = np.zeros((h, w, 3), np.uint8)
            rgb[..., 2] = (v >> 8).astype(np.uint8)    # R (OpenCV is BGR): high byte
            rgb[..., 1] = (v & 255).astype(np.uint8)   # G: low byte
            png = os.path.join(tmp, "dist16.png"); cv2.imwrite(png, rgb)
            dst = os.path.join(out_dir, f"{stem}-dist16.webp"); save_webp(png, dst, True, 100); written.append(dst)
            cam = {"fx": float(K[0, 0]), "fy": float(K[1, 1]), "cx": float(K[0, 2]), "cy": float(K[1, 2]),
                   "near_m": a.near_m, "far_m": a.far_m, "width": w, "height": h,
                   "note": "intrinsics normalised to the image (fx in widths, fy in heights); distance = exp(mix(log(near), log(far), (R*256+G)/65535))"}
            dst = os.path.join(out_dir, f"{stem}-camera.json")
            with open(dst, "w") as f: json.dump(cam, f, indent=2)
            written.append(dst)

        if a.npz:
            dst = os.path.join(out_dir, f"{stem}-depth.npz")
            np.savez_compressed(dst, depth=np.where(m, d, 0).astype(np.float32), mask=m, K=K)
            written.append(dst)

    pct = np.percentile(d[m], [1, 50, 99])
    print(f"{w}x{h}  valid {m.mean():.0%}  depth m (1/50/99%): {pct[0]:.1f} / {pct[1]:.1f} / {pct[2]:.1f}  "
          f"view {2 * np.degrees(np.arctan(0.5 / K[0, 0])):.0f} deg across")
    for f in written: print(f"wrote {f}  ({os.path.getsize(f) // 1024} KB)")


if __name__ == "__main__":
    main()
