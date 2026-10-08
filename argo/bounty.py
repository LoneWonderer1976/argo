"""bounty.py -- the week's bounty for Thomas: one target, one bar, one reward, live on Dad's yes.

    python -m argo.bounty                                   # this week's and next week's, and the menu
    python -m argo.bounty --propose                         # draw next week's from the menu (dry run)
    python -m argo.bounty --propose --apply --issue-file b.md   # Sunday's Action: body to the file, title to stdout
    python -m argo.bounty --do "reroll" --apply
    python -m argo.bounty --do "target cycle_miles 10; reward x2; approve" --week 2026-10-12 --apply
    python -m argo.bounty --reply --issue-body issue.md --comment comment.md --apply
    python -m argo.bounty --selftest

Ben, 08/10/2026: "every sunday night I want to generate a bounty mission for Tom ... i would like
control over it ... happy for this to be auto and i rubber stamp or veto", and "lean on cycling as
he likes to get out on his bike and can do that independently". The design and his rulings are
ARGO_BRIEF.md, "Bounties".

- THE MENU IS BEN'S: data/bounty_targets.csv (what a bounty asks, each line with the range its bar
  is drawn from and a weight) and data/bounty_rewards.csv (what it pays). Both open in Excel. The
  draw only ever takes a line marked on; a bar is a step inside that line's range.
- NOTHING REACHES HIS PAGE WITHOUT DAD'S YES. Sunday's Action proposes next week's bounty as an
  issue; a reply -- approve, veto, reroll, bar N, reward ..., target <key> -- is the decision.
  A proposal never approved lapses with its week.
- A LIVE BOUNTY IS A PROMISE: it may be eased (a lower bar) or sweetened (more of the same reward),
  never withdrawn, made harder or swapped.
- THE ONLY STORED STATE is data/bounties.json: what was proposed and what Dad said. Whether it was
  hit, and what it pays, is derived by progress() on every run like every other penny, strikes
  included. A missed bounty pays nothing and says nothing to him: no failed stamp, no streak.
- An approval mid-week counts the whole week from Monday: he cannot have aimed at a bounty he
  could not see, so it is generous, not gameable.
"""
import argparse
import csv
import datetime as dt
import io
import random
import re
import sys

from . import rates, store
from .weeks import this_week, today_uk, week_label, week_of

SCOPES = {"run": ("run",), "walk": ("walk",), "cycle": ("cycle",), "swim": ("swim",), "kayak": ("kayak",),
          "foot": ("walk", "run"), "any": tuple(rates.SPORTS)}
METRICS = ("miles", "climb_m", "hours", "outings", "days", "sports", "steps", "steps_days")
SINGLE_OK = ("miles", "climb_m", "hours")          # the metrics a bar on ONE outing can be counted on
STEPS_METRICS = ("steps", "steps_days")
REWARD_TYPES = ("fixed", "target_x", "week_x", "real")
YES = ("yes", "y", "on", "true", "1")
WEEK_RE = re.compile(r"<!--\s*argo-bounty:\s*(\d{4}-\d{2}-\d{2})\s*-->")

_VERB = {"cycle": "Ride", "walk": "Walk", "run": "Run", "swim": "Swim", "kayak": "Paddle", "foot": "Walk or run", "any": "Cover"}
_NOUN = {"cycle": "ride", "walk": "walk", "run": "run", "swim": "swim", "kayak": "paddle", "foot": "walk or run", "any": "outing"}
_ON = {"cycle": " on your bike", "walk": " walking", "run": " running", "swim": " swimming", "kayak": " paddling",
       "foot": " on foot", "any": ""}
_MONEY = {"cycle": "cycling", "walk": "walking", "run": "running", "swim": "swimming", "kayak": "paddling",
          "foot": "walking and running", "any": "activity"}


# --- the menu ---------------------------------------------------------------------------------

def sports_of(token: str) -> tuple:
    out = []
    for t in (token or "any").lower().split():
        out += [s for s in SCOPES[t] if s not in out]
    return tuple(out)


def _num(text: str, what: str) -> float:
    try:
        return float(str(text).replace("£", "").replace(",", "").replace("×", "").strip().lower().strip("x"))
    except ValueError:
        raise ValueError(f"{what} needs a number, not '{text}'")


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252")          # saved from Excel as plain "CSV"


def _rows(text: str, name: str, build) -> list[dict]:
    out, bad = [], []
    for i, row in enumerate(csv.DictReader(io.StringIO(text)), start=2):
        row = {(k or "").strip().lower(): (v.strip() if isinstance(v, str) else "") for k, v in row.items()}
        if not row.get("key"):
            continue                          # a blank line
        try:
            out.append(build(row))
        except (ValueError, KeyError) as e:
            bad.append(f"{name} line {i} ({row['key']}): {e}")
    keys = [r["key"] for r in out]
    bad += [f"{name}: the key '{k}' is used twice" for k in sorted({k for k in keys if keys.count(k) > 1})]
    if bad:
        raise ValueError("; ".join(bad))
    return out


def _target_row(row: dict) -> dict:
    sports = (row.get("sports") or "any").lower()
    for tok in sports.split():
        if tok not in SCOPES:
            raise ValueError(f"sports '{tok}' is not one of {', '.join(SCOPES)}")
    metric = (row.get("metric") or "").lower()
    if metric not in METRICS:
        raise ValueError(f"metric '{metric}' is not one of {', '.join(METRICS)}")
    counted = (row.get("counted") or "week").lower()
    if counted not in ("week", "one"):
        raise ValueError("counted is 'week' (the week's total) or 'one' (one outing)")
    if counted == "one" and metric not in SINGLE_OK:
        raise ValueError(f"only {', '.join(SINGLE_OK)} can be counted on one outing")
    lo = _num(row.get("min"), "min")
    hi = _num(row.get("max") or row.get("min"), "max")
    step = _num(row.get("step") or "0", "step")
    if lo <= 0 or hi < lo or step < 0:
        raise ValueError("needs 0 < min <= max and a step of 0 or more")
    return {"key": row["key"], "on": (row.get("on") or "yes").lower() in YES, "weight": _num(row.get("weight") or "1", "weight"),
            "sports": sports, "metric": metric, "counted": counted, "min": lo, "max": hi, "step": step,
            "words": row.get("words", "")}


