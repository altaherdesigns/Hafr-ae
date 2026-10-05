// The opening stage's single timeline (spec §5). Everything the 3D stage and
// the still mode show is a pure function of scroll progress p in [0, 1].

export const clamp = (x, a, b) => Math.min(b, Math.max(a, x));

export function smooth(e0, e1, x) {
  const t = clamp((x - e0) / (e1 - e0), 0, 1);
  return t * t * (3 - 2 * t);
}

// Rises over [a0, a1], falls over [b0, b1].
const span = (p, a0, a1, b0, b1) => smooth(a0, a1, p) * (1 - smooth(b0, b1, p));
const z = v => v + 0; // folds -0 into 0

export function progress(rectTop, sectionH, stageH) {
  const travel = sectionH - stageH;
  if (travel <= 0) return 0;
  return clamp(-rectTop / travel, 0, 1);
}

const TAU = 0.12; // seconds
export function approach(ps, p, dt) {
  return ps + (p - ps) * (1 - Math.exp(-dt / TAU));
}

const CAPTIONS = [[0.55, 0.63], [0.63, 0.71], [0.71, 0.80]];
const FADE = 0.012;

export function stateAt(p) {
  return {
    headline: 1 - smooth(0.08, 0.14, p),
    laser: smooth(0.02, 0.11, p),
    laserVis: span(p, 0.02, 0.03, 0.11, 0.13),
    glow: span(p, 0.09, 0.12, 0.12, 0.15),
    explode: span(p, 0.15, 0.55, 0.80, 0.92),
    cam: span(p, 0.20, 0.55, 0.80, 0.92),
    captions: CAPTIONS.map(([a, b]) => span(p, a, a + FADE, b - FADE, b)),
    drift: span(p, 0.55, 0.58, 0.77, 0.80),
  };
}

// Directions are perpendicular to the 35° kerf, in y-up stage space.
const ACROSS = [0.574, -0.819];
const ORDER = ['p1', 'p2', 'dot', 'H', 'A', 'F', 'R'];
const LETTER_DX = { H: -0.045, A: -0.015, F: 0.015, R: 0.045 };
const STAGGER = 0.04;
const MAX_DELAY = STAGGER * (ORDER.length - 1);

export function pieceOffsets(explode) {
  const out = {};
  ORDER.forEach((id, i) => {
    const e = clamp((explode * (1 + MAX_DELAY) - i * STAGGER), 0, 1);
    let dx = 0, dy = 0;
    if (id === 'p1') { dx = ACROSS[0] * 0.06 * e; dy = ACROSS[1] * 0.06 * e; }
    else if (id === 'p2' || id === 'dot') {
      dx = -ACROSS[0] * 0.06 * e; dy = -ACROSS[1] * 0.06 * e + (id === 'dot' ? 0.03 * e : 0);
    } else dx = LETTER_DX[id] * e;
    out[id] = { dx: z(dx), dy: z(dy), dz: 0.03 + 0.12 * e };
  });
  return out;
}
