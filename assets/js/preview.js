// "See it on your wall": the visitor's photo, their family name set in a real
// Arabic font, drawn as cut letters standing off the wall, pinned in place with
// four corners. Everything runs in the browser; the photo never leaves the phone.
// Loaded on demand by site.js the first time the tool is opened.
import { drawWarped, inside, isConvex, transform } from './lib/warp.js';

const FONTS_CSS = 'https://fonts.googleapis.com/css2?family=Amiri:wght@700&family=Reem+Kufi:wght@700'
  + '&family=Aref+Ruqaa:wght@700&family=El+Messiri:wght@700&family=Rakkas&family=Outfit:wght@500&display=swap';

const STYLES = {
  naskh: { family: 'Amiri', weight: 700, scale: 1 },
  kufi: { family: 'Reem Kufi', weight: 700, scale: 0.92 },
  ruqaa: { family: 'Aref Ruqaa', weight: 700, scale: 1 },
  modern: { family: 'El Messiri', weight: 700, scale: 0.95 },
  bold: { family: 'Rakkas', weight: 400, scale: 1 },
};

// face: four gradient stops top to bottom; edge: the cut side; grain: surface texture
const FINISHES = {
  gold: { face: ['#f6dc93', '#c49a45', '#ecd07c', '#8f6c2b'], edge: '#5c4416', grain: 'brushed' },
  silver: { face: ['#f4f5f6', '#aeb2b7', '#e3e5e8', '#80858b'], edge: '#55595e', grain: 'brushed' },
  black: { face: ['#3d3d3d', '#181818', '#2b2b2b', '#0d0d0d'], edge: '#000000', grain: 'matte' },
  rust: { face: ['#b8682f', '#7c3c17', '#a5582a', '#5d2b10'], edge: '#3a1908', grain: 'rust' },
  white: { face: ['#ffffff', '#dcdcdc', '#f3f3f3', '#c2c2c2'], edge: '#9c9c9c', grain: 'matte' },
  antique: { face: ['#a8885a', '#5e4727', '#8f7246', '#3f2e17'], edge: '#2a1e0e', grain: 'brushed' },
};

const MAX_PHOTO = 2000;
const BASE = 220; // art font size in px

let fontsReady = null;
function loadFonts() {
  if (fontsReady) return fontsReady;
  if (!document.querySelector('link[data-try-fonts]')) {
    const l = document.createElement('link');
    l.rel = 'stylesheet'; l.href = FONTS_CSS; l.dataset.tryFonts = '';
    document.head.appendChild(l);
  }
  const wanted = Object.values(STYLES).map(s => `${s.weight} 40px "${s.family}"`).concat('500 40px "Outfit"');
  const loads = Promise.all(wanted.map(f => document.fonts.load(f, 'حفر 24 AB').catch(() => null)));
  fontsReady = Promise.race([loads, new Promise(r => setTimeout(r, 5000))]);
  return fontsReady;
}

// Deterministic noise so the texture doesn't shimmer as the visitor types.
function rng(seed) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}

function canvas(w, h) {
  const c = document.createElement('canvas');
  c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h));
  return c;
}

