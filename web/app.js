"use strict";

const TOKEN_KEY = "aion.interface.token";
const SNAPSHOT_KEY = "aion.interface.snapshot.v1";
const MONEY_KEY = "aion.interface.money.v1";
const COSTS_KEY = "aion.interface.costs.v1";
const HEALTH_KEY = "aion.interface.health.v1";
const TASKS_KEY = "aion.interface.tasks.v1";
const PROJECTS_KEY = "aion.interface.projects.v1";
const QUEUE_KEY = "aion.interface.capture-queue.v1";
const SNAPSHOT_FIELDS = ["status", "blockers", "today"];

const byId = id => document.getElementById(id);
const state = { token: localStorage.getItem(TOKEN_KEY) || "", busy: false };

function toast(message) {
  const node = byId("toast");
  node.textContent = message;
  node.classList.add("show");
  setTimeout(() => node.classList.remove("show"), 2400);
}

function setConnection(online, label) {
  const node = byId("connection");
  node.className = `connection ${online ? "online" : "offline"}`;
  node.textContent = label || (online ? "Connected · live state" : "Offline · showing saved state");
}

function storedJSON(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) || fallback; } catch (_) { return fallback; }
}

async function api(path, options = {}) {
  const headers = { Authorization: `Bearer ${state.token}`, ...(options.headers || {}) };
  if (options.body) headers["Content-Type"] = "application/json";
  const response = await fetch(path, { ...options, headers, cache: "no-store" });
  const payload = await response.json().catch(() => ({}));
  if (response.status === 401) throw new Error("unauthorized");
  if (!response.ok) throw new Error(payload.error || `request failed (${response.status})`);
  return payload.data;
}

function showDashboard() {
  byId("unlock").hidden = true;
  byId("dashboard").hidden = false;
}

function relativeTime(iso) {
  const diffSec = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (diffSec < 10) return "just now";
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.round(diffSec / 60);
  if (diffMin < 60) return `${diffMin} minute${diffMin === 1 ? "" : "s"} ago`;
  const diffHour = Math.round(diffMin / 60);
  if (diffHour < 24) return `${diffHour} hour${diffHour === 1 ? "" : "s"} ago`;
  return new Date(iso).toLocaleString();
}

function renderSnapshot(snapshot) {
  SNAPSHOT_FIELDS.forEach(field => {
    if (typeof snapshot[field] === "string") byId(field).textContent = snapshot[field];
  });
  if (snapshot.asOf) byId("as-of").textContent = `Updated ${relativeTime(snapshot.asOf)}`;
}

function renderApprovals(rows) {
  const root = byId("approvals");
  root.replaceChildren();
  rows.forEach(row => {
    const card = document.createElement("article");
    card.className = "approval";
    const title = document.createElement("strong");
    title.textContent = `${row.approval_id} · ${row.action}`;
    const detail = document.createElement("p");
    detail.className = "muted";
    detail.textContent = `Why: ${row.why} · Cost: ${row.cost} · Maximum downside: ${row.max_downside}`;
    const actions = document.createElement("div");
    actions.className = "approval-actions";
    ["APPROVE", "DENY"].forEach(verb => {
      const button = document.createElement("button");
      button.className = verb === "APPROVE" ? "approve" : "deny";
      button.textContent = verb === "APPROVE" ? "Approve" : "Deny";
      button.addEventListener("click", () => decide(verb, row.approval_id, row.action));
      actions.append(button);
    });
    card.append(title, detail, actions);
    root.append(card);
  });
}

function formatInr(amount) {
  const rounded = Math.round(amount);
  const sign = rounded < 0 ? "−" : "";
  return `${sign}₹${new Intl.NumberFormat("en-IN").format(Math.abs(rounded))}`;
}

function renderMoney(split) {
  const net = byId("money-net");
  net.textContent = formatInr(split.real.net_inr);
  net.classList.toggle("negative", split.real.net_inr < 0);
  byId("money-sub").textContent =
    `Revenue ${formatInr(split.real.revenue_inr)} · Cost ${formatInr(split.real.cost_inr)}`;
}

