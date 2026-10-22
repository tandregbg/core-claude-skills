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


def archived(root: Path, repo: str) -> tuple | None:
    """CR-121/CR-148: the same three reads, from an archive instead of from `gh`.

    `<venture>/.movementmeta/<owner>-<name>.json` -- the sibling of `.githubmeta/` and
    `.jirameta/`, found the same way and read the same way: whatever an archiver wrote,
    never the network. `{"issues": [...], "labels": [...], "events": [[event, iso,
    number, label], ...]}`, each list exactly as `gh` returns it. The events are sorted
    and scoped to the issues read, which is what `load()` does, so the two reads hand
    `History` the same thing and a record is not a second code path downstream.

    Without it the movement half of the card is reachable only with a live `gh`, which
    means it cannot be generated on a machine with no credential and -- the reason this
    exists -- cannot be covered by a test at all. The repo table, the demo rows and the
    post's grouped blockers were all unreachable from a fixture, and two of them were
    wrong because of it.
    """
    venture = next((p for p in [root, *root.parents] if (p / ".movementmeta").is_dir()), None)
    if venture is None:
        return None
    f = venture / ".movementmeta" / (repo.replace("/", "-") + ".json")
    if not f.is_file():
        return None
    d = json.loads(f.read_text(encoding="utf-8"))
    nums = {i["number"] for i in d.get("issues") or []}
    events = sorted((_ts(t), e, int(n), l) for e, t, n, l in (d.get("events") or [])
                    if int(n) in nums)
    return d.get("issues") or [], d.get("labels") or [], events


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

    # The archive first where there is one, `gh` otherwise: an archived read is what
    # every other source in this pipeline does, and it is the only one a fixture can
    # reach (CR-121/CR-148, see `archived`).
    issues, labels, events = archived(root, repo) or load(repo)
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
    # CR-114 (a reader, 9/10): every row says whether it is the release gap or all issues, so the two
    # "waiting for a test" counts cannot be read as duplicates.
    gap_labels = " or ".join(f"`{g}`" for g in GAP)
    gap_split = ", ".join(f"{g} {t[g]}" for g in GAP)
    todo_split = ", ".join(f"{g} {t[g] - t[g + '_fixed']}" for g in GAP)
    head = [
        f"**Movement** — `{repo}`, read {now:%d/%m %H:%M} · details: `{rel}`",
        "",
        "| | Now | Since yesterday | Since 7 days |",
        "|---|--:|--:|--:|",
        f"| **Release gap** — open issues labelled {gap_labels} | **{gap(t)}** ({gap_split}) | "
        f"{d(gap(t), gap(y)) if known_y else '—'} | {d(gap(t), gap(wk)) if known_w else '—'} |",
        f"| Release gap: still to fix | **{todo(t)}** ({todo_split}) | {d(todo(t), todo(y)) if known_y else '—'} | |",
        f"| Release gap: fixed, waiting for a test | {gap(t) - todo(t)} | | |",
        f"| All issues: open | {t['open']} | {d(t['open'], y['open'] if y else None)} | {d(t['open'], wk['open'] if wk else None)} |",
    ]
    if FIXED:
        wcell = (d(t["fixed"], wk["fixed"]) if wk and fixed_since and
                 dt.datetime.combine(wk["date"], dt.time(23, 59), TZ) >= fixed_since else "—")
        head.append(f"| All issues: fixed, waiting for a test | {t['fixed']} | {d(t['fixed'], y['fixed'] if y else None)} | {wcell} |")
    head.append(f"| All issues: opened / closed today | {t['opened']} / {t['closed']} | | |")

    gapi = sorted([i for i in live_open if prio(i) in GAP],
                  key=lambda i: (PRIORITY.index(prio(i)), area(i), i["number"]))
    if gapi:
        top = collections.Counter(area(i) for i in gapi).most_common(2)
        head += ["", "Where the gap is: " + "; ".join(f"**{a}** {c}" for a, c in top) + f" of {len(gapi)}."]
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
          (f"- Priority labels in use since {first_prio.astimezone(TZ):%d/%m}; earlier days show —." if first_prio else "- No priority labels found."),
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

    # ---- declared reports (CR-107), with a stable current path (CR-114)
    # A dated file per day is history, not a source: if today's is missing, nothing
    # says what to rely on. `current:` names the one path that is always the status;
    # its last commit date is its age. `pattern:` alone is reported as a series with
    # no stable source, which is the finding.
    rep = []
    report_state = []          # (name, owner, path_or_None, age_days_or_None)
    for r in (repo_decl.get("reports") or []):
        if r.get("current"):
            try:
                when = _gh(["api", f"repos/{repo}/commits?path={r['current']}&per_page=1",
                            "--jq", ".[0].commit.committer.date"]).strip()
                age_ = (today - _ts(when).astimezone(TZ).date()).days if when else None
                tag = ("updated today" if age_ == 0 else f"STALE — last updated {age_}d ago") if age_ is not None else "NOT FOUND"
                rep.append(f"  report    {r.get('name', r['current'])[:44]:44} current {r['current']} · {tag}")
                report_state.append((r.get("name", r["current"]), r.get("owner"), r["current"], age_))
            except Exception as e:
                rep.append(f"  report    {r.get('name', r['current'])[:44]:44} NOT READ — {e}")
                report_state.append((r.get("name", r["current"]), r.get("owner"), r["current"], None))
            if not r.get("pattern"):
                continue
        try:
            names_ = json.loads(_gh(["api", f"repos/{repo}/contents/{r['dir']}", "--jq", "[.[].name]"]))
            hits = sorted(n for n in names_ if re.match(r["pattern"], n))
            newest = hits[-1] if hits else None
            ds = re.search(r"(\d{4})-?(\d{2})-?(\d{2})", newest or "")
            age = f" · {(today - dt.date(int(ds[1]), int(ds[2]), int(ds[3]))).days}d old" if ds else ""
            rep.append(f"  report    {r.get('name', r['dir'])[:44]:44} "
                       + (f"newest {r['dir']}/{newest}{age}" if newest else "NONE FOUND")
                       + ("" if r.get("current") else " · no stable current path (CR-114)"))
            if not r.get("current"):
                d_ = int(age.split()[1][:-1]) if age else None
                report_state.append((r.get("name", r["dir"]), r.get("owner"),
                                     f"{r['dir']}/{newest}" if newest else None, d_))
        except Exception as e:  # best effort
            rep.append(f"  report    {r.get('name', r.get('dir', '?'))[:44]:44} NOT READ — {e}")
    top = PRIORITY[0] if PRIORITY else None
    blockers = [{"n": i["number"], "title": i["title"], "url": i["url"], "area": area(i),
                 "fixed": bool(FIXED and FIXED in names(i)),
                 "who": [a["login"] for a in i["assignees"]]}
                for i in gapi if top and prio(i) == top]
    # CR-155: every gap-label issue with its assignees and priority, not only the top one:
    # the compact agenda's round is built from what is ASSIGNED to each person.
    gap = [{"n": i["number"], "title": i["title"], "url": i["url"],
            "fixed": bool(FIXED and FIXED in names(i)),
            "who": [a["login"] for a in i["assignees"]], "prio": prio(i)}
           for i in gapi]
    # CR-119: a declared label the repo does not have makes every count silently zero.
    missing = [x for x in PRIORITY + [FIXED, BLOCKED, ANSWERED] if x and x not in defs]
    return headline, path, rep, {"blockers": blockers, "gap": gap, "reports": report_state, "top": top,
                                 "missing_labels": missing}


