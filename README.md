# ⛵ Argo

Pocket money for getting out. Thomas's Garmin watch records the activity, Argo turns it into
points at the rates in [`argo/rates.py`](argo/rates.py), the points into pence, and the week into
a statement for Dad. His page shows what he has earned so far this week, what is owed, what has
been paid — the Easter eggs he has found (hidden milestones, each with its own message), and his
personal bests: a banner when he breaks one, and his top five at everything, sport by sport.

Nothing runs anywhere but GitHub: an Action syncs from Garmin every hour and publishes the page
to GitHub Pages; another opens the Sunday statement as an issue (GitHub emails it to you); your
reply of **paid** settles the week. The data is JSON in this repo, so every payment is a commit.

## Setting it up — two things are yours, everything else is scripted

1. **Log the GitHub CLI in** (installed already), once, in a terminal — it opens the browser:
   ```bash
   gh auth login --web
   ```
2. **Run the setup.** Creates the private repo `<you>/argo` from this folder, pushes it, switches
   on Pages, sets the page address, and tells you what is left:
   ```bash
   python setup.py
   ```
3. **Log Thomas's Garmin in**, once — it asks for the email and password of the account his watch
   syncs to (and an MFA code if there is one), stores the tokens as the `GARMINTOKENS` secret,
   starts the first sync on GitHub and fetches his activities here too:
   ```bash
   python -m argo.login
   ```
   The tokens last about a year; when the *sync* Action starts failing to log in, run it again.

Then open `https://<you>.github.io/argo/` on his phone and *Add to Home Screen*.

The sync runs hourly from then on. Everything since **1 May 2026** is fetched and scored, so the
first statement will show a backlog of owed weeks: reply **paid all** to it to settle them in one go.
The Easter eggs count from **21 September 2026** (`EGGS_START`), so the backlog wins none of them.
His whole Garmin history is on the page too (Actions → *sync* → tick *whole history*, or
`python -m argo.sync --all`): anything before `SCHEME_START` is shown as *before Argo* and never paid.
Steps count from the same day (`STEPS_START`): 50p per 10,000, gross, every day, from the watch.

## The week

- Monday to Sunday, UK time. The scheme opens on `SCHEME_START` (rates.py); nothing before it counts
  (it is on his page as history, earning nothing).
- **Sunday night** a statement issue opens and GitHub emails it to you: every activity, its
  points, anything flagged (implausible speed, no heart rate, an unscored sport), the eggs found,
  the week's money and the running total owed.
- **Pay:** reply to the email (or comment on the issue) with **paid** — the week is marked paid,
  the issue closes, his page moves it from *owed* to *paid*. **paid all** settles every unpaid week
  up to that one. A word after it (**paid cash**) is kept as a note.
