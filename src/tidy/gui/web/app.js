/* Tidy desktop UI — toolbar + repo sidebar + detail panel + bottom log strip.
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

// theme swatch colors (mirror themes.py) for the toolbar dots
const THEME_SWATCH = {
  neon: "#ff4fd8",
  crt: "#7dff8a",
  gameboy: "#9bbc0f",
  watermelon: "#2b8c3e",
  paper: "#c1440e",
};

let currentTheme = "neon";
const state = { selected: null, repos: [], logs: [] };

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

function toast(msg) {
  const el = document.getElementById("toast");
  el.style.display = "block";
  el.textContent = msg;
  clearTimeout(el._tm);
  el._tm = setTimeout(() => (el.style.display = "none"), 2200);
}

const LVL_RANK = { ERROR: 0, WARN: 1, INFO: 2 };
function repoHealth() {
  // repo id -> worst recent log level (for sidebar dots)
  const m = {};
  for (const e of state.logs) {
    if (!e.repo) continue;
    const rank = LVL_RANK[e.level] ?? 2;
    if (m[e.repo] === undefined || rank < (LVL_RANK[m[e.repo]] ?? 2)) m[e.repo] = e.level;
  }
  return m;
}

/* ============================ rendering ============================ */

function renderThemeDots(names) {
  document.getElementById("themeDots").innerHTML = names
    .map(
      (n) =>
        `<span class="dot-btn${n === currentTheme ? " active" : ""}" data-theme="${esc(n)}" title="${esc(n)}" style="background:${THEME_SWATCH[n] || "var(--panel2)"}"></span>`
    )
    .join("");
}

function renderSidebar(repos, health) {
  const box = document.getElementById("repolist");
  if (!repos.length) {
    box.innerHTML = `<div class="empty">no repos yet</div>`;
    return;
  }
  box.innerHTML = repos
    .map((r) => {
      const lvl = health[r.id] || "INFO";
      const dotCls = lvl === "ERROR" ? "err" : lvl === "WARN" ? "warn" : "ok";
      const active = state.selected === r.id ? " active" : "";
      return `<div class="repo-item${active}" data-id="${esc(r.id)}">
        <span class="r-dot ${dotCls}"></span>
        <span class="r-name">${esc(r.id)}</span>
        <span class="r-x" data-del="${esc(r.id)}" title="remove repo">✕</span>
      </div>`;
    })
    .join("");
}

function renderDetail(repo, stats, repoCount) {
  const box = document.getElementById("detail");
  if (!repo) {
    box.innerHTML = `<div class="empty">select a repo from the sidebar — or ＋ ADD REPO</div>`;
    return;
  }
  const chips = (repo.schedules || [])
    .map(
      (s) =>
        `<span class="chip" data-repo="${esc(repo.id)}" data-time="${esc(s.time)}"><span class="x">✕</span>${esc(s.time)}</span>`
    )
    .join("");
  const remote = repo.remote
    ? `<span class="badge okc">remote ✓</span>`
    : `<span class="badge badc">no remote</span>`;
  const branch = repo.branch ? `<span class="badge">branch ${esc(repo.branch)}</span>` : "";
  box.innerHTML = `
    <div class="banner">
      <div class="dot"></div>
      <div>
        <div class="bt" id="detailStatus">STATUS: READY</div>
        <div class="bs" id="detailSub">${stats.last_error ? esc(stats.last_error) : "all systems nominal"}</div>
      </div>
    </div>
    <div class="repoid">${esc(repo.id)}</div>
    <div class="repopath">${esc(repo.path)}</div>
    <div class="badges">${remote}${branch}</div>

    <div class="card-head">◈ SCHEDULE</div>
    <div class="chips">
      <input type="time" class="time" data-repo="${esc(repo.id)}" value="18:00">
      <span class="chip" data-add="${esc(repo.id)}">＋ ADD TIME</span>
      ${chips}
    </div>

    <div class="card-head">◈ ACTIONS</div>
    <div class="btnbar">
      <button class="btn pri" data-push="${esc(repo.id)}">▶ PUSH NOW</button>
      <button class="btn" data-pull="${esc(repo.id)}">PULL</button>
    </div>

    <div class="card-head">◈ STATS</div>
    <div class="stats">
      <div class="stat"><div class="n">${stats.last_run ? esc(stats.last_run.slice(5, 16)) : "—"}</div><div class="c">LAST BACKUP</div></div>
      <div class="stat"><div class="n">${repoCount}</div><div class="c">REPOS</div></div>
      <div class="stat"><div class="n">${stats.total_pushes ?? 0}</div><div class="c">PUSHES</div></div>
    </div>`;
}

