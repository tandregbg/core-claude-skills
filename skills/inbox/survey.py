#!/usr/bin/env python3
"""What is in the inbox: the register, the ledger and the folder, reconciled.

The companion to `skills/outbox/resolved.py --survey`, and written for the same
reason (CR-134): every check that existed asked whether a single item was well
formed, and nothing asked what the whole population looked like or whether it had
moved. On one vault that let 215 of 253 register entries point at files that did
not exist -- 85 % drift -- while the register reported them as waiting to be
processed.

The inbox has one failure mode the outbox cannot have. An outbox manifest lives
*inside* its folder, so the record and the material cannot come apart. The inbox
register is a separate file from the content it describes, so it can drift
silently and did. Hence the three-way reconciliation here: entry, file, outcome.

Read-only, and prints to stdout: it writes no file. Which flags produce which
view (CR-138 -- the shape is contracted in `skills/inbox/SKILL.md`, not only here):

    (no flag)             JSON: the three-way reconciliation above
    --markdown            the same reconciliation as prose -- the situation half
    --table --markdown    the operator-facing task audit: every open entry, one
                          row each, a proposed bucket and an empty `Godta` column
    --undated --markdown  the working list of entries with neither date nor age
    --migration           the context -> venture worksheet, venture column first

Five views, and the flags are not exclusive: `main()` tests them in order, so
`--migration` wins over `--table`, which wins over `--undated`. `--table` and
`--undated` print JSON without `--markdown`; `--migration` never reads that flag
and prints the worksheet either way.

`--markdown` on its own is a situation report; it is `--table` that makes it the
audit the operator decides from. Every open entry appears there exactly once --
a subset under the audit's filename is a regression.
"""
import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

# docs/schemas/inbox.md. `new`, `archived`, `filed`, `keep` and `cancelled` are
# in live use and none of them is declared -- which is the point of listing the
# enum in code rather than in prose (CR-132).
DECLARED = ("pending", "processing", "processed", "skipped")

DATE = re.compile(r"^(\d{2})(\d{2})(\d{2})")


def as_date(v):
    m = DATE.match(str(v or ""))
    if not m:
        return None
    try:
        return date(2000 + int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def age(v, today):
    d = as_date(v)
    return None if d is None else (today - d).days


def is_open_task(task, status_mod):
    return status_mod.is_open(task) if status_mod else task.get("status") == "pending"


def movement(vault, today):
    """What closed today, so a living document shows it moving rather than only its size.

    Counted from `completed:` for finished entries and from a note carrying today's
    stamp for withdrawn ones -- the ledger has no closing date for the latter
    (CR-127 proposes one). Honest about that: a withdrawal without a dated note is
    not counted.
    """
    import yaml
    led = yaml.safe_load((vault / "_inbox" / "_tasks.yaml").read_text(encoding="utf-8"))
    stamp = today.strftime("%y%m%d")
    done = cancelled = 0
    for t in led.get("tasks", []):
        st = str(t.get("status") or "")
        if st == "completed" and str(t.get("completed") or "") == stamp:
            done += 1
        elif st == "cancelled" and any(stamp in str(n) for n in (t.get("notes") or [])):
            cancelled += 1
    return {"closed_today": done, "cancelled_today": cancelled}


def survey(vault: Path, today: date, stale_days: int = 30) -> dict:
    import yaml
    inbox = vault / "_inbox"
    reg = yaml.safe_load((inbox / "_inbox.yaml").read_text(encoding="utf-8"))
    items = reg.get("items", [])

    # --- the register, reconciled three ways -------------------------------
    def locate(i):
        f = str(i.get("file") or "")
        if not f:
            return None
        for base in (inbox, inbox / ".archive"):
            if (base / f).exists():
                return str(base.relative_to(vault))
        at = i.get("archived_to")
        if at and (vault / str(at).lstrip("./")).exists():
            return "archived_to"
        return None

    def has_outcome(i):
        p = i.get("processed") or {}
        return bool(i.get("output_file") or p.get("output_file") or i.get("archived_to"))

    entries = []
    for i in items:
        st = i.get("status")
        entries.append({
            "id": i.get("id"),
            "title": i.get("title"),
            "file": i.get("file"),
            "status": st,
            "declared": st in DECLARED,
            "where": locate(i),
            "outcome": has_outcome(i),
            "age_days": age(i.get("created"), today),
        })
    waiting = [e for e in entries if e["status"] in ("pending", "new", "processing")]

    # --- the task ledger ---------------------------------------------------
    led = yaml.safe_load((inbox / "_tasks.yaml").read_text(encoding="utf-8"))
    try:                                     # the ledger's own status module, if reachable
        sys.path.insert(0, os.path.expanduser("~/repos/vault-tools/todoist-task-pipeline"))
        import task_status
    except Exception:
        task_status = None
    tasks = [t for t in led.get("tasks", []) if is_open_task(t, task_status)]
    undated = [t for t in tasks if not t.get("due")]
    unaged = [t for t in tasks if not t.get("created")]
    orphans = [t for t in undated if not t.get("created")]   # neither date nor age

    def ctx(t):
        c = (t.get("context") or "").lower()
        c = re.split(r"[·—–\-]| \(", c)[0].strip()
        return c or "(ingen kontext)"

    groups = {}
    for t in orphans:
        groups.setdefault(ctx(t), []).append(
            {"id": t["id"], "task": t.get("task", ""), "priority": t.get("priority")})

    # --- the folder: a door, not a dwelling --------------------------------
    resident = {"_capture.md", "_frame.md", "_ideas.md", "_inbox.yaml", "_tasks.yaml",
                "CLAUDE.md", "daglig-triage.md"}
    files = sorted(p.name for p in inbox.iterdir()
                   if p.is_file() and not p.name.startswith("."))
    return {
        "vault": str(vault), "today": today.isoformat(), "stale_days": stale_days,
        "register": {
            "entries": len(entries),
            "waiting": len(waiting),
            "undeclared_status": sorted({e["status"] for e in entries if not e["declared"]}),
            "undeclared_count": sum(1 for e in entries if not e["declared"]),
            "file_missing": sum(1 for e in entries if e["file"] and not e["where"]),
            "no_outcome": sum(1 for e in entries if not e["outcome"]),
            "by_status": {s: sum(1 for e in entries if e["status"] == s)
                          for s in sorted({str(e["status"]) for e in entries})},
            "waiting_items": sorted(waiting, key=lambda e: -(e["age_days"] or 0)),
        },
        "ledger": {
            "open": len(tasks),
            "overdue": sum(1 for t in tasks
                           if as_date(t.get("due")) and as_date(t["due"]) < today),
            "undated": len(undated),
            "no_created": len(unaged),
            "unsortable": len(orphans),
            "groups": {k: v for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))},
        },
        "folder": {
            "files": files,
            "unexpected": [f for f in files if f not in resident],
        },
        "movement": movement(vault, today),
    }


