#!/usr/bin/env python3
"""Mechanical parts of /company (CR-125): create the skeleton, check a profile. Report only.

    python3 company_tool.py init <org-folder> --vertical <v> [--level light] [--language en] [--display Name]
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
import argparse, datetime, json, re, sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("needs pyyaml -- run with a python that has it")

HERE = Path(__file__).resolve().parent
SCHEMAS = HERE.parents[1] / "docs" / "schemas"

FACETS = ["essence", "company", "offering", "positioning", "messaging", "gtm", "strategy", "brand", "public"]
LEVELS = ["public", "light", "medium", "full"]
LEVEL_FACETS = {
    "public": ["company", "offering", "public"],
    "light": ["company", "offering", "public", "essence", "positioning", "messaging", "strategy", "brand"],
    "medium": FACETS,
    "full": FACETS,
}
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
            "object": isinstance(v, dict)}[t]


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
            out.append(f"{where}: {value!r} is not one of the allowed forms")
        return out
    if "const" in schema and value != schema["const"]:
        out.append(f"{where}: must be {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{where}: {value!r} is not one of {schema['enum']}")
    t = schema.get("type")
    if t and not _types(value, t):
        out.append(f"{where}: {value!r} is not of type {t}")
        return out
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
def check_dir(d, max_age_days, today):
    out = []
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
        if fm.get("status") in ("draft-locked", "final") and not fm.get("sources"):
            out.append(finding("unsourced", p, f"status {fm.get('status')} but no sources listed"))
    for name, schema_file in (("sources.yaml", "company-sources.schema.json"), ("brands.yaml", "company-brands.schema.json")):
        p = d / name
        if not p.exists():
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
            key = "sources" if name == "sources.yaml" else "brands"
            ids = [x.get("id") for x in data.get(key, [])]
            errs += [f"duplicate id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
            if key == "brands":
                for b in data["brands"]:
                    r = b["relation"]
                    if r.startswith("sub-brand-of:") and r.split(":", 1)[1] not in ids:
                        errs.append(f"{b['id']}: relation points at unknown brand {r.split(':', 1)[1]!r}")
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
    if a.copies:
        findings += check_copies(root, dirs)
    if a.json:
        print(json.dumps({"company_dirs": [str(d) for d in dirs], "findings": findings}, indent=2, ensure_ascii=False))
    else:
        for f in findings:
            loc = f"{f['file']}:{f['line']}" if f.get("line") else f["file"]
            print(f"[FINDING] {f['kind']}: {loc} -- {f['message']}")
        print(f"{len(dirs)} _company folder(s), {len(findings)} finding(s)")
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
    for facet in LEVEL_FACETS[a.level]:
        (target / f"{facet}-{v}.md").write_text(
            f"---\nvertical: {v}\nfacet: {facet}\nlevel: {a.level}\nstatus: draft\ngenerated: {today}\nreviewed:\n"
            f"language: {a.language}\nsources: []\n---\n\n# {display} -- {facet}\n\n_Not provided yet._\n", encoding="utf-8")
    (target / "README.md").write_text(
        f"---\nvertical: {v}\nfacet: readme\nstatus: draft\ngenerated: {today}\nreviewed:\nlanguage: {a.language}\n---\n\n"
        f"# {display} -- profile maintenance\n\n## Sources read\n\n## Conflicts\n\n## Gaps\n\n## Regenerate when\n", encoding="utf-8")
    (target / "AUDIT-LOG.md").write_text(f"# {display} -- audit log\n\n| Date | By | What was checked | Changed | Next due |\n|---|---|---|---|---|\n", encoding="utf-8")
    (target / "sources.yaml").write_text(f"vertical: {v}\nupdated: {today}\nsources: []\n", encoding="utf-8")
    (target / "brands.yaml").write_text(f"vertical: {v}\nbrands: []\n", encoding="utf-8")
    note = ("question set: template at " + a.template) if a.template else \
        "no question set attached: the files are the plain skeleton (set company.template: to attach one)"
    print(f"created {target} ({a.level}: {len(LEVEL_FACETS[a.level])} facet files); {note}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("folder")
    c.add_argument("--max-age-days", type=int, default=365); c.add_argument("--json", action="store_true")
    c.add_argument("--copies", action="store_true"); c.add_argument("--today")
    c.set_defaults(fn=cmd_check)
    i = sub.add_parser("init"); i.add_argument("folder"); i.add_argument("--vertical", required=True)
    i.add_argument("--level", choices=LEVELS, default="light"); i.add_argument("--language", default="en")
    i.add_argument("--display"); i.add_argument("--template"); i.add_argument("--today")
    i.set_defaults(fn=cmd_init)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