// ---------- the sign itself ----------
export function renderSign({ name, number, latin, style, finish, night, placeholder }) {
  const st = STYLES[style] || STYLES.naskh, fin = FINISHES[finish] || FINISHES.gold;
  const size = BASE * st.scale;
  const arFont = `${st.weight} ${size}px "${st.family}"`;
  const laFont = `500 ${Math.round(size * 0.3)}px "Outfit"`;
  const m = canvas(8, 8).getContext('2d');

  const items = [];
  const text = (name || '').trim() || placeholder;
  m.font = arFont; m.direction = 'rtl';
  const nm = m.measureText(text);
  const nameW = nm.actualBoundingBoxLeft + nm.actualBoundingBoxRight;
  let asc = nm.actualBoundingBoxAscent, desc = nm.actualBoundingBoxDescent;
  let numW = 0, nu = null;
  const num = (number || '').trim();
  const gap = size * 0.38;
  if (num) {
    m.direction = 'ltr';
    nu = m.measureText(num);
    numW = nu.actualBoundingBoxLeft + nu.actualBoundingBoxRight;
    asc = Math.max(asc, nu.actualBoundingBoxAscent); desc = Math.max(desc, nu.actualBoundingBoxDescent);
  }
  const row1W = nameW + (num ? gap + numW : 0);
  const la = (latin || '').trim().toUpperCase();
  let laW = 0, laA = 0, laD = 0, laL = 0;
  if (la) {
    m.font = laFont; m.direction = 'ltr';
    const lm = m.measureText(la);
    laW = lm.actualBoundingBoxLeft + lm.actualBoundingBoxRight; laL = lm.actualBoundingBoxLeft; laA = lm.actualBoundingBoxAscent; laD = lm.actualBoundingBoxDescent;
  }
  const row2Gap = la ? size * 0.22 : 0;
  const contentW = Math.max(row1W, laW), contentH = asc + desc + (la ? row2Gap + laA + laD : 0);
  const pad = size * 0.42;
  const W = contentW + pad * 2, H = contentH + pad * 2;

  // Row 1: the number sits to the left of the name, as it reads in Arabic.
  const row1X = pad + (contentW - row1W) / 2, baseY = pad + asc;
  if (num) items.push({ t: num, font: arFont, dir: 'ltr', x: row1X + nu.actualBoundingBoxLeft, y: baseY });
  // Right-aligned Arabic: x is the alignment point, actualBoundingBoxRight reaches past it.
  const nameL = row1X + (num ? numW + gap : 0);
  items.push({ t: text, font: arFont, dir: 'rtl', x: nameL + nameW - nm.actualBoundingBoxRight, y: baseY });
  if (la) items.push({ t: la, font: laFont, dir: 'ltr', x: pad + (contentW - laW) / 2 + laL, y: baseY + desc + row2Gap + laA });

  const glyphs = (ctx, dx = 0, dy = 0) => {
    for (const it of items) {
      ctx.font = it.font; ctx.direction = it.dir;
      ctx.textAlign = it.dir === 'rtl' ? 'right' : 'left';
      ctx.fillText(it.t, it.x + dx, it.y + dy);
    }
  };

  const art = canvas(W, H), ctx = art.getContext('2d');
  ctx.textBaseline = 'alphabetic';
  const FAR = W * 3; // draw off-canvas and keep only the shadow, which every browser blurs

  const shade = (color, blur, ox, oy, times = 1) => {
    ctx.save();
    ctx.shadowColor = color; ctx.shadowBlur = blur; ctx.shadowOffsetX = FAR + ox; ctx.shadowOffsetY = oy;
    ctx.fillStyle = '#000';
    for (let i = 0; i < times; i++) glyphs(ctx, -FAR, 0);
    ctx.restore();
  };

  if (night) {
    // Halo-lit: warm light spills onto the wall from behind the letters.
    shade('rgba(255, 178, 92, 0.95)', size * 0.22, 0, 0, 2);
    shade('rgba(255, 214, 150, 0.9)', size * 0.06, 0, 0, 1);
  } else {
    // Standing off the wall: a soft cast shadow, low sun from the upper left.
    shade('rgba(0, 0, 0, 0.5)', size * 0.05, size * 0.07, size * 0.1, 1);
    shade('rgba(0, 0, 0, 0.25)', size * 0.015, size * 0.03, size * 0.045, 1);
  }

  // The cut edge: the letter's thickness, stepped toward the shadow side.
  const depth = Math.round(size * 0.045);
  ctx.fillStyle = night ? '#050505' : fin.edge;
  for (let k = depth; k >= 1; k--) glyphs(ctx, k * 0.55, k * 0.8);

  // The face, on its own layer so the finish stays inside the letters.
  const face = canvas(W, H), f = face.getContext('2d');
  f.textBaseline = 'alphabetic';
  const g = f.createLinearGradient(0, pad, 0, pad + contentH);
  fin.face.forEach((c, i) => g.addColorStop(i / (fin.face.length - 1), c));
  f.fillStyle = g;
  glyphs(f);
  f.globalCompositeOperation = 'source-atop';
  const r = rng(W * 7 + H);
  if (fin.grain === 'brushed') {
    for (let y = 0; y < H; y += 2) {
      f.fillStyle = `rgba(${r() > 0.5 ? '255,255,255' : '0,0,0'},${(r() * 0.07).toFixed(3)})`;
      f.fillRect(0, y, W, 1 + (r() > 0.8 ? 1 : 0));
    }
  } else if (fin.grain === 'rust') {
    for (let i = 0; i < W * H / 90; i++) {
      f.fillStyle = r() > 0.5 ? 'rgba(60,22,6,0.35)' : 'rgba(214,128,62,0.3)';
      f.fillRect(r() * W, r() * H, 1 + r() * 3, 1 + r() * 3);
    }
  }
  // A 35° sheen across the face.
  const sh = f.createLinearGradient(0, 0, W, H * 0.7);
  sh.addColorStop(0.25, 'rgba(255,255,255,0)'); sh.addColorStop(0.45, 'rgba(255,255,255,0.22)');
  sh.addColorStop(0.6, 'rgba(255,255,255,0)');
  f.fillStyle = sh; f.fillRect(0, 0, W, H);
  if (night) { f.fillStyle = 'rgba(0,0,0,0.72)'; f.fillRect(0, 0, W, H); }
  ctx.drawImage(face, 0, 0);
  return { canvas: art, w: W, h: H };
}

