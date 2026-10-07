#!/usr/bin/env python3
"""Issue movement for a declared repo: the release gap over time, by area (CR-107).

Generated, never hand-edited. Reads GitHub live (read-only, via `gh`) and writes:
  <out>/YYMMDD-issue-movement.md        the details file the agenda's movement block links to
  <out>/snapshots/YYMMDD.json           that run's per-issue state, for exact day-over-day later
and returns the agenda's movement block.

The one live read in the agenda pipeline, and deliberately so: the vault's archive keeps
the most recently updated issues, which answers "what moved" but never "how many are open".
Best effort -- a failure is reported and the agenda is still built.

Config, beside `carry_forward` in the project's config:

    external_systems:
      repos:
        - url: github.com/Org/repo
          labels:
            priority: [blocker, critical, medium]   # highest first; one priority per issue
            gap: [blocker, critical]                # the priorities that make the release gap
            awaiting_test: "status: Fixed"          # fixed, waiting for verification
            blocked: "status: Blocked on backend"   # optional: who owes the next step
            answered: answered-waiting-on-jira      # optional: blocked, but already answered
            area_prefix: "area:"
          reports:                                  # optional: dated reports in the repo (CR-107)
            - name: Status report
              dir: docs/investigations
              pattern: '^\\d{4}-\\d{2}-\\d{2}-status-report\\.md$'
    workflows:
      post_processing:
        carry_forward:
          movement:
            out: status/movement                    # relative to the project root
            days: 14
            note: "..."                             # optional line printed under the block

History is rebuilt from the repo's issue events. Priority labels exist only from their
first use; before that the series says so instead of printing zero.

Three checks, printed in the block (pass or fail, never silent):
  - the state rebuilt from history must equal GitHub's current state
  - every day shown must be covered by event history (GitHub keeps about 90 days)
  - the agenda's date must equal the day the movement was read (else STALE)
"""
import argparse, collections, datetime as dt, json, os, re, subprocess, sys
from pathlib import Path
from zoneinfo import ZoneInfo



def _gh(args):
    r = subprocess.run(["gh"] + args, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"gh {' '.join(args[:3])}: {r.stderr.strip()[:200]}")
    return r.stdout


def _ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def repo_slug(url: str) -> str:
    return re.sub(r"^(https?://)?github\.com/", "", url).strip("/")


def declared(cf: dict) -> dict | None:
    """The first declared repo that carries a `labels:` block, or None."""
    for r in ((cf.get("ext") or {}).get("repos") or []):
        if isinstance(r, dict) and r.get("labels") and r.get("url"):
            return r
    return None


def load(repo):
    issues = json.loads(_gh(["issue", "list", "-R", repo, "--state", "all", "--limit", "5000", "--json",
                             "number,title,state,createdAt,closedAt,labels,assignees,url"]))
    labels = json.loads(_gh(["label", "list", "-R", repo, "--limit", "200", "--json", "name,description"]))
    raw = _gh(["api", f"repos/{repo}/issues/events?per_page=100", "--paginate", "--jq",
               '.[]|select(.event=="labeled" or .event=="unlabeled" or .event=="closed" or .event=="reopened")'
               '|[.event,.created_at,.issue.number,(.label.name//"")]|@tsv'])
    nums = {i["number"] for i in issues}
    events = []
    for line in raw.splitlines():
        e, t, n, l = line.split("\t")
        if int(n) in nums:
            events.append((_ts(t), e, int(n), l))
    events.sort()
    return issues, labels, events


class History:
    """At time t: was issue n open, and did it carry label l."""

    def __init__(self, issues, events):
        self.issue = {i["number"]: i for i in issues}
        self.lab = collections.defaultdict(list)
        self.state = collections.defaultdict(list)
        self.first_use = {}
        for t, e, n, l in events:
            if e in ("labeled", "unlabeled"):
                self.lab[(n, l)].append((t, e == "labeled"))
                self.first_use.setdefault(l, t)
            else:
                self.state[n].append((t, e == "reopened"))

    def is_open(self, n, t):
        i = self.issue[n]
        if _ts(i["createdAt"]) > t:
            return False
        ev = [o for (et, o) in self.state[n] if et <= t]
        if ev:
            return ev[-1]
        if self.state[n]:
            return True
        return not i["closedAt"] or _ts(i["closedAt"]) > t

    def has(self, n, l, t):
        ev = self.lab.get((n, l))
        if ev:
            before = [p for (et, p) in ev if et <= t]
            return before[-1] if before else False
        # No event: applied at creation. Counted from creation, never before the
        # label's first recorded use in the repo.
        if l not in {x["name"] for x in self.issue[n]["labels"]}:
            return False
        c = _ts(self.issue[n]["createdAt"])
        return max(c, self.first_use.get(l, c)) <= t


