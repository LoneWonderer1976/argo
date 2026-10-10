"""records.py -- Thomas's personal bests: the tables of his best activities, and the records he breaks.

Ben, 10/10/2026: "Tom gets a banner whenever he breaks a PB, longest cycle, most meters climbed
etc etc and also give him tables of his best activities, walking, cycling etc".

    python -m argo.records            # print his tables and every record broken since RECORDS_START
    python -m argo.records --selftest

Derived on every run like everything else: a strike, a relabel or a new sync re-ranks the lot.

- **The tables are his whole history**, before Argo included: a personal best is a best ever, not
  a best since the pocket money began. Struck activities never count, and neither does one over
  its sport's speed ceiling (`rates.MAX_SPEED_MPS` -- that is the car, whatever the flag says).
- **A record is broken** when an activity beats every earlier one at the precision the page
  prints (0.1 mile, a metre, a minute, a second of pace, 0.1 mph): "10.0 mi beats 10.0 mi" is
  not a record. A first ever (no earlier one to beat) is not a break, it is the Easter eggs' job.
- **Breaks are cheered from RECORDS_START** (a setting). The walk through history before it only
  sets the bar, so the first sync after the build does not fire a backlog of banners.
- **Fastest is in the tables but never cheered on a bike** -- the bounty's reasoning (ARGO_BRIEF,
  08/10): a speed prize rewards rushing on the roads.
"""
import argparse
import datetime as dt

from . import rates

MI = 1609.344
NOUN = {"run": "run", "walk": "walk", "cycle": "ride", "swim": "swim", "kayak": "paddle"}
METRICS = ("distance", "climb", "time", "speed")
CLIMB_SPORTS = ("run", "walk", "cycle")
# the shortest outing that may hold a speed record: a 200 m dash is not his fastest run
SPEED_MIN_M = {"run": MI, "walk": MI, "cycle": 3 * MI, "swim": 100.0, "kayak": MI}
NO_CHEER = {("cycle", "speed")}
TOP_N = 5


def metric_value(a: dict, metric: str) -> float | None:
    """The raw number one activity offers a metric, or None when it has none to offer."""
    sport = a["sport"]
    if metric == "distance":
        return a.get("distance_m") or None
    if metric == "climb":
        return (a.get("ascent_m") or None) if sport in CLIMB_SPORTS else None
    if metric == "time":
        return a.get("duration_s") or None
    if metric == "speed":
        v = a.get("avg_speed_mps")
        return v if v and (a.get("distance_m") or 0) >= SPEED_MIN_M[sport] else None
    raise ValueError(metric)


