# ⛵ Argo

Pocket money for getting out. A Garmin watch records the activity, Argo turns it into points at
the rates in [`argo/rates.py`](argo/rates.py), the points into pence, and the week into a statement
for Dad. His page shows what he has earned so far this week, what is owed, and what has been paid.

Nothing runs anywhere but GitHub: an Action syncs from Garmin every hour and publishes the page
to GitHub Pages; another sends the Sunday statement; a third is the **Pay** button. The data is
JSON in this repo, so every payment is a commit.

## One-time setup (Ben)

1. **Create the GitHub repository** — private is fine — and push this folder to it:
   ```bash
   git remote add origin https://github.com/<you>/argo.git && git push -u origin main
   ```
2. **Garmin tokens.** On the PC, once:
   ```bash
   pip install garminconnect && python -m argo.login
   ```
   It asks for the Garmin Connect email and password of the account the watch syncs to (and
   an MFA code if the account has one), then prints a long token string. Paste that into
   **Settings → Secrets and variables → Actions → New repository secret** named `GARMINTOKENS`.
   The tokens last about a year; when the sync Action starts failing to log in, run it again.
3. **The page.** Settings → Pages → *Deploy from a branch* → branch `main`, folder `/docs`.
   The address is `https://<you>.github.io/argo/`; add it as a repository **variable** named
   `PAGE_URL` (Settings → Secrets and variables → Actions → Variables) so the email can link it.
   On his phone, open the address and *Add to Home Screen* — it installs as an app.
4. **The email.** Five secrets: `SMTP_USER` (the Gmail address it sends from), `SMTP_PASS` (a
   Gmail **App Password** — Google account → Security → 2-Step Verification → App passwords; never
   the account password), `MAIL_TO` (where the statement goes), and optionally `SMTP_HOST` /
   `SMTP_PORT` if not Gmail (defaults `smtp.gmail.com` / `587`).
5. **Run it once by hand:** Actions → *sync* → Run workflow. A green run and a commit called
   `sync …` means it is working; the page updates a minute later.

## The week

- Monday to Sunday, UK time. The scheme opens on `SCHEME_START` (rates.py); nothing before it counts.
- **Sunday night** the statement arrives: every activity, its points, anything flagged
  (implausible speed, no heart rate, an unscored sport), the week's money and the running total owed.
- **Pay:** the email's link opens the *pay* workflow — *Run workflow*, leave the fields blank, and
  the oldest unpaid week is marked paid today. His page moves it from *owed* to *paid*.
- **Strike:** the same form with an activity id in *strike* (ids are in the email and on the page)
  removes it from scoring, with the reason shown on his page. *unstrike* undoes it.

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
[`ARGO_BRIEF.md`](ARGO_BRIEF.md).
