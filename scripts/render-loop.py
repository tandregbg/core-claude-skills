#!/usr/bin/env python3
"""Render the working loop as Mermaid, from `working_loop` in ecosystem.yaml.

    python3 scripts/render-loop.py            # print
    python3 scripts/render-loop.py --write    # replace the block in README.md

The README and the landing page both show this loop. CR-062 declared it once so
they would stop being two hand-written copies; a hand-drawn diagram alongside the
declaration is the third copy, and it had already drifted two steps behind within
hours of being written. So the picture is generated and `check-components.py`
fails when the committed block no longer matches the declaration.
"""
import argparse, re, sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
START, END = "<!-- working-loop:start -->", "<!-- working-loop:end -->"


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true", help="exit 1 if README is stale")
    a = ap.parse_args()

    loop = yaml.safe_load((ROOT / "ecosystem.yaml").read_text(encoding="utf-8"))["working_loop"]
    block = render(loop)
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")

    if a.check or a.write:
        # tolerate an empty block: the markers may be placed before anything is rendered
        m = re.search(re.escape(START) + r"\n(.*?)" + re.escape(END), text, re.S)
        if not m:
            sys.exit(f"README.md has no {START} / {END} block")
        if a.check:
            if m.group(1).strip() != block.strip():
                sys.exit("[FAIL] README working-loop block is stale — "
                         "run python3 scripts/render-loop.py --write")
            print("[OK] README working-loop block matches the declaration")
            return
        readme.write_text(text[:m.start(1)] + block + "\n" + text[m.end(1):], encoding="utf-8")
        print(f"  README.md updated — {len(loop)} steps")
        return
    print(block)


if __name__ == "__main__":
    main()
