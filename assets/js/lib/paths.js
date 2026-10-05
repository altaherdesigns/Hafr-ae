// Locked Slice outlines are plain M/L/Z polylines in y-down SVG space.
// These helpers turn them into polygons in y-up stage space (spec §5).

export function parsePath(d) {
  const polys = [];
  let cur = null;
  const re = /([MLZ])|(-?\d*\.?\d+(?:e-?\d+)?)/gi;
  const nums = [];
  let cmd = null;
  const flush = () => {
    while (nums.length >= 2) {
      const pt = [nums.shift(), nums.shift()];
      if (cmd === 'M' || !cur) { cur = [pt]; polys.push(cur); cmd = 'L'; }
      else cur.push(pt);
    }
  };
  for (const m of d.matchAll(re)) {
    if (m[1]) {
      flush();
      const c = m[1].toUpperCase();
      if (c === 'Z') { cur = null; cmd = 'M'; }
      else cmd = c;
    } else nums.push(parseFloat(m[2]));
  }
  flush();
  return polys;
}

const z = v => v + 0;
export const toStage = ([x, y]) => [z((x - 914) / 1892), z(-(y + 15) / 1892)];

export function area(poly) {
  let s = 0;
  for (let i = 0; i < poly.length; i++) {
    const [x1, y1] = poly[i], [x2, y2] = poly[(i + 1) % poly.length];
    s += x1 * y2 - x2 * y1;
  }
  return s / 2;
}

export function insidePolygon(pt, poly) { return inside(pt, poly); }

function inside([x, y], poly) {
  let hit = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) hit = !hit;
  }
  return hit;
}

export function groupShapes(polys) {
  const bySize = [...polys].sort((a, b) => Math.abs(area(b)) - Math.abs(area(a)));
  const groups = [];
  for (const poly of bySize) {
    const parent = groups.find(g => inside(poly[0], g.outer));
    if (parent) parent.holes.push(poly);
    else groups.push({ outer: poly, holes: [] });
  }
  const minX = g => Math.min(...g.outer.map(p => p[0]));
  return groups.sort((a, b) => minX(a) - minX(b));
}

// The seven pieces of the locked lockup, in y-up stage units (spec §5).
export function buildShapeSpecs(slice) {
  const one = key => parsePath(slice[key])[0].map(toStage);
  const letters = groupShapes(parsePath(slice['e-lat'])).map((g, i) => ({
    id: ['H', 'A', 'F', 'R'][i],
    outer: g.outer.map(toStage),
    holes: g.holes.map(h => h.map(toStage)),
  }));
  return [
    { id: 'p1', outer: one('e-p1'), holes: [] },
    { id: 'p2', outer: one('e-p2'), holes: [] },
    { id: 'dot', outer: one('e-p3'), holes: [] },
    ...letters,
  ];
}

function segDist([px, py], [ax, ay], [bx, by]) {
  const dx = bx - ax, dy = by - ay;
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy || 1)));
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
}

function clearance(pt, rings) {
  let d = Infinity;
  for (const r of rings) for (let i = 0; i < r.length; i++) d = Math.min(d, segDist(pt, r[i], r[(i + 1) % r.length]));
  return d;
}

// Points well inside a piece (and outside its counters) for standoffs.
export function interiorPoints(outer, holes, n) {
  const xs = outer.map(p => p[0]), ys = outer.map(p => p[1]);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const rings = [outer, ...holes];
  const cands = [];
  const N = 28;
  for (let i = 0; i <= N; i++) for (let j = 0; j <= N; j++) {
    const pt = [x0 + ((x1 - x0) * i) / N, y0 + ((y1 - y0) * j) / N];
    if (!inside(pt, outer) || holes.some(h => inside(pt, h))) continue;
    cands.push({ pt, c: clearance(pt, rings) });
  }
  cands.sort((a, b) => b.c - a.c);
  const picked = [];
  if (cands.length) picked.push(cands[0]);
  while (picked.length < n && cands.length) {
    let best = null, bestScore = -1;
    for (const k of cands) {
      if (k.c < cands[0].c * 0.5) continue;
      const far = Math.min(...picked.map(p => Math.hypot(p.pt[0] - k.pt[0], p.pt[1] - k.pt[1])));
      if (far > bestScore) { bestScore = far; best = k; }
    }
    if (!best) break;
    picked.push(best);
  }
  return picked.map(k => k.pt);
}
