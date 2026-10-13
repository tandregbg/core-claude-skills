#!/usr/bin/env python3
"""Move an _insights.yaml to a profile's schema-3 shape, or recount it (CR-123).

    python3 profile_migrate.py <folder> --plan plan.yaml            # dry run: the table
    python3 profile_migrate.py <folder> --plan plan.yaml --apply
    python3 profile_migrate.py <folder> --recount [--apply]          # counts only

The JUDGED part of a migration (which podcast type an entry is, who raised it, whether
a `rule` is really a claim) is made by the model in `/insights migrate --profile`, per
entry and shown as a table first. It arrives here as a plan:

    entries:
      12: {type: claim, voice: guest, confidence: consensus}
      48: {type: practice, voice: both}
    confirmations:                 # per entry, per confirmation source: its voice
      12: {"260103-episode-guest-topic.md": guest}

This script is the ARITHMETIC and the WRITING: it applies the plan, recounts
`confirmation_count` (by the profile's count_by), `independent_count` and
`owner_count` from the voices, and sets the top-level `version: 3`.

WRITING (CR-122): targeted line edits only. The file is never loaded and dumped back:
comments, key order, quoting and å/ä/ö stay as they are. Before anything is written
the result is re-parsed and compared with the original: every entry must be equal
except for the fields this run set, and the count of å/ä/ö must be unchanged.
Otherwise nothing is written and the reason is printed.

Never runs on a folder whose profile is `meeting`.
"""
import argparse, json, re, sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("needs pyyaml -- run with a python that has it")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ops-config"))
sys.path.insert(0, str(HERE))
import profiles  # noqa: E402
import promotion_candidates as pc  # noqa: E402

ENTRY = re.compile(r"^(\s*)- id:\s*(\d+)\s*(#.*)?$")
SWEDISH = re.compile(r"[åäöÅÄÖ]")
SET_FIELDS = ("type", "voice", "confidence", "confirmation_count", "independent_count", "owner_count")


class Doc:
    """An _insights.yaml as lines, with entry spans found by `- id: N` lines."""

    def __init__(self, text: str):
        self.lines = text.split("\n")

    def spans(self) -> dict:
        out, starts = {}, []
        for i, line in enumerate(self.lines):
            m = ENTRY.match(line)
            if m:
                starts.append((i, len(m.group(1)), int(m.group(2))))
        for k, (i, indent, iid) in enumerate(starts):
            end = len(self.lines)
            for j in range(i + 1, len(self.lines)):
                line = self.lines[j]
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                lead = len(line) - len(line.lstrip())
                if lead <= indent:
                    end = j
                    break
            out[iid] = (i, end, indent + 2)
        return out

    def set_field(self, iid: int, key: str, value) -> bool:
        span = self.spans().get(iid)
        if not span:
            return False
        start, end, fi = span
        rendered = _scalar(value)
        pat = re.compile(rf"^ {{{fi}}}{re.escape(key)}:(\s.*)?$")
        for j in range(start + 1, end):
            if pat.match(self.lines[j]):
                comment = re.search(r"\s+#.*$", self.lines[j])
                self.lines[j] = f"{' ' * fi}{key}: {rendered}" + (comment.group(0) if comment and "'" not in comment.group(0) and '"' not in comment.group(0) else "")
                return True
        # insert after `type:` when present, else directly after the id line
        at = start + 1
        type_pat = re.compile(rf"^ {{{fi}}}type:")
        for j in range(start + 1, end):
            if type_pat.match(self.lines[j]):
                at = j + 1
                break
        self.lines.insert(at, f"{' ' * fi}{key}: {rendered}")
        return True

    def set_confirmation_voice(self, iid: int, source: str, voice: str) -> bool:
        span = self.spans().get(iid)
        if not span:
            return False
        start, end, fi = span
        for j in range(start + 1, end):
            line = self.lines[j]
            if source not in line or "source" not in line:
                continue
            stripped = line.strip()
            if stripped.startswith("- {") and stripped.endswith("}"):          # flow style
                if re.search(r"\bvoice:\s*[\w-]+", line):
                    self.lines[j] = re.sub(r"\bvoice:\s*[\w-]+", f"voice: {voice}", line)
                else:
                    self.lines[j] = line[:line.rstrip().rfind("}")] + f", voice: {voice}}}"
                return True
            if re.match(r"^\s*-\s+source:", line):                            # block style
                item_indent = len(line) - len(line.lstrip()) + 2
                k = j + 1
                while k < end and (len(self.lines[k]) - len(self.lines[k].lstrip())) >= item_indent \
                        and self.lines[k].strip():
                    if re.match(rf"^ {{{item_indent}}}voice:", self.lines[k]):
                        self.lines[k] = f"{' ' * item_indent}voice: {voice}"
                        return True
                    k += 1
                self.lines.insert(j + 1, f"{' ' * item_indent}voice: {voice}")
                return True
        return False

    def set_version(self, version: int) -> None:
        for j, line in enumerate(self.lines):
            if re.match(r"^version:\s*", line):
                self.lines[j] = f"version: {version}"
                return
        self.lines.insert(0, f"version: {version}")

    def text(self) -> str:
        return "\n".join(self.lines)


