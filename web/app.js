"use strict";

const TOKEN_KEY = "aion.interface.token";
const SNAPSHOT_KEY = "aion.interface.snapshot.v1";
const QUEUE_KEY = "aion.interface.capture-queue.v1";
const SNAPSHOT_FIELDS = ["money", "status", "blockers", "today", "tasks"];

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

function renderSnapshot(snapshot) {
  SNAPSHOT_FIELDS.forEach(field => {
    if (typeof snapshot[field] === "string") byId(field).textContent = snapshot[field];
  });
  if (snapshot.asOf) byId("as-of").textContent = `Last successful refresh: ${new Date(snapshot.asOf).toLocaleString()}`;
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

async function decide(verb, id, action) {
  if (!confirm(`${verb === "APPROVE" ? "Approve" : "Deny"} ${id}?\n\n${action}`)) return;
  try {
    const answer = await api("/api/command", { method: "POST", body: JSON.stringify({ message: `${verb} ${id}` }) });
    toast(answer.split("\n")[0]);
    await refresh();
  } catch (error) { toast(error.message === "unauthorized" ? "Token rejected" : "Could not send decision"); }
}

async function refresh() {
  if (!state.token || state.busy) return;
  state.busy = true;
  try {
    const names = [...SNAPSHOT_FIELDS, "approvals"];
    const values = await Promise.all(names.map(name => api(`/api/${name}`)));
    const live = Object.fromEntries(names.map((name, index) => [name, values[index]]));
    live.asOf = new Date().toISOString();
    renderSnapshot(live);
    renderApprovals(live.approvals);
    localStorage.setItem(SNAPSHOT_KEY, JSON.stringify(Object.fromEntries(
      [...SNAPSHOT_FIELDS, "asOf"].map(name => [name, live[name]])
    )));
    setConnection(true);
    await flushQueue();
  } catch (error) {
    if (error.message === "unauthorized") {
      localStorage.removeItem(TOKEN_KEY); state.token = "";
      byId("unlock").hidden = false; byId("dashboard").hidden = true;
      setConnection(false, "Token rejected · reconnect this device");
    } else setConnection(false);
  } finally { state.busy = false; }
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
  localStorage.setItem(TOKEN_KEY, state.token); showDashboard(); refresh();
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
if (state.token) { showDashboard(); refresh(); }
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/service-worker.js").catch(() => {});
