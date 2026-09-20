# Argo — design log

The reasoning behind the app, in the order the decisions were made. `README.md` says how to run
it; this says why it is the shape it is. A decision that is not written here did not happen.

## What it is (20/09/2026)

A sister app to Nostos Datum for Ben's son: his Garmin activities, scored as points the way
Ben's own are, converted to pocket money, with a weekly statement to Ben and a phone page for
him. Ben's words: *"the main point is to award his activities points in much the same way as my
activity points, the points will then be converted to pocket money (the aim being to get him
active) — or possibly screentime or both, I'd want a summary emailed to me each week so I can pay
him, he can then track in real time how much pocket money his activities are earning him."*

Decided the same day, all Ben's:

| | |
|---|---|
| Garmin account | his own, so the sync logs in as him and sees only his activities |
| Rates | *"nominally use the same basic activity scores for distance and ascent as those I use"* — Nostos Datum's `DISTANCE_PER_MILE`, `SWIM_PTS_PER_100M`, `ASCENT_PTS_PER_M`, copied into `rates.py`; the detail *"we'll decide in detail later"* |
| Money | **25p a point** |
| Sports | walking, cycling, running, swimming, kayaking; *"we can add more if needed"* |
| Hosting | *"hosted somewhere if free"* — GitHub Actions + Pages |
| Name | Argo — the ship that sailed for the Golden Fleece; the voyage that pays out at the end |
| Folder | its own, `C:\Argo`, its own repo; nothing imported from the Fitness Project |

What 25p a point comes to: £1 a mile run or kayaked, 50p a mile walked, 25p a mile cycled, 25p
per 100 m swum; plus 1p per metre climbed running, ½p walking, ¼p cycling. A 2-mile run is £2.
`WEEK_CAP_POINTS` exists and is off — the slot is there for when the rates are settled.

## The shape

**sync → score → ledger → page → statement.** Five modules and a rate table, all stdlib except
`garminconnect`, no database.

- **The data folder is the database.** One JSON file per activity (Argo's fields plus Garmin's
  summary whole, as the original), one per track, a ledger of paid weeks, a file of strikes.
  Plain files in git means every sync, payment and strike is a commit with a date, `git log` is
  the audit trail, and GitHub Actions can read and write it with nothing installed. At a child's
  volume (a few activities a week, tracks thinned to 400 points) the repo stays small for years.
- **Derive, never cache.** `score.py` recomputes every point and every pound from the activity
  files against `rates.py` on every run. Change a rate, strike an activity, and the whole history
  re-scores; the page cannot disagree with the rule. The only stored state is what a person
  decided: which weeks are paid, which activities are struck.
- **Money rounds on the week.** Per-activity pence are shown, but a week's `pence` is rounded
  from the week's points total, so the sum of the cards can differ from the week by a penny and
  the week is what is owed.
- **Three states for a week:** *current* (still earning), *owed* (complete, unpaid), *paid* (in
  the ledger, with a date). The page's three numbers are those three sums. "Real time" for him
  means the current week's figure moving as the hourly sync lands.
- **Flags, never refusals.** A "bike ride" at 40 mph, a walk with no heart rate, a sport the
  scheme does not pay: each is scored as the rule says and MARKED — highlighted on his page,
  printed on the statement — so Ben can strike it before he pays. The app never docks a child
  silently; the adjudicator is the parent, and the parent is shown the evidence.
- **The summary, not the FIT file.** Garmin's activity list carries distance, ascent, duration,
  heart rate and speed — everything the rate table and the flags need — so there is no FIT
  parsing. The track is the GPX download, only asked for when the summary says one exists, and
  a failed track download stores the activity anyway: a missing map is not a missing payment.
- **The window.** From the later of `SCHEME_START` and the day before the newest stored
  activity, to today; an id already stored is skipped. A re-run is free and `--since` can widen
  the window without harm. Nothing before `SCHEME_START` is stored or paid.
