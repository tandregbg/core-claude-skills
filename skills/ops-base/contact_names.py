#!/usr/bin/env python3
"""Who a name or a folder means -- the contact metadata rules, in one place (CR-185, CR-186).

Contact metadata lives in `_contacts/<name>/_meta.yaml` (contact-meta schema v1.2). Two keys added in
1.99.0 need the same reading everywhere, so they are read here and nowhere else:

- **`contact:` on a folder outside `_contacts/`** (CR-185). A one-to-one series kept under a venture,
  as CR-182 routes it, says which contact it is about. A call card is named after it, and a reader
  looking for the person behind the folder asks for it before the folder's own name.
- **`aliases_within:` on a contact** (CR-186). An alias that holds only under a vault path: inside the
  path a bare first name is this contact, outside it the name means what it meant before -- typically
  shared, and then nobody's.

The five rules for a name found IN A FILE (`resolve_in_file`):

1. a fuller name matches as itself first (longer names are tried before shorter);
2. a scoped alias wins over the name's global meaning inside its scope -- shared or not: inside
   the path the bare name is this contact, which is what declaring the scope says;
3. the longest matching prefix wins;
4. two contacts claiming the same name under the same prefix is a tie, and the name is nobody's;
5. a TYPED query (`resolve_query`) is unchanged by scopes: "Erik" typed by a user stays ambiguous.

    import contact_names as cn
    contacts = cn.load(vault)
    cn.resolve_in_file("Erik", "acme/meetings/260101-standup.md", contacts)   # -> "erik-sandberg"
    cn.folder_contact(vault / "acme/meetings/management/Erik")                # -> "erik-sandberg"
"""
from __future__ import annotations

from pathlib import Path

try:
    import yaml
except ImportError:                                     # pragma: no cover
    yaml = None

CONTACTS_DIR = "_contacts"


def _meta(folder: Path) -> dict:
    p = Path(folder) / "_meta.yaml"
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) if yaml and p.is_file() else None
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _slug_name(slug: str) -> str:
    return " ".join(w.capitalize() for w in slug.replace("_", " ").replace("-", " ").split())


def _prefix(p) -> str | None:
    """A vault-relative folder with one trailing slash, or None for an empty one ("/" included:
    a vault-wide scope is a global alias and belongs in `aliases`)."""
    core = str(p).strip().strip("/")
    return core + "/" if core else None


def _list(value) -> list:
    """A YAML value as a list of non-empty strings: a scalar is one name, null is none."""
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    return [str(v).strip() for v in items if v is not None and str(v).strip()]


def _rel(path) -> str:
    """A vault-relative path as the string the prefixes are compared with."""
    s = str(path).replace("\\", "/")
    while s.startswith("./"):
        s = s[2:]
    return s


def load(vault) -> dict:
    """{slug: {"display_name", "names", "scoped": [(prefix, name)]}} for every contact folder.

    `names` are the global ones (display name, aliases, the folder name made readable);
    `scoped` the `aliases_within` pairs. A folder without `_meta.yaml` is still a contact."""
    out = {}
    root = Path(vault) / CONTACTS_DIR
    if not root.is_dir():
        return out
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        meta = _meta(folder)
        display = str(meta.get("display_name") or "").strip() or _slug_name(folder.name)
        names = {display, _slug_name(folder.name)}
        names |= set(_list(meta.get("aliases")))
        scoped = []
        within = meta.get("aliases_within") or {}
        if isinstance(within, dict):
            for prefix, aliases in within.items():
                pre = _prefix(prefix)
                if pre:
                    scoped += [(pre, a) for a in _list(aliases)]
        out[folder.name] = {"display_name": display, "names": sorted(names), "scoped": scoped}
    return out


def _owners(contacts: dict) -> dict:
    """{name.lower(): {slugs}} over the global names."""
    owners: dict = {}
    for slug, c in contacts.items():
        for n in c["names"]:
            owners.setdefault(n.lower(), set()).add(slug)
    return owners


_TIE = object()


def _scoped(rel_path, name: str, contacts: dict):
    """The scoped claim on `name` in this file: a slug, _TIE, or None when no scope applies."""
    rel_path = _rel(rel_path)
    key = name.strip().lower()
    best, best_len, tie = None, -1, False
    for slug, c in contacts.items():
        for prefix, alias in c["scoped"]:
            if alias.lower() != key or not rel_path.startswith(prefix):
                continue
            if len(prefix) > best_len:
                best, best_len, tie = slug, len(prefix), False
            elif len(prefix) == best_len and slug != best:
                tie = True
    return _TIE if tie else best


def scoped_owner(rel_path, name: str, contacts: dict):
    """The one contact `name` means in a file at `rel_path` by a scoped alias, or None.
    Longest matching prefix wins; a same-prefix tie between two contacts is nobody's."""
    claim = _scoped(rel_path, name, contacts)
    return None if claim is _TIE else claim


def resolve_in_file(name: str, rel_path: str, contacts: dict):
    """The contact a name found in a file means, or None (unknown, or shared and unscoped).

    The caller tries longer names first (rule 1): "Erik Lindgren" is looked up as a whole before
    any bare "Erik" on the same line is considered."""
    key = name.strip().lower()
    owners = _owners(contacts).get(key, set())
    claim = _scoped(rel_path, name, contacts)
    if claim is _TIE:
        return None                  # rule 4: a tie inside the scope is nobody's, not a global owner's
    if claim:
        return claim                 # rule 2: inside its scope the scoped alias decides
    if len(owners) == 1:
        return next(iter(owners))
    return None


def resolve_query(query: str, contacts: dict):
    """(slug or None, candidates) for a name a person typed. Scopes do not apply (rule 5)."""
    key = query.strip().lower()
    if key in contacts:
        return key, [key]
    hits = sorted(_owners(contacts).get(key, set()))
    return (hits[0] if len(hits) == 1 else None), hits


def folder_contact(folder) -> str | None:
    """The contact a folder OUTSIDE `_contacts/` declares it is about (`contact:`), or None.
    Inside `_contacts/` the folder is the contact and the key is ignored."""
    f = Path(folder)
    if CONTACTS_DIR in f.parts:
        return None
    value = _meta(f).get("contact")
    value = str(value).strip() if value is not None else ""
    return value or None


def _plain_name(value: str) -> bool:
    """A contact folder name: one path segment, not hidden, not a parent reference."""
    return bool(value) and "/" not in value and "\\" not in value and not value.startswith(".")


def person_of_folder(folder) -> str:
    """Who a folder is about, for a reader that needs one name: `contact`, then `display_name`,
    then the folder's own name."""
    f = Path(folder)
    meta = _meta(f) if CONTACTS_DIR not in f.parts else {}
    return (folder_contact(f) or str(meta.get("display_name") or "").strip() or f.name)


def dangling(vault, folders) -> list:
    """[(folder, contact)] for every folder whose `contact:` names no folder under `_contacts/`."""
    root = Path(vault) / CONTACTS_DIR
    try:                             # exact names: a case-insensitive file system must not hide
        present = {d.name for d in root.iterdir() if d.is_dir()}   # `contact: X` against `x/`
    except OSError:
        present = set()
    out = []
    for f in folders:
        c = folder_contact(f)
        if c and (not _plain_name(c) or c not in present):
            out.append((Path(f), c))
    return out
