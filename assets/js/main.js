/* ==========================================================================
   Noma Living: interactions
   Edit CONFIG and ROOMS below to update contact details and prices.
   ========================================================================== */

const CONFIG = {
  whatsapp: "96100000000",          // international format, digits only (e.g. 9617XXXXXXX)
  phone: "+961 00 000 000",
  email: "hello@nomaliving.com",
  instagram: "https://instagram.com/",
  discounts: { month: 0, semester: 0.05, year: 0.10 },
  planLabel: { month: "/ month", semester: "/ month · 5-month semester", year: "/ month · 10-month year" },
};

const ROOMS = [
  {
    id: "twin", name: "Twin Studio", nums: "Studios 102 · 104 · 105", tag: "Best value",
    price: 450, unit: "per student",
    desc: "Two single beds, one good flatmate. Our most affordable way to live at Noma, ideal for sharing with a friend.",
    specs: [["i-ruler", "23–28 m²"], ["i-bed", "2 single beds"], ["i-users", "2 students"]],
    imgs: ["twin-mural", "twin-arches", "twin-skyline", "twin-detail", "kitchen-bed", "bath-wide"],
  },
  {
    id: "double", name: "Double Studio", nums: "Studio 106",
    price: 650, unit: "whole studio",
    desc: "A cosy studio that's all yours: a double bed, your own kitchenette and a quiet corner to study.",
    specs: [["i-ruler", "23 m²"], ["i-bed", "1 double bed"], ["i-users", "1 student"]],
    imgs: ["double-navy", "double-angle", "double-wide", "double-detail", "kitchen-corner", "bath-vanity"],
  },
  {
    id: "king", name: "King Studio", nums: "Studios 101 · 107",
    price: 720, unit: "whole studio",
    desc: "Our roomiest layout, with an extra-large bed and more space to spread out your notes (and your wardrobe).",
    specs: [["i-ruler", "25 m²"], ["i-bed", "Extra-large double"], ["i-users", "1 student"]],
    imgs: ["king-curtains", "king-sun", "king-front", "king-tv", "lounge-sofa", "bath-4"],
  },
];

const INCLUDED = ["Private kitchenette", "Private bathroom", "24/7 electricity", "Wi-Fi", "AC & heating", "Flat-screen TV", "Bed linen & towels", "Kitchenware", "Wardrobe storage", "Elevator access"];

const GALLERY = [
  ["twin-skyline", "studio", "Twin studio", "wide"],
  ["exterior-night", "common", "The building at night", "tall"],
  ["king-sun", "studio", "King studio"],
  ["kitchen-portrait", "kitchen", "Kitchenette", "tall"],
  ["lobby", "common", "Reception", "wide"],
  ["double-navy", "studio", "Double studio"],
  ["bath-vanity", "bath", "Private bathroom"],
  ["mural-noma", "common", "Studio with NOMA artwork", "wide"],
  ["twin-arches", "studio", "Twin studio"],
  ["bath-shower", "bath", "Walk-in shower", "tall"],
  ["keybox-wall", "common", "Self check-in lockboxes"],
  ["lounge-sofa", "studio", "Lounge corner"],
  ["king-angle", "studio", "King studio", "wide"],
  ["kitchen-corner", "kitchen", "Kitchenette"],
  ["hallway", "common", "First-floor hallway"],
  ["bath-wide", "bath", "Bathroom"],
  ["entrance", "common", "Entrance", "wide"],
  ["twin-detail", "studio", "Twin studio detail"],
  ["kitchen-table", "kitchen", "Kitchenette & table"],
  ["mural-stairs", "common", "Beirut-inspired murals"],
  ["exterior-day", "common", "Hamra street view", "tall"],
  ["bath-2", "bath", "Bathroom"],
];

const img = (n) => `assets/img/${n}.jpg`;
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const waLink = (text = "") => `https://wa.me/${CONFIG.whatsapp}${text ? `?text=${encodeURIComponent(text)}` : ""}`;
let plan = "month";