def render(sv: dict) -> str:
    r, l, f = sv["register"], sv["ledger"], sv["folder"]
    out = [f"# Inkorgen — läget {sv['today']}", "",
           "> **Genererad** ur `_inbox/` av `skills/inbox/survey.py --markdown`. Redigera inte",
           "> här: lägesdelen skrivs över vid nästa körning. Besluten hör i auditens `→`-rader.", ""]
    out += ["## Registret (`_inbox.yaml`)", "",
            "| Mått | Antal |", "|---|---|",
            f"| poster | {r['entries']} |",
            f"| **väntar på bearbetning** | **{r['waiting']}** |",
            f"| odeklarerat statusord | **{r['undeclared_count']}** |",
            f"| pekar på en fil som inte finns | **{r['file_missing']}** |",
            f"| utan registrerat utfall | {r['no_outcome']} |", ""]
    if r["undeclared_status"]:
        words = ", ".join(f"`{w}`" for w in r["undeclared_status"])
        out += [f"Odeklarerade ord i bruk: {words}. Enumet i `docs/schemas/inbox.md` är "
                "`pending | processing | processed | skipped`.", ""]
    out += ["| Status | Antal |", "|---|---|"]
    out += [f"| `{k}` | {v} |" for k, v in sorted(r["by_status"].items(), key=lambda kv: -kv[1])]
    out += [""]
    if r["waiting_items"]:
        out += ["### Väntar", "", "| Ålder | Post | Fil |", "|---|---|---|"]
        for e in r["waiting_items"]:
            a = f"{e['age_days']} dgr" if e["age_days"] is not None else "—"
            out.append(f"| {a} | {e['title'] or e['id']} | "
                       f"{'`'+str(e['file'])+'`' if e['file'] else '—'}"
                       f"{'' if e['where'] else ' **saknas**'} |")
        out += [""]
    out += ["## Uppgiftsregistret (`_tasks.yaml`)", "",
            "| Mått | Antal |", "|---|---|",
            f"| öppna | {l['open']} |",
            f"| **förfallna** | **{l['overdue']}** |",
            f"| utan datum | {l['undated']} |",
            f"| utan `created` | {l['no_created']} |",
            f"| **varken datum eller `created`** | **{l['unsortable']}** |", "",
            "De sista går inte att åldersbedöma, sortera eller skriva av — de syns bara för den",
            "som läser hela listan. Grupperade per kontext, störst först:", "",
            "| Kontext | Poster | Id |", "|---|---|---|"]
    for k, v in l["groups"].items():
        ids = " ".join(f"`#{x['id']}`" for x in sorted(v, key=lambda x: x["id"]))
        out.append(f"| **{k}** | {len(v)} | {ids} |")
    out += [""]
    if f["unexpected"]:
        out += ["## Filer i `_inbox/`", "",
                "*Regeln: en dörr, inte en bostad. Arbetsdokument flyttas ut till sitt riktiga hem.*",
                ""]
        out += [f"- `{x}`" for x in f["unexpected"]] + [""]
    return "\n".join(out)


