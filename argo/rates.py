"""rates.py -- THE RATE TABLE. Every number that turns an activity into money lives here.

Argo pays points for distance and ascent at the same rates Nostos Datum pays Ben (20/09/2026,
"nominally use the same basic activity scores for distance and ascent as those I use"), and
converts points to pocket money at PENCE_PER_POINT. Nothing else in the app holds a rate.

At 25p a point:  GBP 1.00 per mile run or kayaked, 50p per mile walked, 25p per mile cycled,
GBP 0.25 per 100 m swum; 1p per metre climbed running, 1/2p walking, 1/4p cycling.

Change a number here and the whole ledger re-scores on the next run -- points are derived from
the stored activities every time, never cached (Nostos Datum's second prime directive).
"""
import datetime as dt

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
STEPS_PTS_PER_10K = 1.0                 # 10,000 steps = 1 point = 25p, gross
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
    assert steps_points(12000, 0) == (12000, 1.2) and steps_points(12000, 5.0) == (12000, 1.2)   # gross
    assert steps_points(None, 0) == (0, 0.0)
    assert STEPS_START >= SCHEME_START
    assert pence(4.0) == 100 and pence(0.019) == 0 and pence(0.02) == 1 and pence(3.999) == 100
    assert gbp(1234) == "£12.34"
    assert EGGS_START >= SCHEME_START
    print("rates: selftest OK")


if __name__ == "__main__":
    selftest()
