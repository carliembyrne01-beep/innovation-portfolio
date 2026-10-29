/* WSG Innovation Portfolio — plain JavaScript, no build step.
   Hash routes: #/  #/register  #/pipeline  #/matrix  #/alignment  #/i/INIT-0003?tab=scoring
                #/workshop  #/updates  #/actions  #/decisions  #/pack  #/import  #/framework */
"use strict";

// ------------------------------------------------------------------ helpers
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const fmtD = (iso) => { if (!iso) return "—"; const [y, m, d] = iso.slice(0, 10).split("-"); return `${+d} ${MON[+m - 1]} ${y}`; };
const dot = (c) => `<span class="dot ${c}"></span>`;
const HC = { Green: "green", "Green/Amber": "ga", Amber: "amber", "Amber/Red": "ar", Red: "red" };
const hcls = (h) => HC[h] || "grey";
const healthChip = (h) => `<span class="chip ${hcls(h)}">${dot(hcls(h))}${esc(h || "Grey")}</span>`;
const prio = (p) => p ? `<span class="prio ${esc(p)}">${esc(p)}</span>` : "—";
const dchip = (d) => `<span class="dchip ${esc(d)}">${esc(d)}</span>`;
const quadChip = (q) => q ? `<span class="chip ${q === "Big Bet" ? "dark" : q === "Quick Win" ? "green" : q === "Money Pit / Park" ? "red" : "outline"}">${esc(q)}</span>` : `<span class="chip grey">Not scored</span>`;
const tags = (list, primary = []) => (list || []).map((t) => `<span class="tag ${primary.includes(t) ? "primary" : ""}">${esc(t)}</span>`).join("");
const sec = (title, sub, extra = "") => `<div class="sec-head"><div class="t"><h2>${esc(title)}</h2></div>${sub ? `<p>${esc(sub)}</p>` : ""}${extra}</div>`;
const field = (label, inner, sub = "") => `<div class="field"><label>${esc(label)}${sub ? ` <span class="sub">${esc(sub)}</span>` : ""}</label>${inner}</div>`;
const opts = (list, value, blank = true) => (blank ? `<option value="">—</option>` : "") + list.map((o) => { const [v, l] = Array.isArray(o) ? o : [o, o]; return `<option value="${esc(v)}" ${v === value ? "selected" : ""}>${esc(l)}</option>`; }).join("");
const sel = (name, list, value, blank = true) => `<select name="${name}">${opts(list, value, blank)}</select>`;
const inp = (name, value = "", type = "text", extra = "") => `<input name="${name}" type="${type}" value="${esc(value ?? "")}" ${extra}>`;
const ta = (name, value = "", rows = 3, extra = "") => `<textarea name="${name}" rows="${rows}" ${extra}>${esc(value ?? "")}</textarea>`;
const stageLabel = (k) => (META.stages.find((s) => s.key === k) || {}).label || k || "—";
const stageMini = (idx) => `<span class="stage-mini" title="Stage ${idx + 1} of 5">${[0, 1, 2, 3, 4].map((n) => `<i class="${n < idx ? "on" : n === idx ? "cur" : ""}"></i>`).join("")}</span>`;
const todayISO = () => META.today;
const addDays = (iso, n) => { const d = new Date(iso + "T00:00:00"); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;

let META = null;
let CACHE = null; // initiative cards for search / workshop

async function api(method, url, body) {
  const r = await fetch(url, { method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
  let d = null;
  try { d = await r.json(); } catch { /* empty */ }
  if (!r.ok) {
    let msg = d?.message;
    if (!msg && Array.isArray(d?.detail)) msg = d.detail.map((e) => `${e.loc?.slice(-1)[0] || ""}: ${(e.msg || "").replace(/^Value error, /, "")}`).join("; ");
    throw new Error(msg || `Request failed (${r.status})`);
  }
  return d;
}
const GET = (u) => api("GET", u);

function toast(msg, err = false) {
  const t = document.createElement("div");
  t.className = "toast" + (err ? " err" : "");
  t.textContent = msg;
  $("#toast").appendChild(t);
  setTimeout(() => t.remove(), err ? 6000 : 3500);
}

async function refreshCache() { CACHE = await GET("/api/initiatives"); return CACHE; }

// Modal form. onSubmit gets the form values (checkbox groups named "x[]" become arrays).
function modal(title, bodyHtml, submitLabel, onSubmit, { wide = false, onOpen } = {}) {
  const root = $("#modal-root");
  root.innerHTML = `<div class="modal-bg"><form class="modal ${wide ? "wide" : ""}" novalidate><h3>${esc(title)}</h3><div class="m-body"><div class="form">${bodyHtml}</div></div>
    <div class="m-foot"><button type="button" class="btn" data-close>Cancel</button><button class="btn primary">${esc(submitLabel)}</button></div></form></div>`;
  const form = $("form", root);
  const close = () => (root.innerHTML = "");
  root.querySelector("[data-close]").onclick = close;
  root.querySelector(".modal-bg").addEventListener("mousedown", (e) => { if (e.target.classList.contains("modal-bg")) close(); });
  form.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
  form.onsubmit = async (e) => {
    e.preventDefault();
    const data = {};
    for (const [k, v] of new FormData(form).entries()) {
      if (k.endsWith("[]")) (data[k.slice(0, -2)] ||= []).push(v); else data[k] = v;
    }
    $$("input[type=checkbox]:not([name$='[]'])", form).forEach((c) => { data[c.name] = c.checked; });
    $$("input[type=checkbox][name$='[]']", form).forEach((c) => { data[c.name.slice(0, -2)] ||= []; });
    const btn = form.querySelector(".m-foot .primary");
    btn.disabled = true;
    try {
      const d = await onSubmit(data, form);
      close();
      if (d?.message) toast(d.message);
      await render();
    } catch (err) { toast(err.message, true); btn.disabled = false; }
  };
  if (onOpen) onOpen(form);
  const first = form.querySelector("input:not([type=radio]):not([type=checkbox]),select,textarea");
  if (first) first.focus();
}
const nul = (o) => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, v === "" ? null : v]));

// ------------------------------------------------------------------ navigation
const NAV = [
  ["View the portfolio", [["#/", "Overview"], ["#/register", "Register"], ["#/pipeline", "Stage pipeline"], ["#/matrix", "Value × complexity"], ["#/alignment", "Strategy alignment"]]],
  ["Run reviews", [["#/workshop", "Workshop mode"], ["#/actions", "Open actions"], ["#/updates", "Updates log"], ["#/decisions", "Decisions log"], ["#/pack", "Leadership pack"]]],
  ["Data", [["#/import", "Import & export"], ["#/framework", "How the framework works"]]],
];

function renderNav(route) {
  const base = "#/" + (route.parts[0] || "");
  $("#nav").innerHTML = NAV.map(([g, items]) => `<div class="nav-group">${g}</div>` + items.map(([href, label]) => {
    const on = href === base || (route.parts[0] === "i" && href === "#/register");
    return `<a href="${href}" class="${on ? "active" : ""}"><span class="lbl">${label}</span></a>`;
  }).join("")).join("") + `<div class="nav-foot"><button data-act="new-initiative">+ New initiative</button><a href="/docs" target="_blank" style="color:#94A3B8">API documentation ↗</a><span>Innovation Portfolio v${esc(META.version)}</span></div>`;
}

