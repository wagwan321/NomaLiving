/* ==========================================================================
   Noma Living: scroll walk-through
   Scrolling scrubs a Blender-rendered image sequence: the street in Hamra,
   the door opening, reception. Day or night is chosen from the sun's real
   position over Beirut (so it follows Lebanese time, whatever the visitor's
   clock says). When the walk-through ends the screen blurs into the page;
   scrolling back up walks you back out.
   Exposes window.NomaIntro = { enabled, end() }: end() is the scroll position
   where the website starts.
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

  /* ---------- frames ---------- */
  const N = 145;
  const size = Math.min(innerWidth, innerHeight * 16 / 9) <= 960 ? "sm" : "lg";
  const src = (i) => `assets/cine/${mode}/${size}/${String(i).padStart(3, "0")}.webp?v=7`;
  const frames = new Array(N);
  const ready = new Array(N).fill(false);
  const load = (i) => new Promise((res) => {
    if (frames[i]) return res();
    const im = new Image(); im.decoding = "async";
    im.onload = () => { ready[i] = true; res(); if (Math.abs(i - Math.round(shown)) < 3) need = true; };
    im.onerror = res;
    im.src = src(i); frames[i] = im;
  });
  // first frame, then a coarse pass across the whole walk-through, then fill the gaps
  const order = [0];
  for (const step of [16, 8, 4, 2, 1]) for (let i = 0; i < N; i += step) if (!order.includes(i)) order.push(i);
  (async () => {
    await load(0);
    cine.classList.add("is-ready");
    need = true;
    for (let k = 1; k < order.length; k += 6) await Promise.all(order.slice(k, k + 6).map(load));
  })();

  /* ---------- canvas ---------- */
  const canvas = cine.querySelector(".cine__canvas");
  const ctx = canvas.getContext("2d");
  // soft backdrop (blurred by CSS) for portrait screens, where the frame doesn't fill the height at first
  const bg = cine.querySelector(".cine__bg");
  const bgx = bg.getContext("2d");
  const fit = () => {
    const dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.round(innerWidth * dpr); canvas.height = Math.round(innerHeight * dpr);
    bg.width = Math.round(innerWidth / 3); bg.height = Math.round(innerHeight / 3);
    need = true;
  };
  const nearest = (i) => {
    for (let o = 0; o < N; o++) {
      if (ready[i - o]) return i - o;
      if (ready[i + o]) return i + o;
    }
    return -1;
  };
  const draw = (i) => {
    const k = nearest(i); if (k < 0) return;
    const im = frames[k], iw = im.naturalWidth, ih = im.naturalHeight;
    const cw = canvas.width, ch = canvas.height;
    const cover = Math.max(cw / iw, ch / ih);
    let s = cover;
    if (cw < ch) {
      // portrait: show the whole street (sign included) first, then fill the screen once inside
      const t = smooth(0.32, 0.58, i / (N - 1));
      const fitW = cw / (iw * 0.78);
      s = fitW + (cover - fitW) * t;
      const bs = Math.max(bg.width / iw, bg.height / ih);
      bgx.drawImage(im, (bg.width - iw * bs) / 2, (bg.height - ih * bs) / 2, iw * bs, ih * bs);
    }
    const w = iw * s, h = ih * s;
    if (s < cover) ctx.clearRect(0, 0, cw, ch);
    ctx.drawImage(im, (cw - w) / 2, (ch - h) * 0.46, w, h);
  };

  /* ---------- scroll → frame ---------- */
  // the website starts one screen before the end of the spacer (main is pulled up by 100vh)
  const end = () => Math.max(1, spacer.offsetHeight - innerHeight);
  window.NomaIntro = { enabled: true, end };
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a)); return t * t * (3 - 2 * t); };
  let shown = 0, need = true, through = false, lastP = -1;

  const set = (name, v) => cine.style.setProperty(name, v.toFixed(4));
  const frameLoop = () => {
    const p = clamp(scrollY / end());
    const target = p * (N - 1);
    shown += (target - shown) * 0.35;
    if (Math.abs(target - shown) < 0.02) shown = target;
    const i = Math.round(shown);
    if (need || i !== draw.last) { draw(i); draw.last = i; need = false; }

    if (p !== lastP) {
      lastP = p;
      set("--hint", 1 - smooth(0.0, 0.035, p));
      set("--place", 1 - smooth(0.04, 0.11, p));
      set("--welcome", smooth(0.86, 0.97, p));
      set("--bars", 1 - smooth(0.9, 1, p));
      set("--progress", p);
      // nearly there: the page waits blurred underneath
      root.classList.toggle("page-blur", p > 0.8 && !through);
    }
    // the hand-off: past the last frame the screen blurs into the page; back up, it returns
    if (!through && p >= 0.999) {
      through = true;
      cine.classList.add("is-through");
      root.classList.remove("cine-on", "page-blur");
    } else if (through && p < 0.985) {
      through = false;
      cine.classList.remove("is-through");
      root.classList.add("cine-on", "page-blur");
    }
    requestAnimationFrame(frameLoop);
  };

  /* ---------- start ---------- */
  if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  if (!location.hash) scrollTo(0, 0);
  fit(); addEventListener("resize", fit);
  requestAnimationFrame(frameLoop);

  cine.querySelector(".cine__skip").addEventListener("click", () => {
    const y = end();
    if (typeof lenis !== "undefined" && lenis) lenis.scrollTo(y, { duration: 1.2 });
    else scrollTo({ top: y, behavior: "smooth" });
  });

  // the first screen of the website is placed (not animated) so the hand-off is just the blur
  document.addEventListener("DOMContentLoaded", () => {
    root.classList.add("instant");
    document.querySelectorAll(".hero [data-reveal], .hero [data-split]").forEach((el) => el.classList.add("is-in"));
    document.body.offsetHeight;
    setTimeout(() => root.classList.remove("instant"), 60);
  });
})();
