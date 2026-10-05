// hafr.ae page behaviour. The still is the default; the 3D stage is an upgrade
// that is only requested when head.js judged the device eligible (spec §5).
import { progress } from './lib/timeline.js';
import { createDriver, guard } from './lib/driver.js';

const H = window.__HAFR || { eligible: false, dev: false, p: null };
const root = document.documentElement;
const rtl = root.dir === 'rtl';
const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');

function initHeader() {
  const hd = document.querySelector('[data-hd]');
  const stage = document.querySelector('[data-stage]');
  if (!hd) return;
  const surfaces = [...document.querySelectorAll('[data-surface]')];
  let queued = false;
  const update = () => {
    queued = false;
    const probe = hd.offsetHeight / 2;
    let tone = 'dark';
    for (const s of surfaces) {
      const r = s.getBoundingClientRect();
      if (r.top <= probe && r.bottom > probe) { tone = s.dataset.surface; break; }
    }
    hd.dataset.tone = tone;
    const pastStage = !stage || stage.getBoundingClientRect().bottom <= hd.offsetHeight;
    if (pastStage) hd.dataset.solid = ''; else delete hd.dataset.solid;
  };
  const queue = () => { if (!queued) { queued = true; requestAnimationFrame(update); } };
  addEventListener('scroll', queue, { passive: true });
  addEventListener('resize', queue);
  update();
}

function initReveals() {
  const els = [...document.querySelectorAll('[data-reveal]')];
  if (reduce.matches || !('IntersectionObserver' in window)) return;
  root.setAttribute('data-reveal-ready', '');
  const io = new IntersectionObserver(entries => {
    for (const e of entries) if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); }
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });
  els.forEach(el => io.observe(el));
  reduce.addEventListener('change', () => {
    if (!reduce.matches) return;
    els.forEach(el => el.classList.add('is-in'));
    root.removeAttribute('data-reveal-ready');
  });
}

function initStage() {
  const section = document.querySelector('[data-stage]');
  if (!section) return;
  const sticky = section.querySelector('[data-stage-sticky]');
  const still = section.querySelector('[data-still]');
  const host = section.querySelector('[data-canvas]');
  const headline = section.querySelector('[data-headline]');
  const caps = [...section.querySelectorAll('[data-cap]')];

  let stage3d = null, ready = false, fellBack = false, timer = 0;
  const intervals = [];

  const read = () => (H.p != null ? H.p
    : progress(section.getBoundingClientRect().top, section.offsetHeight, sticky.offsetHeight));

  const apply = (s, ps) => {
    headline.style.opacity = s.headline;
    headline.style.transform = `translateY(${((1 - s.headline) * -14).toFixed(2)}px)`;
    caps.forEach((c, i) => {
      const o = s.captions[i];
      c.style.opacity = o;
      c.style.transform = `translateY(${((1 - o) * 14).toFixed(2)}px)`;
    });
    if (stage3d && ready) stage3d.render(s, ps, performance.now() / 1000);
  };

  const driver = createDriver({ read, apply, smoothing: H.p == null });

  let raf = 0, last = 0, onScreen = true, scrolledAt = 0;
  const frame = t => {
    const dt = last ? Math.min(0.1, (t - last) / 1000) : 1 / 60;
    if (stage3d && ready && last && t - scrolledAt < 200 && intervals.length < 90) {
      intervals.push(t - last);
      if (guard(intervals) === 'fail') fallback('slow');
    }
    last = t;
    const moving = driver.tick(dt);
    raf = moving && onScreen && !document.hidden ? requestAnimationFrame(frame) : 0;
    if (!raf) last = 0;
  };
  const kick = () => { if (!raf && onScreen && !document.hidden) raf = requestAnimationFrame(frame); };

  addEventListener('scroll', () => { scrolledAt = performance.now(); kick(); }, { passive: true });
  addEventListener('resize', kick);
  document.addEventListener('visibilitychange', kick);
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(([e]) => { onScreen = e.isIntersecting; kick(); }).observe(section);
  }
  kick();

  function fallback(why) {
    if (fellBack) return;
    fellBack = true;
    clearTimeout(timer);
    if (stage3d) { try { stage3d.dispose(); } catch (e) { /* already gone */ } }
    stage3d = null; ready = false;
    host.replaceChildren();
    still.removeAttribute('data-hidden');
    root.classList.remove('stage-3d');
    root.dataset.stageMode = `still:${why}`;
    kick();
  }

  // The 6 s readiness budget only counts while the page is visible: a page
  // opened in a background tab must not give up on 3D before anyone sees it.
  function armTimer() {
    clearTimeout(timer);
    if (ready || fellBack) return;
    if (document.hidden) {
      document.addEventListener('visibilitychange', armTimer, { once: true });
      return;
    }
    timer = setTimeout(() => {
      if (document.hidden) armTimer(); else fallback('timeout');
    }, 6000);
  }

  async function load3d() {
    armTimer();
    try {
      const mod = await import('./stage.js');
      if (fellBack) return;
      stage3d = await mod.start({
        host, still, rtl,
        getState: () => driver.current(),
        onReady: () => {
          if (fellBack) return;
          clearTimeout(timer);
          ready = true;
          root.dataset.stageMode = '3d';
          still.setAttribute('data-hidden', '');
          kick();
        },
        onFail: why => fallback(why),
      });
      if (fellBack && stage3d) { stage3d.dispose(); stage3d = null; }
    } catch (e) {
      fallback('error');
    }
  }

  if (H.eligible) load3d(); else root.dataset.stageMode = 'still';
  reduce.addEventListener('change', () => { if (reduce.matches && !H.override) fallback('reduced-motion'); });
}

initHeader();
initReveals();
initStage();

// Development builds only: ?at=<section id> jumps straight to a section (for screenshots).
if (H.dev) {
  const at = new URLSearchParams(location.search).get('at');
  const target = at && document.getElementById(at);
  if (target) requestAnimationFrame(() => target.scrollIntoView({ behavior: 'instant', block: 'start' }));
}