# --- Proposing a bucket -----------------------------------------------------
# A prose heuristic, and labelled as one. It exists so a 129-row list can be
# scanned and accepted in blocks instead of read one entry at a time; the
# operator overrides any row. `sure` marks the rows where the signal is in the
# text itself rather than inferred from its shape.

DONE_MARKS = re.compile(
    r"\b(återkopplade|genomfört|genomförd|hölls|skickad|skickat|signerat|klart|klar|"
    r"avbockad|avklarad|startad|infört|löst|fixat|beslutat|lanserad|redan gjort|"
    r"är gjort|gjordes|blev )", re.IGNORECASE)
IMPERATIVE = re.compile(
    r"^(ring|ringa|messa|mejla|maila|skicka|boka|köp|köpa|kolla|hämta|fråga|följ|"
    r"följa|gå igenom|gå|sätt|sätta|skriv|skriva|ta |ta\b|få |få\b|bestäm|bestämma|"
    r"förbered|förbereda|avgör|avgöra|lägg|lägga|flytta|rätta|rensa|städa|uppdatera|"
    r"verifiera|kontrollera|stäm|stämma|hör |höra|svara|planera|undersök|undersöka|"
    r"installera|committa|pusha|avaktivera|arkivera|signera|slutför|slutföra|bevaka|"
    r"bygg|bygga|dema|exportera|kvantifiera|normalisera|peka|konvertera|döp|byt|byta)",
    re.IGNORECASE)
TOPIC = re.compile(r"^[A-ZÅÄÖ][\wåäöÅÄÖ\-/ ]{0,40}$")


def propose(row: dict, context: str, today: date) -> tuple[str, bool, str]:
    """(bucket, sure, why) for one ledger entry."""
    text = (row.get("task") or "").strip()
    first = text.split("\n")[0]

    # A context that names a date the world has passed.
    m = re.search(r"(\d{1,2})/(\d{1,2})\b", context or "")
    if m:
        try:
            d = date(today.year, int(m.group(2)), int(m.group(1)))
            if (today - d).days > 14:
                return ("ÖVERSPELAD", True,
                        f"kontexten pekar på {m.group(0)}, {(today - d).days} dagar sedan")
        except ValueError:
            pass

    hit = DONE_MARKS.search(text)
    if hit:
        return ("ÖVERSPELAD", True, f"texten säger ”{hit.group(0).strip()}” — formulerad i dåtid")

    if IMPERATIVE.match(first):
        return ("GÖRA", True, "börjar med en handling")

    if len(first) <= 45 and TOPIC.match(first) and not first.endswith(("?", ":")):
        return ("REFERENS", True, "ämne utan handling")

    if row.get("priority"):
        return ("GÖRA", False, f"har prio {row['priority']} men ingen tydlig handling")

    if "?" in first:
        return ("REFERENS", False, "en fråga, inte en uppgift")

    return ("GÖRA", False, "ingen tydlig signal — läs raden")


def propose_for(state: str, row: dict, today: date) -> tuple[str, bool, str]:
    """The bucket to offer, which depends on the state the entry is in."""
    text = (row.get("task") or "").strip()
    first = text.split("\n")[0]
    hit = DONE_MARKS.search(text)
    imp = bool(IMPERATIVE.match(first))

    if state == "FÖRFALLNA":
        if hit:
            return ("AVSKRIV", True, f"texten säger ”{hit.group(0).strip()}”")
        if (row["age_days"] or 0) > 30:
            return ("NYTT DATUM", False, f"{row['age_days']} dagar sen — datumet är inte sant längre")
        return ("NYTT DATUM", False, "förfallen; sätt om eller avskriv")

    if state == "DATERADE FRAMÅT":
        return ("LÅT STÅ", True, "daterad framåt")

    if state == "ODATERADE MED PRIO":
        if hit:
            return ("AVSKRIV", True, f"texten säger ”{hit.group(0).strip()}”")
        if row.get("priority") in ("P0", "P1"):
            return ("SÄTT DATUM", True, "P0/P1 utan datum bryter mot _config/priority.md")
        return ("SÄTT DATUM", False, f"{row['priority']} utan datum — syns inte i vyn")

    # ODATERADE och UTAN DATUM OCH UTAN ÅLDER
    m = re.search(r"(\d{1,2})/(\d{1,2})\b", row.get("context_full") or "")
    if m:
        try:
            d = date(today.year, int(m.group(2)), int(m.group(1)))
            if (today - d).days > 14:
                return ("AVSKRIV", True,
                        f"kontexten pekar på {m.group(0)}, {(today - d).days} dagar sedan")
        except ValueError:
            pass
    if hit:
        return ("AVSKRIV", True, f"texten säger ”{hit.group(0).strip()}”")
    if imp:
        return ("SÄTT DATUM", True, "börjar med en handling")
    if len(first) <= 45 and TOPIC.match(first) and not first.endswith(("?", ":")):
        return ("REFERENS", True, "ämne utan handling")
    if "?" in first:
        return ("REFERENS", False, "en fråga, inte en uppgift")
    return ("SÄTT DATUM", False, "ingen tydlig signal — läs raden")


