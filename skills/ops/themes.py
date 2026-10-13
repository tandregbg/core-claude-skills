#!/usr/bin/env python3
"""The themes registry (CR-124): consistency checks and counts per quarter.

    python3 themes.py check <project>            # report-only findings
    python3 themes.py quarters <project> [--theme T07]   # Markdown table(s)
    python3 themes.py check <project> --json

A project opts in with `themes: {enabled: true}` in its config chain; the registry is
`<project>/_themes.yaml`. Summaries carry one metadata line, `Themes: T07 (primary), T03`
(Swedish label `Teman`), insights carry `themes: [T07]`.

CHECKS (never writes, never merges, never creates a theme):
  three-way   registry units[] <-> the summary's Themes line <-> the themes of insights
              whose `source` is that summary
  two-way     insight `themes` <-> registry `insight_ids`
  ids         a theme id used anywhere and absent from the registry; a `merged` theme
              still in use; a `synthesis` path that does not exist
  shape       a Themes line with more than two primary themes, or outside 2-6 themes;
              a registry unit whose summary does not exist

REGISTRY SCHEMA 1 (<project>/_themes.yaml):
    schema: 1
    next_id: 14
    themes:
      - id: T07                     # T + two or three digits, never reused
        name: Hiring before product-market fit
        description: one sentence
        aliases: [early hiring]     # reuse before create: match aliases first
        status: active              # active | merged
        merged_into: null           # T## when merged (a person's decision)
        first_seen: 2025-03-14      # original date where present
        last_seen: 2026-09-02
        units:                      # the profile's unit: meeting or episode
          - {source: 260103-episode-guest-topic.md, role: primary, note: one line}
        insight_ids: [12, 48]
        related: [T03]
        synthesis: .knowledge/wiki/themes/t07-hiring-before-product-market-fit.md
  No personal or company names in any theme field.

QUARTERS: per theme, units counted per calendar quarter by the ORIGINAL date (the
summary's `Originally published:` line, CR-123), else the date in the file name. A
back-catalogue episode therefore lands in the quarter it was first published.
"""
import argparse, datetime, json, os, re, sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("needs pyyaml -- run with a python that has it")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ops-config"))
import profiles  # noqa: E402

REGISTRY = "_themes.yaml"
THEME_ID = re.compile(r"\bT\d{2,3}\b")
LINE = re.compile(r"^\s*(?:[-*]\s+)?\**(?:Themes|Teman)\**\s*:\**\s*(.*)$", re.I)
ORIGINAL = re.compile(r"^\s*(?:[-*]\s+)?\**(?:Originally published|Ursprungligen publicerad)\**\s*:\**\s*"
                      r"(\d{4}-\d{2}-\d{2}|\d{6})", re.I)
DATED = re.compile(r"^(\d{6})-.*\.md$")
MIN_THEMES, MAX_THEMES, MAX_PRIMARY = 2, 6, 2


def enabled(project: Path) -> bool:
    for _, cfg in profiles.chain(project):
        block = cfg.get("themes")
        if isinstance(block, dict) and "enabled" in block:
            return bool(block["enabled"])
    return False