/* ---------- Smooth scroll ---------- */
let lenis = null;
if (window.Lenis && !reduceMotion) {
  lenis = new Lenis({ duration: 1.15, easing: (t) => 1 - Math.pow(1 - t, 4) });
  const raf = (t) => { lenis.raf(t); requestAnimationFrame(raf); };
  requestAnimationFrame(raf);
}
const scrollToEl = (el) => {
  if (!el) return;
  if (lenis) lenis.scrollTo(el, { offset: -80 });
  else el.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
};
const lockScroll = (on) => {
  document.documentElement.style.overflow = on ? "hidden" : "";
  if (lenis) on ? lenis.stop() : lenis.start();
};

/* ---------- Contact links ---------- */
$$("[data-wa]").forEach((a) => { a.href = waLink("Hi Noma! I have a question about your studios."); a.target = "_blank"; a.rel = "noopener"; });
$$("[data-phone]").forEach((a) => { a.href = `tel:${CONFIG.phone.replace(/\s/g, "")}`; a.textContent = CONFIG.phone; });
$$("[data-email]").forEach((a) => { a.href = `mailto:${CONFIG.email}`; a.textContent = CONFIG.email; });
$$("[data-insta]").forEach((a) => { a.href = CONFIG.instagram; a.target = "_blank"; a.rel = "noopener"; });
$$("[data-year]").forEach((el) => (el.textContent = new Date().getFullYear()));

/* ---------- Nav ---------- */
const nav = $(".nav");
const fab = $(".fab");
const mobileCta = $(".mobile-cta");
let lastY = 0;
// scroll measured from where the website starts (after the walk-through, if any)
const siteTop = () => (window.NomaIntro && window.NomaIntro.enabled ? window.NomaIntro.end() : 0);
const onScroll = () => {
  const y = window.scrollY - siteTop();
  nav.classList.toggle("is-scrolled", y > 20);
  if (!document.body.classList.contains("menu-open")) nav.classList.toggle("is-hidden", y > 400 && y > lastY);
  const past = y > window.innerHeight * 0.7;
  fab.classList.toggle("is-on", past);
  mobileCta.classList.toggle("is-on", past);
  lastY = y;
};
addEventListener("scroll", onScroll, { passive: true });
onScroll();

// highlight current section
const links = $$(".nav__links a");
const spy = new IntersectionObserver((entries) => {
  entries.forEach((e) => {
    if (!e.isIntersecting) return;
    links.forEach((l) => l.classList.toggle("is-active", l.getAttribute("href") === `#${e.target.id}`));
  });
}, { rootMargin: "-45% 0px -50% 0px" });
links.forEach((l) => { const s = $(l.getAttribute("href")); if (s) spy.observe(s); });

// mobile menu
const burger = $(".burger");
const menu = $("#menu");
const setMenu = (open) => {
  document.body.classList.toggle("menu-open", open);
  burger.setAttribute("aria-expanded", open);
  burger.setAttribute("aria-label", open ? "Close menu" : "Open menu");
  menu.setAttribute("aria-hidden", !open);
  lockScroll(open);
  if (open) nav.classList.remove("is-hidden");
};
burger.addEventListener("click", () => setMenu(!document.body.classList.contains("menu-open")));

// in-page anchors (+ optional form tab)
document.addEventListener("click", (e) => {
  const a = e.target.closest('a[href^="#"]');
  if (!a || a.hasAttribute("data-wa") || a.hasAttribute("data-phone") || a.hasAttribute("data-email") || a.hasAttribute("data-insta")) return;
  const id = a.getAttribute("href");
  e.preventDefault();
  if (a.dataset.tab) setFormTab(a.dataset.tab);
  if (document.body.classList.contains("menu-open")) setMenu(false);
  if (a.closest(".modal")) closeModal();
  if (id === "#top") { const t = siteTop(); lenis ? lenis.scrollTo(t) : scrollTo({ top: t, behavior: "smooth" }); return; }
  scrollToEl($(id));
});

/* ---------- Sliding pills (toggle + tabs) ---------- */
const movePill = (group) => {
  const pill = $(".toggle__pill, .tabs__pill", group);
  const btn = $('[aria-selected="true"]', group);
  if (!pill || !btn) return;
  pill.style.width = `${btn.offsetWidth}px`;
  pill.style.transform = `translateX(${btn.offsetLeft - 5}px)`;
};
const pillGroups = $$(".toggle, .tabs");
const refreshPills = () => pillGroups.forEach(movePill);
addEventListener("resize", refreshPills);
document.fonts && document.fonts.ready.then(refreshPills);