STATE_NOTE = {
    "FÖRFALLNA": "Datumet har passerat. Antingen är uppgiften gjord, eller är datumet inte sant längre.",
    "ODATERADE MED PRIO": "Prio satt men inget datum. En post utan datum kan aldrig vara P0/P1 "
                          "(`_config/priority.md`), och utan datum syns den inte i triagen.",
    "ODATERADE": "Har `created` men inget datum — går att åldersbedöma, men driver inget.",
    "UTAN DATUM OCH UTAN ÅLDER": "Varken datum eller `created`. Går inte att sortera, påminna om "
                                 "eller skriva av. Den svåraste gruppen.",
    "DATERADE FRAMÅT": "Ligger rätt. Listade för fullständighetens skull.",
}
ORDER = ["FÖRFALLNA", "ODATERADE MED PRIO", "UTAN DATUM OCH UTAN ÅLDER", "ODATERADE",
         "DATERADE FRAMÅT"]


def venture_map(vault):
    """The operator's decided context -> venture map, if the vault declares one.

    `_config/verksamhet-karta.yaml`: the eight ventures of `_INDEX-verksamheter.md`
    plus three working states (`per-post`, `oklart`, `ej-namngiven`). Declared in
    the vault rather than in this code, because the ventures are the operator's and
    this tool only reports them.
    """
    import yaml
    f = vault / "_config" / "verksamhet-karta.yaml"
    if not f.is_file():
        return {}
    d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    return {str(k).strip().lower(): v for k, v in (d.get("karta") or {}).items()}


def portfolio_projects(vault):
    """Project names from the portfolio table, for validating `projekt:`."""
    f = vault / "_INDEX-projekt.md"
    if not f.is_file():
        return {}
    s = f.read_text(encoding="utf-8")
    try:
        sec = s[s.index("## PORTFÖLJEN"):s.index("### Sammanräkning")]
    except ValueError:
        sec = s
    out = {}
    for line in sec.split("\n"):
        if not (line.startswith("| ") and line.count("|") >= 7 and "---" not in line):
            continue
        cells = [c.strip() for c in line.split("|")]
        name = re.sub(r"[*└_ ]", "", cells[1]).strip()
        if not name or name == "Projekt":
            continue
        out[re.sub(r"[^a-z0-9åäö]", "", name.lower())] = cells[1].strip(" *└")
    return out


def match_project(ctx, projects):
    """A context matches a portfolio row when one is a prefix of the other.

    Prefix rather than equality: a context reads `goa` where the portfolio row is
    `Goa 2026`. Equality matched 2 of 50 values on one vault; prefix is what makes
    the field checkable in both directions.
    """
    key = re.sub(r"[^a-z0-9åäö]", "", (ctx or "").lower())
    if not key:
        return None
    if len(key) < 3:
        # Too short to be a prefix of anything, but a row that short ('Ål') matches itself.
        return next((n for k, n in projects.items() if k == key), None)
    for pkey, name in projects.items():
        if pkey == key or pkey.startswith(key) or key.startswith(pkey):
            return name
    return None