def _walk(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in sorted(filenames):
            yield Path(dirpath) / name


def summaries(project: Path) -> dict:
    """basename -> path of every dated summary under the project."""
    return {p.name: p for p in _walk(project) if DATED.match(p.name)}


def parse_summary(path: Path) -> dict:
    """{'themes': {id: role}, 'line': n or None, 'original': date or None}."""
    out = {"themes": {}, "line": None, "original": None, "primary": 0}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for n, raw in enumerate(text.splitlines()[:60], 1):
        m = ORIGINAL.match(raw)
        if m and not out["original"]:
            out["original"] = _as_date(m.group(1))
        m = LINE.match(raw)
        if m and out["line"] is None:
            out["line"] = n
            for part in m.group(1).split(","):
                ids = THEME_ID.findall(part)
                if ids:
                    role = "primary" if "primary" in part.lower() or "primär" in part.lower() else "secondary"
                    out["themes"][ids[0]] = role
            out["primary"] = sum(1 for r in out["themes"].values() if r == "primary")
    return out


def _as_date(text) -> datetime.date | None:
    text = str(text or "").strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            return datetime.date.fromisoformat(text)
        if re.fullmatch(r"\d{6}", text):
            return datetime.datetime.strptime(text, "%y%m%d").date()
    except ValueError:
        return None
    return None


def load_registry(project: Path) -> dict:
    f = project / REGISTRY
    if not f.is_file():
        return {}
    try:
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {"_error": "unreadable"}
    return doc if isinstance(doc, dict) else {}


def insights(project: Path) -> list:
    out = []
    for p in _walk(project):
        if p.name != "_insights.yaml":
            continue
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        for e in doc.get("insights") or []:
            if isinstance(e, dict):
                out.append(e)
    return out


def _vault_path(project: Path, rel: str) -> bool:
    for folder in [project, *project.parents]:
        if (folder / rel).exists():
            return True
    return False


def check(project) -> list:
    project = Path(project).expanduser()
    reg = load_registry(project)
    if reg.get("_error"):
        return [{"kind": "themes", "file": REGISTRY, "line": None, "message": "registry cannot be parsed"}]
    themes = {str(t.get("id")): t for t in reg.get("themes") or [] if isinstance(t, dict) and t.get("id")}
    summ = summaries(project)
    parsed = {name: parse_summary(p) for name, p in summ.items()}
    found = []

    def add(file, line, message):
        found.append({"kind": "themes", "file": file, "line": line, "message": message})

    # shape of each summary's line, and ids it names
    for name, info in sorted(parsed.items()):
        if info["line"] is None:
            continue
        if info["primary"] > MAX_PRIMARY:
            add(name, info["line"], f"{info['primary']} primary themes (at most {MAX_PRIMARY})")
        if not MIN_THEMES <= len(info["themes"]) <= MAX_THEMES:
            add(name, info["line"], f"{len(info['themes'])} themes (expected {MIN_THEMES}-{MAX_THEMES})")
        for tid in info["themes"]:
            if tid not in themes:
                add(name, info["line"], f"{tid} is not in {REGISTRY}")
            elif themes[tid].get("status") == "merged":
                add(name, info["line"], f"{tid} is merged into {themes[tid].get('merged_into')}; retag")

    # registry -> summaries
    for tid, t in sorted(themes.items()):
        for u in t.get("units") or []:
            src = str((u or {}).get("source") or "").strip()
            if not src:
                continue
            if src not in parsed:
                add(REGISTRY, None, f"{tid} lists {src}, which does not exist")
            elif tid not in parsed[src]["themes"]:
                add(src, parsed[src]["line"], f"registry {tid} lists this summary; its Themes line does not name {tid}")
        if t.get("synthesis") and not _vault_path(project, str(t["synthesis"])):
            add(REGISTRY, None, f"{tid} synthesis {t['synthesis']} does not exist")
    for name, info in sorted(parsed.items()):
        for tid in info["themes"]:
            t = themes.get(tid)
            if t and name not in {str((u or {}).get("source") or "") for u in t.get("units") or []}:
                add(REGISTRY, None, f"{tid} has no unit {name}, whose Themes line names it")

    # insights <-> summaries, insights <-> registry
    listed = {tid: {int(i) for i in (t.get("insight_ids") or []) if str(i).isdigit()} for tid, t in themes.items()}
    ids_seen = set()
    for e in insights(project):
        iid = e.get("id")
        tags = [str(x) for x in (e.get("themes") or [])]
        ids_seen.add(iid)
        src = str(e.get("source") or "").strip()
        for tid in tags:
            if tid not in themes:
                add("_insights.yaml", None, f"insight #{iid} names {tid}, which is not in {REGISTRY}")
                continue
            if iid not in listed[tid]:
                add(REGISTRY, None, f"{tid} insight_ids lacks #{iid}, which names {tid}")
            if src in parsed and parsed[src]["line"] is not None and tid not in parsed[src]["themes"]:
                add(src, parsed[src]["line"], f"insight #{iid} from this summary names {tid}; the Themes line does not")
    by_id = {e.get("id"): e for e in insights(project)}
    for tid, ids in sorted(listed.items()):
        for iid in sorted(ids):
            e = by_id.get(iid)
            if e is None:
                add(REGISTRY, None, f"{tid} insight_ids names #{iid}, which does not exist")
            elif tid not in [str(x) for x in (e.get("themes") or [])]:
                add("_insights.yaml", None, f"insight #{iid} is in {tid} insight_ids but does not name {tid}")
    return found


def unit_date(path: Path, info: dict) -> datetime.date | None:
    if info.get("original"):
        return info["original"]
    m = DATED.match(path.name)
    return _as_date(m.group(1)) if m else None


def quarters(project, theme: str | None = None) -> dict:
    """{theme id: {'YYYY-Qn': count}} by original date."""
    project = Path(project).expanduser()
    reg = load_registry(project)
    summ = summaries(project)
    out = {}
    for t in reg.get("themes") or []:
        tid = str(t.get("id"))
        if theme and tid != theme:
            continue
        counts = {}
        for u in t.get("units") or []:
            p = summ.get(str((u or {}).get("source") or ""))
            if not p:
                continue
            d = unit_date(p, parse_summary(p))
            if d:
                q = f"{d.year}-Q{(d.month - 1) // 3 + 1}"
                counts[q] = counts.get(q, 0) + 1
        out[tid] = dict(sorted(counts.items()))
    return out


def quarters_table(counts: dict) -> str:
    qs = sorted({q for c in counts.values() for q in c})
    lines = ["| Theme | " + " | ".join(qs) + " |", "|---|" + "---|" * len(qs)]
    for tid, c in counts.items():
        lines.append(f"| {tid} | " + " | ".join(str(c.get(q, 0)) for q in qs) + " |")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Themes registry checks and quarter counts (CR-124). Never writes.")
    ap.add_argument("command", choices=["check", "quarters"])
    ap.add_argument("project")
    ap.add_argument("--theme")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    project = Path(args.project).expanduser()
    if args.command == "check":
        found = check(project)
        if args.json:
            print(json.dumps(found, ensure_ascii=False, indent=2))
        else:
            for f in found:
                where = f["file"] + (f":{f['line']}" if f["line"] else "")
                print(f"[THEMES] {where}  {f['message']}")
            print(f"{len(found)} theme finding(s)")
    else:
        counts = quarters(project, args.theme)
        print(json.dumps(counts, indent=2) if args.json else quarters_table(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
