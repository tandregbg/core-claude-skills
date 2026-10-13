#!/usr/bin/env python3
"""Resolve a folder's profile (CR-123): the bundle of defaults a project selects.

    python3 profiles.py <folder>            # JSON: name, values, where it was declared
    python3 profiles.py <folder> --text

A profile is declared in `base.yaml` (`profiles:`), next to this script. A project
selects one with `profile: <name>` in its `.claude/ops-config.yaml` or `_ops.yaml`,
and may override keys with `profiles: {<name>: {...}}` in the same chain.

RESOLUTION, walking up from the folder:
  - files read at each level, nearest first: `.claude/ops-config.yaml`, `_ops.yaml`,
    `_config/base.yaml` (the vault's own defaults);
  - the NEAREST `profile:` wins; none anywhere -> `meeting`;
  - an unknown name -> `meeting`, with a warning (never a guess);
  - overrides: every `profiles.<name>` block on the way up is merged over the
    skill defaults, the nearer block winning key by key.

Never writes. Imported by promotion_candidates.py, hygiene_check.py and themes.py,
so that every script resolves the same profile the same way.
"""
import argparse, json, sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("needs pyyaml -- run with a python that has it")

HERE = Path(__file__).resolve().parent
BASE = HERE / "base.yaml"
DEFAULT = "meeting"
CHAIN = (Path(".claude") / "ops-config.yaml", Path("_ops.yaml"), Path("_config") / "base.yaml")


def skill_profiles(base: Path = BASE) -> dict:
    try:
        return (yaml.safe_load(base.read_text(encoding="utf-8")) or {}).get("profiles") or {}
    except (OSError, yaml.YAMLError):
        return {}


def _load(f: Path) -> dict:
    try:
        doc = yaml.safe_load(f.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return doc if isinstance(doc, dict) else {}


def chain(start: Path):
    """(path, parsed config) for every config file above `start`, nearest first."""
    here = start if start.is_dir() else start.parent
    for folder in [here, *here.parents]:
        for name in CHAIN:
            f = folder / name
            if f.is_file():
                yield f, _load(f)


def resolve(start, base: Path = BASE) -> dict:
    start = Path(start).expanduser()
    defaults = skill_profiles(base)
    files = list(chain(start))
    declared, source = None, None
    for f, cfg in files:
        if cfg.get("profile"):
            declared, source = str(cfg["profile"]).strip(), str(f)
            break
    warnings = []
    name = declared or DEFAULT
    if name not in defaults:
        warnings.append(f"unknown profile '{name}' in {source}; using '{DEFAULT}'")
        name = DEFAULT
    values = dict(defaults.get(name) or {})
    for f, cfg in reversed(files):          # farthest first, so the nearest wins
        block = (cfg.get("profiles") or {}).get(name)
        if isinstance(block, dict):
            values.update(block)
    return {"name": name, "declared": declared, "source": source,
            "values": values, "warnings": warnings}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Resolve a folder's profile (CR-123). Never writes.")
    ap.add_argument("folder")
    ap.add_argument("--text", action="store_true")
    args = ap.parse_args(argv)
    r = resolve(args.folder)
    if args.text:
        print(f"profile: {r['name']}" + (f" (from {r['source']})" if r["source"] else " (default)"))
        for w in r["warnings"]:
            print(f"warning: {w}")
        for k, v in r["values"].items():
            print(f"  {k}: {v}")
    else:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
