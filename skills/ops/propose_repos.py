#!/usr/bin/env python3
"""CR-151: the repository list is derived from the status reports, and PROPOSED.

    python3 propose_repos.py --dir <project>/meetings [--days 14] [--date YYMMDD]
    python3 propose_repos.py --dir <project>/meetings --write --confirm <repo>[,<repo>...]

A project declared ONE repository -- its own portal -- so the agenda, the movement
block and the digest read that one only. The release it was working toward depended on
at least seven others, and the only place that said so was the daily status report: in
a table of backend merges, in the release-branch paragraphs, in the blocker list. A
count taken on the declared repository alone showed several people with nothing merged;
over the others the same people had merged work every week. The first reading had been
wrong and nobody had been told.

Counting mentions across twelve consecutive daily reports gave the shape in minutes --
one repository in every report, two in all but one, then a middle group named on five to
eleven days, then nothing that was not an ordinary word. The list could have been
proposed from the reports rather than from memory, which is what this does.

**Nothing is written without a yes.** The default run prints a proposal and exits; the
block is written only by a second run naming, repository by repository, what the
operator confirmed. That is the CR's central safety property: a helper that edits a
project's config from its own reading of a report is a helper nobody can trust with a
config again, however good the reading was.

Reads local files only -- the declared `vault_reports:` series (CR-116) -- and resolves
WHICH files a declaration names through `build_movement`, never a second resolver.
"""
import argparse
import datetime as dt
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_movement as bm  # noqa: E402

# The read scope a proposed entry gets (proposal 4). Deliberately not `issues`: a
# repository's issues are its team's working surface, and reading them into an agenda
# turns another team's queue into this meeting's business. Pulls and releases say what
# SHIPPED, which is what the reports named the repository for in the first place.
DEFAULT_READS = ["pulls", "releases"]
# Days without a mention before a re-run names a declared entry as quiet (proposal 5).
# Longer than the default window, so an entry is never reported quiet on the strength
# of a window that could not have seen it.
QUIET_DAYS = 30
# Mentions on more than this many days make an undeclared repository a pre-flight
# warning (proposal 6). Two days is a coincidence; four is a pattern. Below the
# middle group the measured reports showed (five to eleven days), so the warning fires
# before the gap has cost a reading.
WARN_DAYS = 3

# `owner/repo` -- the one unambiguous spelling, and the only one that carries its own
# organisation. Allowed around it: whitespace, brackets, a markdown link, a cell wall.
# A trailing `.git` or a path under the repository (`acme/app/blob/main/x.py`) reduces
# to the repository, because the fact wanted is WHICH repository, not which file.
# A repository name may hold a dot (`acme/docs.site`), so the name class allows one --
# which means a slug at the end of a sentence ends in the sentence's full stop. Trimmed
# by `_trim`, not by narrowing the class: `warehouse.` and `warehouse` counted as two
# repositories, each on a fraction of the days, which is the one way this count can be
# wrong without looking wrong.
_SLUG = re.compile(r"(?<![\w/.-])([A-Za-z0-9][\w.-]*)/([A-Za-z0-9][\w.-]*?)(?:\.git)?(?![\w.-])")
# A forge host written in front of the slug (defect pass): a report that writes
# `github.com/acme/queue/pull/12` -- the form anybody gets by copying a browser's
# address bar -- offers `github.com/acme` to `_SLUG` first, so the ORGANISATION was
# proposed as a repository under the slug `github.com/acme` and the repository itself
# was never counted. The host is stripped before the line is scanned, which also makes
# the docstring above true: the path under the repository then reduces to the
# repository, as it claims. A scheme is stripped with it so `https://` leaves no `//`
# for the slug reader to trip on.
_FORGE = re.compile(r"\b(?:https?://)?(?:www\.)?"
                    r"(?:github\.com|gitlab\.com|bitbucket\.org|codeberg\.org)/", re.I)
# `repo#12`, `repo #12`, `repo PR #12`, `repo pull #12`. The bare name only -- a report
# writes the short name far more often than the slug, which is why a count on slugs
# alone found two repositories where the reports named eight.
_BARE_ITEM = re.compile(r"(?<![\w/.-])([a-z][\w.-]{2,})\s*(?:(?:PR|pull|pull\s+request|issue)s?\s*)?#(\d+)",
                        re.I)
