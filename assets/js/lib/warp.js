// Corner-pin warp for the wall preview: maps a flat rectangle (the rendered
// sign) onto any four-cornered shape on the photo, the way a sign on a wall
// seen at an angle is foreshortened. Canvas 2D has no perspective transform,
// so the source is cut into a grid of triangles, each drawn with an affine map.

// Solve the 8 unknowns of the homography taking the unit square
// (0,0)(1,0)(1,1)(0,1) to quad [tl, tr, br, bl].
export function squareToQuad(q) {
  const [[x0, y0], [x1, y1], [x2, y2], [x3, y3]] = q;
  const dx1 = x1 - x2, dx2 = x3 - x2, dy1 = y1 - y2, dy2 = y3 - y2;
  const sx = x0 - x1 + x2 - x3, sy = y0 - y1 + y2 - y3;
  let g = 0, h = 0;
  const den = dx1 * dy2 - dx2 * dy1;
  if (Math.abs(sx) > 1e-9 || Math.abs(sy) > 1e-9) {
    if (Math.abs(den) < 1e-12) return null;
    g = (sx * dy2 - dx2 * sy) / den;
    h = (dx1 * sy - sx * dy1) / den;
  }
  return [x1 - x0 + g * x1, x3 - x0 + h * x3, x0,
          y1 - y0 + g * y1, y3 - y0 + h * y3, y0,
          g, h, 1];
}

export function apply(H, u, v) {
  const w = H[6] * u + H[7] * v + H[8];
  return [(H[0] * u + H[1] * v + H[2]) / w, (H[3] * u + H[4] * v + H[5]) / w];
}

// A quad is usable when it is convex and not folded over itself.
export function isConvex(q) {
  let sign = 0;
  for (let i = 0; i < 4; i++) {
    const [ax, ay] = q[i], [bx, by] = q[(i + 1) % 4], [cx, cy] = q[(i + 2) % 4];
    const z = (bx - ax) * (cy - by) - (by - ay) * (cx - bx);
    if (Math.abs(z) < 1e-6) return false;
    const s = Math.sign(z);
    if (sign && s !== sign) return false;
    sign = s;
  }
  return true;
}

export function inside(q, x, y) {
  let hit = false;
  for (let i = 0, j = 3; i < 4; j = i++) {
    const [xi, yi] = q[i], [xj, yj] = q[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) hit = !hit;
  }
  return hit;
}

export function centroid(q) {
  return [(q[0][0] + q[1][0] + q[2][0] + q[3][0]) / 4, (q[0][1] + q[1][1] + q[2][1] + q[3][1]) / 4];
}

// Scale and rotate a quad about its centroid.
export function transform(q, scale, angle = 0) {
  const [cx, cy] = centroid(q), c = Math.cos(angle) * scale, s = Math.sin(angle) * scale;
  return q.map(([x, y]) => [cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c]);
}

// Draw one source triangle onto one destination triangle.
function tri(ctx, img, s0, s1, s2, d0, d1, d2) {
  // Grow the clip triangle by a hair so neighbouring triangles leave no seams.
  const cx = (d0[0] + d1[0] + d2[0]) / 3, cy = (d0[1] + d1[1] + d2[1]) / 3;
  const grow = p => {
    const dx = p[0] - cx, dy = p[1] - cy, len = Math.hypot(dx, dy) || 1;
    return [p[0] + (dx / len) * 0.6, p[1] + (dy / len) * 0.6];
  };
  const [e0, e1, e2] = [grow(d0), grow(d1), grow(d2)];
  const den = s0[0] * (s1[1] - s2[1]) + s1[0] * (s2[1] - s0[1]) + s2[0] * (s0[1] - s1[1]);
  if (Math.abs(den) < 1e-9) return;
  const a = (d0[0] * (s1[1] - s2[1]) + d1[0] * (s2[1] - s0[1]) + d2[0] * (s0[1] - s1[1])) / den;
  const b = (d0[1] * (s1[1] - s2[1]) + d1[1] * (s2[1] - s0[1]) + d2[1] * (s0[1] - s1[1])) / den;
  const c = (d0[0] * (s2[0] - s1[0]) + d1[0] * (s0[0] - s2[0]) + d2[0] * (s1[0] - s0[0])) / den;
  const d = (d0[1] * (s2[0] - s1[0]) + d1[1] * (s0[0] - s2[0]) + d2[1] * (s1[0] - s0[0])) / den;
  const e = (d0[0] * (s1[0] * s2[1] - s2[0] * s1[1]) + d1[0] * (s2[0] * s0[1] - s0[0] * s2[1]) + d2[0] * (s0[0] * s1[1] - s1[0] * s0[1])) / den;
  const f = (d0[1] * (s1[0] * s2[1] - s2[0] * s1[1]) + d1[1] * (s2[0] * s0[1] - s0[0] * s2[1]) + d2[1] * (s0[0] * s1[1] - s1[0] * s0[1])) / den;
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(e0[0], e0[1]); ctx.lineTo(e1[0], e1[1]); ctx.lineTo(e2[0], e2[1]);
  ctx.closePath();
  ctx.clip();
  ctx.transform(a, b, c, d, e, f);
  ctx.drawImage(img, 0, 0);
  ctx.restore();
}

// Draw `img` (canvas or image, w x h) warped onto quad q in ctx's current space.
export function drawWarped(ctx, img, w, h, q, steps = 14) {
  const H = squareToQuad(q);
  if (!H) return;
  const pt = [];
  for (let j = 0; j <= steps; j++) {
    const row = [];
    for (let i = 0; i <= steps; i++) row.push(apply(H, i / steps, j / steps));
    pt.push(row);
  }
  const sw = w / steps, sh = h / steps;
  for (let j = 0; j < steps; j++) {
    for (let i = 0; i < steps; i++) {
      const s00 = [i * sw, j * sh], s10 = [(i + 1) * sw, j * sh];
      const s01 = [i * sw, (j + 1) * sh], s11 = [(i + 1) * sw, (j + 1) * sh];
      tri(ctx, img, s00, s10, s11, pt[j][i], pt[j][i + 1], pt[j + 1][i + 1]);
      tri(ctx, img, s00, s11, s01, pt[j][i], pt[j + 1][i + 1], pt[j + 1][i]);
    }
  }
}
