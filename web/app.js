const stateUrl = "/api/state";
let latestData = { leads: [], approvals: [], events: [], settings: { mode: "approval", paused: "false" } };
let autoRefresh = true;

function fmtTime(seconds) {
  if (!seconds) return "-";
  return new Date(seconds * 1000).toLocaleString();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
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
        <strong>${escapeHtml(a.lead_name)} - ${escapeHtml(a.lead_priority)} (${escapeHtml(a.lead_score)})</strong>
        <p>${escapeHtml(a.reason)}</p>
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
  const query = document.querySelector("#leadSearch").value.trim().toLowerCase();
  const priority = document.querySelector("#priorityFilter").value;
  const filtered = leads.filter((lead) => {
    const searchText = `${lead.name} ${lead.source} ${lead.location} ${lead.status} ${lead.contact_status}`.toLowerCase();
    return (priority === "all" || lead.priority === priority) && (!query || searchText.includes(query));
  });
  document.querySelector("#leadFilterStatus").textContent =
    filtered.length === leads.length ? `Showing all ${leads.length} leads` : `Showing ${filtered.length} of ${leads.length} leads`;
  if (!filtered.length) {
    document.querySelector("#leadRows").innerHTML = '<tr><td colspan="5"><div class="empty">No leads match this filter.</div></td></tr>';
    return;
  }
  document.querySelector("#leadRows").innerHTML = leads
    .filter((lead) => filtered.includes(lead))
    .map(
      (lead) => `
      <tr>
        <td>
          <strong>${escapeHtml(lead.name)}</strong><br>
          <span>${escapeHtml(lead.source)} - ${escapeHtml(lead.location)}</span>
        </td>
        <td><span class="pill ${escapeHtml(lead.priority)}">${escapeHtml(lead.priority)}</span></td>
        <td>${escapeHtml(lead.score)}</td>
        <td>${escapeHtml(lead.status)}<br><span>${escapeHtml(lead.contact_status)}</span></td>
        <td>${escapeHtml(lead.attempts)}</td>
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
        <strong>${escapeHtml(event.kind)}</strong>
        <div>${escapeHtml(event.message)}</div>
      </div>`
    )
    .join("");
}

async function load() {
  const res = await fetch(stateUrl);
  const data = await res.json();
  latestData = data;
  const { leads, approvals, settings } = data;
  document.querySelector("#hotCount").textContent = countWhere(leads, (l) => l.priority === "Hot");
  document.querySelector("#approvalCount").textContent = countWhere(approvals, (a) => a.status === "pending");
  document.querySelector("#followUpCount").textContent = countWhere(leads, (l) => l.status === "follow_up");
  document.querySelector("#contactedCount").textContent = countWhere(leads, (l) => l.status === "contacted");
  document.querySelector("#statusLine").textContent = `Mode: ${settings.mode}; paused: ${settings.paused}`;
  document.querySelector("#modeChip").textContent = settings.mode;
  document.querySelector("#syncChip").textContent = settings.paused === "true" ? "paused" : "online";
  document.querySelector("#leadChip").textContent = leads.length;
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
document.querySelector("#leadSearch").addEventListener("input", () => renderLeads(latestData.leads));
document.querySelector("#priorityFilter").addEventListener("change", () => renderLeads(latestData.leads));
document.querySelector("#refreshToggle").addEventListener("click", () => {
  autoRefresh = !autoRefresh;
  document.querySelector("#refreshToggle").textContent = autoRefresh ? "Auto refresh on" : "Auto refresh off";
});

function startParticles() {
  const canvas = document.querySelector("#particleCanvas");
  const ctx = canvas.getContext("2d");
  const particles = [];
  const pointer = { x: window.innerWidth / 2, y: window.innerHeight / 2, active: false };
  const maxParticles = 90;

  function resize() {
    canvas.width = window.innerWidth * window.devicePixelRatio;
    canvas.height = window.innerHeight * window.devicePixelRatio;
    canvas.style.width = `${window.innerWidth}px`;
    canvas.style.height = `${window.innerHeight}px`;
    ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
  }

  function addParticle(x, y, boost = 1) {
    particles.push({
      x,
      y,
      vx: (Math.random() - 0.5) * 1.8 * boost,
      vy: (Math.random() - 0.5) * 1.8 * boost,
      life: 1,
      size: 1.5 + Math.random() * 3,
    });
    if (particles.length > maxParticles) particles.shift();
  }

  function draw() {
    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
    if (pointer.active && Math.random() > 0.35) addParticle(pointer.x, pointer.y);
    for (let i = particles.length - 1; i >= 0; i -= 1) {
      const p = particles[i];
      p.x += p.vx;
      p.y += p.vy;
      p.life -= 0.018;
      if (p.life <= 0) {
        particles.splice(i, 1);
        continue;
      }
      ctx.beginPath();
      ctx.fillStyle = `rgba(36, 233, 255, ${p.life * 0.7})`;
      ctx.shadowBlur = 18;
      ctx.shadowColor = "rgba(36, 233, 255, 0.8)";
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.shadowBlur = 0;
    requestAnimationFrame(draw);
  }

  window.addEventListener("resize", resize);
  window.addEventListener("pointermove", (event) => {
    pointer.x = event.clientX;
    pointer.y = event.clientY;
    pointer.active = true;
    addParticle(pointer.x, pointer.y, 1.8);
  });
  window.addEventListener("pointerleave", () => {
    pointer.active = false;
  });
  resize();
  draw();
}

load();
startParticles();
setInterval(() => {
  if (autoRefresh) load();
}, 5000);
