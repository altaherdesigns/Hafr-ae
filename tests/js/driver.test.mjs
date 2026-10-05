import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createDriver, guard } from '../../assets/js/lib/driver.js';

test('stops once converged outside the hold', () => {
  const d = createDriver({ read: () => 0.4, apply: () => {} });
  assert.equal(d.tick(1 / 60), false);
});

test('keeps ticking while the hold drift is active', () => {
  const d = createDriver({ read: () => 0.65, apply: () => {} });
  assert.equal(d.tick(1 / 60), true);
});

test('smoothed progress rises monotonically to a new target, then stops', () => {
  let target = 0;
  const seen = [];
  const d = createDriver({ read: () => target, apply: (s, ps) => seen.push(ps) });
  target = 1;
  let moving = true, frames = 0;
  while (moving && frames < 600) { moving = d.tick(1 / 60); frames++; }
  assert.equal(moving, false);
  for (let i = 1; i < seen.length; i++) assert.ok(seen[i] >= seen[i - 1]);
  assert.equal(seen[seen.length - 1], 1);
});

test('pinned progress applies exactly, with no smoothing', () => {
  let got = null;
  const d = createDriver({ read: () => 0.35, apply: (s, ps) => { got = ps; }, smoothing: false });
  d.tick(1 / 60);
  assert.equal(got, 0.35);
});

test('apply receives the timeline state for the smoothed progress', () => {
  let state = null;
  const d = createDriver({ read: () => 0.6, apply: s => { state = s; } });
  d.tick(1 / 60);
  assert.deepEqual(state.captions, [1, 0, 0]);
  assert.equal(d.current().ps, 0.6);
});

test('frame guard waits, then judges the median interval', () => {
  assert.equal(guard(Array(89).fill(60)), 'wait');
  assert.equal(guard(Array(90).fill(50)), 'fail');
  assert.equal(guard(Array(90).fill(16.7)), 'ok');
  assert.equal(guard([...Array(50).fill(16), ...Array(40).fill(200)]), 'ok', 'median, not mean');
});