def render_living(vault, sv: dict, states: dict, today: date) -> str:
    """One living view of the ledger: venture, then context, then the entries.

    Replaces two documents that covered the same entries in two groupings -- one by
    state, one by venture -- which is duplication, not two views. The venture is the
    operator's primary attribute; the state travels with each row instead of
    deciding the sections.
    """
    vmap = venture_map(vault)
    projects = portfolio_projects(vault)
    OBJ = {"rutin": "Löpande ansvar", "väntar": "Löpande ansvar (bevakning)", "idé": "Idé",
           "reflektion": "Note / logg", "uppföljning": "ärendetyp", "samtal": "ärendetyp",
           "möte": "ärendetyp", "kontakt": "ärendetyp", "kolla": "ärendetyp",
           "uppföljningspunkter": "ärendetyp", "att kategorisera": "okategoriserad"}
    STATE = {"FÖRFALLNA": "förfallen", "ODATERADE MED PRIO": "prio utan datum",
             "UTAN DATUM OCH UTAN ÅLDER": "ingen ålder", "ODATERADE": "odaterad",
             "DATERADE FRAMÅT": "framåt"}
    rows = []
    for st, items in states.items():
        for r in items:
            ctx = re.split(r"\s*·\s*", (r.get("context_full") or "").strip())[0].lower() or "(tomt)"
            rows.append({**r, "_state": st, "_ctx": ctx,
                         "_v": vmap.get(ctx) or "**?**",
                         "_prop": propose_for(st, r, today)})
    UNSET = ("kontextstyrd", "oklart", "ej-namngiven", "**?**")
    STATE_ORDER = {"Personligt": 1, "kontextstyrd": 2, "oklart": 3, "ej-namngiven": 3}
    by_v = {}
    for r in rows:
        by_v.setdefault(r["_v"], {}).setdefault(r["_ctx"], []).append(r)

    mv = sv.get("movement") or {}
    moved = mv.get("closed_today", 0) + mv.get("cancelled_today", 0)
    l = sv["ledger"]
    out = [f"# Uppgifter — levande vy, {sv['today']}", "",
           "> **Genererad** ur `_inbox/_tasks.yaml`, `_config/verksamhet-karta.yaml` och",
           "> PORTFÖLJEN. Samma filnamn varje gång: håll den öppen. Kör om med",
           "> `survey.py --vault \"$VAULT\" --table --markdown`.", "",
           "**Verksamhet först, sedan kontext.** Tillståndet (förfallen, ingen ålder …) följer",
           "med varje rad i stället för att bestämma sektionerna.", ""]
    if moved:
        out += [f"**I dag: {mv.get('closed_today',0)} avbockade, "
                f"{mv.get('cancelled_today',0)} avskrivna — {moved} poster ur registret.**", ""]
    tally = {}
    for r in rows:
        tally[r["_prop"][0]] = tally.get(r["_prop"][0], 0) + 1
    sure = sum(1 for r in rows if r["_prop"][1])
    out += [f"**{l['open']} öppna poster.** Förslagen: "
            + " · ".join(f"**{v} {k}**" for k, v in sorted(tally.items(), key=lambda kv: -kv[1]))
            + f". **{sure}** har signalen i texten (✓), {len(rows)-sure} är gissningar (?).", "",
            "**Godta:** tom = förslaget gäller. Datum (`261027`) · `R` referens · `Ö` avskriv · `S` låt stå.",
            ""]
    out += ["| Verksamhet | Poster | Varav att läsa |", "|---|---|---|"]
    for v in sorted(by_v, key=lambda x: (STATE_ORDER.get(x, 0), x)):
        n = sum(len(i) for i in by_v[v].values())
        unread = sum(1 for cs in by_v[v].values() for r in cs if not r["_prop"][1])
        label = {"kontextstyrd": "— *(kontextstyrda)*", "oklart": "*obeslutade*",
                 "ej-namngiven": "*ej namngivna*", "**?**": "*utan karta*"}.get(v, f"**{v}**")
        out.append(f"| {label} | {n} | {unread} |")
    out += ["", "---", ""]

    for v in sorted(by_v, key=lambda x: (STATE_ORDER.get(x, 0), x)):
        cs = by_v[v]
        n = sum(len(i) for i in cs.values())
        head = {"kontextstyrd": "Kontextstyrda — ärendetypen är det primära",
                "oklart": "Obeslutad verksamhet", "ej-namngiven": "Kom inte upp i genomgången",
                "**?**": "Utan post i kartan"}.get(v, v)
        out += [f"## {head} — {n} poster", ""]
        if v == "kontextstyrd":
            out += ["*Hör inte till någon affär. Tom verksamhet är ett svar, inte en lucka.*", ""]
        elif v == "Fria projekt":
            out += ["*Byggt för egen räkning — beslutstestets steg 7. Inte Personligt, som är livet.*", ""]
        for ctx, items in sorted(cs.items(), key=lambda kv: -len(kv[1])):
            pr = match_project(ctx, projects)
            ot = OBJ.get(ctx, "")
            h = f"### `{ctx}` — {len(items)}"
            if pr:
                h += f" · projekt **{pr}**"
            if ot:
                h += f" · *{ot}*"
            out += [h, "",
                    "| # | Verksamhet | Projekt | Läge | Uppgift | Förslag | | Godta |",
                    "|---|---|---|---|---|---|---|---|"]
            for r in sorted(items, key=lambda r: (-(r.get("age_days") or 0), r["id"])):
                b, s_, _w = r["_prop"]
                t = " ".join((r.get("task") or "").split())
                t = t[:70].rsplit(" ", 1)[0] + "…" if len(t) > 70 else t
                pri = f" `{r['priority']}`" if r.get("priority") else ""
                st = STATE.get(r["_state"], r["_state"])
                age = f"{r['age_days']} d" if r.get("age_days") else (r.get("due") or "")
                lage = f"{st} {age}".strip()
                # Verksamhet och projekt per rad, aven nar de upprepas: en rad ska ga att
                # lasa och besluta om utan att forst lasa rubriken ovanfor (operator, 261020).
                vcell = "—" if v in UNSET else v
                pcell = pr or "—"
                out.append(f"| `#{r['id']}`{pri} | {vcell} | {pcell} | {lage} | {t} | "
                           f"**{b}** | {'✓' if s_ else '?'} | |")
            out += [""]
    return "\n".join(out)