// ---------- photos ----------
async function loadPhoto(file) {
  let src;
  try { src = await createImageBitmap(file, { imageOrientation: 'from-image' }); } catch (e) {
    src = await new Promise((res, rej) => {
      const img = new Image(); img.onload = () => res(img); img.onerror = rej; img.src = URL.createObjectURL(file);
    });
  }
  const s = Math.min(1, MAX_PHOTO / Math.max(src.width, src.height));
  const c = canvas(src.width * s, src.height * s);
  c.getContext('2d').drawImage(src, 0, 0, c.width, c.height);
  return c;
}

// A plain rendered wall for visitors who just want to look.
function sampleWall() {
  const c = canvas(1600, 1100), x = c.getContext('2d'), r = rng(42);
  const g = x.createLinearGradient(0, 0, 1600, 1100);
  g.addColorStop(0, '#e2cfac'); g.addColorStop(1, '#c4ab80');
  x.fillStyle = g; x.fillRect(0, 0, 1600, 1100);
  for (let i = 0; i < 60000; i++) {
    x.fillStyle = r() > 0.5 ? `rgba(255,250,235,${(r() * 0.18).toFixed(2)})` : `rgba(90,62,30,${(r() * 0.14).toFixed(2)})`;
    x.fillRect(r() * 1600, r() * 1100, 1 + r() * 2.5, 1 + r() * 2.5);
  }
  const v = x.createRadialGradient(500, 300, 100, 800, 550, 1100);
  v.addColorStop(0, 'rgba(255,240,210,0.25)'); v.addColorStop(1, 'rgba(60,40,20,0.35)');
  x.fillStyle = v; x.fillRect(0, 0, 1600, 1100);
  x.fillStyle = 'rgba(60,40,20,0.18)'; x.fillRect(0, 960, 1600, 6); // coping line
  return c;
}

