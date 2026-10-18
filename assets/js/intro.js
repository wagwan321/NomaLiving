/* ==========================================================================
   Noma Living: cinematic intro
   Plays the Blender walk-through (street → door opens → lobby). On the last
   frame the whole picture glides into the hero's arch and dissolves into the
   page (on narrow screens it lifts away like a curtain instead).
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
  root.classList.add("intro-on");
  if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  scrollTo(0, 0);

  const frame = intro.querySelector(".intro__frame");
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
    intro.classList.add("is-out", "is-fast");
    finish(650);
  };

  // The hand-off: last frame → hero arch
  const land = () => {
    if (ended || landing) return;
    landing = true;
    timers.forEach(clearTimeout);
    const arch = document.querySelector(".hero__arch");
    const r = arch && arch.getBoundingClientRect();
    const fits = r && r.width > 0 && r.top >= 0 && r.bottom <= innerHeight + 2 && innerWidth > 900;

    // show the hero photo underneath right away, without its own reveal
    if (arch) {
      const img = arch.querySelector("img");
      arch.style.transition = "none"; if (img) img.style.transition = "none";
      arch.classList.add("is-in");
      requestAnimationFrame(() => requestAnimationFrame(() => { arch.style.transition = ""; if (img) img.style.transition = ""; }));
    }

    state("is-landing");
    resolveReveal();                       // headline, nav and badges animate in around it
    if (fits) {
      // pin the frame where it is, then let CSS glide it into the arch
      Object.assign(frame.style, { top: "0px", left: "0px", width: innerWidth + "px", height: innerHeight + "px" });
      frame.getBoundingClientRect();
      state("is-morph");
      Object.assign(frame.style, {
        top: r.top + "px", left: r.left + "px", width: r.width + "px", height: r.height + "px",
        borderRadius: `${r.width / 2}px ${r.width / 2}px 0 0`,
      });
      setTimeout(() => state("is-dissolve"), 1500);   // landed: melt into the real photo
      setTimeout(() => finish(0), 2500);
    } else {
      state("is-curtain");
      setTimeout(() => finish(0), 1500);
    }
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