def render_undated(sv: dict, detail: dict) -> str:
    """The full, working list of ledger entries that carry neither a date nor an age.

    Replaces a hand-written file that had to be re-verified by hand each time it
    was opened: on 2026-10-20 the counts in its header were thirteen days old and
    seven of the entries it listed had been closed since. The grouping, the test
    and the three buckets are its own -- only the measuring is new.
    """
    l = sv["ledger"]
    out = [f"# Odaterade poster — {sv['today']}", "",
           "> **Genererad** ur `_inbox/_tasks.yaml` av `skills/inbox/survey.py --undated --markdown`.",
           "> Sortera i filen om du vill, men skriv besluten i",
           "> [`261020-audit-inkorg.md`](261020-audit-inkorg.md) — den här skrivs över vid nästa körning.",
           "",
           f"**{l['unsortable']} poster** har varken `due` eller `created`. Av {l['open']} öppna är",
           f"{l['undated']} odaterade och {l['no_created']} saknar `created`; det är skärningen som",
           "listas här.", "",
           "**Felet är inte att de är många.** Utan `created` kan ingen åldersregel tillämpas, ingen",
           "vy sortera dem och ingen påminnelse utlösas. De syns bara för den som läser hela listan,",
           "vilket ingen gör. Städningen är engångsarbete; att fältet kan utelämnas vid skapandet är",
           "det som bygger upp högen igen.", "",
           "---", "",
           "## Så här går genomgången", "",
           "Tre hinkar per post. Ta dem gruppvis, inte i id-ordning.", "",
           "| Hink | Innebär | Vad som händer |", "|---|---|---|",
           "| **GÖRA** | Ska faktiskt göras | Får **datum** och prioritet. Utan datum hamnar den här igen |",
           "| **REFERENS** | Värt att minnas, ingen åtgärd | Flyttas **ut ur `_tasks.yaml`** till `_ideas.md` eller rätt projektmapp |",
           "| **ÖVERSPELAD** | Gjord, obsolet eller tappad | Avskrivs med skäl |", "",
           "**Testet för REFERENS:** finns det en handling med ett slut? *\"Messa Ola Gravenfors\"* är",
           "en handling. *\"Bolagen, bolagsstrukturen och tankar framåt\"* är ett ämne — det hör inte i",
           "ett uppgiftsregister.", "", "---", ""]
    for ctx, rows in detail.items():
        out += [f"## {ctx} — {len(rows)} poster", ""]
        for r in rows:
            pri = f" `{r['priority']}`" if r.get("priority") else ""
            out.append(f"### `#{r['id']}`{pri}")
            out.append("")
            out.append(r["task"].strip())
            if r.get("context_full") and r["context_full"].lower() != ctx:
                out.append("")
                out.append(f"*Kontext: {r['context_full']}*")
            if r.get("notes"):
                out.append("")
                out.append(f"*{len(r['notes'])} not{'' if len(r['notes'])==1 else 'er'} i registret.*")
            out += ["", "- [ ] GÖRA — datum: ______  prio: ____", "- [ ] REFERENS — till: ______",
                    "- [ ] ÖVERSPELAD — skäl: ______", ""]
    return "\n".join(out)


