# Placing things in a picture, and rebuilding it as a surface

## The picture's own 3D

`depth.py --npz` keeps MoGe's metric depth (metres, up to the model's scale error), the valid-pixel mask, and the
camera intrinsics normalised to the image (`fx` in image widths, `fy` in heights, `cx, cy` the centre). A pixel
`(x, y)` of a `w × h` picture lies along the ray

```
dir = ((x + 0.5) / w - cx) / fx,  ((y + 0.5) / h - cy) / fy,  1      (OpenCV: x right, y down, z forward)
point = dir * depth[y, x]
```

`fit_plane.py` prints everything in three.js camera space instead: `(x, -y, -z)`, camera at the origin looking down -Z.
Put a three.js camera at the origin with the picture's field of view (`2 * atan(0.5 / fy)` vertically, in degrees for
`PerspectiveCamera`) and anything placed at those coordinates lines up with the picture.

## Planes: billboards, walls, the ground

`fit_plane.py plane <npz> --box X0,Y0,X1,Y1` fits a plane to the pixels in the box (least squares, then twice more on
the 80% nearest the plane, which drops edges and strays) and reports its centre, normal (facing the camera), distance
and flatness (RMS, metres). Then it carries the box's corners onto the plane, or the four `--corners` you give.

- **Pick the corners inside the panel's own edges** (top left, top right, bottom right, bottom left, as the panel is
  drawn), not a screen-aligned box round it. A real sign is seldom square to the picture; a rectangle laid
  "world-horizontal" on it looked lopsided to the person who asked for it.
- **Ground:** a box on open floor or road gives the plane a character stands on; its normal is the picture's "up",
  which is how much the picture is tilted (a picture taken looking down might be tilted 20°). Rotate the whole scene by
  that to level it.
- `flatness_rms_m` of a few centimetres on a wall tens of metres away is flat. Large values: the box straddles two
  surfaces; make it smaller.

## Rebuilding the whole picture as a surface

With `--dist16`, the picture can be rebuilt as a mesh: a fine grid (e.g. 768 × 384) whose vertices are pushed out along
their pixels' rays to the decoded distance, in the vertex shader:

```glsl
uniform sampler2D uDist;                 /* <stem>-dist16.webp, NoColorSpace, nearest filtering, no mipmaps */
uniform float uNearM, uFarM;             /* from <stem>-camera.json */
float dist(vec2 uv) {
  vec4 t = texture(uDist, uv);
  float q = (t.r * 255.0 * 256.0 + t.g * 255.0) / 65535.0;
  return exp(mix(log(uNearM), log(uFarM), q));
}
```

Then `p = vec3((uv.x - cx) / fx, (uv.y - cy) / fy, -1.0) * dist(uv)` (with `uv.y` counting up, flip `cy` accordingly).

What happens next decides whether it looks good:

- **From the picture's own eye it is perfect** (it is the picture). Turning and zooming the camera from that point
  stays perfect.
- **Moving the camera reveals what the picture never saw.** Where depth jumps (a near tower against the river far
  below) the sheet stretches into a smear. Find those triangles from the neighbours' depth ratio (over ~1.3×) and
  discard them, then show a **back layer** behind: the same picture with the near objects painted out (LaMa
  inpainting, Apache-2.0, or a frame of a camera-move video of the same scene if one exists), with its own depth.
- On a real project, viewers still saw smudges and doubled objects (a bridge's cables, a tower) once the camera moved
  more than a little, and the final scene kept the camera at the picture's eye: it turns and zooms between framings,
  and the depth is used only to place things (a billboard on a building, a character on a roof). **Plan for that**;
  promise parallax only for small moves.
- Depth of field over such a scene can ghost thin structures (cables became a second bridge). Leave it off, or
  test it on the thinnest things in the picture.

## Upscaling

A picture shown large benefits from a 2× upscale (Real-ESRGAN, BSD-3) for wide screens, with the original size for
phones. Upscale the picture only: compute depth on the original (the model does not need the extra pixels).
