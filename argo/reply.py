"""reply.py -- Ben's reply on a statement issue, turned into the ledger write it asks for.

    python -m argo.reply --issue-body issue.md --comment comment.md [--apply]

The statement issue carries `<!-- argo-week: 2026-09-21 -->`; a comment on it (a reply to the
notification email lands here too) is read for its FIRST non-empty line:

    paid                      mark that week paid
    paid all                  mark every unpaid week up to and including it
    paid cash / paid bank     the same, with the word kept as the note
    strike 12345678 the car   strike that activity (it earns nothing; the reason shows on his page)
    unstrike 12345678         put it back
    sport 12345678 kayak      the watch said "other"; this is what it was

Anything else is ignored with a polite note. The result goes to stdout for the workflow to post
back as a comment; "CLOSE" on the last line tells it to close the issue.
"""
import argparse
import re

from . import pay, rates, score

WEEK_RE = re.compile(r"<!--\s*argo-week:\s*(\d{4}-\d{2}-\d{2})\s*-->")


def first_line(text: str) -> str:
    for line in (text or "").splitlines():
        line = line.strip()
        if line and not line.startswith(">"):
            return line
    return ""


def parse(comment: str) -> tuple[str, list[str]]:
    words = first_line(comment).split()
    if not words:
        return "", []
    return words[0].lower().strip(".,!"), words[1:]


def handle(issue_body: str, comment: str, apply: bool) -> str:
    try:
        return _handle(issue_body, comment, apply)
    except SystemExit as e:          # pay.py refuses with a sentence; post the sentence, don't fail the run
        return f"Not done: {e}"


def _handle(issue_body: str, comment: str, apply: bool) -> str:
    m = WEEK_RE.search(issue_body or "")
    if not m:
        return "This issue has no week marker, so I can't tell which week you mean."
    week = m.group(1)
    verb, rest = parse(comment)
    if verb == "paid":
        note = " ".join(w for w in rest if w.lower() != "all") or None
        if any(w.lower() == "all" for w in rest):
            pay.mark_through(week, note, apply)
        else:
            pay.mark_paid(week, note, apply)
        data = score.build()
        w = next(x for x in data["weeks"] if x["monday"] == week)
        return (f"Marked {w['label']} paid ({rates.gbp(w['pence'])}). Owed in total now: "
                f"{rates.gbp(data['totals']['owed_pence'])}.\nCLOSE")
    if verb == "strike" and rest:
        pay.strike(rest[0], " ".join(rest[1:]) or "struck by Dad", apply)
        data = score.build()
        w = next(x for x in data["weeks"] if x["monday"] == week)
        return f"Struck {rest[0]}. {w['label']} is now {w['points']:.1f} pts = {rates.gbp(w['pence'])}. Reply **paid** when ready."
    if verb == "sport" and len(rest) >= 2:
        pay.relabel(rest[0], rest[1].lower(), apply)
        data = score.build()
        w = next(x for x in data["weeks"] if x["monday"] == week)
        return f"{rest[0]} is now a {rest[1].lower()}. {w['label']} is now {w['points']:.1f} pts = {rates.gbp(w['pence'])}. Reply **paid** when ready."
    if verb == "unstrike" and rest:
        pay.unstrike(rest[0], apply)
        return f"Un-struck {rest[0]}; it scores again. Reply **paid** when ready."
    return ("I read replies that start with **paid**, **paid all**, **strike `<id>` reason**, **unstrike `<id>`** "
            "or **sport `<id>` run|walk|cycle|swim|kayak** -- nothing done.")


def selftest() -> None:
    assert first_line("\n\n  paid  \n> On Sun, Ben wrote:\n> stuff") == "paid"
    assert first_line("> quoted only") == ""
    assert parse("Paid.\nthanks") == ("paid", [])
    assert parse("paid all") == ("paid", ["all"])
    assert parse("strike 123 that was the car") == ("strike", ["123", "that", "was", "the", "car"])
    assert WEEK_RE.search("x\n<!-- argo-week: 2026-09-21 -->\ny").group(1) == "2026-09-21"
    assert "no week marker" in handle("no marker", "paid", False)
    assert "nothing done" in handle("<!-- argo-week: 2026-09-21 -->", "thanks!", False)
    assert handle("<!-- argo-week: 2099-01-05 -->", "paid", False).startswith("Not done: the week of")
    print("reply: selftest OK")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--issue-body")
    ap.add_argument("--comment")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    issue = open(a.issue_body, encoding="utf-8").read()
    comment = open(a.comment, encoding="utf-8").read()
    print(handle(issue, comment, a.apply))


if __name__ == "__main__":
    main()
