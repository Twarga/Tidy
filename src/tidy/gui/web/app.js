/* Tidy desktop UI v3 — multi-page pixel app.
   Pages slide in/out; the Clock page + drawer host a clickable analog clock
   (hour/minute hands, drag or tap, synced digital readout).
   Talks to the Python Api via pywebview (Promise-based bridge). */
"use strict";

// pywebview injects `window.pywebview` shortly after page scripts on GTK,
// so the API is resolved lazily (polled) rather than captured at boot.
function apiReady() {
  return window.pywebview && window.pywebview.api;
}
async function getApi() {
  for (let i = 0; i < 200 && !apiReady(); i++) {
    await new Promise((r) => setTimeout(r, 100));
  }
  return apiReady();
}

const THEME_SWATCH = {
  neon: "#ff4fd8",
  crt: "#7dff8a",
  gameboy: "#9bbc0f",
  watermelon: "#2fb25a",
  paper: "#c1440e",
};
const PAGES = ["overview", "repos", "clock", "activity", "settings"];
const LVL_RANK = { ERROR: 0, WARN: 1, INFO: 2 };

const state = {
  page: "overview",
  repos: [],
  logs: [],
  settings: null,
  theme: "neon",
  clockRepo: null,
  clockH: 18,
  clockM: 0,
  clockMode: "H",
  clockBusy: false,
};

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}
function pad2(n) {
  return String(n).padStart(2, "0");
}
function hm(h, m) {
  return `${pad2(h)}:${pad2(m)}`;
}

/* ------------------------------ chrome: titlebar / statusbar / toast ---------------- */

let toastTimer = null;
function toast(msg, kind) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = "on" + (kind === "bad" ? " bad" : kind === "good" ? " good" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.className = ""), 2600);
}

let busyDepth = 0;
function setBusy(on) {
  busyDepth = Math.max(0, busyDepth + (on ? 1 : -1));
  document.body.classList.toggle("busy", busyDepth > 0);
}

function statusBar(msg, repo) {
  document.getElementById("sRepo").textContent = repo || "tidy";
  document.getElementById("sMsg").textContent = msg || "";
}

