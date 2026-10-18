/* ==========================================================================
   Noma Living: cinematic intro
   Plays the Blender walk-through (street → door opens → lobby), lands on
   "Welcome home." and softly dissolves into the page.
   Exposes window.NomaIntro = { playing, reveal, done }:
     reveal → the page should start its entrance animations
     done   → the intro is gone, scrolling can resume
   ========================================================================== */
(() => {
  const intro = document.getElementById("intro");
  const params = new URLSearchParams(location.search);
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  // skip for reduced motion, deep links (#apply…) and ?nointro while developing
  const skip = !intro || reduce || params.has("nointro") || (location.hash && location.hash !== "#top");

  let resolveReveal, resolveDone;
  const reveal = new Promise((r) => (resolveReveal = r));
  const done = new Promise((r) => (resolveDone = r));
  window.NomaIntro = { playing: !skip, reveal, done };

  if (skip) { intro?.remove(); resolveReveal(); resolveDone(); return; }

  const root = document.documentElement;
  root.classList.add("intro-on", "page-blur");
  if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  scrollTo(0, 0);

  const video = intro.querySelector(".intro__video");
  const timers = [];
  let ended = false, landing = false;
  const state = (c) => intro.classList.add(c);
  const at = (ms, fn) => timers.push(setTimeout(() => !ended && fn(), ms));

  const finish = (delay) => {
    ended = true;
    timers.forEach(clearTimeout);
    resolveReveal();
    setTimeout(() => {
      root.classList.remove("intro-on");
      video.pause();
      intro.remove();
      resolveDone();
    }, delay);
  };

  // Skip / failure: a quick fade, no choreography
  const bail = () => {
    if (ended || landing) return;
    root.classList.remove("page-blur");
    intro.classList.add("is-out", "is-fast");
    finish(650);
  };

  // Everything in the first screen is shown in place right away (no piece-by-piece
  // entrance), so the only motion at hand-off is the blur.
  const settleHero = () => {
    root.classList.add("instant");
    document.querySelectorAll(".hero [data-reveal], .hero [data-split]").forEach((el) => el.classList.add("is-in"));
    document.body.offsetHeight;            // apply without transitions
    setTimeout(() => root.classList.remove("instant"), 60);
  };

  // The hand-off: the whole screen blurs out of "Welcome home." while the page
  // underneath, already in place, comes into focus
  const land = () => {
    if (ended || landing) return;
    landing = true;
    timers.forEach(clearTimeout);
    settleHero();
    resolveReveal();
    setTimeout(() => {
      state("is-landing");
      root.classList.remove("page-blur");
    }, 30);
    setTimeout(() => finish(0), 1700);
  };

  intro.querySelector(".intro__skip").addEventListener("click", bail);
  addEventListener("keydown", (e) => { if (e.key === "Escape") bail(); });

  // the video can't load or autoplay: don't hold the site hostage
  const stall = setTimeout(bail, 7000);

  const start = () => {
    if (ended || intro.classList.contains("is-ready")) return;
    clearTimeout(stall);
    const p = video.play();
    if (p && p.catch) p.catch(bail);
    state("is-ready");
    at(500, () => state("is-place"));
    at(3000, () => intro.classList.remove("is-place"));
  };

  video.addEventListener("canplaythrough", start, { once: true });
  // some browsers never fire canplaythrough on slow links; start once enough is buffered
  video.addEventListener("loadeddata", () => setTimeout(start, 1500), { once: true });
  video.addEventListener("error", bail, { once: true });

  // as the camera settles on reception: welcome card, then the hand-off
  video.addEventListener("timeupdate", () => {
    if (!intro.classList.contains("is-welcome") && video.duration && video.currentTime > video.duration - 1.9) state("is-welcome");
  });
  video.addEventListener("ended", () => at(700, land), { once: true });
})();