function budgetLabel(pct) {
  if (pct >= 95) return "Stopped";
  if (pct >= 70) return "Nearly at limit";
  if (pct >= 50) return "Slowing down";
  return "On track";
}

function renderBudget(costs) {
  const pct = Math.max(0, Math.min(100, costs.strong_model_pct));
  const fill = byId("budget-fill");
  fill.style.width = `${pct}%`;
  fill.classList.toggle("warn", pct >= 50 && pct < 85);
  fill.classList.toggle("critical", pct >= 85);
  byId("budget-label").textContent = `Spending: ${budgetLabel(pct)}`;
}

function renderHealth(snapshot) {
  const dot = byId("health-dot");
  const text = byId("health-text");
  dot.classList.toggle("good", snapshot.healthy && !snapshot.paused);
  dot.classList.toggle("bad", !snapshot.healthy && !snapshot.paused);
  if (snapshot.paused) {
    text.textContent = "Paused — nothing is running right now.";
  } else if (snapshot.healthy) {
    text.textContent = "Everything's running normally.";
  } else {
    text.textContent = `Needs attention — ${snapshot.bottleneck}.`;
  }
}

function renderTasks(rows) {
  const root = byId("tasks");
  root.replaceChildren();
  if (!rows.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "Nothing queued right now.";
    root.append(empty);
    return;
  }
  rows.forEach(row => {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = row.title;
    const detail = document.createElement("p");
    detail.className = "task-detail";
    detail.textContent = `${row.task_id} · value ${row.value}` +
      (row.next_action ? ` → ${row.next_action}` : "");
    details.append(summary, detail);
    root.append(details);
  });
}

function renderProjects(rows) {
  const root = byId("projects");
  root.replaceChildren();
  if (!rows.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No projects yet.";
    root.append(empty);
    return;
  }
  rows.forEach(row => {
    const card = document.createElement("article");
    card.className = "project";
    const head = document.createElement("div");
    head.className = "project-head";
    const title = document.createElement("strong");
    title.textContent = row.project;
    const open = document.createElement("span");
    open.className = "project-open";
    open.textContent = `${row.open_tasks} open`;
    head.append(title, open);
    const net = document.createElement("p");
    net.className = "project-net";
    net.classList.toggle("negative", row.real_net_inr < 0);
    net.textContent = `Real net ${formatInr(row.real_net_inr)}`;
    const sim = document.createElement("p");
    sim.className = "muted";
    sim.textContent = row.simulated_net_inr
      ? `Simulated ${formatInr(row.simulated_net_inr)}`
      : "No simulated figures";
    card.append(head, net, sim);
    root.append(card);
  });
}

async function decide(verb, id, action) {
  const question = verb === "APPROVE" ? "Approve this?" : "Deny this?";
  if (!confirm(`${question}\n\n${action}`)) return;
  try {
    const answer = await api("/api/command", { method: "POST", body: JSON.stringify({ message: `${verb} ${id}` }) });
    toast(answer.split("\n")[0]);
    await refresh();
  } catch (error) {
    toast(error.message === "unauthorized"
      ? "That token didn't work — reconnect this device"
      : "Couldn't send that — check your connection and try again");
  }
}

async function refresh() {
  if (!state.token || state.busy) return;
  state.busy = true;
  try {
    const names = [...SNAPSHOT_FIELDS, "approvals"];
    const [values, moneySplit, costs, health, rankedTasks, projectRows] = await Promise.all([
      Promise.all(names.map(name => api(`/api/${name}`))),
      api("/api/v1/money"),
      api("/api/v1/costs"),
      api("/api/v1/snapshot"),
      api("/api/v1/tasks"),
      api("/api/v1/projects"),
    ]);
    const live = Object.fromEntries(names.map((name, index) => [name, values[index]]));
    live.asOf = new Date().toISOString();
    renderSnapshot(live);
    renderApprovals(live.approvals);
    renderMoney(moneySplit);
    renderBudget(costs);
    renderHealth(health);
    renderTasks(rankedTasks);
    renderProjects(projectRows);
    localStorage.setItem(SNAPSHOT_KEY, JSON.stringify(Object.fromEntries(
      [...SNAPSHOT_FIELDS, "asOf"].map(name => [name, live[name]])
    )));
    localStorage.setItem(MONEY_KEY, JSON.stringify(moneySplit));
    localStorage.setItem(COSTS_KEY, JSON.stringify(costs));
    localStorage.setItem(HEALTH_KEY, JSON.stringify(health));
    localStorage.setItem(TASKS_KEY, JSON.stringify(rankedTasks));
    localStorage.setItem(PROJECTS_KEY, JSON.stringify(projectRows));
    setConnection(true);
    await flushQueue();
  } catch (error) {
    if (error.message === "unauthorized") {
      stopAutoRefresh();
      localStorage.removeItem(TOKEN_KEY); state.token = "";
      byId("unlock").hidden = false; byId("dashboard").hidden = true;
      setConnection(false, "Token rejected · reconnect this device");
    } else setConnection(false);
  } finally { state.busy = false; }
}