- **Weeks on the watch's local clock.** `startTimeLocal` is what a person means by "Tuesday's
  run"; the week is Monday–Sunday from that string, never the UTC instant.
- **The login is one interactive step, on Ben's PC.** `login.py` asks for the credentials once,
  caches tokens locally and prints the token string for the `GARMINTOKENS` secret. The
  `garminconnect` client accepts the string directly (anything over 512 characters is taken as
  the tokens themselves). No password is stored anywhere and none passes through the code path
  the Action runs.

## Why GitHub Actions and Pages

The free-tier web hosts either sleep (a 30-second wake when he opens the page) or have no disk
that survives a deploy. Actions has a scheduler, a secrets store and a git remote it can push
to; Pages serves a static folder with no server to wake. The costs are accepted: the sync is
hourly rather than instant (a watch sync is not instant either), and the Pay button is a
`workflow_dispatch` form rather than a button on the page — the page has no server to receive a
click, and putting a write path on a public page for a child's money is not worth a nicer button.
The statement carries the link to the form. If the hourly cadence or the form grates, the same
code runs unchanged on any machine with cron and Python.

## The page

Mobile first: one column, a hero with the three numbers, the weeks as a bar chart and a list,
the activities as cards, totals by sport, and the rate table in his own money ("£1.00 a mile").
A card opens a sheet with the numbers and a Leaflet map on OpenStreetMap tiles (no key, no
account). It reloads `data.json` whenever the app comes back to the foreground. A manifest and
icons make it installable from the browser's *Add to Home Screen*. No service worker on purpose:
a cached `data.json` is the opposite of real time.

## The same evening: backdated, the Easter eggs, and GitHub as the postman (20/09/2026)

Ben: *"I'd like to backdate activities to 1st May and hide some Easter eggs, motivational
messages that appear when he achieves a milestone, his name is Thomas, milestones might be 10
mile cycle, 2 mile run, 5 mile walk, would like loads and each to have a unique message, I'd also
like you to do as many of the steps as you can before I do anything manually."*

- **`SCHEME_START` = 1 May 2026**, a Friday; the ledger's first week is the Monday before it (27
  April) and holds only what happened from the 1st. A complete week that earned nothing is now
  **empty** rather than *owed* — twenty £0.00 weeks marked OWED before the first sync would have
  been noise — and `pay --through` / a reply of **paid all** settle a backlog in one go, since
  the first statement will carry five months of owed weeks.
- **The Easter eggs are `argo/milestones.py`: 111 of them, each a rule and a message written for
  the moment**, for Thomas by name where it reads naturally. Kinds: one activity's distance or
  climb, all-time distance and climb, money, counts, a week's count, week streaks, pace, time of
  day, time on feet, a weekend double, three sports in a week, all five sports. The ladders sit
  on real things — Hadrian's Wall, the South Downs Way, Land's End to John o' Groats, the
  Channel, Snowdon / Ben Nevis / Mont Blanc / Everest, round the Isle of Wight — and the money
  eggs on the voyage (the £100 one is the Golden Fleece). Each is won by the FIRST activity that
  crosses it and dated to that day; it is evaluated afresh on every run, so a strike can take
  one back and a rate change can move the money ones, exactly as the ledger moves.
- **Hidden means hidden.** `data.json` carries only the WON eggs; the rest are a count. The page
  shows a trophy cabinet of the won ones (tap one to read it again), three 🥚 for what is still
  hidden, and the number. A newly-won egg gets a full-screen fanfare when the page is next
  opened — which ones this phone has already celebrated is `localStorage`, a per-viewer
  convenience; a wiped phone replays them, which is hardly a punishment. A phone opening the
  page for the first time against a long history is NOT made to sit through months of fanfares:
  more than five unseen at once are marked seen silently and live in the cabinet.
