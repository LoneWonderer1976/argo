"""statement.py -- the weekly email to Ben: what was earned, what looks odd, what is owed.

    python -m argo.statement            # last completed week, sent to MAIL_TO
    python -m argo.statement --print    # the same, printed, nothing sent
    python -m argo.statement --week 2026-09-21
    python -m argo.statement --issue-file body.md   # the GitHub-issue form: body to the file, title to stdout

Sent on Sunday night by the Action for the week just finished. THE DEFAULT ROUTE IS A GITHUB
ISSUE, not SMTP: the Action opens an issue titled with the week and its money, GitHub emails the
repository's owner about it as it does any issue, and a reply of "paid" -- from the email or on
the issue -- is what marks the week paid (paid.yml). No mail account, no app password, nothing
for Ben to set up. SMTP is kept as an extra for when a proper email is wanted too. Every activity of the week is
listed with its points; a flagged one is marked so Ben can strike it (data/overrides.json)
before he pays; the footer carries the running owed figure and the two links -- the page, and
the Pay workflow that marks the week settled.

Mail goes out over SMTP with STARTTLS. The account is Ben's, as five secrets: SMTP_HOST
(default smtp.gmail.com), SMTP_PORT (587), SMTP_USER, SMTP_PASS (a Gmail App Password, not the
account password), MAIL_TO. MAIL_FROM defaults to SMTP_USER. PAGE_URL and PAY_URL are repository
variables so the links are right without editing code.
"""
import argparse
import datetime as dt
import html
import os
import smtplib
import sys
from email.message import EmailMessage

from . import rates, score
from .weeks import last_week


def _fmt_km(m) -> str:
    return f"{(m or 0) / 1000:.1f} km"


def _fmt_dur(s) -> str:
    s = int(s or 0)
    return f"{s // 3600}h {s % 3600 // 60:02d}m" if s >= 3600 else f"{s // 60} min"


def compose(data: dict, monday: dt.date) -> tuple[str, str, str]:
    """(subject, plain text, html) for one week."""
    week = next((w for w in data["weeks"] if w["monday"] == monday.isoformat()), None)
    if week is None:
        raise SystemExit(f"no week {monday} in the ledger (scheme starts {data['scheme']['start']})")
    acts = [a for a in data["activities"] if a["week"] == monday.isoformat()]
    acts.sort(key=lambda a: a["start_local"])
    page = os.environ.get("PAGE_URL", "")
    pay = os.environ.get("PAY_URL", "")
    owed = data["totals"]["owed_pence"]
    subject = f"Argo: {week['label']} — {rates.gbp(week['pence'])}" + \
              (f" ({week['n_flagged']} to check)" if week["n_flagged"] else "")

    lines = [f"ARGO — week of {week['label']}", ""]
    for a in acts:
        mark = "  STRUCK" if a["excluded"] else ("  ** CHECK: " + "; ".join(a["flags"]) if a["flags"] else "")
        lines.append(f"{a['start_local'][5:16]}  {a['sport']:5}  {_fmt_km(a['distance_m']):>8}  "
                     f"{(a['ascent_m'] or 0):4.0f} m  {_fmt_dur(a['duration_s']):>7}  {a['points']:5.1f} pts  "
                     f"{a['name']}{mark}")
    if not acts:
        lines.append("(no activities)")
    lines += ["", f"Points {week['points']:.1f}" + (f" (paid for {week['points_paid_for']:.1f}, capped)" if week["capped"] else "")
              + f"  ->  {rates.gbp(week['pence'])} at {rates.PENCE_PER_POINT}p a point",
              f"Owed in total (unpaid weeks): {rates.gbp(owed)}", ""]
    if pay:
        lines.append(f"Mark this week paid: {pay}")
    if page:
        lines.append(f"His page: {page}")
    text = "\n".join(lines) + "\n"

    rows = []
    for a in acts:
        cls = ' style="background:#fff3cd"' if (a["flags"] and not a["excluded"]) else ""
        note = ("<br><small>struck: " + html.escape(a["excluded"]) + "</small>") if a["excluded"] else \
               ("<br><small>⚠ " + html.escape("; ".join(a["flags"])) + "</small>" if a["flags"] else "")
        rows.append(f"<tr{cls}><td>{a['start_local'][5:16]}</td><td>{a['sport']}</td>"
                    f"<td align=right>{_fmt_km(a['distance_m'])}</td><td align=right>{(a['ascent_m'] or 0):.0f} m</td>"
                    f"<td align=right>{_fmt_dur(a['duration_s'])}</td><td align=right><b>{a['points']:.1f}</b></td>"
                    f"<td>{html.escape(a['name'])}{note}</td></tr>")
    body = f"""<div style="font-family:system-ui,sans-serif;max-width:720px">
<h2 style="margin:0 0 4px">Argo — {html.escape(week['label'])}</h2>
<p style="margin:0 0 12px;color:#555">{len(acts)} activities · {week['points']:.1f} points · <b style="font-size:1.2em">{rates.gbp(week['pence'])}</b>
{' (capped from ' + format(week['points'], '.1f') + ' pts)' if week['capped'] else ''}</p>
<table cellpadding=6 style="border-collapse:collapse;font-size:14px">
<tr style="border-bottom:1px solid #ccc"><th align=left>when</th><th align=left>sport</th><th>dist</th><th>climb</th><th>time</th><th>pts</th><th align=left>name</th></tr>
{''.join(rows) or '<tr><td colspan=7><i>no activities</i></td></tr>'}
</table>
<p style="margin-top:16px"><b>Owed in total: {rates.gbp(owed)}</b> (every unpaid week)</p>
<p>{f'<a href="{html.escape(pay)}">Mark this week paid</a> &nbsp;·&nbsp; ' if pay else ''}{f'<a href="{html.escape(page)}">his page</a>' if page else ''}</p>
<p style="color:#888;font-size:12px">A highlighted row is one to look at before paying — strike it in data/overrides.json and the ledger re-scores.</p>
</div>"""
    return subject, text, body


