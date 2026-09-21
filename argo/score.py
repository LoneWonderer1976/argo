"""score.py -- activities -> points -> weeks -> money. Recomputed whole on every run.

    python -m argo.score           # writes docs/data.json (and copies the tracks) for the page
    python -m argo.score --print   # the same, printed as a table
    python -m argo.score --selftest

The only state that is NOT derived is the ledger (which weeks Ben has paid) and the overrides
(which activities he has struck). Everything else -- every point, every pound -- is computed
from data/activities against rates.py each time, so a rate change or a strike re-scores the
whole history and the page can never disagree with the rule.

Money is rounded on a WEEK'S total, not per activity: `pence_share` on an activity row is for
display and can be a penny off the week's figure; the week's `pence` is what is owed.
"""
import argparse
import datetime as dt
import json
import shutil

from . import milestones, rates, store
from .weeks import last_week, this_week, today_uk, week_for, week_label, week_of


def flags_for(row: dict) -> list[str]:
    """Reasons to look twice. Never a refusal -- Ben strikes, the app flags."""
    out = []
    sport = row.get("sport")
    if sport == "other":
        out.append(f"not a scored sport ({row.get('type_key') or 'unknown'})")
        return out
    speed = row.get("avg_speed_mps") or 0
    ceiling = rates.MAX_SPEED_MPS.get(sport)
    if ceiling and speed > ceiling:
        out.append(f"average speed {speed * 2.23694:.1f} mph is over the {sport} ceiling")
    if not row.get("avg_hr") and (row.get("distance_m") or 0) > 0:
        out.append("no heart rate recorded")
    dist = row.get("distance_m") or 0
    if 0 < dist < rates.MIN_DISTANCE_M:
        out.append(f"only {dist:.0f} m")
    dur = row.get("duration_s") or 0
    if dur and dur > 6 * 3600:
        out.append(f"{dur / 3600:.1f} hours long")
    return out


def scored_activities(activities: list[dict], excluded: dict, relabel: dict | None = None) -> list[dict]:
    """`relabel` is overrides["sport"]: Ben's word on what an activity was when the watch said
    "other" (a kayak logged as Other, 20/09/2026). Applied before pricing and before the flags."""
    out = []
    relabel = relabel or {}
    for a in activities:
        if not a.get("start_local"):
            continue
        if str(a["id"]) in relabel:
            a = {**a, "sport": relabel[str(a["id"])], "relabelled": True}
        day = dt.date.fromisoformat(a["start_local"][:10])
        if day < rates.SCHEME_START:
            continue
        ex = excluded.get(str(a["id"]))
        pts = rates.points_for(a["sport"], a.get("distance_m"), a.get("ascent_m")) if ex is None \
            else {"distance": 0.0, "ascent": 0.0}
        total = pts["distance"] + pts["ascent"]
        out.append({
            "id": a["id"], "name": a["name"], "sport": a["sport"], "type_key": a.get("type_key"),
            "date": day.isoformat(), "start_local": a["start_local"], "week": week_for(a["start_local"]).isoformat(),
            "distance_m": a.get("distance_m"), "ascent_m": a.get("ascent_m"), "duration_s": a.get("duration_s"),
            "avg_hr": a.get("avg_hr"), "avg_speed_mps": a.get("avg_speed_mps"),
            "points": round(total, 3), "points_distance": round(pts["distance"], 3), "points_ascent": round(pts["ascent"], 3),
            "pence_share": rates.pence(total),
            "flags": flags_for(a), "excluded": ex, "has_track": store.has_track(a["id"]),
            "relabelled": bool(a.get("relabelled")),
        })
    return out


def steps_rows(steps: dict, rows: list[dict]) -> list[dict]:
    """One row per day from STEPS_START with a step count: the count, the miles on foot in
    recorded (unstruck) walks and runs that day, the net, the points."""
    on_foot: dict[str, float] = {}
    for r in rows:
        if r["sport"] in rates.STEPS_DEDUCT_SPORTS and not r["excluded"]:
            on_foot[r["date"]] = on_foot.get(r["date"], 0.0) + (r["distance_m"] or 0) * rates.MILES_PER_METRE
    out = []
    for date in sorted(steps):
        if date < rates.STEPS_START.isoformat():
            continue
        miles = on_foot.get(date, 0.0)
        net, pts = rates.steps_points(steps[date].get("steps"), miles)
        out.append({"date": date, "week": week_of(dt.date.fromisoformat(date)).isoformat(), "steps": int(steps[date].get("steps") or 0),
                    "miles_on_foot": round(miles, 2), "deducted": int(round(miles * rates.STEPS_PER_MILE_DEDUCTED)),
                    "net": net, "points": round(pts, 3)})
    return out