# CR-140: both dated spellings a report series is written in. The house convention
# for a dated report file is 6-digit YYMMDD (`vault_reports()` below, the agenda's
# own note names), but a repository series may be written 4-digit ISO, and `build()`
# reads that one. A pre-flight that knows only one spelling calls a conventionally
# named report undated, which is the difference between *fresh* and *cannot tell*.
# Six digits first: `20261021` would otherwise read its first four as a year.
_DATED = (re.compile(r"(\d{2})(\d{2})(\d{2})(?!\d)"),
          re.compile(r"(\d{4})-(\d{2})-(\d{2})"))


def filename_date(name: str) -> dt.date | None:
    """The date in a dated report filename -- 6-digit YYMMDD or 4-digit ISO -- or None.

    A name that carries digits in neither shape, or digits that are not a date
    (`261332-status.md`), is undated: the caller reports that, never a guess.
    """
    for i, rx in enumerate(_DATED):
        m = rx.search(name or "")
        if not m:
            continue
        y = int(m[1]) + 2000 if i == 0 else int(m[1])
        try:
            return dt.date(y, int(m[2]), int(m[3]))
        except ValueError:
            continue
    return None


# CR-140: letter runs and digit runs are separate words, so a year appended with no
# separator does not swallow the name it was appended to -- `reports` -> `reports2026`
# is the commonest form this rename takes, and one token `reports2026` shares nothing
# with `reports`. Digit-only tokens are dropped by `_words()`: two unrelated folders
# both carrying `2026` are not the same series renamed.
_WORD = re.compile(r"[a-z]+|[0-9]+")


def _words(name: str) -> set[str]:
    """The words of a directory name that can carry a match: four letters or more."""
    return {w for w in _WORD.findall(name.lower()) if len(w) >= 4 and w.isalpha()}