def _reward_row(row: dict) -> dict:
    kind = (row.get("type") or "").lower()
    if kind not in REWARD_TYPES:
        raise ValueError(f"type '{kind}' is not one of {', '.join(REWARD_TYPES)}")
    out = {"key": row["key"], "on": (row.get("on") or "yes").lower() in YES, "weight": _num(row.get("weight") or "1", "weight"),
           "type": kind, "words": row.get("words", ""), "min": None, "max": None, "step": 0.0, "cap_pence": None}
    if kind == "real":
        if not out["words"]:
            raise ValueError("a real-world reward needs its words")
        return out
    lo = _num(row.get("min"), "min")
    hi = _num(row.get("max") or row.get("min"), "max")
    step = _num(row.get("step") or "0", "step")
    if kind == "fixed":                       # pounds in the sheet, pence in the app
        lo, hi, step = round(lo * 100), round(hi * 100), round(step * 100)
        if lo <= 0 or hi < lo:
            raise ValueError("needs 0 < min <= max (in pounds)")
    elif lo <= 1 or hi < lo:
        raise ValueError("a multiplier needs 1 < min <= max")
    cap = row.get("cap", "")
    out.update(min=lo, max=hi, step=step, cap_pence=round(_num(cap, "cap") * 100) if cap else None)
    return out


def parse_menu(targets_text: str, rewards_text: str) -> tuple[list[dict], list[dict]]:
    targets = _rows(targets_text, "bounty_targets.csv", _target_row)
    rewards = _rows(rewards_text, "bounty_rewards.csv", _reward_row)
    for name, rows in (("bounty_targets.csv", targets), ("bounty_rewards.csv", rewards)):
        if not any(r["on"] and r["weight"] > 0 for r in rows):
            raise ValueError(f"{name}: no line is switched on")
    return targets, rewards


def load_menu() -> tuple[list[dict], list[dict]]:
    read = lambda p: _decode(p.read_bytes()) if p.exists() else ""
    return parse_menu(read(store.BOUNTY_TARGETS), read(store.BOUNTY_REWARDS))


# --- the draw ---------------------------------------------------------------------------------

def _tidy(v: float):
    v = round(float(v), 4)
    return int(v) if v.is_integer() else v


def _ladder(lo: float, hi: float, step: float) -> list:
    if step <= 0 or hi <= lo:
        return [lo]
    out, i = [], 0
    while lo + i * step <= hi + 1e-9:
        out.append(lo + i * step)
        i += 1
    return out


def _pick(rng: random.Random, rows: list[dict], avoid=()) -> dict:
    live = [r for r in rows if r["on"] and r["weight"] > 0]
    pool = [r for r in live if r["key"] not in avoid] or live
    return rng.choices(pool, weights=[r["weight"] for r in pool])[0]


def target_from(row: dict, rng: random.Random, bar=None) -> dict:
    bar = _tidy(bar if bar is not None else rng.choice(_ladder(row["min"], row["max"], row["step"])))
    return {"key": row["key"], "sports": row["sports"], "metric": row["metric"], "counted": row["counted"],
            "bar": bar, "words": row["words"], "range": [_tidy(row["min"]), _tidy(row["max"])]}


def reward_from(row: dict, rng: random.Random) -> dict:
    value = None if row["type"] == "real" else _tidy(rng.choice(_ladder(row["min"], row["max"], row["step"])))
    return {"key": row["key"], "type": row["type"], "value": value, "cap_pence": row["cap_pence"], "words": row["words"]}


def draw(monday: str, rolls: int, menu, avoid=()) -> tuple[dict, dict]:
    """Seeded by the week and the number of rolls, so a re-run of the same draw is the same draw."""
    rng = random.Random(f"argo-bounty|{monday}|{rolls}")
    targets, rewards = menu
    return target_from(_pick(rng, targets, avoid), rng), reward_from(_pick(rng, rewards), rng)


# --- words ------------------------------------------------------------------------------------

def _scope(t: dict) -> str:
    return t["sports"] if t["sports"] in _VERB else "any"


def fmt_bar(metric: str, v) -> str:
    return f"{int(v):,}" if metric == "steps" else f"{float(v):g}"


def _default_words(t: dict) -> str:
    m, one, s = t["metric"], t["counted"] == "one", _scope(t)
    if m == "miles":
        return f"One {_NOUN[s]} of {{bar}} miles or more" if one else f"{_VERB[s]} {{bar}} miles this week"
    if m == "climb_m":
        return f"Climb {{bar}} m in one {_NOUN[s]}" if one else f"Climb {{bar}} m{_ON[s]} this week"
    if m == "hours":
        return f"One {_NOUN[s]} of {{bar}} hours or more" if one else f"{{bar}} hours{_ON[s] or ' out and moving'} this week"
    if m == "outings":
        return {"cycle": "Go out on your bike {bar} times this week", "walk": "Go for {bar} walks this week",
                "run": "Go for {bar} runs this week"}.get(s, "Get out {bar} times this week")
    if m == "days":
        return f"Get out{_ON[s]} on {{bar}} different days this week"
    if m == "sports":
        return "Do {bar} different sports this week"
    if m == "steps":
        return "Walk {bar} steps this week"
    return f"{rates.BOUNTY_STEPS_DAY:,} steps on {{bar}} days this week"


def target_words(t: dict) -> str:
    s = (t.get("words") or _default_words(t)).replace("{bar}", fmt_bar(t["metric"], t["bar"]))
    return re.sub(r"\b1 (mile|hour|time|day|walk|run|ride)s\b", r"1 \1", s)       # "Run 1 mile", not "1 miles"


