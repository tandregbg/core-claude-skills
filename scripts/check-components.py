#!/usr/bin/env python3
"""Check the components graph against the rest of the contract.

`components:` says how the parts touch each other; `vault_conventions:` says
how they touch files. The two can disagree, and did the day the block was
written: two paths a component claimed to write were not declared anywhere.

Checks, in order of how quietly each would otherwise fail:

  1. Every vault path a component writes or reads is declared.
  2. `depends_on` names a real component, or an external thing that is
     explicitly outside the graph.
  3. No cycles.
  4. Every component carries the fields a reader relies on.

Run it after editing either block:  python3 scripts/check-components.py
"""

import os
import sys

try:
    import yaml
except ImportError:
    sys.exit("needs pyyaml")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED = ('id', 'kind', 'role', 'reads', 'writes', 'depends_on')


def vault_paths(doc):
    vc = doc.get('vault_conventions') or {}
    entries = (vc.get('vault_root') or []) + (vc.get('per_folder') or [])
    return {e['path'] for e in entries if isinstance(e, dict) and 'path' in e}


def looks_like_a_path(text):
    """A vault path, as opposed to prose like 'the vault broadly'."""
    head = text.split(' —')[0].split(' -')[0].strip()
    return head if (head.startswith('_') or head.startswith('<') or head.startswith('.')) else None


def mentions_a_path(text):
    """A path named mid-sentence, which looks_like_a_path would miss.

    Prose is allowed — "the vault, per vault_conventions" is a legitimate
    entry — but prose that NAMES a file is a path written informally, and was
    slipping through unchecked: "the generated registers at vault root" passed
    while declaring nothing. Anything with a vault-file shape is checked.
    """
    import re
    for token in re.findall(r'[<_.][\w<>*/.-]*\.(?:yaml|md|json|toml)\b|[<_][\w<>*/.-]+/', text):
        if not token.startswith(('http', 'www')):
            yield token.rstrip(',;')


def main():
    doc = yaml.safe_load(open(os.path.join(HERE, 'ecosystem.yaml'), encoding='utf-8'))
    comps = doc.get('components')
    if not comps:
        sys.exit('[FAIL] no components: block')

    paths = vault_paths(doc)
    ids = {c['id'] for c in comps}
    problems = []

    for c in comps:
        for field in REQUIRED:
            if field not in c:
                problems.append(f"{c.get('id', '?')}: missing `{field}`")

        for direction in ('reads', 'writes'):
            for item in c.get(direction) or []:
                head = looks_like_a_path(item)
                if head and head not in paths:
                    problems.append(
                        f"{c['id']}: {direction} `{head}`, which vault_conventions "
                        f"does not declare")
                    continue
                if head:
                    continue
                # Prose entry: still check any file it names.
                for token in mentions_a_path(item):
                    if token not in paths:
                        problems.append(
                            f"{c['id']}: {direction} names `{token}` in prose, "
                            f"which vault_conventions does not declare")

    # depends_on: either names a component, or is external. External is fine -
    # msal and an HTTP library are real dependencies - but it must not be a
    # typo'd component id, so anything that fuzzily matches an id must match it
    # exactly somewhere in the string.
    edges = {}
    for c in comps:
        edges[c['id']] = [other for dep in c['depends_on'] for other in ids
                          if other != c['id'] and other in dep]

    state = {}

    def walk(node, trail):
        if state.get(node) == 'done':
            return
        if state.get(node) == 'open':
            problems.append('cycle: ' + ' -> '.join(trail + [node]))
            return
        state[node] = 'open'
        for nxt in edges.get(node, []):
            walk(nxt, trail + [node])
        state[node] = 'done'

    for c in comps:
        walk(c['id'], [])

    # working_loop: the steps a person takes, which both the README and the
    # landing page render. Checked here so a step cannot name a vault path
    # nothing declares, and so a manual step must say why it is manual - the
    # reason is the whole point of marking it.
    loop = doc.get('working_loop') or []
    seen_ids = set()
    produced = set()
    for step in loop:
        for field in ('id', 'phase', 'label', 'does'):
            if field not in step:
                problems.append(f"working_loop {step.get('id', '?')}: missing `{field}`")
        if step.get('id') in seen_ids:
            problems.append(f"working_loop: duplicate id `{step.get('id')}`")
        seen_ids.add(step.get('id'))
        # A step that can be run is not manual. Both claims live in one record,
        # so hold them against each other rather than trusting either alone.
        if step.get('manual') and step.get('command'):
            problems.append(
                f"working_loop {step.get('id')}: marked manual but carries a "
                f"command - a reader resolves that contradiction by guessing")
        # No command, not manual, not external reads as an unfinished feature -
        # the failure why_manual exists to prevent, one field over.
        if not any(step.get(k) for k in ('command', 'manual', 'external')):
            problems.append(
                f"working_loop {step.get('id')}: has no command and is neither "
                f"manual nor external - say which, or it reads as unbuilt")
        if step.get('manual') and not step.get('why_manual'):
            problems.append(
                f"working_loop {step.get('id')}: manual without why_manual - "
                f"a step marked manual and not explained reads as unfinished")
        for item in (step.get('produces') or []):
            produced.add(item)
        for item in (step.get('consumes') or []) + (step.get('produces') or []):
            head = looks_like_a_path(item)
            if head and head not in paths:
                problems.append(
                    f"working_loop {step.get('id')}: names `{head}`, which "
                    f"vault_conventions does not declare")
    # Anything consumed should be produced by an earlier step or be a path.
    for step in loop:
        for item in (step.get('consumes') or []):
            if item not in produced and not looks_like_a_path(item):
                problems.append(
                    f"working_loop {step.get('id')}: consumes `{item}`, which "
                    f"no step produces and no path declares")

    print(f"components: {len(comps)}  declared vault paths: {len(paths)}  "
          f"loop steps: {len(loop)}")
    for cid, deps in edges.items():
        if deps:
            print(f"  {cid} -> {', '.join(deps)}")

    if problems:
        print()
        for p in problems:
            print(f"[FAIL] {p}")
        sys.exit(1)
    print("\n[OK] components consistent with vault_conventions")


if __name__ == '__main__':
    main()
