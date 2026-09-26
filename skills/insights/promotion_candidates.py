#!/usr/bin/env python3
"""List the candidate groups for hypothesis -> rule promotion (CR-100).

Compile Pass 2 is part arithmetic, part judgement. This script is the arithmetic,
and only the arithmetic, so that compile and a review surface see the same
candidates instead of each implementing the gates and drifting apart:

    python3 promotion_candidates.py <folder-or-vault>            # JSON
    python3 promotion_candidates.py <folder-or-vault> --text     # readable listing
    python3 promotion_candidates.py <folder> --threshold 3 --topic-tags seo,payments

It never judges whether entries make the same claim, never splits a group, never
checks for contradictions and never writes. Those are judged: by the model in
`/insights compile`, or by a person on a review surface (CR-100).

THE GATES (compile Pass 2, steps 1-3, the deterministic part)
  candidate  confidence is not `rule` (absent, `hypothesis`, or a legacy
             high/medium/low value from early extractions), status active or
             absent, type in decision | preference | learning | pattern, has an id
  pair       same folder, same type, and >= 2 shared tags OR the same primary tag
             (first in tags[]). Tags compare case-insensitively.
  group      a connected component of the pair graph (see GROUPING below)
  threshold  size >= workflows.knowledge_extraction.evolution.compile_threshold
             (default 3; --threshold overrides)
  marks      distinct-date count; `single_session` when every member shares one
             date (compile skips those, CR-098); shared tags, each marked
             `topic: true|false` ONLY when insight_topic_tags is configured

GROUPING: connected components, not greedy seeding. Tag overlap is not transitive
(A~B on two tags, B~C on two others, A and C share nothing). A component keeps
A, B and C together; a greedy seed keeps whichever pair it met first, so the
result depends on file order and a pair can vanish without anyone seeing it.
Pass 2 already has a judged step for exactly this -- "split before promoting"
(CR-098) -- so the generator errs toward the superset and leaves the split to
the reader. A missed candidate is invisible; an oversized one is split in plain
view.

GROUP KEY: sha256 over the members sorted by id, one line per member:
    f"{id}\\t{date}\\t{summary}\\t{','.join(sorted(tags))}"
joined with "\\n", UTF-8, lowercase hex. Any change to a member's date, summary
or tags -- or a member added, removed or superseded -- gives a new key. A review
(`promotion_review`) records the key it judged; compile honours it only while
the key still matches.

REVIEW STATE: reviews are read from `promotion_review` on any member. A review's
key is recomputed over the ids it recorded (`group`); a mismatch, or a recorded id
that is gone or no longer a candidate, makes it `stale`.
  - recorded ids == the group's ids: the group's state is the decision
    (`approved` / `rejected`) while the key matches, else `stale`.
  - recorded ids are a SUBSET: valid only as a split, i.e. the review carries
    `split_from` equal to the CURRENT group's key. Then it is reported under
    `subset_reviews` with its decision. Without `split_from`, or when the group
    has changed since the split (a member added, edited or superseded), it is
    `stale`, and so is the group: an entry added after a review may be the very
    reversal the contradiction check exists for, so a review never silently
    narrows itself to the entries that happen to still match.
  - no review on any member: `unreviewed`.

CONFIG: the nearest `.claude/ops-config.yaml` or `_ops.yaml` walking up from the
target that sets workflows.knowledge_extraction.evolution; --config names one.
Flags override the file.
"""
import argparse, datetime, hashlib, json, os, sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("needs pyyaml -- run with a python that has it")

PROMOTABLE = ("decision", "preference", "learning", "pattern")
DEFAULT_THRESHOLD = 3
REVIEW_DECISIONS = ("approved", "rejected")


# --- reading -------------------------------------------------------------

def _evolution(cfg: dict) -> dict:
    return (((cfg or {}).get("workflows") or {}).get("knowledge_extraction") or {}).get(
        "evolution") or {}


def find_config(start: Path) -> dict:
    """Nearest config above `start` that declares the evolution block."""
    here = start if start.is_dir() else start.parent
    for folder in [here, *here.parents]:
        for name in (Path(".claude") / "ops-config.yaml", Path("_ops.yaml")):
            f = folder / name
            if f.is_file():
                try:
                    evo = _evolution(yaml.safe_load(f.read_text(encoding="utf-8")) or {})
                except (OSError, yaml.YAMLError):
                    continue
                if evo:
                    return evo
    return {}


