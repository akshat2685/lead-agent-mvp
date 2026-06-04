const stateUrl = "/api/state";

function fmtTime(seconds) {
  if (!seconds) return "-";
  return new Date(seconds * 1000).toLocaleString();
}

async function post(url) {
  const res = await fetch(url, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  await load();
}

function countWhere(items, fn) {
  return items.filter(fn).length;
}

function renderApprovalList(rootId, approvals, emptyText) {
  const root = document.querySelector(rootId);
  const pending = approvals.filter((a) => a.status === "pending");
  if (!pending.length) {
    root.innerHTML = `<div class="empty">${emptyText}</div>`;
    return;
  }
  root.innerHTML = pending
    .map(
      (a) => `
      <article class="approval">
        <strong>${a.lead_name} - ${a.lead_priority} (${a.lead_score})</strong>
        <p>${a.reason}</p>
        <div class="row">
          <button class="primary" onclick="post('/api/approvals/${a.id}/approve')">${a.action === "research_contact" ? "Approve research" : "Approve call"}</button>
          <button class="danger" onclick="post('/api/approvals/${a.id}/reject')">Reject</button>
        </div>
      </article>`
    )
    .join("");
}

function renderApprovals(approvals) {
  renderApprovalList("#callApprovals", approvals.filter((a) => a.action === "call"), "No call-ready approvals.");
  renderApprovalList("#researchApprovals", approvals.filter((a) => a.action === "research_contact"), "No research tasks.");
}

function renderLeads(leads) {
  document.querySelector("#leadRows").innerHTML = leads
    .map(
      (lead) => `
      <tr>
        <td>
          <strong>${lead.name}</strong><br>
          <span>${lead.source} - ${lead.location}</span>
        </td>
        <td><span class="pill ${lead.priority}">${lead.priority}</span></td>
        <td>${lead.score}</td>
        <td>${lead.status}<br><span>${lead.contact_status}</span></td>
        <td>${lead.attempts}</td>
      </tr>`
    )
    .join("");
}

function renderEvents(events) {
  const root = document.querySelector("#events");
  if (!events.length) {
    root.innerHTML = '<div class="empty">No activity yet.</div>';
    return;
  }
  root.innerHTML = events
    .map(
      (event) => `
      <div class="event">
        <span>${fmtTime(event.created_at)}</span>
        <strong>${event.kind}</strong>
        <div>${event.message}</div>
      </div>`
    )
    .join("");
}

async function load() {
  const res = await fetch(stateUrl);
  const data = await res.json();
  const { leads, approvals, settings } = data;
  document.querySelector("#hotCount").textContent = countWhere(leads, (l) => l.priority === "Hot");
  document.querySelector("#approvalCount").textContent = countWhere(approvals, (a) => a.status === "pending");
  document.querySelector("#followUpCount").textContent = countWhere(leads, (l) => l.status === "follow_up");
  document.querySelector("#contactedCount").textContent = countWhere(leads, (l) => l.status === "contacted");
  document.querySelector("#statusLine").textContent = `Mode: ${settings.mode}; paused: ${settings.paused}`;
  document.querySelector("#pauseBtn").textContent = settings.paused === "true" ? "Resume" : "Pause";
  document.querySelector("#modeSelect").value = settings.mode;
  renderApprovals(approvals);
  renderLeads(leads);
  renderEvents(data.events);
}

document.querySelector("#runBtn").addEventListener("click", () => post("/api/agent/run"));
document.querySelector("#pauseBtn").addEventListener("click", async () => {
  const current = document.querySelector("#pauseBtn").textContent === "Resume";
  await post(`/api/settings?paused=${current ? "false" : "true"}`);
});
document.querySelector("#modeSelect").addEventListener("change", async (event) => {
  await post(`/api/settings?mode=${encodeURIComponent(event.target.value)}`);
});

load();
setInterval(load, 5000);
