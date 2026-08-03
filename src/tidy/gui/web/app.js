/* Tidy web UI — talks to the Python Api via pywebview (Promise-based bridge). */
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

let currentTheme = "neon";

/* ---- render helpers ---- */
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

function logLine(entry) {
  const cls = { INFO: "ok", WARN: "wa", ERROR: "er" }[entry.level] || "";
  const repo = entry.repo ? `[${esc(entry.repo)}] ` : "";
  return `<span class="ts">[${esc(entry.ts)}]</span> <span class="${cls}">${repo}${esc(entry.message)}</span>`;
}

/* ---- state ---- */
async function refresh() {
  const api = await getApi();
  if (!api) return;
  const settings = await api.get_settings();
  currentTheme = settings.theme;
  document.documentElement.dataset.theme = currentTheme;
  document.getElementById("themeLabel").textContent = "theme: " + currentTheme;

  const repos = await api.list_repos();
  document.getElementById("statRepos").textContent = repos.length;
  const stats = settings.stats;
  document.getElementById("statPushes").textContent = stats.total_pushes ?? 0;
  document.getElementById("statLast").textContent = stats.last_run ? stats.last_run.slice(5, 16) : "—";
  document.getElementById("statusSub").textContent =
    stats.last_error ? "last error: " + stats.last_error : "all systems nominal";

  renderRepos(repos);
  renderThemes(settings.themes || []);
  const logs = await api.get_logs(30);
  document.getElementById("log").innerHTML = logs.map(logLine).join("") || "no activity yet";
}

function renderRepos(repos) {
  const box = document.getElementById("repos");
  if (!repos.length) {
    box.innerHTML = `<div class="empty">no repos configured — click ＋ ADD REPO</div>`;
    return;
  }
  box.innerHTML = repos.map((r) => {
    const chips = (r.schedules || [])
      .map((s) => `<span class="chip" data-repo="${esc(r.id)}" data-time="${esc(s.time)}">✕ ${esc(s.time)}</span>`)
      .join("");
    const remote = r.remote ? `<span style="color:var(--ok)">remote ✓</span>` : `<span style="color:var(--bad)">no remote</span>`;
    return `
      <div class="repo" data-id="${esc(r.id)}">
        <div class="rn">${esc(r.id)}</div>
        <div class="rp">${esc(r.path)} · ${remote}</div>
        <div class="row">
          <div class="chips">
            <input type="time" class="time" data-repo="${esc(r.id)}" value="18:00">
            <button class="chip" data-add-time="${esc(r.id)}">＋ ADD TIME</button>
            ${chips}
          </div>
          <button class="btn" data-push="${esc(r.id)}">▶ PUSH</button>
        </div>
      </div>`;
  }).join("");
}

function renderThemes(names) {
  const box = document.getElementById("themes");
  box.innerHTML = names.map((n) =>
    `<button class="th ${n === currentTheme ? "active" : ""}" data-theme-name="${esc(n)}" title="${esc(n)}"></button>`
  ).join("");
}

/* ---- actions ---- */
async function toast(msg) { /* simple status flash */
  document.getElementById("statusText").textContent = "STATUS: " + msg;
}

document.addEventListener("click", async (e) => {
  const api = await getApi();
  if (!api) return;
  const pushBtn = e.target.closest("[data-push]");
  if (pushBtn) {
    await toast("pushing…");
    const res = await api.backup_now(pushBtn.dataset.push);
    const first = (res.results || [])[0];
    await toast(first ? (first.ok ? "pushed ✓" : "failed ✗") : (res.error || "done"));
    refresh();
    return;
  }
  const addTime = e.target.closest("[data-add-time]");
  if (addTime) {
    const repo = addTime.dataset.addTime;
    const input = document.querySelector(`input.time[data-repo="${repo}"]`);
    await api.add_schedule(repo, input ? input.value : "18:00");
    refresh();
    return;
  }
  const chip = e.target.closest("[data-time]");
  if (chip) {
    await api.remove_schedule(chip.dataset.repo, chip.dataset.time);
    refresh();
    return;
  }
  const themeBtn = e.target.closest("[data-theme-name]");
  if (themeBtn) {
    const res = await api.set_theme(themeBtn.dataset.themeName);
    if (!res.error) { document.documentElement.dataset.theme = res.theme; currentTheme = res.theme; refresh(); }
    return;
  }
});

document.getElementById("btnAddRepo").addEventListener("click", async () => {
  const api = await getApi();
  if (!api) return;
  const res = await api.add_repo();
  await toast(res.ok ? "repo added ✓" : (res.error || "canceled"));
  refresh();
});

document.getElementById("btnBackupAll").addEventListener("click", async () => {
  const api = await getApi();
  if (!api) return;
  await toast("pushing all…");
  const res = await api.backup_now("all");
  const failed = (res.results || []).filter((r) => !r.ok).length;
  await toast(failed ? `${failed} failed ✗` : "all pushed ✓");
  refresh();
});

document.getElementById("btnPullAll").addEventListener("click", async () => {
  const api = await getApi();
  if (!api) return;
  await toast("pulling…");
  await api.pull_now("all");
  await toast("pulled ✓");
  refresh();
});

/* ---- boot + live log poll ---- */
refresh();
setInterval(refresh, 4000);