def unit(t: dict) -> str:
    s = _scope(t)
    return {"miles": "miles", "climb_m": "m", "hours": "hours", "days": "days", "sports": "sports", "steps": "steps",
            "steps_days": "days", "outings": {"cycle": "rides", "walk": "walks", "run": "runs"}.get(s, "outings")}[t["metric"]]


def _times(v) -> str:
    return {2: "double", 3: "triple"}.get(v, f"{float(v):g}×")


def reward_words(t: dict, rw: dict) -> str:
    cap = f" (up to {rates.gbp(rw['cap_pence'])} extra)" if rw.get("cap_pence") else ""
    if rw["type"] == "fixed":
        return f"{rates.gbp(rw['value'])} extra"
    if rw["type"] == "target_x":
        noun = "steps" if t["metric"] in STEPS_METRICS else _MONEY[_scope(t)]
        s = f"{_times(rw['value'])} your {noun} money this week{cap}"
    elif rw["type"] == "week_x":
        s = f"{_times(rw['value'])} your whole week's pocket money{cap}"
    else:
        s = rw["words"]
    return s[:1].upper() + s[1:]


def _bonus(rw: dict, points: float) -> int:
    p = max(0, int((float(rw["value"]) - 1) * points * rates.PENCE_PER_POINT + 0.5))
    return min(p, rw["cap_pence"]) if rw.get("cap_pence") else p


def estimate_pence(t: dict, rw: dict) -> int | None:
    """What the reward comes to at exactly the bar, where that is knowable in advance."""
    if rw["type"] == "fixed":
        return rw["value"]
    if rw["type"] != "target_x":
        return None
    if t["metric"] == "miles" and t["sports"] in rates.DISTANCE_PER_MILE:
        return _bonus(rw, t["bar"] * rates.DISTANCE_PER_MILE[t["sports"]])
    if t["metric"] == "steps":
        return _bonus(rw, t["bar"] / 10000 * rates.STEPS_PTS_PER_10K)
    if t["metric"] == "steps_days":
        return _bonus(rw, t["bar"] * rates.BOUNTY_STEPS_DAY / 10000 * rates.STEPS_PTS_PER_10K)
    return None


# --- progress: derived on every run, like every other penny ---------------------------------

def is_outing(r: dict) -> bool:
    return ((r.get("distance_m") or 0) * rates.MILES_PER_METRE >= rates.BOUNTY_OUTING_MIN_MILES
            or (r.get("duration_s") or 0) >= rates.BOUNTY_OUTING_MIN_MINUTES * 60)


def _amount(metric: str, r: dict) -> float:
    if metric == "miles":
        return (r.get("distance_m") or 0) * rates.MILES_PER_METRE
    if metric == "climb_m":
        return r.get("ascent_m") or 0
    return (r.get("duration_s") or 0) / 3600


def progress(b: dict, acts: list[dict], days: list[dict], week_points: float = 0.0) -> dict:
    """One week's scored rows (score.scored_activities) and step days against one bounty.
    `worth_pence` is what the reward comes to as things stand; `bonus_pence` is that once the bar falls."""
    t, rw = b["target"], b["reward"]
    metric, bar = t["metric"], float(t["bar"])
    mine = sorted((r for r in acts if not r.get("excluded") and not r.get("history") and r["sport"] in sports_of(t["sports"])),
                  key=lambda r: r["start_local"])
    value, met_on = 0.0, None
    if metric in STEPS_METRICS:
        for d in sorted(days, key=lambda d: d["date"]):
            value += d["steps"] if metric == "steps" else int(d["steps"] >= rates.BOUNTY_STEPS_DAY)
            if met_on is None and value >= bar - 1e-9:
                met_on = d["date"]
        money = sum(d["points"] for d in days)
    else:
        seen: set = set()
        for r in mine:
            if metric in SINGLE_OK:
                a = _amount(metric, r)
                value = max(value, a) if t["counted"] == "one" else value + a
            elif is_outing(r):
                if metric == "outings":
                    value += 1
                else:
                    seen.add(r["date"] if metric == "days" else r["sport"])
                    value = len(seen)
            if met_on is None and value >= bar - 1e-9:
                met_on = r["date"]
        money = sum(r["points"] for r in mine)      # every activity of its sports, short ones too: they all earned
    worth = {"fixed": lambda: rw["value"], "target_x": lambda: _bonus(rw, money),
             "week_x": lambda: _bonus(rw, week_points)}.get(rw["type"], lambda: 0)()
    return {"value": round(value, 2), "bar": t["bar"], "met": met_on is not None, "met_on": met_on,
            "worth_pence": worth, "bonus_pence": worth if met_on else 0}


def view(monday: str, b: dict, p: dict) -> dict:
    """What leaves the server for his page and the statement -- a LIVE bounty only."""
    t, rw = b["target"], b["reward"]
    return {"monday": monday, "label": week_label(dt.date.fromisoformat(monday)), "words": target_words(t),
            "reward": reward_words(t, rw), "reward_type": rw["type"], "metric": t["metric"], "counted": t["counted"],
            "unit": unit(t), "bar": t["bar"], "value": p["value"], "met": p["met"], "met_on": p["met_on"],
            "worth_pence": p["worth_pence"], "bonus_pence": p["bonus_pence"],
            "treat": rw["words"] if rw["type"] == "real" else None}


def _history() -> tuple[list[dict], list[dict]]:
    from . import score                     # score imports this module; this way round is lazy
    ov = store.overrides()
    rows = score.paid_rows(score.scored_activities(store.activities(), ov["exclude"], ov["sport"]))
    return rows, score.steps_rows(store.steps(), rows)