def weeks_from(rows: list[dict], ledger: dict, days: list[dict] | None = None) -> list[dict]:
    """One entry per week from the week of SCHEME_START to this week, newest first, empty weeks included."""
    by_week: dict[str, list[dict]] = {}
    for r in rows:
        by_week.setdefault(r["week"], []).append(r)
    steps_by_week: dict[str, list[dict]] = {}
    for d in days or []:
        steps_by_week.setdefault(d["week"], []).append(d)
    paid = ledger.get("weeks", {})
    out = []
    monday = week_of(rates.SCHEME_START)
    end = this_week()
    if rows or days:   # a watch clock ahead of the calendar, or a selftest run before the scheme opens
        end = max([end] + [dt.date.fromisoformat(r["week"]) for r in rows] + [dt.date.fromisoformat(d["week"]) for d in days or []])
    while monday <= end:
        key = monday.isoformat()
        acts = by_week.get(key, [])
        sdays = steps_by_week.get(key, [])
        steps_pts = sum(d["points"] for d in sdays)
        pts = sum(r["points"] for r in acts) + steps_pts
        capped = min(pts, rates.WEEK_CAP_POINTS) if rates.WEEK_CAP_POINTS else pts
        by_sport: dict[str, dict] = {}
        for r in acts:
            s = by_sport.setdefault(r["sport"], {"n": 0, "distance_m": 0.0, "ascent_m": 0.0, "points": 0.0})
            s["n"] += 1
            s["distance_m"] += r["distance_m"] or 0
            s["ascent_m"] += r["ascent_m"] or 0
            s["points"] += r["points"]
        entry = {
            "monday": key, "label": week_label(monday),
            # a complete week that earned nothing is "empty": neither owed nor waiting to be paid
            "status": "paid" if key in paid else ("current" if monday == end else
                                                 ("owed" if rates.pence(capped) else "empty")),
            "points": round(pts, 3), "points_paid_for": round(capped, 3), "capped": capped < pts,
            "pence": rates.pence(capped), "activities": [r["id"] for r in acts],
            "n_activities": len(acts), "n_flagged": sum(1 for r in acts if r["flags"] and not r["excluded"]),
            "by_sport": {k: {kk: round(vv, 3) if isinstance(vv, float) else vv for kk, vv in v.items()}
                         for k, v in by_sport.items()},
            "paid_on": paid.get(key, {}).get("paid_on"), "paid_note": paid.get(key, {}).get("note"),
            "steps": sum(d["steps"] for d in sdays), "steps_net": sum(d["net"] for d in sdays),
            "steps_deducted": sum(d["deducted"] for d in sdays), "steps_points": round(steps_pts, 3), "steps_days": len(sdays),
        }
        out.append(entry)
        monday += dt.timedelta(days=7)
    out.reverse()
    return out


def build(activities: list[dict] | None = None, ledger: dict | None = None,
          overrides: dict | None = None, steps: dict | None = None) -> dict:
    activities = store.activities() if activities is None else activities
    ledger = store.ledger() if ledger is None else ledger
    overrides = store.overrides() if overrides is None else overrides
    steps = store.steps() if steps is None else steps
    rows = scored_activities(activities, overrides.get("exclude", {}), overrides.get("sport", {}))
    days = steps_rows(steps, rows)
    weeks = weeks_from(rows, ledger, days)
    won = milestones.achieved(rows, days=days)
    by_week_won: dict[str, list] = {}
    for m in won:
        by_week_won.setdefault(week_for(m["date"]).isoformat(), []).append(m)
    for w in weeks:
        w["milestones"] = [{"key": m["key"], "title": m["title"]} for m in by_week_won.get(w["monday"], [])]
    paid_pence = sum(w["pence"] for w in weeks if w["status"] == "paid")
    owed_pence = sum(w["pence"] for w in weeks if w["status"] == "owed")
    current = next((w for w in weeks if w["status"] == "current"), None)
    rows.sort(key=lambda r: r["start_local"], reverse=True)
    return {
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "today": today_uk().isoformat(),
        "scheme": {
            "start": rates.SCHEME_START.isoformat(), "pence_per_point": rates.PENCE_PER_POINT,
            "week_cap_points": rates.WEEK_CAP_POINTS, "sports": list(rates.SPORTS),
            "eggs_start": rates.EGGS_START.isoformat(),
            "steps_start": rates.STEPS_START.isoformat(), "steps_pts_per_10k": rates.STEPS_PTS_PER_10K,
            "steps_per_mile_deducted": rates.STEPS_PER_MILE_DEDUCTED,
            "distance_per_mile": rates.DISTANCE_PER_MILE, "swim_per_100m": rates.SWIM_PTS_PER_100M,
            "ascent_per_m": rates.ASCENT_PTS_PER_M,
        },
        "totals": {
            "points": round(sum(r["points"] for r in rows) + sum(d["points"] for d in days), 3),
            "steps_points": round(sum(d["points"] for d in days), 3), "steps_net": sum(d["net"] for d in days),
            "pence": sum(w["pence"] for w in weeks),
            "paid_pence": paid_pence, "owed_pence": owed_pence,
            "current_pence": current["pence"] if current else 0,
            "activities": len(rows),
            "distance_m": round(sum(r["distance_m"] or 0 for r in rows), 1),
            "ascent_m": round(sum(r["ascent_m"] or 0 for r in rows), 1),
        },
        "weeks": weeks,
        "activities": rows,
        "steps": list(reversed(days)),
        # the Easter eggs: only the WON ones leave the server; the rest are a number
        "milestones": {"won": list(reversed(won)), "hidden": len(milestones.MILESTONES) - len(won),
                       "total": len(milestones.MILESTONES)},
    }