def renamed_to(root: Path, declared: str) -> str | None:
    """CR-140: a directory beside the declared one that looks like the same series renamed.

    A folder renamed overnight makes every report under it read as *source missing*,
    which sends a person looking for a report that exists. The likelier cause is that
    the CONFIG is stale, and the difference is one a script can see: the declared
    parent is still there and holds a sibling whose name shares a word with the name
    that went away.

    Same parent only, and a shared word of at least four letters. Looser matching
    (any parent, any shared prefix) suggests folders that have nothing to do with the
    series, and a suggestion that is wrong is worse than none: it is read as an
    answer. Returns the suggestion as a path relative to the declared parent's own
    spelling, or None.
    """
    d = Path(declared)
    want = _words(d.name)
    if not want:
        return None
    levels = (root, *root.parents)
    # CR-140: the declared directory is looked for across EVERY level before any
    # suggestion is made, the way `vault_reports()` resolves it. Guarding per level
    # instead let a decoy sibling in a nearer parent be suggested while the real
    # declared directory stood in a higher one -- a suggestion that is read as an
    # answer, pointing away from the folder that was there all along.
    if any((p_ / d).is_dir() for p_ in levels):
        return None
    for p_ in levels:
        parent = (p_ / d.parent) if str(d.parent) != "." else p_
        if not parent.is_dir():
            continue
        for cand in sorted(x for x in parent.iterdir() if x.is_dir()):
            if _words(cand.name) & want:
                return str(d.parent / cand.name) if str(d.parent) != "." else cand.name
    return None


def report_states(cf: dict, today: dt.date | None = None):
    """CR-140: the state of every declared report, with no repository history read.

    `build()` reports the same thing, but only after `load()` has pulled every issue
    and every label event -- about three minutes. A pre-flight that has to wait that
    long to say a report is three days old reports it three days late, so this takes
    the one status call per declared report and nothing else: the commit date of a
    `current:` path, or one directory listing for a `pattern:` series.

    Returns the `(name, owner, path_or_None, age_days_or_None)` tuples `build()` and
    `vault_reports()` return, with a fifth list of (name, detail) for what could not
    be read -- a failure here is reported, never guessed at as "missing".
    """
    today = today or dt.date.today()
    # CR-140: the zone `build()` reads a commit date in, from the same declaration
    # (`carry_forward.movement.tz`). Reading it in the machine's zone instead let the
    # two disagree about one report across the stale boundary -- exactly the
    # disagreement a pre-flight exists to prevent.
    mv = cf.get("movement") or {}
    tz = ZoneInfo(mv["tz"]) if mv.get("tz") else dt.datetime.now().astimezone().tzinfo
    states, problems = [], []
    for decl in ((cf.get("ext") or {}).get("repos") or []):
        if not (isinstance(decl, dict) and decl.get("url")):
            continue
        repo = repo_slug(decl["url"])
        for r in (decl.get("reports") or []):
            nm = r.get("name") or r.get("current") or r.get("dir", "?")
            # CR-140: a report declaring BOTH `current:` and `pattern:` is one
            # report, and `build()` reports it from `current:` alone -- the series
            # behind it is history, the stable path is the status (CR-114). Reading
            # the series here too would cost a second call per report and could
            # still only repeat that one state, so the fast path reads `current:`
            # and the two agree on the state they report. A `pattern:`-only
            # declaration is the series' own state, below.
            if r.get("current"):
                try:
                    when = _gh(["api", f"repos/{repo}/commits?path={r['current']}&per_page=1",
                                "--jq", ".[0].commit.committer.date"]).strip()
                    age = (today - _ts(when).astimezone(tz).date()).days if when else None
                    states.append((nm, r.get("owner"), r["current"] if when else None, age))
                except Exception as e:   # best effort, as everywhere else in this pipeline
                    problems.append((nm, f"not read — {type(e).__name__}: {str(e).splitlines()[0][:80]}"))
                continue
            try:
                names_ = json.loads(_gh(["api", f"repos/{repo}/contents/{r['dir']}", "--jq", "[.[].name]"]))
                hits = sorted(n for n in names_ if re.match(r["pattern"], n))
                newest = hits[-1] if hits else None
                # CR-140: both dated spellings, 6-digit YYMMDD and 4-digit ISO. The
                # 4-digit regex alone called every house-convention report undated.
                when_ = filename_date(newest or "")
                age = (today - when_).days if when_ else None
                states.append((nm, r.get("owner"), f"{r['dir']}/{newest}" if newest else None, age))
            except Exception as e:
                problems.append((nm, f"not read — {type(e).__name__}: {str(e).splitlines()[0][:80]}"))
    _lines, vs = vault_reports(cf, today)
    return states + list(vs), problems


