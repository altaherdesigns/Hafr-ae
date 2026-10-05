import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parsePath, toStage, area, groupShapes } from '../../assets/js/lib/paths.js';

const slice = JSON.parse(readFileSync(new URL('../../assets/data/slice.json', import.meta.url), 'utf8'));

test('Arabic pieces are one polygon each', () => {
  for (const key of ['e-p1', 'e-p2', 'e-p3']) assert.equal(parsePath(slice[key]).length, 1, key);
});

test('Latin groups into H, A, F, R with counters as holes', () => {
  const groups = groupShapes(parsePath(slice['e-lat']));
  assert.equal(groups.length, 4);
  assert.deepEqual(groups.map(g => g.holes.length), [0, 1, 0, 1]);
  const minX = g => Math.min(...g.outer.map(p => p[0]));
  for (let i = 1; i < 4; i++) assert.ok(minX(groups[i]) > minX(groups[i - 1]));
});

test('holes wind opposite to their outer', () => {
  const groups = groupShapes(parsePath(slice['e-lat']));
  for (const g of groups) for (const h of g.holes) assert.ok(Math.sign(area(h)) !== Math.sign(area(g.outer)));
});

test('stage mapping centres the lockup and makes it 1 unit wide', () => {
  assert.deepEqual(toStage([914, -15]), [0, 0]);
  const xs = Object.entries(slice).filter(([k]) => k.startsWith('e-'))
    .flatMap(([, d]) => parsePath(d).flat().map(p => toStage(p)[0]));
  assert.ok(Math.abs(Math.max(...xs) - Math.min(...xs) - 1) < 0.001);
  assert.ok(toStage([0, -700])[1] > 0, 'SVG up becomes stage up');
});
