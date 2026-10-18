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

  /* ---------- frames: full 1920×1080, loaded and decoded ahead of time ---------- */
  const N = 145;
  const src = (i) => `assets/cine/${mode}/${String(i).padStart(3, "0")}.webp?v=8`;
  const frames = new Array(N);
  const ready = new Uint8Array(N);
  let want = 0, drawn = -1;
  const load = (i) => {
    if (frames[i]) return Promise.resolve();
    const im = new Image(); frames[i] = im;
    im.src = src(i);
    return im.decode().then(() => { ready[i] = 1; if (Math.abs(i - want) < 4) paint(); }, () => {});
  };
  // first frame, then a coarse pass across the whole walk-through, then fill the gaps
  const order = [];
  for (const step of [16, 8, 4, 2, 1]) for (let i = 0; i < N; i += step) if (!order.includes(i)) order.push(i);

  /* ---------- canvas: drawn 1:1, scaled to the screen by CSS (object-fit: cover) ---------- */
  const canvas = cine.querySelector(".cine__canvas");
  canvas.width = 1920; canvas.height = 1080;
  const ctx = canvas.getContext("2d", { alpha: false });
  const nearest = (i) => {
    for (let o = 0; o < N; o++) {
      if (ready[i - o]) return i - o;
      if (ready[i + o]) return i + o;
    }
    return -1;
  };
  function paint() {
    const k = nearest(want);
    if (k < 0 || k === drawn) return;
    ctx.drawImage(frames[k], 0, 0, 1920, 1080);
    drawn = k;
  }

  (async () => {
    await load(0);
    cine.classList.add("is-ready");
    paint();
    for (let k = 1; k < order.length; k += 8) await Promise.all(order.slice(k, k + 8).map(load));
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
    want = Math.round(p * (N - 1));
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
