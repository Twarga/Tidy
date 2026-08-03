/* Tidy desktop UI v4.
   Model: work every session (repo) has its OWN configure page. Add a session,
   pick its folder, then set MANY daily times (digital input OR the clock
   mini-game in a slide-up drawer). Activity log is a VSCode-style collapsible
   panel. Talks to Python via pywebview (Promise-based bridge). */
"use strict";

// pywebview injects `window.pywebview` shortly after page scripts on GTK.
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
const LVL_RANK = { ERROR: 0, WARN: 1, INFO: 2 };

const state = {
  page: "sessions",
  configRepo: null,
  repos: [],
  logs: [],
  settings: null,
  theme: "neon",
  clockH: 18,
  clockM: 0,
  clockMode: "H",
  clockBusy: false,
  logsOpen: true,
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
const TIME_RE = /^([01]?\d|2[0-3]):([0-5]\d)$/;

/* ------------------------------ chrome ---------------- */

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

/* ------------------------------ routing ---------------- */

function showPage(name) {
  state.page = name;
  document.querySelectorAll(".page").forEach((p) => p.classList.toggle("on", p.id === `p-${name}`));
  const navActive = name === "configure" ? "sessions" : name;
  document.querySelectorAll(".nav-item").forEach((n) =>
    n.classList.toggle("active", n.dataset.page === navActive)
  );
  renderPage(name);
}

function renderPage(name) {
  const el = document.getElementById(`p-${name}`);
  if (!el) return;
  if (name === "configure" && !state.configRepo && state.repos.length) {
    state.configRepo = state.repos[0].id;
  }
  if (name === "configure" && !state.repos.some((r) => r.id === state.configRepo)) {
    showPage("sessions");
    return;
  }
  const renderers = {
    sessions: renderSessions,
    configure: renderConfigure,
    activity: renderActivity,
    settings: renderSettings,
  };
  renderers[name](el);
}

/* ------------------------------ helpers ---------------- */

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
function emptyPage(msg, btn) {
  return `<div class="empty">${msg}</div>${btn ? `<div style="text-align:center">${btn}</div>` : ""}`;
}

/* ------------------------------ Sessions page ------------------------------ */

function renderSessions(el) {
  if (!state.repos.length) {
    el.innerHTML = `
      <div class="page-title">Working sessions</div>
      <div class="page-sub">Each session is a folder you keep backed up to git</div>
      ${emptyPage("no sessions yet — add your first folder", `<button class="btn pri ic" data-addsession>＋ ADD SESSION…</button>`)}
      <div style="height:8px"></div>
      <div class="card muted" style="font-size:18px">
        A session = folder + remote + daily push times. Click a session to configure it.
      </div>`;
    return;
  }
  el.innerHTML = `
    <div class="page-title">Working sessions</div>
    <div class="page-sub">${state.repos.length} session${state.repos.length === 1 ? "" : "s"} · click to configure</div>
    <div class="row" style="margin-bottom:16px"><button class="btn pri ic" data-addsession>＋ ADD SESSION</button></div>
    <div class="grid2">${state.repos.map(repoCard).join("")}</div>`;
}

function repoCard(r) {
  const times = (r.schedules || []).map((s) => s.time).join(" · ") || "no times yet";
  const remote = r.remote ? `<span class="badge okc">REMOTE ✓</span>` : `<span class="badge bdc">NO REMOTE</span>`;
  const branch = r.branch ? `<span class="badge">BR ${esc(r.branch)}</span>` : "";
  return `
    <div class="repo-card" data-open="${esc(r.id)}" style="animation-delay:${Math.min(state.repos.indexOf(r) * 60, 300)}ms">
      <div class="rc-head">
        <span class="rc-dot ${healthDot(r.id)}"></span>
        <span class="rc-name">${esc(r.id)}</span>
        <span style="flex:1"></span>
        <button class="btn small danger" data-del="${esc(r.id)}" title="stop tracking">✕</button>
      </div>
      <div class="rc-path">${esc(r.path)}</div>
      <div class="row">${remote}${branch}</div>
      <div class="chiprow">
        <span class="chip add" data-open="${esc(r.id)}">＋ configure times</span>
        <span class="muted" style="font-size:18px">${times}</span>
      </div>
    </div>`;
}

/* ------------------------------ Configure page (per session) ------------------------------ */

function renderConfigure(el) {
  const r = state.repos.find((x) => x.id === state.configRepo);
  if (!r) return;
  const chips = (r.schedules || []).map((s) =>
    `<span class="chip" data-chiptime="${esc(r.id)}" data-time="${esc(s.time)}">${esc(s.time)}<span class="x">✕</span></span>`
  ).join("") || `<span class="muted" style="font-size:19px">none yet — add one or three below</span>`;
  const remote = r.remote ? `<span class="badge okc">REMOTE ✓</span>` : `<span class="badge bdc">NO REMOTE</span>`;
  const branch = r.branch ? `<span class="badge">BR ${esc(r.branch)}</span>` : "";
  const st = state.settings?.stats || {};
  el.innerHTML = `
    <div class="cfg-head">
      <button class="btn small ghost ic" data-nav="sessions">◀ sessions</button>
      <span class="rc-dot ${healthDot(r.id)}"></span>
      <div>
        <div class="cfg-name">${esc(r.id)}</div>
        <div class="muted" style="font-size:17px">${esc(r.path)}</div>
      </div>
      <div style="flex:1"></div>
      ${remote}${branch}
    </div>

    <div class="card" style="margin-bottom:16px">
      <div class="card-h">Schedule — add several times per day</div>
      <div class="chiprow"><div class="times-list" id="timesChips">${chips}</div></div>
      <div class="addrow">
        <input class="time" id="timeInput" value="18:00" spellcheck="false">
        <button class="btn" data-digitaladd>＋ ADD TIME</button>
        <span class="muted" style="font-size:17px">or</span>
        <button class="btn live ic" data-openclock>🕐 PICK WITH THE CLOCK</button>
      </div>
    </div>

    <div class="grid2">
      <div class="card">
        <div class="card-h">Actions</div>
        <div class="row">
          <button class="btn pri ic" data-push="${esc(r.id)}">▶ PUSH NOW</button>
          <button class="btn ic" data-pull="${esc(r.id)}">◀ PULL</button>
        </div>
      </div>
      <div class="card">
        <div class="card-h">Stats</div>
        <div class="row">
          ${statCard(st.total_pushes ?? 0, "PUSHES")}
          ${statCard(st.last_run ? esc(st.last_run.slice(0, 16).replace("T", " ")) : "—", "LAST RUN")}
        </div>
      </div>
    </div>`;
}

/* ------------------------------ the clock mini-game ------------------------------ */

const CLOCK_R = 130;
function clockSvg(hr, min) {
  const cx = 150, cy = 150;
  const hourAngle = ((hr % 12) + min / 60) * 30;
  const minAngle = min * 6;
  let ticks = "";
  for (let i = 0; i < 12; i++) {
    const a = (i * 30 - 90) * (Math.PI / 180);
    ticks += `<line class="tick${i % 3 === 0 ? " major" : ""}" x1="${cx + Math.cos(a) * (CLOCK_R - 16)}" y1="${cy + Math.sin(a) * (CLOCK_R - 16)}" x2="${cx + Math.cos(a) * (CLOCK_R - 8)}" y2="${cy + Math.sin(a) * (CLOCK_R - 8)}"></line>`;
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
  const toDeg = (ev) => {
    const rect = svg.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    return (((Math.atan2(ev.clientY - cy, ev.clientX - cx) * 180) / Math.PI + 90) + 360) % 360;
  };
  const apply = (ev) => {
    const deg = toDeg(ev);
    if (state.clockMode === "H") {
      state.clockH = Math.round(deg / 30) % 12 || 12;
    } else {
      state.clockM = ((Math.round(deg / 6) / 5) * 5 + 60) % 60;
    }
    update();
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
    update();
  });
}

function clockWidget(repo, host) {
  if (!repo) return;
  state.clockRepo = repo.id;
  const update = () => {
    const box = host.querySelector(".clock-face-box");
    if (box) box.innerHTML = clockSvg(state.clockH, state.clockM);
    const read = host.querySelector(".dread");
    if (read) {
      read.innerHTML = `${hm(state.clockH, state.clockM)}<small>${state.clockMode === "H" ? "drag or tap the HOUR hand" : "drag or tap the MINUTES hand"}</small>`;
      read.classList.remove("pop");
      void read.offsetWidth;
      read.classList.add("pop");
    }
    host.querySelectorAll(".mode-switch .m").forEach((m) =>
      m.classList.toggle("act", m.dataset.clockmode === state.clockMode)
    );
    const btn = host.querySelector("[data-clockadd]");
    if (btn) btn.textContent = `＋ ADD ${hm(state.clockH, state.clockM)} TO THIS SESSION`;
  };
  host.innerHTML = `
    <div class="card-h">🕐 Pick a time — ${esc(repo.id)}</div>
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
          <div class="val">${hm(state.clockH, state.clockM)}</div>
          <button data-clockplus="H">＋</button>
        </div>
        <div class="clock-hint">tap or drag on the clock · minutes snap to 5</div>
        <div style="height:14px"></div>
        <button class="btn pri" data-clockadd>＋ ADD ${hm(state.clockH, state.clockM)} TO THIS SESSION</button>
      </div>
    </div>`;
  const svg = host.querySelector("svg.clock");
  if (svg) {
    wireClock(svg, update);
    update();
  }
}

/* ------------------------------ Activity page ------------------------------ */

function renderActivity(el) {
  const rows = state.logs
    .map((e, i) => `
      <div class="log-entry" style="animation-delay:${Math.min(i * 40, 320)}ms">
        <span class="lvl ${e.level || "INFO"}">${esc(e.level || "INFO")}</span>
        <span class="ts">[${esc(e.ts)}]</span>
        <span class="msg">${e.repo ? `<b class="okc">${esc(e.repo)}</b> · ` : ""}${esc(e.message)}</span>
      </div>`)
    .join("");
  el.innerHTML = `
    <div class="page-title">Activity</div>
    <div class="page-sub">Every push, pull and error · newest at the bottom</div>
    <div class="card">${rows || emptyPage("no activity yet")}</div>`;
}
function emptyPlace(msg) {
  return `<div class="empty">${msg}</div>`;
}

/* ------------------------------ Settings page ------------------------------ */

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
          <div><div style="font-size:24px">Autosync</div><div class="muted" style="font-size:16px">push on schedule</div></div>
        </div>
        <div class="toggle ${s.notifications ? "on" : ""}" id="tgNotify">
          <div class="sw-box"><div class="knob"></div></div>
          <div><div style="font-size:24px">Notifications</div><div class="muted" style="font-size:16px">desktop popups</div></div>
        </div>
        <div class="toggle ${document.body.classList.contains("hi") ? "on" : ""}" id="tgHi">
          <div class="sw-box"><div class="knob"></div></div>
          <div><div style="font-size:24px">High contrast</div><div class="muted" style="font-size:16px">stronger text for tired eyes</div></div>
        </div>
        <div class="toggle ${state.logsOpen ? "on" : ""}" id="tgLogs">
          <div class="sw-box"><div class="knob"></div></div>
          <div><div style="font-size:24px">Activity panel</div><div class="muted" style="font-size:16px">show the log bar at the bottom</div></div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-h">About</div>
      <div>tidy <span class="okc">0.1.0</span> — pixel backup &amp; sync · config in <span class="muted">~/.config/tidy</span></div>
    </div>`;
}

/* ------------------------------ log panel (VSCode-style) ------------------------------ */

function setLogsOpen(on) {
  state.logsOpen = !!on;
  document.body.classList.toggle("logs-on", state.logsOpen);
  const btn = document.getElementById("btnLogs");
  if (btn) btn.classList.toggle("live", state.logsOpen);
}

function renderLogPanel(logs) {
  const box = document.getElementById("lpList");
  if (!box) return;
  const rows = logs.map((e) => `
    <div class="log-entry">
      <span class="ts">[${esc(e.ts)}]</span>
      <span class="msg">${e.repo ? `<b class="okc">${esc(e.repo)}</b> · ` : ""}${esc(e.message)}</span>
    </div>`).join("");
  box.innerHTML = rows || `<div class="empty">no activity yet</div>`;
}

function toggleLogs() {
  setLogsOpen(!state.logsOpen);
}

/* ------------------------------ actions ------------------------------ */

async function addSessionFlow() {
  const api = await getApi();
  if (!api) return;
  setBusy(true);
  toast("pick a folder…");
  const res = await api.add_repo();
  setBusy(false);
  if (res.ok) {
    toast(`session ${res.repo.id} added ✓`, "good");
    state.configRepo = res.repo.id;
    await refresh();
    showPage("configure");
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
  refresh();
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
  refresh();
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

async function addSchedule(repoId, time, fromClock) {
  const api = await getApi();
  if (!api) return;
  if (!TIME_RE.test(time)) {
    toast("enter a valid time like 18:30", "bad");
    return;
  }
  setBusy(true);
  const res = await api.add_schedule(repoId, time);
  setBusy(false);
  toast(res.error ? res.error : `added ${time} ✓`, res.error ? "bad" : "good");
  await refresh();
  if (fromClock) {
    // keep the clock open so you can add the next of your 3 times
    const inDrawer = document.getElementById("drawer").classList.contains("on");
    if (!inDrawer) openClockDrawer();
    rerenderClock();
  } else {
    renderPage("configure");
  }
}

function openClockDrawer() {
  const repo = state.repos.find((r) => r.id === state.configRepo) || state.repos[0];
  if (!repo) return;
  openDrawer("");
  clockWidget(repo, document.getElementById("drawerBody"));
}

function rerenderClock() {
  const repo = state.repos.find((r) => r.id === state.configRepo) || state.repos[0];
  const host = document.getElementById("drawer").classList.contains("on")
    ? document.getElementById("drawerBody")
    : null;
  if (host && repo) clockWidget(repo, host);
}

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

/* ------------------------------ global click handling ------------------------------ */

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
  if (e.target.closest("[data-close]") || e.target.closest("#scrim")) {
    closeDrawer();
    return;
  }

  const theme = e.target.closest(".theme-card");
  if (theme) {
    setTheme(theme.dataset.theme);
    return;
  }

  const addSession = e.target.closest("[data-addsession]");
  if (addSession) {
    addSessionFlow();
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
    if (state.configRepo === del.dataset.del) state.configRepo = null;
    refresh();
    return;
  }

  const open = e.target.closest("[data-open]");
  if (open) {
    state.configRepo = open.dataset.open;
    showPage("configure");
    return;
  }

  // remove one schedule chip (configure page)
  const chip = e.target.closest("[data-chiptime]");
  if (chip) {
    const res = await api.remove_schedule(chip.dataset.chiptime, chip.dataset.time);
    toast(res.error ? res.error : `removed ${chip.dataset.time}`, res.error ? "bad" : undefined);
    await refresh();
    renderPage("configure");
    return;
  }

  // digital add
  const digital = e.target.closest("[data-digitaladd]");
  if (digital) {
    const val = (document.getElementById("timeInput") || {}).value || "18:00";
    addSchedule(state.configRepo, val, false);
    return;
  }

  // open the clock mini-game
  const openClock = e.target.closest("[data-openclock]");
  if (openClock) {
    openClockDrawer();
    return;
  }

  // clock: mode switch
  const mode = e.target.closest("[data-clockmode]");
  if (mode) {
    state.clockMode = mode.dataset.clockmode;
    state.clockBusy = false;
    rerenderClock();
    return;
  }

  // clock: steppers
  const step = e.target.closest("[data-clockplus],[data-clockminus]");
  if (step) {
    if (step.dataset.clockplus === "H") state.clockH = (state.clockH + 1 + 24) % 24;
    else if (step.dataset.clockminus === "H") state.clockH = (state.clockH - 1 + 24) % 24;
    rerenderClock();
    return;
  }

  // clock: add this time
  const clockAdd = e.target.closest("[data-clockadd]");
  if (clockAdd) {
    addSchedule(state.configRepo, hm(state.clockH, state.clockM), true);
    return;
  }

  // settings toggles
  const tgAutosync = e.target.closest("#tgAutosync");
  if (tgAutosync) {
    await api.set_autosync(!state.settings.autosync);
    refresh();
    return;
  }
  const tgNotify = e.target.closest("#tgNotify");
  if (tgNotify) {
    await api.set_notifications(!state.settings.notifications);
    refresh();
    return;
  }
  const tgHi = e.target.closest("#tgHi");
  if (tgHi) {
    document.body.classList.toggle("hi");
    toast(document.body.classList.contains("hi") ? "high contrast on ✓" : "high contrast off", "good");
    return;
  }
  const tgLogs = e.target.closest("#tgLogs");
  if (tgLogs) {
    drawLogs();
    return;
  }
});

function drawLogs() {
  setLogsOpen(!state.logsOpen);
}

/* ------------------------------ toolbar buttons ------------------------------ */

document.getElementById("btnBackupAll").addEventListener("click", () => backupRepo("all"));
document.getElementById("btnPullAll").addEventListener("click", () => pullRepo("all"));
document.getElementById("btnLogs").addEventListener("click", drawLogs);
document.getElementById("logClose").addEventListener("click", drawLogs);

/* ------------------------------ refresh ------------------------------ */

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
  if (state.configRepo && !repos.some((r) => r.id === state.configRepo)) state.configRepo = null;
  if (!state.configRepo && repos.length) state.configRepo = repos[0].id;

  state.logs = await api.get_logs(50);

  const st = settings.stats || {};
  const tStatus = document.getElementById("tStatus");
  tStatus.classList.toggle("fail", !!st.last_error);
  document.getElementById("tStatusMsg").textContent = st.last_error
    ? "last backup failed"
    : `${repos.length} session${repos.length === 1 ? "" : "s"} · ${st.total_pushes ?? 0} pushes`;
  document.getElementById("navRepos").textContent = repos.length || "";

  setLogsOpen(state.logsOpen);
  renderLogPanel(state.logs);
  if (!state.clockBusy) renderPage(state.page);
}

/* ------------------------------ boot ------------------------------ */

document.body.classList.add("hi");
setLogsOpen(true);
setInterval(tickClock, 1000);
tickClock();
showPage("sessions");
refresh();
setInterval(() => {
  if (!state.clockBusy) refresh();
}, 4000);