def vault_report_dir(cf: dict, r: dict) -> Path | None:
    """The declared vault report's directory, resolved -- or None when it is not there.

    `dir:` is relative to the project root or found walking up, which is the one rule
    every reader of `vault_reports:` has to agree on: a project nested two levels under
    the venture declares `../../meetings/board/status` and the same folder has to resolve
    to the same path whichever reader asked.
    """
    root = Path(cf.get("_root") or ".")
    return next(((p_ / r["dir"]).resolve() for p_ in (root, *root.parents)
                 if (p_ / r["dir"]).is_dir()), None)


def vault_report_files(d: Path, r: dict) -> list[Path]:
    """The file(s) a declared vault report currently resolves to, in that directory.

    `current:` first when it exists -- a stable filename is the author's statement that
    this is the live one -- and otherwise the newest name matching `pattern:`, by sort,
    which is what a YYMMDD or ISO prefix makes chronological. Empty when neither answers.

    One reader, so a check that reports a report's age and a digest that reads its text
    (CR-150, proposal 2) cannot disagree about WHICH file the declaration named.
    """
    if r.get("current") and (f := d / r["current"]).exists():
        return [f]
    pat = r.get("pattern") or r"^$"
    return sorted(x for x in d.iterdir() if x.is_file() and re.match(pat, x.name))[-1:]


def vault_reports(cf: dict, today: dt.date | None = None):
    """CR-116: report series kept in the vault, not the repo -- board reports, dashboards.

    external_systems:
      vault_reports:
        - name: Board status
          dir: ../../meetings/board/status      # relative to the project root, or found walking up
          pattern: '^\\d{6}[a-z]?-board-status\\.md$'
          current: status.md                    # optional: a stable file in that dir
          owner: Ann                            # optional: summarised in that person's round minute

    Local files only -- no fetch. Returns (source lines, report states) in the shape
    `build()` returns for repo reports, so the card treats both alike.
    """
    today = today or dt.date.today()
    lines, states = [], []
    root = Path(cf["_root"])
    for r in ((cf.get("ext") or {}).get("vault_reports") or []):
        nm = r.get("name") or r.get("dir", "?")
        d = vault_report_dir(cf, r) if r.get("dir") else None
        if not d:
            # CR-140: a renamed folder reads as "source missing" when the likelier
            # cause is that the config is stale. Name the sibling that looks like it.
            hint = renamed_to(root, r["dir"]) if r.get("dir") else None
            lines.append(f"  report    {nm[:44]:44} NOT FOUND — {r.get('dir')}"
                         + (f" · config stale? {hint} exists" if hint else ""))
            states.append((nm, r.get("owner"), None, None))
            continue
        # One resolver for which file the declaration names (`vault_report_files`); the
        # two branches below differ only in how that file is DATED -- a `current:` path
        # carries no date in its name, so its mtime is the only answer, while a dated
        # series is dated by its filename.
        got = vault_report_files(d, r)
        if r.get("current") and got and got[0].name == r["current"]:
            age = (today - dt.date.fromtimestamp(got[0].stat().st_mtime)).days
            lines.append(f"  report    {nm[:44]:44} current {r['current']} · "
                         + ("updated today" if age == 0 else f"STALE — last updated {age}d ago"))
            states.append((nm, r.get("owner"), r["current"], age))
            continue
        newest = got[0].name if got else None
        # CR-140: one reader for both dated spellings, so a repo series and a vault
        # series of the same shape cannot be dated by one and called undated by the other.
        when_ = filename_date(newest or "")
        age = (today - when_).days if when_ else None
        lines.append(f"  report    {nm[:44]:44} " + (f"newest {newest}" + (f" · {age}d old" if age is not None else "")
                                                     if newest else "NONE FOUND"))
        states.append((nm, r.get("owner"), newest, age))
    return lines, states


def run(cf: dict, agenda_day: dt.date | None = None):
    """For build_agenda: (headline, path, report_lines) or (None, reason, [])."""
    decl = declared(cf)
    if not decl:
        return None, "no repo with `labels:` declared", [], {}
    try:
        return build(decl, cf.get("movement") or {}, Path(cf["_root"]), agenda_day)
    except Exception as e:
        return None, f"not read — {e}", [], {}


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    from build_agenda import config  # noqa: E402
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="the project's meetings folder (for the config chain)")
    ap.add_argument("--date", help="YYMMDD the agenda is for; stamps STALE when it differs from today")
    a = ap.parse_args()
    cf = config(Path(a.dir).resolve())
    day = dt.datetime.strptime(a.date, "%y%m%d").date() if a.date else None
    head, path, rep, _x = run(cf, day)
    if head is None:
        sys.exit(f"movement: {path}")
    print(head)
    print("\n".join(rep))
    print(f"\nwrote {path}")
