"""sync.py -- Garmin Connect -> data/. Fetches what is new, touches nothing that is stored.

    python -m argo.sync            # normal run: everything since the newest stored activity
    python -m argo.sync --since 2026-09-01   # re-open the window (stored files still win)
    python -m argo.sync --dry-run  # list what it would fetch, write nothing

LOGIN. Garmin tokens come from the GARMINTOKENS environment variable (the string that
`python -m argo.login` prints -- in GitHub Actions it is a repository secret), or from a local
`.garmin_tokens/` folder that login.py leaves behind on Ben's PC. Nothing here ever sees a
password.

WINDOW. From the later of SCHEME_START and the day before the newest stored activity, to today.
Garmin is asked for summaries in that window; an id already in data/activities is skipped, so
a re-run is free and a widened window is safe. The summary is what Garmin's own list returns
(distance, ascent, duration, heart rate, speed -- everything the rate table needs); the track
comes from the GPX download, thinned to TRACK_POINTS for the phone map, and is only asked for
when the summary says there is one.
"""
import argparse
import datetime as dt
import os
import sys
import xml.etree.ElementTree as ET

from . import store
from .rates import SCHEME_START, STEPS_START
from .sports import sport_for
from .weeks import today_uk

TOKEN_DIR = store.ROOT / ".garmin_tokens"
TRACK_POINTS = 400