# A table row's first cell, for proposal 1's third shape: a table of merges whose rows
# are repositories. `_table_repos` decides whether the column IS repositories.
_RULE = re.compile(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$")
# A first-column header that says the column holds repositories. Without this the
# first cell of every table in the report -- an area, a person, a date -- would be
# counted as a repository, which is the failure mode that makes a count worthless.
_REPO_HEADER = re.compile(r"^\**\s*(?:source\s+)?repos?(?:itor(?:y|ies))?\s*\**$", re.I)
# A first cell that can be a repository NAME: lower-case, hyphen or dot or underscore,
# no spaces. A cell with a space in it is prose, a person or an area.
_NAME_CELL = re.compile(r"^\**\s*`?([a-z][a-z0-9._-]{2,})`?\s*\**$")
# A name whose last dot-segment is a file extension: `deploy.sh`, `migrate.py`,
# `schema.sql` (defect pass). A repository name may carry a dot (`acme/docs.site`), so
# the classes above allow one -- which let a shell command in a report propose
# `deploy.sh` as a repository, since `_trim` strips `.-_` from the ends and never a
# segment. Matched on the extension rather than on a list of commands: the set of file
# names a status report can hold is open, and the set of extensions that are never a
# repository's last segment is not.
_FILE_EXT = re.compile(r"\.(?:sh|py|js|ts|tsx|jsx|rb|go|rs|java|kt|swift|c|h|cpp|sql|ya?ml"
                       r"|json|toml|ini|cfg|conf|md|txt|csv|tsv|log|lock|env|sock|pid"
                       r"|png|jpe?g|gif|svg|pdf|zip|tar|gz|tgz|html?|css|scss)$", re.I)
# A word that is an ordinary English word in a status report before it is a repository
# name. These are the "probably prose" cases the CR names: a repository called
# `scripts`, a word `billing`. The list is NOT the test -- the test is proposal 2's
# separate listing, and a word here is still SHOWN, just under the other heading, so
# the operator can confirm it. Silently dropping it would be the worse error: the
# repository that is genuinely called `scripts` would never be proposed at all.
_PROSE_WORDS = {
    "and", "api", "app", "backend", "billing", "build", "builds", "changes", "config",
    "database", "deploy", "docs", "frontend", "infra", "logs", "main", "merge",
    "merges", "release", "releases", "report", "reports", "scripts", "server",
    "service", "services", "site", "staging", "status", "test", "tests", "web",
}
# Words that are never a repository in `owner/repo` position: a date, a fraction, a
# path fragment a report writes in prose (`and/or`). A slug whose owner OR name is one
# of these is dropped before counting rather than listed as prose: it is not a
# candidate anybody would confirm, and a proposal padded with them is not read.
_NOT_SLUG = {"and", "or", "a", "the", "n", "either", "yes", "no", "am", "pm", "he", "she", "they"}


def _trim(name: str) -> str:
    """A matched name with sentence punctuation off its end -- `warehouse.` -> `warehouse`.

    A repository name may legitimately carry a dot, so the match has to allow one; a slug
    ending a sentence then ends in the full stop. Left in, `acme/warehouse.` and
    `acme/warehouse` count as two repositories on a fraction of the days each, which is a
    wrong count that does not look wrong.
    """
    return name.strip(".-_")


def working_days_back(end: dt.date, days: int) -> dt.date:
    """The date `days` WORKING days before `end`, inclusive of `end` itself.

    The window is working days because the reports are (proposal 1's default is 14
    working days): counting 14 calendar days back from a Monday reaches ten reports,
    and a repository named in every one of them then reads as named on ten days out of
    fourteen -- a shape that says *sometimes* about a repository that is in every
    report there is.
    """
    d, left = end, max(1, days)
    while left > 1:
        d -= dt.timedelta(days=1)
        if d.weekday() < 5:
            left -= 1
    return d


def window_files(cf: dict, r: dict, start: dt.date, end: dt.date) -> list[tuple[dt.date, Path]]:
    """Every dated file of one declared `vault_reports:` series inside the window.

    `build_movement` owns `vault_reports:` resolution (the walk-up from the project
    root, `current:` before `pattern:`, newest by sort) and this reuses it rather than
    keeping a second answer: a window that resolved the directory differently from
    `--check` would count mentions in a folder whose age nobody is reporting.

    Where `vault_report_files` answers *which file is the status now*, a window asks a
    different question -- *which files cover these days* -- so the pattern is applied
    over the directory and each name dated with `filename_date()`, the same reader
    `--check` dates a report with. A file whose name carries no date cannot be placed
    in a window and is left out; `current:` is the status, not a day, and is left out
    for the same reason. Both are reported by the caller, never silently dropped.
    """
    d = bm.vault_report_dir(cf, r) if r.get("dir") else None
    if not d:
        return []
    pat = r.get("pattern") or r"^$"
    out = []
    for f in sorted(x for x in d.iterdir() if x.is_file() and re.match(pat, x.name)):
        when = bm.filename_date(f.name)
        if when is not None and start <= when <= end:
            out.append((when, f))
    return sorted(out)


def _table_repos(lines: list[str]) -> list[tuple[int, str]]:
    """Proposal 1's third shape: first cells of tables whose first column IS repositories.

    `(line number, name)`. The header gate is the whole design: a status report is
    mostly tables, and a reader that took the first cell of each would count areas,
    people and dates as repositories. A table of backend merges headed `Repository` is
    exactly where the measured reports named the repositories nothing had declared.
    """
    out: list[tuple[int, str]] = []
    header: list[str] | None = None
    in_body = False
    fenced = False
    for i, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            fenced, header, in_body = not fenced, None, False
            continue
        if fenced:
            continue                  # a table SAMPLE inside a fence is not a report's table
        cells = _cells(line)
        if cells is None:
            header, in_body = None, False
            continue
        if _RULE.match(line):
            in_body = header is not None and bool(header) and bool(_REPO_HEADER.match(header[0]))
            continue
        if not in_body:
            header = cells
            continue
        if cells and (m := _NAME_CELL.match(cells[0])):
            out.append((i, _trim(m.group(1)).lower()))
    return out


def _cells(line: str) -> list[str] | None:
    """A markdown table row's cells, or None when the line is not one."""
    s = line.strip()
    if not s.startswith("|"):
        return None
    return [c.strip() for c in s.strip("|").split("|")]


def mentions(text: str) -> dict[str, dict]:
    """Every repository one report names, by lower-cased short name.

    Per name: `slugs` (the `owner/repo` spellings seen, which is how an entry gets a
    `url:` at all), `items` (the pull-request and issue numbers cited) and `lines` (the
    line numbers, so a purpose can be quoted from the report's own words).

    Keyed on the SHORT name, not the slug, because the three shapes name the same
    repository three ways -- `acme/app`, `app#12`, a cell `app` -- and a count that
    kept them apart reports one repository as three, each on a third of the days.

    A FENCED block is skipped (defect pass), the way `check_links` and the decisions
    reader in `hygiene_check.py` skip one: inside a fence a report writes the shell
    commands and the paths of a release, and `cd acme/infra`, `scripts/deploy.sh` and a
    config path then arrive as repository candidates on every day the runbook is pasted
    -- which is every day, so they rank above the repositories that are really there.
    """
    lines = text.splitlines()
    found: dict[str, dict] = {}

    def note(name: str, i: int, slug: str | None = None, item: int | None = None):
        e = found.setdefault(name, {"slugs": set(), "items": set(), "lines": set()})
        e["lines"].add(i)
        if slug:
            e["slugs"].add(slug)
        if item is not None:
            e["items"].add(item)

    fenced = False
    for i, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        # The forge host comes off before the slug reader sees the line, so a copied
        # browser URL names the repository and not its organisation (defect pass).
        line = _FORGE.sub("", line)
        for m in _SLUG.finditer(line):
            owner, name = _trim(m.group(1)), _trim(m.group(2))
            if not owner or not name:
                continue
            if owner.lower() in _NOT_SLUG or name.lower() in _NOT_SLUG:
                continue
            if owner.isdigit() or name.isdigit():
                continue              # a date or a fraction, not a repository
            if _FILE_EXT.search(name):
                continue              # a path, not a repository: `scripts/deploy.sh`
            note(name.lower(), i, slug=f"{owner}/{name}")
        for m in _BARE_ITEM.finditer(line):
            # A slug already matched here carries its own `#number` in some reports
            # (`acme/app#12`); the bare leg would then record `app` a second time,
            # which is harmless -- same key -- and records the item number, which the
            # slug leg cannot see.
            if (nm := _trim(m.group(1)).lower()) and not _FILE_EXT.search(nm):
                note(nm, i, item=int(m.group(2)))
    for i, name in _table_repos(lines):
        if name:
            note(name, i, None)
    return found


def purpose_from(text: str, line_no: int) -> str:
    """A one-line purpose in the report's OWN WORDS, from the line that named it.

    Copied, never composed: a purpose a helper wrote for a repository it has never
    read is a guess in a config file, and a guess in a config file is indistinguishable
    from a decision. The operator edits it; what is offered is what the report said.
    """
    lines = text.splitlines()
    if not 1 <= line_no <= len(lines):
        return ""
    s = lines[line_no - 1].strip()
    if (cells := _cells(s)) is not None:
        # In a table the useful words are the row's, minus its first cell (the
        # repository's own name) and minus any cell that is only a number.
        s = " · ".join(c.strip("*` ") for c in cells[1:]
                       if c.strip("*` ") and not c.strip("*` ").isdigit())
    s = re.sub(r"^[#>\-*\s]+", "", s).strip("*` ")
    s = re.sub(r"\s+", " ", s)
    return s[:120]


def count_window(cf: dict, start: dt.date, end: dt.date):
    """Repository mentions over the window: (counts, read, problems).

    `counts` maps short name -> {days, items, slugs, purpose}; `days` is the number of
    DAYS a repository was named, not the number of mentions. A repository named nine
    times in one report is named on one day, and the day count is the number the
    measured reading turned on: one repository in every report, two in all but one.

    `read` is the (date, path) list actually read, so the proposal can state its basis.
    `problems` names what could not be read -- an unreadable file, a declared series
    with no directory. A report that was not read is reported, never counted as a
    report that named nothing.
    """
    counts: dict[str, dict] = {}
    read: list[tuple[dt.date, Path]] = []
    problems: list[str] = []
    for r in ((cf.get("ext") or {}).get("vault_reports") or []):
        if not isinstance(r, dict) or not r.get("dir"):
            continue
        nm = r.get("name") or r.get("dir")
        if bm.vault_report_dir(cf, r) is None:
            problems.append(f"{nm}: declared directory not found — {r['dir']}")
            continue
        files = window_files(cf, r, start, end)
        if not files:
            problems.append(f"{nm}: no dated report in the window")
            continue
        for when, f in files:
            try:
                text = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                problems.append(f"{f.name}: not read — {type(e).__name__}")
                continue
            read.append((when, f))
            for name, hit in mentions(text).items():
                e = counts.setdefault(name, {"days": set(), "items": set(),
                                             "slugs": set(), "purpose": ""})
                e["days"].add(when)
                e["items"] |= hit["items"]
                e["slugs"] |= hit["slugs"]
                if not e["purpose"]:
                    e["purpose"] = purpose_from(text, min(hit["lines"]))
    return counts, sorted(read), problems


def probably_prose(name: str, info: dict) -> bool:
    """Proposal 2: a word that matches a repository name but is probably just a word.

    A candidate is prose when it was never written as `owner/repo`, never carried an
    item number, and is an ordinary word a status report uses. Any ONE of those three
    makes it a repository: `acme/scripts` is a repository however ordinary `scripts` is
    as a word, and `billing#214` cites an item in something.
    """
    if info.get("slugs") or info.get("items"):
        return False
    return name in _PROSE_WORDS


def declared_slugs(cf: dict) -> dict[str, str]:
    """The project's declared repositories: short name (lower) -> slug.

    Resolved through `build_movement.repo_slug`, the reader `from_repo` and the
    movement block already match a declaration with -- so a repository the agenda
    reads can never read as undeclared here.
    """
    out = {}
    for r in ((cf.get("ext") or {}).get("repos") or []):
        if not (isinstance(r, dict) and r.get("url")):
            continue
        slug = bm.repo_slug(str(r["url"]))
        short = (r.get("name") or slug.rsplit("/", 1)[-1]).strip().lower()
        out[short] = slug
    return out


def undeclared(cf: dict, counts: dict[str, dict], min_days: int = WARN_DAYS) -> list[tuple[str, int]]:
    """Proposal 6: repositories the reports name on more than `min_days` days and the
    project does not declare -- `(name, days)`, most days first.

    Strictly more than `min_days`: the threshold is the number of days that is still a
    coincidence, so a repository on exactly that many is not yet a finding.
    """
    have = declared_slugs(cf)
    out = [(n, len(i["days"])) for n, i in counts.items()
           if n not in have and len(i["days"]) > min_days and not probably_prose(n, i)]
    return sorted(out, key=lambda t: (-t[1], t[0]))


def quiet(cf: dict, counts: dict[str, dict], window_days: int) -> list[str]:
    """Proposal 5: declared repositories the window's reports never named.

    Named, NEVER REMOVED -- and only when the window is long enough to mean something:
    a two-day window that names one repository is not evidence that the other seven are
    quiet. A repository can be declared for a reason no report mentions (a release
    archive, a config repository touched twice a year), which is exactly why removing
    one is the operator's decision and not this script's.
    """
    if window_days < QUIET_DAYS:
        return []
    return sorted(n for n in declared_slugs(cf) if n not in counts)


def block(entries: list[tuple[str, dict]], basis: str, today: dt.date,
          known: dict[str, str] | None = None) -> str:
    """The `repos:` YAML for the confirmed entries, with the comment naming its basis.

    The comment is proposal 3's requirement and it is not decoration: a reader who
    meets this block in six months has to be able to tell a declaration somebody made
    from one a script proposed and somebody confirmed, and on what reading. The slug
    is the report's own `owner/repo` when a report wrote one; when no report did, the
    entry is written with the name and a marker, because inventing an organisation
    would be the one way this helper could write something false into a config.
    """
    out = [f"  # Proposed from {basis}, confirmed {today.isoformat()} (CR-151).",
           "  # Day counts are days a report NAMED the repository, not commits.",
           "  repos:"]
    for name, info in entries:
        slug = sorted(info.get("slugs") or [])[0] if info.get("slugs") else (known or {}).get(name)
        days, items = len(info.get("days") or ()), len(info.get("items") or ())
        if slug:
            out.append(f"    - url: github.com/{slug}")
        else:
            out.append(f"    - url: ORGANISATION-NOT-IN-THE-REPORTS/{name}   # fill in the organisation")
        out.append(f"      name: {name}")
        out.append(f"      reads: [{', '.join(DEFAULT_READS)}]")
        if info.get("purpose"):
            out.append(f"      purpose: \"{info['purpose'].replace(chr(34), chr(39))}\"")
        out.append(f"      # named on {days} day(s), {items} item(s) cited")
    return "\n".join(out)


class UnparseableResult(Exception):
    """An insertion whose result would not load as YAML, or would lose an entry.

    Raised instead of returning the text, so a caller cannot write a config that no
    longer parses. See `insert_repos`.
    """


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _repos_key(lines: list[str], top: int, end: int) -> int | None:
    """The index of external_systems' OWN `repos:` key, or None.

    Its own, which is the whole point (defect pass): the first reader matched `repos:`
    anywhere in the block at any indent, so a `repos:` nested one level deeper -- under
    a `github:` sub-key, say -- was matched and the entries were spliced at that
    deeper key's item indent, under a mapping. The result did not parse at all.

    The block's own keys are the shallowest indented lines in it; `repos:` is that key
    only when it sits at exactly that depth. The value after the colon is NOT part of
    this test, because `repos: []` is the same key as `repos:` and the first reader's
    `^\\s+repos:\\s*$` saw neither it nor the no-key case -- so it opened a SECOND
    `repos:` key above the first. YAML with a duplicate key either fails to parse or
    silently keeps one of the two, and the one it kept was the empty hand-written list:
    the operator's confirmed entries were written to the file and then ignored by every
    reader of it.
    """
    body = [i for i in range(top + 1, end) if lines[i].strip()]
    own = min((_indent(lines[i]) for i in body), default=None)
    if own is None:
        return None
    return next((i for i in body
                 if _indent(lines[i]) == own and re.match(r"^\s*repos:", lines[i])), None)


def insert_repos(text: str, entries: str) -> str:
    """The config's text with `entries` added under `external_systems:`.

    A TEXT insertion, not a YAML round-trip: the configs this edits are hand-written
    and carry the comments that say why each declaration is there, and a dump would
    return the same data with every one of those comments gone. The operator would
    then be reading a diff about repositories that had also silently deleted the
    reasons for everything else.

    The shapes, which are the ones a hand-written config is actually in:

    * `repos:` as its own line with items under it -- the entries go after its last
      item, so a confirmed addition never shadows a hand-written declaration.
    * `repos: []`, `repos: {}` or `repos:` with any other inline value -- the inline
      value is REPLACED by a block list holding the confirmed entries. An empty inline
      list declares nothing, so nothing is lost; a non-empty inline value is refused
      below rather than guessed at.
    * no `repos:` key -- one is opened at the depth external_systems' other keys are at.
    * no `external_systems:` block -- the block is appended with its own key.
    * a `repos:` nested deeper inside external_systems -- not this key, see `_repos_key`.

    **The result is parsed before it is returned**, and `UnparseableResult` is raised
    rather than text returned when it does not load, or when the repository list that
    comes back is not the one intended. This is a text edit to a human-written file and
    the previous reader's failures all had the same shape -- plausible text, YAML that
    either failed or quietly dropped the operator's confirmation -- so the guard lives
    HERE, where no caller can be written that skips it. The CR's point is that the
    operator stays in control, and a config handed back unloadable takes control away
    more completely than writing nothing would.
    """
    # Under an existing `repos:`, the basis comments belong at the ITEMS' indent, not
    # the key's: a comment outdented to the key reads as a comment about the whole
    # block, which is the one thing it is not -- the hand-written entries above it were
    # not proposed by anything.
    lines = text.splitlines()
    top = next((i for i, l in enumerate(lines) if re.match(r"^external_systems:\s*$", l)), None)
    if top is None:
        out = text.rstrip("\n") + "\n\nexternal_systems:\n" + entries.rstrip("\n") + "\n"
        return _checked(text, out, entries)
    # The end of the `external_systems:` block: the next line at column zero.
    end = next((i for i in range(top + 1, len(lines))
                if lines[i].strip() and not lines[i][0].isspace()), len(lines))
    repos = _repos_key(lines, top, end)
    if repos is None:
        # No key of its own. Re-indent the proposal to whatever depth this block's
        # other keys use, since a config indented four spaces would otherwise get a
        # two-space `repos:` sibling -- a different key at a different level.
        depth = min((_indent(lines[i]) for i in range(top + 1, end) if lines[i].strip()),
                    default=2)
        out = lines[:top + 1] + _reindent(entries, depth).splitlines() + lines[top + 1:]
        return _checked(text, "\n".join(out) + "\n", entries)
    depth = _indent(lines[repos])
    inline = lines[repos].split(":", 1)[1].strip()
    # The items go at the depth this file's existing items are at, not at a fixed two
    # past the key: a config indented four spaces throughout puts its list items at
    # eight, and a two-space item under an eight-space sibling does not parse. When
    # there are no existing items, `block()`'s own two-past-the-key is the convention.
    at = next((i for i in range(repos + 1, end)
               if lines[i].strip() and _indent(lines[i]) <= depth), end)
    items = [i for i in range(repos + 1, at) if lines[i].strip()
             and not lines[i].lstrip().startswith("#")]
    body = _reindent(_entry_lines(entries),
                     _indent(lines[items[0]]) if items else depth + 2)
    # Proposal 3: the basis and the date travel with the entries even when the key
    # already exists. They are `block()`'s header, which `_entry_lines` leaves behind
    # so the items re-indent correctly, so they are re-attached here at the ITEMS'
    # depth -- a reader meeting this block in six months has to be able to tell a
    # declaration somebody made from one a script proposed and somebody confirmed.
    head = [l for l in entries.splitlines()
            if l.lstrip().startswith("#") and "repos:" not in l
            and not l.lstrip().startswith("# named on")]
    if head:
        lead = " " * (_indent(body.splitlines()[0]) if body.strip() else depth + 2)
        body = "\n".join(lead + h.lstrip() for h in head) + "\n" + body
    if inline and not inline.startswith("#"):
        # `repos: []` and friends: the key line is rewritten as a bare key and the
        # entries become its items. An inline value that is not an empty list or map
        # holds a declaration this cannot merge into, so it is refused -- the operator
        # reformats it and re-runs, which is a worse morning than a working insertion
        # and a far better one than a config that lost a declaration.
        if inline not in ("[]", "{}"):
            raise UnparseableResult(
                f"`repos:` holds an inline value this cannot merge into ({inline}). "
                "Write it as a block list and re-run; nothing was written.")
        out = (lines[:repos] + [f"{' ' * depth}repos:"]
               + body.splitlines() + lines[repos + 1:])
        return _checked(text, "\n".join(out) + "\n", entries)
    # After `repos:`, its items run until a line indented no deeper than `repos:` is.
    at = next((i for i in range(repos + 1, end)
               if lines[i].strip() and _indent(lines[i]) <= depth), end)
    out = lines[:at] + body.splitlines() + lines[at:]
    return _checked(text, "\n".join(out) + "\n", entries)


def _entry_lines(entries: str) -> str:
    """`block()`'s ITEMS and their own comments -- without the key or its header.

    `block()` opens with two comment lines at the key's depth (the basis and what a day
    count means) and then the `repos:` key. Those three belong to the KEY: when the key
    already exists in the config, they must not travel with the items, because
    `_reindent` anchors on the shallowest line it is given, and a header comment two
    spaces shallower than the items shifted every item two spaces too deep -- which put
    the list below a depth no key owns and refused the whole insertion. Keeping only the
    lines from the first item onward leaves the items as the shallowest thing here.
    """
    lines = entries.splitlines()
    first = next((i for i, l in enumerate(lines) if l.lstrip().startswith("- ")), None)
    if first is None:                 # no items: nothing of this block is an entry
        return ""
    return "\n".join(lines[first:]).rstrip("\n")


def _reindent(entries: str, depth: int) -> str:
    """`entries` moved so that its own outermost level sits at `depth` spaces.

    `block()` writes at the two-space depth of the common config; a config whose
    `external_systems:` keys are indented four would otherwise receive items at a depth
    that belongs to no key.
    """
    body = [l for l in entries.splitlines() if l.strip()]
    base = min((_indent(l) for l in body), default=0)
    shift = depth - base
    if shift == 0:
        return entries.rstrip("\n")
    out = []
    for l in entries.splitlines():
        if not l.strip():
            out.append(l)
        elif shift > 0:
            out.append(" " * shift + l)
        else:
            out.append(l[min(-shift, _indent(l)):])
    return "\n".join(out).rstrip("\n")


def _checked(before: str, after: str, entries: str) -> str:
    """`after`, once it parses and holds every entry the operator confirmed.

    Three things are checked, and each one is a way the first reader went wrong while
    producing plausible-looking text: the result LOADS; `external_systems.repos` is a
    LIST (a duplicate key left it as the hand-written `[]`); and every name confirmed is
    in it, with the entries that were there before still there. The caller writes
    nothing when this raises, so a refusal costs the operator a re-run and a config that
    silently lost the confirmation costs them the next reading of the agenda.
    """
    try:
        got = yaml.safe_load(after)
    except yaml.YAMLError as e:
        raise UnparseableResult(
            f"the result would not parse as YAML ({type(e).__name__}); nothing was written") from e
    repos = ((got or {}).get("external_systems") or {}).get("repos")
    if not isinstance(repos, list):
        raise UnparseableResult(
            "the result's external_systems.repos is not a list; nothing was written")
    want = [l.split("name:", 1)[1].strip() for l in entries.splitlines()
            if l.strip().startswith("name:")]
    have = {str(e.get("name") or "") for e in repos if isinstance(e, dict)}
    if (missing := [w for w in want if w not in have]):
        raise UnparseableResult(
            f"the result would not hold the confirmed entr(y/ies) {', '.join(missing)}; "
            "nothing was written")
    try:
        old = yaml.safe_load(before)
    except yaml.YAMLError:
        return after                  # it did not parse before this; not ours to judge
    kept = ((old or {}).get("external_systems") or {}).get("repos") or []
    if isinstance(kept, list) and (lost := [e for e in kept if e not in repos]):
        raise UnparseableResult(
            f"the result would drop {len(lost)} declared repositor(y/ies); nothing was written")
    return after


def no_url(name: str, info: dict, declared: dict[str, str]) -> bool:
    """Proposal 3: an entry that cannot be read -- no organisation anywhere to read it at.

    This helper reaches no network, so *cannot be read* here is not *access denied*: it
    is that nothing in the window ever wrote the repository as `owner/repo` and the
    project does not declare it either, so there is no address. Said out loud, because
    the alternative is a `url:` with an organisation the script picked, and a config
    entry pointing at an organisation nobody named is worse than one marked unresolved.
    The measured project had exactly one such name: a repository login that appeared in
    the reports with no organisation and mapped to nothing.
    """
    return not info.get("slugs") and name not in declared


def proposal(cf: dict, counts: dict[str, dict], read: list, problems: list[str],
             window_days: int) -> str:
    """The printed proposal. Prints; writes nothing (proposal 3)."""
    have = declared_slugs(cf)
    cand = sorted(((n, i) for n, i in counts.items() if not probably_prose(n, i)),
                  key=lambda t: (-len(t[1]["days"]), t[0]))
    prose = sorted(n for n, i in counts.items() if probably_prose(n, i))
    new = [(n, i) for n, i in cand if n not in have]
    basis = (f"{len(read)} report(s), {read[0][0].isoformat()} to {read[-1][0].isoformat()}"
             if read else "no report read")
    out = [f"Read {basis} over a {window_days} working-day window.", ""]
    if problems:
        out += ["Not read (reported, not counted as a report that named nothing):"]
        out += [f"  {p}" for p in problems] + [""]
    if not cand:
        out += ["No repository named in the reports read.", ""]
    else:
        out += [f"  {'repository':24}  {'days':>4}  {'items':>5}  state"]
        out += [f"  {'-' * 24}  ----  -----  -----"]
        for n, i in cand:
            state = "declared" if n in have else "NOT DECLARED"
            if no_url(n, i, have):
                state += " · cannot be read — no organisation in the reports"
            out.append(f"  {n[:24]:24}  {len(i['days']):>4}  {len(i['items']):>5}  {state}")
        out.append("")
    if prose:
        out += ["Probably prose (a word that matches a repository name; confirm if one of these"
                " really is a repository):", "  " + ", ".join(prose), ""]
    if (q := quiet(cf, counts, window_days)):
        out += [f"Declared and not named in the window ({window_days} working days) — NOT removed,"
                " for you to judge:", "  " + ", ".join(q), ""]
    if new:
        out += ["PROPOSED, nothing written yet. Confirm what belongs, then re-run with:", "",
                "  --write --confirm " + ",".join(n for n, _ in new), "",
                "The block that would be written:", "",
                block(new, basis, dt.date.today(), have), ""]
    else:
        out += ["Nothing to propose: every repository the reports name is already declared.", ""]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default=".", help="the project's meetings folder (for the config chain)")
    ap.add_argument("--days", type=int, default=14,
                    help="the window, in working days (default 14)")
    ap.add_argument("--date", help="YYMMDD the window ends on; default today")
    ap.add_argument("--write", action="store_true",
                    help="write the block -- requires --confirm. Without it this prints a proposal")
    ap.add_argument("--confirm", default="",
                    help="comma-separated repositories the operator confirmed. CR-151: nothing is "
                         "written without this, and a name the reports did not show is refused")
    a = ap.parse_args()

    md = Path(a.dir).resolve()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_agenda import config  # noqa: E402  (imported here, as build_movement does)
    cf = config(md)
    end = dt.datetime.strptime(a.date, "%y%m%d").date() if a.date else dt.date.today()
    start = working_days_back(end, a.days)
    counts, read, problems = count_window(cf, start, end)

    if not a.write:
        print(proposal(cf, counts, read, problems, a.days))
        return
    # Proposal 3: the write path exists only for a confirmed list, and it refuses a
    # name the reports did not show. A helper that wrote whatever it was handed would
    # be a config editor with a confirmation flag on it, which is not the same thing.
    want = [w.strip().lower() for w in a.confirm.split(",") if w.strip()]
    if not want:
        sys.exit("--write needs --confirm <repo>[,<repo>...]: nothing is written without a yes (CR-151)")
    unknown = [w for w in want if w not in counts]
    if unknown:
        sys.exit(f"not named in the reports read: {', '.join(unknown)} — "
                 "add it to the config by hand if it belongs")
    basis = (f"{len(read)} report(s), {read[0][0].isoformat()} to {read[-1][0].isoformat()}"
             if read else "no report read")
    entries = block([(w, counts[w]) for w in want], basis, dt.date.today(), declared_slugs(cf))
    target = cf.get("_config_file")
    if not target:
        sys.exit("no config file resolved for this folder — nothing to write to")
    target = Path(target)
    # The insertion is validated before anything reaches disk: `insert_repos` refuses a
    # result that would not load, or that would lose a declaration, and the refusal is
    # the whole answer -- nothing is written and the operator still has the config they
    # had. A helper that edits a config has one duty above proposing well.
    try:
        updated = insert_repos(target.read_text(encoding="utf-8"), entries)
    except UnparseableResult as e:
        sys.exit(f"{target}: {e} (CR-151)")
    target.write_text(updated, encoding="utf-8")
    print(f"wrote {len(want)} confirmed entr(y/ies) to {target}:\n")
    print(entries)


if __name__ == "__main__":
    main()
