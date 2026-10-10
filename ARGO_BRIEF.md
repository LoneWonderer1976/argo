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
- **Hidden means hidden.** The whole Trophies panel is absent from the page until the first egg is won (Ben, 20/09: *"so it is a surprise"*) — the first fanfare is the first he hears of them. `data.json` carries only the WON eggs; the rest are a count. The page
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
- **2 points per 10,000 steps, gross** — 50p. `STEPS_PTS_PER_10K` = 2.0 at 25p a point (it was 1.0, 25p, for the day before the scheme's first steps landed: Ben, 21/09, *"amend steps value to 50p per 10,000"*). The deduction
  Ben asked for and withdrew in the same minute is kept as a dial at zero
  (`STEPS_PER_MILE_DEDUCTED` = 0): the miles on foot per day are still computed and shown on the
  day's row, so turning it back on is a number, not a build.
- **The week's points are activities plus steps**, and the cap, the money and the statement all
  sit on that total. A complete week with no activities but some steps is *owed*, not *empty*.
- **Seven steps eggs** — 10k / 15k / 20k / 30k days, 70k and 100k weeks, a million — walk the
  days rather than the activities, from `EGGS_START` like the rest.
- The page shows the last fourteen days as bars (gold at 10,000 and over), the week rows carry
  the count, and the rate table has its row. The statement has a steps line.

## The admin panel (21/09/2026)

Ben: *"is it possible to add a backend or admin mechanism so I can adjust any of these variables
manually"*. There is no server to put a panel on, and adding one for this would be the first
piece of the app that could go down. So the panel is GitHub: **a `settings` workflow whose
"Run workflow" form is the admin screen** — eight named fields for the money rates, an *other*
field for `key=value` pairs, a *reset* field — plus `set <key> <value>` / `reset <key>` as a
reply on a statement issue, and `python -m argo.settings` on the PC. All three go through one
table, `rates.SETTINGS`, which names every constant that may be overridden, its type and a note.

The mechanism: the numbers in `rates.py` are the DEFAULTS; `data/settings.json` holds
overrides; `rates.py` applies them at the bottom of its own import, so every module that does
`from .rates import X` sees the override. `DEFAULTS` is captured before that, so the report can
show *current / default / overridden*. A value is validated before anything is written (a date
must be a date, a rate cannot be negative, `pence_per_point` cannot be 0), and a batch is
all-or-nothing. `check.py` runs the selftests with `ARGO_NO_SETTINGS=1` so they test the
defaults whatever Ben has set.

Because points are derived on every run, a change re-scores the whole history, past weeks
included — which is what "adjust the variables" should mean, and is also the caveat: lowering a
rate lowers an *owed* week's figure. A *paid* week keeps its `pence` in the ledger as paid.

## His whole history, and the activities filtered and sorted (29/09/2026)

Thomas asked, through Ben: *"bring his entire Garmin history in, this won't affect pocket money as
everything prior to the original start date won't count"*, and *"his activities to be both
filterable and sortable, filter by date, sport etc, sort by distance, time, speed etc"*.

- **History is stored, shown, never paid.** The sync no longer drops what is older than
  `SCHEME_START`; `score.py` marks such a row `history`, gives it no points and no flags (there is
  nothing for Ben to adjudicate), and `paid_rows()` keeps it out of every week, every egg, the
  steps and the totals. The **scheme's start date decides the money, not what the sync happened
  to fetch** — so moving `scheme_start` earlier in the settings would pay history, which is what
  that setting should mean. Measured on the import: 45 activities (Jan 2025 → Apr 2026), and the
  weeks, the eggs and every pound identical before and after.
- **`python -m argo.sync --all`**, or the *whole history* tick on the sync workflow's form, asks
  Garmin from 2000 (a query bound, not a rule) and also re-asks for any track a past run missed
  (a failed GPX download stores the activity without its map; in the trial import two failed the
  first time and came back on the retry, and the real one needed none: 60 tracks for 60). A
  half-second pause between GPX downloads keeps a big import from being a burst.
- **Garmin's safety records are never stored.** The watch's assistance button logs an
  "activity" (`typeKey` *assistance*) with the place it was pressed, in the same list as a run.
  One was in his history (14 March 2026, late evening). It is not exercise and the page is
  public, so the sync skips any type whose key says *assist* or *incident*. That is held back
  rather than published because publishing cannot be undone and holding back can; if Ben wants
  it on the page, it is one word out of `SAFETY_WORDS` and an `--all` run.
- **The filters are the phone's own.** Sport chips (several at once), *When* (all time, this
  week, the last 30 days, each year, since Argo began, before Argo, chosen dates), a name search,
  and ten sorts (newest / oldest, distance, time, speed, climb, most earned, each way). An
  activity with no distance or no speed sorts LAST whichever way round, so *shortest* does not
  open on a page of breathing exercises. The choice is remembered in `localStorage`, a per-viewer
  convenience like the eggs already seen; clearing it keeps the sort.