def write_site(data: dict) -> bool:
    """Write docs/data.json and the tracks. Returns False (and leaves the file alone) when nothing
    but the timestamp would change -- so an hourly run with no news makes no commit."""
    store.DOCS.mkdir(exist_ok=True)
    target = store.DOCS / "data.json"
    if target.exists():
        try:
            old = json.loads(target.read_text(encoding="utf-8"))
            if {k: v for k, v in old.items() if k not in ("built_at", "today")} ==                {k: v for k, v in data.items() if k not in ("built_at", "today")}:
                return False
        except ValueError:
            pass
    target.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    dest = store.DOCS / "tracks"
    dest.mkdir(exist_ok=True)
    wanted = {f"{r['id']}.json" for r in data["activities"] if r["has_track"]}
    for p in dest.glob("*.json"):
        if p.name not in wanted:
            p.unlink()
    for name in wanted:
        src = store.TRACKS / name
        if src.exists():
            shutil.copyfile(src, dest / name)
    return True


def print_table(data: dict) -> None:
    t = data["totals"]
    print(f"Argo -- {t['activities']} activities, {t['points']:.1f} points, {rates.gbp(t['pence'])} "
          f"(paid {rates.gbp(t['paid_pence'])}, owed {rates.gbp(t['owed_pence'])}, "
          f"this week {rates.gbp(t['current_pence'])})")
    for w in data["weeks"]:
        print(f"  {w['label']:>22}  {w['status']:7}  {w['n_activities']:2} acts  {w['points']:6.1f} pts  "
              f"{rates.gbp(w['pence']):>8}" + ("  CAPPED" if w["capped"] else "")
              + (f"  {w['n_flagged']} flagged" if w["n_flagged"] else "")
              + (f"  steps {w['steps_net']:,} net = {w['steps_points']:.1f} pts" if w["steps_days"] else ""))
    for r in data["activities"]:
        note = " | ".join(r["flags"]) if r["flags"] else ""
        if r["excluded"]:
            note = f"STRUCK: {r['excluded']}"
        print(f"    {r['start_local'][:16]}  {r['sport']:5}  {(r['distance_m'] or 0) / 1000:5.1f} km "
              f"{(r['ascent_m'] or 0):4.0f} m  {r['points']:5.1f} pts  {r['name']}" + (f"  [{note}]" if note else ""))


