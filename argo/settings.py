"""settings.py -- Ben's dials. Every number in rates.py can be overridden without touching code.

    python -m argo.settings                       # every setting: current value, default, whether overridden
    python -m argo.settings --set steps_pts_per_10k 2 --apply
    python -m argo.settings --set week_cap_points 40 --set eggs_start 2026-10-01 --apply
    python -m argo.settings --reset week_cap_points --apply
    python -m argo.settings --reset all --apply
    python -m argo.settings --changes "pence_per_point=30 walk_per_mile=2.5" --apply   # the workflow's form

Overrides live in data/settings.json ({key: value}); rates.py reads it as it imports, so every
module that imports a constant from rates sees the override. The defaults in rates.py stay the
record of what Ben decided first; the file is what he changed since, and git says when.

The same table drives three doors: this command, the `settings` workflow's form on GitHub
(Actions -> settings -> Run workflow, from a phone), and `set <key> <value>` as a reply on a
statement issue. A bad value is refused with the reason, never half-applied.
"""
import argparse
import datetime as dt

from . import rates, store

SETTINGS = rates.SETTINGS       # the table lives beside the numbers it names


def parse(key: str, raw) -> object:
    """A setting's value from text (or JSON), validated. Raises ValueError with the reason."""
    if key not in SETTINGS:
        raise ValueError(f"no such setting '{key}'; the settings are {', '.join(SETTINGS)}")
    _, kind, _ = SETTINGS[key]
    text = str(raw).strip().lower()
    if kind == "int?":
        if text in ("none", "off", "", "0"):
            return None
        kind = int
    if kind == "date":
        try:
            return dt.date.fromisoformat(text).isoformat()
        except ValueError:
            raise ValueError(f"{key} needs a date like 2026-10-01, not '{raw}'")
    if kind == "per100":
        v = float(text)
        if v < 0:
            raise ValueError(f"{key} cannot be negative")
        return v / 100.0
    try:
        v = kind(float(text)) if kind is int else kind(text)
    except ValueError:
        raise ValueError(f"{key} needs a number, not '{raw}'")
    if v < 0:
        raise ValueError(f"{key} cannot be negative")
    if key == "pence_per_point" and v == 0:
        raise ValueError("pence_per_point of 0 would pay nothing for anything")
    return v


def display(key: str, value) -> str:
    _, kind, _ = SETTINGS[key]
    if value is None:
        return "none"
    if kind == "per100":
        return f"{value * 100:g}"
    if isinstance(value, dt.date):
        return value.isoformat()
    return f"{value:g}" if isinstance(value, float) else str(value)


current = rates.current
apply_overrides = rates.apply_overrides


def changes_from_text(text: str) -> dict:
    """'steps_pts_per_10k=2 week_cap_points=none' -> {key: raw}."""
    out = {}
    for part in (text or "").replace(",", " ").split():
        if "=" not in part:
            raise ValueError(f"'{part}' is not key=value")
        k, v = part.split("=", 1)
        out[k.strip().lower()] = v.strip()
    return out


def report() -> str:
    ov = store.settings()
    lines = [f"{'setting':26} {'current':>12}  {'default':>12}  note"]
    for key, (attr, kind, note) in SETTINGS.items():
        cur = display(key, current(key))
        default = display(key, rates.DEFAULTS[key])
        mark = "*" if key in ov else " "
        lines.append(f"{key:26} {cur:>12}{mark} {default:>12}  {note}")
    lines.append("* = overridden in data/settings.json" if ov else "(no overrides; every value is its default)")
    return "\n".join(lines)


def set_many(changes: dict, apply: bool) -> list[str]:
    """Validate every change first, then write them all or none. Returns the lines to print."""
    parsed = {k: parse(k, v) for k, v in changes.items()}         # raises on the first bad one
    ov = store.settings()
    out = []
    for k, v in parsed.items():
        before = display(k, current(k))
        after = display(k, v if not (SETTINGS[k][1] == "date") else dt.date.fromisoformat(v))
        out.append(f"{'SET' if apply else 'would set'} {k}: {before} -> {after}")
        ov[k] = v
    if apply:
        store.write_settings(ov)
        apply_overrides(ov)
    return out


def reset(key: str, apply: bool) -> list[str]:
    ov = store.settings()
    keys = list(ov) if key == "all" else [key]
    out = []
    for k in keys:
        if k not in ov:
            out.append(f"{k} is not overridden")
            continue
        out.append(f"{'RESET' if apply else 'would reset'} {k}: {display(k, current(k))} -> {display(k, rates.DEFAULTS[k])} (default)")
        del ov[k]
    if apply:
        store.write_settings(ov)
        for k in keys:
            apply_overrides({k: rates.DEFAULTS[k]})
    return out


def selftest() -> None:
    assert parse("pence_per_point", "30") == 30 and parse("week_cap_points", "none") is None
    assert parse("week_cap_points", "40") == 40 and parse("eggs_start", "2026-10-01") == "2026-10-01"
    assert parse("run_ascent_per_100m", "4") == 0.04 and parse("steps_pts_per_10k", "2.5") == 2.5
    for bad in (("pence_per_point", "x"), ("eggs_start", "tomorrow"), ("nope", "1"), ("pence_per_point", "0"), ("walk_per_mile", "-1")):
        try:
            parse(*bad)
            raise AssertionError(f"accepted {bad}")
        except ValueError:
            pass
    assert changes_from_text("a=1, b=none  c=2026-01-01") == {"a": "1", "b": "none", "c": "2026-01-01"}
    saved = dict(rates.DISTANCE_PER_MILE), rates.PENCE_PER_POINT
    try:
        assert apply_overrides({"walk_per_mile": 3.0, "pence_per_point": 30, "bogus": 1}) == ["bogus"]
        assert rates.DISTANCE_PER_MILE["walk"] == 3.0 and rates.PENCE_PER_POINT == 30 and rates.pence(1.0) == 30
        assert rates.points_for("walk", 1609.344, 0)["distance"] == 3.0
    finally:
        rates.DISTANCE_PER_MILE.update(saved[0])
        rates.PENCE_PER_POINT = saved[1]
    assert current("pence_per_point") == rates.PENCE_PER_POINT and display("walk_ascent_per_100m", 0.02) == "2"
    assert "setting" in report()
    print("settings: selftest OK")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", nargs=2, action="append", metavar=("KEY", "VALUE"), default=[])
    ap.add_argument("--changes", help="'key=value key=value' in one string")
    ap.add_argument("--reset", metavar="KEY", help="a key, or 'all'")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    changes = dict(a.set)
    if a.changes:
        changes.update(changes_from_text(a.changes))
    if not changes and not a.reset:
        print(report())
        return
    try:
        lines = []
        if a.reset:
            lines += reset(a.reset, a.apply)
        if changes:
            lines += set_many(changes, a.apply)
    except ValueError as e:
        raise SystemExit(f"refused: {e}")
    print("\n".join(lines))
    if not a.apply:
        print("(dry run -- add --apply)")


if __name__ == "__main__":
    main()
