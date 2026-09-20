"""milestones.py -- the Easter eggs. Hidden until Thomas earns one, then his for good.

Ben, 20/09/2026: "hide some Easter eggs, motivational messages that appear when he achieves a
milestone ... milestones might be 10 mile cycle, 2 mile run, 5 mile walk, would like loads and
each to have a unique message."

Each milestone is a rule over his activities and a message written for that moment. They are
evaluated in activity order, so each one is won by the first activity that crosses it and is
dated to that day. Only the WON ones go into data.json -- the page shows the rest as a count of
eggs still hidden, so reading the page never spoils them. Struck activities and unscored sports
count for nothing here either.

Kinds: single (one activity's distance), climb (one activity's ascent), total / total_climb
(all-time), money (pence earned all-time), count (activities), week_count (in one week),
week_streak (consecutive weeks with an activity), pace (a run of a mile or more at this many
minutes a mile or better), hour_before / hour_after (start time), weekend (Saturday AND Sunday
in the same week), sports_in_week, all_sports, single_time / total_time (seconds).
"""
import datetime as dt
from dataclasses import dataclass

from .rates import SPORTS, pence

MI = 1609.344
KM = 1000.0
H = 3600.0


@dataclass(frozen=True)
class Milestone:
    key: str
    kind: str
    sport: str | None
    value: float
    title: str
    message: str


def M(key, kind, sport, value, title, message):
    return Milestone(key, kind, sport, value, title, message)


