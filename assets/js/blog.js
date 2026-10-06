// Guides: keep "On this page" open beside the text on wide screens, close it
// after a jump on small ones, and mark the section being read.
const toc = document.querySelector('[data-toc]');

if (toc) {
  const wide = window.matchMedia('(min-width: 1100px)');
  const sync = () => { if (wide.matches) toc.open = true; };
  sync();
  wide.addEventListener('change', sync);

  const links = [...toc.querySelectorAll('a[href^="#"]')];
  const heads = links.map(a => document.getElementById(decodeURIComponent(a.hash.slice(1))));
  links.forEach(a => a.addEventListener('click', () => { if (!wide.matches) toc.open = false; }));

  let queued = false;
  const mark = () => {
    queued = false;
    const line = Math.min(window.innerHeight * 0.35, 320);
    let current = -1;
    heads.forEach((h, i) => { if (h && h.getBoundingClientRect().top <= line) current = i; });
    links.forEach((a, i) => {
      if (i === current) a.setAttribute('aria-current', 'true');
      else a.removeAttribute('aria-current');
    });
  };
  const queue = () => { if (!queued) { queued = true; requestAnimationFrame(mark); } };
  addEventListener('scroll', queue, { passive: true });
  addEventListener('resize', queue);
  mark();
}
