#!/usr/bin/env python3
"""Mechanical parts of /company (CR-125): create the skeleton, check a profile. Report only.

    python3 company_tool.py init <org-folder> --vertical <v> [--level basic] [--language en] [--display Name]
    python3 company_tool.py check <vault-or-org-folder> [--max-age-days 365] [--json] [--copies]

`init` writes `<org>/_company/` with the plain skeleton for the level and refuses to touch an existing
folder. It carries no questions: a question set comes from an optional template (`company.template:`).

`check` finds every `_company/` below the folder and reports, never rewrites:

  stale       a facet file not reviewed or generated within max_age_days, or status `stale`
  schema      sources.yaml / brands.yaml against docs/schemas/company-*.schema.json; frontmatter keys and enums
  unsourced   a facet marked draft-locked or final that lists no sources
  credential  a value that looks like a key, token or password (a reference such as env:NAME is fine)
  copy        (--copies) a profile file outside any `_company/`, found by name and frontmatter

Judgement checks that need reading (a status claim with no recent evidence, a fact without a source marker)
are done by the agent in `/company check`; this script covers what a program can decide.
Dot-folders are never walked.
"""
import argparse, datetime, json, re, sys, unicodedata
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("needs pyyaml -- run with a python that has it")

HERE = Path(__file__).resolve().parent
SCHEMAS = HERE.parents[1] / "docs" / "schemas"

FACETS = ["essence", "company", "offering", "positioning", "messaging", "gtm", "strategy", "brand", "public"]
LEVELS = ["public", "basic", "standard", "complete"]
STATUSES = ["draft", "synthesis-locked", "draft-locked", "final", "stale"]
FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)
SECRET = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{16,}"),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*[\"']?(?!env:|op:|<)[A-Za-z0-9/+_.=-]{16,}"),
    re.compile(r"\b[A-Fa-f0-9]{40,}\b"),
]


# ---------------------------------------------------------------- small JSON-schema subset
def _types(v, t):
    return {"string": isinstance(v, str), "boolean": isinstance(v, bool), "array": isinstance(v, list),
            "object": isinstance(v, dict), "integer": isinstance(v, int) and not isinstance(v, bool)}[t]


def validate(value, schema, root, path="", out=None):
    """The subset the two schemas use: $ref, type, enum, const, pattern, minLength, required, properties,
    additionalProperties, items, uniqueItems, oneOf, format: date."""
    out = [] if out is None else out
    if "$ref" in schema:
        node = root
        for part in schema["$ref"].lstrip("#/").split("/"):
            node = node[part]
        return validate(value, node, root, path, out)
    where = path or "<root>"
    if "oneOf" in schema:
        if sum(1 for s in schema["oneOf"] if not validate(value, s, root, path, [])) != 1:
            if isinstance(value, list) and any(isinstance(x, bool) for x in value):
                out.append(f"{where}: {value!r} holds a YAML boolean; quote the codes (unquoted no, on, off, yes, y, n become booleans)")
                return out
            out.append(f"{where}: {value!r} is not one of the allowed forms")
        return out
    if "const" in schema and value != schema["const"]:
        out.append(f"{where}: must be {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{where}: {value!r} is not one of {schema['enum']}")
    t = schema.get("type")
    if t == "string" and isinstance(value, bool):
        out.append(f"{where}: {value!r} is a YAML boolean, not a string; quote it (unquoted no, on, off, yes, y, n become booleans)")
        return out
    if t and not _types(value, t):
        out.append(f"{where}: {value!r} is not of type {t}")
        return out
    if t == "integer" and "minimum" in schema and value < schema["minimum"]:
        out.append(f"{where}: {value!r} is below {schema['minimum']}")
    if t == "string":
        if "minLength" in schema and len(value) < schema["minLength"]:
            out.append(f"{where}: empty")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            out.append(f"{where}: {value!r} does not match {schema['pattern']}")
        if schema.get("format") == "date" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            out.append(f"{where}: {value!r} is not a date (YYYY-MM-DD)")
    if t == "object":
        for r in schema.get("required", []):
            if r not in value:
                out.append(f"{where}: {r!r} is required")
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                validate(v, props[k], root, f"{path}/{k}", out)
            elif schema.get("additionalProperties") is False:
                out.append(f"{where}: unexpected key {k!r}")
    if t == "array":
        if schema.get("uniqueItems") and len({json.dumps(x, sort_keys=True) for x in value}) != len(value):
            out.append(f"{where}: items are not unique")
        for i, x in enumerate(value):
            if "items" in schema:
                validate(x, schema["items"], root, f"{path}/{i}", out)
    return out


