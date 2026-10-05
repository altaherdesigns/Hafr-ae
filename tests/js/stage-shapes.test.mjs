import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { buildShapeSpecs, interiorPoints, insidePolygon } from '../../assets/js/lib/paths.js';

const slice = JSON.parse(readFileSync(new URL('../../assets/data/slice.json', import.meta.url), 'utf8'));

test('seven pieces with the expected ids', () => {
  const specs = buildShapeSpecs(slice);
  assert.deepEqual(specs.map(s => s.id), ['p1', 'p2', 'dot', 'H', 'A', 'F', 'R']);
});

test('only A and R carry counters', () => {
  const holes = Object.fromEntries(buildShapeSpecs(slice).map(s => [s.id, s.holes.length]));
  assert.deepEqual(holes, { p1: 0, p2: 0, dot: 0, H: 0, A: 1, F: 0, R: 1 });
});

test('everything sits inside the stage frame', () => {
  for (const s of buildShapeSpecs(slice)) {
    for (const [x, y] of [...s.outer, ...s.holes.flat()]) {
      assert.ok(x >= -0.6 && x <= 0.6 && y >= -0.5 && y <= 0.5, `${s.id} ${x},${y}`);
    }
  }
});

test('the Arabic sits above the Latin in stage space', () => {
  const specs = Object.fromEntries(buildShapeSpecs(slice).map(s => [s.id, s]));
  const maxY = s => Math.max(...s.outer.map(p => p[1]));
  assert.ok(Math.min(...specs.dot.outer.map(p => p[1])) > maxY(specs.H));
});

test('standoff points sit inside each piece and clear of its counters', () => {
  for (const s of buildShapeSpecs(slice)) {
    const n = s.id === 'p1' || s.id === 'p2' ? 2 : 1;
    const pts = interiorPoints(s.outer, s.holes, n);
    assert.equal(pts.length, n, s.id);
    for (const pt of pts) {
      assert.ok(insidePolygon(pt, s.outer), `${s.id} outside`);
      for (const h of s.holes) assert.ok(!insidePolygon(pt, h), `${s.id} in a counter`);
    }
    if (n === 2) assert.ok(Math.hypot(pts[0][0] - pts[1][0], pts[0][1] - pts[1][1]) > 0.05, `${s.id} too close`);
  }
});
