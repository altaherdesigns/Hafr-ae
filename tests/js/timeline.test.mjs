import { test } from 'node:test';
import assert from 'node:assert/strict';
import { stateAt, approach, progress, pieceOffsets } from '../../assets/js/lib/timeline.js';

test('assembled at both ends', () => {
  for (const p of [0, 0.14, 0.92, 0.96, 1]) assert.equal(stateAt(p).explode, 0, `p=${p}`);
});

test('fully exploded through the hold', () => {
  for (const p of [0.55, 0.6, 0.7, 0.8]) assert.equal(stateAt(p).explode, 1, `p=${p}`);
});

test('captions exclusive and complete', () => {
  assert.deepEqual(stateAt(0.59).captions, [1, 0, 0]);
  assert.deepEqual(stateAt(0.67).captions, [0, 1, 0]);
  assert.deepEqual(stateAt(0.755).captions, [0, 0, 1]);
  for (const p of [0.3, 0.85, 1]) assert.deepEqual(stateAt(p).captions, [0, 0, 0]);
});

test('headline and laser windows', () => {
  assert.equal(stateAt(0).headline, 1);
  assert.equal(stateAt(0.2).headline, 0);
  assert.equal(stateAt(0.01).laserVis, 0);
  assert.ok(stateAt(0.06).laserVis > 0);
  assert.equal(stateAt(0.2).laserVis, 0);
  assert.equal(stateAt(0.09).glow, 0);
  assert.ok(stateAt(0.12).glow > 0.9);
  assert.equal(stateAt(0.15).glow, 0);
});

test('all fields within 0..1 across p', () => {
  for (let i = 0; i <= 1000; i++) {
    const s = stateAt(i / 1000);
    for (const v of [s.headline, s.laser, s.laserVis, s.glow, s.explode, s.cam, s.drift, ...s.captions]) {
      assert.ok(v >= 0 && v <= 1, `p=${i / 1000}`);
    }
  }
});

test('approach converges and is frame-rate independent', () => {
  let a = 0, b = 0;
  for (let i = 0; i < 60; i++) a = approach(a, 1, 1 / 60);
  for (let i = 0; i < 120; i++) b = approach(b, 1, 1 / 120);
  assert.ok(Math.abs(a - b) < 1e-9);
  assert.ok(a > 0.999);
});

test('progress clamps', () => {
  assert.equal(progress(100, 5000, 1000), 0);
  assert.equal(progress(-2000, 5000, 1000), 0.5);
  assert.equal(progress(-9000, 5000, 1000), 1);
  assert.equal(progress(-10, 800, 800), 0);
});

test('pieces separate across the kerf, never toward it', () => {
  const o = pieceOffsets(1);
  assert.ok(o.p1.dx > 0 && o.p1.dy < 0);
  assert.ok(o.p2.dx < 0 && o.p2.dy > 0);
  assert.ok(o.dot.dy > o.p2.dy);
  assert.ok(o.H.dx < o.A.dx && o.A.dx < 0 && o.F.dx > 0 && o.R.dx > o.F.dx);
  assert.deepEqual(pieceOffsets(0).p1, { dx: 0, dy: 0, dz: 0.03 });
  for (const k of Object.keys(o)) assert.ok(Math.abs(o[k].dz - 0.15) < 1e-12, k);
});