def load_yaml_json(path):
    # dates become strings so the schema's string checks apply
    return json.loads(json.dumps(yaml.safe_load(path.read_text(encoding="utf-8")), default=str))


# ---------------------------------------------------------------- finding helpers
def finding(kind, file, message, line=None):
    f = {"kind": kind, "file": str(file), "message": message}
    if line:
        f["line"] = line
    return f


def frontmatter(path):
    m = FM.match(path.read_text(encoding="utf-8", errors="replace"))
    if not m:
        return None
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def as_date(v):
    if isinstance(v, datetime.date):
        return v
    if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v.strip()):
        return datetime.date.fromisoformat(v.strip())
    return None


def find_company_dirs(root):
    found = []
    def walk(d, depth):
        if depth > 5:
            return
        for p in sorted(d.iterdir()):
            if not p.is_dir() or p.name.startswith(".") or p.name == "node_modules":
                continue
            if p.name == "_company":
                found.append(p)
            else:
                walk(p, depth + 1)
    if root.name == "_company":
        return [root]
    walk(root, 0)
    return found


# ---------------------------------------------------------------- checks
LOCAL_MARK = re.compile(r"\[(s\d+)\]")
REG_MARK = re.compile(r"\[(s-[a-z0-9][a-z0-9-]*)\]")
LOCAL_DEF = re.compile(r"(?:^|;)\s*(?:[-*]\s*)?\[(s\d+)\]\s+\S", re.M)


def register_ids(d):
    """Ids declared in sources.yaml, or None when it cannot be read (the schema check reports that)."""
    try:
        return {x.get("id") for x in load_yaml_json(d / "sources.yaml").get("sources", [])}
    except Exception:  # noqa: BLE001
        return None


def check_markers(p, fm, ids):
    """A local [sN] needs a line in the same file that defines it; [s-id] and frontmatter s- entries need the register."""
    text = p.read_text(encoding="utf-8", errors="replace")
    body = text[FM.match(text).end():] if FM.match(text) else text
    out = []
    defined = set(LOCAL_DEF.findall(body))
    for m in sorted(set(LOCAL_MARK.findall(body)) - defined, key=lambda x: int(x[1:])):
        out.append(finding("marker", p, f"[{m}] is used but no line in the file defines it (a Sources list entry starting [{m}])"))
    if ids is not None:
        for m in sorted(set(REG_MARK.findall(body)) - ids):
            out.append(finding("marker", p, f"[{m}] is not declared in sources.yaml"))
        for s in fm.get("sources") or []:
            if isinstance(s, str) and re.fullmatch(r"s-[a-z0-9][a-z0-9-]*", s) and s not in ids:
                out.append(finding("marker", p, f"frontmatter source {s} is not declared in sources.yaml"))
    return out


H1 = re.compile(r"^# (.+?) -- ([a-z]+)\s*$", re.M)
OPEN = re.compile(r"_Not provided yet\._|\(gap\)|\(No source found|\(Ingen källa hittad")
DECISION = re.compile(r"\*\*Decision needed:\*\*|\*\*Beslut krävs:\*\*|\((?:beslut krävs|decision needed)", re.I)


def summarise(d):
    """Per facet: open items and decisions waiting for the owner. A count, not a finding."""
    rows = []
    for facet in FACETS:
        for p in sorted(d.glob(f"{facet}-*.md")):
            t = p.read_text(encoding="utf-8", errors="replace")
            rows.append((facet, len(OPEN.findall(t)), len(DECISION.findall(t))))
    return rows


