/* ==========================================================================
   Noma Living: cinematic intro
   Night exterior → arched doors → doors swing inward → dolly into the lobby.
   Exposes window.NomaIntro = { playing, done } so main.js can wait for it.
   ========================================================================== */
(() => {
  const intro = document.getElementById("intro");
  const params = new URLSearchParams(location.search);
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  // skip for reduced motion, deep links (#apply…) and ?nointro while developing
  const skip = !intro || reduce || params.has("nointro") || (location.hash && location.hash !== "#top");

  let finish;
  const done = new Promise((r) => (finish = r));
  window.NomaIntro = { playing: !skip, done };

  if (skip) { intro?.remove(); finish(); return; }

  const root = document.documentElement;
  root.classList.add("intro-on");
  if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  scrollTo(0, 0);

  const ext = intro.querySelector(".intro__ext img");
  const lobby = intro.querySelector(".intro__lobby img");
  const cam = intro.querySelector(".intro__cam");
  const doorway = intro.querySelector(".intro__doorway");
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const timers = [];
  let ended = false;

  const loaded = (img) => (img.complete && img.naturalWidth ? Promise.resolve() : new Promise((r) => { img.onload = r; img.onerror = r; }));

  // aim the exterior push-in at the real front door of the building
  const aimExterior = () => {
    const iw = ext.naturalWidth || 1362, ih = ext.naturalHeight || 2047;
    const vw = innerWidth, vh = innerHeight;
    const s = Math.max(vw / iw, vh / ih);
    const posY = 0.62; // keep in sync with object-position in CSS
    const ox = (vw - iw * s) * 0.5, oy = (vh - ih * s) * posY;
    const door = { x: 0.225, y: 0.64 }; // the glass entrance, as a fraction of the photo
    ext.style.transformOrigin = `${ox + door.x * iw * s}px ${oy + door.y * ih * s}px`;
  };

  // how far the camera has to travel for the doorway to swallow the screen
  const aimDolly = () => {
    const r = doorway.getBoundingClientRect();
    const scale = Math.max(innerWidth / r.width, innerHeight / (r.height * 0.62)) * 1.35;
    cam.style.transformOrigin = `${r.left + r.width / 2}px ${r.top + r.height * 0.58}px`;
    cam.style.setProperty("--dolly", scale.toFixed(2));
  };

  const end = (fast) => {
    if (ended) return;
    ended = true;
    timers.forEach(clearTimeout);
    intro.classList.add("is-out");
    if (fast) intro.classList.add("is-fast");
    root.classList.remove("intro-on");
    finish();
    setTimeout(() => intro.remove(), fast ? 700 : 1400);
  };

  intro.querySelector(".intro__skip").addEventListener("click", () => end(true));
  addEventListener("keydown", (e) => { if (e.key === "Escape") end(true); });

  const at = (ms, fn) => timers.push(setTimeout(() => !ended && fn(), ms));
  const state = (c) => intro.classList.add(c);

  (async () => {
    // wait for the two hero photos (max ~5s), but show the logo for at least a beat
    await Promise.race([Promise.all([loaded(ext), loaded(lobby), sleep(900)]), sleep(5000)]);
    if (ended) return;
    aimExterior();
    addEventListener("resize", aimExterior);

    state("is-ready");                 // logo out, letterbox in
    at(250, () => state("is-ext"));    // night exterior, camera walks to the entrance
    at(3100, () => { aimDolly(); state("is-door"); });  // dissolve to the doors
    at(4500, () => state("is-open"));  // doors swing inward, light pours out
    at(5150, () => { aimDolly(); state("is-enter"); }); // dolly through the doorway
    at(6900, () => state("is-welcome"));
    at(8300, () => end(false));
  })();
})();