def all_open(vault, today):
    """Every open ledger entry, bucketed by the state it is actually in.

    `undated_detail` covered only the entries with neither date nor age -- the
    hardest group, but 129 of 292. A sweep of the register needs all of them, and
    the proposal differs by state: an overdue entry needs a new date or a reason,
    a dateless one needs a date or a different home.
    """
    import yaml, os, sys as _s
    led = yaml.safe_load((vault / "_inbox" / "_tasks.yaml").read_text(encoding="utf-8"))
    try:
        _s.path.insert(0, os.path.expanduser("~/repos/vault-tools/todoist-task-pipeline"))
        import task_status
    except Exception:
        task_status = None
    states = {"FÖRFALLNA": [], "DATERADE FRAMÅT": [], "ODATERADE MED PRIO": [],
              "ODATERADE": [], "UTAN DATUM OCH UTAN ÅLDER": []}
    for t in led.get("tasks", []):
        if not is_open_task(t, task_status):
            continue
        d = as_date(t.get("due"))
        row = {"id": t["id"], "task": t.get("task", ""), "priority": t.get("priority"),
               "context_full": t.get("context"), "notes": t.get("notes") or [],
               "due": t.get("due"), "created": t.get("created"),
               "age_days": (today - d).days if d and d < today else None}
        if d and d < today:
            states["FÖRFALLNA"].append(row)
        elif d:
            states["DATERADE FRAMÅT"].append(row)
        elif not t.get("created"):
            states["UTAN DATUM OCH UTAN ÅLDER"].append(row)
        elif t.get("priority"):
            states["ODATERADE MED PRIO"].append(row)
        else:
            states["ODATERADE"].append(row)
    for k in states:
        states[k].sort(key=lambda r: (-(r["age_days"] or 0), r["id"]))
    return {k: v for k, v in states.items() if v}


def ctx_of(row):
    c = (row.get("context_full") or "").lower()
    c = re.split(r"[·—–\-]| \(", c)[0].strip()
    return c or "(ingen kontext)"


def undated_detail(vault, today):
    """Kept for `--undated`: only the entries with neither date nor age."""
    rows = {}
    for r in all_open(vault, today).get("UTAN DATUM OCH UTAN ÅLDER", []):
        rows.setdefault(ctx_of(r), []).append(r)
    for c in rows:
        rows[c].sort(key=lambda r: r["id"])
    return {k: v for k, v in sorted(rows.items(), key=lambda kv: (-len(kv[1]), kv[0]))}