def check_names(d):
    """The H1 of a facet file is `# <Display name> -- <facet>` (facet in English), same display name everywhere."""
    names, out = {}, []
    for p in sorted(d.glob("*.md")):
        fm = frontmatter(p) or {}
        facet = fm.get("facet")
        if facet not in FACETS:
            continue
        m = re.search(r"^# (.+)$", p.read_text(encoding="utf-8", errors="replace"), re.M)
        mm = H1.match(m.group(0)) if m else None
        if not mm or mm.group(2) != facet:
            out.append(finding("name", p, f"H1 should read '# <Display name> -- {facet}'"))
        else:
            names.setdefault(unicodedata.normalize("NFC", mm.group(1)), []).append(p)
    if len(names) > 1:
        main = max(names, key=lambda k: len(names[k]))
        out += [finding("name", ps[0], f"H1 display name {n!r} differs from {main!r} used in most files")
                for n, ps in names.items() if n != main]
    return out


SID = re.compile(r"s-[a-z0-9][a-z0-9-]*")
DEC_OLD = re.compile(r"Decision for the owner:|\((?:beslut krävs|decision needed)|Beslut krävs:", re.I)
DEC_NEW = re.compile(r"\*\*Decision needed:\*\*(.*)")


def check_strict(d):
    """The structure the overview graph needs (contract section 8). Off by default: `check --strict`."""
    out = []
    srcs, feeds = {}, {}
    try:
        for x in load_yaml_json(d / "sources.yaml").get("sources", []):
            srcs[x["id"]] = x
    except Exception:  # noqa: BLE001 - the schema check reports an unreadable register
        return out
    for sid, x in srcs.items():
        p = d / "sources.yaml"
        if "curation" not in x:
            out.append(finding("provenance", p, f"{sid} does not say whether it is an original, derived or curated (curation:)"))
        elif x["curation"] != "original" and not x.get("derived_from"):
            out.append(finding("provenance", p, f"{sid} is {x['curation']} but names no derived_from"))
        if x.get("derived_from", "").startswith("s-") and x["derived_from"] not in srcs:
            out.append(finding("provenance", p, f"{sid}: derived_from {x['derived_from']} is not declared in sources.yaml"))
        if x.get("authority") == "binding" and not x.get("decided_by"):
            out.append(finding("provenance", p, f"{sid} is binding but names no decided_by (a binding source records a decision by the company)"))
        if x.get("authority") == "binding" and x.get("curation") in ("derived", "curated"):
            out.append(finding("provenance", p, f"{sid} is {x['curation']} and cannot be binding; the original or the company's own decision is"))
    readme = d / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8", errors="replace")
        if any(x.get("pages") for x in srcs.values()) and not re.search(r"^## Reviewer notes and extraction losses", text, re.M):
            out.append(finding("provenance", readme, "paged originals are used, so README needs '## Reviewer notes and extraction losses'"))
        m = re.search(r"^## Conflicts?\b.*?$(.*?)(?=^## |\Z)", text, re.S | re.M)
        for line in (m.group(1).split("\n") if m else []):
            s = line.strip()
            cell = re.match(r"^\|\s*([^|]*?)\s*\|", s)
            first = cell.group(1) if cell else None
            if first is not None and not re.fullmatch(r"C?\d+", first):
                continue                       # table header, separator or a row that is not a register entry
            if first is None and not s.startswith("- "):
                continue
            ident = first if first is not None else (re.match(r"^- (\S+)", s).group(1) if re.match(r"^- (\S+)", s) else "")
            if not re.fullmatch(r"C\d+", ident):
                out.append(finding("graph", readme, f"conflict {ident!r} is not written C<n>: {s[:60]}"))
                continue
            sides = re.findall(r"\[(s-[a-z0-9][a-z0-9-]*)\]", s)
            if len(sides) < 2:
                out.append(finding("graph", readme, f"{ident} has {len(sides)} [s-id] marker(s); a conflict needs both sides (two markers, which may name the same source on different pages)"))
            if not any(re.search(rf"\b{f}\b", s) for f in FACETS):
                out.append(finding("graph", readme, f"{ident} does not name the facet(s) it touches"))
    for p in sorted(d.glob("*.md")):
        fm = frontmatter(p) or {}
        facet = fm.get("facet")
        if facet not in FACETS:
            continue
        body = p.read_text(encoding="utf-8", errors="replace")
        local = {}
        for line in body.split("\n"):
            for lm in re.finditer(r"(?:^|;)\s*(?:[-*]\s*)?\[(s\d+)\]\s+(.*?)(?=;\s*\[s\d+\]|$)", line):
                ids = SID.findall(lm.group(2))
                if not ids:
                    out.append(finding("graph", p, f"[{lm.group(1)}] is defined by a path or text but names no register id (s-...)"))
                local[lm.group(1)] = ids
            if DEC_OLD.search(line) and not DEC_NEW.search(line):
                out.append(finding("graph", p, f"decision not in the form '**Decision needed:** <question> (<owner role>)': {line.strip()[:60]}"))
            dm = DEC_NEW.search(line)
            if dm and not re.search(r"\([^()]+\)\s*(?:\[[^\]]+\]\s*)*\.?\s*$", dm.group(1)):
                out.append(finding("graph", p, f"decision names no owner role in parentheses: {line.strip()[:60]}"))
        for cm in re.finditer(r"\[(s-[a-z0-9][a-z0-9-]*)\]\s*\(pp?\.\s*(\d+)(?:\s*[-\u2013]\s*(\d+))?\)", body):
            n = srcs.get(cm.group(1), {}).get("pages")
            hi = int(cm.group(3) or cm.group(2))
            if n and (hi > n or int(cm.group(2)) < 1):
                out.append(finding("provenance", p, f"{cm.group(0)} cites a page beyond the {n} pages declared for {cm.group(1)}"))
        cited = set(re.findall(r"\[(s-[a-z0-9][a-z0-9-]*)\]", body))
        for lk in set(re.findall(r"\[(s\d+)\]", body)):
            cited.update(local.get(lk, []))
        for sid in sorted(cited):
            if sid in srcs and facet not in srcs[sid].get("feeds", []):
                out.append(finding("graph", p, f"cites {sid}, but its feeds in sources.yaml do not include {facet}"))
    return out


