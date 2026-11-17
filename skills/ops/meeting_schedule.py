#!/usr/bin/env python3
"""The declared meeting schedule (CR-179): when a series meets, and what may run around it.

    python3 meeting_schedule.py --dir <project or meetings folder> [--json] [--now ISO]

Read-only. One reader for one declaration, shared by `build_agenda.py`, `project_brief.py`
and `run_report.py`, so the three cannot disagree about when a series meets.

The block, in the project's config beside `meeting_types`:

    meetings:
      - type: standup                     # a key in meeting_types; names the preparation mode
        days: [mon, thu]                  # or: weekdays, daily
        time: "08:30"
        timezone: Europe/Stockholm        # optional; the machine's own zone when absent
        duration: 30m
        prepare_lead: 45m                 # the preparation starts here; ready by lead - 15m
        transcript_wait: 4h               # how long after the end to look for the recording
        unattended: [prepare, process]    # what may run with nobody there; absent = nothing
        apply_ledgers: false              # an unattended run writes ledgers only when true

Why one block: series wrote their meeting time in three shapes -- a
`meeting_types.<type>.schedule` block, a `time:` key, a YAML comment -- and nothing could
read all three. **Absent means off**: a series without `meetings:` is never touched by a
scheduler, and every reader here behaves exactly as it did before the block existed.

Resolution is the normal config chain, nearest declaration wins, walking up: a project's
`.claude/ops-config.yaml`, then `_ops.yaml`, then the vault's `_config/base.yaml`. The
nearest `meetings:` is taken whole -- a list is not merged across layers, because a merged
schedule is one nobody wrote. `meetings: []` declares "none here" and stops the walk.

A malformed entry is a PROBLEM, reported by name and skipped -- never a crash, and never a
guess. A typo in `days` drops that day and says so; it must not empty the schedule.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

import yaml

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover -- python < 3.9
    ZoneInfo = None
    ZoneInfoNotFoundError = Exception

# The config file pair, nearest-first within one folder. Declared once, here: build_agenda
# re-exports it, so a reader walking the chain itself cannot drift from the order the
# agenda resolves.
CONFIG_FILES = (Path(".claude") / "ops-config.yaml", Path("_ops.yaml"))
VAULT_FILE = Path("_config") / "base.yaml"

STEPS = ("prepare", "process")
DAY_NAMES = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
DAY_SETS = {"weekdays": (0, 1, 2, 3, 4), "daily": (0, 1, 2, 3, 4, 5, 6)}
DEFAULTS = {"duration": "30m", "prepare_lead": "45m", "transcript_wait": "4h"}
# The preparation is READY this long after it starts: `prepare_lead: 45m` is a run that
# starts 45 minutes before the meeting and is due 30 minutes before it.
READY_AFTER = datetime.timedelta(minutes=15)

_DUR = re.compile(r"^\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m(?:in)?)?\s*$", re.I)
_TIME = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def duration(value) -> datetime.timedelta | None:
    """`30m`, `4h`, `1h30m`, or a bare number of minutes. None when unreadable."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return datetime.timedelta(minutes=value) if value >= 0 else None
    s = str(value or "").strip()
    if s.isdigit():
        return datetime.timedelta(minutes=int(s))
    m = _DUR.match(s)
    if not m or not (m.group(1) or m.group(2)):
        return None
    return datetime.timedelta(hours=int(m.group(1) or 0), minutes=int(m.group(2) or 0))


def _days(value, where: str, problems: list[str]) -> tuple[int, ...]:
    raw = [value] if isinstance(value, str) else list(value or [])
    out: set[int] = set()
    for x in raw:
        v = str(x).strip().lower()
        if v in DAY_SETS:
            out.update(DAY_SETS[v])
            continue
        i = next((n for n, d in enumerate(DAY_NAMES) if d == v or (len(v) == 3 and d.startswith(v))), None)
        if i is None:
            problems.append(f"{where}: unknown day {x!r} -- ignored")
        else:
            out.add(i)
    return tuple(sorted(out))


