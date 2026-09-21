"""make_guide.py -- the one-page-per-topic PDF of every command and instruction for Argo and Atlas.

    python make_guide.py            # writes Argo_and_Atlas_guide.pdf beside this file

Kept in the Argo repo so it can be regenerated when the commands change.
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (PageBreak, Paragraph, Preformatted, SimpleDocTemplate,
                                Table, TableStyle)

OUT = Path(__file__).resolve().parent / "Argo_and_Atlas_guide.pdf"

ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=20, spaceAfter=6, textColor=colors.HexColor("#0f2a44"))
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=13.5, spaceBefore=12, spaceAfter=4, textColor=colors.HexColor("#0f2a44"))
H3 = ParagraphStyle("h3", parent=ss["Heading3"], fontSize=11, spaceBefore=8, spaceAfter=2)
P = ParagraphStyle("p", parent=ss["BodyText"], fontSize=9.6, leading=13, alignment=TA_LEFT, spaceAfter=4)
SMALL = ParagraphStyle("small", parent=P, fontSize=8.6, leading=11.5, textColor=colors.HexColor("#555555"))
CODE = ParagraphStyle("code", parent=ss["Code"], fontName="Courier", fontSize=8.8, leading=11.5,
                      backColor=colors.HexColor("#f3f5f8"), borderPadding=(4, 6, 4, 6), leftIndent=4, spaceBefore=2, spaceAfter=6)


def code(text: str):
    return Preformatted(text.strip("\n"), CODE)


CELL = ParagraphStyle("cell", parent=P, fontSize=8.8, leading=11, spaceAfter=0)


def cell(text):
    safe = text.replace("&", "&amp;").replace("<b>", "\u0001").replace("</b>", "\u0002").replace("<", "&lt;")
    return Paragraph(safe.replace("\u0001", "<b>").replace("\u0002", "</b>"), CELL)


def table(rows, widths, header=True):
    rows = [[cell(("<b>%s</b>" % c) if i == 0 and header else c) if isinstance(c, str) else c for c in r] for i, r in enumerate(rows)]
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [("FONT", (0, 0), (-1, -1), "Helvetica", 8.8), ("LEADING", (0, 0), (-1, -1), 11),
             ("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d0da")),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3e7ed")), ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.8)]
    t.setStyle(TableStyle(style))
    return t


story = []
A = story.append

A(Paragraph("Argo &amp; Atlas — the guide", H1))
A(Paragraph("Every command and instruction for the two apps, in one place. Argo is Thomas's pocket-money app; "
            "Atlas is Joe's stats page. Both run entirely on GitHub: an Action syncs from Garmin every hour and "
            "publishes a page; the data is JSON in the repository. Generated 21 September 2026 from the code as it stood.", P))

A(Paragraph("The addresses", H2))
A(table([
    ["", "Argo (Thomas)", "Atlas (Joe)"],
    ["His page", "https://lonewonderer1976.github.io/argo/", "https://lonewonderer1976.github.io/atlas/"],
    ["The repository", "https://github.com/LoneWonderer1976/argo", "https://github.com/LoneWonderer1976/atlas"],
    ["Actions (the buttons)", "…/argo/actions", "…/atlas/actions"],
    ["Statements (issues)", "…/argo/issues", "—"],
    ["On the PC", "C:\\Argo", "C:\\Atlas"],
], [38 * mm, 66 * mm, 66 * mm]))
A(Paragraph("Both pages install on a phone from the browser's <b>Add to Home Screen</b>. Both are public pages "
            "(GitHub Pages on the free plan), as agreed.", SMALL))

# ------------------------------------------------------------------ setup
A(Paragraph("One-time setup", H2))
A(Paragraph("<b>Argo is done.</b> Atlas has one step left, which needs Joe's Garmin email and password typed by you "
            "(nothing stores them; the tokens they produce last about a year):", P))
A(code("""
cd C:\\Atlas
python -m atlas.login
"""))
A(Paragraph("That stores the Garmin tokens as the repository secret <font face='Courier'>GARMINTOKENS</font>, starts the "
            "first sync on GitHub, and fetches his activities to the PC as well. The page fills a few minutes later.", P))
A(Paragraph("If either app's <i>sync</i> Action ever starts failing to log in (about a year on), run the same login "
            "command in that app's folder again — <font face='Courier'>python -m argo.login</font> for Argo.", P))
A(Paragraph("Everything else was scripted: the repositories, GitHub Pages, the page addresses. To rebuild any of it "
            "(for a new copy of either app, say), <font face='Courier'>python setup.py</font> in the folder is safe to re-run "
            "and skips what is already done. It needs the GitHub CLI logged in: "
            "<font face='Courier'>gh auth login --web</font>, once.", P))

# ------------------------------------------------------------------ Argo week
A(PageBreak())
A(Paragraph("Argo — the week", H2))
A(Paragraph("The week runs <b>Monday to Sunday</b>, UK time. The ledger pays from <b>1 May 2026</b>; the Easter eggs and "
            "the steps count from <b>21 September 2026</b>. Everything is derived from the stored activities on every "
            "run, so a rule change re-scores every week.", P))
A(Paragraph("What it pays (the defaults — every one is a setting, see <i>Changing the rules</i>)", H3))
A(table([
    ["", "points", "money at 25p a point"],
    ["Running", "4 per mile + 1 per 25 m climbed", "£1.00 a mile + 1p per metre climbed"],
    ["Walking", "2 per mile + 1 per 50 m climbed", "50p a mile + ½p per metre climbed"],
    ["Cycling", "1 per mile + 1 per 100 m climbed", "25p a mile + ¼p per metre climbed"],
    ["Kayaking", "4 per mile", "£1.00 a mile"],
    ["Swimming", "1 per 100 m", "25p per 100 m"],
    ["Steps", "2 per 10,000, gross, every day", "50p per 10,000"],
    ["Anything else (football, breathwork…)", "0 — shown, flagged, unpaid", "—"],
], [52 * mm, 60 * mm, 58 * mm]))
A(Paragraph("Money is rounded on the week's total, not per activity. A week is <b>current</b> (still earning), "
            "<b>owed</b> (finished, unpaid), <b>paid</b>, or <b>empty</b> (finished, nothing earned).", SMALL))

A(Paragraph("The Sunday statement and paying him", H3))
A(Paragraph("Every Sunday at about 21:45 an <b>issue</b> opens on the Argo repository titled with the week and its "
            "money; GitHub emails it to you. It lists every activity with its points, anything to look at "
            "(implausible speed, no heart rate, an unscored sport), the steps, the eggs found, and the running total owed.", P))
A(Paragraph("<b>Pay Thomas, then reply to that email (or comment on the issue) with one line:</b>", P))
A(table([
    ["reply", "what happens"],
    ["paid", "that week is marked paid today; the issue closes; his page moves it from owed to paid"],
    ["paid all", "every unpaid week up to and including that one is marked paid (for a backlog)"],
    ["paid cash", "the same as paid, with the word kept as a note"],
    ["strike 12345678 the car", "that activity earns nothing, with the reason shown on his page (ids are in the statement's table)"],
    ["unstrike 12345678", "puts it back"],
    ["sport 12345678 kayak", "the watch said \"other\"; this is what it was (run, walk, cycle, swim, kayak)"],
    ["set steps_pts_per_10k 3", "changes a setting (the list is under Changing the rules)"],
    ["reset week_cap_points", "puts a setting back to its default; reset all for every one"],
], [48 * mm, 122 * mm]))
A(Paragraph("The bot answers on the issue within a minute with the new figures. Only your replies are listened to. "
            "To get a statement without waiting for Sunday: Actions → <i>statement</i> → <i>Run workflow</i>, with a "
            "week's Monday (blank = the last completed week).", SMALL))
A(Paragraph("The <i>pay</i> workflow (Actions → <i>pay</i> → <i>Run workflow</i>) does the same things from a form, if "
            "you prefer that to replying.", SMALL))

A(Paragraph("The Easter eggs", H3))
A(Paragraph("118 hidden milestones, each with its own message — first mile, two-mile run, ten-mile ride, Ben Nevis's "
            "height climbed, £100 (\"the Golden Fleece\"), a ten-week streak, a 20,000-step day, a million steps… "
            "The Trophies panel does not exist on his page until the first one is won; then each new one gets a "
            "full-screen fanfare when he next opens the page, and a cabinet lists the ones he has. Only won eggs leave "
            "the server, so nothing on the page spoils the rest. The list is <font face='Courier'>C:\\Argo\\argo\\milestones.py</font>.", P))

# ------------------------------------------------------------------ Argo settings
A(PageBreak())
A(Paragraph("Argo — changing the rules (the admin panel)", H2))
A(Paragraph("Every number is a <b>setting</b> with a default in the code and an override kept in "
            "<font face='Courier'>data/settings.json</font>. Three ways to change one — the same table behind all three:", P))
A(Paragraph("1. The form, from a phone or PC", H3))
A(Paragraph("GitHub → the argo repository → <b>Actions</b> → <b>settings</b> → <b>Run workflow</b>. Fill in only what you "
            "want to change; blank fields stay as they are. <i>other</i> takes anything not in the named fields as "
            "key=value pairs (e.g. <font face='Courier'>eggs_start=2026-10-01 run_ascent_per_100m=4</font>); "
            "<i>reset</i> takes one setting's name, or <font face='Courier'>all</font>. A bad value is refused with the "
            "reason and nothing is changed. Every change is a commit.", P))
A(Paragraph("2. A reply on any statement issue", H3))
A(code("""
set steps_pts_per_10k 3
reset week_cap_points
"""))
A(Paragraph("3. On the PC", H3))
A(code("""
cd C:\\Argo
python -m argo.settings                                  # every setting: current, default, overridden?
python -m argo.settings --set pence_per_point 30 --apply
python -m argo.settings --set week_cap_points 40 --set eggs_start 2026-10-01 --apply
python -m argo.settings --reset all --apply
"""))
A(Paragraph("The settings", H3))
A(table([
    ["setting", "default", "what it is"],
    ["pence_per_point", "25", "pence paid per point"],
    ["week_cap_points", "none", "most points paid in a week; none = no cap"],
    ["scheme_start", "2026-05-01", "the day the ledger opens"],
    ["eggs_start", "2026-09-21", "the day the Easter eggs start counting"],
    ["steps_start", "2026-09-21", "the day steps start counting"],
    ["steps_pts_per_10k", "2", "points per 10,000 steps"],
    ["steps_per_mile_deducted", "0", "steps not paid per recorded mile on foot (0 = gross)"],
    ["run_per_mile / walk_per_mile", "4 / 2", "points per mile"],
    ["cycle_per_mile / kayak_per_mile", "1 / 4", "points per mile"],
    ["swim_per_100m", "1", "points per 100 m swum"],
    ["run_ascent_per_100m", "4", "points per 100 m climbed running"],
    ["walk_ascent_per_100m", "2", "points per 100 m climbed walking"],
    ["cycle_ascent_per_100m", "1", "points per 100 m climbed cycling"],
    ["min_distance_m", "100", "an activity shorter than this earns nothing"],
], [52 * mm, 26 * mm, 92 * mm]))
A(Paragraph("A change re-scores every week, past ones included — lowering a rate lowers what is still owed. A week "
            "already marked paid keeps its paid figure. Changes made on the PC reach the page after "
            "<font face='Courier'>git push</font>; changes made through the form or a reply are live at the next hourly sync.", SMALL))

# ------------------------------------------------------------------ Argo PC
A(Paragraph("Argo — on the PC", H2))
A(code("""
cd C:\\Argo
python check.py                       # every selftest + pyflakes (run after any edit)
python -m argo.sync --dry-run         # what Garmin has that we do not, without fetching
python -m argo.sync                   # fetch it (the Action does this hourly anyway)
python -m argo.score --print          # the ledger as a table; rebuilds docs/data.json
python -m argo.statement --print      # the last completed week's statement, printed
python -m argo.pay                    # dry run: the oldest unpaid week   (--apply to mark it)
python -m argo.pay --through 2026-09-14 --apply      # settle every unpaid week up to that Monday
python -m argo.pay --strike 12345678 --reason "the car" --apply
python -m argo.pay --sport 12345678 kayak --apply
python -m argo.demo                   # a made-up data.json to look at the page design
git add data docs && git commit -m "why" && git push   # PC changes reach the page this way
"""))
A(Paragraph("Scripts that write are dry-run by default and take <font face='Courier'>--apply</font>. The design log "
            "(why everything is the way it is) is <font face='Courier'>C:\\Argo\\ARGO_BRIEF.md</font>; the README has the same "
            "instructions as this page.", SMALL))

# ------------------------------------------------------------------ Atlas
A(PageBreak())
A(Paragraph("Atlas — Joe's stats", H2))
A(Paragraph("No money, no rewards. Every hour the Action fetches Joe's activities <i>and their timelines</i> (the TCX "
            "file of every activity), recomputes everything and publishes the page. Six tabs:", P))
A(table([
    ["tab", "what is on it"],
    ["Overview", "all-time distance / time / climb / streak; this week against last; the last 12 weeks by sport; totals per sport; the latest activities"],
    ["Records", "per sport, the fastest 400 m · 800 m · 1 km · 1 mile · 2 km · 3 km · 2 miles · 5 km · 5 miles · 10 km · 15 km · 10 miles · 20 km · half · 30 km · marathon (runs); "
                "1 km → 100 miles in fifteen steps (rides); walk, swim and kayak ladders; longest, most climb, longest time, fastest average; biggest week and month. "
                "A record is the fastest stretch INSIDE an activity — the quickest 5 km within a 12 km run. Tap one for its progression chart."],
    ["Rank", "every activity by the Atlas score (distance by sport plus climb — a ranking axis, nothing more), overall or within a sport"],
    ["Progress", "weekly and monthly distance stacked by sport; monthly climb; running pace and heart rate over time (fitness is heart rate coming down at the same pace); "
                 "the same for cycling speed; cumulative distance this year; consistency"],
    ["Log", "every activity in a table — tap a heading to sort, a chip to filter by sport, a row for the detail"],
    ["Map", "every track at once, coloured by sport; tap a line for the activity"],
], [24 * mm, 146 * mm]))
A(Paragraph("Tapping any activity opens its sheet: the numbers, its map, its best efforts with <b>PB</b> where it holds the record.", SMALL))

A(Paragraph("Corrections", H3))
A(Paragraph("The watch is occasionally wrong. Two corrections, both applied before anything is computed:", P))
A(code("""
cd C:\\Atlas
python -m atlas.fix --strike 12345678 --reason "watch left running" --apply
python -m atlas.fix --unstrike 12345678 --apply
python -m atlas.fix --sport 12345678 kayak --apply        # the watch said "other"
git add data && git commit -m "why" && git push
"""))
A(Paragraph("Ids are in the Log tab's detail sheet (the address of the activity on Garmin Connect ends in the same number).", SMALL))

A(Paragraph("Atlas — on the PC", H3))
A(code("""
cd C:\\Atlas
python check.py                       # every selftest + pyflakes
python -m atlas.sync --dry-run        # what Garmin has that we do not
python -m atlas.stats --print         # headline numbers, records, top 10; rebuilds docs/data.json
python -m atlas.demo                  # a made-up data.json to look at the page design
"""))
A(Paragraph("The scoring rates behind the rankings are in <font face='Courier'>C:\\Atlas\\atlas\\scoring.py</font>; the record "
            "ladders in <font face='Courier'>records.py</font>. The design log is <font face='Courier'>ATLAS_BRIEF.md</font>.", SMALL))

# ------------------------------------------------------------------ how it runs
A(Paragraph("How it all runs, and what to do when it doesn't", H2))
A(table([
    ["when", "what", "where to look"],
    ["seven minutes past every hour", "sync: Garmin → data → page (both apps). Commits only when something new landed.", "Actions → sync"],
    ["Sunday ~21:45", "Argo's statement issue opens (it syncs first, so a Sunday-afternoon ride is on it)", "Actions → statement; Issues"],
    ["when you reply", "Argo's paid workflow reads the first line of your comment and acts on it", "Actions → paid"],
    ["when you run it", "settings (Argo), pay (Argo)", "Actions → the workflow → Run workflow"],
], [40 * mm, 84 * mm, 46 * mm]))
A(Paragraph("The page not updating", H3))
A(Paragraph("Open Actions and look at the latest <i>sync</i>. Green: the page updates within a minute or two (GitHub's "
            "cache holds a file for up to ten minutes; a pull-to-refresh on the phone gets the new one). Red with "
            "\"authentication\" or \"login\" in the log: the Garmin tokens have expired — run "
            "<font face='Courier'>python -m argo.login</font> (or <font face='Courier'>atlas.login</font>) again. "
            "Red for another reason: the log names the line; send it to me.", P))
A(Paragraph("A sport the watch names oddly", H3))
A(Paragraph("It shows as <i>other</i>, earns nothing (Argo) and is flagged on the statement. Relabel it with "
            "<font face='Courier'>sport &lt;id&gt; kayak</font>; if the watch keeps using that name, tell me and it is a "
            "one-word change so it maps automatically from then on.", P))
A(Paragraph("Two things to keep in mind", H3))
A(Paragraph("Both pages are public at guessable addresses, with the boys' first names and their routes on them. "
            "And the hourly cadence is GitHub's schedule, which is best-effort — a run can be a few minutes late.", P))

doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                        title="Argo & Atlas — the guide", author="Argo")
doc.build(story)
print(f"written {OUT} ({OUT.stat().st_size // 1024} KB)")