def insight_files(root: Path):
    """Every _insights.yaml under root; dot-folders (incl. .archive/) are skipped."""
    if root.is_file():
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        if "_insights.yaml" in filenames:
            yield Path(dirpath) / "_insights.yaml"


def _date(value) -> str:
    # YAML reads an unquoted ISO date (2026-04-01) as a date object. The schema says
    # YYMMDD; normalise rather than fail, so one hand-edited entry cannot break a run.
    if isinstance(value, datetime.date):
        return value.strftime("%y%m%d")
    text = str(value if value is not None else "").strip()
    return text.zfill(6) if text.isdigit() and len(text) < 6 else text


def _tags(entry: dict) -> list:
    raw = entry.get("tags") or []
    if not isinstance(raw, list):
        raw = [raw]
    return [str(t).strip().lower() for t in raw if str(t).strip()]


def is_candidate(entry: dict) -> bool:
    if not isinstance(entry, dict) or not isinstance(entry.get("id"), int):
        return False
    if str(entry.get("confidence") or "").strip().lower() == "rule":
        return False
    if str(entry.get("status") or "active").strip().lower() != "active":
        return False
    return str(entry.get("type") or "").strip().lower() in PROMOTABLE


# --- the arithmetic ------------------------------------------------------

def paired(a: dict, b: dict) -> bool:
    ta, tb = _tags(a), _tags(b)
    if not ta or not tb:
        return False
    if ta[0] == tb[0]:
        return True
    return len(set(ta) & set(tb)) >= 2


