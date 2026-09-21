"""rates.py -- THE RATE TABLE. Every number that turns an activity into money lives here.

Argo pays points for distance and ascent at the same rates Nostos Datum pays Ben (20/09/2026,
"nominally use the same basic activity scores for distance and ascent as those I use"), and
converts points to pocket money at PENCE_PER_POINT. Nothing else in the app holds a rate.

At 25p a point:  GBP 1.00 per mile run or kayaked, 50p per mile walked, 25p per mile cycled,
GBP 0.25 per 100 m swum; 1p per metre climbed running, 1/2p walking, 1/4p cycling.

Change a number here and the whole ledger re-scores on the next run -- points are derived from
the stored activities every time, never cached (Nostos Datum's second prime directive).

THESE ARE THE DEFAULTS. Ben overrides any of them without touching code -- `python -m argo.settings`,
the `settings` workflow's form on GitHub, or `set <key> <value>` on a statement issue -- and the
overrides live in data/settings.json, read at the bottom of this file as it imports, so every
module that imports a constant from here sees the override. `DEFAULTS` keeps the original values
for the settings report. ARGO_NO_SETTINGS=1 in the environment skips the file (check.py sets it
so the selftests test the defaults).
"""
import datetime as dt
import json
import os
from pathlib import Path

# --- the scheme -----------------------------------------------------------------------------
SCHEME_START = dt.date(2026, 5, 1)      # the day the ledger opens (Ben, 20/09: "backdate to 1st May"). Nothing before it earns.
EGGS_START = dt.date(2026, 9, 21)       # the Easter eggs count from here (Ben, 20/09: the backdated months must not
                                        # burn through them on the first load). Set it to SCHEME_START to count history.
PENCE_PER_POINT = 25
WEEK_CAP_POINTS = None                  # a ceiling on points paid per week; None = no cap (Ben, later)

# --- steps (Ben, 20/09/2026: "25p per 10,000 steps ... don't backdate this, start from tomorrow";
# a deduction of 2,000 steps per recorded mile on foot was asked for and withdrawn the same
# minute -- "make it gross, 25p per 10,000 irrespective" -- so the dial exists and sits at 0) ----
STEPS_START = dt.date(2026, 9, 21)
STEPS_PTS_PER_10K = 2.0                 # 10,000 steps = 2 points = 50p, gross (Ben, 21/09: was 25p for a day)
STEPS_PER_MILE_DEDUCTED = 0             # steps per recorded mile on foot NOT paid; 0 = gross (Ben)
STEPS_DEDUCT_SPORTS = ("walk", "run")

# --- sports ---------------------------------------------------------------------------------
# Ben, 20/09/2026: walking, cycling, running, swimming and kayaking, "we can add more if needed".
SPORTS = ("run", "walk", "cycle", "swim", "kayak")

DISTANCE_PER_MILE = {"cycle": 1.0, "walk": 2.0, "run": 4.0, "kayak": 4.0}
SWIM_PTS_PER_100M = 1.0
ASCENT_PTS_PER_M = {"cycle": 1.0 / 100, "walk": 1.0 / 50, "run": 1.0 / 25}

MILES_PER_METRE = 1.0 / 1609.344

# --- plausibility (flags, never refusals; Ben adjudicates on the statement) -------------------
# A "bike ride" at 40 mph is the car; a "run" at 4-minute miles is the bike; a walk with no
# movement and no heart rate is a watch left recording. These are generous ceilings, and a flag
# still pays -- it is printed on the weekly statement so Ben can strike it (data/overrides.json).
MAX_SPEED_MPS = {"run": 6.5, "walk": 3.0, "cycle": 16.0, "swim": 2.5, "kayak": 5.0}
MIN_DISTANCE_M = 100.0                  # below this an activity is noise and earns nothing


def points_for(sport: str, distance_m: float | None, ascent_m: float | None) -> dict:
    """Points for one activity, by channel. Unknown sport or no distance -> zero, never None."""
    out = {"distance": 0.0, "ascent": 0.0}
    if sport not in SPORTS or not distance_m or distance_m < MIN_DISTANCE_M:
        return out
    if sport == "swim":
        out["distance"] = distance_m / 100.0 * SWIM_PTS_PER_100M
    else:
        out["distance"] = distance_m * MILES_PER_METRE * DISTANCE_PER_MILE[sport]
    if ascent_m and sport in ASCENT_PTS_PER_M:
        out["ascent"] = ascent_m * ASCENT_PTS_PER_M[sport]
    return out


def steps_points(steps: int | None, miles_on_foot: float) -> tuple[int, float]:
    """(net steps, points) for one day: the day's steps less 2,000 per recorded mile on foot,
    never below zero."""
    net = max(0, int(steps or 0) - int(round(miles_on_foot * STEPS_PER_MILE_DEDUCTED)))
    return net, net / 10000.0 * STEPS_PTS_PER_10K


