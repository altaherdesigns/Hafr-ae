import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const code = readFileSync(new URL('../../assets/js/head.js', import.meta.url), 'utf8');
const ctx = {};
vm.createContext(ctx);
vm.runInContext(code, ctx);
const eligible = ctx.hafrEligible;

const OK = { importmap: true, webgl2: true, reducedMotion: false, saveData: false, deviceMemory: undefined, override: null };

test('capable browser with no signals gets 3D', () => {
  assert.equal(eligible(OK), true);
});

test('reduced motion, data saver and low memory get the still', () => {
  assert.equal(eligible({ ...OK, reducedMotion: true }), false);
  assert.equal(eligible({ ...OK, saveData: true }), false);
  assert.equal(eligible({ ...OK, deviceMemory: 2 }), false);
  assert.equal(eligible({ ...OK, deviceMemory: 4 }), true);
});

test('no import maps or no WebGL 2 gets the still', () => {
  assert.equal(eligible({ ...OK, importmap: false }), false);
  assert.equal(eligible({ ...OK, webgl2: false }), false);
});

test('development override wins', () => {
  assert.equal(eligible({ ...OK, reducedMotion: true, override: '3d' }), true);
  assert.equal(eligible({ ...OK, override: 'still' }), false);
});

test('head.js does nothing outside a browser', () => {
  assert.equal(typeof ctx.__HAFR, 'undefined');
});
