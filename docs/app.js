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
    renderWeeks();
    renderActivities();
    renderSports();
    renderRates();
  }

  function renderWeeks() {
    const weeks = DATA.weeks.slice(0, 12);
    const box = $("weeks");
    box.innerHTML = weeks.map((w) => `
      <div class="week">
        <span class="pill ${w.status}">${w.status}</span>
        <span class="label">${esc(w.label)}<div class="n">${w.n_activities} activit${w.n_activities === 1 ? "y" : "ies"} · ${w.points.toFixed(1)} pts${w.capped ? " · capped" : ""}${w.paid_on ? " · paid " + w.paid_on : ""}</div></span>
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
    $("sheet-flags").innerHTML = (a.excluded ? [`<div class="flag">Struck: ${esc(a.excluded)}</div>`] : a.flags.map((f) => `<div class="flag">⚠ ${esc(f)}</div>`)).join("");
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