def log(msg: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def login():
    try:
        from garminconnect import Garmin
    except ImportError:
        sys.exit("garminconnect is not installed:  pip install garminconnect")
    tokens = os.environ.get("GARMINTOKENS")
    if tokens and len(tokens) > 512:
        api = Garmin()
        api.login(tokens)
        log("logged in from GARMINTOKENS")
        return api
    if TOKEN_DIR.exists():
        api = Garmin()
        api.login(str(TOKEN_DIR))
        log(f"logged in from {TOKEN_DIR.name}/")
        return api
    sys.exit("no Garmin tokens: run `python -m argo.login` once, or set GARMINTOKENS")


def summary_row(a: dict) -> dict:
    """Argo's row from a Garmin list entry. The entry itself rides along as `raw`."""
    type_key = (a.get("activityType") or {}).get("typeKey")
    return {
        "id": int(a["activityId"]),
        "name": (a.get("activityName") or "").strip(),
        "type_key": type_key,
        "sport": sport_for(type_key),
        "start_local": (a.get("startTimeLocal") or "")[:19],
        "start_gmt": (a.get("startTimeGMT") or "")[:19],
        "duration_s": a.get("duration"),
        "moving_s": a.get("movingDuration"),
        "distance_m": a.get("distance"),
        "ascent_m": a.get("elevationGain"),
        "descent_m": a.get("elevationLoss"),
        "avg_speed_mps": a.get("averageSpeed"),
        "max_speed_mps": a.get("maxSpeed"),
        "avg_hr": a.get("averageHR"),
        "max_hr": a.get("maxHR"),
        "calories": a.get("calories"),
        "steps": a.get("steps"),
        "start_lat": a.get("startLatitude"),
        "start_lon": a.get("startLongitude"),
        "has_polyline": bool(a.get("hasPolyline")),
        "synced_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "raw": a,
    }


def gpx_points(gpx: bytes) -> list[list[float]]:
    """Every trkpt in a GPX, as [lat, lon] rounded to ~1 m."""
    root = ET.fromstring(gpx)
    pts = []
    for el in root.iter():
        if el.tag.endswith("}trkpt") or el.tag == "trkpt":
            try:
                pts.append([round(float(el.get("lat")), 5), round(float(el.get("lon")), 5)])
            except (TypeError, ValueError):
                continue
    return pts


def thin(points: list, n: int = TRACK_POINTS) -> list:
    """At most n points, evenly spaced along the list, first and last always kept."""
    if len(points) <= n:
        return points
    step = (len(points) - 1) / (n - 1)
    return [points[round(i * step)] for i in range(n)]


def window_start(since: str | None) -> dt.date:
    if since:
        return dt.date.fromisoformat(since)
    rows = store.activities()
    if rows:
        newest = dt.date.fromisoformat(rows[-1]["start_local"][:10])
        return max(SCHEME_START, newest - dt.timedelta(days=1))
    return SCHEME_START


STEPS_REFETCH_DAYS = 3      # a day's count grows until midnight; the last few days are always re-read


def sync_steps(api, dry_run: bool = False) -> int:
    """Daily step counts from STEPS_START, the last STEPS_REFETCH_DAYS days re-read every run."""
    end = today_uk()
    if end < STEPS_START:
        return 0
    have = store.steps()
    settled = [d for d in have if d < (end - dt.timedelta(days=STEPS_REFETCH_DAYS)).isoformat()]
    start = max(STEPS_START, dt.date.fromisoformat(max(settled)) + dt.timedelta(days=1)) if settled else STEPS_START
    start = min(start, end - dt.timedelta(days=STEPS_REFETCH_DAYS))
    start = max(start, STEPS_START)
    try:
        days = api.get_daily_steps(str(start), str(end)) or []
    except Exception as e:
        log(f"WARNING: could not read daily steps ({e})")
        return 0
    n = 0
    for d in days:
        date = d.get("calendarDate")
        if not date or date < STEPS_START.isoformat():
            continue
        row = {"steps": int(d.get("totalSteps") or 0), "distance_m": d.get("totalDistance"), "goal": d.get("stepGoal"),
               "synced_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        if have.get(date, {}).get("steps") != row["steps"]:
            n += 1
        have[date] = row
    log(f"steps: {len(days)} days read from {start}, {n} changed")
    if not dry_run and days:
        store.write_steps(have)
    return n


def run(since: str | None = None, dry_run: bool = False) -> int:
    start = window_start(since)
    end = today_uk()
    if start > end:
        log(f"the scheme opens {SCHEME_START}; nothing to fetch yet")
        return 0
    api = login()
    sync_steps(api, dry_run)
    log(f"asking Garmin for activities {start} .. {end}")
    listed = api.get_activities_by_date(str(start), str(end)) or []
    have = store.activity_ids()
    new = [a for a in listed if a.get("activityId") is not None and int(a["activityId"]) not in have]
    log(f"Garmin lists {len(listed)}; {len(new)} new")
    fetched = 0
    for a in sorted(new, key=lambda a: a.get("startTimeLocal") or ""):
        row = summary_row(a)
        km = (row["distance_m"] or 0) / 1000
        log(f"  {row['start_local'][:16]}  {row['sport']:5}  {km:5.1f} km  {row['name']}"
            + ("  [track]" if row["has_polyline"] else ""))
        if dry_run:
            continue
        if row["start_local"] and dt.date.fromisoformat(row["start_local"][:10]) < SCHEME_START:
            continue   # before the ledger opened -- never stored, never paid
        if row["has_polyline"]:
            try:
                from garminconnect import Garmin
                gpx = api.download_activity(row["id"], dl_fmt=Garmin.ActivityDownloadFormat.GPX)
                pts = gpx_points(gpx)
                if pts:
                    store.write_track(row["id"], thin(pts), len(pts))
            except Exception as e:      # a missing track is a missing map, not a missing payment
                log(f"    track download failed ({e}); summary still stored")
        store.write_activity(row)
        fetched += 1
    log(f"stored {fetched} new activities" if not dry_run else "dry run -- nothing written")
    return fetched


def selftest() -> None:
    gpx = b"""<?xml version="1.0"?><gpx xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>
      <trkpt lat="50.9123456" lon="-1.2345678"><ele>40</ele></trkpt>
      <trkpt lat="50.9124" lon="-1.2346"/></trkseg></trk></gpx>"""
    assert gpx_points(gpx) == [[50.91235, -1.23457], [50.9124, -1.2346]]
    pts = [[i, i] for i in range(1000)]
    t = thin(pts, 400)
    assert len(t) == 400 and t[0] == [0, 0] and t[-1] == [999, 999]
    assert thin(pts[:10], 400) == pts[:10]
    row = summary_row({"activityId": "7", "activityName": " Lunch Run ", "activityType": {"typeKey": "trail_running"},
                       "startTimeLocal": "2026-09-22 16:05:00.0", "distance": 3200.0, "elevationGain": 41.2,
                       "duration": 1500.5, "hasPolyline": True})
    assert row["id"] == 7 and row["sport"] == "run" and row["start_local"] == "2026-09-22 16:05:00"
    assert row["name"] == "Lunch Run" and row["raw"]["activityId"] == "7" and row["ascent_m"] == 41.2
    assert summary_row({"activityId": 1})["sport"] == "other"
    print("sync: selftest OK")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", help="re-open the window from this date (YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    run(a.since, a.dry_run)


if __name__ == "__main__":
    main()
