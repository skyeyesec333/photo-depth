#!/usr/bin/env python3
"""fit_plane.py: find where things are in a picture, from the depth depth.py --npz wrote.

  fit_plane.py plane <depth.npz> --box X0,Y0,X1,Y1 [--corners X,Y X,Y X,Y X,Y]
      Fits a plane to the pixels in the box (a wall, a billboard panel, the ground) and prints its centre, normal and
      flatness, and the box's corners (or the given corners, e.g. picked inside a panel's own edges) carried onto it.
  fit_plane.py point <depth.npz> X,Y [X,Y ...]
      The 3D point under each pixel.

Pixels are in the picture's own pixel grid (0,0 top left); add --norm to give them as 0..1 fractions instead.
Coordinates are printed for three.js: camera at the origin looking down -Z, +Y up, metres (MoGe's scale).
Output is JSON on stdout.
"""
import argparse, json, re, sys

import numpy as np


def die(msg, code=2):
    print(f"fit_plane.py: {msg}", file=sys.stderr)
    sys.exit(code)


NUM = r"-?\d+(?:\.\d+)?"


def pair(s):
    if not re.fullmatch(fr"{NUM},{NUM}", s): die(f"expected X,Y numbers, got {s!r}")
    return tuple(float(v) for v in s.split(","))


def load(path):
    try:
        z = np.load(path, allow_pickle=False)  # never unpickle: an npz from elsewhere must not run code
        d, m, K = z["depth"], z["mask"].astype(bool), z["K"]
    except Exception as e:
        die(f"could not read {path} as depth.py's npz ({type(e).__name__})")
    if d.ndim != 2 or d.shape != m.shape or K.shape != (3, 3): die("unexpected array shapes in the npz")
    return d, m, K


def rays(K, h, w, xs, ys):
    """Pixel centres to camera-space directions (OpenCV: x right, y down, z forward), K normalised to the image."""
    u, v = (xs + 0.5) / w, (ys + 0.5) / h
    return np.stack([(u - K[0, 2]) / K[0, 0], (v - K[1, 2]) / K[1, 1], np.ones_like(u)], -1)


def to_three(p):
    p = np.asarray(p, float)
    return [round(float(p[..., 0]), 4), round(float(-p[..., 1]), 4), round(float(-p[..., 2]), 4)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("plane"); pp.add_argument("npz"); pp.add_argument("--box", required=True)
    pp.add_argument("--corners", nargs=4, metavar="X,Y"); pp.add_argument("--norm", action="store_true")
    pt = sub.add_parser("point"); pt.add_argument("npz"); pt.add_argument("xy", nargs="+"); pt.add_argument("--norm", action="store_true")
    a = ap.parse_args()

    d, m, K = load(a.npz)
    h, w = d.shape
    scale = (w, h) if a.norm else (1, 1)
    px = lambda q: (q[0] * scale[0], q[1] * scale[1])

    def inside(x, y):
        if not (0 <= x < w and 0 <= y < h): die(f"pixel {x:.1f},{y:.1f} is outside the {w}x{h} picture")

    if a.cmd == "point":
        out = []
        for s in a.xy:
            x, y = px(pair(s)); inside(x, y)
            xi, yi = int(x), int(y)
            if not m[yi, xi]: out.append({"pixel": [x, y], "point": None, "note": "no depth here (sky or invalid)"}); continue
            p = rays(K, h, w, np.array(x), np.array(y)) * d[yi, xi]
            out.append({"pixel": [x, y], "distance_m": round(float(d[yi, xi]), 3), "point": to_three(p)})
        print(json.dumps(out, indent=2)); return

    b = [float(v) for v in a.box.split(",")] if re.fullmatch(fr"{NUM}(,{NUM}){{3}}", a.box) else die("--box must be X0,Y0,X1,Y1")
    (x0, y0), (x1, y1) = px((b[0], b[1])), px((b[2], b[3]))
    x0, x1, y0, y1 = sorted((x0, x1)) + sorted((y0, y1))
    inside(x0, y0); inside(x1 - 1e-6, y1 - 1e-6)
    ys, xs = np.mgrid[int(y0):int(np.ceil(y1)), int(x0):int(np.ceil(x1))]
    ys, xs = ys.ravel(), xs.ravel()
    ok = m[ys, xs]
    if ok.sum() < 30: die("fewer than 30 pixels with depth in that box: pick a region with surface in it", 1)
    ys, xs = ys[ok], xs[ok]
    P = rays(K, h, w, xs.astype(float), ys.astype(float)) * d[ys, xs][:, None]

    # robust fit: least squares, then refit on the inner 80% by distance to the plane (drops edges and stray pixels)
    keep = np.ones(len(P), bool)
    for _ in range(3):
        c = P[keep].mean(0); _, s, vt = np.linalg.svd(P[keep] - c, full_matrices=False); nrm = vt[2]
        r = np.abs((P - c) @ nrm); keep = r <= np.percentile(r, 80)
    if nrm @ c > 0: nrm = -nrm  # face the camera
    rms = float(np.sqrt(np.mean(((P[keep] - c) @ nrm) ** 2)))

    corners = [px(pair(s)) for s in a.corners] if a.corners else [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    cs = []
    for (x, y) in corners:
        inside(x, y)
        r = rays(K, h, w, np.array(x), np.array(y))
        den = r @ nrm
        if abs(den) < 1e-6: die("a corner's line of sight runs along the plane; pick another corner", 1)
        cs.append(to_three(r * ((c @ nrm) / den)))
    print(json.dumps({
        "pixels_used": int(keep.sum()), "centre": to_three(c), "normal": to_three(nrm),
        "distance_m": round(float(np.linalg.norm(c)), 3), "flatness_rms_m": round(rms, 4),
        "corners": cs, "frame": "three.js camera space: camera at origin, -Z forward, +Y up, metres",
    }, indent=2))


if __name__ == "__main__":
    main()