- **Speed is the watch's own number**: pace (min/mi) on foot, per 100 m in the pool, mph on
  wheels and water, from Garmin's `averageSpeed`, which counts stops, so a long hike reads slow.
  It is Garmin's figure, so it matches the app on his phone.
- **Everything the list shows is summed**: a line under the filters (count, miles, climb, time,
  and the money from activities, which is not the hero's *earned ever*, since that has the steps
  in it), and the Totals table follows the same filter. The list pages at 30, since the history
  more than tripled it. History cards say *before Argo* where the money would be; the sheet
  says why, and gained speed and max heart rate.
- In passing: the score and statement selftests called `build()` without steps, so they read the
  LIVE `steps.json` and had been failing since his first steps landed on 21/09. They pass `{}` now.

## The weekly bounty (08/10/2026)

Ben: *"every sunday night I want to generate a bounty mission for Tom, the bounty mission will be
a target activity, distance, elevation, number or amount and will pay a fixed amount, a
multiplier or some other bounty on his usual pocket money, for example If you cycle 10 miles this
week you will receive double pocket money for your cycling distance, i would like control over
it so need a tool to let me select the week's bounty, happy for this to be auto and i rubber
stamp or veto"*, and *"thrash out this idea for me before building"*. The design was thrashed
out first. His answers came the same evening, then *"sounds good, lean on cycling as he likes to
get out on his bike and can do that independently"*. Built that night: `argo/bounty.py`.

**Measured first** (his last 12 complete weeks, to 4 October): he went out in 8 of them. Most
of those weeks had one outing; a few had two or three. He covered 4 to 14 miles a week, mostly
walking, and **rode in only 2 of the 12 weeks**. There has been no run, swim or kayak since May,
and he averages 8–9k steps a day. So the bounty's main job is a second outing in a one-outing
week, and a first in an empty one. *Two outings this week* would have been hit in 4 of the 12.

**Ben's rulings:**

