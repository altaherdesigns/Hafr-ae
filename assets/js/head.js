// Inlined into <head> by build.py. Decides before first paint whether the 3D
// stage runs (spec §5). The still is the default; this only upgrades.
function hafrEligible(env) {
  if (env.override === '3d') return true;
  if (env.override === 'still') return false;
  if (!env.importmap || !env.webgl2) return false;
  if (env.reducedMotion || env.saveData === true) return false;
  if (typeof env.deviceMemory === 'number' && env.deviceMemory < 4) return false;
  return true;
}

if (typeof document !== 'undefined') (function () {
  var w = window, dev = !!w.__HAFR_DEV, q = dev ? new URLSearchParams(location.search) : null;
  var s = q && q.get('stage'), override = s === '3d' || s === 'still' ? s : null;
  var pv = q && q.get('p'), pin = pv !== null && pv !== undefined && pv !== '' && !isNaN(+pv) ? Math.max(0, Math.min(1, +pv)) : null;
  var webgl2 = false;
  try {
    var gl = document.createElement('canvas').getContext('webgl2', { failIfMajorPerformanceCaveat: true });
    webgl2 = !!gl;
    var lose = gl && gl.getExtension('WEBGL_lose_context');
    if (lose) lose.loseContext();
  } catch (e) { webgl2 = false; }
  var env = {
    importmap: !!(w.HTMLScriptElement && HTMLScriptElement.supports && HTMLScriptElement.supports('importmap')),
    webgl2: webgl2,
    reducedMotion: !!(w.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches),
    saveData: !!(navigator.connection && navigator.connection.saveData),
    deviceMemory: navigator.deviceMemory,
    override: override
  };
  var eligible = hafrEligible(env);
  var root = document.documentElement;
  root.classList.add('js');
  if (eligible) root.classList.add('stage-3d');
  if (dev && q.get('qa')) root.classList.add('qa'); // development: flat layout for full-page screenshots
  w.__HAFR = { eligible: eligible, dev: dev, override: override, p: pin };
})();