// ---------- the tool ----------
export function mount(dialog) {
  const $ = s => dialog.querySelector(s);
  const cv = $('[data-try-canvas]'), ctx = cv.getContext('2d');
  const area = $('[data-stage-area]'), empty = $('[data-empty]'), hint = $('[data-hint]'), busy = $('[data-busy]');
  const form = $('[data-form]');
  const D = dialog.dataset;
  let photo = null, quad = null, sign = null, size = 100, view = { s: 1, ox: 0, oy: 0 };
  let dirty = true;

  const val = n => form.elements[n].value;
  const labelOf = n => {
    const el = form.querySelector(`input[name="${n}"]:checked`);
    return el ? el.closest('label').querySelector('[data-label]').textContent.trim() : '';
  };

  function rebuildSign() {
    sign = renderSign({ name: val('name'), number: val('number'), latin: val('latin'), style: val('style'),
      finish: val('finish'), night: val('light') === 'night', placeholder: D.placeholder });
    if (photo && quad) {
      // Keep the sign's position and height; stretch each edge about its midpoint to the new proportions.
      const hgt = (Math.hypot(quad[3][0] - quad[0][0], quad[3][1] - quad[0][1]) + Math.hypot(quad[2][0] - quad[1][0], quad[2][1] - quad[1][1])) / 2;
      const top = Math.hypot(quad[1][0] - quad[0][0], quad[1][1] - quad[0][1]);
      const bot = Math.hypot(quad[2][0] - quad[3][0], quad[2][1] - quad[3][1]);
      const oldW = (top + bot) / 2 || 1, newW = hgt * (sign.w / sign.h);
      const k = newW / oldW;
      quad = quad.map(([x, y], i) => {
        const left = i === 0 || i === 3;
        const a = left ? quad[i] : quad[i === 1 ? 0 : 3], b = left ? quad[i === 0 ? 1 : 2] : quad[i];
        const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
        return [mx + (x - mx) * k, my + (y - my) * k];
      });
      clamp();
    }
    dirty = true; draw();
  }

  // Keep the sign inside the photo: no wider than 90% of it.
  function clamp() {
    const xs = quad.map(p => p[0]), span = Math.max(...xs) - Math.min(...xs), max = photo.width * 0.9;
    if (span > max) quad = transform(quad, max / span);
  }

  function placeDefault() {
    const w = photo.width * 0.56, h = w * (sign.h / sign.w);
    const cx = photo.width / 2, cy = photo.height * 0.45;
    quad = [[cx - w / 2, cy - h / 2], [cx + w / 2, cy - h / 2], [cx + w / 2, cy + h / 2], [cx - w / 2, cy + h / 2]];
    size = 100; form.elements.size.value = 100;
  }

  function fit() {
    const r = area.getBoundingClientRect(), dpr = Math.min(2, window.devicePixelRatio || 1);
    cv.width = Math.round(r.width * dpr); cv.height = Math.round(r.height * dpr);
    cv.style.width = r.width + 'px'; cv.style.height = r.height + 'px';
    if (photo) {
      const s = Math.min(r.width / photo.width, r.height / photo.height);
      view = { s, ox: (r.width - photo.width * s) / 2, oy: (r.height - photo.height * s) / 2, dpr };
    } else view = { s: 1, ox: 0, oy: 0, dpr };
    dirty = true; draw();
  }

  function compose(c, s, ox, oy, handles) {
    const night = val('light') === 'night';
    c.save();
    c.translate(ox, oy); c.scale(s, s);
    c.drawImage(photo, 0, 0);
    if (night) { c.fillStyle = 'rgba(6, 16, 22, 0.66)'; c.fillRect(0, 0, photo.width, photo.height); }
    drawWarped(c, sign.canvas, sign.w, sign.h, quad, 16);
    c.restore();
    if (handles) {
      const pts = quad.map(([x, y]) => [ox + x * s, oy + y * s]);
      c.save();
      c.setLineDash([6, 6]); c.lineWidth = 1.5; c.strokeStyle = 'rgba(255,255,255,0.85)';
      c.shadowColor = 'rgba(0,0,0,0.5)'; c.shadowBlur = 3;
      c.beginPath(); pts.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y))); c.closePath(); c.stroke();
      c.setLineDash([]);
      for (const [x, y] of pts) {
        c.beginPath(); c.arc(x, y, 11, 0, Math.PI * 2);
        c.fillStyle = '#B9A06A'; c.fill(); c.lineWidth = 2; c.strokeStyle = '#fff'; c.stroke();
      }
      c.restore();
    }
  }

  function draw() {
    if (!dirty) return;
    dirty = false;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, cv.width, cv.height);
    if (!photo || !sign) return;
    ctx.setTransform(view.dpr, 0, 0, view.dpr, 0, 0);
    compose(ctx, view.s, view.ox, view.oy, true);
  }

  async function usePhoto(c) {
    busy.hidden = false;
    await loadFonts();
    busy.hidden = true;
    photo = c;
    sign = renderSign({ name: val('name'), number: val('number'), latin: val('latin'), style: val('style'),
      finish: val('finish'), night: val('light') === 'night', placeholder: D.placeholder });
    placeDefault();
    empty.hidden = true; hint.hidden = false; dialog.dataset.ready = '';
    fit();
  }

  dialog.querySelectorAll('[data-photo]').forEach(inp => inp.addEventListener('change', async () => {
    const file = inp.files && inp.files[0];
    inp.value = '';
    if (!file) return;
    try { await usePhoto(await loadPhoto(file)); } catch (e) { busy.hidden = true; }
  }));
  $('[data-sample]').addEventListener('click', () => usePhoto(sampleWall()));

  let pending = 0;
  form.addEventListener('input', e => {
    if (e.target.name === 'size') {
      const next = +e.target.value;
      if (quad) quad = transform(quad, next / size);
      size = next; dirty = true; draw(); return;
    }
    if (!photo) return;
    cancelAnimationFrame(pending);
    pending = requestAnimationFrame(rebuildSign);
  });
  form.addEventListener('submit', e => e.preventDefault());

  // ---------- pointer: drag the sign, drag a corner, pinch to resize and turn ----------
  const toImg = (e) => {
    const r = cv.getBoundingClientRect();
    return [(e.clientX - r.left - view.ox) / view.s, (e.clientY - r.top - view.oy) / view.s];
  };
  const pointers = new Map();
  let mode = null, corner = -1, start = null, startQuad = null, pinch = null;

  cv.addEventListener('pointerdown', e => {
    if (!photo) return;
    cv.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, toImg(e));
    hint.hidden = true;
    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      pinch = { d: Math.hypot(b[0] - a[0], b[1] - a[1]), a: Math.atan2(b[1] - a[1], b[0] - a[0]), q: quad.map(p => p.slice()) };
      mode = 'pinch'; return;
    }
    const p = pointers.get(e.pointerId), tol = 26 / view.s;
    corner = quad.findIndex(([x, y]) => Math.hypot(x - p[0], y - p[1]) < tol);
    if (corner >= 0) mode = 'corner';
    else if (inside(quad, p[0], p[1])) mode = 'move';
    else mode = null;
    start = p; startQuad = quad.map(q => q.slice());
  });
  cv.addEventListener('pointermove', e => {
    if (!pointers.has(e.pointerId)) {
      if (photo && e.pointerType === 'mouse') {
        const p = toImg(e), tol = 26 / view.s;
        cv.style.cursor = quad.some(([x, y]) => Math.hypot(x - p[0], y - p[1]) < tol) ? 'crosshair'
          : inside(quad, p[0], p[1]) ? 'move' : 'default';
      }
      return;
    }
    pointers.set(e.pointerId, toImg(e));
    if (mode === 'pinch' && pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      const d = Math.hypot(b[0] - a[0], b[1] - a[1]), ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
      quad = transform(pinch.q, d / pinch.d, ang - pinch.a);
    } else if (mode === 'move') {
      const p = pointers.get(e.pointerId), dx = p[0] - start[0], dy = p[1] - start[1];
      quad = startQuad.map(([x, y]) => [x + dx, y + dy]);
    } else if (mode === 'corner') {
      const p = pointers.get(e.pointerId), next = quad.map(q => q.slice());
      next[corner] = [startQuad[corner][0] + p[0] - start[0], startQuad[corner][1] + p[1] - start[1]];
      if (isConvex(next)) quad = next;
    } else return;
    dirty = true; draw();
  });
  const end = e => {
    pointers.delete(e.pointerId);
    if (pointers.size < 2 && mode === 'pinch') mode = null;
    if (!pointers.size) mode = null;
  };
  cv.addEventListener('pointerup', end);
  cv.addEventListener('pointercancel', end);
  cv.addEventListener('wheel', e => {
    if (!photo) return;
    e.preventDefault();
    quad = transform(quad, e.deltaY < 0 ? 1.06 : 1 / 1.06); dirty = true; draw();
  }, { passive: false });
  cv.addEventListener('keydown', e => {
    if (!photo) return;
    const step = 12 / view.s, moves = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
    if (moves[e.key]) quad = quad.map(([x, y]) => [x + moves[e.key][0], y + moves[e.key][1]]);
    else if (e.key === '+' || e.key === '=') quad = transform(quad, 1.06);
    else if (e.key === '-') quad = transform(quad, 1 / 1.06);
    else return;
    e.preventDefault(); dirty = true; draw();
  });

  // ---------- out: save, or send to Hafr ----------
  function exportBlob() {
    const out = canvas(photo.width, photo.height), o = out.getContext('2d');
    compose(o, 1, 0, 0, false);
    const fs = Math.max(14, Math.round(photo.width * 0.016));
    o.font = `500 ${fs}px "Outfit", sans-serif`; o.direction = document.documentElement.dir || 'ltr';
    o.textAlign = o.direction === 'rtl' ? 'left' : 'right';
    o.fillStyle = 'rgba(255,255,255,0.85)'; o.shadowColor = 'rgba(0,0,0,0.6)'; o.shadowBlur = 4;
    o.fillText(D.mark, o.direction === 'rtl' ? fs : out.width - fs, out.height - fs);
    return new Promise(res => out.toBlob(res, 'image/jpeg', 0.9));
  }
  function message() {
    const name = val('name').trim() || D.placeholder;
    return D.msg.replace('{name}', [name, val('number').trim()].filter(Boolean).join(' '))
      .replace('{style}', labelOf('style')).replace('{finish}', labelOf('finish'));
  }
  function download(blob) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = D.file;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }
  $('[data-save]').addEventListener('click', async () => { if (photo) download(await exportBlob()); });
  $('[data-send]').addEventListener('click', async () => {
    const text = message();
    if (!photo) { window.open(D.wa + encodeURIComponent(text), '_blank', 'noopener'); return; }
    const blob = await exportBlob();
    const file = new File([blob], D.file, { type: 'image/jpeg' });
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      try { await navigator.share({ files: [file], text }); return; } catch (e) { if (e.name === 'AbortError') return; }
    }
    // No file sharing here (most desktops): save the picture, then open the chat to attach it.
    download(blob);
    window.open(D.wa + encodeURIComponent(text + '\n' + D.attach), '_blank', 'noopener');
  });

  new ResizeObserver(() => fit()).observe(area);
  loadFonts().then(() => { if (photo) rebuildSign(); });
  return { fit };
}