MILESTONES = [
    # --- the first of everything -------------------------------------------------------------
    M("first", "count", "any", 1, "All aboard",
      "Thomas, the Argo has left the harbour. Every voyage starts with one push off the shore -- and this was yours."),
    M("first_run", "count", "run", 1, "First run",
      "Your first run on the log. Nobody remembers their fastest run as well as they remember their first, Thomas."),
    M("first_walk", "count", "walk", 1, "First walk",
      "First walk banked. Walking is how explorers found every mountain, river and coast on the map -- they all started with one."),
    M("first_cycle", "count", "cycle", 1, "First ride",
      "First ride in the book. A bike is the fastest thing you own that runs on breakfast."),
    M("first_swim", "count", "swim", 1, "First swim",
      "First swim logged. Fish have had a 400-million-year head start and you're already catching up, Thomas."),
    M("first_kayak", "count", "kayak", 1, "First paddle",
      "First paddle! Jason had fifty rowers on the Argo. You've got two arms and it still counts."),
    M("all_sports", "all_sports", None, 5, "Pentathlete",
      "Run, walk, ride, swim AND paddle -- you've now done all five. There isn't a way of moving you haven't tried."),

    # --- one run ----------------------------------------------------------------------------
    M("run_1mi", "single", "run", 1 * MI, "The first mile",
      "A whole mile in one run. Most people never run one on purpose. You just did."),
    M("run_2mi", "single", "run", 2 * MI, "Two-mile run",
      "Two miles in one go, Thomas! That's the length of Southampton's whole waterfront -- and you ran it."),
    M("run_3mi", "single", "run", 3 * MI, "Three-mile run",
      "Three miles running. From Fair Oak to Eastleigh station and you'd still be going."),
    M("run_5k", "single", "run", 5 * KM, "The 5k",
      "5 kilometres -- a proper parkrun distance. Thousands of grown-ups get up early on Saturdays to do exactly this."),
    M("run_5mi", "single", "run", 5 * MI, "Five-mile run",
      "Five miles in one run. That's Fair Oak to Winchester's edge on foot, at a run. Your legs are becoming an engine."),
    M("run_10k", "single", "run", 10 * KM, "The 10k",
      "Ten kilometres! This is a race distance with medals. You've done it for pocket money and pride."),
    M("run_8mi", "single", "run", 8 * MI, "Eight-mile run",
      "Eight miles running. Longer than the Solent is wide. Longer than most adults will run this year."),
    M("run_10mi", "single", "run", 10 * MI, "Ten-mile run",
      "TEN miles in one run, Thomas. There's a word for people who do this: runner. It's yours now."),
    M("run_half", "single", "run", 21.0975 * KM, "Half marathon",
      "13.1 miles -- a half marathon. Pheidippides ran to Athens with news of a battle. You ran this for the joy of it."),

    # --- one walk ---------------------------------------------------------------------------
    M("walk_2mi", "single", "walk", 2 * MI, "Two-mile walk",
      "A two-mile walk in the log. Easy? Maybe. But the Argo didn't reach Colchis by staying in port."),
    M("walk_3mi", "single", "walk", 3 * MI, "Three-mile walk",
      "Three miles walked. That's the distance a Roman legionary covered every hour, in armour, with a pack."),
    M("walk_5mi", "single", "walk", 5 * MI, "Five-mile walk",
      "Five miles on foot, Thomas! Ten thousand steps and then some. Hadrian's Wall soldiers would've nodded at that."),
    M("walk_8mi", "single", "walk", 8 * MI, "Eight-mile walk",
      "Eight miles walked in one go. That's a real hike -- boots-and-sandwiches territory."),
    M("walk_10mi", "single", "walk", 10 * MI, "Ten-mile walk",
      "Ten miles walked. Explorers call this 'a day's march'. You call it Tuesday."),
    M("walk_13mi", "single", "walk", 13.1 * MI, "The long walk",
      "Half a marathon, on foot, in one walk. The South Downs Way is 100 miles -- you've just done an eighth of it in a day."),
    M("walk_20mi", "single", "walk", 20 * MI, "Twenty miles",
      "TWENTY miles walked in one day, Thomas. That's the distance across the Isle of Wight and back. Legend status."),

    # --- one ride ---------------------------------------------------------------------------
    M("cycle_5mi", "single", "cycle", 5 * MI, "Five-mile ride",
      "Five miles on the bike. Wheels are the best invention humans ever made, and you're using them properly."),
    M("cycle_10mi", "single", "cycle", 10 * MI, "Ten-mile ride",
      "TEN miles in one ride, Thomas! Fair Oak to Winchester and you'd have change. This is a proper bike ride now."),
    M("cycle_15mi", "single", "cycle", 15 * MI, "Fifteen-mile ride",
      "Fifteen miles ridden. You've now cycled further in one go than most people drive to work."),
    M("cycle_20mi", "single", "cycle", 20 * MI, "Twenty-mile ride",
      "Twenty miles on the bike. Southampton to Portsmouth, near enough. Your legs are getting ideas."),
    M("cycle_25mi", "single", "cycle", 25 * MI, "The 25",
      "Twenty-five miles in one ride! Round-the-Solent distance. Riders train for months to do this comfortably."),
    M("cycle_30mi", "single", "cycle", 30 * MI, "Thirty-mile ride",
      "Thirty miles, Thomas. Fair Oak to Salisbury. If Stonehenge were the target you'd nearly be there."),
    M("cycle_40mi", "single", "cycle", 40 * MI, "Forty-mile ride",
      "Forty miles ridden in one day. That's a stage a touring cyclist would be pleased with. Sandwich earned."),
    M("cycle_50mi", "single", "cycle", 50 * MI, "The half-century",
      "FIFTY miles in one ride. Cyclists call it a half-century and talk about it for weeks. You're allowed to as well."),
    M("cycle_65mi", "single", "cycle", 65 * MI, "Round the Island",
      "65 miles -- the distance round the whole Isle of Wight. In one ride. Thomas, that is enormous."),

    # --- one swim ---------------------------------------------------------------------------
    M("swim_200", "single", "swim", 200, "Eight lengths",
      "200 metres swum -- eight lengths of a normal pool. Odysseus took ten years at sea; you're moving faster."),
    M("swim_500", "single", "swim", 500, "Half a kilometre",
      "500 metres in one swim. Twenty lengths. The water is starting to be your friend."),
    M("swim_1k", "single", "swim", 1 * KM, "The kilometre swim",
      "A whole kilometre swum, Thomas! Forty lengths. That's the distance across Southampton Water."),
    M("swim_1mi", "single", "swim", 1 * MI, "The mile swim",
      "A MILE in the water. Sixty-four lengths. The Solent at its narrowest is about this -- you could swim to the Island."),
    M("swim_2k", "single", "swim", 2 * KM, "Two kilometres",
      "Two kilometres swum in one session. Olympic distance-swimmers warm up with this. Then again, so do you now."),

    # --- one paddle -------------------------------------------------------------------------
    M("kayak_2mi", "single", "kayak", 2 * MI, "Two miles afloat",
      "Two miles paddled. The Argonauts rowed through the Clashing Rocks. You rowed through a Saturday. Same spirit."),
    M("kayak_5mi", "single", "kayak", 5 * MI, "Five miles afloat",
      "Five miles by paddle, Thomas. That's the length of the Itchen from Eastleigh to the sea. Serious boat work."),
    M("kayak_10mi", "single", "kayak", 10 * MI, "Ten miles afloat",
      "Ten miles paddled in one go. Jason would have signed you up for the Argo on the spot."),

    # --- climbing, in one go ----------------------------------------------------------------
    M("climb_100", "climb", "any", 100, "The first hundred",
      "100 metres of climbing in one outing. That's the height of Big Ben's tower, on your own legs."),
    M("climb_250", "climb", "any", 250, "Up and up",
      "250 metres climbed in one go. Higher than Butser Hill from the bottom. Gravity noticed, and you won."),
    M("climb_330", "climb", "any", 330, "The Eiffel Tower",
      "330 metres of climbing -- the height of the Eiffel Tower, Thomas, and there was no lift."),
    M("climb_500", "climb", "any", 500, "Half a kilometre up",
      "500 metres of ascent in one outing. Every hill you went up, you came down from -- and still kept going."),
    M("climb_828", "climb", "any", 828, "The Burj Khalifa",
      "828 metres climbed in one day -- the height of the tallest building on Earth. On a bike or on foot, that's colossal."),
    M("climb_1000", "climb", "any", 1000, "The vertical kilometre",
      "A THOUSAND metres of climbing in one outing. Mountaineers call this a vertical kilometre. It's a badge, and it's yours."),

    # --- all-time distance ------------------------------------------------------------------
    M("total_run_10mi", "total", "run", 10 * MI, "Ten miles run, all told",
      "Your running now adds up to ten miles. Small runs, big total -- that's how every journey works."),
    M("total_run_marathon", "total", "run", 42.195 * KM, "A marathon, in pieces",
      "26.2 miles of running altogether -- a whole marathon, one run at a time. Some people never manage it in a lifetime."),
    M("total_run_50mi", "total", "run", 50 * MI, "Fifty miles run",
      "Fifty miles of running in the book, Thomas. Fair Oak to Brighton. On foot. Over time, but every step yours."),
    M("total_run_100mi", "total", "run", 100 * MI, "A hundred miles run",
      "ONE HUNDRED miles run. Fair Oak to London and back again. You are officially a distance runner."),
    M("total_walk_25mi", "total", "walk", 25 * MI, "Twenty-five miles walked",
      "Twenty-five miles of walking add up. You've now walked the length of the River Itchen, source to sea."),
    M("total_walk_84mi", "total", "walk", 84 * MI, "Hadrian's Wall",
      "84 miles of walking -- the full length of Hadrian's Wall, coast to coast. The Romans built it; you've walked it."),
    M("total_walk_100mi", "total", "walk", 100 * MI, "The South Downs Way",
      "100 miles walked all told, Thomas -- the whole South Downs Way, Winchester to Eastbourne. Every hill on it counted."),
    M("total_cycle_50mi", "total", "cycle", 50 * MI, "Fifty miles ridden",
      "Fifty miles of cycling in the log. Your wheels have now turned about 40,000 times for this."),
    M("total_cycle_100mi", "total", "cycle", 100 * MI, "The century",
      "A hundred miles ridden altogether. Southampton to Bristol. The bike is earning its keep and so are you."),
    M("total_cycle_250mi", "total", "cycle", 250 * MI, "Two hundred and fifty miles ridden",
      "250 miles on the bike, Thomas. That's Fair Oak to Edinburgh, near enough, if you'd pointed north and kept going."),
    M("total_cycle_500mi", "total", "cycle", 500 * MI, "Five hundred miles",
      "FIVE HUNDRED miles ridden. There's a song about walking this far. You rode it, which is faster and has fewer verses."),
    M("total_cycle_874mi", "total", "cycle", 874 * MI, "Land's End to John o' Groats",
      "874 miles -- the length of Britain, Land's End to John o' Groats, on the bike. Thomas, this is the big one."),
    M("total_swim_5k", "total", "swim", 5 * KM, "Five kilometres swum",
      "Five kilometres of swimming altogether. Two hundred lengths. The pool should be charging you rent."),
    M("total_swim_channel", "total", "swim", 21 * MI, "The Channel",
      "21 miles swum in total -- the width of the English Channel, Dover to Calais. Done in a pool, but done."),
    M("total_any_100mi", "total", "any", 100 * MI, "A hundred miles, any way",
      "One hundred miles under your own power, all sports together. That's the first big number, Thomas."),
    M("total_any_250mi", "total", "any", 250 * MI, "Two hundred and fifty miles",
      "250 miles moved by muscle. From here to Cornwall's far end. You're going places even when you're going in circles."),
    M("total_any_500mi", "total", "any", 500 * MI, "Five hundred miles, any way",
      "500 miles altogether. Fair Oak to Aberdeen. You'd be there by now if it had all been in a straight line."),
    M("total_any_1000mi", "total", "any", 1000 * MI, "A THOUSAND miles",
      "ONE THOUSAND MILES, Thomas. The Argo sailed about this far to reach the Golden Fleece. Welcome to Colchis."),

    # --- all-time climbing ------------------------------------------------------------------
    M("total_climb_1000", "total_climb", None, 1000, "A kilometre of climbing",
      "1,000 metres of ascent altogether. Your hills are adding up to a mountain."),
    M("total_climb_snowdon", "total_climb", None, 1085, "Snowdon",
      "1,085 metres climbed all told -- the height of Snowdon, the tallest mountain in Wales. From sea level, on your own legs."),
    M("total_climb_nevis", "total_climb", None, 1345, "Ben Nevis",
      "1,345 metres of climbing: Ben Nevis, the highest point in Britain. All your uphills, stacked, reach the top."),
    M("total_climb_blanc", "total_climb", None, 4808, "Mont Blanc",
      "4,808 metres of ascent -- the summit of Mont Blanc, the roof of Western Europe. Bit by bit, you climbed it."),
    M("total_climb_everest", "total_climb", None, 8849, "Everest",
      "8,849 METRES. That is Mount Everest, Thomas, from sea level to the summit, climbed on Hampshire hills. Unbelievable."),

    # --- money ------------------------------------------------------------------------------
    M("money_100", "money", None, 100, "The first pound",
      "Your first pound earned by moving. Not given -- EARNED. Different thing entirely, Thomas."),
    M("money_500", "money", None, 500, "A fiver",
      "Five pounds earned. Every penny of it was a step, a pedal or a stroke. The best-earned fiver in the house."),
    M("money_1000", "money", None, 1000, "Ten pounds",
      "Ten pounds! That's a real note. Fold it up and remember what it cost: nothing but effort."),
    M("money_2000", "money", None, 2000, "Twenty pounds",
      "Twenty pounds earned by your own legs. The Argonauts split the treasure fifty ways. This is all yours."),
    M("money_5000", "money", None, 5000, "Fifty pounds",
      "FIFTY pounds. Thomas, most people your age have never earned fifty pounds at anything. You did it by being outside."),
    M("money_10000", "money", None, 10000, "The Golden Fleece",
      "ONE HUNDRED POUNDS. This is the Golden Fleece -- the thing the whole voyage was for. Jason needed a dragon asleep. You just needed to keep going."),
    M("money_25000", "money", None, 25000, "Two hundred and fifty pounds",
      "£250 earned. That's more than the Argo's crew got paid, and they had to fight a bronze giant."),
    M("money_50000", "money", None, 50000, "Five hundred pounds",
      "FIVE HUNDRED POUNDS, all of it from moving. Thomas, you've built something here that nobody can take away: the habit."),

    # --- how many ---------------------------------------------------------------------------
    M("count_10", "count", "any", 10, "Ten outings",
      "Ten activities in the log. It's officially a habit now -- that's the hard part, and it's done."),
    M("count_25", "count", "any", 25, "Twenty-five outings",
      "Twenty-five outings. A quarter of the way to a hundred, and every one of them made you a bit stronger than the last."),
    M("count_50", "count", "any", 50, "Fifty outings",
      "Fifty activities, Thomas. The Argo had fifty oars. You've pulled every one of them."),
    M("count_100", "count", "any", 100, "The hundredth",
      "ONE HUNDRED activities. A hundred times you chose to go out when you could have stayed in. That's character, not luck."),
    M("count_250", "count", "any", 250, "Two hundred and fifty outings",
      "250 outings. If you'd read a page of a book each time you'd have finished The Odyssey. You did something better."),
    M("count_run_10", "count", "run", 10, "Ten runs",
      "Ten runs. Somewhere in there your legs stopped complaining and started asking when the next one is."),
    M("count_run_50", "count", "run", 50, "Fifty runs",
      "Fifty runs logged, Thomas. Fifty times out of the door. Runners are made exactly like this."),
    M("count_cycle_25", "count", "cycle", 25, "Twenty-five rides",
      "Twenty-five bike rides. Your bike has now seen more of Hampshire than most cars."),
    M("count_walk_25", "count", "walk", 25, "Twenty-five walks",
      "Twenty-five walks. Darwin worked out evolution on his daily walk. No pressure, but keep going."),
    M("count_swim_10", "count", "swim", 10, "Ten swims",
      "Ten swims. The water's given up trying to push you out and started letting you through."),

    # --- weeks ------------------------------------------------------------------------------
    M("week_3", "week_count", None, 3, "Three in a week",
      "Three activities in one week. That's a training week -- what athletes call it when they're being serious."),
    M("week_5", "week_count", None, 5, "Five in a week",
      "FIVE activities in a single week, Thomas. Five days out of seven. That's not a hobby any more, that's a lifestyle."),
    M("week_7", "week_count", None, 7, "Seven in a week",
      "Seven activities in one week -- one for every day. Even the Argonauts took Sundays off. Astonishing."),
    M("streak_3", "week_streak", None, 3, "Three weeks running",
      "Three weeks in a row with something in the log. Consistency is the secret nobody wants to hear. You've got it."),
    M("streak_5", "week_streak", None, 5, "Five-week streak",
      "Five weeks straight. Over a month of never letting a week go by empty. This is how it becomes who you are."),
    M("streak_10", "week_streak", None, 10, "Ten-week streak",
      "TEN weeks in a row, Thomas. Ten! Weather, homework, everything -- and you still went out every single week."),
    M("streak_20", "week_streak", None, 20, "Twenty-week streak",
      "Twenty consecutive weeks. Nearly half a year without a gap. There are Olympic athletes with worse records."),
    M("streak_52", "week_streak", None, 52, "A whole year",
      "FIFTY-TWO WEEKS IN A ROW. A full year, Thomas, without a single empty week. Frame this one."),
    M("weekend", "weekend", None, 1, "Weekend warrior",
      "Something on Saturday AND Sunday in the same week. The weekend is for adventures, and you treated it that way."),
    M("triathlete_week", "sports_in_week", None, 3, "Three sports, one week",
      "Three different sports in a single week. That's what a triathlete's diary looks like."),

    # --- speed ------------------------------------------------------------------------------
    M("pace_12", "pace", "run", 12, "Twelve-minute miles",
      "A mile or more at under 12 minutes a mile. That's quicker than a brisk walk -- properly running, start to finish."),
    M("pace_10", "pace", "run", 10, "Ten-minute miles",
      "Under 10 minutes a mile for a mile or more. Thomas, that's the pace most adult runners would be pleased with."),
    M("pace_9", "pace", "run", 9, "Nine-minute miles",
      "Nine-minute miles, sustained. You're now quicker than the average finisher at most 10k races."),
    M("pace_8", "pace", "run", 8, "Eight-minute miles",
      "Under EIGHT minutes a mile for a mile or more. This is fast. Club runners' fast. Keep that one in the bank."),
    M("pace_7", "pace", "run", 7, "Seven-minute miles",
      "Seven-minute miles! Thomas, at this pace you would beat nearly everyone in a parkrun. Nearly everyone."),

    # --- time of day and time on feet -------------------------------------------------------
    M("early_bird", "hour_before", None, 7, "Early bird",
      "Out before seven in the morning. The best part of the day belongs to the people who get up for it."),
    M("dawn_patrol", "hour_before", None, 6, "Dawn patrol",
      "Started before SIX a.m. Thomas, at that hour the only company is birds and the occasional fox. Respect."),
    M("night_owl", "hour_after", None, 20, "Night owl",
      "Out after eight in the evening. Head torch or streetlights, that's dedication."),
    M("hour_long", "single_time", "any", 1 * H, "The hour",
      "A whole hour moving in one go. Sixty minutes of not stopping. The clock was on your side today."),
    M("two_hours", "single_time", "any", 2 * H, "Two hours out",
      "Two hours in one outing, Thomas. That's a film's worth of effort with a much better ending."),
    M("four_hours", "single_time", "any", 4 * H, "The long day",
      "FOUR hours in a single outing. Expedition length. Take the rest of the day off -- you've earned every minute."),
    M("total_time_10h", "total_time", None, 10 * H, "Ten hours moving",
      "Ten hours of activity altogether. Ten hours that could have been a screen and were a world instead."),
    M("total_time_24h", "total_time", None, 24 * H, "A whole day",
      "Twenty-four hours moving, all added up -- a full day and night of it. Thomas, that's a serious number."),
    M("total_time_100h", "total_time", None, 100 * H, "A hundred hours",
      "ONE HUNDRED HOURS. Athletes talk about 10,000 hours to master something. You're 1 % of the way to being the best in the world, which is further than almost anyone gets."),
]