const AUTO_REFRESH_MS = 60000;
let autoRefreshTimer = null;

function startAutoRefresh() {
  stopAutoRefresh();
  autoRefreshTimer = setInterval(() => { if (!document.hidden) refresh(); }, AUTO_REFRESH_MS);
}
function stopAutoRefresh() {
  if (autoRefreshTimer) clearInterval(autoRefreshTimer);
  autoRefreshTimer = null;
}

function captureQueue() { return storedJSON(QUEUE_KEY, []); }
function showQueue() {
  const count = captureQueue().length;
  byId("queue-count").textContent = count ? `${count} capture${count === 1 ? "" : "s"} waiting to sync.` : "";
}

async function flushQueue() {
  const queue = captureQueue();
  while (queue.length) {
    await api("/api/command", { method: "POST", body: JSON.stringify({ message: `[${queue[0].kind}] ${queue[0].text}` }) });
    queue.shift(); localStorage.setItem(QUEUE_KEY, JSON.stringify(queue)); showQueue();
  }
}

byId("token-form").addEventListener("submit", event => {
  event.preventDefault(); state.token = byId("token").value.trim();
  localStorage.setItem(TOKEN_KEY, state.token); showDashboard(); refresh(); startAutoRefresh();
});
byId("capture-form").addEventListener("submit", async event => {
  event.preventDefault();
  const text = byId("capture").value.trim();
  const kind = new FormData(event.currentTarget).get("kind");
  const queue = captureQueue(); queue.push({ kind, text, at: new Date().toISOString() });
  localStorage.setItem(QUEUE_KEY, JSON.stringify(queue)); event.currentTarget.reset(); showQueue();
  toast("Saved on this device");
  try { await flushQueue(); toast("Added to AION"); } catch (_) { setConnection(false); }
});
byId("refresh").addEventListener("click", refresh);
byId("forget").addEventListener("click", () => {
  localStorage.removeItem(TOKEN_KEY); state.token = ""; location.reload();
});

renderSnapshot(storedJSON(SNAPSHOT_KEY, {})); showQueue();
const cachedMoney = storedJSON(MONEY_KEY, null);
if (cachedMoney) renderMoney(cachedMoney);
const cachedCosts = storedJSON(COSTS_KEY, null);
if (cachedCosts) renderBudget(cachedCosts);
const cachedHealth = storedJSON(HEALTH_KEY, null);
if (cachedHealth) renderHealth(cachedHealth);
const cachedTasks = storedJSON(TASKS_KEY, null);
if (cachedTasks) renderTasks(cachedTasks);
const cachedProjects = storedJSON(PROJECTS_KEY, null);
if (cachedProjects) renderProjects(cachedProjects);
if (state.token) { showDashboard(); refresh(); startAutoRefresh(); }
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/service-worker.js").catch(() => {});

// Catch up immediately when the phone comes back to the foreground, rather
// than waiting up to a minute for the next scheduled refresh.
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && state.token) refresh();
});

// Keep "Updated Xs ago" honest between refreshes without hitting the network.
setInterval(() => {
  const cached = storedJSON(SNAPSHOT_KEY, {});
  if (cached.asOf && !byId("dashboard").hidden) {
    byId("as-of").textContent = `Updated ${relativeTime(cached.asOf)}`;
  }
}, 15000);