def hit_rate(t: dict, monday: dt.date, rows: list[dict], days: list[dict], n: int = 12) -> tuple[int, int]:
    """How many of the n weeks before `monday` would have hit this target -- information for Dad, never a rule."""
    first = week_of(rates.SCHEME_START)
    weeks = [w.isoformat() for w in (monday - dt.timedelta(days=7 * i) for i in range(1, n + 1)) if w >= first]
    if t["metric"] in STEPS_METRICS:
        weeks = [w for w in weeks if any(d["week"] == w for d in days)]
    probe = {"target": t, "reward": {"type": "real", "value": None, "cap_pence": None, "words": ""}}
    hits = sum(progress(probe, [r for r in rows if r["week"] == w], [d for d in days if d["week"] == w])["met"] for w in weeks)
    return hits, len(weeks)


# --- Dad's word -------------------------------------------------------------------------------

HELP_ROWS = (
    ("approve", "it goes on his page"),
    ("veto", "no bounty that week"),
    ("reroll", "draw another from the menu"),
    ("bar 8", "a different bar (once he can see it, only lower)"),
    ("reward £3 · reward x2 · reward week x1.5 · reward treat <what it is>", "a different reward; add cap £4 after a multiplier (once he can see it, only more of the same)"),
    ("target <key> · target <key> 10", "another line of the menu, and its bar if you name one"),
    ("propose", "draw one for a week that has none"),
)
HELP = " · ".join(f"**{c}**" for c, _ in HELP_ROWS) + ". Several at once: one per line, or separated by ;"


def parse_reward(words: list[str], old: dict | None) -> dict:
    """'£3' / '50p' / 'x2' / 'double' / 'week x1.5' / 'x2 cap £4' / 'treat you choose the takeaway'."""
    text = " ".join(words).strip()
    low = text.lower()
    if low.split()[:1] in (["treat"], ["real"]):
        rest = text.split(None, 1)[1].strip() if len(text.split(None, 1)) > 1 else ""
        if not rest:
            raise ValueError("say what the treat is, e.g. reward treat you choose Friday's takeaway")
        return {"key": "by hand", "type": "real", "value": None, "cap_pence": None, "words": rest}
    cap, cap_given = None, False
    m = re.search(r"\bcap\s+(\S+)", low)
    if m:
        cap_given = True
        cap = None if m.group(1) in ("none", "off") else round(_num(m.group(1), "cap") * 100)
        low = low[:m.start()].strip()
    week = low.startswith("week")
    if week:
        low = low[4:].strip()
    mult = {"double": 2, "triple": 3}.get(low)
    if mult is None:
        m2 = re.fullmatch(r"[x×]\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*[x×]", low)
        mult = float(m2.group(1) or m2.group(2)) if m2 else None
    if mult is not None:
        if mult <= 1:
            raise ValueError("a multiplier has to be more than 1")
        kind = "week_x" if week else "target_x"
        if not cap_given:
            cap = old["cap_pence"] if old and old["type"] == kind else rates.BOUNTY_CAP_PENCE
        return {"key": "by hand", "type": kind, "value": _tidy(mult), "cap_pence": cap, "words": ""}
    m3 = re.fullmatch(r"£?\s*(\d+(?:\.\d{1,2})?)\s*(p?)", low)
    if m3 and not week:
        pence = int(m3.group(1)) if m3.group(2) else round(float(m3.group(1)) * 100)
        if pence > 0:
            return {"key": "by hand", "type": "fixed", "value": pence, "cap_pence": None, "words": ""}
    raise ValueError("I read rewards like £3, 50p, x2, week x1.5 or treat <what it is>")


def _smaller(old: dict, new: dict) -> str | None:
    """Why `new` is not a sweetening of a live `old`, or None if it is."""
    if old["type"] != new["type"] or old["type"] == "real":
        return "he can see it now, so the reward can only grow, not change kind"
    if float(new["value"]) < float(old["value"]):
        return "he can see it now, so the reward can only go up"
    if old["cap_pence"] is not None and (new["cap_pence"] is not None and new["cap_pence"] < old["cap_pence"]):
        return "he can see it now, so the cap can only go up"
    return None


def describe(b: dict) -> list[str]:
    t, rw = b["target"], b["reward"]
    est = estimate_pence(t, rw)
    status = {"proposed": "proposed, not on his page yet", "live": "LIVE on his page",
              "vetoed": "vetoed, so no bounty that week"}[b["status"]]
    return [f"🎯 **{target_words(t)}**",
            f"Reward: **{reward_words(t, rw)}**" + (f" (about +{rates.gbp(est)} at the bar)" if est and rw["type"] == "target_x" else ""),
            f"Status: {status}"]


def _lines(text: str) -> list[str]:
    out = []
    for line in re.split(r"[\n;]", text or ""):
        line = line.strip()
        if line.startswith(">") or re.match(r"^On .+wrote:$", line):
            break                               # the quoted email below a reply
        if line:
            out.append(line)
    return out


