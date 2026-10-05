// Scheduling core for the opening stage: smooths scroll progress toward its
// target and decides when the render loop may sleep (spec §5).
import { approach, stateAt } from './timeline.js';

const EPS = 0.0005;

export function createDriver({ read, apply, smoothing = true }) {
  let ps = read();
  let state = stateAt(ps);
  return {
    tick(dt) {
      const p = read();
      if (!smoothing) ps = p;
      else {
        ps = approach(ps, p, dt);
        if (Math.abs(p - ps) < EPS) ps = p;
      }
      state = stateAt(ps);
      apply(state, ps);
      return Math.abs(p - ps) >= EPS || state.drift > 0;
    },
    current: () => ({ state, ps }),
  };
}

// After 90 frames rendered while scrolling, a median frame interval above
// 45 ms means this device cannot carry the stage: drop to the still.
export function guard(intervals) {
  if (intervals.length < 90) return 'wait';
  const sorted = [...intervals].sort((a, b) => a - b);
  const mid = sorted.length >> 1;
  const median = sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  return median > 45 ? 'fail' : 'ok';
}