def _blank_week():
    return {"count": 0, "sports": set(), "days": set()}


def achieved(rows: list[dict]) -> list[dict]:
    """Milestones won, each at the first activity that crossed it. `rows` are score.py's rows in
    any order; struck activities and unscored sports are ignored."""
    rows = sorted((r for r in rows if not r.get("excluded") and r.get("sport") in SPORTS),
                  key=lambda r: r["start_local"])
    won: dict[str, dict] = {}
    dist = {s: 0.0 for s in SPORTS} | {"any": 0.0}
    count = {s: 0 for s in SPORTS} | {"any": 0}
    climb = 0.0
    points = 0.0
    time_s = 0.0
    weeks: dict[str, dict] = {}
    sports_seen: set[str] = set()
    for r in rows:
        s = r["sport"]
        d = r.get("distance_m") or 0.0
        c = r.get("ascent_m") or 0.0
        t = r.get("duration_s") or 0.0
        dist[s] += d
        dist["any"] += d
        count[s] += 1
        count["any"] += 1
        climb += c
        points += r.get("points") or 0.0
        time_s += t
        sports_seen.add(s)
        day = dt.date.fromisoformat(r["start_local"][:10])
        w = weeks.setdefault(r["week"], _blank_week())
        w["count"] += 1
        w["sports"].add(s)
        w["days"].add(day.weekday())
        streak, monday = 0, dt.date.fromisoformat(r["week"])
        while monday.isoformat() in weeks:
            streak += 1
            monday -= dt.timedelta(days=7)
        hour = int(r["start_local"][11:13]) if len(r["start_local"]) >= 13 else 12
        speed = r.get("avg_speed_mps") or 0.0
        pace_min_mi = (MI / speed) / 60 if speed > 0 else None

        for m in MILESTONES:
            if m.key in won:
                continue
            k, sp, v = m.kind, m.sport, m.value
            hit = False
            if k == "single":
                hit = (sp == "any" or s == sp) and d >= v
            elif k == "climb":
                hit = (sp == "any" or s == sp) and c >= v
            elif k == "total":
                hit = dist[sp] >= v
            elif k == "total_climb":
                hit = climb >= v
            elif k == "money":
                hit = pence(points) >= v
            elif k == "count":
                hit = count[sp] >= v
            elif k == "week_count":
                hit = w["count"] >= v
            elif k == "week_streak":
                hit = streak >= v
            elif k == "pace":
                hit = s == sp and d >= MI and pace_min_mi is not None and pace_min_mi <= v
            elif k == "hour_before":
                hit = hour < v
            elif k == "hour_after":
                hit = hour >= v
            elif k == "weekend":
                hit = {5, 6} <= w["days"]
            elif k == "sports_in_week":
                hit = len(w["sports"]) >= v
            elif k == "all_sports":
                hit = len(sports_seen) >= v
            elif k == "single_time":
                hit = (sp == "any" or s == sp) and t >= v
            elif k == "total_time":
                hit = time_s >= v
            if hit:
                won[m.key] = {"key": m.key, "title": m.title, "message": m.message,
                              "date": day.isoformat(), "activity_id": r["id"], "sport": s}
    return sorted(won.values(), key=lambda x: (x["date"], x["key"]))