def build(repo_decl: dict, mv: dict, root: Path, agenda_day: dt.date | None = None):
    """Returns (headline_markdown, details_path, reports_lines)."""
    repo = repo_slug(repo_decl["url"])
    lab = repo_decl["labels"]
    PRIORITY = list(lab.get("priority") or [])
    GAP = list(lab.get("gap") or PRIORITY[:2])
    FIXED = lab.get("awaiting_test")
    BLOCKED, ANSWERED = lab.get("blocked"), lab.get("answered")
    AREA = lab.get("area_prefix") or "area:"
    TZ = ZoneInfo(mv["tz"]) if mv.get("tz") else dt.datetime.now().astimezone().tzinfo
    days = int(mv.get("days") or 14)
    out = root / (mv.get("out") or "status/movement")
    (out / "snapshots").mkdir(parents=True, exist_ok=True)

    issues, labels, events = load(repo)
    h = History(issues, events)
    now = dt.datetime.now(TZ)
    today = now.date()
    stamp = today.strftime("%y%m%d")
    names = lambda i: {x["name"] for x in i["labels"]}

    def prio_at(n, t):
        return next((p for p in PRIORITY if h.has(n, p, t)), None)

    def prio(i):
        return next((p for p in PRIORITY if p in names(i)), "none")

    def area(i):
        a = [x["name"][len(AREA):] for x in i["labels"] if x["name"].startswith(AREA)]
        return ", ".join(sorted(a)) if a else "(no area label)"

    first_prio = min((h.first_use[p] for p in GAP if p in h.first_use), default=None)
    rows = []
    for k in range(days - 1, -1, -1):
        d = today - dt.timedelta(days=k)
        end = now if k == 0 else dt.datetime.combine(d, dt.time(23, 59, 59), TZ)
        start = dt.datetime.combine(d, dt.time(0, 0), TZ)
        open_ = [n for n in h.issue if h.is_open(n, end)]
        r = {"date": d, "open": len(open_),
             "opened": sum(1 for i in issues if start <= _ts(i["createdAt"]) <= end),
             "closed": sum(1 for (t, e, n, l) in events if e == "closed" and start <= t <= end),
             "fixed": sum(1 for n in open_ if FIXED and h.has(n, FIXED, end)),
             "prio_known": first_prio is not None and end >= first_prio}
        for p in GAP:
            o = [n for n in open_ if prio_at(n, end) == p]
            r[p] = len(o)
            r[p + "_fixed"] = sum(1 for n in o if FIXED and h.has(n, FIXED, end))
        rows.append(r)

    # ---- checks
    checks = []
    live_open = [i for i in issues if i["state"] == "OPEN"]
    if rows[-1]["open"] != len(live_open):
        checks.append(f"open issues rebuilt from history = {rows[-1]['open']}, GitHub reports {len(live_open)}")
    for p in GAP:
        live = sum(1 for i in live_open if prio(i) == p)
        if rows[-1][p] != live:
            checks.append(f"open {p} rebuilt = {rows[-1][p]}, GitHub reports {live}")
    oldest = events[0][0] if events else None
    uncovered = [r["date"] for r in rows if oldest and dt.datetime.combine(r["date"], dt.time(0, 0), TZ) < oldest]
    if uncovered:
        checks.append(f"issue events reach back to {oldest.astimezone(TZ):%d/%m} only; "
                      f"{len(uncovered)} earlier day(s) left out of the series")
        rows = [r for r in rows if r["date"] not in uncovered]
    if len(issues) >= 5000:
        checks.append("the issue list hit its 5,000 limit; counts may be incomplete")

    json.dump({"repo": repo, "taken": now.isoformat(timespec="minutes"), "checks": checks,
               "issues": [{"n": i["number"], "state": i["state"], "labels": sorted(names(i)),
                           "created": i["createdAt"], "closed": i["closedAt"], "title": i["title"],
                           "assignees": [a["login"] for a in i["assignees"]]} for i in issues]},
              open(out / "snapshots" / f"{stamp}.json", "w"), indent=0)

    t = rows[-1]
    y = rows[-2] if len(rows) > 1 else None
    wk = rows[-8] if len(rows) >= 8 else None

    def gap(r):
        return sum(r[p] for p in GAP)

    def todo(r):
        return sum(r[p] - r[p + "_fixed"] for p in GAP)

    def d(a, b):
        if b is None:
            return "—"
        x = a - b
        return "=" if x == 0 else f"{'+' if x > 0 else ''}{x}"

    split = " + ".join(str(t[p]) for p in GAP)
    split_todo = " + ".join(str(t[p] - t[p + "_fixed"]) for p in GAP)
    known_y = y is not None and y["prio_known"]
    known_w = wk is not None and wk["prio_known"]
    fixed_since = h.first_use.get(FIXED) if FIXED else None
    rel = os.path.relpath(out / f"{stamp}-issue-movement.md", root)
    head = [
        f"**Movement** — `{repo}`, read {now:%d/%m %H:%M} · details: `{rel}`",
        "",
        "| | Now | Since yesterday | Since 7 days |",
        "|---|--:|--:|--:|",
        f"| **Open {' + '.join(GAP)}, by label** | **{gap(t)}** ({split}) | "
        f"{d(gap(t), gap(y)) if known_y else 'not labelled yet'} | {d(gap(t), gap(wk)) if known_w else 'not labelled yet'} |",
        f"| … still to fix | **{todo(t)}** ({split_todo}) | {d(todo(t), todo(y)) if known_y else '—'} | |",
        f"| … fixed, waiting for a test | {gap(t) - todo(t)} | | |",
        f"| Open issues, all | {t['open']} | {d(t['open'], y['open'] if y else None)} | {d(t['open'], wk['open'] if wk else None)} |",
    ]
    if FIXED:
        wcell = (d(t["fixed"], wk["fixed"]) if wk and fixed_since and
                 dt.datetime.combine(wk["date"], dt.time(23, 59), TZ) >= fixed_since
                 else (f"label used from {fixed_since.astimezone(TZ):%d/%m}" if fixed_since else "—"))
        head.append(f"| Fixed, waiting for a test | {t['fixed']} | {d(t['fixed'], y['fixed'] if y else None)} | {wcell} |")
    head.append(f"| Opened / closed today | {t['opened']} / {t['closed']} | | |")

    gapi = sorted([i for i in live_open if prio(i) in GAP],
                  key=lambda i: (PRIORITY.index(prio(i)), area(i), i["number"]))
    if gapi:
        top = collections.Counter(area(i) for i in gapi).most_common(2)
        head += ["", "Where the gap is: " + "; ".join(f"**{a}** {c}" for a, c in top) + f" of {len(gapi)}."]
    if first_prio:
        head.append(f"Priority labels in use since {first_prio.astimezone(TZ):%d/%m}; earlier days have no priority history.")
    if mv.get("note"):
        head.append(str(mv["note"]))
    head += ["", "**Checks: passed** — the rebuilt state matches GitHub now, and every day shown is covered by history."
             if not checks else "**CHECK FAILED — do not quote these numbers until fixed:** " + "; ".join(checks) + "."]
    if agenda_day and agenda_day != today:
        head.insert(0, f"**STALE — read {today:%d/%m}, the agenda is for {agenda_day:%d/%m}. Rebuild before the meeting.**\n")
    headline = "\n".join(head)

    # ---- the details file
    openi = live_open
    areas = collections.defaultdict(collections.Counter)
    for i in openi:
        areas[area(i)][prio(i) + (" fixed" if FIXED and FIXED in names(i) else "")] += 1
    L = [f"# Issue movement — `{repo}`, {now:%d %B %Y}", "",
         f"**Generated** {now:%Y-%m-%d %H:%M} by the ops skill's `build_movement.py` from GitHub issues and "
         f"issue events. Never hand-edited; regenerate instead. Snapshot: `snapshots/{stamp}.json`.", "",
         "## 1. Headline", "", "\n".join(head[2:] if not head[0].startswith("**STALE") else head[3:]), "",
         f"## 2. Day by day, last {len(rows)} days", "",
         "End of each day; today is *now*. Each issue counts at its highest priority; *(f)* = already fixed, waiting for a test.", "",
         "| Day | Opened | Closed | Open | Fixed, waiting for a test | " + " | ".join(f"Open {p} (f)" for p in GAP) + " |",
         "|---|--:|--:|--:|--:|" + "--:|" * len(GAP)]
    for r in rows:
        cells = [f"{r[p]} ({r[p + '_fixed']})" if r["prio_known"] else "—" for p in GAP]
        L.append(f"| {r['date']:%a %d/%m} | {r['opened']} | {r['closed']} | {r['open']} | {r['fixed']} | " + " | ".join(cells) + " |")
    L += ["", "*— = the priority labels were not in use yet.*", "",
          "## 3. Open issues by area and priority, now", "",
          "| Area | " + " | ".join(p.capitalize() for p in PRIORITY) + " | No priority | of all: fixed |",
          "|---|" + "--:|" * (len(PRIORITY) + 2)]
    tot = collections.Counter()
    for a in sorted(areas, key=lambda a: -sum(areas[a][p] + areas[a][p + " fixed"] for p in GAP)):
        c = areas[a]
        fx = sum(v for k_, v in c.items() if k_.endswith(" fixed"))
        cells = [c[p] + c[p + " fixed"] for p in PRIORITY + ["none"]]
        for p, v in zip(PRIORITY + ["none"], cells):
            tot[p] += v
        tot["fixed"] += fx
        L.append(f"| {a} | " + " | ".join(str(v) for v in cells) + f" | {fx} |")
    L.append("| **All** | " + " | ".join(f"**{tot[p]}**" for p in PRIORITY + ["none"]) + f" | **{tot['fixed']}** |")
    L += ["", f"**{tot['none']} of {len(openi)} open issues ({100 * tot['none'] // max(1, len(openi))}%) carry no priority label.** "
          "Until they are triaged, the gap is a floor.", "",
          "## 4. The open issues in the gap", "",
          "| # | Priority | Area | State | Age (days) | Assignee | Title |", "|---|---|---|---|--:|---|---|"]
    for i in gapi:
        st = ("fixed, waiting for a test" if FIXED and FIXED in names(i)
              else "blocked: " + BLOCKED if BLOCKED and BLOCKED in names(i) else "open")
        L.append(f"| [#{i['number']}]({i['url']}) | {prio(i)} | {area(i)} | {st} | {(now - _ts(i['createdAt'])).days} | "
                 f"{', '.join(a['login'] for a in i['assignees']) or '—'} | {i['title'][:90].replace('|', '/')} |")
    defs = {l["name"]: l["description"] for l in labels}
    L += ["", "## 5. Definitions — as the repo's labels define them", "", "| Label | Definition |", "|---|---|"]
    for n in PRIORITY + [x for x in (FIXED, BLOCKED, ANSWERED) if x] + sorted(k for k in defs if k.startswith(AREA)):
        if n in defs:
            L.append(f"| `{n}` | {defs[n] or '*(no description)*'} |")
    L += ["", "## 6. Limits", "",
          "- Labels applied when an issue was created leave no event; they count from creation, never before the label's first use.",
          f"- Areas are the repo's `{AREA}` labels, so anyone can reproduce a count with a GitHub filter.",
          "- Ticket systems outside GitHub are not read."]
    if BLOCKED:
        b = sum(1 for i in openi if BLOCKED in names(i))
        ans = sum(1 for i in openi if BLOCKED in names(i) and ANSWERED and ANSWERED in names(i))
        L.append(f"- `{BLOCKED}` is who owes the next step, not a severity: {b} open"
                 + (f", of which {ans} already answered (`{ANSWERED}`)" if ANSWERED else "") + ".")
    if checks:
        L += ["", "## Checks failed", ""] + [f"- {c}" for c in checks]
    path = out / f"{stamp}-issue-movement.md"
    path.write_text("\n".join(L) + "\n", encoding="utf-8")

    # ---- declared reports: newest per pattern (CR-107)
    rep = []
    for r in (repo_decl.get("reports") or []):
        try:
            names_ = json.loads(_gh(["api", f"repos/{repo}/contents/{r['dir']}", "--jq", "[.[].name]"]))
            hits = sorted(n for n in names_ if re.match(r["pattern"], n))
            newest = hits[-1] if hits else None
            ds = re.search(r"(\d{4})-?(\d{2})-?(\d{2})", newest or "")
            age = f" · {(today - dt.date(int(ds[1]), int(ds[2]), int(ds[3]))).days}d old" if ds else ""
            rep.append(f"  report    {r.get('name', r['dir'])[:44]:44} "
                       + (f"newest {r['dir']}/{newest}{age}" if newest else "NONE FOUND"))
        except Exception as e:  # best effort
            rep.append(f"  report    {r.get('name', r.get('dir', '?'))[:44]:44} NOT READ — {e}")
    return headline, path, rep


def run(cf: dict, agenda_day: dt.date | None = None):
    """For build_agenda: (headline, path, report_lines) or (None, reason, [])."""
    decl = declared(cf)
    if not decl:
        return None, "no repo with `labels:` declared", []
    try:
        return build(decl, cf.get("movement") or {}, Path(cf["_root"]), agenda_day)
    except Exception as e:
        return None, f"not read — {e}", []


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    from build_agenda import config  # noqa: E402
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="the project's meetings folder (for the config chain)")
    ap.add_argument("--date", help="YYMMDD the agenda is for; stamps STALE when it differs from today")
    a = ap.parse_args()
    cf = config(Path(a.dir).resolve())
    day = dt.datetime.strptime(a.date, "%y%m%d").date() if a.date else None
    head, path, rep = run(cf, day)
    if head is None:
        sys.exit(f"movement: {path}")
    print(head)
    print("\n".join(rep))
    print(f"\nwrote {path}")