def _scalar(value) -> str:
    if isinstance(value, bool) or value is None:
        return json.dumps(value)
    if isinstance(value, int):
        return str(value)
    text = str(value)
    return text if re.fullmatch(r"[A-Za-z_][\w-]*", text) else json.dumps(text, ensure_ascii=False)


def counts(entry: dict, prof: dict) -> dict:
    owner = str(prof.get("owner_voice") or "").lower()
    units = pc.voice_units(entry, owner)
    sources = {pc._unit(entry.get("source"))} | {pc._unit(c.get("source")) for c in entry.get("confirmations") or []
                                                 if isinstance(c, dict)}
    sources.discard("")
    dates = {pc._date(entry.get("date"))} | {pc._date(c.get("date")) for c in entry.get("confirmations") or []
                                             if isinstance(c, dict) and c.get("date")}
    dates.discard("")
    by_unit = (prof.get("count_by") or "date") == "unit"
    return {"confirmation_count": len(sources) if by_unit else len(dates),
            "independent_count": len(units["independent"]), "owner_count": len(units["owner"])}


def _strip(entry: dict, keys) -> dict:
    e = {k: v for k, v in entry.items() if k not in keys}
    if isinstance(e.get("confirmations"), list):
        e["confirmations"] = [{k: v for k, v in c.items() if k != "voice"} if isinstance(c, dict) else c
                              for c in e["confirmations"]]
    return e


def verify(before: str, after: str) -> str | None:
    try:
        a, b = yaml.safe_load(before) or {}, yaml.safe_load(after) or {}
    except yaml.YAMLError as error:
        return f"the result does not parse: {error}"
    if len(SWEDISH.findall(before)) != len(SWEDISH.findall(after)):
        return "the count of å/ä/ö changed"
    ea = {e.get("id"): e for e in a.get("insights") or [] if isinstance(e, dict)}
    eb = {e.get("id"): e for e in b.get("insights") or [] if isinstance(e, dict)}
    if set(ea) != set(eb):
        return "the set of entries changed"
    for iid in ea:
        if _strip(ea[iid], SET_FIELDS) != _strip(eb[iid], SET_FIELDS):
            return f"entry #{iid} changed outside the fields this run sets"
    rest_a = {k: v for k, v in a.items() if k not in ("insights", "version")}
    rest_b = {k: v for k, v in b.items() if k not in ("insights", "version")}
    if rest_a != rest_b:
        return "a top-level key other than version changed"
    return None


