#!/usr/bin/env python3
"""The folders every vault walk skips -- one definition, read from the contract (CR-180, CR-182).

A walk that indexes, counts, summarises, sweeps or lints the vault must not enter these folders.
Most of them carry a dot, so a walker that drops every dot-folder already skips them. Two do not:
`_callcards/` (CR-180) and `_toread/` (CR-182) are VIEWS for a person, given an underscore so they
can be pinned on a phone -- which a dot-folder cannot -- and the underscore is exactly what makes a
dot-only filter walk into them. A view read back as source synthesises a view of itself.

The list is the contract's (`vault_conventions.conventions`, id `walk_skip`). A vault may ADD names
through its own `_config/base.yaml` (`vault_conventions.walk_skip: [...]`), e.g. when it has renamed
one of the surfaces; it can never remove one.

    import walk_skip
    dirnames[:] = [d for d in dirnames if not walk_skip.skip(d, root)]
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

try:
    import yaml
except ImportError:                                     # pragma: no cover
    yaml = None

HERE = Path(__file__).resolve().parent
ECOSYSTEM = HERE.parents[1] / "ecosystem.yaml"

# Fallback only, for a contract that cannot be read. The contract is the source of truth.
DEFAULT = (".archive", ".transcripts", ".handoff", ".status", "_callcards", "_toread")


def _strip(name) -> str:
    return str(name).strip().strip("/")


@lru_cache(maxsize=None)
def contract_names(contract: str = str(ECOSYSTEM)) -> frozenset:
    """The names declared by the contract's `walk_skip` convention."""
    try:
        data = yaml.safe_load(Path(contract).read_text(encoding="utf-8")) if yaml else None
        for conv in (data or {}).get("vault_conventions", {}).get("conventions", []) or []:
            if isinstance(conv, dict) and conv.get("id") == "walk_skip":
                paths = [_strip(p) for p in conv.get("paths") or [] if _strip(p)]
                if paths:
                    return frozenset(paths)
    except Exception:
        pass
    return frozenset(DEFAULT)


def vault_root(start) -> Path | None:
    """Walk up until a folder holding _inbox/, _outbox/ or .obsidian/ (the contract's rule)."""
    if start is None:
        return None
    p = Path(start).resolve()
    for d in (p, *p.parents):
        if any((d / m).exists() for m in ("_inbox", "_outbox", ".obsidian")):
            return d
    return None


@lru_cache(maxsize=None)
def _vault_extra(root: str) -> frozenset:
    cfg = Path(root) / "_config" / "base.yaml"
    try:
        data = yaml.safe_load(cfg.read_text(encoding="utf-8")) if yaml and cfg.is_file() else None
        extra = ((data or {}).get("vault_conventions") or {}).get("walk_skip") or []
        return frozenset(_strip(n) for n in extra if _strip(n))
    except Exception:
        return frozenset()


def names(start=None) -> frozenset:
    """Contract names plus any the vault adds. `start` is any path inside the vault, or None."""
    root = vault_root(start)
    return contract_names() | (_vault_extra(str(root)) if root else frozenset())


def skip(dirname: str, start=None) -> bool:
    """True if a walker must not enter a folder with this name."""
    return _strip(dirname) in names(start)


if __name__ == "__main__":                              # pragma: no cover
    import sys
    print("\n".join(sorted(names(sys.argv[1] if len(sys.argv) > 1 else None))))