def selftest() -> None:
    acts = [
        {"id": 1, "name": "Run", "sport": "run", "type_key": "running", "start_local": "2026-09-22 16:00:00",
         "distance_m": 1609.344, "ascent_m": 25.0, "duration_s": 600, "avg_hr": 150, "avg_speed_mps": 2.7},
        {"id": 2, "name": "Ride", "sport": "cycle", "type_key": "cycling", "start_local": "2026-09-23 16:00:00",
         "distance_m": 16093.44, "ascent_m": 100.0, "duration_s": 3600, "avg_hr": None, "avg_speed_mps": 4.5},
        {"id": 3, "name": "Car", "sport": "cycle", "type_key": "cycling", "start_local": "2026-09-29 16:00:00",
         "distance_m": 16093.44, "ascent_m": 0, "duration_s": 600, "avg_hr": 90, "avg_speed_mps": 26.8},
        {"id": 4, "name": "PE", "sport": "other", "type_key": "football", "start_local": "2026-09-29 12:00:00",
         "distance_m": 3000, "ascent_m": 0, "duration_s": 3600, "avg_hr": 140, "avg_speed_mps": 1.0},
        {"id": 5, "name": "Old", "sport": "run", "type_key": "running", "start_local": "2026-04-30 16:00:00",
         "distance_m": 5000, "ascent_m": 0, "duration_s": 1500, "avg_hr": 150, "avg_speed_mps": 3.3},
    ]
    ledger = {"weeks": {"2026-09-21": {"paid_on": "2026-09-28"}}}
    steps = {"2026-09-22": {"steps": 14000}, "2026-09-23": {"steps": 8000}, "2026-09-30": {"steps": 11000}, "2026-09-20": {"steps": 99999}}
    d = build(acts, ledger, {"exclude": {"3": "that was the car"}, "sport": {"4": "kayak"}}, steps)
    days = {x["date"]: x for x in d["steps"]}
    assert "2026-09-20" not in days, "before STEPS_START must not count"
    assert days["2026-09-22"]["miles_on_foot"] == 1.0 and days["2026-09-22"]["deducted"] == 0   # gross: the mile run costs nothing
    assert days["2026-09-22"]["net"] == 14000 and days["2026-09-22"]["points"] == 2.8
    assert days["2026-09-23"]["net"] == 8000 and days["2026-09-30"]["points"] == 2.2
    w = {x["monday"]: x for x in d["weeks"]}
    assert w["2026-09-21"]["steps_points"] == 4.4 and w["2026-09-21"]["points"] == 20.4 and w["2026-09-21"]["pence"] == 510
    assert w["2026-09-28"]["steps_points"] == 2.2 and w["2026-09-28"]["pence"] == 241   # 2.2 pts of steps + the relabelled kayak
    d = build(acts, ledger, {"exclude": {"3": "that was the car"}, "sport": {"4": "kayak"}}, {})
    rows = {r["id"]: r for r in d["activities"]}
    assert rows[4]["sport"] == "kayak" and rows[4]["points"] > 0 and rows[4]["relabelled"] and rows[4]["flags"] == []
    d = build(acts, ledger, {"exclude": {"3": "that was the car"}})
    rows = {r["id"]: r for r in d["activities"]}
    assert 5 not in rows, "before SCHEME_START must not score"
    assert rows[1]["points"] == 5.0 and rows[1]["flags"] == []
    assert rows[2]["points"] == 11.0 and rows[2]["flags"] == ["no heart rate recorded"]
    assert rows[3]["points"] == 0.0 and rows[3]["excluded"] == "that was the car"
    assert any("over the cycle ceiling" in f for f in rows[3]["flags"])
    assert rows[4]["points"] == 0.0 and rows[4]["flags"][0].startswith("not a scored sport")
    weeks = {w["monday"]: w for w in d["weeks"]}
    w1, w2 = weeks["2026-09-21"], weeks["2026-09-28"]
    assert w1["status"] == "paid" and w1["points"] == 16.0 and w1["pence"] == 400 and w1["paid_on"] == "2026-09-28"
    assert w2["points"] == 0.0 and w2["n_flagged"] == 1, w2      # id 3 is struck, id 4 still flagged
    assert d["totals"]["paid_pence"] == 400
    won = {m["key"]: m for m in d["milestones"]["won"]}
    assert rates.EGGS_START <= dt.date(2026, 9, 22), "fixture predates EGGS_START; move the fixture"
    assert {"first", "first_run", "run_1mi", "first_cycle", "cycle_5mi", "cycle_10mi", "climb_100"} <= set(won), won.keys()
    assert "pace_10" in won and "pace_9" not in won and won["run_1mi"]["date"] == "2026-09-22"   # 2.7 m/s = 9.9 min/mi
    assert d["milestones"]["hidden"] == d["milestones"]["total"] - len(won)
    assert [m["title"] for m in weeks["2026-09-21"]["milestones"]] and weeks["2026-09-28"]["milestones"] == []
    assert d["weeks"][0]["monday"] == max(this_week(), dt.date(2026, 9, 28)).isoformat()
    assert d["weeks"][-1]["monday"] == week_of(rates.SCHEME_START).isoformat()
    # the cap
    old = rates.WEEK_CAP_POINTS
    rates.WEEK_CAP_POINTS = 10.0
    try:
        w = {x["monday"]: x for x in build(acts, ledger, {"exclude": {}})["weeks"]}["2026-09-21"]
        assert w["capped"] and w["points"] == 16.0 and w["points_paid_for"] == 10.0 and w["pence"] == 250
    finally:
        rates.WEEK_CAP_POINTS = old
    assert last_week() < this_week()
    print("score: selftest OK")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--print", action="store_true", help="print the table as well")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    data = build()
    changed = write_site(data)
    if a.print:
        print_table(data)
    t = data["totals"]
    print(f"docs/data.json {'written' if changed else 'unchanged'}: {t['activities']} activities, {len(data['weeks'])} weeks, "
          f"{rates.gbp(t['pence'])} earned, {rates.gbp(t['owed_pence'])} owed")


if __name__ == "__main__":
    main()