| | |
|---|---|
| Silence | **held until he approves.** Nothing reaches Tom's page without his yes. A proposal not approved by the week's end lapses (the next Sunday's proposal closes its issue) |
| Rewards | **all four:** a fixed bonus; a multiplier on the target's money (*double your cycling money*); a multiplier on the whole week; a real-world reward he honours by hand, from a list he writes (none yet: the sheet carries one example line, switched off) |
| The bar | **his ranges only.** Each menu line carries a min–max, and the draw takes a step inside it. The proposal still prints how often his last 12 weeks would have hit it, as information, not a rule |
| Shape | **one bar.** Hit it, get it: no stretch rung, no partial credit |
| Weight | **lean on cycling.** The starter menu gives the five cycling lines 14 of 23 weight, about 61 % of draws |

**What was built. These are my readings; Ben may overrule any of them:**

- **The menu is his: two sheets that open in Excel**, `data/bounty_targets.csv` and
  `data/bounty_rewards.csv`. The brief's first draft said one file; two keep each sheet's
  columns honest.
  - A target line has `on`, `weight`, `sports`, `metric`, `counted` (`week` or `one` outing),
    `min`, `max`, `step` and `words` (`{bar}` is the number).
  - The sports are `run`, `walk`, `cycle`, `swim`, `kayak`, `foot` (walk and run) and `any`, or
    several separated by spaces.
  - The metrics are `miles`, `climb_m`, `hours`, `outings`, `days`, `sports`, `steps` and
    `steps_days`.
  - A reward line has a `type` (`fixed`, `target_x`, `week_x` or `real`), `min`, `max` and
    `step` (pounds for a fixed bonus, the multiplier otherwise), `cap` in pounds (blank means no
    cap) and `words` for a treat.
  - A bad line is refused with its line number, and the Sunday run fails loudly rather than
    drawing from half a menu. Excel's UTF-8 BOM and its plain cp1252 CSV are both read.
- **The starter menu** has 14 targets and 3 rewards:
  - **Cycling:** 8–15 miles a week; one ride of 6–12; 2–3 rides; 150–300 m climbed; 1.5–3 hours.
  - **The rest:** 2–3 outings; 2–4 active days; 5–10 miles walked; one walk of 4–7; 200–400 m
    climbed on foot; 2–4 hours moving; 10k steps on 3–5 days; a 1–3 mile run; two sports.
  - **Rewards:** £1–£3 fixed; double the target's money; ×1.5 the week. Both multipliers are
    capped at +£5.
  - **Measured on the menu:** the low ends of the cycling lines would each have been hit in only
    0–1 of his last 12 weeks, against 2–7 for the rest. That is what *lean on cycling* asks of
    him, not a pricing error; Ben has the numbers (`python -m argo.bounty` prints them) and the
    ranges are his.
- **"The target's money"** means everything the bounty's sports earned that week, distance and
  climb, so *double your cycling money* doubles the week's cycling. A steps bounty doubles the
  steps money. Doubling only the metric's own channel would have made a doubled *climb 150 m on
  your bike* worth 37p.
- **An outing counts toward a bar from 1 mile or 20 minutes** (`BOUNTY_OUTING_MIN_*`, settings).
  `MIN_DISTANCE_M`'s 100 m would make two strolls to the gate two outings.
- **No speed or pace bounties.** A speed bar rewards rushing on a bike on the roads, and speed
  is where a car journey passing as a ride would show.
- **The weekly cycle:**
  - **Sunday:** `statement.yml`'s second job, which runs after the statement whatever it did,
    draws next week's bounty (`--propose`). The draw is seeded by the week, never repeats last
    week's target, and skips a week that already has one. The job closes any open bounty issue
    as lapsed, then opens the new one with the week marker `<!-- argo-bounty: ... -->`.
  - **Ben's reply** goes to `paid.yml`'s second job. It is the same workflow as the paid replies
    on purpose: two workflows woken by one comment share the `argo-data` concurrency group, and a
    second pending run cancels the first.
  - **Every line of the reply is read**, unlike the statement's first-line rule. Lines that are
    not commands (a signature) are skipped, and the quoted email below stops the reading. So
    `target cycle_miles 10` / `reward x2` / `approve` works in one email.
  - **The form:** `bounty.yml` takes the same lines from a form.
  - **On the PC:** `python -m argo.bounty --do ... --apply`. When no week is named it means the
    week waiting for a decision, else next week.
- **The only stored state is `data/bounties.json`**: the target, the reward, the status
  (`proposed`, `live` or `vetoed`), the dates, who set it and the roll count. Whether it was hit
  is `progress()`, run by `score.weeks_from` on every build, strikes included. **Once hit, its
  money is part of the week's `pence`** (`pence_points` keeps the points' share), outside
  `WEEK_CAP_POINTS`. A paid week keeps its ledger figure as ever.
- **An approval mid-week counts the whole week from Monday.** Tom cannot have aimed at a bounty
  he could not see, so this is generous, not gameable. Approving a week that has ended is refused.
- **A live bounty is a promise.** A veto, a reroll or a new target is refused once he can see
  it. A bar may only come down, and a reward may only be more of the same kind, with a cap no
  lower. A hand-typed multiplier is capped at `BOUNTY_CAP_PENCE` (£5) unless the reply says
  `cap £N` or `cap none`.