/* ---------- Rooms ---------- */
const roomsEl = $("#rooms");
const fmt = (n) => `$${Math.round(n).toLocaleString("en-US")}`;
const priceFor = (r) => r.price * (1 - CONFIG.discounts[plan]);

roomsEl.innerHTML = ROOMS.map((r, i) => `
  <article class="room" data-reveal style="--d:${i * 0.1}s" data-room="${r.id}">
    <div class="room__media">
      <span class="room__tag">${r.nums.split(" ")[0] === "Studio" ? "1 studio" : `${r.nums.split("·").length} studios`}</span>
      ${r.tag ? `<span class="room__tag room__tag--hot">${r.tag}</span>` : ""}
      <div class="room__slides">${r.imgs.slice(0, 4).map((n, k) => `<img src="${img(n)}" alt="${r.name} photo ${k + 1}" loading="lazy" class="${k ? "" : "is-on"}">`).join("")}</div>
      <div class="room__dots">${r.imgs.slice(0, 4).map((_, k) => `<i class="${k ? "" : "is-on"}"></i>`).join("")}</div>
      <div class="room__arrows">
        <button type="button" data-dir="-1" aria-label="Previous photo"><svg class="ico"><use href="#i-chev"/></svg></button>
        <button type="button" data-dir="1" aria-label="Next photo"><svg class="ico"><use href="#i-chev"/></svg></button>
      </div>
    </div>
    <div class="room__body">
      <div class="room__top"><h3>${r.name}</h3><span class="room__nums">${r.nums}</span></div>
      <p class="room__desc">${r.desc}</p>
      <ul class="specs">${r.specs.map(([ic, t]) => `<li><svg class="ico"><use href="#${ic}"/></svg>${t}</li>`).join("")}</ul>
      <div class="room__foot">
        <div class="price"><small>from</small><strong data-price>${fmt(priceFor(r))}</strong><span>${r.unit} ${CONFIG.planLabel[plan]}</span></div>
        <div class="room__btns">
          <button class="btn btn--ghost btn--sm" type="button" data-open="${r.id}">Details</button>
        </div>
      </div>
    </div>
  </article>`).join("");

// card sliders
$$(".room").forEach((card) => {
  const slides = $$(".room__slides img", card);
  const dots = $$(".room__dots i", card);
  let idx = 0;
  const go = (n) => {
    idx = (n + slides.length) % slides.length;
    slides.forEach((s, k) => s.classList.toggle("is-on", k === idx));
    dots.forEach((d, k) => d.classList.toggle("is-on", k === idx));
  };
  $$(".room__arrows button", card).forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); go(idx + +b.dataset.dir); }));
  let sx = 0;
  const media = $(".room__media", card);
  media.addEventListener("touchstart", (e) => (sx = e.touches[0].clientX), { passive: true });
  media.addEventListener("touchend", (e) => { const dx = e.changedTouches[0].clientX - sx; if (Math.abs(dx) > 40) go(idx + (dx < 0 ? 1 : -1)); });
  media.addEventListener("click", () => openModal(card.dataset.room));
  media.style.cursor = "pointer";
});

// stay-length toggle
const toggle = $(".toggle");
$$("button", toggle).forEach((b) => b.addEventListener("click", () => {
  $$("button", toggle).forEach((x) => x.setAttribute("aria-selected", x === b));
  movePill(toggle);
  plan = b.dataset.plan;
  $$(".room").forEach((card) => {
    const r = ROOMS.find((x) => x.id === card.dataset.room);
    const el = $("[data-price]", card);
    el.classList.remove("is-ticking"); void el.offsetWidth; el.classList.add("is-ticking");
    el.textContent = fmt(priceFor(r));
    el.nextElementSibling.textContent = `${r.unit} ${CONFIG.planLabel[plan]}`;
  });
}));

