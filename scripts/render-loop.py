#!/usr/bin/env python3
"""Render README's generated blocks from ecosystem.yaml: the working loop and orientation.

    python3 scripts/render-loop.py            # print both blocks
    python3 scripts/render-loop.py --check    # exit 1 if README is stale
    python3 scripts/render-loop.py --write    # replace both blocks in README.md

The README and the landing page both show the loop. CR-062 declared it once so
they would stop being two hand-written copies; a hand-drawn diagram alongside the
declaration is the third copy, and it had already drifted two steps behind within
hours of being written. So the picture is generated and `check-components.py`
fails when the committed block no longer matches the declaration.

`orientation` (CR-077) carries the same promise -- *rendered, never restated* -- and
until CR-166 nothing kept it: no script referenced `orientation`, so the README block
could drift from the declaration silently, which is the exact failure the rule was
written to prevent. One script does both, because two scripts doing the same job is
the same defect one layer up. This one also resolves each entry's `sources` against
the contract, so an answer may not cite a declaration that does not exist.
"""
import argparse, re, sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
START, END = "<!-- working-loop:start -->", "<!-- working-loop:end -->"
O_START, O_END = "<!-- orientation:start -->", "<!-- orientation:end -->"

# The prose around the entries lives here for the same reason the loop block's does:
# generated means the whole block, so there is no hand-written half to drift.
O_INTRO = """Generated from `orientation` in [`ecosystem.yaml`](ecosystem.yaml) \u2014 do not edit here (CR-077).

Two onboardings produced the same questions, and none of them were about the loop below. They
were about the substrate: which folders are read, which are sealed, what is in the context
window, where a session starts. **A person cannot run the loop before they can read the room.**"""


def esc(t: str) -> str:
    return t.replace("<", "&lt;").replace(">", "&gt;").replace('"', "'")


def render(loop: list) -> str:
    phases, seen = [], set()
    for s in loop:
        if s["phase"] not in seen:
            seen.add(s["phase"]); phases.append(s["phase"])

    L = ["```mermaid", "graph TB"]
    for i, ph in enumerate(phases):
        L.append(f'    subgraph p{i}["{esc(ph)}"]')
        for s in (x for x in loop if x["phase"] == ph):
            mark = "  ·  by hand" if s.get("manual") else ("  ·  external" if s.get("external") else "")
            L.append(f'        {s["id"]}["<b>{esc(s["id"])}</b><br/>{esc(s["label"])}{esc(mark)}"]')
        L.append("    end")

    # An edge exists where one step produces what another consumes. Drawn from the
    # declaration rather than from memory, which is what kept the hand-drawn version
    # missing two steps.
    made = {}
    for s in loop:
        for item in s.get("produces") or []:
            made.setdefault(item, s["id"])
    L.append("")
    for s in loop:
        for item in s.get("consumes") or []:
            src = made.get(item)
            if src and src != s["id"]:
                L.append(f'    {src} -->|{esc(item)}| {s["id"]}')
    L.append("```")

    manual = [s for s in loop if s.get("manual")]
    L += ["",
          f"**{len(loop)} steps, {len(phases)} phases.** Generated from `working_loop` in "
          "`ecosystem.yaml` — the same declaration the landing page reads. Do not edit this block by "
          "hand; run `python3 scripts/render-loop.py --write`.",
          "",
          "**The loop closes at the summary.** What did not land in one session becomes the top of the "
          "next agenda, carrying a session count and an age — so an item cannot quietly outlive the "
          "series it belongs to.",
          ""]
    if manual:
        L.append(f"**{len(manual)} steps are deliberately by hand**, marked above. Each is a place "
                 "where generating the obvious answer would be confidently wrong in a way the reader "
                 "could not check:")
        L.append("")
        for s in manual:
            L.append(f"- **{s['id']}** — {s.get('why_manual', '')}")
        L.append("")
    return "\n".join(L)


def render_orientation(entries: list) -> str:
    """The orientation block: the provenance line, the prose, then one row per entry.

    The question is rendered AS ASKED (CR-077): the wording is the evidence, and a
    person recognises their own question faster than a category.
    """
    L = [O_INTRO, "", "| | |", "|---|---|"]
    for e in entries:
        q = " ".join(str(e["question"]).split())
        a = " ".join(str(e["answer"]).split())
        L.append(f"| {q} | {a} |")
    return "\n".join(L)


def resolve(doc, path: str):
    """Walk a dotted `sources` path. A list of mappings is keyed by id, name or path,
    so `skills.company` and `vault_conventions.conventions.vault_relative` both resolve."""
    node = doc
    for part in path.split("."):
        if isinstance(node, dict):
            if part in node:
                node = node[part]
                continue
            node = list(node.values())
        if isinstance(node, list):
            hit = None
            for item in node:
                if isinstance(item, dict) and part in (item.get("id"), item.get("name"), item.get("path")):
                    hit = item
                    break
                if isinstance(item, list):                      # skills: two lists under one key
                    for sub in item:
                        if isinstance(sub, dict) and part in (sub.get("id"), sub.get("name")):
                            hit = sub
                            break
            if hit is None:
                return None
            node = hit
            continue
        return None
    return node


def check_sources(doc) -> list:
    """An answer may cite only declarations that exist. CR-166: the entry is one
    answer, the check is the reason every later answer stays true."""
    problems = []
    for e in doc.get("orientation") or []:
        for s in e.get("sources") or []:
            if resolve(doc, s) is None:
                problems.append(f"orientation {e['id']}: sources `{s}` resolves to nothing")
    return problems


def block_of(text: str, start: str, end: str):
    m = re.search(re.escape(start) + r"\n(.*?)" + re.escape(end), text, re.S)
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true", help="exit 1 if README is stale")
    a = ap.parse_args()

    doc = yaml.safe_load((ROOT / "ecosystem.yaml").read_text(encoding="utf-8"))
    loop = doc["working_loop"]
    blocks = [("working-loop", START, END, render(loop)),
              ("orientation", O_START, O_END, render_orientation(doc["orientation"]))]
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    bad = check_sources(doc)

    if not (a.check or a.write):
        for _, _, _, b in blocks:
            print(b)
            print()
        for p in bad:
            print(f"[FAIL] {p}")
        return

    # tolerate an empty block: the markers may be placed before anything is rendered
    for name, start, end, _ in blocks:
        if not block_of(text, start, end):
            sys.exit(f"README.md has no {start} / {end} block")

    if a.check:
        stale = [name for name, start, end, b in blocks
                 if block_of(text, start, end).group(1).strip() != b.strip()]
        if stale or bad:
            for p in bad:
                print(f"[FAIL] orientation sources: {p.split(': ', 1)[1]}", file=sys.stderr)
            if stale:
                print(f"[FAIL] README {', '.join(stale)} block(s) stale - "
                      "run python3 scripts/render-loop.py --write", file=sys.stderr)
            sys.exit(1)
        print(f"[OK] README working-loop and orientation blocks match the declaration "
              f"({len(loop)} steps, {len(doc['orientation'])} entries)")
        return

    # Write the block that sits last in the file first, so earlier offsets still hold.
    for name, start, end, b in sorted(blocks, key=lambda x: text.index(x[1]), reverse=True):
        m = block_of(text, start, end)
        text = text[:m.start(1)] + b + "\n" + text[m.end(1):]
    readme.write_text(text, encoding="utf-8")
    print(f"  README.md updated - {len(loop)} loop steps, {len(doc['orientation'])} orientation entries")
    for p in bad:
        print(f"  [FAIL] {p}")
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
