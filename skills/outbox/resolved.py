#!/usr/bin/env python3
"""resolved.py -- plan the filing of outbox items that were resolved without being sent (CR-103).

Reads `_outbox/*/_manifest.md` and prints, as JSON (or `--text`), what `/outbox close
--all-resolved` would do. It NEVER moves, writes or deletes anything: the skill shows the plan,
the person confirms, and the skill does the moves.

What it reports:

- **resolved** -- every item whose status is `avskriven <date>` (withdrawn, CR-047), with its kind:
  - `superseded` when the status note starts with the declared form `ersatt av <item-name>`
    (optionally followed by `; ` and free text). The replacing item is looked up in `_outbox/` and
    then among closed items in the vault. A superseded draft is filed to the contact or project
    folder's `.archive/<YYMMDD>-<subject>-superseded/`, not beside the correspondence.
  - `withdrawn` otherwise: closed as today, into the contact or project folder.
  A superseded draft whose replacing item cannot be found is planned as `withdrawn` and the
  missing reference is reported -- never guessed.
- **undeclared_status** -- every manifest whose status is not one of the declared forms, with the
  closest declared one (`redo att skicka` -> `klar-att-skicka`). A report, never a rewrite.

The destination's PARENT folder (which contact or project) is not decided here: the manifest's
contact and project fields are passed through as hints, and `/outbox close` resolves them the way
it always has. What is decided here is only what can be decided from the files: the kind, the
archive sub-path, the outcome line and the timeline line for the replacing item.

Usage:
    resolved.py [--vault DIR | --outbox DIR] [--today YYYY-MM-DD] [--text]

The vault is found from --vault, else $VAULT_ROOT, else by walking up from the working directory
to the first folder holding `_outbox/`.
"""

from __future__ import annotations

import argparse
import datetime
import difflib
import json
import os
import re
import sys
from pathlib import Path

# --- vocabulary: identifiers English, the written words are data (CR-049) ---------------------

# Written labels a manifest field may carry. The first is the canonical one.
FIELD_LABELS = {
    "status": ["Status", "Läge", "State"],
    "status_note": ["Statusnot", "Status-note", "Status note", "Statusnote"],
    "contact": ["Kontakt", "Contact"],
    "project": ["Projekt", "Project"],
    "subject": ["Ämne", "Subject"],
}

# Declared status forms (the /outbox schema). Logical name -> accepted leading words.
DECLARED_STATUS = {
    "draft": ["draft", "utkast"],
    "ready": ["klar-att-skicka"],
    "sent": ["skickad"],
    "withdrawn": ["avskriven"],
    "archived": ["arkiverad"],
}
# The canonical written word for each, used when naming the closest declared form.
CANONICAL = {"draft": "draft", "ready": "klar-att-skicka", "sent": "skickad",
             "withdrawn": "avskriven", "archived": "arkiverad"}

# Words seen in undeclared statuses, mapped to the declared form they meant.
SYNONYMS = {
    "redo": "ready", "klar": "ready", "ready": "ready", "färdig": "ready",
    "skickat": "sent", "sent": "sent", "utskickad": "sent", "postad": "sent",
    "avbruten": "withdrawn", "withdrawn": "withdrawn", "struken": "withdrawn",
    "obsolet": "withdrawn", "obsolete": "withdrawn", "inaktuell": "withdrawn",
    "arkiverat": "archived", "archived": "archived",
    "utkast": "draft", "draft": "draft", "påbörjad": "draft",
}

# The superseded form of a withdrawn item's status note, and the lines written when filing it.
SUPERSEDED_NOTE = re.compile(r"^\s*ersatt av\s+`?([0-9]{6}[A-Za-z0-9._-]*)`?", re.IGNORECASE)
OUTCOME_LINE = "Ersatt av {item} ({status})"
TIMELINE_LINE = "- {date}: Ersätter {draft} ({draft_status})"
ARCHIVE_SUFFIX = "superseded"