/* ---------- Room modal ---------- */
const modal = $("#roomModal");
let lastFocus = null;
const openModal = (id) => {
  const r = ROOMS.find((x) => x.id === id);
  if (!r) return;
  lastFocus = document.activeElement;
  $("#mTitle").textContent = r.name;
  $("#mRooms").textContent = r.nums;
  $("#mDesc").textContent = r.desc;
  $("#mSpecs").innerHTML = r.specs.map(([ic, t]) => `<li><svg class="ico"><use href="#${ic}"/></svg>${t}</li>`).join("");
  $("#mList").innerHTML = INCLUDED.map((t) => `<li><svg class="ico"><use href="#i-check"/></svg>${t}</li>`).join("");
  $("#mPrice").textContent = fmt(priceFor(r));
  $("#mUnit").textContent = `${r.unit} ${CONFIG.planLabel[plan]}`;
  $("#mApply").dataset.room = r.id;
  const main = $("#mImg");
  main.src = img(r.imgs[0]); main.alt = `${r.name}`;
  $("#mThumbs").innerHTML = r.imgs.slice(0, 5).map((n, k) => `<button type="button" class="${k ? "" : "is-on"}" data-src="${img(n)}" aria-label="Show photo ${k + 1}"><img src="${img(n)}" alt=""></button>`).join("");
  $$("#mThumbs button").forEach((b) => b.addEventListener("click", () => {
    $$("#mThumbs button").forEach((x) => x.classList.toggle("is-on", x === b));
    main.style.opacity = 0;
    setTimeout(() => { main.src = b.dataset.src; main.style.opacity = 1; }, 180);
  }));
  modal.classList.add("is-open");
  modal.setAttribute("aria-hidden", "false");
  lockScroll(true);
  setTimeout(() => $(".modal__close", modal).focus(), 50);
};
const closeModal = () => {
  if (!modal.classList.contains("is-open")) return;
  modal.classList.remove("is-open");
  modal.setAttribute("aria-hidden", "true");
  lockScroll(false);
  lastFocus && lastFocus.focus({ preventScroll: true });
};
roomsEl.addEventListener("click", (e) => { const b = e.target.closest("[data-open]"); if (b) openModal(b.dataset.open); });
$$("[data-close]", modal).forEach((el) => el.addEventListener("click", closeModal));
$("#mApply").addEventListener("click", (e) => prefill({ studio: e.currentTarget.dataset.room, plan }));

/* ---------- Gallery + lightbox ---------- */
const grid = $("#grid");
grid.innerHTML = GALLERY.map(([n, cat, cap, size], i) => `
  <button class="tile ${size ? `tile--${size}` : ""}" data-cat="${cat}" data-cap="${cap}" data-i="${i}" data-reveal style="--d:${(i % 4) * 0.06}s" aria-label="Open photo: ${cap}">
    <img src="${img(n)}" alt="${cap}" loading="lazy">
  </button>`).join("");

$$(".chip").forEach((chip) => chip.addEventListener("click", () => {
  $$(".chip").forEach((c) => c.classList.toggle("is-active", c === chip));
  const f = chip.dataset.filter;
  const tiles = $$(".tile", grid);
  tiles.forEach((t) => t.classList.add("is-out"));
  setTimeout(() => {
    tiles.forEach((t) => {
      const show = f === "all" || t.dataset.cat === f;
      t.classList.toggle("is-gone", !show);
    });
    requestAnimationFrame(() => requestAnimationFrame(() => tiles.forEach((t) => t.classList.remove("is-out"))));
  }, 300);
}));

const lb = $("#lightbox");
const lbImg = $("#lbImg");
let lbList = [], lbIdx = 0;
const lbShow = (i) => {
  lbIdx = (i + lbList.length) % lbList.length;
  const [n, , cap] = GALLERY[lbList[lbIdx]];
  lbImg.style.opacity = 0;
  setTimeout(() => { lbImg.src = img(n); lbImg.alt = cap; $("#lbCap").textContent = `${cap} · ${lbIdx + 1} / ${lbList.length}`; lbImg.style.opacity = 1; }, 150);
};
grid.addEventListener("click", (e) => {
  const t = e.target.closest(".tile");
  if (!t) return;
  lbList = $$(".tile:not(.is-gone)", grid).map((x) => +x.dataset.i);
  lb.classList.add("is-open");
  lb.setAttribute("aria-hidden", "false");
  lockScroll(true);
  lbShow(lbList.indexOf(+t.dataset.i));
  $(".lightbox__close").focus();
});
const lbClose = () => { lb.classList.remove("is-open"); lb.setAttribute("aria-hidden", "true"); lockScroll(false); };
lb.addEventListener("click", (e) => {
  const b = e.target.closest("[data-lb]");
  if (b) { b.dataset.lb === "close" ? lbClose() : lbShow(lbIdx + (b.dataset.lb === "next" ? 1 : -1)); }
  else if (e.target === lb) lbClose();
});
let lsx = 0;
lb.addEventListener("touchstart", (e) => (lsx = e.touches[0].clientX), { passive: true });
lb.addEventListener("touchend", (e) => { const dx = e.changedTouches[0].clientX - lsx; if (Math.abs(dx) > 50) lbShow(lbIdx + (dx < 0 ? 1 : -1)); });

