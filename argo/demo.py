"""demo.py -- write a made-up docs/data.json so the page can be looked at before the first sync.

    python -m argo.demo

Touches nothing in data/. The next `python -m argo.score` (or the hourly Action) overwrites it
with the real thing. The made-up activities start on SCHEME_START.
"""
import datetime as dt
import math
import random

from . import rates, score, store


def _track(lat, lon, n=120, r=0.004):
    return [[round(lat + r * math.sin(2 * math.pi * i / n), 5), round(lon + r * 1.6 * math.cos(2 * math.pi * i / n), 5)]
            for i in range(n + 1)]


def main() -> None:
    rnd = random.Random(7)
    acts, day = [], rates.EGGS_START      # from the eggs' start, so the demo shows some won
    plan = [("run", "running", 2.4, 30), ("walk", "walking", 4.0, 40), ("cycle", "cycling", 12.0, 90),
            ("swim", "lap_swimming", 0.6, 0), ("run", "trail_running", 3.1, 55), ("cycle", "mountain_biking", 9.0, 140),
            ("walk", "hiking", 6.5, 210), ("other", "football", 3.0, 0), ("kayak", "kayaking", 3.2, 0)]
    for i in range(16):
        sport, key, km, climb = plan[i % len(plan)]
        d = day + dt.timedelta(days=i * 1.6 // 1)
        speed = {"run": 2.9, "walk": 1.4, "cycle": 5.2, "swim": 0.8, "kayak": 1.6, "other": 1.0}[sport] * rnd.uniform(.9, 1.1)
        dist = km * 1000 * rnd.uniform(.85, 1.15)
        acts.append({"id": 90000 + i, "name": f"{key.replace('_', ' ').title()}", "sport": sport, "type_key": key,
                     "start_local": f"{d} {rnd.randint(8, 18):02d}:{rnd.randint(0, 59):02d}:00",
                     "distance_m": round(dist, 1), "ascent_m": round(climb * rnd.uniform(.7, 1.3), 1),
                     "duration_s": round(dist / speed), "avg_hr": None if i == 5 else rnd.randint(120, 175),
                     "avg_speed_mps": round(speed * (5 if i == 11 else 1), 2)})
    for a in acts:
        a["_track"] = _track(50.92 + rnd.uniform(-.02, .02), -1.29 + rnd.uniform(-.02, .02)) if a["sport"] not in ("swim", "other") else None
    first = rates.EGGS_START - dt.timedelta(days=rates.EGGS_START.weekday())
    ledger = {"weeks": {first.isoformat(): {"paid_on": (first + dt.timedelta(days=7)).isoformat()}}}
    steps = {}
    sd = rates.STEPS_START
    while sd <= max(dt.date.today(), rates.STEPS_START + dt.timedelta(days=20)):
        steps[sd.isoformat()] = {"steps": rnd.randint(3000, 19000)}
        sd += dt.timedelta(days=1)
    real_has_track = store.has_track
    store.has_track = lambda i: any(a["id"] == i and a["_track"] for a in acts)
    try:
        data = score.build(acts, ledger, {"exclude": {"90011": "that was the car"}}, steps)
    finally:
        store.has_track = real_has_track
    store.DOCS.mkdir(exist_ok=True)
    (store.DOCS / "tracks").mkdir(exist_ok=True)
    import json
    (store.DOCS / "data.json").write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    for a in acts:
        if a["_track"]:
            (store.DOCS / "tracks" / f"{a['id']}.json").write_text(json.dumps({"id": a["id"], "points": a["_track"]}))
    print(f"DEMO data.json written ({len(acts)} made-up activities) -- `python -m argo.score` puts the real one back")


if __name__ == "__main__":
    main()