FIELD_LINE = re.compile(r"^\*\*([^*:]+):\*\*\s*(.*?)\s*$")
DATE_PREFIX = re.compile(r"^([0-9]{6})-")


# --- reading ------------------------------------------------------------------------------------

def read_fields(text: str) -> dict[str, str]:
    """The manifest's labelled fields, keyed by logical name. Only the first block is read."""
    by_label = {label.lower(): logical
                for logical, labels in FIELD_LABELS.items() for label in labels}
    fields: dict[str, str] = {}
    for line in text.split("\n")[:60]:
        m = FIELD_LINE.match(line.strip())
        if not m:
            continue
        logical = by_label.get(m.group(1).strip().lower())
        if logical and logical not in fields:
            fields[logical] = m.group(2).strip()
    return fields


def section(text: str, heading: str) -> str:
    """The body of a `## <heading>` section, empty if absent or only a placeholder."""
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not m:
        return ""
    body = m.group(1).strip()
    if re.fullmatch(r"\*?\(?[^)]*(filled in|fylls i)[^)]*\)?\*?", body, re.IGNORECASE):
        return ""
    return body


def clean(status: str) -> str:
    """The status as written, without emphasis or code markers a hand edit may have wrapped it in."""
    return (status or "").strip().strip("*_`").strip()


def status_kind(status: str) -> str | None:
    """The declared logical status, or None when the written word is not declared."""
    first = clean(status).lower()
    for logical, words in DECLARED_STATUS.items():
        for word in words:
            if first == word or first.startswith(word + " ") or first.startswith(word + "\t"):
                return logical
    return None


# A status word right after one of these is negated: "ej skickad" means NOT sent, and suggesting
# `skickad` for it would propose the opposite of what the line says.
NEGATIONS = {"ej", "inte", "icke", "aldrig", "not", "never", "no", "un"}


def closest_declared(status: str) -> str | None:
    """The declared written form an undeclared status most likely meant.

    A word preceded by a negation is skipped, so `ej skickad` gets no suggestion rather than
    `skickad`. Better no hint than the opposite of what the person wrote.
    """
    words = re.findall(r"[\wåäöÅÄÖ-]+", clean(status).lower())
    usable = [w for i, w in enumerate(words) if not (i and words[i - 1] in NEGATIONS)
              and w not in NEGATIONS]
    for word in usable:
        if word in SYNONYMS:
            return CANONICAL[SYNONYMS[word]]
    candidates = [w for ws in DECLARED_STATUS.values() for w in ws]
    for word in usable:
        match = difflib.get_close_matches(word, candidates, n=1, cutoff=0.7)
        if match:
            return CANONICAL[next(k for k, ws in DECLARED_STATUS.items() if match[0] in ws)]
    return None


def _slug_of_project(text: str | None) -> str | None:
    """The folder-name part of a free-text Projekt field: `rollout-2026 (note); more` -> `rollout-2026`."""
    m = re.match(r"\s*`?([A-Za-z0-9][A-Za-z0-9._-]*)", text or "")
    return m.group(1) if m else None


def _name_words(text: str | None) -> set[str]:
    return {w.lower() for w in re.findall(r"[^\W\d_]{3,}", text or "", re.UNICODE)}