def apply_commands(recs: dict, monday: str, text: str, menu, today: dt.date, by: str = "Dad") -> tuple[list[str], bool, bool]:
    """Dad's lines, in order, against one week's bounty. `menu` is a callable (loaded only if a line
    needs it). Returns (what was done, whether the issue may close, whether anything changed)."""
    weeks = recs.setdefault("weeks", {})
    mon = dt.date.fromisoformat(monday)
    over = today > mon + dt.timedelta(days=6)
    prev = weeks.get((mon - dt.timedelta(days=7)).isoformat())
    last_key = prev["target"]["key"] if prev else None
    out, changed, known = [], False, 0
    for line in _lines(text):
        words = line.split()
        verb, rest = words[0].lower().strip(".,!:"), words[1:]
        b = weeks.get(monday)
        if verb not in ("approve", "approved", "ok", "yes", "veto", "reroll", "propose", "target", "bar", "reward", "show", "status", "help"):
            continue                              # a signature, a greeting: not a command
        known += 1
        if verb in ("show", "status"):
            continue
        if verb == "help":
            out.append(HELP)
            continue
        if over and verb != "veto":
            out.append(f"Not done ({line}): the week of {week_label(mon)} is over.")
            continue
        if verb == "propose" or (verb == "reroll" and not b):
            if b:
                out.append(f"{week_label(mon)} already has a bounty ({b['status']}); reply **reroll** for another.")
                continue
            t, rw = draw(monday, 0, menu(), avoid={last_key})
            weeks[monday] = {"target": t, "reward": rw, "status": "proposed", "by": "draw", "rolls": 0,
                             "proposed_on": today.isoformat(), "approved_on": None, "vetoed_on": None}
            out.append("Drawn from the menu.")
            changed = True
            continue
        if not b:
            out.append(f"Not done ({line}): nothing is proposed for {week_label(mon)} yet; reply **propose** or **target** *key*.")
            continue
        live = b["status"] == "live"
        if verb in ("approve", "approved", "ok", "yes"):
            if live:
                out.append("It is already live.")
            else:
                b.update(status="live", approved_on=today.isoformat(), vetoed_on=None)
                out.append("Approved: it is on his page now.")
                changed = True
        elif verb == "veto":
            if live:
                out.append("Not done: he can see it now, and a bounty he can see is a promise. You can still make it "
                           "easier (**bar** *lower*) or bigger (**reward** *more*).")
            elif b["status"] == "vetoed":
                out.append("It is already vetoed.")
            else:
                b.update(status="vetoed", vetoed_on=today.isoformat())
                out.append("Vetoed: no bounty that week, unless you **reroll** or **approve** after all.")
                changed = True
        elif live and verb in ("reroll", "target"):
            out.append(f"Not done ({line}): he can see this one, so it stays. You can make it easier or bigger.")
        elif verb == "reroll":
            b["rolls"] = int(b.get("rolls", 0)) + 1
            t, rw = draw(monday, b["rolls"], menu(), avoid={last_key, b["target"]["key"]})
            b.update(target=t, reward=rw, status="proposed", by="draw", vetoed_on=None)
            out.append("Rerolled.")
            changed = True
        elif verb == "target":
            row = next((r for r in menu()[0] if rest and r["key"].lower() == rest[0].lower()), None)
            if row is None:
                out.append(f"Not done ({line}): the target keys are {', '.join(r['key'] for r in menu()[0])}.")
                continue
            try:
                bar = _num(rest[1], "the bar") if len(rest) > 1 else None
            except ValueError as e:
                out.append(f"Not done: {e}.")
                continue
            if bar is not None and bar <= 0:
                out.append("Not done: the bar has to be more than 0.")
                continue
            b.update(target=target_from(row, random.Random(f"argo-bounty|{monday}|{row['key']}"), bar),
                     status="proposed", by=by, vetoed_on=None)
            out.append(f"Target set from the menu's `{row['key']}`.")
            changed = True
        elif verb == "bar":
            try:
                bar = _num(rest[0] if rest else "", "the bar")
            except ValueError as e:
                out.append(f"Not done: {e}.")
                continue
            if bar <= 0:
                out.append("Not done: the bar has to be more than 0.")
            elif live and bar > float(b["target"]["bar"]):
                out.append("Not done: he can see it now, so the bar can only come down.")
            elif bar == float(b["target"]["bar"]):
                out.append("The bar is already that.")
            else:
                b["target"]["bar"] = _tidy(bar)
                if not live:
                    b.update(status="proposed", vetoed_on=None)
                out.append(f"Bar set to {fmt_bar(b['target']['metric'], bar)}.")
                changed = True
        elif verb == "reward":
            try:
                rw = parse_reward(rest, b["reward"]) if rest else None
            except ValueError as e:
                out.append(f"Not done: {e}.")
                continue
            if rw is None:
                out.append("Not done: say what the reward is, e.g. reward £3.")
                continue
            why = _smaller(b["reward"], rw) if live else None
            if why:
                out.append(f"Not done: {why}.")
                continue
            b["reward"] = rw
            if not live:
                b.update(status="proposed", vetoed_on=None)
            out.append("Reward set.")
            changed = True
    if not known:
        out.append("I read replies like these, nothing done: " + HELP)
    b = weeks.get(monday)
    if b:
        out += [""] + describe(b)
    return out, bool(b) and b["status"] in ("live", "vetoed"), changed


def default_week(recs: dict, today: dt.date) -> str:
    """The week a form or the PC means when it names none: next week's if it has a bounty, else
    this week's if it has one, else next week."""
    cur = (today - dt.timedelta(days=today.weekday()))
    nxt = (cur + dt.timedelta(days=7)).isoformat()
    weeks = recs.get("weeks", {})
    return nxt if nxt in weeks or cur.isoformat() not in weeks else cur.isoformat()


def issue_markdown(monday: str, b: dict, hits: tuple[int, int] | None) -> tuple[str, str]:
    """(title, body) of the Sunday proposal. The hidden marker is how a reply knows its week."""
    label = week_label(dt.date.fromisoformat(monday))
    t, rw = b["target"], b["reward"]
    lo, hi = t.get("range") or [t["bar"], t["bar"]]
    lines = [f"<!-- argo-bounty: {monday} -->",
             f"**The bounty proposed for {label}.** Thomas cannot see it until you approve it.", "",
             *describe(b)[:2], ""]
    if hits and hits[1]:
        lines.append(f"His last {hits[1]} weeks would have hit it in **{hits[0]}**.")
    lines += [f"Drawn from the menu: target `{t['key']}` (bar from {fmt_bar(t['metric'], lo)} to {fmt_bar(t['metric'], hi)}), "
              f"reward `{rw['key']}`.", "",
              "**Reply with a line, or several** (one per line, or separated by ;):",
              *(f"- **{c}**: {w}" for c, w in HELP_ROWS), "",
              "Nothing reaches his page until you reply **approve**; if you never do, it lapses with the week. "
              "Once he can see it, it can only get easier or bigger. The menu is `data/bounty_targets.csv` and "
              "`data/bounty_rewards.csv` in the repository."]
    return f"Argo bounty: {label}, proposed", "\n".join(lines) + "\n"


