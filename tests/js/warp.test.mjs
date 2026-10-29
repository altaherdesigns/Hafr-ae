import { test } from 'node:test';
import assert from 'node:assert/strict';
import { squareToQuad, apply, isConvex, inside, transform, centroid } from '../../assets/js/lib/warp.js';

const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-6, `${a} != ${b}`);

test('maps the unit square corners onto the quad corners', () => {
  const q = [[10, 20], [310, 40], [290, 220], [30, 200]];
  const H = squareToQuad(q);
  [[0, 0], [1, 0], [1, 1], [0, 1]].forEach(([u, v], i) => {
    const [x, y] = apply(H, u, v);
    close(x, q[i][0]); close(y, q[i][1]);
  });
});

test('a rectangle maps affinely (centre to centre)', () => {
  const H = squareToQuad([[0, 0], [200, 0], [200, 100], [0, 100]]);
  const [x, y] = apply(H, 0.5, 0.5);
  close(x, 100); close(y, 50);
});

test('perspective quads keep straight lines but move the centre', () => {
  const q = [[0, 0], [100, 20], [100, 80], [0, 100]];
  const [x] = apply(squareToQuad(q), 0.5, 0.5);
  assert.ok(x > 50, 'the far side is shorter, so the centre moves toward it');
});

test('convexity and hit testing', () => {
  const q = [[0, 0], [100, 0], [100, 50], [0, 50]];
  assert.equal(isConvex(q), true);
  assert.equal(isConvex([[0, 0], [100, 50], [100, 0], [0, 50]]), false);
  assert.equal(inside(q, 50, 25), true);
  assert.equal(inside(q, 150, 25), false);
});

test('transform scales about the centroid', () => {
  const q = [[0, 0], [100, 0], [100, 50], [0, 50]];
  const t = transform(q, 2);
  assert.deepEqual(centroid(t), centroid(q));
  close(t[1][0] - t[0][0], 200);
});