def destination_candidates(vault: Path, project: str | None, contact: str | None) -> list[dict]:
    """Folders in the vault a closed item could be filed under, most likely first.

    Not a decision: `/outbox close` picks, and asks when there is more than one or none. What this
    fixes is showing the manifest's free text (`rollout-2026 (action …); used by …`) as if it
    were a path. Only folders that exist are returned; dot-folders are never searched.
    """
    out: list[dict] = []
    slug = _slug_of_project(project)
    if slug:
        for pattern in (f"_projects/{slug}", f"*/_projects/{slug}", f"*/*/_projects/{slug}"):
            for hit in sorted(vault.glob(pattern)):
                if hit.is_dir() and not any(p.startswith(".") for p in hit.relative_to(vault).parts):
                    out.append({"kind": "project", "path": hit.relative_to(vault).as_posix()})
    # The person is named before any parenthesis, comma or dash: "Bob (Acme, CS)".
    # Matching the whole field also matched every folder carrying the company's name.
    name_part = re.split(r"[(,;]| — | -- ", contact or "", maxsplit=1)[0]
    wanted = _name_words(name_part)
    contacts = vault / "_contacts"
    if wanted and contacts.is_dir():
        for folder in sorted(contacts.iterdir()):
            if folder.is_dir() and not folder.name.startswith(".") \
                    and _name_words(folder.name.replace("-", " ")) & wanted:
                out.append({"kind": "contact", "path": folder.relative_to(vault).as_posix()})
    seen, unique = set(), []
    for c in out:
        if c["path"] not in seen:
            seen.add(c["path"]); unique.append(c)
    return unique


def subject_of(item: str) -> str:
    """`YYMMDD-recipient_subject` -> `subject`; the whole name after the date when there is no `_`."""
    rest = DATE_PREFIX.sub("", item)
    return rest.split("_", 1)[1] if "_" in rest else rest


# --- finding the replacing item -------------------------------------------------------------------

SKIP_DIRS = {".git", ".obsidian", ".trash"}


def find_replacing(vault: Path, outbox: Path, name: str) -> dict:
    """Where the replacing item is: still staged, or closed into the vault.

    A closed item has usually been renamed (its recipient prefix stripped), so it is found either
    by its original folder name or by a manifest that records where it came from (`_outbox/<name>`,
    which `close` writes into the timeline).
    """
    staged = outbox / name
    if (staged / "_manifest.md").is_file():
        text = _read(staged / "_manifest.md")
        return {"found": True, "where": "_outbox", "path": str(staged),
                "status": read_fields(text).get("status", "")}
    needle = f"_outbox/{name}"
    for root, dirs, files in os.walk(vault):
        here = Path(root)
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")
                   and here / d != outbox]
        if "_manifest.md" in files:
            if here.name == name:
                text = _read(here / "_manifest.md")
                return {"found": True, "where": "closed", "path": str(here),
                        "status": read_fields(text).get("status", "")}
            text = _read(here / "_manifest.md")
            if needle in text:
                return {"found": True, "where": "closed", "path": str(here),
                        "status": read_fields(text).get("status", "")}
    return {"found": False, "where": None, "path": None, "status": None}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


# --- planning -----------------------------------------------------------------------------------