def _zone(name, where: str, problems: list[str]):
    if not name:
        return None
    if ZoneInfo is None:
        problems.append(f"{where}: timezone {name!r} cannot be read on this Python -- local time used")
        return None
    try:
        return ZoneInfo(str(name))
    except (ZoneInfoNotFoundError, ValueError, OSError):
        problems.append(f"{where}: unknown timezone {name!r} -- entry skipped")
        return False


def parse(raw, meeting_types=None) -> tuple[list[dict], list[str]]:
    """Normalise a `meetings:` value. Returns (entries, problems).

    An entry missing `type`, `days` or `time`, or with an unknown timezone, is skipped
    with a problem. Unknown `unattended` steps are dropped with a problem: a step this
    suite does not know cannot have been meant to run unattended.
    """
    problems: list[str] = []
    if raw is None:
        return [], problems
    if not isinstance(raw, list):
        return [], [f"meetings: expected a list, found {type(raw).__name__} -- ignored"]
    known_types = set((meeting_types or {}).keys()) if isinstance(meeting_types, dict) else set()
    out = []
    for n, e in enumerate(raw, 1):
        where = f"meetings[{n}]"
        if not isinstance(e, dict):
            problems.append(f"{where}: expected a mapping -- skipped")
            continue
        typ = str(e.get("type") or "").strip()
        if not typ:
            problems.append(f"{where}: no `type` -- skipped")
            continue
        where = f"meetings[{n}] ({typ})"
        if known_types and typ not in known_types:
            problems.append(f"{where}: type is not a key in meeting_types -- preparation mode defaults to single")
        days = _days(e.get("days"), where, problems)
        if not days:
            problems.append(f"{where}: no readable day in `days` -- skipped")
            continue
        tm = _TIME.match(str(e.get("time") or "").strip())
        if not tm:
            problems.append(f"{where}: `time` must be HH:MM -- skipped")
            continue
        tz = _zone(e.get("timezone"), where, problems)
        if tz is False:
            continue
        durs = {}
        for k, default in DEFAULTS.items():
            d = duration(e.get(k, default))
            if d is None:
                problems.append(f"{where}: `{k}` {e.get(k)!r} unreadable -- {default} used")
                d = duration(default)
            durs[k] = d
        un = e.get("unattended") or []
        un = [un] if isinstance(un, str) else list(un)
        steps = []
        for s in un:
            s = str(s).strip().lower()
            if s in STEPS:
                steps.append(s)
            else:
                problems.append(f"{where}: unattended step {s!r} is not one of {', '.join(STEPS)} -- dropped")
        apply = e.get("apply_ledgers", False)
        if not isinstance(apply, bool):
            problems.append(f"{where}: `apply_ledgers` must be true or false -- false used")
            apply = False
        out.append({"type": typ, "days": days,
                    "time": f"{int(tm.group(1)):02d}:{tm.group(2)}",
                    "timezone": str(e.get("timezone")) if tz else None, "_tz": tz,
                    **durs, "unattended": tuple(dict.fromkeys(steps)), "apply_ledgers": apply})
    return out, problems


def _load(p: Path) -> dict | None:
    try:
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    return d if isinstance(d, dict) else None


def declared(start: Path) -> dict:
    """The `meetings:` declaration that applies at `start`, through the config chain.

    Returns {"meetings": [...], "problems": [...], "file": Path | None}. An absent block
    is `{"meetings": [], "problems": [], "file": None}` -- the shape every reader treats
    as "not declared", which is how an absent block changes nothing.
    """
    start = Path(start).resolve()
    chain = [root / name for root in (start, *start.parents) for name in CONFIG_FILES]
    chain += [root / VAULT_FILE for root in (start, *start.parents)]
    for p in chain:
        if not p.is_file():
            continue
        d = _load(p)
        if d is None or "meetings" not in d:
            continue
        entries, problems = parse(d.get("meetings"), d.get("meeting_types"))
        return {"meetings": entries, "problems": problems, "file": p}
    return {"meetings": [], "problems": [], "file": None}


def _local_zone():
    return datetime.datetime.now().astimezone().tzinfo


def _aware(now: datetime.datetime | None) -> datetime.datetime:
    now = now or datetime.datetime.now().astimezone()
    return now if now.tzinfo else now.replace(tzinfo=_local_zone())


