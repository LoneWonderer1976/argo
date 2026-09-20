# ⛵ Argo

Pocket money for getting out. Thomas's Garmin watch records the activity, Argo turns it into
points at the rates in [`argo/rates.py`](argo/rates.py), the points into pence, and the week into
a statement for Dad. His page shows what he has earned so far this week, what is owed, what has
been paid — and the Easter eggs he has found (111 hidden milestones, each with its own message).

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

## The week

- Monday to Sunday, UK time. The scheme opens on `SCHEME_START` (rates.py); nothing before it counts.
- **Sunday night** a statement issue opens and GitHub emails it to you: every activity, its
  points, anything flagged (implausible speed, no heart rate, an unscored sport), the eggs found,
  the week's money and the running total owed.
- **Pay:** reply to the email (or comment on the issue) with **paid** — the week is marked paid,
  the issue closes, his page moves it from *owed* to *paid*. **paid all** settles every unpaid week
  up to that one. A word after it (**paid cash**) is kept as a note.
- **Strike:** reply **strike `<id>` the reason** (ids are in the statement's table) and the
  activity earns nothing, with the reason shown on his page; **unstrike `<id>`** undoes it. Then **paid**.
- The *pay* workflow (Actions tab → *pay* → Run workflow) does the same from a form, if you prefer.

## On the PC

```bash
python check.py                 # every selftest + pyflakes
python -m argo.sync --dry-run   # what Garmin has that we do not
python -m argo.score --print    # the ledger as a table (and rebuilds docs/data.json)
python -m argo.statement --print
python -m argo.pay              # dry run; --apply to write
python -m argo.demo             # a made-up data.json to look at the page before the first sync
```

Scripts that write are dry-run by default and take `--apply`. The design log is
[`ARGO_BRIEF.md`](ARGO_BRIEF.md). An email statement over SMTP is also there if ever wanted
(`argo/statement.py`'s docstring has the five secrets); the issue route needs nothing.
