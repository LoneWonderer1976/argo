"""store.py -- the data folder IS the database.

    data/activities/<id>.json   one per Garmin activity: Argo's fields + the raw summary, kept whole
    data/tracks/<id>.json       the activity's line, thinned for a phone map (lat/lon pairs)
    data/steps.json             daily step counts {"2026-09-21": {"steps": 11234, ...}} -- the ONE file the
                                sync rewrites, because a day's count grows until midnight (the last few
                                days are re-fetched every run)
    data/ledger.json            the weeks Ben has marked PAID  {"weeks": {"2026-09-21": {"paid_on": ..}}}
    data/overrides.json         Ben's strikes and relabels  {"exclude": {"<id>": "reason"}, "sport": {"<id>": "kayak"}}

Plain JSON in git: every change is a commit, every mistake has an undo, and GitHub Actions can
read and write it with nothing installed. An activity file is written once and never edited
by the app (its raw summary is the original); everything derived from it is recomputed on every
run by score.py.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ACTS = DATA / "activities"
TRACKS = DATA / "tracks"
STEPS = DATA / "steps.json"
LEDGER = DATA / "ledger.json"
OVERRIDES = DATA / "overrides.json"
DOCS = ROOT / "docs"


def _read(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                    encoding="utf-8")


def activity_ids() -> set[int]:
    return {int(p.stem) for p in ACTS.glob("*.json")}


def activities() -> list[dict]:
    """Every stored activity, oldest first."""
    rows = [_read(p, None) for p in ACTS.glob("*.json")]
    return sorted((r for r in rows if r), key=lambda r: r["start_local"])


def write_activity(row: dict) -> None:
    _write(ACTS / f"{row['id']}.json", row)


def write_track(activity_id: int, points: list[list[float]], n_raw: int) -> None:
    _write(TRACKS / f"{activity_id}.json", {"id": activity_id, "n_raw": n_raw, "points": points})


def has_track(activity_id: int) -> bool:
    return (TRACKS / f"{activity_id}.json").exists()


def steps() -> dict:
    return _read(STEPS, {})


def write_steps(obj: dict) -> None:
    _write(STEPS, obj)


def ledger() -> dict:
    return _read(LEDGER, {"weeks": {}})


def write_ledger(obj: dict) -> None:
    _write(LEDGER, obj)


def overrides() -> dict:
    ov = _read(OVERRIDES, {})
    ov.setdefault("exclude", {})
    ov.setdefault("sport", {})
    return ov


def write_overrides(obj: dict) -> None:
    _write(OVERRIDES, obj)