function renderLog(logs) {
  const box = document.getElementById("log");
  box.innerHTML =
    logs
      .map((e) => {
        const cls = { INFO: "ok", WARN: "wa", ERROR: "er" }[e.level] || "";
        const repo = e.repo ? `<span class="er">${esc(e.repo)}</span> ` : "";
        return `<div><span class="ts">[${esc(e.ts)}]</span> ${repo}<span class="${cls}">${esc(e.message)}</span></div>`;
      })
      .join("") || `<div class="empty">no activity yet</div>`;
}

/* ============================ state refresh ============================ */

async function refresh() {
  const api = await getApi();
  if (!api) return;

  const settings = await api.get_settings();
  currentTheme = settings.theme;
  document.documentElement.dataset.theme = currentTheme;
  const stats = settings.stats || {};
  document.getElementById("statusLine").innerHTML = stats.last_error
    ? `<b class="badc">● last run failed</b>`
    : `<b class="okc">● all systems nominal</b>`;
  renderThemeDots(settings.themes || []);

  const repos = await api.list_repos();
  state.repos = repos;
  if (!state.selected || !repos.some((r) => r.id === state.selected)) {
    state.selected = repos.length ? repos[0].id : null;
  }

  state.logs = await api.get_logs(40);
  const health = repoHealth();
  renderSidebar(repos, health);
  renderDetail(
    state.selected ? repos.find((r) => r.id === state.selected) : null,
    stats,
    repos.length
  );
  renderLog(state.logs);
}

/* ============================ actions ============================ */

document.addEventListener("click", async (e) => {
  const api = await getApi();
  if (!api) return;

  const themeBtn = e.target.closest("[data-theme]");
  if (themeBtn) {
    const res = await api.set_theme(themeBtn.dataset.theme);
    if (!res.error) {
      currentTheme = res.theme;
      document.documentElement.dataset.theme = res.theme;
      refresh();
    }
    return;
  }

  const del = e.target.closest("[data-del]");
  if (del) {
    await api.remove_repo(del.dataset.del);
    if (state.selected === del.dataset.del) state.selected = null;
    refresh();
    return;
  }

  const item = e.target.closest(".repo-item");
  if (item) {
    state.selected = item.dataset.id;
    refresh();
    return;
  }

  const push = e.target.closest("[data-push]");
  if (push) {
    toast("pushing…");
    const res = await api.backup_now(push.dataset.push);
    const first = (res.results || [])[0];
    toast(first ? (first.ok ? "pushed ✓" : "push failed ✗") : res.error || "done");
    refresh();
    return;
  }

  const pull = e.target.closest("[data-pull]");
  if (pull) {
    toast("pulling…");
    await api.pull_now(pull.dataset.pull);
    toast("pulled ✓");
    refresh();
    return;
  }

  const add = e.target.closest("[data-add]");
  if (add) {
    const input = document.querySelector(`input.time[data-repo="${add.dataset.add}"]`);
    await api.add_schedule(add.dataset.add, input ? input.value : "18:00");
    refresh();
    return;
  }

  const chip = e.target.closest("[data-time]");
  if (chip) {
    await api.remove_schedule(chip.dataset.repo, chip.dataset.time);
    refresh();
  }
});

document.getElementById("btnAddRepo").addEventListener("click", async () => {
  const api = await getApi();
  if (!api) return;
  const res = await api.add_repo();
  toast(res.ok ? "repo added ✓" : res.error || "canceled");
  if (res.ok) state.selected = res.repo.id;
  refresh();
});

document.getElementById("btnBackupAll").addEventListener("click", async () => {
  const api = await getApi();
  if (!api) return;
  toast("pushing all…");
  const res = await api.backup_now("all");
  const failed = (res.results || []).filter((r) => !r.ok).length;
  toast(failed ? `${failed} failed ✗` : "all pushed ✓");
  refresh();
});

document.getElementById("btnPullAll").addEventListener("click", async () => {
  const api = await getApi();
  if (!api) return;
  toast("pulling…");
  await api.pull_now("all");
  toast("pulled ✓");
  refresh();
});

/* ============================ boot ============================ */
refresh();
setInterval(refresh, 4000);
