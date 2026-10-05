// The opening stage: the locked Slice lockup as a real exploded assembly
// (spec §5). Loaded only by dynamic import, only when head.js said yes.
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { buildShapeSpecs, interiorPoints, toStage } from './lib/paths.js';
import { pieceOffsets, stateAt } from './lib/timeline.js';

const DEPTH = 0.04, BEVEL_T = 0.006, BEVEL_S = 0.004;
const FOV = 30;
const KERF_A = toStage([579.5, 45.9]);
const KERF_B = toStage([1513, -608]);
const FRONT = 0.03 + DEPTH + 0.002;
const DEG = Math.PI / 180;

function limewash(size, seed) {
  let s = seed;
  const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  const grid = n => Array.from({ length: (n + 1) * (n + 1) }, rnd);
  const g1 = grid(24), g2 = grid(96);
  const sample = (g, n, u, v) => {
    const x = u * n, y = v * n, i = Math.floor(x), j = Math.floor(y), fx = x - i, fy = y - j;
    const at = (a, b) => g[Math.min(b, n) * (n + 1) + Math.min(a, n)];
    const sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
    return (at(i, j) * (1 - sx) + at(i + 1, j) * sx) * (1 - sy) + (at(i, j + 1) * (1 - sx) + at(i + 1, j + 1) * sx) * sy;
  };
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext('2d');
  const img = ctx.createImageData(size, size);
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const n = 0.65 * sample(g1, 24, x / size, y / size) + 0.35 * sample(g2, 96, x / size, y / size);
    const v = Math.round(255 * (0.96 + 0.08 * n) / 1.04);
    const k = (y * size + x) * 4;
    img.data[k] = img.data[k + 1] = img.data[k + 2] = v;
    img.data[k + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

export async function start({ host, still, rtl, getState, onReady, onFail }) {
  const res = await fetch(new URL('../data/slice.json', import.meta.url));
  if (!res.ok) throw new Error(`slice.json ${res.status}`);
  const specs = buildShapeSpecs(await res.json());

  const narrow = () => host.clientWidth < 768;
  const coarse = window.matchMedia('(pointer: coarse)').matches;

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.setClearColor(0x0f2427, 1);
  const canvas = renderer.domElement;
  canvas.style.opacity = '0';
  canvas.style.transition = 'opacity .9s cubic-bezier(.2,.7,.1,1)';
  host.appendChild(canvas);
  const lost = e => { e.preventDefault(); onFail('context'); };
  canvas.addEventListener('webglcontextlost', lost, false);

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envRT = pmrem.fromScene(new RoomEnvironment(), 0.04);

  // Wall: night petrol limewash.
  const wallTex = limewash(1024, 20261005);
  const wallMat = new THREE.MeshStandardMaterial({ color: 0x2f646a, map: wallTex, roughness: 0.92, metalness: 0 });
  const wall = new THREE.Mesh(new THREE.PlaneGeometry(8, 5), wallMat);
  wall.receiveShadow = true;
  scene.add(wall);

  // Satin champagne-toned metal.
  const metal = new THREE.MeshStandardMaterial({
    color: 0xc2a670, metalness: 1, roughness: 0.4, envMap: envRT.texture, envMapIntensity: 0.32,
  });
  const stud = new THREE.MeshStandardMaterial({
    color: 0x9aa0a4, metalness: 1, roughness: 0.32, envMap: envRT.texture, envMapIntensity: 0.5, transparent: true, opacity: 0,
  });
  const holeMat = new THREE.MeshBasicMaterial({ color: 0x050c0d, transparent: true, opacity: 0 });

  const studGeo = new THREE.CylinderGeometry(0.006, 0.006, 1, 18);
  studGeo.rotateX(Math.PI / 2);
  studGeo.translate(0, 0, 0.5);
  const holeGeo = new THREE.CircleGeometry(0.008, 20);

  const pieces = specs.map(spec => {
    const shape = new THREE.Shape(spec.outer.map(([x, y]) => new THREE.Vector2(x, y)));
    for (const h of spec.holes) shape.holes.push(new THREE.Path(h.map(([x, y]) => new THREE.Vector2(x, y))));
    const geo = new THREE.ExtrudeGeometry(shape, {
      depth: DEPTH - 2 * BEVEL_T, curveSegments: 1,
      bevelEnabled: true, bevelThickness: BEVEL_T, bevelSize: BEVEL_S, bevelOffset: -BEVEL_S, bevelSegments: 3,
    });
    geo.translate(0, 0, BEVEL_T); // back face at z = 0
    const mesh = new THREE.Mesh(geo, metal);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    scene.add(mesh);
    const n = spec.id === 'p1' || spec.id === 'p2' ? 2 : 1;
    const studs = interiorPoints(spec.outer, spec.holes, n).map(([x, y]) => {
      const s = new THREE.Mesh(studGeo, stud);
      const hole = new THREE.Mesh(holeGeo, holeMat);
      scene.add(s, hole);
      return { x, y, s, hole };
    });
    return { id: spec.id, mesh, studs };
  });

  // Laser: a bright strip revealed along the kerf, plus a soft glow.
  const kdx = KERF_B[0] - KERF_A[0], kdy = KERF_B[1] - KERF_A[1];
  const kLen = Math.hypot(kdx, kdy), kAng = Math.atan2(kdy, kdx);
  const additive = color => new THREE.MeshBasicMaterial({
    color, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false,
  });
  const laser = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), additive(0xe9d3a0));
  const glow = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), additive(0xffd9a0));
  laser.rotation.z = glow.rotation.z = kAng;
  glow.scale.set(kLen, 0.02, 1);
  glow.position.set(KERF_A[0] + kdx / 2, KERF_A[1] + kdy / 2, FRONT);
  scene.add(laser, glow);

  // Light: one key raking from the upper left, a low fill.
  const key = new THREE.DirectionalLight(0xfff1dc, 2.4);
  key.position.set(-0.9, 0.62, 0.75).multiplyScalar(3);
  key.castShadow = true;
  key.shadow.mapSize.set(narrow() || coarse ? 1024 : 2048, narrow() || coarse ? 1024 : 2048);
  key.shadow.radius = 4;
  key.shadow.bias = -0.0005;
  key.shadow.normalBias = 0.004;
  Object.assign(key.shadow.camera, { left: -0.95, right: 0.95, top: 0.85, bottom: -0.85, near: 0.5, far: 7 });
  key.shadow.camera.updateProjectionMatrix();
  scene.add(key, key.target);
  scene.add(new THREE.HemisphereLight(0xdfe8e6, 0x1a3a3f, 0.85));

  const camera = new THREE.PerspectiveCamera(FOV, 1, 0.01, 50);
  const target = new THREE.Vector3(0, 0, 0.05);
  let dist = 3;

  function pose(state, time) {
    const o = pieceOffsets(state.explode);
    for (const p of pieces) {
      const { dx, dy, dz } = o[p.id];
      p.mesh.position.set(dx, dy, dz);
      for (const st of p.studs) {
        st.s.position.set(st.x + dx, st.y + dy, 0);
        st.s.scale.set(1, 1, dz);
        st.hole.position.set(st.x + dx, st.y + dy, 0.0005);
      }
    }
    stud.opacity = state.explode;
    holeMat.opacity = state.explode * 0.85;
    stud.visible = holeMat.visible = state.explode > 0.001;

    const len = kLen * state.laser;
    laser.scale.set(Math.max(len, 1e-4), 0.004, 1);
    laser.position.set(KERF_A[0] + Math.cos(kAng) * len / 2, KERF_A[1] + Math.sin(kAng) * len / 2, FRONT);
    laser.material.opacity = state.laserVis;
    glow.material.opacity = state.glow * 0.6;
    laser.visible = state.laserVis > 0.001;
    glow.visible = state.glow > 0.001;

    const drift = state.drift * 1.5 * DEG * Math.sin((2 * Math.PI * time) / 14);
    const yaw = state.cam * 28 * DEG * (rtl ? -1 : 1) + drift;
    const pitch = state.cam * 8 * DEG;
    camera.position.set(
      target.x + dist * Math.sin(yaw) * Math.cos(pitch),
      target.y + dist * Math.sin(pitch),
      target.z + dist * Math.cos(yaw) * Math.cos(pitch));
    camera.lookAt(target);
  }

  // Projected extent of the whole assembly for a given pose, in CSS px.
  const corner = new THREE.Vector3();
  function extent(state) {
    pose(state, 0);
    scene.updateMatrixWorld(true);
    camera.updateMatrixWorld(true);
    const w = host.clientWidth, h = host.clientHeight;
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (const p of pieces) {
      const bb = p.mesh.geometry.boundingBox || (p.mesh.geometry.computeBoundingBox(), p.mesh.geometry.boundingBox);
      for (let i = 0; i < 8; i++) {
        corner.set(i & 1 ? bb.max.x : bb.min.x, i & 2 ? bb.max.y : bb.min.y, i & 4 ? bb.max.z : bb.min.z)
          .applyMatrix4(p.mesh.matrixWorld).project(camera);
        const sx = (corner.x + 1) / 2 * w, sy = (1 - corner.y) / 2 * h;
        x0 = Math.min(x0, sx); x1 = Math.max(x1, sx); y0 = Math.min(y0, sy); y1 = Math.max(y1, sy);
      }
    }
    return { w: x1 - x0, h: y1 - y0 };
  }

  // Match the still's size and position at p = 0, then make sure the fully
  // exploded, turned assembly fits; shrink both together if it does not.
  function solve() {
    const w = host.clientWidth, h = host.clientHeight;
    if (!w || !h) return;
    camera.aspect = w / h;
    for (let pass = 0; pass < 2; pass++) {
      const hr = host.getBoundingClientRect(), sr = still.getBoundingClientRect();
      const cx = (sr.left + sr.width / 2 - hr.left) / w, cy = (sr.top + sr.height / 2 - hr.top) / h;
      camera.setViewOffset(w, h, (0.5 - cx) * w, (0.5 - cy) * h, w, h);
      // Lockup is 1 stage unit wide; its front face sits near the target plane.
      dist = h / (2 * Math.tan((FOV / 2) * DEG) * (sr.width * (1892 / 1972)));
      camera.updateProjectionMatrix();
      const ex = extent({ ...stateAt(0.6), explode: 1, cam: 1, drift: 0 });
      const k = Math.min(1, (0.86 * w) / ex.w, (0.6 * h) / ex.h);
      if (k > 0.98) break;
      const cur = parseFloat(getComputedStyle(still).getPropertyValue('--still-scale')) || 1;
      still.style.setProperty('--still-scale', String((cur * k).toFixed(3)));
    }
  }

  function resize() {
    const w = host.clientWidth, h = host.clientHeight;
    if (!w || !h) return;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, narrow() ? 1.25 : 1.75));
    renderer.setSize(w, h, false);
    solve();
    draw(true);
  }

  let last = { ps: -1, t: 0 }, readyFired = false;
  function draw(force, state, ps, time = performance.now() / 1000) {
    if (!state) ({ state, ps } = getState());
    // Drift-only frames are capped at 30 fps.
    if (!force && ps === last.ps && time - last.t < 1 / 30) return;
    pose(state, time);
    renderer.render(scene, camera);
    last = { ps, t: time };
    if (!readyFired) {
      readyFired = true;
      requestAnimationFrame(() => { canvas.style.opacity = '1'; onReady(); });
    }
  }

  const ro = new ResizeObserver(resize);
  ro.observe(host);
  resize();

  return {
    render(state, ps, time) { draw(false, state, ps, time); },
    dispose() {
      ro.disconnect();
      canvas.removeEventListener('webglcontextlost', lost);
      scene.traverse(o => { if (o.geometry) o.geometry.dispose(); });
      [metal, stud, holeMat, wallMat, laser.material, glow.material].forEach(m => m.dispose());
      wallTex.dispose();
      envRT.dispose();
      pmrem.dispose();
      renderer.dispose();
      canvas.remove();
    },
  };
}
