/* ==========================================================================
   Noma Living: scroll walk-through
   Scrolling scrubs a Blender-rendered image sequence: the street in Hamra,
   the door opening, reception. Day or night is chosen from the sun's real
   position over Beirut (so it follows Lebanese time, whatever the visitor's
   clock says). Past the last frame the screen blurs into the page; scrolling
   back up walks you back out.
   Exposes window.NomaIntro = { enabled, end(), sync() }: end() is the scroll
   position where the rest of the website starts; sync() redraws right away
   (main.js calls it from the smooth-scroll loop so the picture never lags a frame).
   Testing: ?time=day | ?time=night forces a mode, ?nointro turns it off,
   ?fps shows a live meter, ?q=0|1|2 forces a quality level.
   ========================================================================== */
(() => {
  const cine = document.getElementById("cine");
  const spacer = document.querySelector(".cine-spacer");
  const params = new URLSearchParams(location.search);
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const root = document.documentElement;
  const canvas = cine && cine.querySelector(".cine__canvas");
  const ctx = canvas && canvas.getContext("2d", { alpha: false });

  if (!cine || !ctx || !window.fetch || reduce || params.has("nointro")) {
    cine?.remove(); spacer?.remove();
    window.NomaIntro = { enabled: false, end: () => 0, sync() {} };
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

  /* ---------- frames ---------- */
  // Two renders of the walk-through: landscape for computers and sideways screens, portrait for
  // phones and upright tablets, so nothing important is cropped away. Each comes in three
  // quality levels (1080p, 720p, 540p); every device gets the sharpest one its screen can show
  // and its memory, processor and connection can carry. Phones load every second frame.
  // Between two frames the next one is blended in by exactly how far you've scrolled, so motion
  // stays fluid at any speed. Frames download as compact files (the ones just ahead of you
  // first) and only a window around the current position is decoded, off the main thread.
  // A frame-rate watch steps down a level if a device keeps missing frames, and remembers it.
  // Where each frame sits along the scroll comes from blender/frames.py (even-pace timeline).
  const V = 16;                                     // bump when the frames change
  const TL = window.NOMA_TIMELINE || null;
  const TOTAL = TL ? TL.length : 290;
  const MAX_DECODES = 2, MAX_FETCHES = 6;
  const TIERS = [["", 1920, 1080], ["-md", 1280, 720], ["-sm", 960, 540]];   // suffix, long, short side
  const nav = navigator, conn = nav.connection || {};
  const smallScreen = () => Math.min(innerWidth, innerHeight) < 600;

  // steps this device has had to take down before (remembered for a week)
  const DROP_KEY = "noma-cine-drop";
  let drop = 0;
  try {
    const d = JSON.parse(localStorage.getItem(DROP_KEY));
    if (d && Date.now() - d.t < 6048e5) drop = Math.min(2, d.n | 0);
  } catch (e) { /* storage blocked: start fresh */ }
  const forcedTier = params.has("q") ? Math.min(2, Math.max(0, +params.get("q") | 0)) : -1;

  const pickTier = (portrait) => {
    if (forcedTier >= 0) return forcedTier;
    // pixels the picture really covers (cover-scaled, sharp screens counted up to 2×, 1.5× on phones)
    const dpr = Math.min(window.devicePixelRatio || 1, smallScreen() ? 1.5 : 2);
    const need = (portrait ? Math.max(innerWidth, innerHeight * 9 / 16) : Math.max(innerHeight, innerWidth * 9 / 16)) * dpr;
    let t = need > 760 ? 0 : need > 560 ? 1 : 2;
    // what the device and its connection can comfortably carry
    const mem = nav.deviceMemory, cores = nav.hardwareConcurrency, net = conn.effectiveType || "";
    if (conn.saveData || /2g/.test(net) || (mem && mem <= 2) || (cores && cores <= 2)) t = 2;
    else if (net === "3g" || (mem && mem <= 4)) t = Math.max(t, 1);
    return Math.min(2, t + drop);
  };
  // decoded frames take width × height × 4 bytes each: keep the window within a memory budget
  const budget = () => (smallScreen() ? 70 : nav.deviceMemory && nav.deviceMemory <= 4 ? 120 : 230) * 1e6;

  // decode off the main thread where possible; older browsers decode through an <img>
  const decode = window.createImageBitmap ? (b) => createImageBitmap(b) : (b) => {
    const img = new Image();
    img.src = URL.createObjectURL(b);
    return img.decode().then(() => img, (e) => { URL.revokeObjectURL(img.src); throw e; });
  };
  const release = (d) => { if (d) d.close ? d.close() : URL.revokeObjectURL(d.src); };

  let folder = "", STEP = 1, ids = [], N = 0, BACK = 8, AHEAD = 18, W = 1920, H = 1080, gen = 0, tier = 0;
  let portraitSet = false, noPortrait = false, off = false;
  let blobs = [], bitmaps = [], state = [], tries = [], decoding = new Set();
  let inflight = 0, cursor = 0, order = [], loaded = 0, decodedAny = false, decodeFails = 0;
  let pos = 0, dir = 1, drawnKey = "", settleUntil = 0;
  const ready = (i) => i >= 0 && i < N && !!bitmaps[i];
  const src = (j) => `assets/cine/${folder}/${String(ids[j]).padStart(3, "0")}.webp?v=${V}`;

  const pump = () => {
    if (decoding.size >= MAX_DECODES) return;
    const g = gen, a = Math.floor(pos);
    const lo = Math.max(0, a - (dir > 0 ? BACK : AHEAD)), hi = Math.min(N - 1, a + (dir > 0 ? AHEAD : BACK));
    for (let o = 0; o <= Math.max(a - lo, hi - a) && decoding.size < MAX_DECODES; o++) {
      for (const i of dir > 0 ? [a + o, a - o] : [a - o, a + o]) {
        if (i < lo || i > hi || !blobs[i] || bitmaps[i] || decoding.has(i)) continue;
        decoding.add(i);
        decode(blobs[i]).then((bm) => {
          if (g !== gen) { release(bm); return; }
          decoding.delete(i); decodedAny = true;
          const c = Math.floor(pos);
          if (i < c - BACK - 4 || i > c + AHEAD + 4) release(bm);
          else { bitmaps[i] = bm; if (Math.abs(i - pos) < 2) paint(); }
          pump();
        }, () => {
          if (g !== gen) return;
          decoding.delete(i);
          // this browser can't read the frames at all (no WebP): go straight to the website
          if (!decodedAny && ++decodeFails >= 3) { disable(); return; }
          blobs[i] = null; state[i] = 0;            // a damaged download: fetch it again
          pump();
        });
        if (decoding.size >= MAX_DECODES) break;
      }
    }
  };

  // downloads: up to 6 at once, always the frames just ahead of you first, then a coarse-to-fine
  // pass over the whole walk-through so a fast scroll finds a nearby frame anywhere
  const nextFetch = () => {
    const a = Math.floor(pos);
    for (let o = -2; o <= AHEAD * 2; o++) {
      const i = a + o * dir;
      if (i >= 0 && i < N && !state[i]) return i;
    }
    while (cursor < order.length && state[order[cursor]]) cursor++;
    return cursor < order.length ? order[cursor] : -1;
  };
  const pumpFetch = () => {
    const g = gen;
    while (inflight < MAX_FETCHES) {
      const i = nextFetch();
      if (i < 0) return;
      state[i] = 1; inflight++;
      const near = Math.abs(i - pos) <= AHEAD;
      fetch(src(i), { priority: near ? "high" : "low" }).then((r) => {
        if (!r.ok) throw new Error(r.status);
        return r.blob();
      }).then((b) => {
        if (g !== gen) return;
        inflight--; state[i] = 2; blobs[i] = b; loaded++;
        set("--loaded", loaded / N);
        if (loaded === N) cine.classList.add("is-loaded");
        if (waiting && enough()) openGate();
        keepWindow();
      }, () => {
        if (g !== gen) return;
        inflight--;
        // no portrait frames on the server: use the landscape ones
        if (portraitSet && !loaded) { noPortrait = true; loadSet(); return; }
        // a dropped connection: try again a little later, three times
        tries[i] = (tries[i] || 0) + 1;
        if (tries[i] <= 3) setTimeout(() => { if (g === gen) { state[i] = 0; pumpFetch(); } }, 1500 * tries[i]);
        pumpFetch();
      });
    }
  };

  // First visit: hold scrolling on the opening shot (with the loading line) until the stretch
  // ahead and a coarse pass over the whole walk-through have arrived, so a slow connection never
  // scrolls into frames that aren't there yet. Never longer than WAIT_MAX.
  const WAIT_MAX = 6000;
  let waiting = false;
  const enough = () => {
    for (let i = 0; i < Math.min(N, AHEAD * 2); i++) if (state[i] !== 2) return false;
    for (let i = 0; i < N; i += 16 / STEP) if (state[i] !== 2) return false;
    return true;
  };
  const holdScroll = (on) => {
    const l = typeof lenis !== "undefined" && lenis;
    if (l) on ? l.stop() : l.start();
    root.classList.toggle("cine-wait", on);
  };
  function openGate() {
    if (!waiting) return;
    waiting = false;
    holdScroll(false);
    root.classList.add("cine-opening");
    setTimeout(() => root.classList.remove("cine-opening"), 900);
  }

  // keep decoded frames around the current position (more ahead in the scroll direction)
  const keepWindow = () => {
    const a = Math.floor(pos);
    const lo = Math.max(0, a - (dir > 0 ? BACK : AHEAD)), hi = Math.min(N - 1, a + (dir > 0 ? AHEAD : BACK));
    for (let i = 0; i < N; i++) {
      if (bitmaps[i] && (i < lo - 4 || i > hi + 4)) { release(bitmaps[i]); bitmaps[i] = null; }
    }
    pump(); pumpFetch();
  };

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
    ctx.drawImage(bitmaps[ka], 0, 0, W, H);
    if (blend) {
      ctx.globalAlpha = f;
      ctx.drawImage(bitmaps[a + 1], 0, 0, W, H);
      ctx.globalAlpha = 1;
    }
    drawnKey = key;
    if (!cine.classList.contains("is-ready")) cine.classList.add("is-ready");
  }

  // choose the frame set for this screen (and re-choose when it rotates, resizes or struggles)
  const loadSet = () => {
    const portrait = !noPortrait && innerHeight > innerWidth * 1.05;
    const t = pickTier(portrait);
    const name = `${mode}${portrait ? "-p" : ""}${TIERS[t][0]}`;
    const step = portrait || smallScreen() ? 2 : 1;
    if (name === folder && step === STEP) return false;
    gen++;
    bitmaps.forEach(release);
    folder = name; STEP = step; tier = t; portraitSet = portrait;
    const [, long, short] = TIERS[t];
    const nw = portrait ? short : long, nh = portrait ? long : short;
    if (nw !== canvas.width || nh !== canvas.height) {
      // keep showing the current picture (scaled) until the new frames arrive: no flash
      let snap = null;
      if (cine.classList.contains("is-ready")) {
        snap = document.createElement("canvas");
        snap.width = canvas.width; snap.height = canvas.height;
        snap.getContext("2d").drawImage(canvas, 0, 0);
      }
      canvas.width = nw; canvas.height = nh;
      if (snap) {
        const s = Math.max(nw / snap.width, nh / snap.height);
        ctx.drawImage(snap, (nw - snap.width * s) / 2, (nh - snap.height * s) / 2, snap.width * s, snap.height * s);
      }
    }
    W = nw; H = nh;
    const keep = Math.max(10, Math.min(30, Math.floor(budget() / (W * H * 4))));
    AHEAD = Math.round(keep * 0.68); BACK = keep - AHEAD;
    ids = []; for (let i = 0; i < TOTAL; i += STEP) ids.push(i);
    N = ids.length;
    blobs = new Array(N); bitmaps = new Array(N); state = new Array(N).fill(0); tries = [];
    decoding = new Set(); inflight = 0; cursor = 0; loaded = 0; drawnKey = "";
    cine.classList.remove("is-loaded"); set("--loaded", 0);
    pos = Math.min(N - 1, frameAt(clamp(scrollY / end())) / STEP);
    order = [];
    for (const s of [16, 8, 4, 2, 1]) for (let i = 0; i < N; i += s) if (s === 16 || i % (s * 2)) order.push(i);
    settleUntil = performance.now() + 1500; samples = [];
    pumpFetch();
    return true;
  };

  // the browser can't show the walk-through: take it out and start on the website
  function disable() {
    if (off) return;
    off = true; gen++;
    openGate();
    bitmaps.forEach(release);
    window.NomaIntro.enabled = false;
    root.classList.remove("has-cine", "cine-on", "page-blur");
    cine.remove(); spacer.remove();
    scrollTo(0, 0);
  }

  /* ---------- scroll → frame (Lenis already smooths the scroll) ---------- */
  // the website starts where <main> starts (main is pulled up over the end of the spacer);
  // measuring it directly stays right when mobile toolbars change the screen height
  const end = () => {
    if (off) return 0;
    const m = document.querySelector("main");
    return Math.max(1, m ? m.offsetTop : spacer.offsetHeight - innerHeight);
  };
  const clamp = (v) => Math.min(1, Math.max(0, v));
  const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a)); return t * t * (3 - 2 * t); };
  const set = (name, v) => cine.style.setProperty(name, v.toFixed(3));
  const frameAt = (p) => {
    if (!TL) return p * (TOTAL - 1);
    let lo = 0, hi = TOTAL - 1;
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (TL[mid] <= p) lo = mid; else hi = mid; }
    const span = TL[hi] - TL[lo];
    return lo + (span > 0 ? (p - TL[lo]) / span : 0);
  };
  let through = false, queued = false, lastP = -1, lastY = -1;

  const update = () => {
    queued = false;
    if (off) return;
    const y = scrollY;
    if (y !== lastY) { lastY = y; scrollAt = performance.now(); }
    const p = clamp(y / end());
    const next = Math.min(N - 1, frameAt(p) / STEP);
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
      if (userScrolled) holdAtSiteTop();
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
  window.NomaIntro = { enabled: true, end, sync: update };

  // Arriving at the website: however fast (or slowly) you were scrolling, land exactly on the
  // homepage's first screen and hold there while the blur plays, then let scrolling resume.
  let userScrolled = false;
  const HOLD_MS = 1300;
  const holdAtSiteTop = () => {
    const y = end();
    const smoothScroller = typeof lenis !== "undefined" && lenis;
    if (smoothScroller) {
      lenis.stop();
      lenis.scrollTo(y, { immediate: true, force: true });
    } else {
      root.style.overflow = "hidden";
      scrollTo(0, y);
    }
    setTimeout(() => {
      if (smoothScroller) lenis.start(); else root.style.overflow = "";
    }, HOLD_MS);
  };
  for (const ev of ["wheel", "touchmove", "keydown", "pointerdown"]) addEventListener(ev, () => { userScrolled = true; }, { passive: true });
  const onScroll = () => { if (!queued) { queued = true; requestAnimationFrame(update); } };

  // Frame-rate watch: while you scroll through the walk-through, time every screen refresh.
  // If this device keeps missing frames (under ~50 fps, or many long stalls), step down one
  // quality level: lighter images to decode and draw. Remembered for next visit.
  let scrollAt = 0, samples = [], lastT = 0;
  const watch = (t) => {
    if (off) return;
    if (lastT && !through && !document.hidden && t > settleUntil && t - scrollAt < 150) {
      samples.push(t - lastT);
      if (samples.length >= 60) {
        const s = samples.slice().sort((a, b) => a - b);
        const median = s[s.length >> 1], stalls = s.filter((d) => d > 34).length / s.length;
        samples = [];
        if ((median > 20 || stalls > 0.2) && tier < 2 && forcedTier < 0) {
          drop++;
          try { localStorage.setItem(DROP_KEY, JSON.stringify({ n: drop, t: Date.now() })); } catch (e) { /* fine */ }
          if (loadSet()) onScroll();
        }
      }
    }
    lastT = t;
    requestAnimationFrame(watch);
  };
  requestAnimationFrame(watch);

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
        meter.textContent = `${Math.round(frames / s)} fps · ${Math.round(paints / s)} new images/s · frame ${Math.floor(pos) + 1}/${N} · ${folder} ${W}×${H} · ${loaded}/${N} loaded`;
        frames = paints = 0; t0 = t;
      }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }
  addEventListener("scroll", onScroll, { passive: true });
  let resizeT;
  addEventListener("resize", () => {
    clearTimeout(resizeT);
    resizeT = setTimeout(() => { if (!off) { loadSet(); onScroll(); } }, 250);
  });

  // touch screens: "Swipe up to step inside"
  if (matchMedia("(hover: none) and (pointer: coarse)").matches) {
    const t = cine.querySelector(".cine__hint-text");
    if (t && t.dataset.touch) t.textContent = t.dataset.touch;
  }

  /* ---------- start ---------- */
  if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  if (!location.hash) {
    scrollTo(0, 0);
    waiting = true; holdScroll(true);
    setTimeout(openGate, WAIT_MAX);
  }
  loadSet();
  update();

  // the first screen of the website is placed (not animated) so the hand-off is just the blur
  document.addEventListener("DOMContentLoaded", () => {
    if (waiting) holdScroll(true);                       // the smooth scroller exists now: hold it too
    root.classList.add("instant");
    document.querySelectorAll(".hero [data-reveal], .hero [data-split]").forEach((el) => el.classList.add("is-in"));
    document.body.offsetHeight;
    setTimeout(() => root.classList.remove("instant"), 60);
    onScroll();
  });
})();