- **A missed bounty pays nothing and says nothing to him**: no *failed* stamp, no streak. The
  statement tells Ben it was not hit, with how close he got.
- **His page.** data.json carries a LIVE bounty only, as `bounty.current` or, once approved
  before its week, `bounty.next` ("Starts on Monday"); a proposal never leaves the server.
  - **The poster:** a wanted poster above the trophies, with a progress bar, what is left, the
    days left, and *worth £x right now* for a multiplier.
  - **On a hit:** a fanfare through the Easter-egg overlay, once a phone (`argo.bounty.seen` in
    localStorage), and a CLAIMED stamp.
  - **The weeks list:** a hit week's row carries a 🎯.
- **The statement** has a bounty line, hit (when and what it adds, a treat to honour by hand) or
  not hit (how close). The week's money reads as points plus bounty.
- **Rehearsed on a copy** of the repo (propose, reroll, an email-shaped reply that sets a target,
  a reward and approves, the score, a veto refused once live), and on the page with an injected
  bounty in all three states, at phone width.
- **Not built:** letting Tom choose one of three. The page cannot take a click, so his choice
  would have to come through Ben.

## Personal bests: a banner when he breaks one, and the tables of his best (10/10/2026)

Ben: *"can we modify Argo so that Tom gets a banner whenever he breaks a PB, longest cycle, most
meters climbed etc etc and also give him tables of his best activities, walking, cycling etc"*.
Built the same day: `argo/records.py`, derived on every build like the rest.

- **What is a record:** for each sport, the longest (distance), the most climbing (run, walk and
  ride; a swim or a paddle has none), the longest time and the fastest; and the most steps in a
  day. Fastest needs a mile on foot or on the water, 3 miles on a bike, 100 m in the pool, so a
  200 m dash is never his fastest run.
- **The tables are his whole history**, before Argo included: a best is a best ever. Struck
  activities never count, and neither does one over its sport's speed ceiling
  (`MAX_SPEED_MPS`): that is the car, flagged or not (history carries no flags).
- **A break must beat every earlier one at the precision the page prints** (0.1 mile, a metre,
  a minute, a second of pace, 0.1 mph), so the page never says *10.0 mi, beating 10.0 mi*. A
  first ever is not a break; that is the Easter eggs' job.
- **Cheered from `RECORDS_START`** (10 October 2026, a setting, `records_start`). The walk
  through history before it only sets the bar, so the first build fired no backlog of banners.
- **The page:** a gold banner at the top for every record broken in the last 7 days (the newest
  break of each record only), tap it for the activity; a fanfare once a phone through the egg
  overlay (`argo.records.seen` in localStorage) for a break in the last 14 days; and **Your bests**
  under the activities, a chip per sport plus steps, the top five at each record with 🥇🥈🥉 and
  a NEW tag for the week's breaks; a row opens the activity.
- **The statement** carries a 🏅 line for the week's bests, with what each beat.
- **My readings Ben may overrule:** a bike's fastest is in the tables but never gets a banner (the
  bounty's reasoning: a speed prize rewards rushing on the roads); history counts toward the
  tables; a day's steps can be cheered while the day is still counting (the fanfare shows the
  count at that moment).
- **Found and fixed in passing:** the page re-reads data.json whenever it comes back into view,
  and each re-read while a fanfare was up rebuilt the queue, showed one and marked it seen, so a
  queue of eggs could lose all but the last. `celebrate()` now leaves an open fanfare alone.

## Not built, deliberately

- **Screen time.** Ben: *"or possibly screentime or both"*. Points are the currency; a second
  exchange rate is a second column in the ledger and nothing in the scoring. Wait for the rates.
- **Streaks, badges.** The brief was simple. A weekly cap comes first if anything does. (The one bonus, the weekly bounty, is Ben's own design of 08/10/2026, above.)
- **A sixth sport.** `sports.py` maps Garmin's type keys by their words; an unlisted sport reads
  as `other`, earns nothing and is flagged, so the first time he logs one it appears on the
  statement and Ben can say whether it pays.