# --- the doors ----------------------------------------------------------------------------------

def run(monday: str | None, text: str, apply: bool, today: dt.date | None = None) -> tuple[str, bool]:
    today = today or today_uk()
    recs = store.bounties()
    monday = monday or default_week(recs, today)
    out, close, changed = apply_commands(recs, monday, text, load_menu, today)
    if apply and changed:
        store.write_bounties(recs)
    if changed and not apply:
        out.append("(dry run: nothing written; add --apply)")
    return "\n".join(out), close


def propose(monday: str, apply: bool, today: dt.date | None = None) -> dict | None:
    """Sunday: draw `monday`'s bounty if it has none. Returns the new record, or None."""
    today = today or today_uk()
    recs = store.bounties()
    if monday in recs["weeks"]:
        return None
    out, _, changed = apply_commands(recs, monday, "propose", load_menu, today, by="draw")
    if not changed:
        raise SystemExit("\n".join(out))
    if apply:
        store.write_bounties(recs)
    return recs["weeks"][monday]


def show() -> None:
    recs = store.bounties()
    rows, days = _history()
    for mon in (this_week(), this_week() + dt.timedelta(days=7)):
        b = recs["weeks"].get(mon.isoformat())
        if not b:
            print(f"{week_label(mon)}: no bounty")
            continue
        wk = mon.isoformat()
        p = progress(b, [r for r in rows if r["week"] == wk], [d for d in days if d["week"] == wk])
        print(f"{week_label(mon)}: " + " | ".join(describe(b)).replace("**", "").replace("🎯 ", "")
              + f" | so far {p['value']:g} of {p['bar']} {unit(b['target'])}" + (f", HIT {p['met_on']}" if p["met"] else ""))
    try:
        targets, rewards = load_menu()
    except ValueError as e:
        print(f"\nTHE MENU HAS A PROBLEM: {e}")
        return
    on = [t for t in targets if t["on"] and t["weight"] > 0]
    total = sum(t["weight"] for t in on)
    print(f"\nTargets ({len(on)} on; cycling {sum(t['weight'] for t in on if t['sports'] == 'cycle') / total:.0%} of draws):")
    for t in targets:
        h, n = hit_rate(target_from(t, random.Random(0), t["min"]), this_week() + dt.timedelta(days=7), rows, days)
        print(f"  {'on ' if t['on'] else 'off'} w{t['weight']:<4g} {t['key']:16} {target_words({**t, 'bar': t['min']}):55} "
              f"bar {fmt_bar(t['metric'], t['min'])}-{fmt_bar(t['metric'], t['max'])}  (low end hit {h} of {n} weeks)")
    print("Rewards:")
    for rw in rewards:
        lo = rates.gbp(rw["min"]) if rw["type"] == "fixed" else (f"x{rw['min']:g}" if rw["min"] else "")
        print(f"  {'on ' if rw['on'] else 'off'} w{rw['weight']:<4g} {rw['key']:16} {rw['type']:9} {lo}"
              + (f"-{rates.gbp(rw['max'])}" if rw["type"] == "fixed" and rw["max"] != rw["min"] else "")
              + (f" cap {rates.gbp(rw['cap_pence'])}" if rw["cap_pence"] else "") + (f" {rw['words']}" if rw["words"] else ""))


# --- the selftest -------------------------------------------------------------------------------

_T = """key,on,weight,sports,metric,counted,min,max,step,words
cycle_miles,yes,3,cycle,miles,week,8,15,1,"Ride {bar} miles this week, as many rides as you like"
one_ride,yes,3,cycle,miles,one,6,12,1,
outings,yes,1,any,outings,week,2,3,1,
days,yes,1,any,days,week,2,4,1,
steps_days,yes,1,any,steps_days,week,3,5,1,
run_off,no,5,run,miles,week,1,3,0.5,
"""
_R = """key,on,weight,type,min,max,step,cap,words
fixed,yes,1,fixed,1,3,0.5,,
double,yes,1,target_x,2,2,,5,
boost,yes,1,week_x,1.5,1.5,,5,
takeaway,no,1,real,,,,,You choose Friday's takeaway
"""


