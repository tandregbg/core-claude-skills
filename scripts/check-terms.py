#!/usr/bin/env python3
"""CR-089: the skills say what the contract says, in the contract's words.

    python3 scripts/check-terms.py

Two checks, each printing [OK] or [DRIFT] lines like check-ecosystem-alignment.sh:

1. Subcommands. Every declared subcommand of a user-invocable skill has a heading in
   that skill's `## Subcommands` section, and every heading there names a declared
   subcommand or alias. This is the link nothing checked before: the contract listed six
   /ops subcommands while the skill documented nine, and the landing page published the
   contract's list.

2. Terms. No `avoid:` phrase from `terms:` appears in skill prose, the README or the
   skills comparison. Fenced code and inline code are skipped - a quoted identifier is not
   prose - and so are the CHANGELOG and docs/proposals/, which record history.

Exit status is 1 when anything drifted.
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROSE = [ROOT / "README.md", ROOT / "docs" / "SKILLS-COMPARISON.md"]


def contract():
    return yaml.safe_load((ROOT / "ecosystem.yaml").read_text(encoding="utf-8"))


def subcommand_section(text):
    """The `### ` lines of the `## Subcommands` (or `## Commands`) section, ignoring
    fenced code - an example output inside the section may itself contain `## `."""
    lines, inside, fenced, seen = [], False, False, False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if line.startswith("## "):
            if re.match(r"## (?:SUBCOMMANDS|Subcommands|Commands)\b", line):
                inside, seen = True, True
                continue
            inside = False
        elif inside and line.startswith("### "):
            lines.append(line)
    return "\n".join(lines) if seen else None


def heading_name(line, skill):
    """`### 2. `/ops check <folder>` -- ...` -> 'check'. None for the default heading."""
    m = re.search(r"`([^`]+)`", line)
    if not m:
        return None
    words = m.group(1).split()
    if words and words[0] == f"/{skill}":
        words = words[1:]
    kept = []
    for w in words:
        if w[0] in "<[\"'" or w == "or":
            break
        kept.append(w)
    return " ".join(kept) or None


def check_subcommands(doc):
    drift = 0
    for s in doc["skills"]["user_invocable"]:
        name = s["name"]
        declared = set(s.get("subcommands") or [])
        aliases = set((s.get("aliases") or {}).keys())
        path = ROOT / "skills" / name / "SKILL.md"
        if not path.exists():
            print(f"[DRIFT] subcommands /{name}: declared in the contract, no skills/{name}/SKILL.md")
            drift += 1
            continue
        section = subcommand_section(path.read_text(encoding="utf-8"))
        if section is None:
            print(f"[DRIFT] subcommands /{name}: SKILL.md has no '## Subcommands' section")
            drift += 1
            continue
        found = set()
        for line in section.splitlines():
            if line.startswith("###"):
                h = heading_name(line, name)
                if h:
                    found.add(h)
        known = declared | aliases
        undeclared = sorted(h for h in found
                            if h not in known and not any(h.startswith(k + " ") for k in known))
        missing = sorted(d for d in declared
                         if d not in found and not any(f.startswith(d + " ") for f in found))
        if undeclared or missing:
            drift += 1
            parts = []
            if missing:
                parts.append("declared, no heading: " + ", ".join(missing))
            if undeclared:
                parts.append("heading, not declared: " + ", ".join(undeclared))
            print(f"[DRIFT] subcommands /{name}: " + "; ".join(parts))
        else:
            print(f"[OK] subcommands /{name}: {len(declared)} declared, all documented")
    return drift


def prose_lines_from(text):
    """Yield (line number, text) outside fenced code, with inline code removed."""
    fenced = False
    for i, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            yield i, re.sub(r"`[^`]*`", "", line)


def prose_lines(path):
    return prose_lines_from(path.read_text(encoding="utf-8"))


def check_terms(doc):
    phrases = []
    for t in doc.get("terms") or []:
        for a in t.get("avoid") or []:
            phrases.append((t["id"], a, re.compile(rf"(?<![\w-]){re.escape(a)}(?![\w-])", re.I)))
    files = sorted((ROOT / "skills").rglob("*.md")) + [p for p in PROSE if p.exists()]
    hits = []
    for f in files:
        for n, text in prose_lines(f):
            for tid, a, rx in phrases:
                if rx.search(text):
                    hits.append(f"{f.relative_to(ROOT)}:{n}: '{a}' -> use the term '{tid}'")
    if hits:
        print(f"[DRIFT] terms: {len(hits)} use(s) of a phrase declared in `avoid:`")
        for h in hits[:40]:
            print(f"        {h}")
        if len(hits) > 40:
            print(f"        ... and {len(hits) - 40} more")
        return 1
    print(f"[OK] terms: {len(phrases)} avoided phrases, none in {len(files)} files")
    return 0


def main():
    doc = contract()
    drift = check_subcommands(doc) + check_terms(doc)
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
