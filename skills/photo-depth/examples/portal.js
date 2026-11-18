/* A picture that behaves like a window (three.js).

   The picture is the scene as seen from a resting viewpoint in front of the glass. From anywhere else each pixel of the
   glass shows what lies along the line of sight from the camera through that point: the far skyline keeps its direction
   while the frame slides over it, and near things move less. The nearness map (depth.py's <stem>-near.webp: 0 = sky,
   1 = nearest) says how far behind the glass each pixel is; the shader walks that line of sight from near to far in
   STEPS steps and takes the first surface it meets, so a near object covers what is behind it and edges do not tear.

   Use:
     const portal = makePortal({ map, near, width: 4, height: 2.5 });  // textures from TextureLoader
     scene.add(portal.mesh);
     portal.setRest(new THREE.Vector3(0, 1.6, 4));   // world point the picture was "taken" from (your default camera)
     // each frame: portal.update(camera);

   Tuning (portal.uniforms):
     uQ    x: how far behind the glass the sky sits (0 = infinitely far), y: the nearest thing (1 = on the glass).
           Too weak to notice? lower y (0.6 → 0.4). Things swimming? raise y. Depth backwards (near things move most
           against the frame)? your map is distance, not nearness: invert it.
     uEase past this fraction of the window, the shift grows ever more slowly (camera far from the rest point).
     uZoom how much of the picture fills the glass (below 1 leaves margin for the shift).
*/
import * as THREE from "three";

const STEPS = 16;

const vertexShader = /* glsl */ `
varying vec2 vUv;
void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;

const fragmentShader = /* glsl */ `
uniform sampler2D uMap, uNear;
uniform vec3 uCamL, uRestL;   /* camera and rest point in the glass's frame: x, y as fractions of the window from its
                                 centre, z the distance in front of the glass (any unit, the same for both) */
uniform vec2 uQ;
uniform float uEase, uZoom;
varying vec2 vUv;
vec2 frame(vec2 s) { s = (s - 0.5) * uZoom + 0.5; return 1.0 - abs(1.0 - mod(s, 2.0)); }  /* past the edge: mirror */
void main() {
  vec2 cam = uCamL.xy + 0.5, ref = uRestL.xy + 0.5;
  float cn = max(uCamL.z, 0.05), rn = max(uRestL.z, 0.05);
  /* where this line of sight meets the sky in the picture: the rest view's point with the same direction */
  vec2 sky = ref + rn * (vUv - cam) / cn;
  vec2 dv = sky - vUv; dv = dv / sqrt(1.0 + dv * dv / (uEase * uEase)); sky = vUv + dv;
  float prevL = 1.0, prevD = -1.0, hitL = 0.0, found = 0.0;
  for (int i = 0; i <= ${STEPS}; i++) {
    float l = 1.0 - float(i) / ${STEPS}.0, q = mix(uQ.x, uQ.y, l);
    float n = texture2D(uNear, frame(mix(sky, vUv, q))).r;
    float d = n - l;
    if (found < 0.5 && d >= 0.0) { hitL = i == 0 ? 1.0 : mix(prevL, l, prevD / (prevD - d)); found = 1.0; }
    prevL = l; prevD = d;
  }
  gl_FragColor = vec4(texture2D(uMap, frame(mix(sky, vUv, mix(uQ.x, uQ.y, hitL)))).rgb, 1.0);
  #include <colorspace_fragment>
}`;

export function makePortal({ map, near, width = 4, height = 2.5 }) {
  map.colorSpace = THREE.SRGBColorSpace;
  near.colorSpace = THREE.NoColorSpace;
  near.generateMipmaps = false; near.minFilter = near.magFilter = THREE.LinearFilter;
  const uniforms = {
    uMap: { value: map }, uNear: { value: near },
    uCamL: { value: new THREE.Vector3(0, 0, 1) }, uRestL: { value: new THREE.Vector3(0, 0, 1) },
    uQ: { value: new THREE.Vector2(0.0, 0.6) }, uEase: { value: 0.2 }, uZoom: { value: 0.86 },
  };
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(width, height), new THREE.ShaderMaterial({ uniforms, vertexShader, fragmentShader }));
  const tmp = new THREE.Vector3();
  const local = (world, out) => {
    mesh.updateWorldMatrix(true, false);
    mesh.worldToLocal(tmp.copy(world));
    return out.set(tmp.x / width, tmp.y / height, tmp.z / width);
  };
  const rest = new THREE.Vector3(0, 0, width);
  return {
    mesh, uniforms,
    setRest(worldPoint) { rest.copy(worldPoint); },
    update(camera) { local(rest, uniforms.uRestL.value); local(camera.getWorldPosition(new THREE.Vector3()), uniforms.uCamL.value); },
  };
}