def selftest() -> None:
    from . import score
    menu = parse_menu(_T, _R)
    targets, rewards = menu
    assert [t["key"] for t in targets][-1] == "run_off" and not targets[-1]["on"]
    assert rewards[0]["min"] == 100 and rewards[0]["step"] == 50 and rewards[1]["cap_pence"] == 500
    assert _ladder(1, 3, 0.5) == [1, 1.5, 2, 2.5, 3] and _ladder(2, 2, 0) == [2]
    for bad, why in ((_T.replace("week,2,4", "fortnight,2,4"), "counted"), (_T.replace(",outings,", ",outting,"), "metric"),
                     (_T.replace("any,days", "bike,days"), "sports"), (_T.replace(",steps_days,week", ",steps_days,one"), "one outing"),
                     (_T + "outings,yes,1,any,outings,week,2,3,1,\n", "twice")):
        try:
            parse_menu(bad, _R)
            raise AssertionError(f"accepted a bad menu ({why})")
        except ValueError as e:
            assert why in str(e), (why, e)
    assert parse_menu(_decode(_T.encode("utf-8-sig")), _R)[0][0]["key"] == "cycle_miles"     # Excel's UTF-8 adds a BOM
    assert _decode("£3".encode("cp1252")) == "£3"                                              # its plain CSV is cp1252
    # the draw: seeded, inside its range, never last week's target, and the reroll moves
    t1, r1 = draw("2026-10-12", 0, menu)
    assert (t1, r1) == draw("2026-10-12", 0, menu)
    row = next(t for t in targets if t["key"] == t1["key"])
    assert row["min"] <= t1["bar"] <= row["max"]
    assert all(draw("2026-10-12", n, menu, avoid={"cycle_miles"})[0]["key"] != "cycle_miles" for n in range(30))
    assert all(draw("2026-10-12", n, menu)[0]["key"] != "run_off" for n in range(60)), "an off line was drawn"
    picks = [draw("2026-10-12", n, menu)[0]["key"] for n in range(400)]
    share = sum(k in ("cycle_miles", "one_ride") for k in picks) / len(picks)
    assert 0.55 < share < 0.80, share                      # 6 of 9 weight is cycling
    # words
    cm = target_from(targets[0], random.Random(0), 10)
    assert target_words(cm) == "Ride 10 miles this week, as many rides as you like" and unit(cm) == "miles"
    assert target_words(target_from(targets[1], random.Random(0), 6)) == "One ride of 6 miles or more"
    assert target_words(target_from(targets[4], random.Random(0), 3)) == "10,000 steps on 3 days this week"
    assert target_words({**cm, "bar": 1, "words": ""}) == "Ride 1 mile this week" and target_words({**cm, "bar": 11, "words": ""}) == "Ride 11 miles this week"
    dbl = reward_from(rewards[1], random.Random(0))
    assert reward_words(cm, dbl) == "Double your cycling money this week (up to £5.00 extra)"
    assert reward_words(cm, reward_from(rewards[2], random.Random(0))) == "1.5× your whole week's pocket money (up to £5.00 extra)"
    assert estimate_pence(cm, dbl) == 250                   # 10 miles at 1 pt = 10 pts, doubled: +£2.50
    # progress, on scored rows: two rides (6 + 5 mi), a 100 m stroll, a struck ride, a 2-mile walk
    M = 1609.344
    acts = [
        {"id": 1, "name": "r1", "sport": "cycle", "start_local": "2026-10-13 16:00:00", "distance_m": 6 * M, "ascent_m": 40, "duration_s": 2400, "avg_hr": 120},
        {"id": 2, "name": "stroll", "sport": "walk", "start_local": "2026-10-14 08:00:00", "distance_m": 100, "ascent_m": 0, "duration_s": 120, "avg_hr": 90},
        {"id": 3, "name": "r2", "sport": "cycle", "start_local": "2026-10-15 16:00:00", "distance_m": 5 * M, "ascent_m": 30, "duration_s": 2000, "avg_hr": 120},
        {"id": 4, "name": "car", "sport": "cycle", "start_local": "2026-10-16 16:00:00", "distance_m": 30 * M, "ascent_m": 0, "duration_s": 1800, "avg_hr": 90},
        {"id": 5, "name": "w", "sport": "walk", "start_local": "2026-10-17 10:00:00", "distance_m": 2 * M, "ascent_m": 20, "duration_s": 2400, "avg_hr": 100},
    ]
    rows = score.scored_activities(acts, {"4": "the car"})
    days = [{"date": "2026-10-12", "week": "2026-10-12", "steps": 12000, "points": 2.4},
            {"date": "2026-10-13", "week": "2026-10-12", "steps": 8000, "points": 1.6},
            {"date": "2026-10-14", "week": "2026-10-12", "steps": 10000, "points": 2.0}]
    live = lambda t, rw: {"target": t, "reward": rw, "status": "live"}
    fixed2 = {"key": "f", "type": "fixed", "value": 200, "cap_pence": None, "words": ""}
    p = progress(live(cm, fixed2), rows, days)
    assert p["value"] == 11.0 and p["met_on"] == "2026-10-15" and p["bonus_pence"] == 200, p     # the struck ride never counts
    assert progress(live({**cm, "bar": 12}, fixed2), rows, days)["bonus_pence"] == 0              # missed: nothing, quietly
    assert progress(live({**cm, "bar": 12}, fixed2), rows, days)["worth_pence"] == 200
    one = target_from(targets[1], random.Random(0), 6)
    assert progress(live(one, fixed2), rows, days)["met_on"] == "2026-10-13"
    assert not progress(live({**one, "bar": 7}, fixed2), rows, days)["met"]
    outs = target_from(targets[2], random.Random(0), 3)
    p = progress(live(outs, fixed2), rows, days)
    assert p["value"] == 3 and p["met_on"] == "2026-10-17", p           # the 100 m stroll is not an outing
    assert progress(live(target_from(targets[3], random.Random(0), 3), fixed2), rows, days)["met_on"] == "2026-10-17"
    sd = progress(live(target_from(targets[4], random.Random(0), 2), fixed2), rows, days)
    assert sd["value"] == 2 and sd["met_on"] == "2026-10-14", sd       # 12,000 and exactly 10,000 count; 8,000 does not
    p = progress(live(cm, dbl), rows, days)                          # double the week's cycling money: 11 mi + 70 m
    assert p["bonus_pence"] == int(11.7 * 25 + 0.5), p
    assert progress(live(cm, {**dbl, "cap_pence": 200}), rows, days)["bonus_pence"] == 200
    assert progress(live(cm, {**dbl, "type": "week_x", "value": 1.5}), rows, days, week_points=20)["bonus_pence"] == 250
    treat = {"key": "t", "type": "real", "value": None, "cap_pence": None, "words": "Takeaway"}
    assert progress(live(cm, treat), rows, days)["bonus_pence"] == 0
    assert view("2026-10-12", live(cm, treat), progress(live(cm, treat), rows, days))["treat"] == "Takeaway"
    assert hit_rate(cm, dt.date(2026, 10, 19), rows, days) == (1, 12)
    # Dad's word
    sun = dt.date(2026, 10, 11)
    recs: dict = {"weeks": {}}
    m = lambda: menu
    out, close, ch = apply_commands(recs, "2026-10-12", "approve", m, sun)
    assert not ch and "nothing is proposed" in out[0]
    out, close, ch = apply_commands(recs, "2026-10-12", "propose", m, sun)
    assert ch and not close and recs["weeks"]["2026-10-12"]["status"] == "proposed"
    first = recs["weeks"]["2026-10-12"]["target"]["key"]
    apply_commands(recs, "2026-10-12", "reroll", m, sun)
    assert recs["weeks"]["2026-10-12"]["target"]["key"] != first and recs["weeks"]["2026-10-12"]["rolls"] == 1
    out, close, ch = apply_commands(recs, "2026-10-12", "target cycle_miles 10\nreward £2\napprove\n\nSent from my iPhone\n> paid", m, sun)
    b = recs["weeks"]["2026-10-12"]
    assert close and b["status"] == "live" and b["target"]["bar"] == 10 and b["reward"]["value"] == 200 and b["by"] == "Dad", out
    for line, why in (("veto", "promise"), ("bar 12", "only come down"), ("reward £1", "only go up"), ("reward x2", "change kind"),
                      ("reroll", "stays"), ("target one_ride", "stays")):
        out, _, ch = apply_commands(recs, "2026-10-12", line, m, sun)
        assert not ch and why in "\n".join(out), (line, out)
    out, _, ch = apply_commands(recs, "2026-10-12", "bar 8; reward £3", m, dt.date(2026, 10, 14))
    assert ch and b["target"]["bar"] == 8 and b["reward"]["value"] == 300 and b["status"] == "live"
    out, _, ch = apply_commands(recs, "2026-10-12", "bar 6", m, dt.date(2026, 10, 19))
    assert not ch and "is over" in out[0]
    out, _, ch = apply_commands(recs, "2026-10-19", "propose", m, dt.date(2026, 10, 18))
    assert recs["weeks"]["2026-10-19"]["target"]["key"] != "cycle_miles", "never last week's target twice running"
    out, close, ch = apply_commands(recs, "2026-10-19", "veto", m, dt.date(2026, 10, 18))
    assert close and recs["weeks"]["2026-10-19"]["status"] == "vetoed"
    out, close, ch = apply_commands(recs, "2026-10-19", "target run_off", m, dt.date(2026, 10, 18))
    assert recs["weeks"]["2026-10-19"]["status"] == "proposed" and recs["weeks"]["2026-10-19"]["target"]["sports"] == "run"
    out, _, ch = apply_commands(recs, "2026-10-19", "thanks!", m, dt.date(2026, 10, 18))
    assert not ch and "nothing done" in out[0]
    assert parse_reward(["x2"], None) == {"key": "by hand", "type": "target_x", "value": 2, "cap_pence": rates.BOUNTY_CAP_PENCE, "words": ""}
    assert parse_reward(["week", "x1.5", "cap", "£4"], None)["cap_pence"] == 400
    assert parse_reward(["50p"], None)["value"] == 50 and parse_reward(["£2.50"], None)["value"] == 250
    assert parse_reward(["double", "cap", "none"], None)["cap_pence"] is None
    assert parse_reward(["treat", "Cinema", "trip"], None)["words"] == "Cinema trip"
    for bad in (["x1"], ["week", "£3"], ["lots"], ["treat"]):
        try:
            parse_reward(bad, None)
            raise AssertionError(f"accepted reward {bad}")
        except ValueError:
            pass
    assert default_week({"weeks": {"2026-10-12": {}}}, dt.date(2026, 10, 13)) == "2026-10-12"
    assert default_week({"weeks": {"2026-10-12": {}, "2026-10-19": {}}}, dt.date(2026, 10, 18)) == "2026-10-19"
    assert default_week({"weeks": {}}, dt.date(2026, 10, 13)) == "2026-10-19"
    title, body = issue_markdown("2026-10-12", b, (2, 12))
    assert title == "Argo bounty: 12–18 Oct 2026, proposed" and WEEK_RE.search(body).group(1) == "2026-10-12"
    assert "hit it in **2**" in body and "approve" in body
    print("bounty: selftest OK")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--week", help="the bounty's Monday (default: the one waiting, else next week)")
    ap.add_argument("--propose", action="store_true", help="draw next week's bounty if it has none")
    ap.add_argument("--issue-file", metavar="PATH", help="with --propose: the issue body here, the title to stdout")
    ap.add_argument("--do", metavar="COMMANDS", help="Dad's lines: approve, veto, reroll, bar 8, reward x2, target <key> ...")
    ap.add_argument("--reply", action="store_true", help="read --issue-body and --comment, as the reply workflow does")
    ap.add_argument("--issue-body")
    ap.add_argument("--comment")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")          # the 🎯 and the £, on a Windows console too
    if a.selftest:
        selftest()
        return
    if a.propose:
        monday = a.week or (this_week() + dt.timedelta(days=7)).isoformat()
        b = propose(monday, a.apply)
        say = sys.stderr if a.issue_file else sys.stdout
        if b is None:
            print(f"{week_label(dt.date.fromisoformat(monday))} already has a bounty; nothing drawn", file=say)
            return
        rows, days = _history()
        title, body = issue_markdown(monday, b, hit_rate(b["target"], dt.date.fromisoformat(monday), rows, days))
        if a.issue_file:
            open(a.issue_file, "w", encoding="utf-8").write(body)
            print(title)
        else:
            print(title + "\n\n" + body + ("" if a.apply else "(dry run: nothing written; add --apply)"))
        return
    if a.reply:
        issue = open(a.issue_body, encoding="utf-8").read()
        m = WEEK_RE.search(issue)
        if not m:
            print("This issue has no bounty marker, so I can't tell which week you mean.")
            return
        text, close = run(m.group(1), open(a.comment, encoding="utf-8").read(), a.apply)
        print(text + ("\nCLOSE" if close else ""))
        return
    if a.do:
        print(run(a.week, a.do, a.apply)[0])
        return
    show()


if __name__ == "__main__":
    main()