document.addEventListener("keydown", (e) => {
  if (lb.classList.contains("is-open")) {
    if (e.key === "Escape") lbClose();
    if (e.key === "ArrowRight") lbShow(lbIdx + 1);
    if (e.key === "ArrowLeft") lbShow(lbIdx - 1);
  } else if (e.key === "Escape") {
    closeModal();
    if (document.body.classList.contains("menu-open")) setMenu(false);
  }
});

/* ---------- Form ---------- */
const form = $("#leadForm");
const done = $(".form-done");
const tabs = $(".tabs");
function setFormTab(type) {
  $$("button", tabs).forEach((b) => b.setAttribute("aria-selected", b.dataset.form === type));
  movePill(tabs);
  form.elements.type.value = type;
  $(".only-tour", form).hidden = type !== "tour";
  $(".only-apply", form).hidden = type !== "apply";
  $(".submit-label", form).textContent = type === "tour" ? "Request my tour" : "Send my application";
}
$$("button", tabs).forEach((b) => b.addEventListener("click", () => setFormTab(b.dataset.form)));

const PLAN_NAMES = { month: "Monthly", semester: "Semester", year: "Full academic year" };
function prefill({ studio, term, who, plan: p }) {
  setFormTab("apply");
  if (studio) form.elements.studio.value = studio;
  if (term) form.elements.term.value = term;
  if (who) form.elements.who.value = who;
  if (p) form.elements.plan.value = PLAN_NAMES[p];
}

// tomorrow as the earliest tour date
const tmr = new Date(Date.now() + 864e5).toISOString().slice(0, 10);
form.elements.date.min = tmr;

form.addEventListener("submit", (e) => {
  e.preventDefault();
  let ok = true;
  ["name", "phone"].forEach((n) => {
    const field = form.elements[n].closest(".field");
    const bad = !form.elements[n].value.trim();
    field.classList.toggle("is-error", bad);
    if (bad) ok = false;
  });
  if (!ok) { toast("Please add your name and phone number."); form.querySelector(".is-error input").focus(); return; }

  const d = Object.fromEntries(new FormData(form));
  const studioName = d.studio === "any" ? "Not sure yet" : ROOMS.find((r) => r.id === d.studio).name;
  const lines = d.type === "tour"
    ? ["Hi Noma! I'd like to book a tour.", `Name: ${d.name}`, `Phone: ${d.phone}`, d.email && `Email: ${d.email}`, `University: ${d.uni}`, `Studio: ${studioName}`, d.date && `Preferred date: ${d.date}`, `Tour: ${d.tourType}`]
    : ["Hi Noma! I'd like to apply for a studio.", `Name: ${d.name}`, `Phone: ${d.phone}`, d.email && `Email: ${d.email}`, `University: ${d.uni}`, `Studio: ${studioName}`, `Move-in: ${d.term}`, `Stay: ${d.plan}`, `Moving in: ${d.who}`];
  if (d.msg) lines.push(`Note: ${d.msg}`);
  window.open(waLink(lines.filter(Boolean).join("\n")), "_blank", "noopener");

  form.hidden = true;
  tabs.hidden = true;
  done.hidden = false;
});
form.addEventListener("input", (e) => e.target.closest(".field")?.classList.remove("is-error"));
$("[data-reset]").addEventListener("click", () => {
  form.reset(); form.hidden = false; tabs.hidden = false; done.hidden = true;
  setFormTab("tour");
});

// hero finder → prefilled application
$("#finder").addEventListener("submit", (e) => {
  e.preventDefault();
  const f = e.currentTarget;
  prefill({ studio: f.elements.studio.value, term: f.elements.term.value, who: f.elements.who.value });
  scrollToEl($("#apply"));
  toast("We've filled in your details below ✦");
});

const toastEl = $(".toast");
let toastT;
function toast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.add("is-on");
  clearTimeout(toastT);
  toastT = setTimeout(() => toastEl.classList.remove("is-on"), 2800);
}

