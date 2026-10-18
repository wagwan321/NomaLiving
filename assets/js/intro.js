/* ==========================================================================
   Noma Living: scroll walk-through
   Scrolling scrubs a Blender-rendered image sequence: the street in Hamra,
   the door opening, reception. Day or night is chosen from the sun's real
   position over Beirut (so it follows Lebanese time, whatever the visitor's
   clock says). Past the last frame the screen blurs into the page; scrolling
   back up walks you back out.
   Exposes window.NomaIntro = { enabled, end() }: end() is the scroll position
   where the rest of the website starts.
   Testing: ?time=day | ?time=night forces a mode, ?nointro turns it off.
   ========================================================================== */
(() => {
  const cine = document.getElementById("cine");
  const spacer = document.querySelector(".cine-spacer");
  const params = new URLSearchParams(location.search);
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const root = document.documentElement;

  if (!cine || reduce || params.has("nointro")) {
    cine?.remove(); spacer?.remove();
    window.NomaIntro = { enabled: false, end: () => 0 };
    return;
  }

  /* ---------- day or night in Beirut ---------- */
  const BEIRUT = { lat: 33.8938, lon: 35.5018 };
  // solar altitude in degrees (low-precision almanac formula, good to ~0.5°)
  const sunAltitude = (date, lat, lon) => {
    const rad = Math.PI / 180;
    const d = (date.getTime() - 946728000000) / 86400000;          // days since J2000.0
    const g = (357.529 + 0.98560028 * d) * rad;
    const q = 280.459 + 0.98564736 * d;
    const L = (q + 1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g)) * rad;
    const e = (23.439 - 0.00000036 * d) * rad;
    const ra = Math.atan2(Math.cos(e) * Math.sin(L), Math.cos(L));
    const dec = Math.asin(Math.sin(e) * Math.sin(L));
    const gmst = ((18.697374558 + 24.06570982441908 * d) % 24 + 24) % 24;
    const ha = (gmst * 15 + lon) * rad - ra;
    return Math.asin(Math.sin(lat * rad) * Math.sin(dec) + Math.cos(lat * rad) * Math.cos(dec) * Math.cos(ha)) / rad;
  };
  const forced = params.get("time");
  const mode = forced === "day" || forced === "night" ? forced
    : sunAltitude(new Date(), BEIRUT.lat, BEIRUT.lon) > -2 ? "day" : "night";
  root.dataset.time = mode;
  root.classList.add("has-cine", "cine-on");

  const clock = cine.querySelector(".cine__clock");
  const tick = () => {
    clock.textContent = new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Beirut", hour: "2-digit", minute: "2-digit" }).format(new Date());
  };
  tick(); setInterval(tick, 30000);

  /* ---------- frames: full 1920×1080 ---------- */
  // 290 rendered frames; phones take every second one to save data. Between two frames
  // the next one is blended in by exactly how far you've scrolled, so motion stays fluid
  // at any scroll speed instead of stepping frame to frame.
  // All frames are downloaded as compact files; only a window of frames around the
  // current position is decoded (off the main thread) so drawing never waits on a decode.
  const TOTAL = 290;
  const SMALL = Math.min(innerWidth, innerHeight) < 600;   // phones (either orientation)
  const STEP = SMALL ? 2 : 1;
  const ids = []; for (let i = 0; i < TOTAL; i += STEP) ids.push(i);
  const N = ids.length;
  const BACK = SMALL ? 5 : 8, AHEAD = SMALL ? 10 : 18;
  const src = (j) => `assets/cine/${mode}/${String(ids[j]).padStart(3, "0")}.webp?v=9`;
  const blobs = new Array(N);
  const bitmaps = new Array(N);
  const decoding = new Set();
  let pos = 0, dir = 1, drawnKey = "";
  const ready = (i) => i >= 0 && i < N && !!bitmaps[i];

  // at most two decodes in flight, nearest frame first, so decoding never crowds out drawing
  const MAX_DECODES = 2;
  const pump = () => {
    if (decoding.size >= MAX_DECODES) return;
    const a = Math.floor(pos);
    const lo = Math.max(0, a - (dir > 0 ? BACK : AHEAD)), hi = Math.min(N - 1, a + (dir > 0 ? AHEAD : BACK));
    for (let o = 0; o <= Math.max(a - lo, hi - a) && decoding.size < MAX_DECODES; o++) {
      for (const i of dir > 0 ? [a + o, a - o] : [a - o, a + o]) {
        if (i < lo || i > hi || !blobs[i] || bitmaps[i] || decoding.has(i)) continue;
        decoding.add(i);
        createImageBitmap(blobs[i]).then((bm) => {
          decoding.delete(i);
          const c = Math.floor(pos);
          if (i < c - BACK - 4 || i > c + AHEAD + 4) bm.close();
          else { bitmaps[i] = bm; if (Math.abs(i - pos) < 2) paint(); }
          pump();
        }, () => { decoding.delete(i); pump(); });
        if (decoding.size >= MAX_DECODES) break;
      }
    }
  };
  // keep decoded frames around the current position (more ahead in the scroll direction)
  const keepWindow = () => {
    const a = Math.floor(pos);
    const lo = Math.max(0, a - (dir > 0 ? BACK : AHEAD)), hi = Math.min(N - 1, a + (dir > 0 ? AHEAD : BACK));
    for (let i = 0; i < N; i++) {
      if (bitmaps[i] && (i < lo - 4 || i > hi + 4)) { bitmaps[i].close(); bitmaps[i] = null; }
    }
    pump();
  };
  const fetchFrame = (i) => fetch(src(i)).then((r) => r.blob()).then((b) => { blobs[i] = b; keepWindow(); }, () => {});
  // first frame, then the frames right after it, then a coarse-to-fine pass over the rest
  const order = [];
  for (let i = 0; i < Math.min(N, AHEAD + 1); i++) order.push(i);
  for (const step of [16, 8, 4, 2, 1]) for (let i = 0; i < N; i += step) if (!order.includes(i)) order.push(i);

  /* ---------- canvas: drawn 1:1, scaled to the screen by CSS (object-fit: cover) ---------- */
  const canvas = cine.querySelector(".cine__canvas");
  canvas.width = 1920; canvas.height = 1080;
  const ctx = canvas.getContext("2d", { alpha: false });
  const nearest = (i) => {
    for (let o = 0; o < N; o++) {
      if (ready(i - o)) return i - o;
      if (ready(i + o)) return i + o;
    }
    return -1;
  };
  function paint() {
    const a = Math.floor(pos), f = pos - a;
    const ka = nearest(a);
    if (ka < 0) return;
    const blend = ka === a && f > 0.02 && ready(a + 1);
    const key = blend ? `${a}:${Math.round(f * 64)}` : `${ka}`;
    if (key === drawnKey) return;
    ctx.globalAlpha = 1;
    ctx.drawImage(bitmaps[ka], 0, 0, 1920, 1080);
    if (blend) {
      ctx.globalAlpha = f;
      ctx.drawImage(bitmaps[a + 1], 0, 0, 1920, 1080);
      ctx.globalAlpha = 1;
    }
    drawnKey = key;
    if (!cine.classList.contains("is-ready")) cine.classList.add("is-ready");
  }

  (async () => {
    for (let k = 0; k < order.length; k += 6) await Promise.all(order.slice(k, k + 6).map(fetchFrame));
  })();

  /* ---------- scroll → frame (Lenis already smooths the scroll) ---------- */
  // the website starts one screen before the end of the spacer (main is pulled up by 100vh)
  const end = () => Math.max(1, spacer.offsetHeight - innerHeight);
  window.NomaIntro = { enabled: true, end };
  const clamp = (v) => Math.min(1, Math.max(0, v));
  const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a)); return t * t * (3 - 2 * t); };
  const set = (name, v) => cine.style.setProperty(name, v.toFixed(3));
  let through = false, queued = false, lastP = -1;

  const update = () => {
    queued = false;
    const p = clamp(scrollY / end());
    const next = p * (N - 1);
    if (next !== pos) { dir = next > pos ? 1 : -1; pos = next; keepWindow(); }
    paint();
    if (Math.abs(p - lastP) > 0.0005) {
      lastP = p;
      set("--hint", 1 - smooth(0, 0.03, p));
      set("--place", 1 - smooth(0.03, 0.1, p));
      set("--welcome", smooth(0.86, 0.97, p));
      set("--progress", p);
    }
    // the hand-off: past the last frame the screen blurs into the page; back up, it returns
    if (!through && p >= 0.999) {
      through = true;
      root.classList.add("page-blur");
      document.querySelector("main")?.offsetHeight;     // start the page blurred…
      cine.classList.add("is-through");
      root.classList.remove("cine-on", "page-blur");      // …and let it come into focus
    } else if (through && p < 0.985) {
      through = false;
      cine.classList.remove("is-through");
      root.classList.add("cine-on");
    }
  };
  const onScroll = () => { if (!queued) { queued = true; requestAnimationFrame(update); } };

  // ?fps shows a live meter: screen refreshes per second, and how many of them painted a new image
  if (params.has("fps")) {
    const meter = document.createElement("div");
    meter.style.cssText = "position:fixed;left:12px;top:84px;z-index:400;padding:8px 12px;border-radius:10px;background:rgba(0,0,0,.65);color:#fff;font:600 12px/1.5 ui-monospace,monospace;pointer-events:none";
    document.documentElement.appendChild(meter);
    let frames = 0, paints = 0, lastKey = drawnKey, t0 = performance.now();
    const loop = (t) => {
      frames++;
      if (drawnKey !== lastKey) { paints++; lastKey = drawnKey; }
      if (t - t0 >= 500) {
        const s = (t - t0) / 1000;
        meter.textContent = `${Math.round(frames / s)} fps · ${Math.round(paints / s)} new images/s · frame ${Math.floor(pos) + 1}/${N}`;
        frames = paints = 0; t0 = t;
      }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }
  addEventListener("scroll", onScroll, { passive: true });
  addEventListener("resize", onScroll);

  /* ---------- start ---------- */
  if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  if (!location.hash) scrollTo(0, 0);
  update();

  // the first screen of the website is placed (not animated) so the hand-off is just the blur
  document.addEventListener("DOMContentLoaded", () => {
    root.classList.add("instant");
    document.querySelectorAll(".hero [data-reveal], .hero [data-split]").forEach((el) => el.classList.add("is-in"));
    document.body.offsetHeight;
    setTimeout(() => root.classList.remove("instant"), 60);
    onScroll();
  });
})();