def check_coverage_rules(d, data):
    """Each item is answered, marked na, or listed as open with a reason; a facet that left draft has no partial items."""
    errs = []
    left_draft = set()
    for p in d.glob("*.md"):
        fm = frontmatter(p) or {}
        if fm.get("facet") in FACETS and fm.get("status") in ("synthesis-locked", "draft-locked", "final"):
            left_draft.add(fm["facet"])
    for it in data.get("items", []):
        st, i = it["status"], it["id"]
        if st in ("answered", "partial", "conflict") and not it.get("where"):
            errs.append(f"{i}: status {st} needs 'where' (file[:line] in _company/)")
        if st in ("na", "open", "decision", "workshop") and not it.get("reason"):
            errs.append(f"{i}: status {st} needs a 'reason'")
        w = it.get("where")
        if w and not (d / w.split(":")[0]).exists():
            errs.append(f"{i}: 'where' names {w.split(':')[0]!r}, which is not in _company/")
        if st == "open" and "close_with" not in it:
            errs.append(f"{i}: status open needs close_with (us or customer)")
        if st != "open" and "close_with" in it:
            errs.append(f"{i}: close_with belongs to status open only")
        if st == "partial" and "remainder" not in it:
            errs.append(f"{i}: status partial needs remainder (open, decision or workshop)")
        if st != "partial" and "remainder" in it:
            errs.append(f"{i}: remainder belongs to status partial only")
        if st == "partial" and it["facet"] in left_draft:
            errs.append(f"{i}: facet {it['facet']} has left draft but this item is only partial")
    return errs


def check_items(d, wanted):
    """Silent omissions: required item ids from an attached question set that coverage.yaml does not list."""
    p = d / "coverage.yaml"
    try:
        have = {x["id"] for x in load_yaml_json(p).get("items", [])} if p.exists() else set()
    except Exception:  # noqa: BLE001 - the schema check reports an unreadable file
        return []
    missing = sorted(w for w in wanted if w not in have)
    if not missing:
        return []
    shown = ", ".join(missing[:8]) + (f" and {len(missing) - 8} more" if len(missing) > 8 else "")
    return [finding("coverage", p, f"{len(missing)} required item(s) are not listed as answered, na or open (silent omission): {shown}")]