def render_migration(vault, today, states) -> str:
    """The context migration worksheet, ordered venture first.

    Column order is the operator's: **venture, then context, then project.** The
    venture is the attribute that decides where a thing belongs; the context is
    what the ledger happens to say today; the project is optional and only exists
    when the portfolio has a row. Ordering it any other way put the least decided
    column first and read as noise (the maintainer, 2026-10-20).
    """
    vmap = venture_map(vault)
    projects = portfolio_projects(vault)
    OBJ = {"rutin": "Löpande ansvar", "väntar": "Löpande ansvar (bevakning)", "idé": "Idé",
           "reflektion": "Note / logg", "uppföljning": "ärendetyp", "samtal": "ärendetyp",
           "möte": "ärendetyp", "kontakt": "ärendetyp", "kolla": "ärendetyp",
           "uppföljningspunkter": "ärendetyp", "att kategorisera": "okategoriserad"}
    rows = {}
    for st, items in states.items():
        for r in items:
            first = re.split(r"\s*·\s*", (r.get("context_full") or "").strip())[0].lower() or "(tomt)"
            rows.setdefault(first, []).append(r)
    # Personligt sist bland verksamheterna ("livet, inte affären" — _INDEX-verksamheter.md),
    # sedan de kontextstyrda, sedan det obeslutade.
    STATE_ORDER = {"Personligt": 1, "kontextstyrd": 2, "oklart": 3, "ej-namngiven": 3}
    def sort_key(kv):
        ctx, items = kv
        v = vmap.get(ctx, "")
        return (STATE_ORDER.get(v, 0), -len(items), ctx)
    body, groups = [], {}
    for ctx, items in sorted(rows.items(), key=sort_key):
        v = vmap.get(ctx) or "**?**"
        groups.setdefault(v, []).append((ctx, items))
    out = [f"# Migrering: kontext → verksamhet · projekt — {today.isoformat()}", "",
           "> **Genererad** ur `_inbox/_tasks.yaml`, `_config/verksamhet-karta.yaml` och",
           "> PORTFÖLJEN i `_INDEX-projekt.md`. Besluten bor i kartan, inte här: ändra där och",
           "> kör om. Normkällor: `_INDEX-objektmodell.md` (sju objekttyper),",
           "> `_INDEX-verksamheter.md` (åtta verksamheter).", "",
           "**Kolumnordning:** verksamhet först, sedan kontext, sedan projekt. Verksamheten är",
           "det attribut som avgör var en sak hör; kontexten är vad registret råkar säga i dag.", ""]
    tot = sum(len(i) for _, i in rows.items())
    UNSET = ("kontextstyrd", "oklart", "ej-namngiven", "**?**")
    decided = sum(len(i) for v, gs in groups.items() for _, i in gs if v not in UNSET)
    ctxled = sum(len(i) for _, i in groups.get("kontextstyrd", []))
    out += [f"**{len(rows)} kontextvärden över {tot} öppna poster.** "
            f"{decided} har en verksamhet, {ctxled} är kontextstyrda "
            f"(ärendetypen är det primära — verksamhet kan saknas och det är korrekt), "
            f"{tot - decided - ctxled} är obeslutade.", ""]
    for v in sorted(set(groups), key=lambda x: (STATE_ORDER.get(x, 0), x)):
        gs = groups[v]
        n = sum(len(i) for _, i in gs)
        label = {"kontextstyrd": "Kontextstyrda — ärendetypen är det primära attributet",
                 "oklart": "Obeslutade",
                 "ej-namngiven": "Kom inte upp i genomgången"}.get(v, v)
        out += [f"## {label} — {n} poster", ""]
        if v == "kontextstyrd":
            out += ["*Dessa hör inte till någon affär. Att verksamhetskolumnen är tom är ett",
                    "svar, inte en lucka — `_INDEX-verksamheter.md` binder en verksamhet till",
                    "*vems affär*, och en uppföljning eller en bevakning är ingens.*", ""]
        elif v == "Fria projekt":
            out += ["*Byggt för egen räkning, ingen såld produkt — beslutstestets steg 7 i",
                    "`_INDEX-verksamheter.md`. Skilt från Personligt, som är livet utan affär.*", ""]
        for ctx, items in sorted(gs, key=lambda kv: -len(kv[1])):
            pr = match_project(ctx, projects)
            ot = OBJ.get(ctx, "")
            head = f"### `{ctx}` — {len(items)} poster"
            if pr:
                head += f" · projekt **{pr}**"
            if ot:
                head += f" · *{ot}*"
            out += [head, "",
                    "| # | Ålder | Uppgift | Godta |", "|---|---|---|---|"]
            for r in sorted(items, key=lambda r: (-(r.get("age_days") or 0), r["id"])):
                t = " ".join((r.get("task") or "").split())
                t = t[:96].rsplit(" ", 1)[0] + "…" if len(t) > 96 else t
                pri = f" `{r['priority']}`" if r.get("priority") else ""
                a = (f"{r['age_days']} d" if r.get("age_days")
                     else (r.get("due") or ("—" if r.get("created") else "ingen ålder")))
                out.append(f"| `#{r['id']}`{pri} | {a} | {t} | |")
            out += [""]
    objrows = [c for c in rows if c in OBJ]
    out += ["---", "",
            "## Vad kartan visar", "",
            f"- **{len(rows)} kontextvärden** över {tot} öppna poster.",
            f"- **{decided} poster** har en avgjord verksamhet, **{tot - decided}** väntar.",
            f"- **{sum(1 for c in rows if match_project(c, projects))} av {len(rows)}** värden "
            "matchar en rad i PORTFÖLJEN och kan därmed bära ett `projekt:`.",
            f"- **{len(objrows)} värden är inte kategorier** utan andra objekttyper eller "
            "ärendetyper, och bryter järnregel 1: "
            + ", ".join(f"`{c}`" for c in sorted(objrows)) + ".", "",
            "Järnregel 2 säger att de märks om och flyttas — aldrig raderas.", ""]
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vault", help="vault root (default: $VAULT_ROOT or cwd)")
    ap.add_argument("--today", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--markdown", action="store_true",
                    help="render the selected view as markdown; alone, the situation half")
    ap.add_argument("--stale-days", type=int, default=30)
    ap.add_argument("--migration", action="store_true",
                    help="the context -> venture worksheet, venture column first")
    ap.add_argument("--table", action="store_true",
                    # CR-138: with --markdown this is the operator-facing audit, and it
                    # covers every open entry -- not only the undated ones.
                    help="every open entry as one row each, with a proposed bucket")
    ap.add_argument("--undated", action="store_true",
                    help="the full working list of entries with neither date nor age")
    a = ap.parse_args(argv)
    root = Path(a.vault or os.environ.get("VAULT_ROOT") or ".").expanduser().resolve()
    if not (root / "_inbox").is_dir():
        print(f"no _inbox at {root}", file=sys.stderr)
        return 2
    today = date.fromisoformat(a.today) if a.today else date.today()
    sv = survey(root, today, a.stale_days)
    if a.migration:
        states = all_open(root, today)
        print(render_migration(root, today, states))
        return 0
    if a.table:
        states = all_open(root, today)
        print(render_living(root, sv, states, today) if a.markdown
              else json.dumps(states, ensure_ascii=False, indent=2))
        return 0
    if a.undated:
        detail = undated_detail(root, today)
        print(render_undated(sv, detail) if a.markdown
              else json.dumps(detail, ensure_ascii=False, indent=2))
        return 0
    print(render(sv) if a.markdown else json.dumps(sv, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
