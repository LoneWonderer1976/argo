/* Argo -- the page. Reads data.json (written by argo/score.py) and draws it. No state of its own. */
(function () {
  const $ = (id) => document.getElementById(id);
  const gbp = (p) => "£" + (p / 100).toFixed(2);
  const km = (m) => ((m || 0) / 1000).toFixed(1) + " km";
  const mi = (m) => ((m || 0) / 1609.344).toFixed(1) + " mi";
  const dur = (s) => { s = Math.round(s || 0); return s >= 3600 ? `${Math.floor(s / 3600)}h ${String(Math.floor(s % 3600 / 60)).padStart(2, "0")}m` : `${Math.floor(s / 60)} min`; };
  const ICON = { run: "🏃", walk: "🚶", cycle: "🚴", swim: "🏊", kayak: "🛶", other: "❓" };
  const DAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const when = (s) => { const d = new Date(s.replace(" ", "T")); return `${DAY[(d.getDay() + 6) % 7]} ${d.getDate()} ${d.toLocaleString("en-GB", { month: "short" })}, ${s.slice(11, 16)}`; };
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  let DATA = null, map = null, layer = null, chart = null;

  async function load() {
    const r = await fetch("data.json?" + Date.now(), { cache: "no-store" });
    DATA = await r.json();
    render();
  }

  function render() {
    const t = DATA.totals;
    $("week-gbp").textContent = gbp(t.current_pence);
    $("owed-gbp").textContent = gbp(t.owed_pence);
    $("paid-gbp").textContent = gbp(t.paid_pence);
    $("total-gbp").textContent = gbp(t.pence);
    const b = new Date(DATA.built_at);
    $("updated").textContent = "updated " + b.toLocaleString("en-GB", { weekday: "short", hour: "2-digit", minute: "2-digit" });
    renderTrophies();
    renderWeeks();
    renderSteps();
    renderActivities();
    renderSports();
    renderRates();
    celebrate();
  }

  /* --- the Easter eggs. data.json carries only the ones already won; the rest are a number. ---
     Which ones THIS phone has already celebrated lives in localStorage (a per-viewer convenience:
     if it is wiped he gets the fanfare again, which is hardly a punishment). */
  const SEEN_KEY = "argo.eggs.seen";
  const seen = () => { try { return new Set(JSON.parse(localStorage.getItem(SEEN_KEY) || "[]")); } catch (e) { return new Set(); } };
  const markSeen = (keys) => { try { localStorage.setItem(SEEN_KEY, JSON.stringify([...keys])); } catch (e) { /* private mode */ } };

  function renderTrophies() {
    const m = DATA.milestones || { won: [], hidden: 0, total: 0 };
    $("trophy-count").textContent = `${m.won.length} of ${m.total}`;
    const cards = m.won.map((w) => `<div class="trophy" data-key="${w.key}"><div class="t-title">🏆 ${esc(w.title)}</div><div class="t-date">${w.date.slice(8, 10)}/${w.date.slice(5, 7)}/${w.date.slice(0, 4)}</div></div>`);
    const locked = Math.min(m.hidden, 3);
    for (let i = 0; i < locked; i++) cards.push(`<div class="trophy locked" title="still hidden">🥚</div>`);
    $("trophies").innerHTML = cards.join("");
    $("hidden-note").textContent = m.hidden ? `${m.hidden} Easter egg${m.hidden === 1 ? "" : "s"} still hidden. Keep going to find them.` : "You have found every single one. Thomas, that is astonishing.";
    $("trophies").querySelectorAll(".trophy[data-key]").forEach((el) => el.addEventListener("click", () => showEgg(m.won.find((w) => w.key === el.dataset.key), false)));
  }

  let eggQueue = [];
  function celebrate() {
    const m = DATA.milestones || { won: [] };
    const done = seen();
    const fresh = m.won.filter((w) => !done.has(w.key)).sort((a, b) => a.date < b.date ? -1 : 1);
    if (!fresh.length) return;
    // first load on a new phone with a long history: don't replay months of eggs one by one
    if (done.size === 0 && fresh.length > 5) { markSeen(new Set(m.won.map((w) => w.key))); return; }
    eggQueue = fresh;
    nextEgg();
  }
  function nextEgg() {
    const w = eggQueue.shift();
    if (!w) { $("egg").hidden = true; return; }
    showEgg(w, true);
  }
  function showEgg(w, isNew) {
    if (!w) return;
    $("egg-title").textContent = w.title;
    $("egg-message").textContent = w.message;
    $("egg-date").textContent = (isNew ? "Earned " : "Found ") + w.date.slice(8, 10) + "/" + w.date.slice(5, 7) + "/" + w.date.slice(0, 4);
    $("egg-next").textContent = eggQueue.length ? "Next one! →" : "Brilliant!";
    $("egg").hidden = false;
    if (isNew) { const s = seen(); s.add(w.key); markSeen(s); }
  }
  $("egg-next").addEventListener("click", nextEgg);

  function renderWeeks() {
    const weeks = DATA.weeks.slice(0, 12);
    const box = $("weeks");
    box.innerHTML = weeks.map((w) => `
      <div class="week ${w.status}">
        <span class="pill ${w.status}">${w.status}</span>
        <span class="label">${esc(w.label)}<div class="n">${w.n_activities} activit${w.n_activities === 1 ? "y" : "ies"}${w.steps ? " · " + w.steps.toLocaleString() + " steps" : ""} · ${w.points.toFixed(1)} pts${w.capped ? " · capped" : ""}${w.paid_on ? " · paid " + w.paid_on : ""}</div></span>
        <span class="gbp">${gbp(w.pence)}</span>
      </div>`).join("");
    const chartWeeks = DATA.weeks.slice(0, 10).reverse();
    const css = getComputedStyle(document.documentElement);
    const col = (s) => css.getPropertyValue("--" + s).trim();
    if (window.Chart) {
      if (chart) chart.destroy();
      chart = new Chart($("weeks-chart"), {
        type: "bar",
        data: {
          labels: chartWeeks.map((w) => w.monday.slice(8, 10) + "/" + w.monday.slice(5, 7)),
          datasets: [{ data: chartWeeks.map((w) => w.pence / 100), backgroundColor: chartWeeks.map((w) => col(w.status)), borderRadius: 6 }],
        },
        options: {
          plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => "£" + c.parsed.y.toFixed(2) } } },
          scales: { x: { grid: { display: false }, ticks: { color: col("muted") } }, y: { beginAtZero: true, ticks: { color: col("muted"), callback: (v) => "£" + v } } },
          animation: false,
        },
      });
    }
  }

  let stepsChart = null;
  function renderSteps() {
    const days = (DATA.steps || []).slice(0, 14).reverse();
    $("steps-section").hidden = !days.length;
    if (!days.length) return;
    const wk = DATA.weeks.find((w) => w.status === "current") || {};
    $("steps-sub").textContent = wk.steps ? `· ${wk.steps.toLocaleString()} this week = ${gbp(Math.round(wk.steps_points * DATA.scheme.pence_per_point))}` : "";
    const t = DATA.totals;
    $("steps-note").textContent = `${t.steps_net.toLocaleString()} steps since ${DATA.scheme.steps_start.slice(8, 10)}/${DATA.scheme.steps_start.slice(5, 7)} = ${t.steps_points.toFixed(1)} pts. ${DATA.scheme.pence_per_point * DATA.scheme.steps_pts_per_10k}p per 10,000 steps.`;
    if (window.Chart) {
      if (stepsChart) stepsChart.destroy();
      const css = getComputedStyle(document.documentElement);
      stepsChart = new Chart($("steps-chart"), {
        type: "bar",
        data: { labels: days.map((d) => d.date.slice(8, 10) + "/" + d.date.slice(5, 7)),
          datasets: [{ data: days.map((d) => d.steps), backgroundColor: days.map((d) => d.steps >= 10000 ? css.getPropertyValue("--accent").trim() : css.getPropertyValue("--walk").trim()), borderRadius: 5 }] },
        options: { animation: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `${c.parsed.y.toLocaleString()} steps` } } },
          scales: { x: { grid: { display: false }, ticks: { color: css.getPropertyValue("--muted").trim() } }, y: { beginAtZero: true, ticks: { color: css.getPropertyValue("--muted").trim(), callback: (v) => (v / 1000) + "k" } } } },
      });
    }
  }

  function renderActivities() {
    const acts = DATA.activities;
    $("empty").hidden = acts.length > 0;
    $("activities").innerHTML = acts.map((a) => `
      <div class="card ${a.excluded ? "struck" : (a.flags.length && a.sport !== "other" ? "flagged" : "")}" data-id="${a.id}">
        <div class="icon ${a.sport}">${ICON[a.sport] || ICON.other}</div>
        <div><div class="name">${esc(a.name || a.sport)}</div>
          <div class="meta">${when(a.start_local)} · ${a.sport === "swim" ? km(a.distance_m) : mi(a.distance_m)}${a.ascent_m ? " · " + Math.round(a.ascent_m) + " m ↑" : ""} · ${dur(a.duration_s)}</div></div>
        <div><div class="gbp">${gbp(a.pence_share)}</div><div class="pts">${a.points.toFixed(1)} pts</div></div>
      </div>`).join("");
    $("activities").querySelectorAll(".card").forEach((el) => el.addEventListener("click", () => openSheet(+el.dataset.id)));
  }

  function renderSports() {
    const by = {};
    for (const a of DATA.activities) {
      const s = by[a.sport] || (by[a.sport] = { n: 0, d: 0, c: 0, p: 0 });
      s.n++; s.d += a.distance_m || 0; s.c += a.ascent_m || 0; s.p += a.points;
    }
    const order = [...DATA.scheme.sports, "other"].filter((s) => by[s]);
    $("sports").querySelector("tbody").innerHTML = order.map((s) =>
      `<tr><td>${ICON[s]} ${s}</td><td>${by[s].n}</td><td>${s === "swim" ? km(by[s].d) : mi(by[s].d)}</td><td>${Math.round(by[s].c)} m</td><td>${by[s].p.toFixed(1)}</td></tr>`).join("")
      || `<tr><td colspan="5" class="muted">nothing yet</td></tr>`;
  }

  function renderRates() {
    const s = DATA.scheme, pp = s.pence_per_point;
    const rows = [];
    for (const [sport, pts] of Object.entries(s.distance_per_mile)) {
      rows.push([`${ICON[sport]} ${sport}`, `${gbp(pts * pp)} a mile`, s.ascent_per_m[sport] ? `+ ${(s.ascent_per_m[sport] * pp * 100).toFixed(1)}p per 100 m climbed` : ""]);
    }
    rows.push([`${ICON.swim} swim`, `${gbp(s.swim_per_100m * pp)} per 100 m`, ""]);
    if (s.steps_pts_per_10k) rows.push([`👟 steps`, `${gbp(s.steps_pts_per_10k * pp)} per 10,000`, `every day, from the watch${s.steps_per_mile_deducted ? `, less ${s.steps_per_mile_deducted.toLocaleString()} per mile walked or run` : ""}`]);
    $("rates").querySelector("tbody").innerHTML = rows.map((r) => `<tr><td>${r[0]}</td><td>${r[1]}</td><td class="muted small">${r[2]}</td></tr>`).join("");
    $("rates-note").textContent = `${pp}p a point · the week runs Monday to Sunday · a week is paid once Dad marks it` + (s.week_cap_points ? ` · at most ${s.week_cap_points} points a week count` : "");
  }

  async function openSheet(id) {
    const a = DATA.activities.find((x) => x.id === id);
    if (!a) return;
    $("sheet-title").textContent = a.name || a.sport;
    $("sheet-sub").textContent = `${ICON[a.sport]} ${a.sport} · ${when(a.start_local)}`;
    $("sheet-stats").innerHTML = [
      [a.sport === "swim" ? km(a.distance_m) : mi(a.distance_m), "distance"], [Math.round(a.ascent_m || 0) + " m", "climb"], [dur(a.duration_s), "time"],
      [a.points.toFixed(1), "points"], [gbp(a.pence_share), "earned"], [a.avg_hr ? Math.round(a.avg_hr) + " bpm" : "—", "avg HR"],
    ].map(([v, l]) => `<div><b>${v}</b><span>${l}</span></div>`).join("");
    $("sheet-flags").innerHTML = (a.excluded ? [`<div class="flag">Struck: ${esc(a.excluded)}</div>`] : a.flags.map((f) => `<div class="flag">⚠ ${esc(f)}</div>`))
      .concat(a.relabelled ? [`<div class="flag">The watch called this "${esc(a.type_key)}" — Dad says ${esc(a.sport)}.</div>`] : []).join("");
    $("sheet").hidden = false;
    const mapEl = $("map");
    mapEl.hidden = !a.has_track;
    if (a.has_track && window.L) {
      if (!map) {
        map = L.map(mapEl, { zoomControl: false, attributionControl: true });
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(map);
      }
      if (layer) layer.remove();
      try {
        const t = await (await fetch(`tracks/${id}.json`)).json();
        layer = L.polyline(t.points, { color: getComputedStyle(document.documentElement).getPropertyValue("--" + a.sport).trim() || "#e4572e", weight: 4 }).addTo(map);
        setTimeout(() => { map.invalidateSize(); map.fitBounds(layer.getBounds(), { padding: [16, 16] }); }, 50);
      } catch (e) { mapEl.hidden = true; }
    }
  }

  $("sheet-close").addEventListener("click", () => { $("sheet").hidden = true; });
  $("sheet").addEventListener("click", (e) => { if (e.target === $("sheet")) $("sheet").hidden = true; });
  document.addEventListener("visibilitychange", () => { if (!document.hidden) load(); });
  load().catch((e) => { $("empty").hidden = false; $("empty").textContent = "Could not load data.json: " + e; });
})();
