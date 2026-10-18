/* ==========================================================================
   Noma Living: cinematic intro
   Plays the Blender walk-through (street → doors open → lobby), lands on
   "Welcome home." and hands over to the site.
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

  const video = intro.querySelector(".intro__video");
  const timers = [];
  let ended = false;
  const state = (c) => intro.classList.add(c);
  const at = (ms, fn) => timers.push(setTimeout(() => !ended && fn(), ms));

  const end = (fast) => {
    if (ended) return;
    ended = true;
    timers.forEach(clearTimeout);
    intro.classList.add("is-out");
    if (fast) intro.classList.add("is-fast");
    root.classList.remove("intro-on");
    finish();
    setTimeout(() => { video.pause(); intro.remove(); }, fast ? 700 : 1500);
  };

  intro.querySelector(".intro__skip").addEventListener("click", () => end(true));
  addEventListener("keydown", (e) => { if (e.key === "Escape") end(true); });

  // the video can't load or autoplay: don't hold the site hostage
  const bail = setTimeout(() => end(true), 7000);

  const start = () => {
    if (ended || intro.classList.contains("is-ready")) return;
    clearTimeout(bail);
    const p = video.play();
    if (p && p.catch) p.catch(() => end(true));
    state("is-ready");
    at(400, () => state("is-place"));
    at(2600, () => intro.classList.remove("is-place"));
  };

  video.addEventListener("canplaythrough", start, { once: true });
  // some browsers never fire canplaythrough on slow links; start once enough is buffered
  video.addEventListener("loadeddata", () => setTimeout(start, 1500), { once: true });
  video.addEventListener("error", () => end(true), { once: true });

  // land on the lobby: welcome card a little before the last frame, then hand over
  video.addEventListener("timeupdate", () => {
    if (!intro.classList.contains("is-welcome") && video.duration && video.currentTime > video.duration - 1.3) {
      state("is-welcome");
    }
  });
  video.addEventListener("ended", () => at(1300, () => end(false)), { once: true });
})();