def pence(points: float) -> int:
    """Whole pence for a points total -- round half up, on the TOTAL, never per activity."""
    return int(points * PENCE_PER_POINT + 0.5)


def gbp(pence_: int) -> str:
    return f"£{pence_ / 100:.2f}"


def selftest() -> None:
    p = points_for("run", 1609.344, 25)
    assert abs(p["distance"] - 4.0) < 1e-9 and abs(p["ascent"] - 1.0) < 1e-9, p
    assert points_for("walk", 1609.344, 50) == {"distance": 2.0, "ascent": 1.0}
    assert points_for("cycle", 16093.44, 100)["distance"] == 10.0
    assert points_for("swim", 500, 0)["distance"] == 5.0
    assert points_for("kayak", 1609.344, 100) == {"distance": 4.0, "ascent": 0.0}   # no ascent at sea
    assert points_for("football", 5000, 0) == {"distance": 0.0, "ascent": 0.0}
    assert points_for("run", None, 0) == {"distance": 0.0, "ascent": 0.0}
    assert points_for("run", 50, 0) == {"distance": 0.0, "ascent": 0.0}            # under the floor
    assert steps_points(12000, 0) == (12000, 2.4) and steps_points(12000, 5.0) == (12000, 2.4)   # gross, 2 pts per 10k
    assert steps_points(None, 0) == (0, 0.0)
    assert STEPS_START >= SCHEME_START
    assert pence(4.0) == 100 and pence(0.019) == 0 and pence(0.02) == 1 and pence(3.999) == 100
    assert gbp(1234) == "£12.34"
    assert EGGS_START >= SCHEME_START
    print("rates: selftest OK")


if __name__ == "__main__":
    selftest()


# --- Ben's overrides, applied last so everything above is a default --------------------------
# key -> (attribute here, type, note). Type is int / float / "date" / "int?" (int or none) /
# "per100" (entered per 100 m, stored per metre). settings.py is the front door; this is the table.
SETTINGS = {
    "pence_per_point":         ("PENCE_PER_POINT", int, "pence paid per point"),
    "week_cap_points":         ("WEEK_CAP_POINTS", "int?", "most points paid in a week; 'none' = no cap"),
    "scheme_start":            ("SCHEME_START", "date", "the day the ledger opens"),
    "eggs_start":              ("EGGS_START", "date", "the day the Easter eggs start counting"),
    "steps_start":             ("STEPS_START", "date", "the day steps start counting"),
    "steps_pts_per_10k":       ("STEPS_PTS_PER_10K", float, "points per 10,000 steps"),
    "steps_per_mile_deducted": ("STEPS_PER_MILE_DEDUCTED", int, "steps not paid per recorded mile on foot (0 = gross)"),
    "run_per_mile":            ("DISTANCE_PER_MILE.run", float, "points per mile run"),
    "walk_per_mile":           ("DISTANCE_PER_MILE.walk", float, "points per mile walked"),
    "cycle_per_mile":          ("DISTANCE_PER_MILE.cycle", float, "points per mile cycled"),
    "kayak_per_mile":          ("DISTANCE_PER_MILE.kayak", float, "points per mile paddled"),
    "swim_per_100m":           ("SWIM_PTS_PER_100M", float, "points per 100 m swum"),
    "run_ascent_per_100m":     ("ASCENT_PTS_PER_M.run", "per100", "points per 100 m climbed running"),
    "walk_ascent_per_100m":    ("ASCENT_PTS_PER_M.walk", "per100", "points per 100 m climbed walking"),
    "cycle_ascent_per_100m":   ("ASCENT_PTS_PER_M.cycle", "per100", "points per 100 m climbed cycling"),
    "min_distance_m":          ("MIN_DISTANCE_M", float, "an activity shorter than this earns nothing"),
}


def current(key: str):
    attr = SETTINGS[key][0]
    if "." in attr:
        d, k = attr.split(".")
        return globals()[d][k]
    return globals()[attr]


def apply_overrides(overrides: dict) -> list[str]:
    """Push each override onto this module. Returns the keys that were unknown (ignored, never fatal)."""
    bad = []
    for key, value in overrides.items():
        if key not in SETTINGS:
            bad.append(key)
            continue
        attr, kind, _ = SETTINGS[key]
        if kind == "date" and isinstance(value, str):
            value = dt.date.fromisoformat(value)
        if "." in attr:
            d, k = attr.split(".")
            globals()[d][k] = value
        else:
            globals()[attr] = value
    return bad


DEFAULTS = {key: current(key) for key in SETTINGS}      # captured before any override


def _load_overrides() -> None:
    if os.environ.get("ARGO_NO_SETTINGS"):
        return
    path = Path(__file__).resolve().parent.parent / "data" / "settings.json"
    if not path.exists():
        return
    try:
        overrides = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return                                     # an unreadable file is no overrides, never a crash
    apply_overrides(overrides)


_load_overrides()