def shown(metric: str, sport: str, v: float) -> float:
    """The value at the precision the page prints, bigger always better -- what a break must beat."""
    if metric == "distance":
        return round(v / 10) if sport == "swim" else round(v / MI, 1)
    if metric == "climb":
        return round(v)
    if metric == "time":
        return int(round(v) // 60)              # whole minutes, floored as the page's dur() prints them
    if metric == "steps":
        return int(v)
    if sport in ("run", "walk"):
        return -round(MI / v)                    # pace in whole seconds a mile: fewer is better
    if sport == "swim":
        return -round(100 / v)
    return round(v * 2.23694, 1)                 # mph


def counts(a: dict) -> bool:
    if a["sport"] not in NOUN or a.get("excluded"):
        return False
    ceiling = rates.MAX_SPEED_MPS.get(a["sport"])
    return not (ceiling and (a.get("avg_speed_mps") or 0) > ceiling)


def title(sport: str, metric: str) -> str:
    n = NOUN.get(sport, sport)
    return {"distance": f"Longest {n}", "climb": f"Most climbing on a {n}", "time": f"Longest time on a {n}",
            "speed": f"Fastest {n}", "steps": "Most steps in a day"}[metric]


def _entry(a: dict, metric: str, v: float) -> dict:
    return {"id": a["id"], "date": a["date"], "name": a.get("name") or a["sport"], "value": round(v, 3),
            "history": bool(a.get("history"))}


def build(rows: list[dict], days: list[dict], start: dt.date | None = None) -> dict:
    """rows: score's scored activities, history INCLUDED; days: score's steps rows.
    -> {"tables": {sport: {metric: [top N]}}, "breaks": [...], "start": iso}."""
    start = start or rates.RECORDS_START
    acts = sorted((a for a in rows if counts(a)), key=lambda a: a["start_local"])
    tables: dict[str, dict] = {}
    breaks: list[dict] = []
    best: dict[tuple, dict] = {}

    def walk(key: tuple, item: dict, v: float, sport: str, metric: str) -> None:
        held = best.get(key)
        if held is None or shown(metric, sport, v) > shown(metric, sport, held["value"]):
            if held is not None and dt.date.fromisoformat(item["date"]) >= start and key not in NO_CHEER:
                breaks.append({"key": f"{sport}:{metric}:{item['date']}:{item['id']}", "sport": sport, "metric": metric,
                               "title": title(sport, metric), **item, "prev_value": held["value"], "prev_date": held["date"]})
            best[key] = item

    for a in acts:
        for metric in METRICS:
            v = metric_value(a, metric)
            if v is None:
                continue
            item = _entry(a, metric, v)
            tables.setdefault(a["sport"], {}).setdefault(metric, []).append(item)
            walk((a["sport"], metric), item, v, a["sport"], metric)
    for d in sorted(days, key=lambda d: d["date"]):
        if d["steps"]:
            item = {"id": None, "date": d["date"], "name": "", "value": d["steps"], "history": False}
            tables.setdefault("steps", {}).setdefault("steps", []).append(item)
            walk(("steps", "steps"), item, d["steps"], "steps", "steps")
    for sport, ms in tables.items():
        for metric, items in ms.items():
            ms[metric] = sorted(items, key=lambda i: (-shown(metric, sport, i["value"]), i["date"]))[:TOP_N]
    return {"tables": tables, "breaks": breaks, "start": start.isoformat()}


def say(sport: str, metric: str, v: float) -> str:
    """A value in his units, as the page prints it."""
    if metric == "distance":
        return f"{v:.0f} m" if sport == "swim" else f"{v / MI:.1f} mi"
    if metric == "climb":
        return f"{v:.0f} m"
    if metric == "time":
        m = int(round(v) // 60)
        return f"{m // 60}h {m % 60:02d}m" if m >= 60 else f"{m} min"
    if metric == "steps":
        return f"{int(v):,} steps"
    if sport in ("run", "walk"):
        s = round(MI / v)
        return f"{s // 60}:{s % 60:02d} /mi"
    if sport == "swim":
        s = round(100 / v)
        return f"{s // 60}:{s % 60:02d} /100 m"
    return f"{v * 2.23694:.1f} mph"


def selftest() -> None:
    def act(i, sport, day, dist_mi, climb, mins, mps=2.0, history=False, excluded=None):
        return {"id": i, "sport": sport, "date": day, "start_local": day + " 10:00:00", "name": f"#{i}",
                "distance_m": dist_mi * MI, "ascent_m": climb, "duration_s": mins * 60, "avg_speed_mps": mps,
                "history": history, "excluded": excluded}
    rows = [act(1, "cycle", "2025-06-01", 8.0, 50, 60, 4.0, history=True),
            act(2, "cycle", "2026-10-11", 8.04, 80, 70, 4.5),        # 8.0 mi again: no distance break; climb and time are
            act(3, "cycle", "2026-10-12", 12.0, 20, 50, 30.0),        # the car: over the ceiling, never a record
            act(4, "cycle", "2026-10-13", 9.0, 10, 40, 6.0, excluded="struck"),
            act(5, "walk", "2026-10-11", 3.0, 30, 60, 1.4),            # a first walk: no break to report
            act(6, "walk", "2026-10-12", 0.5, 5, 10, 2.5),            # under a mile: never the fastest walk
            act(7, "cycle", "2026-10-14", 10.0, 0, 30, 9.0),          # faster, but a bike's speed is never cheered
            act(8, "cycle", "2026-10-01", 9.5, 0, 20, 3.0)]           # before RECORDS_START: sets the bar silently
    days = [{"date": "2026-10-09", "steps": 9000}, {"date": "2026-10-12", "steps": 12000}, {"date": "2026-10-13", "steps": 12000}]
    r = build(rows, days, dt.date(2026, 10, 10))
    got = {(b["sport"], b["metric"], b["id"]) for b in r["breaks"]}
    assert got == {("cycle", "climb", 2), ("cycle", "time", 2), ("cycle", "distance", 7), ("steps", "steps", None)}, got
    b = next(b for b in r["breaks"] if b["metric"] == "distance")
    assert b["prev_date"] == "2026-10-01" and b["title"] == "Longest ride", b
    t = r["tables"]["cycle"]
    assert [i["id"] for i in t["distance"]] == [7, 8, 1, 2], t["distance"]      # 1 and 2 tie at 8.0: the earlier ranks first
    assert 3 not in [i["id"] for m in t.values() for i in m] and 4 not in [i["id"] for m in t.values() for i in m]
    assert t["speed"][0]["id"] == 7 and t["distance"][2]["history"]
    assert [i["id"] for i in r["tables"]["walk"]["speed"]] == [5] and r["tables"]["steps"]["steps"][0]["date"] == "2026-10-12"
    assert say("run", "speed", MI / 540) == "9:00 /mi" and say("cycle", "distance", 10 * MI) == "10.0 mi" and say("walk", "time", 3900) == "1h 05m"
    print("records: selftest OK")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    from . import score, store
    every = score.scored_activities(store.activities(), store.overrides().get("exclude", {}), store.overrides().get("sport", {}))
    r = build(every, score.steps_rows(store.steps(), score.paid_rows(every)))
    for sport, ms in r["tables"].items():
        for metric, items in ms.items():
            print(f"{title(sport, metric)}: " + "; ".join(f"{say(sport, metric, i['value'])} {i['date']}" for i in items))
    print(f"{len(r['breaks'])} record(s) broken since {r['start']}")
    for b in r["breaks"]:
        print(f"  {b['date']}  {b['title']}: {say(b['sport'], b['metric'], b['value'])} "
              f"(was {say(b['sport'], b['metric'], b['prev_value'])}, {b['prev_date']})")


if __name__ == "__main__":
    main()