def components(entries: list) -> list:
    """Connected components of the pair graph, members sorted by (date, id)."""
    parent = list(range(len(entries)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            if paired(entries[i], entries[j]):
                parent[root(i)] = root(j)
    groups = {}
    for i, e in enumerate(entries):
        groups.setdefault(root(i), []).append(e)
    return [sorted(g, key=lambda e: (_date(e.get("date")), e["id"])) for g in groups.values()]


def group_key(members: list) -> str:
    lines = []
    for e in sorted(members, key=lambda e: e["id"]):
        lines.append(f"{e['id']}\t{_date(e.get('date'))}\t{str(e.get('summary') or '')}\t"
                     f"{','.join(sorted(_tags(e)))}")
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _review_of(entry: dict):
    review = entry.get("promotion_review")
    return review if isinstance(review, dict) else None


def review_states(members: list, by_id: dict) -> tuple:
    """(group state, the matching review or None, subset reviews)."""
    ids = sorted(e["id"] for e in members)
    current = group_key(members)
    own, subsets = None, []
    for e in members:
        review = _review_of(e)
        if not review:
            continue
        recorded = review.get("group") or [e["id"]]
        try:
            recorded = sorted(int(i) for i in recorded)
        except (TypeError, ValueError):
            recorded = []
        decision = str(review.get("decision") or "").strip().lower()
        judged = [by_id.get(i) for i in recorded]
        if (not recorded or any(m is None for m in judged)
                or decision not in REVIEW_DECISIONS):
            state = "stale"
        else:
            state = decision if group_key(judged) == str(review.get("group_key") or "") else "stale"
        if recorded != ids and state != "stale" and review.get("split_from") != current:
            state = "stale"          # a subset is valid only as a split of THIS group
        record = {"on_entry": e["id"], "decision": decision or None,
                  "date": _date(review.get("date")) or None, "by": review.get("by"),
                  "group": recorded, "recorded_key": review.get("group_key"),
                  "split_from": review.get("split_from"),
                  "reason": review.get("reason"), "state": state}
        if recorded == ids:
            own = record
        else:
            subsets.append(record)
    if own:
        state = own["state"]
    elif any(r["state"] == "stale" for r in subsets):
        state = "stale"
    else:
        state = "unreviewed"
    return state, own, subsets


def shared_tags(members: list, topic_tags) -> list:
    counts = {}
    for e in members:
        for t in set(_tags(e)):
            counts[t] = counts.get(t, 0) + 1
    out = []
    for t in sorted(t for t, n in counts.items() if n >= 2):
        item = {"tag": t, "members": counts[t]}
        if topic_tags is not None:
            item["topic"] = t in topic_tags
        out.append(item)
    return out


def scan(root: Path, threshold: int, topic_tags) -> dict:
    report = {"root": str(root), "threshold": threshold,
              "topic_tags_configured": topic_tags is not None,
              "folders_scanned": 0, "unreadable": [], "candidate_groups": []}
    for f in insight_files(root):
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as error:
            report["unreadable"].append({"file": str(f), "error": type(error).__name__})
            continue
        report["folders_scanned"] += 1
        entries = [e for e in (doc.get("insights") or []) if is_candidate(e)]
        by_id = {e["id"]: e for e in entries}
        folder = f.parent
        try:
            rel = str(folder.relative_to(root)) if root.is_dir() else str(folder)
        except ValueError:
            rel = str(folder)
        for kind in PROMOTABLE:
            same_type = [e for e in entries if str(e.get("type")).strip().lower() == kind]
            for members in components(same_type):
                if len(members) < threshold:
                    continue
                dates = sorted({_date(e.get("date")) for e in members})
                state, own, subsets = review_states(members, by_id)
                report["candidate_groups"].append({
                    "folder": rel,
                    "type": kind,
                    "ids": [e["id"] for e in members],
                    "canonical_id": members[0]["id"],
                    "size": len(members),
                    "distinct_dates": len(dates),
                    "single_session": len(dates) == 1,
                    "shared_tags": shared_tags(members, topic_tags),
                    "group_key": group_key(members),
                    "review_state": state,
                    "review": own,
                    "subset_reviews": subsets,
                    "members": [{"id": e["id"], "date": _date(e.get("date")),
                                 "summary": e.get("summary"), "tags": _tags(e),
                                 "source": e.get("source")} for e in members],
                })
    report["candidate_groups"].sort(key=lambda g: (-g["size"], g["folder"], g["type"]))
    return report


# --- output --------------------------------------------------------------

def as_text(report: dict) -> str:
    lines = [f"{len(report['candidate_groups'])} candidate group(s) in "
             f"{report['folders_scanned']} folder(s), threshold {report['threshold']}"]
    if report["unreadable"]:
        lines.append(f"{len(report['unreadable'])} file(s) could not be read")
    for g in report["candidate_groups"]:
        flags = []
        if g["single_session"]:
            flags.append("single session")
        if g["review_state"] != "unreviewed":
            flags.append(g["review_state"])
        tags = ", ".join(t["tag"] + (" (topic)" if t.get("topic") else "") for t in g["shared_tags"])
        lines.append("")
        lines.append(f"{g['folder']}  {g['type']}  {g['size']} entries, "
                     f"{g['distinct_dates']} date(s){'  [' + '; '.join(flags) + ']' if flags else ''}")
        lines.append(f"  shared: {tags}")
        for m in g["members"]:
            lines.append(f"  #{m['id']} {m['date']}  {m['summary']}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Candidate groups for insight promotion (CR-100). Never writes.")
    ap.add_argument("target", help="a folder, a vault root, or one _insights.yaml")
    ap.add_argument("--threshold", type=int, help="overrides compile_threshold")
    ap.add_argument("--topic-tags", help="comma-separated; overrides insight_topic_tags")
    ap.add_argument("--config", help="an ops config to read instead of walking up")
    ap.add_argument("--text", action="store_true", help="readable listing instead of JSON")
    args = ap.parse_args(argv)

    target = Path(args.target).expanduser()
    if not target.exists():
        print(f"no such path: {target}", file=sys.stderr)
        return 2
    if args.config:
        evo = _evolution(yaml.safe_load(Path(args.config).read_text(encoding="utf-8")) or {})
    else:
        evo = find_config(target)
    threshold = args.threshold or int(evo.get("compile_threshold") or DEFAULT_THRESHOLD)
    if args.topic_tags is not None:
        topic = {t.strip().lower() for t in args.topic_tags.split(",") if t.strip()}
    elif evo.get("insight_topic_tags"):
        topic = {str(t).strip().lower() for t in evo["insight_topic_tags"]}
    else:
        topic = None

    report = scan(target, threshold, topic)
    print(as_text(report) if args.text
          else json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