/* ---------- FAQ: animated open/close ---------- */
$$(".accordion details").forEach((det) => {
  const sum = $("summary", det);
  const body = $("div", det);
  sum.addEventListener("click", (e) => {
    if (reduceMotion) return;
    e.preventDefault();
    if (det.dataset.busy) return;
    det.dataset.busy = 1;
    if (!det.open) {
      // close any other open one
      $$(".accordion details[open]").forEach((o) => o !== det && $("summary", o).click());
      det.open = true;
      const h = body.scrollHeight;
      body.animate([{ height: "0px", opacity: 0 }, { height: `${h}px`, opacity: 1 }], { duration: 500, easing: "cubic-bezier(.22,1,.36,1)" })
        .onfinish = () => delete det.dataset.busy;
    } else {
      const h = body.scrollHeight;
      body.animate([{ height: `${h}px`, opacity: 1 }, { height: "0px", opacity: 0 }], { duration: 380, easing: "cubic-bezier(.65,0,.35,1)" })
        .onfinish = () => { det.open = false; delete det.dataset.busy; };
    }
  });
});

/* ---------- Reveal on scroll ---------- */
const countUp = (el) => {
  const end = +el.dataset.count, suffix = el.dataset.suffix || "";
  if (reduceMotion) { el.textContent = end + suffix; return; }
  const t0 = performance.now(), dur = 1400;
  const step = (t) => {
    const p = Math.min((t - t0) / dur, 1);
    el.textContent = Math.round(end * (1 - Math.pow(1 - p, 3))) + suffix;
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
};

const io = new IntersectionObserver((entries) => {
  entries.forEach((e) => {
    if (!e.isIntersecting) return;
    e.target.classList.add("is-in");
    $$("[data-count]", e.target).forEach(countUp);
    if (e.target.matches("[data-count]")) countUp(e.target);
    io.unobserve(e.target);
  });
}, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
// Clip-path reveals start fully clipped, and IntersectionObserver ignores a
// target clipped to nothing, so watch their parent and reveal the children.
const clipIo = new IntersectionObserver((entries) => {
  entries.forEach((e) => {
    if (!e.isIntersecting) return;
    e.target._clipKids.forEach((k) => k.classList.add("is-in"));
    clipIo.unobserve(e.target);
  });
}, { threshold: 0.05, rootMargin: "0px 0px -6% 0px" });
const observeAll = () => {
  $$("[data-reveal]:not(.is-in), [data-split]:not(.is-in), .steps__list:not(.is-in)").forEach((el) => {
    if (!/^(clip|arch)$/.test(el.dataset.reveal)) return io.observe(el);
    const p = el.parentElement;
    (p._clipKids ||= []).push(el);
    clipIo.observe(p);
  });
  revealPassed();
};
// anything already scrolled past (fast jumps, reload mid-page) shows immediately
const revealPassed = () => $$("[data-reveal]:not(.is-in), [data-split]:not(.is-in)").forEach((el) => {
  if (el.getBoundingClientRect().bottom < 0) {
    el.classList.add("is-in");
    $$("[data-count]", el).forEach(countUp);
  }
});
let passT;
addEventListener("scroll", () => { clearTimeout(passT); passT = setTimeout(revealPassed, 150); }, { passive: true });

observeAll();
refreshPills();

/* ---------- Parallax ---------- */
const pEls = $$("[data-parallax]");
const pImgs = $$("[data-parallax-img]");
let ticking = false;
const parallax = () => {
  const vh = innerHeight;
  pEls.forEach((el) => {
    const r = el.getBoundingClientRect();
    const c = r.top + r.height / 2 - vh / 2;
    el.style.translate = `0 ${c * +el.dataset.parallax}px`;
  });
  pImgs.forEach((el) => {
    const box = el.parentElement.getBoundingClientRect();
    if (box.bottom < 0 || box.top > vh) return;
    const p = (box.top + box.height / 2 - vh / 2) / vh; // -1 .. 1
    el.style.translate = `0 ${p * -9}%`;
  });
  ticking = false;
};
if (!reduceMotion) {
  addEventListener("scroll", () => { if (!ticking) { ticking = true; requestAnimationFrame(parallax); } }, { passive: true });
  parallax();
}