- **Strike:** reply **strike `<id>` the reason** (ids are in the statement's table) and the
  activity earns nothing, with the reason shown on his page; **unstrike `<id>`** undoes it. Then **paid**.
- The *pay* workflow (Actions tab → *pay* → Run workflow) does the same from a form, if you prefer.

## Changing the rules — the admin panel

Every number (pence per point, the per-mile and per-climb rates, the steps rate, the weekly cap,
the three start dates) is a **setting** with a default in `argo/rates.py` and an override in
`data/settings.json`. Three ways to change one, all the same table:

- **The form:** Actions → *settings* → *Run workflow*. Fill in only what you want to change; blank
  stays as is; *other* takes `key=value` pairs for the rest; *reset* puts one (or `all`) back to
  its default. Works from a phone. A bad value is refused with the reason.
- **A reply on a statement issue:** `set steps_pts_per_10k 3`, `reset week_cap_points`.
- **On the PC:** `python -m argo.settings` lists them all; `--set key value --apply` changes one.

A change re-scores every week, past and present (points are never stored), and is a commit —
`git log data/settings.json` is the history of the rules. The settings are:

`pence_per_point` · `week_cap_points` · `scheme_start` · `eggs_start` · `steps_start` ·
`steps_pts_per_10k` · `steps_per_mile_deducted` · `run_per_mile` · `walk_per_mile` ·
`cycle_per_mile` · `kayak_per_mile` · `swim_per_100m` · `run_ascent_per_100m` ·
`walk_ascent_per_100m` · `cycle_ascent_per_100m` · `min_distance_m` · `bounty_outing_min_miles` ·
`bounty_outing_min_minutes` · `bounty_cap_pence`

## The weekly bounty

One mission a week on top of his usual pocket money: a target (*Ride 10 miles this week*), one
bar, one reward (a fixed bonus, a multiplier on that sport's money or on the whole week, or a
real-world treat you hand over yourself).

- **Sunday night**, after the statement, a second issue opens with **next week's bounty, drawn
  from your menu**. Thomas cannot see it yet.
- **Reply** `approve` and it goes on his page as a wanted poster with a progress bar. `veto` means
  no bounty that week. `reroll` draws another. `bar 8`, `reward £3`, `reward x2`,
  `reward week x1.5` and `reward treat <what it is>` change it, and `target <key>` picks another
  line of the menu. You can put several on separate lines. If you never approve, it lapses with
  the week.
- **Once he can see it**, it can only get easier (a lower bar) or bigger (more of the same reward).
  It can never be withdrawn or made harder.
- When he hits it he gets a fanfare and the money joins that week's statement. A miss just goes
  away: he never sees a *failed*.
- **The menu is yours**, in two files that open in Excel:
  - [`data/bounty_targets.csv`](data/bounty_targets.csv) holds what a bounty asks. Each line has
    `on`, a `weight`, `sports`, a `metric`, `counted` (`week` or `one` outing), the `min`–`max`
    range its bar is drawn from in `step`s, and the `words` he reads, where `{bar}` is the number.
  - [`data/bounty_rewards.csv`](data/bounty_rewards.csv) holds what it pays. Money is in pounds.
  - The metrics are `miles`, `climb_m`, `hours`, `outings`, `days`, `sports`, `steps` and
    `steps_days`.
  - Sports are `run`, `walk`, `cycle`, `swim`, `kayak`, `foot` (walk or run) and `any`.
  - The reward types are `fixed`, `target_x` (multiplies the bounty's sports' money that week),
    `week_x` (multiplies the whole week) and `real` (a treat, in `words`).
  - Cycling carries most of the weight, since he can get out on his bike on his own.
- **The form**, Actions → *bounty* → *Run workflow*, takes the same lines as a reply.
  `python -m argo.bounty` on the PC shows this week's and next week's bounties and the menu, with
  how often each line's lowest bar would have been hit.

## A sync on the hour — cron-job.org

GitHub's own schedule is best-effort: asked hourly, it ran 4–6 times a day in October 2026. So
cron-job.org (free) starts the sync every hour instead, by calling GitHub's "run workflow" door.
GitHub's schedule stays on as a backup; the two cannot collide (the sync waits its turn).

1. **A token that can only start Argo's workflows.** GitHub → Settings → Developer settings →
   Personal access tokens → **Fine-grained tokens** → Generate new token. Name *argo cron*,
   expiry up to a year, **Repository access: Only select repositories → argo**,
   **Permissions → Repositories → Actions: Read and write** (nothing else). Copy the token.
2. **The cron job.** cron-job.org → Create cronjob:
   - URL: `https://api.github.com/repos/LoneWonderer1976/argo/actions/workflows/sync.yml/dispatches`
   - Schedule: every hour, at minute **37** (GitHub's own tries are at :07, so the two interleave)
   - Advanced → Request method **POST**, headers:
     - `Accept: application/vnd.github+json`
     - `Authorization: Bearer <the token>`
     - `X-GitHub-Api-Version: 2022-11-28`
     - `Content-Type: application/json`
   - Request body: `{"ref":"main"}`
   - Save and press *Test run*: a good call answers **204**, and a *sync* run appears under the
     repo's Actions tab with *workflow_dispatch* beside it.
3. **When the token expires** the job starts failing (401) and cron-job.org emails you; make a new
   token the same way and paste it over the old one. GitHub's own schedule keeps things moving
   meanwhile.

Hourly costs about 720 of the private repo's 2,000 free Actions minutes a month. Not more often:
the minutes run short around every 30 minutes, and Garmin dislikes being polled hard.

## On the PC

```bash
python check.py                 # every selftest + pyflakes
python -m argo.sync --dry-run   # what Garmin has that we do not
python -m argo.sync --all       # his whole history, and any track a past run missed
python -m argo.score --print    # the ledger as a table (and rebuilds docs/data.json)
python -m argo.statement --print
python -m argo.pay              # dry run; --apply to write
python -m argo.bounty           # this week's and next week's bounty, and the menu
python -m argo.bounty --do "approve" --apply    # the same lines as a reply on the bounty issue
python -m argo.demo             # a made-up data.json to look at the page before the first sync
```

Scripts that write are dry-run by default and take `--apply`. The design log is
[`ARGO_BRIEF.md`](ARGO_BRIEF.md). An email statement over SMTP is also there if ever wanted
(`argo/statement.py`'s docstring has the five secrets); the issue route needs nothing.