function tickClock() {
  const d = new Date();
  document.getElementById("tTime").textContent = `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}

/* ------------------------------ routing: pages slide in/out ---------------- */

function showPage(name) {
  if (!PAGES.includes(name)) name = "overview";
  state.page = name;
  document.querySelectorAll(".page").forEach((p) => p.classList.toggle("on", p.id === `p-${name}`));
  document.querySelectorAll(".nav-item").forEach((n) =>
    n.classList.toggle("active", n.dataset.page === name)
  );
  renderPage(name);
}

function renderPage(name) {
  const el = document.getElementById(`p-${name}`);
  if (!el) return;
  const r = {
    overview: renderOverview,
    repos: renderRepos,
    clock: renderClockPage,
    activity: renderActivity,
    settings: renderSettings,
  }[name];
  r(el);
}

/* ------------------------------ small helpers ---------------- */

function repoHealth() {
  const m = {};
  for (const e of state.logs) {
    if (!e.repo) continue;
    const rank = LVL_RANK[e.level] ?? 2;
    if (m[e.repo] === undefined || rank < (LVL_RANK[m[e.repo]] ?? 2)) m[e.repo] = e.level;
  }
  return m;
}
function healthDot(repoId) {
  const lvl = repoHealth()[repoId] || "INFO";
  return lvl === "ERROR" ? "err" : lvl === "WARN" ? "warn" : "ok";
}
function statCard(n, c) {
  return `<div class="stat"><div class="n">${n}</div><div class="c">${c}</div></div>`;
}
function emptyPage(msg) {
  return `<div class="empty">${msg}</div>`;
}

/* ------------------------------ overview ---------------- */

function renderOverview(el) {
  const s = state.settings?.stats || {};
  const repoCount = state.repos.length;
  const fail = !!s.last_error;
  el.innerHTML = `
    <div class="hero">
      <div>
        <div class="hb">${fail ? "⚠ BACKUP FAILED LAST RUN" : "ALL SYSTEMS NOMINAL"}</div>
        <div class="hs">${fail ? esc(s.last_error) : `${repoCount} repo${repoCount === 1 ? "" : "s"} · ${s.total_pushes ?? 0} pushes · next backup daily`}</div>
      </div>
      <div style="flex:1"></div>
      <button class="btn pri ic" data-push="all">▶ BACKUP ALL NOW</button>
      <button class="btn ic" data-pull="all">◀ PULL ALL</button>
    </div>
    <div class="grid3">
      ${statCard(repoCount, "REPOS TRACKED")}
      ${statCard(s.total_pushes ?? 0, "TOTAL PUSHES")}
      ${statCard(s.last_run ? esc(s.last_run.slice(0, 16).replace("T", " ")) : "—", "LAST BACKUP")}
    </div>
    <div style="height:18px"></div>
    <div class="card">
      <div class="card-h">Quick jump</div>
      <div class="row">
        <button class="btn ic" data-nav="repos">🗂 Manage repos</button>
        <button class="btn ic" data-nav="clock">🕐 Set a backup time</button>
        <button class="btn ic" data-nav="activity">📜 View activity</button>
        <button class="btn ic" data-nav="settings">⚙ Settings</button>
      </div>
    </div>`;
}

/* ------------------------------ repos ---------------- */

function renderRepos(el) {
  if (!state.repos.length) {
    el.innerHTML = `
      <div class="page-title">Repos</div>
      <div class="page-sub">Folders you keep backed up</div>
      ${emptyPage("nothing tracked yet — add a folder to start backing it up")}
      <div style="text-align:center"><button class="btn pri ic" data-addrepo>＋ ADD REPO…</button></div>`;
    return;
  }
  el.innerHTML = `
    <div class="page-title">Repos</div>
    <div class="page-sub">${state.repos.length} tracked · click a chip to edit times</div>
    <div class="row" style="margin-bottom:16px"><button class="btn pri ic" data-addrepo>＋ ADD REPO…</button></div>
    <div class="grid2">${state.repos.map(repoCard).join("")}</div>`;
}

function repoCard(r) {
  const chips = (r.schedules || [])
    .map(
      (s) =>
        `<span class="chip" data-repo="${esc(r.id)}" data-time="${esc(s.time)}">${esc(s.time)}<span class="x">✕</span></span>`
    )
    .join("");
  const remote = r.remote
    ? `<span class="badge okc">REMOTE ✓</span>`
    : `<span class="badge bdc">NO REMOTE</span>`;
  const branch = r.branch ? `<span class="badge">BRANCH ${esc(r.branch)}</span>` : "";
  const times = chips || `<span class="muted" style="font-size:17px">no times yet</span>`;
  return `
    <div class="repo-card" style="animation-delay:${Math.min(state.repos.indexOf(r) * 60, 300)}ms">
      <div class="rc-head">
        <span class="rc-dot ${healthDot(r.id)}"></span>
        <span class="rc-name">${esc(r.id)}</span>
        <span style="flex:1"></span>
        <button class="btn small ic" data-edit="${esc(r.id)}" title="set backup times">🕐</button>
        <button class="btn small danger" data-del="${esc(r.id)}" title="stop tracking">✕</button>
      </div>
      <div class="rc-path">${esc(r.path)}</div>
      <div class="row">${remote}${branch}</div>
      <div class="chiprow">
        <span class="chip add" data-edit="${esc(r.id)}">＋ ADD TIME</span>
        ${times}
      </div>
      <div class="row">
        <button class="btn pri ic" data-push="${esc(r.id)}">▶ PUSH NOW</button>
        <button class="btn ic" data-pull="${esc(r.id)}">◀ PULL</button>
      </div>
    </div>`;
}

/* ------------------------------ the clock mini-game ---------------- */

const CLOCK_R = 130;

function clockSvg(hr, min) {
  const cx = 150, cy = 150;
  const hourAngle = ((hr % 12) + min / 60) * 30;
  const minAngle = min * 6;
  let ticks = "";
  for (let i = 0; i < 12; i++) {
    const a = (i * 30 - 90) * (Math.PI / 180);
    const r1 = CLOCK_R - 16, r2 = CLOCK_R - 8;
    ticks += `<line class="tick${i % 3 === 0 ? " major" : ""}" x1="${cx + Math.cos(a) * r1}" y1="${cy + Math.sin(a) * r1}" x2="${cx + Math.cos(a) * r2}" y2="${cy + Math.sin(a) * r2}"></line>`;
  }
  let nums = "";
  for (let i = 1; i <= 12; i++) {
    const a = (i * 30 - 90) * (Math.PI / 180);
    nums += `<text class="num${i === (hr % 12 || 12) ? " act" : ""}" x="${cx + Math.cos(a) * (CLOCK_R - 34)}" y="${cy + Math.sin(a) * (CLOCK_R - 34) + 5}">${i}</text>`;
  }
  const hx = cx + Math.cos((hourAngle - 90) * (Math.PI / 180)) * (CLOCK_R - 46);
  const hy = cy + Math.sin((hourAngle - 90) * (Math.PI / 180)) * (CLOCK_R - 46);
  const mx = cx + Math.cos((minAngle - 90) * (Math.PI / 180)) * (CLOCK_R - 18);
  const my = cy + Math.sin((minAngle - 90) * (Math.PI / 180)) * (CLOCK_R - 18);
  return `
    <svg class="clock" width="300" height="300" viewBox="0 0 300 300">
      <circle class="face" cx="${cx}" cy="${cy}" r="${CLOCK_R}"></circle>
      <circle class="dragring" cx="${cx}" cy="${cy}" r="${CLOCK_R - 6}"></circle>
      ${ticks}${nums}
      <line class="handM" x1="${cx}" y1="${cy}" x2="${mx}" y2="${my}"></line>
      <line class="handH" x1="${cx}" y1="${cy}" x2="${hx}" y2="${hy}"></line>
      <circle class="pin" cx="${cx}" cy="${cy}" r="9"></circle>
    </svg>`;
}

function wireClock(svg, update) {
  // pointer → angle from center; returns degrees 0..359 (0 = 12 o'clock)
  const toDeg = (ev) => {
    const rect = svg.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    let deg = (Math.atan2(ev.clientY - cy, ev.clientX - cx) * 180) / Math.PI + 90;
    return (deg + 360) % 360;
  };
  const apply = (ev) => {
    const deg = toDeg(ev);
    if (state.clockMode === "H") {
      state.clockH = Math.round(deg / 30) % 12 || 12;
    } else {
      state.clockM = Math.round(deg / 6) / 5 * 5; // snap to 5-min
      state.clockM = (state.clockM + 60) % 60;
    }
    update(true);
  };
  svg.addEventListener("pointerdown", (ev) => {
    state.clockBusy = true;
    svg.classList.add("dragging");
    svg.setPointerCapture(ev.pointerId);
    apply(ev);
  });
  svg.addEventListener("pointermove", (ev) => {
    if (svg.classList.contains("dragging")) apply(ev);
  });
  svg.addEventListener("pointerup", (ev) => {
    svg.classList.remove("dragging");
    state.clockBusy = false;
    apply(ev);
    update(false);
  });
}

/* one clock instance: svg + digital + mode + steppers + schedule button */
function clockWidget(repo, host) {
  if (!repo) return;
  state.clockRepo = repo.id;
  if (host.id === "clockHost" && !host.isConnected) return;
  const update = (busy) => {
    state.clockBusy = busy || state.clockBusy;
    const svgBox = host.querySelector(".clock-face-box");
    if (svgBox) svgBox.innerHTML = clockSvg(state.clockH, state.clockM);
    const read = host.querySelector(".dread");
    if (read) {
      read.innerHTML = `${hm(state.clockH, state.clockM)}<small>${state.clockMode === "H" ? "drag or tap to set HOUR" : "drag or tap to set MINUTES"}</small>`;
      read.classList.remove("pop");
      void read.offsetWidth;
      read.classList.add("pop");
    }
    host.querySelectorAll(".mode-switch .m").forEach((m) =>
      m.classList.toggle("act", m.dataset.clockmode === state.clockMode)
    );
    const btn = host.querySelector("[data-clockadd]");
    if (btn) btn.textContent = `＋ SCHEDULE BACKUP @ ${hm(state.clockH, state.clockM)}`;
  };
  host.innerHTML = `
    <div class="card-h">🕐 Set backup time — ${esc(repo.id)}</div>
    <div class="clockbox">
      <div class="clock-face-box">${clockSvg(state.clockH, state.clockM)}</div>
      <div>
        <div class="dread">${hm(state.clockH, state.clockM)}</div>
        <div style="height:12px"></div>
        <div class="mode-switch">
          <div class="m" data-clockmode="H">hour</div>
          <div class="m" data-clockmode="M">min</div>
        </div>
        <div style="height:12px"></div>
        <div class="stepper">
          <button data-clockminus="H">−</button>
          <div class="val" id="clockVal">${hm(state.clockH, state.clockM)}</div>
          <button data-clockplus="H">＋</button>
        </div>
        <div class="clock-hint">tap or drag on the clock · minutes snap to 5</div>
        <div style="height:14px"></div>
        <button class="btn pri" data-clockadd>＋ SCHEDULE BACKUP @ ${hm(state.clockH, state.clockM)}</button>
      </div>
    </div>`;
  const svg = host.querySelector("svg.clock");
  if (svg) {
    wireClock(svg, update);
    update(false);
  }
}

/* re-render the active clock widget (drawer when open, else clock page) */
function rerenderClockHost() {
  const repo = state.repos.find((r) => r.id === state.clockRepo) || state.repos[0];
  const inDrawer = document.getElementById("drawer").classList.contains("on");
  const host = inDrawer ? document.getElementById("drawerBody") : document.getElementById("clockHost");
  if (host && repo) clockWidget(repo, host);
}

/* ------------------------------ clock page ---------------- */

function renderClockPage(el) {
  if (!state.repos.length) {
    el.innerHTML = `
      <div class="page-title">Clock</div>
      <div class="page-sub">Pick a backup time by playing with the clock</div>
      ${emptyPage("add a repo first — then set its backup time here")}
      <div style="text-align:center"><button class="btn pri ic" data-addrepo>＋ ADD REPO…</button></div>`;
    return;
  }
  if (!state.clockRepo || !state.repos.some((r) => r.id === state.clockRepo)) {
    state.clockRepo = state.repos[0].id;
  }
  const repo = state.repos.find((r) => r.id === state.clockRepo);
  const selectors = state.repos
    .map((r) => {
      const times = (r.schedules || []).map((s) => s.time).join(", ") || "no times";
      return `<div class="chip ${r.id === state.clockRepo ? "add" : ""}" data-clockrepo="${esc(r.id)}" title="${esc(times)}">${esc(r.id)}</div>`;
    })
    .join("");
  el.innerHTML = `
    <div class="page-title">Clock</div>
    <div class="page-sub">Drag the hands like a real clock — it doubles as a game</div>
    <div class="chiprow">${selectors}</div>
    <div id="clockHost"></div>
    <div style="height:16px"></div>
    <div class="card">
      <div class="card-h">Scheduled times for ${esc(repo.id)}</div>
      <div class="chiprow">
        ${(repo.schedules || []).map((s) => `<span class="chip" data-repo="${esc(repo.id)}" data-time="${esc(s.time)}">${esc(s.time)}<span class="x">✕</span></span>`).join("") || `<span class="muted">no times — schedule one with the clock above</span>`}
      </div>
    </div>`;
  clockWidget(repo, document.getElementById("clockHost"));
}

/* ------------------------------ activity ---------------- */

function renderActivity(el) {
  const rows = state.logs
    .map(
      (e, i) => `
      <div class="log-entry" style="animation-delay:${Math.min(i * 40, 320)}ms">
        <span class="lvl ${e.level || "INFO"}">${esc(e.level || "INFO")}</span>
        <span class="ts">[${esc(e.ts)}]</span>
        <span class="msg">${e.repo ? `<b class="okc">${esc(e.repo)}</b> · ` : ""}${esc(e.message)}</span>
      </div>`
    )
    .join("");
  el.innerHTML = `
    <div class="page-title">Activity</div>
    <div class="page-sub">Latest events, newest at the bottom</div>
    <div class="card">${rows || emptyPage("no activity yet")}</div>`;
}

/* ------------------------------ settings ---------------- */

function renderSettings(el) {
  const s = state.settings || {};
  const themeCards = Object.keys(THEME_SWATCH)
    .map((n) => {
      const act = n === state.theme ? " active" : "";
      return `<div class="theme-card${act}" data-theme="${n}">
        <div class="sw" style="background:${THEME_SWATCH[n]}"></div>
        <div class="tn">${n}</div>
      </div>`;
    })
    .join("");
  el.innerHTML = `
    <div class="page-title">Settings</div>
    <div class="page-sub">Appearance & behaviour</div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-h">Theme</div>
      <div class="theme-grid">${themeCards}</div>
    </div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-h">Behaviour</div>
      <div class="row" style="gap:26px">
        <div class="toggle ${s.autosync ? "on" : ""}" id="tgAutosync">
          <div class="sw-box"><div class="knob"></div></div>
          <div><div style="font-size:24px">Autosync</div><div class="muted" style="font-size:16px">daemon pushes on schedule</div></div>
        </div>
        <div class="toggle ${s.notifications ? "on" : ""}" id="tgNotify">
          <div class="sw-box"><div class="knob"></div></div>
          <div><div style="font-size:24px">Notifications</div><div class="muted" style="font-size:16px">desktop popups on results</div></div>
        </div>
        <div class="toggle ${document.body.classList.contains("hi") ? "on" : ""}" id="tgHi">
          <div class="sw-box"><div class="knob"></div></div>
          <div><div style="font-size:24px">High contrast</div><div class="muted" style="font-size:16px">stronger text for tired eyes</div></div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-h">About</div>
      <div>tidy <span class="okc">0.1.0</span> — pixel backup &amp; sync · config in <span class="muted">~/.config/tidy</span></div>
    </div>`;
}

/* ------------------------------ drawer (slides up) ---------------- */

function openDrawer(html) {
  document.getElementById("drawer").innerHTML =
    `<div class="drawer-handle"></div>` +
    `<button class="btn small ghost drawer-close" data-close>✕ close</button>` +
    `<div id="drawerBody">${html}</div>`;
  document.getElementById("drawer").classList.add("on");
  document.getElementById("scrim").classList.add("on");
}
function closeDrawer() {
  document.getElementById("drawer").classList.remove("on");
  document.getElementById("scrim").classList.remove("on");
}

/* ------------------------------ actions ---------------- */

async function addRepoFlow() {
  const api = await getApi();
  if (!api) return;
  setBusy(true);
  toast("pick a folder…");
  const res = await api.add_repo();
  setBusy(false);
  if (res.ok) {
    toast(`added ${res.repo.id} ✓`, "good");
    state.clockRepo = res.repo.id;
    await refresh();
    showPage("repos");
  } else if (res.error && res.error !== "no folder selected") {
    toast(res.error, "bad");
  }
}

async function backupRepo(id) {
  const api = await getApi();
  if (!api) return;
  setBusy(true);
  statusBar("backing up…", id === "all" ? "tidy" : id);
  const res = await api.backup_now(id);
  setBusy(false);
  const results = res.results || [];
  const failed = results.filter((r) => !r.ok).length;
  if (id === "all") {
    toast(failed ? `${failed} failed ✗` : "all backed up ✓", failed ? "bad" : "good");
    statusBar(failed ? `${failed} failed` : "all backed up", "tidy");
  } else {
    const first = results[0];
    if (first) {
      toast(first.ok ? "backed up ✓" : "backup failed ✗", first.ok ? "good" : "bad");
      statusBar(first.message || (first.ok ? "backed up" : "failed"), id);
    }
  }
  await refresh();
  renderPage(state.page);
}

async function pullRepo(id) {
  const api = await getApi();
  if (!api) return;
  setBusy(true);
  statusBar("pulling…", id === "all" ? "tidy" : id);
  const res = await api.pull_now(id);
  setBusy(false);
  const failed = (res.results || []).filter((r) => !r.ok).length;
  toast(id === "all" ? (failed ? `${failed} failed ✗` : "pulled all ✓") : "pulled ✓", failed ? "bad" : "good");
  statusBar(id === "all" ? (failed ? `${failed} failed` : "pulled all") : "pulled", id === "all" ? "tidy" : id);
  await refresh();
  renderPage(state.page);
}

async function setTheme(name) {
  const api = await getApi();
  if (!api) return;
  const res = await api.set_theme(name);
  if (!res.error) {
    state.theme = res.theme;
    document.documentElement.dataset.theme = res.theme;
    toast(`theme: ${res.theme} ✓`, "good");
    renderPage(state.page);
  }
}

/* ------------------------------ global click handling ---------------- */

document.addEventListener("click", async (e) => {
  const api = await getApi();
  if (!api) return;

  const nav = e.target.closest("[data-nav]");
  if (nav) {
    showPage(nav.dataset.nav);
    return;
  }
  const navItem = e.target.closest(".nav-item");
  if (navItem) {
    showPage(navItem.dataset.page);
    return;
  }
  if (e.target.closest("[data-close]")) {
    closeDrawer();
    return;
  }
  if (e.target.closest("#scrim")) {
    closeDrawer();
    return;
  }

  const theme = e.target.closest(".theme-card");
  if (theme) {
    setTheme(theme.dataset.theme);
    return;
  }

  const addRepo = e.target.closest("[data-addrepo]");
  if (addRepo) {
    addRepoFlow();
    return;
  }

  const push = e.target.closest("[data-push]");
  if (push) {
    backupRepo(push.dataset.push);
    return;
  }
  const pull = e.target.closest("[data-pull]");
  if (pull) {
    pullRepo(pull.dataset.pull);
    return;
  }

  const del = e.target.closest("[data-del]");
  if (del) {
    const res = await api.remove_repo(del.dataset.del);
    toast(res.error ? res.error : `removed ${del.dataset.del}`, res.error ? "bad" : undefined);
    if (!res.error && state.clockRepo === del.dataset.del) state.clockRepo = null;
    await refresh();
    renderPage(state.page);
    return;
  }

  // repo card "edit" → clock drawer
  const edit = e.target.closest("[data-edit]");
  if (edit) {
    const repo = state.repos.find((r) => r.id === edit.dataset.edit);
    if (repo) {
      openDrawer("");
      clockWidget(repo, document.getElementById("drawerBody"));
    }
    return;
  }

  // clock page repo selector
  const clockRepo = e.target.closest("[data-clockrepo]");
  if (clockRepo) {
    state.clockRepo = clockRepo.dataset.clockrepo;
    renderPage("clock");
    return;
  }

  // clock mode switch
  const mode = e.target.closest("[data-clockmode]");
  if (mode) {
    state.clockMode = mode.dataset.clockmode;
    state.clockBusy = false;
    rerenderClockHost();
    return;
  }

  // steppers
  const step = e.target.closest("[data-clockplus],[data-clockminus]");
  if (step) {
    if (step.dataset.clockplus === "H") {
      state.clockH = (state.clockH + 1 + 24) % 24;
    } else if (step.dataset.clockminus === "H") {
      state.clockH = (state.clockH - 1 + 24) % 24;
    }
    rerenderClockHost();
    return;
  }

  // schedule add (clock)
  const addTime = e.target.closest("[data-clockadd]");
  if (addTime) {
    if (!state.clockRepo) return;
    setBusy(true);
    const res = await api.add_schedule(state.clockRepo, hm(state.clockH, state.clockM));
    setBusy(false);
    toast(res.error ? res.error : `scheduled ${hm(state.clockH, state.clockM)} ✓`, res.error ? "bad" : "good");
    await refresh();
    if (document.getElementById("drawer").classList.contains("on")) {
      rerenderClockHost();
    } else {
      renderPage(state.page);
    }
    return;
  }

  // remove a schedule chip
  const chip = e.target.closest("[data-time]");
  if (chip) {
    const res = await api.remove_schedule(chip.dataset.repo, chip.dataset.time);
    toast(res.error ? res.error : `removed ${chip.dataset.time}`, res.error ? "bad" : undefined);
    await refresh();
    renderPage(state.page);
    return;
  }

  // settings toggles
  const tgAutosync = e.target.closest("#tgAutosync");
  if (tgAutosync) {
    const next = !state.settings.autosync;
    await api.set_autosync(next);
    await refresh();
    renderPage("settings");
    return;
  }
  const tgNotify = e.target.closest("#tgNotify");
  if (tgNotify) {
    const next = !state.settings.notifications;
    await api.set_notifications(next);
    await refresh();
    renderPage("settings");
    return;
  }
  const tgHi = e.target.closest("#tgHi");
  if (tgHi) {
    document.body.classList.toggle("hi");
    toast(document.body.classList.contains("hi") ? "high contrast on ✓" : "high contrast off", "good");
    return;
  }
});

/* ------------------------------ toolbar buttons ---------------- */

document.getElementById("btnBackupAll").addEventListener("click", () => backupRepo("all"));
document.getElementById("btnPullAll").addEventListener("click", () => pullRepo("all"));

/* ------------------------------ refresh ---------------- */

let refreshToken = 0;
async function refresh() {
  const token = ++refreshToken;
  const api = await getApi();
  if (!api || token !== refreshToken) return;

  const settings = await api.get_settings();
  state.settings = settings;
  state.theme = settings.theme;
  document.documentElement.dataset.theme = settings.theme;

  const repos = await api.list_repos();
  state.repos = repos;
  if (state.clockRepo && !repos.some((r) => r.id === state.clockRepo)) state.clockRepo = null;
  if (!state.clockRepo && repos.length) state.clockRepo = repos[0].id;

  state.logs = await api.get_logs(50);

  // titlebar status
  const st = settings.stats || {};
  const tStatus = document.getElementById("tStatus");
  tStatus.classList.toggle("fail", !!st.last_error);
  document.getElementById("tStatusMsg").textContent = st.last_error
    ? "last backup failed"
    : `${repos.length} repo${repos.length === 1 ? "" : "s"} · ${st.total_pushes ?? 0} pushes`;
  document.getElementById("navRepos").textContent = repos.length || "";

  // re-render current page (skip while the user is dragging the clock)
  if (!state.clockBusy) renderPage(state.page);
}

/* ------------------------------ boot ---------------- */

document.body.classList.add("hi");
setInterval(tickClock, 1000);
tickClock();
showPage("overview");
refresh();
setInterval(() => {
  if (!state.clockBusy) refresh();
}, 4000);