- **GitHub is the postman.** The Sunday statement is a GitHub ISSUE, not an email: GitHub emails
  the repository's owner about every issue anyway, so the statement arrives in Ben's inbox with
  no mail account, no app password, nothing to configure. And a reply to that email lands on the
  issue as a comment, so **`paid.yml` reads the first line of any comment by the owner** —
  *paid*, *paid all*, *strike <id> reason*, *unstrike <id>* — makes the write, answers on the
  issue and closes it. `argo/reply.py` is the parser; a refusal from `pay.py` (the week is not
  over) is posted as the answer rather than failing the run. SMTP stays as an optional extra.
- **The setup is two commands that need Ben and one that does not.** `gh auth login --web` (his
  GitHub, his browser), `python -m argo.login` (Thomas's Garmin password, typed by Ben, stored
  nowhere — the script sets the `GARMINTOKENS` secret through `gh` itself and starts the first
  sync), and `python setup.py` between them, which creates the private repo, pushes, switches on
  Pages and sets `PAGE_URL`. The GitHub CLI was installed with winget for this. Nothing else
  is manual.

## Two clocks: the money from 1 May, the eggs from 21 September (20/09/2026, late)

Ben: *"will the easter eggs get burnt through on first load"* — and then, *"can we set the
pocket money to back date to May but eggs start from tomorrow."* As first built the five
backdated months would have won thirty-odd eggs the moment the first sync landed, with the
fanfare skipped for a backlog that size: the discovery gone before he had opened the page once.
So `rates.EGGS_START` (21 September 2026, the Monday) is a second clock: `milestones.achieved()`
ignores every activity before it, and its totals, counts and streaks start there too, while
the ledger keeps paying from `SCHEME_START`. Set `EGGS_START = SCHEME_START` to count history
instead. `check.py` asserts the eggs' start is not before the ledger's.

Also settled: **the page is public** (GitHub Pages from a private repo is public on the free
plan; private sites are an Enterprise feature). Ben chose to accept it over a Strava-style
privacy trim on the tracks or no maps at all — *"I'll accept it"*. The address is his
username plus "argo"; the page carries Thomas's first name and his routes.

## Steps (20/09/2026, late)

Ben: *"for Thomas can we add steps, give 25p per 10,000 steps minus 2000 steps per mile walked
or run so we don't pay twice, don't backdate this, start from tomorrow"* — and, before it was
built, *"I've changed my mind make it gross, 25p per 10,000 irrespective."*

- **A third clock.** `STEPS_START` = 21 September 2026. The sync reads Garmin's daily step
  counts from there (`get_daily_steps`), and `data/steps.json` is the one file the sync
  REWRITES: a day's count grows until midnight, so the last three days are re-read every run
  and overwritten. Everything else in `data/` is still written once.
- **1 point per 10,000 steps, gross.** `STEPS_PTS_PER_10K` = 1.0 at 25p a point. The deduction
  Ben asked for and withdrew in the same minute is kept as a dial at zero
  (`STEPS_PER_MILE_DEDUCTED` = 0): the miles on foot per day are still computed and shown on the
  day's row, so turning it back on is a number, not a build.
- **The week's points are activities plus steps**, and the cap, the money and the statement all
  sit on that total. A complete week with no activities but some steps is *owed*, not *empty*.
- **Seven steps eggs** — 10k / 15k / 20k / 30k days, 70k and 100k weeks, a million — walk the
  days rather than the activities, from `EGGS_START` like the rest.
- The page shows the last fourteen days as bars (gold at 10,000 and over), the week rows carry
  the count, and the rate table has its row. The statement has a steps line.

## Not built, deliberately

- **Screen time.** Ben: *"or possibly screentime or both"*. Points are the currency; a second
  exchange rate is a second column in the ledger and nothing in the scoring. Wait for the rates.
- **Streaks, bonuses, badges.** The brief was simple. A weekly cap comes first if anything does.
- **A sixth sport.** `sports.py` maps Garmin's type keys by their words; an unlisted sport reads
  as `other`, earns nothing and is flagged, so the first time he logs one it appears on the
  statement and Ben can say whether it pays.