def selftest() -> None:
    keys = [m.key for m in MILESTONES]
    assert len(keys) == len(set(keys)), "duplicate key"
    assert len({m.title for m in MILESTONES}) == len(MILESTONES), "duplicate title"
    assert len({m.message for m in MILESTONES}) == len(MILESTONES), "duplicate message"
    kinds = {"single", "climb", "total", "total_climb", "money", "count", "week_count", "week_streak", "pace",
             "hour_before", "hour_after", "weekend", "sports_in_week", "all_sports", "single_time", "total_time"}
    assert all(m.kind in kinds for m in MILESTONES)
    assert len(MILESTONES) >= 100, len(MILESTONES)

    def row(i, sport, day, dist, climb=0, dur=1800, speed=None, hour=16, pts=None):
        from .rates import points_for
        p = points_for(sport, dist, climb)
        return {"id": i, "sport": sport, "start_local": f"{day} {hour:02d}:00:00", "week": (dt.date.fromisoformat(day)
                - dt.timedelta(days=dt.date.fromisoformat(day).weekday())).isoformat(), "distance_m": dist,
                "ascent_m": climb, "duration_s": dur, "avg_speed_mps": speed, "points": p["distance"] + p["ascent"],
                "excluded": None}

    rows = [
        row(1, "run", "2026-05-04", 2.1 * MI, 30, speed=MI / (9.5 * 60)),      # Mon: 2-mile run at 9:30/mi
        row(2, "cycle", "2026-05-09", 10.2 * MI, 120, dur=3700),               # Sat: 10-mile ride, over an hour
        row(3, "walk", "2026-05-10", 5.1 * MI, 105, hour=6),                   # Sun: 5-mile walk, early
        row(4, "cycle", "2026-05-12", 3 * MI, 0),                              # next week (streak 2)
        row(5, "other", "2026-05-13", 50 * MI, 0),                             # unscored: counts for nothing
        {**row(6, "run", "2026-05-14", 10 * MI, 0), "excluded": "the car"},    # struck: nothing
    ]
    got = {a["key"]: a for a in achieved(rows)}
    for k in ("first", "first_run", "run_1mi", "run_2mi", "pace_12", "pace_10", "first_cycle", "cycle_5mi",
              "cycle_10mi", "hour_long", "first_walk", "walk_2mi", "walk_3mi", "walk_5mi", "early_bird",
              "climb_100", "weekend", "week_3", "triathlete_week"):
        assert k in got, k
    assert got["run_2mi"]["date"] == "2026-05-04" and got["run_2mi"]["activity_id"] == 1
    assert got["weekend"]["date"] == "2026-05-10" and got["week_3"]["activity_id"] == 3
    assert "pace_9" not in got and "run_3mi" not in got and "run_10mi" not in got and "climb_250" not in got
    assert "streak_3" not in got and "dawn_patrol" not in got and "first_swim" not in got
    assert got["money_100"]["activity_id"] == 1                                  # 8.4 + 1.2 pts = 240p on the first run
    assert achieved([]) == []
    # a milestone is won once and dated to the first crossing
    twice = achieved(rows + [row(7, "run", "2026-06-01", 2.5 * MI)])
    assert sum(1 for a in twice if a["key"] == "run_2mi") == 1 and {a["key"]: a for a in twice}["run_2mi"]["date"] == "2026-05-04"
    print(f"milestones: selftest OK ({len(MILESTONES)} eggs)")


if __name__ == "__main__":
    selftest()
