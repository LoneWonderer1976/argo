"""pay.py -- mark a week PAID (or strike an activity). The only two writes a person makes.

    python -m argo.pay                       # dry run: shows the oldest unpaid week and what it would mark
    python -m argo.pay --apply               # mark it paid, today
    python -m argo.pay --week 2026-09-21 --note "cash" --apply
    python -m argo.pay --through 2026-09-21 --apply    # every unpaid week up to and including that one
    python -m argo.pay --undo --week 2026-09-21 --apply
    python -m argo.pay --strike 12345678 --reason "that was the car" --apply
    python -m argo.pay --unstrike 12345678 --apply
    python -m argo.pay --sport 12345678 kayak --apply    # the watch said "other"; Ben says what it was

Dry-run by default; --apply writes. The Pay workflow in GitHub Actions runs exactly these with
--apply, from the inputs on its "Run workflow" form, then re-scores and commits -- so the ledger
lives in git and every payment is a commit with a date on it.

A week can only be marked paid once it is COMPLETE (its Sunday has passed): the current week is
still earning.
"""
import argparse
import datetime as dt

from . import rates, score, store
from .weeks import this_week, week_label


def oldest_unpaid(data: dict) -> str | None:
    owed = [w for w in data["weeks"] if w["status"] == "owed"]
    return owed[-1]["monday"] if owed else None


def mark_paid(monday: str, note: str | None, apply: bool) -> None:
    day = dt.date.fromisoformat(monday)
    if day.weekday() != 0:
        raise SystemExit(f"{monday} is not a Monday")
    if day >= this_week():
        raise SystemExit(f"the week of {week_label(day)} is not over yet")
    ledger = store.ledger()
    if monday in ledger["weeks"]:
        print(f"{week_label(day)} is already marked paid ({ledger['weeks'][monday].get('paid_on')})")
        return
    data = score.build()
    week = next((w for w in data["weeks"] if w["monday"] == monday), None)
    if week is None:
        raise SystemExit(f"no week {monday} in the ledger")
    print(f"{'MARK' if apply else 'would mark'} {week_label(day)} paid: {week['points']:.1f} pts = {rates.gbp(week['pence'])}"
          + (f"  ({week['n_flagged']} flagged activity still counted)" if week["n_flagged"] else ""))
    if apply:
        ledger["weeks"][monday] = {"paid_on": dt.date.today().isoformat(), "pence": week["pence"],
                                   **({"note": note} if note else {})}
        store.write_ledger(ledger)


def mark_through(monday: str, note: str | None, apply: bool) -> None:
    """Every owed week up to and including `monday` -- for settling a backlog in one go."""
    data = score.build()
    owed = [w["monday"] for w in data["weeks"] if w["status"] == "owed" and w["monday"] <= monday]
    if not owed:
        print(f"nothing owed up to {monday}")
        return
    for m in sorted(owed):
        mark_paid(m, note, apply)


def unmark(monday: str, apply: bool) -> None:
    ledger = store.ledger()
    if monday not in ledger["weeks"]:
        raise SystemExit(f"{monday} is not marked paid")
    print(f"{'UNMARK' if apply else 'would unmark'} {monday} (was paid {ledger['weeks'][monday].get('paid_on')})")
    if apply:
        del ledger["weeks"][monday]
        store.write_ledger(ledger)


def strike(activity_id: str, reason: str | None, apply: bool) -> None:
    ov = store.overrides()
    if not (store.ACTS / f"{activity_id}.json").exists():
        raise SystemExit(f"no activity {activity_id} in data/activities")
    print(f"{'STRIKE' if apply else 'would strike'} {activity_id}: {reason or '(no reason)'}")
    if apply:
        ov["exclude"][str(activity_id)] = reason or "struck"
        store.write_overrides(ov)


def relabel(activity_id: str, sport: str, apply: bool) -> None:
    if sport not in rates.SPORTS:
        raise SystemExit(f"'{sport}' is not one of {', '.join(rates.SPORTS)}")
    if not (store.ACTS / f"{activity_id}.json").exists():
        raise SystemExit(f"no activity {activity_id} in data/activities")
    ov = store.overrides()
    print(f"{'RELABEL' if apply else 'would relabel'} {activity_id} as {sport}")
    if apply:
        ov["sport"][str(activity_id)] = sport
        store.write_overrides(ov)


def unstrike(activity_id: str, apply: bool) -> None:
    ov = store.overrides()
    if str(activity_id) not in ov["exclude"]:
        raise SystemExit(f"{activity_id} is not struck")
    print(f"{'UNSTRIKE' if apply else 'would unstrike'} {activity_id} (was: {ov['exclude'][str(activity_id)]})")
    if apply:
        del ov["exclude"][str(activity_id)]
        store.write_overrides(ov)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--week", help="the week's Monday (default: the oldest unpaid week)")
    ap.add_argument("--through", help="mark every unpaid week up to and including this Monday")
    ap.add_argument("--note")
    ap.add_argument("--undo", action="store_true", help="un-mark the week")
    ap.add_argument("--strike", metavar="ID", help="exclude an activity from scoring")
    ap.add_argument("--reason")
    ap.add_argument("--unstrike", metavar="ID")
    ap.add_argument("--sport", nargs=2, metavar=("ID", "SPORT"), help="relabel an activity's sport")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if a.sport:
        relabel(a.sport[0], a.sport[1], a.apply)
    elif a.strike:
        strike(a.strike, a.reason, a.apply)
    elif a.unstrike:
        unstrike(a.unstrike, a.apply)
    elif a.through:
        mark_through(a.through, a.note, a.apply)
    elif a.undo:
        if not a.week:
            raise SystemExit("--undo needs --week")
        unmark(a.week, a.apply)
    else:
        monday = a.week or oldest_unpaid(score.build())
        if not monday:
            print("nothing owed")
            return
        mark_paid(monday, a.note, a.apply)
    if not a.apply:
        print("(dry run -- add --apply)")


if __name__ == "__main__":
    main()