def occurrences(entry: dict, after: datetime.datetime, limit: int = 1):
    """The next `limit` starts of one entry at or after `after`, in the entry's zone."""
    tz = entry.get("_tz") or _local_zone()
    after = _aware(after).astimezone(tz)
    hh, mm = (int(x) for x in entry["time"].split(":"))
    day = after.date()
    out = []
    for _ in range(8 * max(1, limit) + 7):
        if day.weekday() in entry["days"]:
            start = datetime.datetime(day.year, day.month, day.day, hh, mm, tzinfo=tz)
            if start >= after:
                out.append(start)
                if len(out) >= limit:
                    break
        day += datetime.timedelta(days=1)
    return out


def next_meeting(entries: list[dict], now: datetime.datetime | None = None):
    """(entry, start) of the soonest declared meeting at or after `now`, or None."""
    best = None
    for e in entries:
        for start in occurrences(e, _aware(now)):
            if best is None or start < best[1]:
                best = (e, start)
    return best


def windows(entry: dict, start: datetime.datetime) -> dict:
    """When each step around one meeting is due. The scheduler's arithmetic, stated once."""
    end = start + entry["duration"]
    prepare_at = start - entry["prepare_lead"]
    return {"start": start, "end": end, "prepare_at": prepare_at,
            "ready_by": prepare_at + READY_AFTER, "transcript_by": end + entry["transcript_wait"]}


def allows(entry: dict | None, step: str) -> bool:
    return bool(entry) and step in entry.get("unattended", ())


def select(entries: list[dict], step: str | None = None, typ: str | None = None) -> tuple[dict | None, str]:
    """The one entry a run is for, or (None, why). Never guesses between two."""
    pool = [e for e in entries if typ is None or e["type"] == typ]
    if step:
        pool = [e for e in pool if allows(e, step)]
    if not pool:
        what = f"type {typ!r}" if typ else "this folder"
        return None, (f"no meeting declared for {what}" if not step
                      else f"`{step}` is not declared unattended for {what} -- absent means off")
    if len(pool) > 1:
        return None, "more than one declared meeting matches -- name the type"
    return pool[0], ""


def public(entry: dict) -> dict:
    """An entry as plain data -- for JSON, the run report and the scheduler."""
    out = {k: v for k, v in entry.items() if not k.startswith("_")}
    out["days"] = [DAY_NAMES[d][:3] for d in entry["days"]]
    out["unattended"] = list(entry["unattended"])
    for k in DEFAULTS:
        out[k] = f"{int(entry[k].total_seconds() // 60)}m"
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dir", default=".", help="a project or meetings folder")
    ap.add_argument("--now", help="ISO datetime to count from (default: now)")
    ap.add_argument("--json", action="store_true", help="machine-readable, for a scheduler")
    a = ap.parse_args()
    now = _aware(datetime.datetime.fromisoformat(a.now)) if a.now else _aware(None)
    d = declared(Path(a.dir))
    rows = []
    for e in d["meetings"]:
        nxt = occurrences(e, now)
        w = windows(e, nxt[0]) if nxt else None
        rows.append({**public(e), "next": {k: v.isoformat() for k, v in w.items()} if w else None})
    if a.json:
        print(json.dumps({"file": str(d["file"]) if d["file"] else None, "meetings": rows,
                          "problems": d["problems"]}, indent=2, ensure_ascii=False))
        return
    if not d["file"]:
        print("meetings: not declared -- nothing here runs on a schedule")
        return
    print(f"meetings: declared in {d['file']}")
    for r in rows:
        nx = r["next"]
        print(f"  {r['type']:<16} {','.join(r['days'])} {r['time']}"
              + (f" {r['timezone']}" if r.get("timezone") else " (local)")
              + f"  unattended: {', '.join(r['unattended']) or 'nothing'}"
              + f"  ledgers: {'applied' if r['apply_ledgers'] else 'proposed'}")
        if nx:
            print(f"    next {nx['start']}  prepare {nx['prepare_at']}  ready {nx['ready_by']}"
                  f"  transcript by {nx['transcript_by']}")
    for p in d["problems"]:
        print(f"  ! {p}")


if __name__ == "__main__":
    main()