def compose_markdown(data: dict, monday: dt.date) -> tuple[str, str]:
    """(title, markdown body) for the GitHub issue. The body carries a hidden week marker that
    paid.yml reads back, so a 'paid' reply knows which week it is about."""
    week = next((w for w in data["weeks"] if w["monday"] == monday.isoformat()), None)
    if week is None:
        raise SystemExit(f"no week {monday} in the ledger (scheme starts {data['scheme']['start']})")
    acts = sorted((a for a in data["activities"] if a["week"] == monday.isoformat()), key=lambda a: a["start_local"])
    page = os.environ.get("PAGE_URL", "")
    owed = data["totals"]["owed_pence"]
    title = f"Argo statement: {week['label']} — {rates.gbp(week['pence'])}" + \
            (f" ({week['n_flagged']} to check)" if week["n_flagged"] else "")
    lines = [f"<!-- argo-week: {monday.isoformat()} -->",
             f"**{len(acts)} activities · {week['points']:.1f} points · {rates.gbp(week['pence'])}**"
             + (f" (capped from {week['points']:.1f} pts)" if week["capped"] else ""), ""]
    if acts:
        lines += ["| when | sport | dist | climb | time | pts | name | id |", "|---|---|---:|---:|---:|---:|---|---|"]
        for a in acts:
            note = f" — **struck:** {a['excluded']}" if a["excluded"] else \
                   (f" — ⚠ {'; '.join(a['flags'])}" if a["flags"] else "")
            lines.append(f"| {a['start_local'][5:16]} | {a['sport']} | {_fmt_km(a['distance_m'])} | {(a['ascent_m'] or 0):.0f} m "
                         f"| {_fmt_dur(a['duration_s'])} | {a['points']:.1f} | {a['name']}{note} | `{a['id']}` |")
    else:
        lines.append("_no activities_")
    if week.get("milestones"):
        lines += ["", "🏆 **Easter eggs found this week:** " + ", ".join(m["title"] for m in week["milestones"])]
    lines += ["", f"**Owed in total: {rates.gbp(owed)}** (every unpaid week)", "",
              "Reply **paid** to mark this week paid. Reply **strike `<id>` reason** to remove an activity from "
              "scoring first, or **sport `<id>` kayak** to relabel one the watch called *other*, then **paid**." + (f" [His page]({page})." if page else "")]
    return title, "\n".join(lines) + "\n"


def send(subject: str, text: str, body: str, to: str | None = None) -> None:
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    pw = os.environ.get("SMTP_PASS")
    to = to or os.environ.get("MAIL_TO")
    if not (user and pw and to):
        sys.exit("SMTP_USER, SMTP_PASS and MAIL_TO must be set to send (use --print to see it instead)")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("MAIL_FROM", user)
    msg["To"] = to
    msg.set_content(text)
    msg.add_alternative(body, subtype="html")
    with smtplib.SMTP(host, port, timeout=60) as s:
        s.starttls()
        s.login(user, pw)
        s.send_message(msg)
    print(f"sent '{subject}' to {to}")


def selftest() -> None:
    d = score.build([{"id": 1, "name": "Run <b>", "sport": "run", "type_key": "running",
                      "start_local": "2026-09-22 16:00:00", "distance_m": 1609.344, "ascent_m": 25.0,
                      "duration_s": 600, "avg_hr": None, "avg_speed_mps": 2.7}],
                    {"weeks": {}}, {"exclude": {}})
    os.environ["PAY_URL"] = "https://example.test/pay"
    subj, text, body = compose(d, dt.date(2026, 9, 21))
    assert subj == "Argo: 21–27 Sep 2026 — £1.25 (1 to check)", subj
    assert "5.0 pts" in text and "CHECK: no heart rate" in text and "https://example.test/pay" in text
    assert "Run &lt;b&gt;" in body and "fff3cd" in body and "Owed in total:" in body
    title, md = compose_markdown(d, dt.date(2026, 9, 21))
    assert title.startswith("Argo statement: 21–27 Sep 2026") and "<!-- argo-week: 2026-09-21 -->" in md
    assert "| `1` |" in md and "⚠ no heart rate" in md and "Easter eggs found this week:" in md and "Reply **paid**" in md
    print("statement: selftest OK")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--week", help="the week's Monday (default: the last completed week)")
    ap.add_argument("--print", action="store_true", help="print instead of sending")
    ap.add_argument("--to", help="override MAIL_TO")
    ap.add_argument("--issue-file", metavar="PATH", help="write the GitHub-issue body here and print its title")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    monday = dt.date.fromisoformat(a.week) if a.week else last_week()
    data = score.build()
    if a.issue_file:
        title, md = compose_markdown(data, monday)
        open(a.issue_file, "w", encoding="utf-8").write(md)
        print(title)
        return
    subject, text, body = compose(data, monday)
    if a.print:
        print(subject, "\n")
        print(text)
        return
    send(subject, text, body, a.to)


if __name__ == "__main__":
    main()