def migrate(folder: Path, plan: dict | None, apply: bool) -> dict:
    target = folder / "_insights.yaml" if folder.is_dir() else folder
    resolved = profiles.resolve(target.parent)
    prof = resolved["values"]
    if resolved["name"] == "meeting":
        return {"error": "the folder's profile is `meeting`; migrate --profile runs only on another profile"}
    before = target.read_text(encoding="utf-8")
    original = yaml.safe_load(before) or {}
    doc = Doc(before)
    rows = []
    plan = plan or {}
    planned = {int(k): v for k, v in (plan.get("entries") or {}).items()}
    voices = {int(k): v for k, v in (plan.get("confirmations") or {}).items()}
    allowed_types = set(prof.get("promotable_types") or []) | {"opportunity", "quote"}
    for e in original.get("insights") or []:
        if not isinstance(e, dict) or not isinstance(e.get("id"), int):
            continue
        iid = e["id"]
        change = dict(planned.get(iid) or {})
        if change.get("type") and change["type"] not in allowed_types:
            return {"error": f"plan gives #{iid} type '{change['type']}', not a {resolved['name']} type"}
        if change.get("confidence") == "rule":
            return {"error": f"plan sets #{iid} to rule; a profile migration never creates rules"}
        merged = dict(e)
        for key in ("type", "voice", "confidence"):
            if key in change:
                merged[key] = change[key]
        confs = []
        for c in e.get("confirmations") or []:
            c = dict(c) if isinstance(c, dict) else c
            if isinstance(c, dict) and str(c.get("source")) in (voices.get(iid) or {}):
                c["voice"] = voices[iid][str(c.get("source"))]
            confs.append(c)
        merged["confirmations"] = confs
        n = counts(merged, prof)
        row = {"id": iid, "type": f"{e.get('type')} -> {merged.get('type')}" if merged.get("type") != e.get("type")
               else str(e.get("type")), "voice": merged.get("voice"), "confidence": merged.get("confidence"), **n}
        rows.append(row)
        for key in ("type", "voice", "confidence"):
            if key in change and change[key] != e.get(key):
                doc.set_field(iid, key, change[key])
        for source, voice in (voices.get(iid) or {}).items():
            if not doc.set_confirmation_voice(iid, source, voice):
                return {"error": f"#{iid}: confirmation {source} not found in the file"}
        for key, value in n.items():
            if e.get(key) != value:
                doc.set_field(iid, key, value)
    doc.set_version(3)
    after = doc.text()
    problem = verify(before, after)
    result = {"file": str(target), "profile": resolved["name"], "rows": rows,
              "changed": before != after, "written": False, "problem": problem}
    if apply and not problem and before != after:
        target.write_text(after, encoding="utf-8")
        result["written"] = True
    return result


def as_text(result: dict) -> str:
    if result.get("error"):
        return f"refused: {result['error']}"
    lines = [f"{result['file']}  profile {result['profile']}",
             "| id | type | voice | confidence | confirmations | independent | owner |",
             "|---|---|---|---|---|---|---|"]
    for r in result["rows"]:
        lines.append(f"| {r['id']} | {r['type']} | {r['voice'] or ''} | {r['confidence'] or 'hypothesis'} | "
                     f"{r['confirmation_count']} | {r['independent_count']} | {r['owner_count']} |")
    if result["problem"]:
        lines.append(f"NOT WRITTEN: {result['problem']}")
    elif result["written"]:
        lines.append("written (targeted edits; re-parsed and compared before writing)")
    elif result["changed"]:
        lines.append("dry run: nothing written; add --apply")
    else:
        lines.append("nothing to change")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Apply a profile migration plan or recount (CR-123).")
    ap.add_argument("folder")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", help="YAML plan made by /insights migrate --profile")
    mode.add_argument("--recount", action="store_true", help="recount only; no judged changes")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    plan = yaml.safe_load(Path(args.plan).read_text(encoding="utf-8")) if args.plan else None
    result = migrate(Path(args.folder).expanduser(), plan, args.apply)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else as_text(result))
    return 1 if result.get("error") or result.get("problem") else 0


if __name__ == "__main__":
    sys.exit(main())