def plan(vault: Path, outbox: Path, today: datetime.date) -> dict:
    resolved, undeclared, unreadable = [], [], []
    counts = {"items": 0, "withdrawn": 0, "superseded": 0}
    for folder in sorted(p for p in outbox.iterdir() if p.is_dir() and not p.name.startswith(".")):
        manifest = folder / "_manifest.md"
        if not manifest.is_file():
            continue
        counts["items"] += 1
        text = _read(manifest)
        if not text:
            unreadable.append(folder.name)
            continue
        fields = read_fields(text)
        status = fields.get("status", "")
        kind = status_kind(status)
        if status and kind is None:
            undeclared.append({"item": folder.name, "status": status,
                               "closest": closest_declared(status)})
        if kind != "withdrawn":
            continue

        counts["withdrawn"] += 1
        note = fields.get("status_note", "")
        entry = {
            "item": folder.name,
            "status": status,
            "note": note,
            "contact": fields.get("contact"),
            "project": fields.get("project"),
            "destinations": destination_candidates(vault, fields.get("project"), fields.get("contact")),
            "outcome_present": bool(section(text, "Utfall")),
            "kind": "withdrawn",
            "problems": [],
        }
        m = SUPERSEDED_NOTE.match(note)
        if m:
            replacing_name = m.group(1).rstrip(".,;:")
            replacing = find_replacing(vault, outbox, replacing_name)
            entry["replaced_by"] = replacing_name
            entry["replacing"] = replacing
            if replacing["found"]:
                counts["superseded"] += 1
                date = DATE_PREFIX.match(folder.name)
                entry["kind"] = "superseded"
                entry["archive_subdir"] = (
                    f".archive/{date.group(1) + '-' if date else ''}"
                    f"{subject_of(folder.name)}-{ARCHIVE_SUFFIX}")
                entry["outcome"] = OUTCOME_LINE.format(
                    item=replacing_name, status=replacing["status"] or "status unknown")
                entry["timeline_line_for_replacing"] = TIMELINE_LINE.format(
                    date=today.isoformat(), draft=folder.name, draft_status=status)
            else:
                entry["problems"].append(
                    f"ersatt av {replacing_name}: not in _outbox/ and no closed item records it; "
                    "filed as an ordinary withdrawn item")
        if entry["kind"] == "withdrawn" and not entry["outcome_present"]:
            entry["outcome"] = f"Skickades inte: {note}" if note else None
            if not note:
                entry["problems"].append("no status note and no outcome: cannot say why (CR-047)")
        resolved.append(entry)

    return {"outbox": str(outbox), "today": today.isoformat(), "counts": counts,
            "resolved": resolved, "undeclared_status": undeclared, "unreadable": unreadable}


# --- entry point --------------------------------------------------------------------------------

def find_vault(start: Path) -> Path | None:
    for candidate in [start, *start.parents]:
        if (candidate / "_outbox").is_dir():
            return candidate
    return None


def render_text(result: dict) -> str:
    out = [f"Outbox: {result['outbox']}", ""]
    out.append("RESOLVED, NOT SENT")
    if not result["resolved"]:
        out.append("  (none)")
    for e in result["resolved"]:
        if e["kind"] == "superseded":
            out.append(f"  {e['item']:<48} superseded by {e['replaced_by']}")
            out.append(f"      -> <folder>/{e['archive_subdir']}/")
        else:
            out.append(f"  {e['item']:<48} withdrawn")
        dests = e.get("destinations") or []
        if dests:
            for d in dests:
                out.append(f"      folder? {d['kind']:<8} {d['path']}")
        else:
            out.append("      folder? none found from Projekt/Kontakt -- /outbox close asks")
        for problem in e["problems"]:
            out.append(f"      ! {problem}")
    if result["undeclared_status"]:
        out += ["", "UNDECLARED STATUS (report only)"]
        for u in result["undeclared_status"]:
            hint = f" -> did you mean `{u['closest']}`?" if u["closest"] else ""
            out.append(f"  {u['item']:<48} `{u['status']}`{hint}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vault", help="vault root (default: $VAULT_ROOT or walk up for _outbox/)")
    ap.add_argument("--outbox", help="the _outbox folder, if not <vault>/_outbox")
    ap.add_argument("--today", help="YYYY-MM-DD for the timeline line (default: today)")
    ap.add_argument("--text", action="store_true", help="readable listing instead of JSON")
    args = ap.parse_args(argv)

    if args.outbox:
        outbox = Path(args.outbox).expanduser()
        vault = Path(args.vault).expanduser() if args.vault else outbox.parent
    else:
        root = (Path(args.vault).expanduser() if args.vault
                else Path(os.environ["VAULT_ROOT"]).expanduser() if os.environ.get("VAULT_ROOT")
                else find_vault(Path.cwd()))
        if root is None:
            print("no vault found: pass --vault or set VAULT_ROOT", file=sys.stderr)
            return 2
        vault, outbox = root, root / "_outbox"
    if not outbox.is_dir():
        print(f"no outbox at {outbox}", file=sys.stderr)
        return 2

    today = (datetime.date.fromisoformat(args.today) if args.today else datetime.date.today())
    result = plan(vault, outbox, today)
    print(render_text(result) if args.text else json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