function parseRoute() {
  const h = location.hash.replace(/^#\/?/, "");
  const [path, qs] = h.split("?");
  return { parts: path.split("/").filter(Boolean), q: Object.fromEntries(new URLSearchParams(qs || "")) };
}
const setQuery = (q) => { const r = parseRoute(); const s = new URLSearchParams(Object.entries({ ...r.q, ...q }).filter(([, v]) => v !== "" && v != null)).toString(); history.replaceState(null, "", `#/${r.parts.join("/")}${s ? "?" + s : ""}`); };

// ------------------------------------------------------------------ shared pieces
function flagList(flags, max = 99) {
  if (!flags.length) return `<div class="flag">${dot("green")}<span>Nothing flagged</span></div>`;
  return flags.slice(0, max).map((f) => `<div class="flag">${dot(f.level)}<span>${esc(f.text)}</span></div>`).join("") + (flags.length > max ? `<div class="hint">+${flags.length - max} more</div>` : "");
}

function stageStrip(c, selected) {
  const idx = c.stage_index;
  return `<div class="stages s5">${META.stages.map((s, n) => {
    const cls = n < idx ? "done" : n === idx ? `current ${["red", "ar"].includes(c.health_class) ? "bad" : c.health_class === "green" ? "ok" : ""}` : "";
    return `<div class="stage ${cls} ${selected === n ? "sel" : ""}" data-act="stage-info" data-n="${n}"><div class="s-n">STAGE ${n + 1}</div><div class="s-l">${esc(s.label)}</div>
      <div class="s-st">${n < idx ? "Passed" : n === idx ? "Current" : "Ahead"}</div></div>`;
  }).join("")}</div>${idx < 0 ? `<div class="hint" style="margin-top:6px">Stage "${esc(c.stage || "none")}" isn't one of the five — use Edit to set it.</div>` : ""}`;
}

function stageGate(n) {
  const s = META.stages[n];
  if (!s) return "";
  return `<div class="card tight"><div class="card-title">Stage ${n + 1} · ${esc(s.label)}</div><div style="font-size:12.5px;margin-bottom:6px">${esc(s.objective)}</div>
    <div class="hint" style="margin-bottom:2px">Evidence expected before moving on:</div><ul style="margin:0;padding-left:18px;font-size:12px">${s.gate.map((g) => `<li>${esc(g)}</li>`).join("")}</ul></div>`;
}

function initiativeTable(rows, { compact = false } = {}) {
  if (!rows.length) return `<div class="card empty">Nothing matches.</div>`;
  return `<div class="card" style="padding:0"><div class="tbl-wrap"><table class="ops"><thead><tr>
    <th class="sortable" data-sort="id">ID</th><th class="sortable" data-sort="name">Initiative</th><th class="sortable" data-sort="stage_index">Stage</th>
    <th class="sortable" data-sort="health">Health</th><th class="sortable" data-sort="priority">Priority</th>${compact ? "" : `<th class="sortable" data-sort="owner">Owner</th>`}
    <th class="sortable" data-sort="quadrant">Quadrant</th>${compact ? "" : `<th class="sortable" data-sort="movement">Last movement</th><th class="sortable" data-sort="next_review_date">Next review</th>`}<th>Flags</th></tr></thead><tbody>
    ${rows.map((c) => `<tr class="click" data-href="#/i/${c.id}">
      <td class="mono nowrap small">${esc(c.id)}</td>
      <td><b>${esc(c.name)}</b>${compact ? "" : `<div class="desc">${esc(c.short_description)}</div>`}</td>
      <td class="nowrap">${stageMini(c.stage_index)} <span class="small">${esc(stageLabel(c.stage))}</span></td>
      <td>${healthChip(c.health)}</td><td>${prio(c.priority)}</td>
      ${compact ? "" : `<td class="small">${esc(c.owner || "—")}</td>`}
      <td>${quadChip(c.quadrant)}${c.value != null ? `<div class="hint mono">V${c.value} · C${c.complexity}</div>` : ""}</td>
      ${compact ? "" : `<td class="small nowrap">${esc(c.movement || "—")}<div class="hint">${fmtD(c.latest_update_date)}</div></td>
      <td class="small nowrap ${c.flags.some((f) => f.kind === "overdue") ? "" : ""}">${fmtD(c.next_review_date)}${c.flags.some((f) => f.kind === "overdue") ? `<div>${dot("red")} <span class="hint">overdue</span></div>` : ""}</td>`}
      <td class="nowrap"><span class="flagcount" title="${esc(c.flags.map((f) => f.text).join("\n"))}">${["red", "amber", "grey"].map((l) => { const n = c.flags.filter((f) => f.level === l).length; return n ? `${dot(l)}${n}` : ""; }).join(" ") || dot("green")}</span></td>
    </tr>`).join("")}</tbody></table></div></div>`;
}

const PRIO_ORDER = { Critical: 0, High: 1, Medium: 2, Low: 3 };
const HEALTH_ORDER = { Red: 0, "Amber/Red": 1, Amber: 2, "Green/Amber": 3, Green: 4, Grey: 5 };
function sortRows(rows, key, asc) {
  const val = (c) => key === "priority" ? PRIO_ORDER[c.priority] ?? 9 : key === "health" ? HEALTH_ORDER[c.health] ?? 9 : key === "quadrant" ? (c.value ?? -1) * 100 - (c.complexity ?? 0) : (c[key] ?? "");
  return [...rows].sort((a, b) => { const x = val(a), y = val(b); return (x < y ? -1 : x > y ? 1 : 0) * (asc ? 1 : -1); });
}

// ------------------------------------------------------------------ pages
const PAGES = {};

PAGES[""] = async () => {
  const d = await GET("/api/overview");
  if (!META.counts.initiatives) return emptyState();
  const maxStage = Math.max(1, ...d.by_stage.map((s) => s.items.length));
  const live = d.by_stage.reduce((a, s) => a + s.items.length, 0);
  return `
  <section>${sec("Portfolio overview", `Live from the register and updates log · ${fmtD(d.today)}`)}
    <div class="grid g4">${d.kpis.map((k) => `<div class="card tight kpi ${k.rag}" data-href="${k.link}" data-link="1"><div class="l">${esc(k.label)}</div><div class="v">${esc(k.value)}</div><div class="note">${esc(k.note)}</div></div>`).join("")}</div>
  </section>
  <section class="grid g-2-1">
    <div class="card"><div class="card-title"><span class="grow">Where initiatives sit in the stage-gate</span><a href="#/pipeline" class="small">Open pipeline →</a></div>
      ${d.by_stage.map((s, n) => `<div class="list-row" style="cursor:pointer" data-href="#/register?stage=${encodeURIComponent(s.key)}">
        <div style="width:150px" class="small"><span class="mono muted">${s.key === "other" ? "—" : n + 1}</span> <b>${esc(s.label)}</b></div>
        <div class="grow"><div class="bar" style="height:16px"><div style="width:${(s.items.length / maxStage) * 100}%;background:var(--wsg-black);display:flex"></div></div></div>
        <div class="mono" style="width:24px;text-align:right">${s.items.length}</div></div>`).join("")}
      <div class="grid g2" style="margin-top:14px">
        <div><div class="card-title">Health</div>${d.health.filter((h) => h.n).map((h) => `<div class="list-row" style="padding:4px 0;cursor:pointer" data-href="#/register?health=${encodeURIComponent(h.label)}">${healthChip(h.label)}<span class="grow"></span><span class="mono">${h.n}</span></div>`).join("")}</div>
        <div><div class="card-title">Quadrant <a class="small" href="#/matrix" style="margin-left:auto">matrix →</a></div>${d.quadrants.filter((q) => q.n).map((q) => `<div class="list-row" style="padding:4px 0;cursor:pointer" data-href="#/register?quadrant=${encodeURIComponent(q.label)}">${quadChip(q.label === "Not scored" ? null : q.label)}<span class="grow"></span><span class="mono">${q.n}</span></div>`).join("")}
          ${d.quadrants[1].n > live * 0.6 ? `<div class="hint" style="margin-top:6px">Most initiatives land in Big Bet at the current lines. <a href="#/matrix">Adjust the lines</a> to separate them.</div>` : ""}</div>
      </div>
    </div>
    <div class="card"><div class="card-title"><span class="grow">Needs attention</span></div>
      ${d.attention.length ? d.attention.map((c) => `<div class="list-row" style="cursor:pointer;align-items:flex-start" data-href="#/i/${c.id}">${dot(c.health_class)}<div class="grow"><b>${esc(c.name)}</b>
        <div class="hint">${prio(c.priority)} · ${esc(stageLabel(c.stage))} · ${esc(c.movement || "no update")}</div><div class="small" style="margin-top:2px">${esc(c.decision_needed || c.next_action || "")}</div></div></div>`).join("") : `<div class="empty">Nothing red, blocked or critical.</div>`}
    </div>
  </section>
  <section class="grid g2">
    <div class="card"><div class="card-title"><span class="grow">Latest updates</span><a href="#/updates" class="small">All updates →</a></div>
      ${d.recent_updates.map((u) => `<div class="list-row" style="cursor:pointer;align-items:flex-start" data-href="#/i/${u.initiative_id}?tab=updates"><span class="mono small muted" style="width:70px">${fmtD(u.update_date)}</span>
        <div class="grow"><b class="small">${esc(u.initiative_name)}</b> <span class="hint">· ${esc(u.update_type || "")} · ${esc(u.movement || "")}</span><div class="small desc" style="color:var(--ink-2)">${esc((u.summary || "").slice(0, 180))}${(u.summary || "").length > 180 ? "…" : ""}</div></div></div>`).join("") || `<div class="empty">No updates yet.</div>`}
    </div>
    <div class="card"><div class="card-title"><span class="grow">Recent decisions</span><a href="#/decisions" class="small">Decisions log →</a></div>
      ${d.recent_decisions.length ? d.recent_decisions.map((x) => `<div class="list-row" style="cursor:pointer" data-href="#/i/${x.initiative_id}?tab=decisions"><span class="mono small muted" style="width:70px">${fmtD(x.decision_date)}</span>${dchip(x.decision)}<div class="grow small"><b>${esc(x.initiative_name)}</b> ${x.stage_to !== x.stage_from ? `· ${esc(stageLabel(x.stage_from))} → ${esc(stageLabel(x.stage_to))}` : ""}</div></div>`).join("")
        : `<div class="empty">No decisions recorded yet. Use <a href="#/workshop">Workshop mode</a> in your next portfolio review to record Stop / Hold / Continue / Pivot / Scale.</div>`}
    </div>
  </section>`;
};

function emptyState() {
  return `<section class="card" style="padding:32px;text-align:center"><h2 class="display" style="margin:0 0 6px">No initiatives yet</h2>
    <p class="muted">Load your MS Lists exports, or start adding initiatives directly.</p>
    <div class="btn-row" style="justify-content:center;margin-top:12px"><a class="btn accent" href="#/import">Import from MS Lists</a><button class="btn" data-act="new-initiative">+ New initiative</button></div></section>`;
}

// ---- register
PAGES.register = async (r) => {
  const rows = await refreshCache();
  const q = r.q;
  const owners = [...new Set(rows.map((c) => c.owner).filter(Boolean))].sort();
  let f = rows.filter((c) => {
    if (q.q) { const s = q.q.toLowerCase(); if (![c.id, c.name, c.short_description, c.owner, c.sponsor, c.bucket].some((v) => (v || "").toLowerCase().includes(s))) return false; }
    if (q.stage && c.stage !== q.stage) return false;
    if (q.bucket && c.bucket !== q.bucket) return false;
    if (q.status && c.status !== q.status) return false;
    if (q.priority && c.priority !== q.priority) return false;
    if (q.owner && c.owner !== q.owner) return false;
    if (q.quadrant && (c.quadrant || "Not scored") !== q.quadrant) return false;
    if (q.health === "bad" ? !["Red", "Amber/Red"].includes(c.health) : q.health && (c.health || "Grey") !== q.health) return false;
    if (q.movement === "blocked" && !["Blocked", "Escalated"].includes(c.movement)) return false;
    if (q.movement === "capture" && c.movement !== "Needs capture") return false;
    if (q.flag === "overdue" && !c.flags.some((x) => x.kind === "overdue")) return false;
    if (q.flag === "owner" && !c.flags.some((x) => ["owner", "sponsor"].includes(x.kind))) return false;
    if (q.area && !c.business_areas.includes(q.area)) return false;
    return true;
  });
  f = sortRows(f, q.sort || "id", q.dir !== "desc");
  const fsel = (name, list, label) => `<select data-filter="${name}" aria-label="${label}"><option value="">${label}</option>${list.map((o) => { const [v, l] = Array.isArray(o) ? o : [o, o]; return `<option value="${esc(v)}" ${q[name] === v ? "selected" : ""}>${esc(l)}</option>`; }).join("")}</select>`;
  const special = { bad: "Red or Amber/Red", blocked: "Blocked or escalated", capture: "Needs capture", overdue: "Review overdue", owner: "Owner / sponsor to confirm" };
  return `<section>${sec("Initiative register", "Every non-BAU initiative in one list. Click a row to open it; use the filters or search to narrow down.",
      `<div class="btn-row" style="margin-top:8px"><button class="btn accent" data-act="new-initiative">+ New initiative</button><a class="btn" href="/api/export/register.csv">Export CSV</a></div>`)}
    <div class="filters">
      <input type="search" data-filter="q" placeholder="Search name, owner, description…" value="${esc(q.q || "")}">
      ${fsel("stage", META.stages.map((s) => [s.key, s.label]), "All stages")}
      ${fsel("health", [["bad", "Red or Amber/Red"], ...META.healths], "All health")}
      ${fsel("priority", META.priorities, "All priorities")}
      ${fsel("bucket", META.buckets, "All buckets")}
      ${fsel("status", META.statuses, "All statuses")}
      ${fsel("owner", owners, "All owners")}
      ${fsel("quadrant", [...META.quadrants, "Not scored"], "All quadrants")}
      ${q.movement || q.flag || q.area ? `<span class="chip info">${esc(special[q.movement] || special[q.flag] || q.area)} <a href="#" data-act="clear-special" style="margin-left:4px">×</a></span>` : ""}
      <span class="count">${f.length} of ${rows.length}</span>${Object.keys(q).some((k) => !["sort", "dir"].includes(k)) ? `<button class="btn sm" data-act="clear-filters">Clear</button>` : ""}
    </div></section>
  <section>${initiativeTable(f)}</section>`;
};

// ---- pipeline
PAGES.pipeline = async () => {
  const rows = (await refreshCache()).filter((c) => !["Stopped", "Closed / BAU"].includes(c.status));
  const cols = META.stages.map((s) => ({ ...s, items: rows.filter((c) => c.stage === s.key) }));
  const other = rows.filter((c) => c.stage_index < 0);
  if (other.length) cols.push({ key: "other", label: "Other / not set", items: other });
  const sorted = (items) => sortRows(items, "priority", true);
  return `<section>${sec("Stage pipeline", "Live initiatives by stage. Coloured edge = health. Click a card to open it.")}
    <div class="board ${other.length ? "extra" : ""}">${cols.map((col, n) => `<div class="col"><div class="col-h"><span>${col.key === "other" ? "" : `<span class="mono muted">${n + 1}</span> `}${esc(col.label)}</span><span class="n">${col.items.length}</span></div>
      ${sorted(col.items).map((c) => `<div class="icard ${c.health_class}" data-href="#/i/${c.id}"><div class="t">${esc(c.name)}</div>
        <div class="r">${prio(c.priority)}${c.quadrant ? `<span class="hint">· ${esc(c.quadrant)}</span>` : ""}</div>
        <div class="s">${esc(c.owner || "Owner not set")}</div>
        ${c.movement ? `<div class="s">${esc(c.movement)} · ${fmtD(c.latest_update_date)}</div>` : ""}</div>`).join("") || `<div class="empty">—</div>`}</div>`).join("")}</div></section>`;
};

// ---- matrix
PAGES.matrix = async (r) => {
  const rows = (await refreshCache()).filter((c) => c.value != null && !["Stopped", "Closed / BAU"].includes(c.status));
  const cuts = { ...META.cuts, ...(r.q.v ? { value_cut: +r.q.v } : {}), ...(r.q.c ? { complexity_cut: +r.q.c } : {}) };
  const quad = (c) => { const hv = c.value >= cuts.value_cut, hc = c.complexity >= cuts.complexity_cut; return hv && !hc ? "Quick Win" : hv && hc ? "Big Bet" : !hv && !hc ? "Filler / Enabler" : "Money Pit / Park"; };
  const W = 760, H = 560, P = 56;
  const x = (v) => P + (v / 10) * (W - P - 20), y = (v) => H - P - (v / 10) * (H - P - 20);
  // Spread points that share the same score so all are visible.
  const groups = {};
  rows.forEach((c) => (groups[`${c.complexity},${c.value}`] ||= []).push(c));
  const fill = { Red: "#DC2626", "Amber/Red": "#E8590C", Amber: "#D97706", "Green/Amber": "#A3B22E", Green: "#16A34A" };
  // Same score → lay the dots out in a small grid centred on that score.
  const num = (c) => +(c.id.match(/\d+/) || [0])[0];
  const pts = Object.values(groups).flatMap((g) => { const cols = Math.ceil(Math.sqrt(g.length)), rowsN = Math.ceil(g.length / cols), gap = 25;
    return sortRows(g, "id", true).map((c, k) => ({ c, cx: x(c.complexity) + ((k % cols) - (cols - 1) / 2) * gap, cy: y(c.value) + (Math.floor(k / cols) - (rowsN - 1) / 2) * gap })); });
  const cx = x(cuts.complexity_cut - 0.5), cy = y(cuts.value_cut - 0.5);
  const counts = META.quadrants.map((q) => [q, rows.filter((c) => quad(c) === q).length]);
  const changed = r.q.v || r.q.c;
  return `<section>${sec("Value × complexity", "Each dot is an initiative's active score: value (0–10) up, complexity (0–10) across. Dot colour = health. Drag the sliders to move the quadrant lines.")}
  <div class="matrix-wrap">
    <svg class="matrix" viewBox="0 0 ${W} ${H}" role="img" aria-label="Value versus complexity matrix">
      <rect x="${P}" y="20" width="${cx - P}" height="${cy - 20}" fill="#F0FDF4"/><rect x="${cx}" y="20" width="${W - 20 - cx}" height="${cy - 20}" fill="#FFFBEA"/>
      <rect x="${P}" y="${cy}" width="${cx - P}" height="${H - P - cy}" fill="#F8FAFC"/><rect x="${cx}" y="${cy}" width="${W - 20 - cx}" height="${H - P - cy}" fill="#FEF2F2"/>
      <text class="q-label" x="${P + 10}" y="40">Quick win</text><text class="q-label" x="${W - 30}" y="40" text-anchor="end">Big bet</text>
      <text class="q-label" x="${P + 10}" y="${H - P - 12}">Filler / enabler</text><text class="q-label" x="${W - 30}" y="${H - P - 12}" text-anchor="end">Money pit / park</text>
      ${[0, 2, 4, 6, 8, 10].map((v) => `<text x="${x(v)}" y="${H - P + 18}" text-anchor="middle" font-size="11" fill="#64748B">${v}</text><text x="${P - 10}" y="${y(v) + 4}" text-anchor="end" font-size="11" fill="#64748B">${v}</text>`).join("")}
      <line x1="${cx}" y1="20" x2="${cx}" y2="${H - P}" stroke="#231F20" stroke-dasharray="5 4"/><line x1="${P}" y1="${cy}" x2="${W - 20}" y2="${cy}" stroke="#231F20" stroke-dasharray="5 4"/>
      <rect x="${P}" y="20" width="${W - P - 20}" height="${H - P - 20}" fill="none" stroke="#E2E8F0"/>
      <text x="${(W + P) / 2}" y="${H - 14}" text-anchor="middle" font-size="12" font-weight="700" fill="#334155">COMPLEXITY →</text>
      <text transform="translate(16 ${(H - P) / 2}) rotate(-90)" text-anchor="middle" font-size="12" font-weight="700" fill="#334155">VALUE →</text>
      ${pts.map(({ c, cx: px, cy: py }) => `<g class="pt" data-href="#/i/${c.id}"><title>${esc(c.name)} — value ${c.value}, complexity ${c.complexity}, ${esc(c.health || "Grey")}</title>
        <circle cx="${px}" cy="${py}" r="11" fill="${fill[c.health] || "#94A3B8"}" stroke="#fff" stroke-width="2"/>
        <text x="${px}" y="${py + 4}" text-anchor="middle" style="fill:#fff;font-weight:700;font-size:10.5px">${num(c)}</text></g>`).join("")}
    </svg>
    <div class="grid" style="align-content:start">
      <div class="card"><div class="card-title">Quadrant lines</div>
        <div class="slider"><span style="width:110px">High value ≥</span><input type="range" min="1" max="10" value="${cuts.value_cut}" data-cut="v"><b>${cuts.value_cut}</b></div>
        <div class="slider"><span style="width:110px">High complexity ≥</span><input type="range" min="1" max="10" value="${cuts.complexity_cut}" data-cut="c"><b>${cuts.complexity_cut}</b></div>
        <div class="hint" style="margin:6px 0">Saved lines: value ≥ ${META.cuts.value_cut}, complexity ≥ ${META.cuts.complexity_cut}. These reproduce the quadrants already recorded in your scoring list.</div>
        ${changed ? `<div class="btn-row"><button class="btn primary sm" data-act="save-cuts" data-v="${cuts.value_cut}" data-c="${cuts.complexity_cut}">Save these lines</button><a class="btn sm" href="#/matrix">Reset</a></div>` : ""}
      </div>
      <div class="card"><div class="card-title">By quadrant · ${rows.length} scored</div>${counts.map(([q, n]) => `<div style="margin-bottom:8px"><div class="list-row" style="padding:4px 0;border:0">${quadChip(q)}<span class="grow"></span><span class="mono">${n}</span></div>
        ${sortRows(rows.filter((c) => quad(c) === q), "id", true).map((c) => `<div class="small" style="display:flex;gap:6px;padding:1px 0;cursor:pointer" data-href="#/i/${c.id}"><span class="mono muted" style="width:18px;text-align:right">${num(c)}</span>${dot(c.health_class)}<span>${esc(c.name)}</span><span class="hint mono" style="margin-left:auto">${c.value}·${c.complexity}</span></div>`).join("")}</div>`).join("")}</div>
      <div class="card"><div class="card-title">Reading it</div><div class="small">Numbers are initiative IDs (3 = INIT-0003). Scores are five value and five complexity factors, each 0–2; initiatives with the same score are grouped around that point. Hover a dot for details; click to open it.</div></div>
    </div>
  </div></section>`;
};

// ---- alignment heatmap
PAGES.alignment = async (r) => {
  const d = await GET("/api/alignment-map");
  const type = r.q.type === "vp" ? "Value Pocket" : "Strategic Priority";
  const inits = d.initiatives.filter((c) => !["Stopped", "Closed / BAU"].includes(c.status));
  const areas = d.areas[type];
  return `<section>${sec("Strategy alignment", "Which initiatives serve which strategic priorities and value pockets. Black = primary, gold = supporting.",
      `<div class="tabs" style="margin-top:10px"><button class="${type === "Strategic Priority" ? "on" : ""}" data-href="#/alignment">Strategic priorities</button><button class="${type === "Value Pocket" ? "on" : ""}" data-href="#/alignment?type=vp">Value pockets</button></div>`)}
    ${areas.length ? `<div class="card" style="overflow-x:auto"><table class="heat"><thead><tr><th></th>${inits.map((c) => `<th class="colh" data-href="#/i/${c.id}" title="${esc(c.name)}">${esc(c.name.length > 30 ? c.name.slice(0, 28) + "…" : c.name)}</th>`).join("")}<th class="colh" style="cursor:default">Primary / total</th></tr></thead><tbody>
      ${areas.map((a) => `<tr><th class="row">${esc(a.area)}</th>${inits.map((c) => { const role = a.links[c.id]; return `<td class="${role === "Primary" ? "P" : role ? "S" : ""}" title="${role ? esc(c.name + " — " + role) : ""}"></td>`; }).join("")}<td class="tot">${a.primary} / ${a.total}</td></tr>`).join("")}
    </tbody></table></div>
    <div class="grid g2"><div class="card"><div class="card-title">Gaps to look at</div>
      ${inits.filter((c) => !areas.some((a) => a.links[c.id])).map((c) => `<div class="list-row" data-href="#/i/${c.id}?tab=alignment" style="cursor:pointer">${dot("amber")}<span class="grow small"><b>${esc(c.name)}</b> has no ${type.toLowerCase()} linked</span></div>`).join("") || `<div class="empty">Every live initiative has at least one ${type.toLowerCase()}.</div>`}
      ${areas.filter((a) => !a.primary).map((a) => `<div class="list-row">${dot("grey")}<span class="grow small"><b>${esc(a.area)}</b> is only ever a supporting link</span></div>`).join("")}
    </div></div>` : `<div class="card empty">No ${type.toLowerCase()} links yet. Import the Alignment / Value Pockets list or add links on an initiative's Alignment tab.</div>`}
  </section>`;
};

// ---- initiative detail
PAGES.i = async (r) => {
  const c = await GET(`/api/initiatives/${encodeURIComponent(r.parts[1])}`);
  const tab = r.q.tab || "overview";
  const selStage = r.q.stage != null ? +r.q.stage : c.stage_index;
  const f = c.fields;
  const prim = c.priorities.filter((p) => p.role === "Primary").map((p) => p.area);
  const tabs = [["overview", "Overview"], ["scoring", "Scoring"], ["alignment", "Alignment"], ["updates", `Updates (${c.updates.length})`], ["decisions", `Decisions (${c.decisions.length})`], ["details", "All register fields"]];
  let body = "";
  if (tab === "overview") {
    body = `<div class="grid g-2-1"><div class="grid" style="align-content:start">
      <div class="card"><div class="card-title">What it is</div><div style="font-size:13px">${esc(c.short_description || "No description yet.")}</div></div>
      <div class="card"><div class="card-title"><span class="grow">Where it's at now</span><button class="btn sm accent" data-act="log-update" data-id="${c.id}">Log update</button></div>
        ${c.updates[0] ? `<div class="hint">${fmtD(c.updates[0].update_date)} · ${esc(c.updates[0].update_type || "")} · ${esc(c.movement || "")}</div><div style="font-size:13px;margin:4px 0 10px">${esc(c.latest_update_summary)}</div>` : `<div class="hint">No updates logged yet.</div>`}
        <dl class="kv"><dt>Decision needed</dt><dd class="pre">${esc(c.decision_needed || "—")}</dd><dt>Next action</dt><dd class="pre">${esc(c.next_action || "—")}</dd>
          <dt>Action owner</dt><dd>${esc(c.next_action_owner || "—")}${c.next_action_due ? ` · due ${fmtD(c.next_action_due)}` : ""}</dd></dl></div>
      <div class="card"><div class="card-title">Dependencies & related</div><div class="small pre">${esc(f.dependencies || "None recorded.")}</div>
        ${c.related.length ? `<div style="margin-top:8px">${c.related.map((x) => x.id ? `<a class="tag" href="#/i/${x.id}" style="text-decoration:none;background:#FFF9C4">${esc(x.label)}</a>` : `<span class="tag">${esc(x.label)}</span>`).join("")}</div>` : ""}</div>
    </div><div class="grid" style="align-content:start">
      <div class="card"><div class="card-title">Flags</div>${flagList(c.flags)}</div>
      ${stageGate(selStage >= 0 ? selStage : 0)}
      <div class="card"><div class="card-title">Key facts</div><dl class="kv">
        <dt>Bucket</dt><dd>${esc(c.bucket || "—")}</dd><dt>Business areas</dt><dd>${tags(c.business_areas) || "—"}</dd>
        <dt>Route</dt><dd>${tags(c.routes) || "—"}</dd><dt>Value types</dt><dd>${tags(c.value_types) || "—"}</dd>
        <dt>Strategic fit</dt><dd>${tags(c.priorities.map((p) => p.area), prim) || "—"}</dd>
        <dt>Evidence</dt><dd>${esc(c.evidence_status || "—")}</dd><dt>Confidence</dt><dd>${esc(c.confidence || "—")}</dd>
        <dt>Funding ask</dt><dd>${esc(f.funding_ask || "—")}</dd><dt>Commercial decision</dt><dd>${esc(f.commercial_decision_required || "—")}</dd>
        <dt>Client impact</dt><dd>${esc(f.client_impact || "—")}</dd><dt>Platform link</dt><dd>${esc(f.integrated_platform_link || "—")}</dd>
        <dt>Last reviewed</dt><dd>${fmtD(c.last_reviewed_date)}</dd><dt>Next review</dt><dd>${fmtD(c.next_review_date)}</dd></dl></div>
    </div></div>`;
  } else if (tab === "scoring") {
    const s = c.score;
    const rowsFor = (labels, kind) => Object.entries(labels).map(([k, l]) => `<div class="score-row"><span>${esc(l)}</span><span class="pips">${[1, 2].map((n) => `<i class="${(s?.[k] ?? 0) >= n ? "on " + kind : ""}"></i>`).join("")} <span class="mono small" style="width:14px;text-align:right">${s?.[k] ?? "–"}</span></span></div>`).join("");
    const money = s && ["est_one_off_cost_aud", "est_annual_run_cost_aud", "est_annual_benefit_aud", "est_revenue_uplift_aud", "est_cost_avoidance_aud", "est_roi_percent", "est_payback_months", "hours_saved_per_month"].some((k) => s[k] != null);
    body = s ? `<div class="btn-row" style="margin-bottom:12px"><button class="btn accent" data-act="score" data-id="${c.id}">Re-score</button><span class="hint">Active score from ${fmtD(s.score_date)} · ${esc(s.scored_by || "")} · confidence ${esc(s.confidence || "—")}${s.review_required ? " · marked for review" : ""}</span></div>
      <div class="score-grid">
        <div class="card"><div class="card-title"><span class="grow">Value</span><span class="total-big">${s.value_total}<span class="hint"> / 10</span></span></div>${rowsFor(META.value_labels, "v")}<div class="small" style="margin-top:10px">${esc(s.value_rationale || "")}</div></div>
        <div class="card"><div class="card-title"><span class="grow">Complexity</span><span class="total-big">${s.complexity_total}<span class="hint"> / 10</span></span></div>${rowsFor(META.complexity_labels, "c")}<div class="small" style="margin-top:10px">${esc(s.complexity_rationale || "")}</div></div>
      </div>
      <div class="card" style="margin-top:12px"><div class="card-title">Quadrant</div>${quadChip(s.quadrant)} ${s.recorded_quadrant && s.recorded_quadrant !== s.quadrant ? `<span class="hint">Recorded in the list as ${esc(s.recorded_quadrant)}</span>` : ""}
        ${s.notes ? `<div class="small" style="margin-top:6px">${esc(s.notes)}</div>` : ""}</div>
      <div class="card" style="margin-top:12px"><div class="card-title">Tangible value (cost / benefit)</div>${money ? `<dl class="kv">${[["est_one_off_cost_aud", "One-off cost $"], ["est_annual_run_cost_aud", "Annual run cost $"], ["est_annual_benefit_aud", "Annual benefit $"], ["est_revenue_uplift_aud", "Revenue uplift $"], ["est_cost_avoidance_aud", "Cost avoidance $"], ["est_roi_percent", "ROI %"], ["est_payback_months", "Payback (months)"], ["hours_saved_per_month", "Hours saved / month"]].filter(([k]) => s[k] != null).map(([k, l]) => `<dt>${l}</dt><dd class="mono">${(+s[k]).toLocaleString("en-AU")}</dd>`).join("")}</dl>` : `<div class="hint">${esc(s.tangible_notes || "Not assessed yet — tangible fields are for later business-case work.")}</div>`}</div>
      ${c.score_history.length > 1 ? `<div class="card" style="margin-top:12px"><div class="card-title">Score history</div><table class="ops"><thead><tr><th>Date</th><th>By</th><th class="num">Value</th><th class="num">Complexity</th><th>Quadrant</th><th>Active</th></tr></thead><tbody>${c.score_history.map((h) => `<tr><td class="mono small">${fmtD(h.score_date)}</td><td class="small">${esc(h.scored_by || "")}</td><td class="num">${h.value_total}</td><td class="num">${h.complexity_total}</td><td>${quadChip(h.quadrant)}</td><td>${h.active ? "✓" : ""}</td></tr>`).join("")}</tbody></table></div>` : ""}`
      : `<div class="card empty">Not scored yet.<div style="margin-top:10px"><button class="btn accent" data-act="score" data-id="${c.id}">Score it now</button></div></div>`;
  } else if (tab === "alignment") {
    const live = c.alignments.filter((a) => a.active);
    const block = (type) => { const list = live.filter((a) => a.alignment_type === type); return `<div class="card"><div class="card-title"><span class="grow">${type === "Strategic Priority" ? "Strategic priorities" : "Value pockets"}</span><button class="btn sm" data-act="add-align" data-id="${c.id}" data-type="${type}">+ Add</button></div>
      ${list.length ? list.map((a) => `<div class="list-row"><span class="tag ${a.role === "Primary" ? "primary" : ""}">${esc(a.role || "Supporting")}</span><span class="grow">${esc(a.area)}</span><button class="btn sm" data-act="rm-align" data-aid="${esc(a.id)}" title="Remove">×</button></div>`).join("") : `<div class="hint">None linked.</div>`}</div>`; };
    body = `<div class="grid g2">${block("Strategic Priority")}${block("Value Pocket")}</div>${f.strategic_alignment_text ? `<div class="hint" style="margin-top:10px">Register text: ${esc(f.strategic_alignment_text)}</div>` : ""}`;
  } else if (tab === "updates") {
    body = `<div class="btn-row" style="margin-bottom:12px"><button class="btn accent" data-act="log-update" data-id="${c.id}">Log update</button><span class="hint">Newest first. Faded = superseded by a later update. Orange boxes are working notes (not for the leadership pack).</span></div>
      <div class="card">${c.updates.length ? c.updates.map(updateEntry).join("") : `<div class="empty">No updates logged yet.</div>`}</div>`;
  } else if (tab === "decisions") {
    body = `<div class="btn-row" style="margin-bottom:12px"><button class="btn primary" data-act="decide" data-id="${c.id}">Record decision</button></div>
      <div class="card">${c.decisions.length ? `<table class="ops"><thead><tr><th>Date</th><th>Decision</th><th>Stage</th><th>Rationale</th><th>Conditions / follow-up</th><th>By</th></tr></thead><tbody>${c.decisions.map((x) => `<tr><td class="mono small nowrap">${fmtD(x.decision_date)}</td><td>${dchip(x.decision)}</td><td class="small nowrap">${x.stage_to !== x.stage_from ? `${esc(stageLabel(x.stage_from))} → <b>${esc(stageLabel(x.stage_to))}</b>` : esc(stageLabel(x.stage_to))}</td><td class="small">${esc(x.rationale || "")}</td><td class="small">${esc(x.conditions || "")}</td><td class="small">${esc(x.decided_by || "")}${x.forum ? `<div class="hint">${esc(x.forum)}</div>` : ""}</td></tr>`).join("")}</tbody></table>` : `<div class="empty">No decisions recorded yet.</div>`}</div>`;
  } else {
    const rows = [["Initiative ID", f.id], ["Name", f.name], ["Short description", f.short_description], ["Primary owner", f.primary_owner], ["Sponsor / exec lead", f.sponsor], ["Business area", (f.business_areas || []).join("; ")], ["Portfolio bucket", f.portfolio_bucket], ["Primary route", (f.primary_route || []).join("; ")], ["Current stage", f.stage], ["Value type", (f.value_types || []).join("; ")], ["Portfolio status", f.portfolio_status], ["Priority", f.priority], ["Overall health", f.health], ["Decision needed", f.decision_needed], ["Next action", f.next_action], ["Next action owner", f.next_action_owner], ["Next review date", fmtD(f.next_review_date)], ["Last reviewed date", fmtD(f.last_reviewed_date)], ["Evidence status", f.evidence_status], ["Dependencies", f.dependencies], ["WSG strategic priority alignment", f.strategic_alignment_text], ["Comments", f.comments], ["Confidence level", f.confidence], ["Integrated Platform link", f.integrated_platform_link], ["Commercial decision required", f.commercial_decision_required], ["Client impact", f.client_impact], ["Funding / resource ask", f.funding_ask], ["Related initiatives", (f.related_initiatives || []).join("; ")]];
    body = `<div class="btn-row" style="margin-bottom:12px"><button class="btn" data-act="edit" data-id="${c.id}">Edit</button><span class="hint">Exactly as held in the register. "Decision needed", "Next action" and "Comments" still carry the dated history from MS Lists; new entries go in the updates log.</span></div>
      <div class="card"><dl class="kv">${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd class="pre">${esc(v || "—")}</dd>`).join("")}</dl></div>`;
  }
  return `<section><div class="job-head"><div><div class="id"><a href="#/register">Register</a> / ${esc(c.id)}</div><h1>${esc(c.name)}</h1>
      <div class="btn-row" style="margin:4px 0">${healthChip(c.health)} ${prio(c.priority)} <span class="chip outline">${esc(c.status || "No status")}</span> ${quadChip(c.quadrant)} ${c.bucket ? `<span class="hint">${esc(c.bucket)}</span>` : ""}</div>
      <div class="meta">Owner <b>${esc(c.owner || "not set")}</b> · Sponsor <b>${esc(c.sponsor || "not set")}</b></div></div>
    <div class="right"><div class="btn-row"><button class="btn accent" data-act="log-update" data-id="${c.id}">Log update</button><button class="btn primary" data-act="decide" data-id="${c.id}">Record decision</button></div>
      <div class="btn-row"><button class="btn sm" data-act="score" data-id="${c.id}">${c.score ? "Re-score" : "Score"}</button><button class="btn sm" data-act="edit" data-id="${c.id}">Edit details</button><a class="btn sm" href="#/workshop?start=${c.id}">Workshop view</a></div></div></div></section>
  <section>${stageStrip(c, selStage)}</section>
  <section><div class="tabs">${tabs.map(([k, l]) => `<button class="${k === tab ? "on" : ""}" data-act="tab" data-tab="${k}">${l}</button>`).join("")}</div>${body}</section>`;
};

function updateEntry(u) {
  return `<div class="upd ${esc(u.update_type || "")} ${u.action_status === "Superseded" ? "superseded" : ""}"><div class="h"><span class="d">${fmtD(u.update_date)}</span><span>${esc(u.update_type || "")}</span>
      ${u.movement ? `<span>· ${esc(u.movement)}</span>` : ""}${u.health ? healthChip(u.health) : ""}${u.action_status ? `<span class="chip ${u.action_status === "Open" ? "info" : "grey"}">${esc(u.action_status)}</span>` : ""}
      ${u.include_in_md_update ? `<span class="chip outline">MD update</span>` : ""}${u.confidential ? `<span class="chip amber">Working only</span>` : ""}</div>
    <div class="b pre">${esc(u.summary || "")}</div>
    ${u.decision_needed ? `<div class="small"><b>Decision needed:</b> ${esc(u.decision_needed)}</div>` : ""}
    ${u.next_action ? `<div class="na"><b>Next:</b> ${esc(u.next_action)}${u.next_action_owner ? ` <span class="muted">— ${esc(u.next_action_owner)}</span>` : ""}${u.due_date ? ` <span class="muted">· due ${fmtD(u.due_date)}</span>` : ""}</div>` : ""}
    ${u.working_notes ? `<div class="wn">${esc(u.working_notes)}</div>` : ""}</div>`;
}

// ---- workshop mode
PAGES.workshop = async (r) => {
  const all = await refreshCache();
  const set = r.q.set || "live";
  const sets = {
    live: ["All live", (c) => !["Stopped", "Closed / BAU"].includes(c.status)],
    attention: ["Red, blocked or critical", (c) => ["Red", "Amber/Red"].includes(c.health) || ["Blocked", "Escalated"].includes(c.movement) || c.priority === "Critical"],
    due: ["Review due", (c) => c.flags.some((f) => f.kind === "overdue") || (c.next_review_date && c.next_review_date <= addDays(todayISO(), 14))],
    capture: ["Needs capture", (c) => c.movement === "Needs capture" || c.stage_index <= 0],
  };
  const list = sortRows(all.filter(sets[set][1]), "priority", true);
  if (!list.length) return `<section>${sec("Workshop mode", "")}<div class="card empty">No initiatives in this set.</div></section>`;
  const id = r.q.start && list.some((c) => c.id === r.q.start) ? r.q.start : list[0].id;
  const pos = list.findIndex((c) => c.id === id);
  const c = await GET(`/api/initiatives/${id}`);
  const prev = list[pos - 1], next = list[pos + 1];
  const s = c.score;
  return `<section class="ws-bar no-print">
      <div class="tabs" style="margin:0;border:0">${Object.entries(sets).map(([k, [l]]) => `<button class="${k === set ? "on" : ""}" data-href="#/workshop?set=${k}">${l} (${all.filter(sets[k][1]).length})</button>`).join("")}</div>
      <span class="grow" style="flex:1"></span>
      <button class="btn" ${prev ? `data-href="#/workshop?set=${set}&start=${prev.id}"` : "disabled"}>← Previous</button>
      <span class="pos">${pos + 1} / ${list.length}</span>
      <button class="btn" ${next ? `data-href="#/workshop?set=${set}&start=${next.id}"` : "disabled"}>Next →</button>
    </section>
    <section class="ws">
      <div class="grid" style="align-content:start;gap:14px">
        <div><div class="hint mono">${esc(c.id)} · ${esc(c.bucket || "")}</div><h1>${esc(c.name)}</h1>
          <div class="btn-row" style="margin:6px 0">${healthChip(c.health)} ${prio(c.priority)} <span class="chip outline">${esc(c.status || "")}</span> ${quadChip(c.quadrant)}${s ? `<span class="hint mono">V${s.value_total} · C${s.complexity_total}</span>` : ""}</div>
          <div class="lead">${esc(c.short_description || "")}</div>
          <div class="hint" style="margin-top:4px">Owner <b>${esc(c.owner || "not set")}</b> · Sponsor <b>${esc(c.sponsor || "not set")}</b></div></div>
        ${stageStrip(c, -1)}
        <div><div class="card-title">Decision needed</div><div class="big-q pre">${esc(c.decision_needed || "None recorded")}</div></div>
        <div class="card"><div class="card-title"><span class="grow">Latest update · ${fmtD(c.latest_update_date)} · ${esc(c.movement || "")}</span><a class="small" href="#/i/${c.id}?tab=updates">history →</a></div>
          <div style="font-size:13.5px">${esc(c.latest_update_summary || "No updates yet.")}</div>
          ${c.next_action ? `<div class="na" style="margin-top:8px;font-size:12.5px;background:#F8FAFC;border:1px solid var(--line-2);border-radius:4px;padding:6px 8px"><b>Next action:</b> ${esc(c.next_action)} <span class="muted">— ${esc(c.next_action_owner || "no owner")}</span></div>` : ""}</div>
        <div class="grid g2"><div class="card"><div class="card-title">Flags</div>${flagList(c.flags)}</div>${stageGate(Math.max(0, c.stage_index))}</div>
      </div>
      <div class="grid" style="align-content:start;gap:14px">
        <form class="card" id="ws-decide"><div class="card-title"><span class="grow">Record the decision</span>${c.decisions[0] ? `<span class="hint">last: ${dchip(c.decisions[0].decision)} ${fmtD(c.decisions[0].decision_date)}</span>` : ""}</div>
          ${decisionFields(c)}
          <div class="btn-row" style="margin-top:10px"><button class="btn primary">Record${next ? " & next →" : ""}</button><button type="button" class="btn" data-act="log-update" data-id="${c.id}">Log update only</button>${next ? `<button type="button" class="btn" data-href="#/workshop?set=${set}&start=${next.id}">Skip</button>` : ""}</div>
        </form>
        <div class="card ws-list"><div class="card-title"><span class="grow">In this session</span><span class="hint">${list.filter((x) => x.last_decision_date === todayISO()).length} of ${list.length} decided today</span></div>${list.map((x) => `<a href="#/workshop?set=${set}&start=${x.id}" class="${x.id === id ? "on" : ""}">${dot(x.health_class)}<span>${esc(x.name)}</span><span class="done">${x.last_decision_date === todayISO() ? `${dchip(x.last_decision)} ✓` : prio(x.priority)}</span></a>`).join("")}</div>
      </div>
    </section>`;
};

const DECISION_HELP = { Stop: "end it; free the resource", Hold: "pause; revisit later", Continue: "keep going at this stage", Pivot: "change scope or approach", Scale: "move forward / expand" };
function decisionFields(c) {
  return `<div class="decide">${META.decisions.map((d) => `<label><input type="radio" name="decision" value="${d}" required><span>${d}<small>${DECISION_HELP[d]}</small></span></label>`).join("")}</div>
    <div class="form" style="margin-top:10px">
      <div class="row">${field("Stage after decision", sel("stage_to", META.stages.map((s) => [s.key, s.label]), c.stage, false))}${field("Health", sel("health", META.healths, c.health || "Grey", false))}${field("Next review", inp("next_review_date", addDays(todayISO(), 28), "date"))}</div>
      ${field("Rationale", ta("rationale", "", 2, `placeholder="Why — what evidence or concern drove this?"`))}
      ${field("Conditions / next action", ta("next_action", "", 2, `placeholder="What has to happen before the next review?"`))}
      <div class="row">${field("Action owner", inp("next_action_owner", c.next_action_owner || "", "text", `list="owners"`))}${field("Decided by", inp("decided_by", "", "text", `placeholder="e.g. MD / portfolio review"`))}${field("Forum", inp("forum", "Monthly portfolio review"))}</div>
    </div><datalist id="owners">${META.owners.map((o) => `<option value="${esc(o)}">`).join("")}</datalist>`;
}

// ---- open actions
PAGES.actions = async (r) => {
  const ups = await GET("/api/updates");
  // Only each initiative's latest update counts — older "Open" rows from MS Lists were never closed off.
  const latest = {};
  ups.forEach((u) => { if (!latest[u.initiative_id] || u.update_date > latest[u.initiative_id].update_date) latest[u.initiative_id] = u; });
  const open = Object.values(latest).filter((u) => u.action_status === "Open" && u.next_action);
  const owner = r.q.owner || "";
  const owners = [...new Set(open.map((u) => u.next_action_owner || "No owner"))].sort();
  const rows = open.filter((u) => !owner || (u.next_action_owner || "No owner") === owner).sort((a, b) => (a.due_date || "9") < (b.due_date || "9") ? -1 : 1);
  const t = todayISO();
  return `<section>${sec("Open actions", "The current next action from each initiative's latest open update. Close an action when it's done, or log a new update to replace it.")}
    <div class="filters"><select data-filter="owner"><option value="">All owners (${open.length})</option>${owners.map((o) => `<option ${o === owner ? "selected" : ""}>${esc(o)}</option>`).join("")}</select>
      <span class="count">${rows.filter((u) => u.due_date && u.due_date < t).length} overdue</span></div></section>
  <section><div class="card" style="padding:0"><table class="ops"><thead><tr><th>Due</th><th>Initiative</th><th>Action</th><th>Owner</th><th></th></tr></thead><tbody>
    ${rows.map((u) => `<tr><td class="mono small nowrap">${u.due_date ? `${u.due_date < t ? dot("red") + " " : ""}${fmtD(u.due_date)}` : "—"}</td>
      <td class="small"><a href="#/i/${u.initiative_id}?tab=updates"><b>${esc(u.initiative_name)}</b></a><div class="hint">from ${fmtD(u.update_date)} update</div></td>
      <td class="small">${esc(u.next_action)}</td><td class="small">${esc(u.next_action_owner || "—")}</td>
      <td class="nowrap"><button class="btn sm" data-act="close-action" data-uid="${esc(u.id)}">Done</button> <button class="btn sm" data-act="log-update" data-id="${u.initiative_id}">Update</button></td></tr>`).join("") || `<tr><td colspan="5" class="empty">No open actions.</td></tr>`}
  </tbody></table></div></section>`;
};

// ---- updates log
PAGES.updates = async (r) => {
  const ups = await GET("/api/updates");
  const q = r.q;
  const rows = ups.filter((u) => (!q.type || u.update_type === q.type) && (!q.md || u.include_in_md_update) && (!q.status || u.action_status === q.status) &&
    (!q.q || [u.initiative_name, u.summary, u.next_action].some((v) => (v || "").toLowerCase().includes(q.q.toLowerCase()))));
  return `<section>${sec("Updates log", "Every dated update across the portfolio — the movement history behind the register.", `<div class="btn-row" style="margin-top:8px"><a class="btn" href="/api/export/updates.csv">Export CSV</a></div>`)}
    <div class="filters"><input type="search" data-filter="q" placeholder="Search…" value="${esc(q.q || "")}">
      <select data-filter="type"><option value="">All types</option>${opts(META.update_types, q.type, false)}</select>
      <select data-filter="status"><option value="">Any status</option>${opts(["Open", "Closed", "Superseded"], q.status, false)}</select>
      <label class="small"><input type="checkbox" data-filter="md" ${q.md ? "checked" : ""}> MD update only</label><span class="count">${rows.length} of ${ups.length}</span></div></section>
  <section><div class="card" style="padding:0"><table class="ops"><thead><tr><th>Date</th><th>Initiative</th><th>Type</th><th>Movement</th><th>Health</th><th>Summary</th><th>Status</th></tr></thead><tbody>
    ${rows.map((u) => `<tr class="click" data-href="#/i/${u.initiative_id}?tab=updates"><td class="mono small nowrap">${fmtD(u.update_date)}</td><td class="small"><b>${esc(u.initiative_name)}</b></td><td class="small nowrap">${esc(u.update_type || "")}</td><td class="small nowrap">${esc(u.movement || "")}</td><td>${u.health ? healthChip(u.health) : ""}</td><td class="small"><div class="desc" style="max-width:560px;color:var(--ink-2)">${esc(u.summary || "")}</div></td><td class="small">${esc(u.action_status || "")}</td></tr>`).join("")}
  </tbody></table></div></section>`;
};

// ---- decisions log
PAGES.decisions = async () => {
  const ds = await GET("/api/decisions");
  return `<section>${sec("Decisions log", "Every Stop / Hold / Continue / Pivot / Scale decision, newest first.")}
    <div class="card" style="padding:0">${ds.length ? `<table class="ops"><thead><tr><th>Date</th><th>Initiative</th><th>Decision</th><th>Stage</th><th>Rationale</th><th>Conditions</th><th>By</th></tr></thead><tbody>
      ${ds.map((x) => `<tr class="click" data-href="#/i/${x.initiative_id}?tab=decisions"><td class="mono small nowrap">${fmtD(x.decision_date)}</td><td class="small"><b>${esc(x.initiative_name)}</b></td><td>${dchip(x.decision)}</td><td class="small nowrap">${x.stage_to !== x.stage_from ? `${esc(stageLabel(x.stage_from))} → <b>${esc(stageLabel(x.stage_to))}</b>` : esc(stageLabel(x.stage_to))}</td><td class="small">${esc(x.rationale || "")}</td><td class="small">${esc(x.conditions || "")}</td><td class="small">${esc(x.decided_by || "")}</td></tr>`).join("")}</tbody></table>`
      : `<div class="empty">No decisions yet. Run <a href="#/workshop">Workshop mode</a> in the next portfolio review.</div>`}</div></section>`;
};

// ---- leadership pack (printable)
PAGES.pack = async (r) => {
  const [cards, ups, ov, decs] = await Promise.all([refreshCache(), GET("/api/updates"), GET("/api/overview"), GET("/api/decisions")]);
  const since = r.q.since || addDays(todayISO(), -31);
  const recent = decs.filter((x) => x.decision_date >= since);
  const mdOnly = r.q.all !== "1";
  const latest = {};
  ups.filter((u) => !u.confidential || !mdOnly).forEach((u) => { if (!latest[u.initiative_id] || u.update_date > latest[u.initiative_id].update_date) latest[u.initiative_id] = u; });
  const rows = sortRows(cards.filter((c) => !["Stopped", "Closed / BAU"].includes(c.status) && (!mdOnly || latest[c.id]?.include_in_md_update)), "priority", true);
  return `<section class="no-print"><div class="btn-row"><button class="btn primary" data-act="print">Print / save as PDF</button>
      <label class="small"><input type="checkbox" data-act="pack-all" ${mdOnly ? "" : "checked"}> Include initiatives not flagged for the MD update</label>
      <span class="hint">Working-only updates and working notes are never shown here.</span></div></section>
  <section class="pack-head"><img src="/static/wsg-logo.svg" alt="WSG"><div><h1>Innovation Portfolio — leadership update</h1><div class="small" style="color:#D5D8DB">${fmtD(todayISO())} · ${rows.length} initiatives</div></div></section>
  <section class="card"><div class="card-title"><span class="grow">Decisions since ${fmtD(since)}</span><span class="no-print small">from <input type="date" data-filter="since" value="${since}"></span></div>
    ${recent.length ? `<table class="ops"><thead><tr><th>Date</th><th>Initiative</th><th>Decision</th><th>Stage</th><th>Rationale / conditions</th></tr></thead><tbody>${recent.map((x) => `<tr><td class="mono small nowrap">${fmtD(x.decision_date)}</td><td class="small"><b>${esc(x.initiative_name)}</b></td><td>${dchip(x.decision)}</td><td class="small nowrap">${x.stage_to !== x.stage_from ? `${esc(stageLabel(x.stage_from))} → <b>${esc(stageLabel(x.stage_to))}</b>` : esc(stageLabel(x.stage_to))}</td><td class="small">${esc(x.rationale || "")}${x.conditions ? `<div class="hint">${esc(x.conditions)}</div>` : ""}</td></tr>`).join("")}</tbody></table>` : `<div class="hint">No decisions recorded in this period.</div>`}</section>
  <section class="grid g4">${ov.kpis.slice(0, 4).map((k) => `<div class="card tight kpi ${k.rag}"><div class="l">${esc(k.label)}</div><div class="v">${esc(k.value)}</div><div class="note">${esc(k.note)}</div></div>`).join("")}</section>
  <section class="card"><div class="card-title">By stage</div><div class="grid g5">${ov.by_stage.filter((s) => s.key !== "other").map((s) => `<div><div class="small"><b>${esc(s.label)}</b> <span class="mono muted">${s.items.length}</span></div><div class="hint">${s.items.map((c) => esc(c.name)).join(" · ") || "—"}</div></div>`).join("")}</div></section>
  ${rows.map((c) => { const u = latest[c.id]; return `<section class="pack-page"><div style="display:flex;gap:10px;align-items:baseline;flex-wrap:wrap"><h2>${esc(c.name)}</h2>${healthChip(c.health)} ${prio(c.priority)} <span class="hint">${esc(stageLabel(c.stage))} · ${esc(c.owner || "")}</span></div>
      ${u ? `<div class="hint">${fmtD(u.update_date)} · ${esc(u.movement || "")}</div><div style="font-size:12.5px;margin:6px 0">${esc(u.summary)}</div>
      <dl class="kv"><dt>Decision needed</dt><dd>${esc(u.decision_needed || "—")}</dd><dt>Next action</dt><dd>${esc(u.next_action || "—")} ${u.next_action_owner ? `<span class="muted">— ${esc(u.next_action_owner)}</span>` : ""}</dd></dl>` : `<div class="hint">No update.</div>`}</section>`; }).join("")}`;
};

// ---- import / export
let IMPORT_FILES = [];
PAGES.import = async () => {
  return `<section>${sec("Import from MS Lists", "Export each list from MS Lists as CSV (Export → Export to CSV), then drop the files here. Nothing loads until you've checked the report and pressed Load. Existing rows are updated by ID; nothing is deleted. The database is backed up before every load.")}
    <div class="drop" id="drop"><b>Drop CSV files here</b><div class="hint">or click to choose — Initiative Register, Scoring Component Model, Alignment / Value Pockets, Initiative Updates Log (any or all)</div><input type="file" id="file" accept=".csv" multiple hidden></div>
    <div id="import-report" style="margin-top:14px"></div></section>
  <section>${sec("Export for Power BI or Excel", "Same column names as the original lists, so existing Power BI reports can point at these files. Multi-choice values are separated by semicolons.")}
    <div class="btn-row"><a class="btn" href="/api/export/register.csv">Initiative Register</a><a class="btn" href="/api/export/scores.csv">Scoring Component Model</a><a class="btn" href="/api/export/alignment.csv">Alignment / Value Pockets</a><a class="btn" href="/api/export/updates.csv">Initiative Updates Log</a></div></section>`;
};

function importReport(d, applied) {
  return d.files.map((f) => `<div class="card" style="margin-bottom:10px"><div class="card-title"><span class="grow">${esc(f.label || "Unrecognised file")} · <span class="mono">${esc(f.filename)}</span></span>
      ${f.kind ? `<span class="chip green">${f.new} new</span> <span class="chip info">${f.updated} update</span> ${f.skipped ? `<span class="chip amber">${f.skipped} skipped</span>` : ""}` : ""}</div>
    ${f.issues.length ? f.issues.map((i) => `<div class="issue"><span class="lv ${i.level}">${i.level}</span><span class="mono small muted" style="width:46px">row ${i.row}</span><span>${esc(i.msg)}</span></div>`).join("") : `<div class="hint">No issues.</div>`}</div>`).join("")
    + (applied ? "" : `<div class="btn-row"><button class="btn primary" data-act="import-apply">Load ${d.files.reduce((a, f) => a + f.new + f.updated, 0)} rows</button><button class="btn" data-act="import-clear">Cancel</button></div>`);
}

async function readFiles(list) {
  IMPORT_FILES = await Promise.all([...list].map((f) => new Promise((res) => { const fr = new FileReader(); fr.onload = () => res({ filename: f.name, content_base64: fr.result.split(",")[1] }); fr.readAsDataURL(f); })));
  try {
    const d = await api("POST", "/api/import/check", { files: IMPORT_FILES });
    $("#import-report").innerHTML = importReport(d, false);
  } catch (e) { toast(e.message, true); }
}

// ---- framework explainer
PAGES.framework = async () => `<section>${sec("How the framework works", "A light stage-gate: capture without a business case, then ask for more evidence as initiatives ask for more resource, funding or rollout.")}
  <div class="grid g5">${META.stages.map((s, n) => `<div class="card"><div class="card-title">Stage ${n + 1}</div><div class="display" style="font-weight:700;font-size:14px">${esc(s.label)}</div><div class="small" style="margin:6px 0">${esc(s.objective)}</div><div class="hint">Gate evidence:</div><ul style="margin:2px 0 0;padding-left:16px;font-size:11.5px">${s.gate.map((g) => `<li>${esc(g)}</li>`).join("")}</ul></div>`).join("")}</div></section>
  <section class="grid g2"><div class="card"><div class="card-title">Scoring</div><div class="small">Five value factors and five complexity factors, each <b>0</b> (none / low), <b>1</b> (some / moderate) or <b>2</b> (strong / high). Totals out of 10.</div>
    <div class="grid g2" style="margin-top:8px"><div><b class="small">Value</b>${Object.values(META.value_labels).map((l) => `<div class="small">· ${esc(l)}</div>`).join("")}</div><div><b class="small">Complexity</b>${Object.values(META.complexity_labels).map((l) => `<div class="small">· ${esc(l)}</div>`).join("")}</div></div>
    <div class="small" style="margin-top:8px">Quadrant is calculated: high value is ≥ ${META.cuts.value_cut}, high complexity is ≥ ${META.cuts.complexity_cut} (<a href="#/matrix">change</a>).</div></div>
    <div class="card"><div class="card-title">Decisions at a review</div>${META.decisions.map((d) => `<div class="list-row">${dchip(d)}<span class="small">${esc(DECISION_HELP[d])}</span></div>`).join("")}
    <div class="hint" style="margin-top:6px">A decision is written to the decisions log and the updates log, and can move the stage and set the next review date.</div></div></section>`;

// ------------------------------------------------------------------ forms
function initiativeForm(c) {
  const f = c?.fields || {};
  const checks = (name, list, chosen) => `<div class="checks">${[...new Set([...list, ...(chosen || [])])].map((v) => `<label><input type="checkbox" name="${name}[]" value="${esc(v)}" ${(chosen || []).includes(v) ? "checked" : ""}>${esc(v)}</label>`).join("")}</div>`;
  return `${field("Name", inp("name", f.name, "text", "required"))}
    ${field("Short description", ta("short_description", f.short_description, 3, `placeholder="What is it, and why does it matter? One or two sentences is enough to start."`))}
    <div class="row">${field("Primary owner", inp("primary_owner", f.primary_owner, "text", `list="owners"`))}${field("Sponsor / exec lead", inp("sponsor", f.sponsor))}</div>
    <div class="row">${field("Stage", sel("stage", META.stages.map((s) => [s.key, s.label]), f.stage || "Idea/concept", false))}${field("Priority", sel("priority", META.priorities, f.priority || "Medium", false))}${field("Health", sel("health", META.healths, f.health || "Grey", false))}</div>
    <div class="row">${field("Portfolio bucket", inp("portfolio_bucket", f.portfolio_bucket, "text", `list="buckets"`))}${field("Status", sel("portfolio_status", META.statuses, f.portfolio_status || "Proposed", false))}${field("Next review", inp("next_review_date", f.next_review_date, "date"))}</div>
    ${field("Business areas", checks("business_areas", META.business_areas, f.business_areas))}
    ${c ? `${field("Decision needed", ta("decision_needed", f.decision_needed, 2))}${field("Dependencies", ta("dependencies", f.dependencies, 2))}
      <div class="row">${field("Evidence status", inp("evidence_status", f.evidence_status))}${field("Confidence", inp("confidence", f.confidence))}${field("Funding / resource ask", inp("funding_ask", f.funding_ask))}</div>
      ${field("Related initiatives", inp("related_initiatives", (f.related_initiatives || []).join("; ")), "separate with ;")}${field("Comments", ta("comments", f.comments, 3))}`
      : `${field("Decision needed first", ta("decision_needed", "", 2, `placeholder="Optional — what would you want leadership to decide?"`))}`}
    <datalist id="owners">${META.owners.map((o) => `<option value="${esc(o)}">`).join("")}</datalist><datalist id="buckets">${META.buckets.map((o) => `<option value="${esc(o)}">`).join("")}</datalist>`;
}

function updateForm(c) {
  return `<div class="hint" style="margin-top:-4px">${esc(c.name)} · currently ${esc(c.health || "Grey")}, ${esc(stageLabel(c.stage))}</div>
    <div class="row">${field("Type", sel("update_type", META.update_types, "Owner Update", false))}${field("Date", inp("update_date", todayISO(), "date"))}${field("Movement", sel("movement", META.movements, "Progressed", false))}${field("Health now", sel("health", META.healths, c.health || "Grey", false))}</div>
    ${field("What's changed?", ta("summary", "", 4, `required placeholder="Progress, evidence, blockers — a few sentences."`))}
    ${field("Decision needed", ta("decision_needed", c.decision_needed || "", 2), "leave as is, edit, or clear")}
    ${field("Next action", ta("next_action", "", 2, `placeholder="What happens next?"`))}
    <div class="row">${field("Action owner", inp("next_action_owner", c.next_action_owner || "", "text", `list="owners"`))}${field("Due", inp("due_date", addDays(todayISO(), 14), "date"))}${field("Next review", inp("next_review_date", c.next_review_date && c.next_review_date > todayISO() ? c.next_review_date : addDays(todayISO(), 28), "date"))}</div>
    ${field("Working notes", ta("working_notes", "", 2, `placeholder="Optional — sensitive context. Never shown in the leadership pack."`))}
    <div class="checks"><label><input type="checkbox" name="include_in_md_update" checked> Include in MD update</label><label><input type="checkbox" name="confidential"> Working only (confidential)</label><label><input type="checkbox" name="supersede_previous" checked> Supersede the previous open update</label></div>
    <datalist id="owners">${META.owners.map((o) => `<option value="${esc(o)}">`).join("")}</datalist>`;
}

function scoreForm(c) {
  const s = c.score || {};
  const seg = (k, l, kind) => `<div class="score-row"><span>${esc(l)}</span><span class="seg" data-kind="${kind}">${[0, 1, 2].map((n) => `<label><input type="radio" name="${k}" value="${n}" ${(s[k] ?? 0) === n ? "checked" : ""}><span>${n}</span></label>`).join("")}</span></div>`;
  return `<div class="hint" style="margin-top:-4px">0 = none / low · 1 = some / moderate · 2 = strong / high. ${c.score ? "Starts from the current score." : ""}</div>
    <div class="score-grid"><div><div class="card-title"><span class="grow">Value</span><span class="total-big" id="vt">0</span></div>${Object.entries(META.value_labels).map(([k, l]) => seg(k, l, "v")).join("")}</div>
    <div><div class="card-title"><span class="grow">Complexity</span><span class="total-big" id="ct">0</span></div>${Object.entries(META.complexity_labels).map(([k, l]) => seg(k, l, "c")).join("")}</div></div>
    <div id="qprev" style="margin:4px 0"></div>
    <div class="row">${field("Value rationale", ta("value_rationale", s.value_rationale, 2))}${field("Complexity rationale", ta("complexity_rationale", s.complexity_rationale, 2))}</div>
    <div class="row">${field("Confidence", sel("confidence", ["High", "Medium", "Low"], s.confidence || "Medium", false))}${field("Scored by", inp("scored_by", ""))}</div>
    <div class="checks"><label><input type="checkbox" name="review_required"> Needs review by owner / sponsor</label></div>`;
}

function liveScore(form) {
  const sum = (kind) => $$(`.seg[data-kind=${kind}] input:checked`, form).reduce((a, i) => a + +i.value, 0);
  const upd = () => {
    const v = sum("v"), c = sum("c");
    $("#vt", form).textContent = v; $("#ct", form).textContent = c;
    const hv = v >= META.cuts.value_cut, hc = c >= META.cuts.complexity_cut;
    $("#qprev", form).innerHTML = `Lands in ${quadChip(hv && !hc ? "Quick Win" : hv && hc ? "Big Bet" : !hv && !hc ? "Filler / Enabler" : "Money Pit / Park")}`;
  };
  form.addEventListener("change", upd); upd();
}

async function openForm(kind, id, extra = {}) {
  const c = id ? await GET(`/api/initiatives/${id}`) : null;
  if (kind === "new") {
    modal("New initiative", initiativeForm(null), "Add to register", async (d) => {
      const r = await api("POST", "/api/initiatives", nul(d));
      META = await GET("/api/meta"); location.hash = `#/i/${r.id}`; return r;
    }, { wide: true });
  } else if (kind === "edit") {
    modal(`Edit — ${c.name}`, initiativeForm(c), "Save", async (d) => { const r = await api("PATCH", `/api/initiatives/${id}`, nul(d)); META = await GET("/api/meta"); return r; }, { wide: true });
  } else if (kind === "update") {
    modal(`Log update — ${c.name}`, updateForm(c), "Log update", (d) => api("POST", `/api/initiatives/${id}/updates`, nul(d)), { wide: true });
  } else if (kind === "score") {
    modal(`${c.score ? "Re-score" : "Score"} — ${c.name}`, scoreForm(c), "Save score", (d) => {
      Object.keys(META.value_labels).concat(Object.keys(META.complexity_labels)).forEach((k) => (d[k] = +d[k]));
      return api("POST", `/api/initiatives/${id}/scores`, nul(d));
    }, { wide: true, onOpen: liveScore });
  } else if (kind === "decide") {
    modal(`Record decision — ${c.name}`, decisionFields(c), "Record decision", (d) => {
      if (!d.decision) throw new Error("Choose Stop, Hold, Continue, Pivot or Scale");
      return api("POST", `/api/initiatives/${id}/decisions`, nul(d));
    }, { wide: true });
  } else if (kind === "align") {
    const list = extra.type === "Strategic Priority" ? META.strategic_priorities : META.value_pockets;
    modal(`Add ${extra.type.toLowerCase()} — ${c.name}`, `${field(extra.type, inp("area", "", "text", `list="areas" required`))}<datalist id="areas">${list.map((o) => `<option value="${esc(o)}">`).join("")}</datalist>
      ${field("Role", sel("role", ["Primary", "Supporting"], "Supporting", false))}`, "Add", (d) => api("POST", `/api/initiatives/${id}/alignments`, { ...d, alignment_type: extra.type }));
  }
}

// ------------------------------------------------------------------ events
document.addEventListener("click", async (e) => {
  const a = e.target.closest("[data-act]");
  if (a) {
    const act = a.dataset.act;
    if (act === "new-initiative") return openForm("new");
    if (act === "log-update") return openForm("update", a.dataset.id);
    if (act === "edit") return openForm("edit", a.dataset.id);
    if (act === "score") return openForm("score", a.dataset.id);
    if (act === "decide") return openForm("decide", a.dataset.id);
    if (act === "add-align") return openForm("align", a.dataset.id, { type: a.dataset.type });
    if (act === "rm-align") { try { toast((await api("DELETE", `/api/alignments/${encodeURIComponent(a.dataset.aid)}`)).message); render(); } catch (err) { toast(err.message, true); } return; }
    if (act === "close-action") { try { await api("PATCH", `/api/updates/${encodeURIComponent(a.dataset.uid)}`, { action_status: "Closed" }); toast("Action closed"); render(); } catch (err) { toast(err.message, true); } return; }
    if (act === "tab") { setQuery({ tab: a.dataset.tab, stage: "" }); return render(); }
    if (act === "stage-info") { if (parseRoute().parts[0] === "i") { setQuery({ stage: a.dataset.n, tab: "overview" }); render(); } return; }
    if (act === "clear-filters") { history.replaceState(null, "", "#/register"); return render(); }
    if (act === "clear-special") { e.preventDefault(); setQuery({ movement: "", flag: "", area: "" }); return render(); }
    if (act === "save-cuts") { try { toast((await api("PUT", "/api/settings/cuts", { value_cut: +a.dataset.v, complexity_cut: +a.dataset.c })).message); META = await GET("/api/meta"); location.hash = "#/matrix"; } catch (err) { toast(err.message, true); } return; }
    if (act === "print") return window.print();
    if (act === "pack-all") { setQuery({ all: a.checked ? "1" : "" }); return render(); }
    if (act === "import-clear") { IMPORT_FILES = []; $("#import-report").innerHTML = ""; return; }
    if (act === "import-apply") {
      a.disabled = true;
      try { const d = await api("POST", "/api/import/apply", { files: IMPORT_FILES }); toast(d.message); META = await GET("/api/meta"); $("#import-report").innerHTML = `<div class="prompt">${esc(d.message)}. Backup saved as ${esc(d.backup || "—")}. <a href="#/">Go to the overview →</a></div>` + importReport(d, true); renderNav(parseRoute()); updateHeader(); }
      catch (err) { toast(err.message, true); a.disabled = false; }
      return;
    }
  }
  if (e.target.closest("#drop")) return $("#file").click();
  const th = e.target.closest("th[data-sort]");
  if (th) { const r = parseRoute(); setQuery({ sort: th.dataset.sort, dir: r.q.sort === th.dataset.sort && r.q.dir !== "desc" ? "desc" : "" }); return render(); }
  const h = e.target.closest("[data-href]");
  if (h && !e.target.closest("a,button:not([data-href])")) { location.hash = h.dataset.href; }
});

document.addEventListener("change", (e) => {
  if (e.target.id === "file") return readFiles(e.target.files);
  const f = e.target.dataset.filter;
  if (f) { setQuery({ [f]: e.target.type === "checkbox" ? (e.target.checked ? "1" : "") : e.target.value }); render(); }
  if (e.target.dataset.cut) setQuery({ [e.target.dataset.cut]: e.target.value }) || render();
});
let typing;
document.addEventListener("input", (e) => {
  if (e.target.dataset.filter === "q") { clearTimeout(typing); typing = setTimeout(async () => { setQuery({ q: e.target.value }); await render(); const s = $("[data-filter=q]"); s.focus(); s.setSelectionRange(s.value.length, s.value.length); }, 250); }
  if (e.target.dataset.cut) { e.target.nextElementSibling.textContent = e.target.value; clearTimeout(typing); typing = setTimeout(() => { setQuery({ [e.target.dataset.cut]: e.target.value }); render(); }, 120); }
});
document.addEventListener("submit", async (e) => {
  if (e.target.id !== "ws-decide") return;
  e.preventDefault();
  const d = Object.fromEntries(new FormData(e.target).entries());
  if (!d.decision) return toast("Choose Stop, Hold, Continue, Pivot or Scale", true);
  const r = parseRoute();
  const id = r.q.start || $(".ws-list a.on")?.getAttribute("href").split("start=")[1];
  try {
    toast((await api("POST", `/api/initiatives/${id}/decisions`, nul(d))).message);
    const next = $(".ws-bar button[data-href*='start=']:last-of-type");
    const list = $$(".ws-list a"); const i = list.findIndex((x) => x.classList.contains("on"));
    if (list[i + 1]) location.hash = list[i + 1].getAttribute("href"); else render();
  } catch (err) { toast(err.message, true); }
});
document.addEventListener("dragover", (e) => { const d = e.target.closest("#drop"); if (d) { e.preventDefault(); d.classList.add("over"); } });
document.addEventListener("dragleave", (e) => { const d = e.target.closest("#drop"); if (d) d.classList.remove("over"); });
document.addEventListener("drop", (e) => { const d = e.target.closest("#drop"); if (d) { e.preventDefault(); d.classList.remove("over"); readFiles(e.dataTransfer.files); } });

// quick find in the header
const jump = $("#jump");
jump.addEventListener("input", async () => {
  if (!CACHE) await refreshCache();
  const s = jump.value.trim().toLowerCase();
  $("#jump-list").innerHTML = s ? CACHE.filter((c) => (c.name + " " + c.id + " " + (c.owner || "")).toLowerCase().includes(s)).slice(0, 10)
    .map((c, n) => `<a href="#/i/${c.id}" class="${n === 0 ? "on" : ""}"><span class="id">${esc(c.id)}</span>${dot(c.health_class)}<span>${esc(c.name)}</span></a>`).join("") || `<a>No match</a>` : "";
});
jump.addEventListener("keydown", (e) => {
  if (e.key === "Enter") { const a = $("#jump-list a.on"); if (a?.getAttribute("href")) { location.hash = a.getAttribute("href"); jump.value = ""; $("#jump-list").innerHTML = ""; } }
  if (e.key === "Escape") { jump.value = ""; $("#jump-list").innerHTML = ""; }
});
document.addEventListener("click", (e) => { if (!e.target.closest(".top-search")) $("#jump-list").innerHTML = ""; else if (e.target.closest("#jump-list a")) { jump.value = ""; setTimeout(() => ($("#jump-list").innerHTML = ""), 0); } });
$("#burger").onclick = () => $("#nav").classList.toggle("closed");

// ------------------------------------------------------------------ render
function updateHeader() { $("#today").textContent = `v${META.version} · ${META.counts.initiatives} initiatives · ${fmtD(META.today)}`; }

async function render() {
  const r = parseRoute();
  renderNav(r);
  updateHeader();
  const page = PAGES[r.parts[0] || ""];
  const main = $("#main");
  if (!page) { main.innerHTML = `<div class="page"><div class="empty">Page not found. <a href="#/">Overview</a></div></div>`; return; }
  try {
    const html = await page(r);
    const y = main.scrollTop;
    main.innerHTML = `<div class="page">${html}</div>`;
    if (render.last === location.hash.split("?")[0]) main.scrollTop = y;
    render.last = location.hash.split("?")[0];
    $$("th[data-sort]").forEach((th) => { if (th.dataset.sort === (r.q.sort || "id")) th.classList.add("sorted", r.q.dir === "desc" ? "desc" : "asc"); });
  } catch (e) { main.innerHTML = `<div class="page"><div class="card empty">${esc(e.message)}</div></div>`; }
}

window.addEventListener("hashchange", render);
(async () => {
  META = await GET("/api/meta");
  updateHeader();
  if (!META.counts.initiatives && !location.hash) location.hash = "#/import";
  render();
})();