def load_wanted(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data = data.get("items", data) if isinstance(data, dict) else data
    return [x if isinstance(x, str) else x["id"] for x in data if isinstance(x, str) or x.get("required", True)]


def check_dir(d, max_age_days, today):
    out = []
    ids_declared = register_ids(d)
    out += check_names(d)
    for p in sorted(d.glob("*.md")):
        if p.name in ("AUDIT-LOG.md",):
            continue
        fm = frontmatter(p)
        if fm is None:
            out.append(finding("schema", p, "no readable frontmatter"))
            continue
        facet = fm.get("facet")
        if facet not in FACETS + ["readme"]:
            out.append(finding("schema", p, f"facet {facet!r} is not one of the nine facets or readme"))
        if fm.get("status") not in STATUSES:
            out.append(finding("schema", p, f"status {fm.get('status')!r} is not one of {STATUSES}"))
        if fm.get("level") not in LEVELS + [None] and facet != "readme":
            out.append(finding("schema", p, f"level {fm.get('level')!r} is not one of {LEVELS}"))
        if facet == "readme":
            continue
        if fm.get("status") == "stale":
            out.append(finding("stale", p, "status is stale"))
        else:
            when = as_date(fm.get("reviewed")) or as_date(fm.get("generated"))
            if when is None:
                out.append(finding("stale", p, "neither reviewed nor generated carries a date"))
            elif (today - when).days > max_age_days:
                out.append(finding("stale", p, f"last {'reviewed' if as_date(fm.get('reviewed')) else 'generated'} {when}, "
                                               f"{(today - when).days} days ago (limit {max_age_days})"))
        out += check_markers(p, fm, ids_declared)
        if fm.get("status") in ("draft-locked", "final") and not fm.get("sources"):
            out.append(finding("unsourced", p, f"status {fm.get('status')} but no sources listed"))
    for name, schema_file in (("sources.yaml", "company-sources.schema.json"), ("brands.yaml", "company-brands.schema.json"),
                              ("coverage.yaml", "company-coverage.schema.json")):
        p = d / name
        if not p.exists():
            if name != "coverage.yaml":        # coverage.yaml exists only where a question set is attached
                out.append(finding("schema", p, "missing"))
            continue
        try:
            data = load_yaml_json(p)
            schema = json.loads((SCHEMAS / schema_file).read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001 - report, don't crash a vault-wide check
            out.append(finding("schema", p, f"unreadable: {e}"))
            continue
        errs = validate(data, schema, schema)
        if not errs:
            key = {"sources.yaml": "sources", "brands.yaml": "brands", "coverage.yaml": "items"}[name]
            ids = [x.get("id") for x in data.get(key, [])]
            errs += [f"duplicate id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
            if key == "brands":
                for b in data["brands"]:
                    r = b["relation"]
                    if r.startswith("sub-brand-of:") and r.split(":", 1)[1] not in ids:
                        errs.append(f"{b['id']}: relation points at unknown brand {r.split(':', 1)[1]!r}")
            if key == "items":
                errs += check_coverage_rules(d, data)
        out += [finding("schema", p, e) for e in errs]
    for p in sorted(d.rglob("*")):
        if not p.is_file() or p.suffix not in (".md", ".yaml", ".json", ".sh") or any(s.startswith(".") for s in p.relative_to(d).parts):
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
            if any(rx.search(line) for rx in SECRET):
                out.append(finding("credential", p, "looks like a credential value; use a reference (env: or a password-manager item)", n))
    return out


def check_copies(root, company_dirs):
    out, inside = [], {str(c) for c in company_dirs}
    name_rx = re.compile(r"^(%s)-[^/]+\.md$" % "|".join(FACETS))
    def walk(d, depth):
        if depth > 8:
            return
        for p in sorted(d.iterdir()):
            if p.is_dir():
                if p.name.startswith(".") or p.name in ("node_modules", "_company"):
                    continue
                walk(p, depth + 1)
            elif name_rx.match(p.name):
                fm = frontmatter(p)
                if fm and fm.get("vertical") and fm.get("facet") in FACETS:
                    out.append(finding("copy", p, "profile file outside any _company/ folder; the profile lives only in _company/"))
    walk(root, 0)
    return out


def cmd_check(a):
    root = Path(a.folder).expanduser().resolve()
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    dirs = find_company_dirs(root)
    findings = []
    for d in dirs:
        findings += check_dir(d, a.max_age_days, today)
    if a.strict:
        for d in dirs:
            findings += check_strict(d)
    if a.items:
        wanted = load_wanted(a.items)
        for d in dirs:
            findings += check_items(d, wanted)
    if a.copies:
        findings += check_copies(root, dirs)
    if a.json:
        print(json.dumps({"company_dirs": [str(d) for d in dirs], "findings": findings}, indent=2, ensure_ascii=False))
    else:
        for f in findings:
            loc = f"{f['file']}:{f['line']}" if f.get("line") else f["file"]
            print(f"[FINDING] {f['kind']}: {loc} -- {f['message']}")
        print(f"{len(dirs)} _company folder(s), {len(findings)} finding(s)")
        if a.summary:
            for d in dirs:
                print(f"\n{d}\n  facet            open items  decisions needed")
                for facet, n_open, n_dec in summarise(d):
                    print(f"  {facet:<16} {n_open:>10}  {n_dec:>16}")
    return 1 if findings else 0


# ---------------------------------------------------------------- init
def cmd_init(a):
    org = Path(a.folder).expanduser().resolve()
    target = org / "_company"
    if target.exists():
        print(f"refused: {target} exists; init never overwrites", file=sys.stderr)
        return 2
    if not org.is_dir():
        print(f"refused: {org} is not a folder", file=sys.stderr)
        return 2
    v = a.vertical
    today = a.today or datetime.date.today().isoformat()
    display = a.display or v
    target.mkdir()
    (target / ".intake").mkdir()
    for facet in FACETS:
        (target / f"{facet}-{v}.md").write_text(
            f"---\nvertical: {v}\nfacet: {facet}\nlevel: {a.level}\nstatus: draft\ngenerated: {today}\nreviewed:\n"
            f"language: {a.language}\nsources: []\n---\n\n# {display} -- {facet}\n\n_Not provided yet._\n", encoding="utf-8")
    (target / "README.md").write_text(
        f"---\nvertical: {v}\nfacet: readme\nstatus: draft\ngenerated: {today}\nreviewed:\nlanguage: {a.language}\n---\n\n"
        f"# {display} -- profile maintenance\n\n## Sources read\n\n## Synthesis\n\nOwner confirmation: pending\n\n"
        "| Facet | Established | Conflicts | Missing | Decision needed |\n|---|---|---|---|---|\n\n"
        "## Conflicts\n\n| # | What | Value A (source) | Value B (source) | Used in the text, and why |\n|---|---|---|---|---|\n\n"
        "## Gaps\n\n## Decisions\n\n## Regenerate when\n", encoding="utf-8")
    (target / "AUDIT-LOG.md").write_text(f"# {display} -- audit log\n\n| Date | By | What was checked | Changed | Next due |\n|---|---|---|---|---|\n", encoding="utf-8")
    (target / "sources.yaml").write_text(f"vertical: {v}\nupdated: {today}\nsources: []\n", encoding="utf-8")
    (target / "brands.yaml").write_text(f"vertical: {v}\nbrands: []\n", encoding="utf-8")
    if a.template:
        (target / "coverage.yaml").write_text(f"vertical: {v}\nupdated: {today}\nitems: []\n", encoding="utf-8")
    note = ("question set: template at " + a.template) if a.template else \
        "no question set attached: the files are the plain skeleton (set company.template: to attach one)"
    print(f"created {target} ({a.level}: {len(FACETS)} facet files); {note}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("folder")
    c.add_argument("--items", help="JSON list of required item ids (or {id, required}) from the attached question set; reports silent omissions"); c.add_argument("--strict", action="store_true", help="also require the structure the overview graph needs (contract section 8)"); c.add_argument("--summary", action="store_true", help="also count open items and decisions per facet"); c.add_argument("--max-age-days", type=int, default=365); c.add_argument("--json", action="store_true")
    c.add_argument("--copies", action="store_true"); c.add_argument("--today")
    c.set_defaults(fn=cmd_check)
    i = sub.add_parser("init"); i.add_argument("folder"); i.add_argument("--vertical", required=True)
    i.add_argument("--level", choices=LEVELS, default="basic"); i.add_argument("--language", default="en")
    i.add_argument("--display"); i.add_argument("--template"); i.add_argument("--today")
    i.set_defaults(fn=cmd_init)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
