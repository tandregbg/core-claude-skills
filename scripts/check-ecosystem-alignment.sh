#!/bin/bash
# check-ecosystem-alignment.sh — Verify all ecosystem components are aligned
# Run after bumping core-skills version to detect drift.
#
# Wired into `/ops sweep` check 8 (CR-023) via workflows.sweep.alignment_check
# in ops-config — the sweep parses the [OK]/[DRIFT]/[SKIP] lines below.
# A [SKIP] (e.g. unreachable mount) means UNVERIFIED, not clean.
#
# Update runbook when [DRIFT] is reported (verified 2026-07-08):
# - Marvin: update the core-skills version reference + any schema notes in
#   its CLAUDE.md, commit.
# - Landing page: patch whats_new in static/i18n/en.json AND sv.json (the
#   title carries the version this script greps), update the footer version
#   in templates/{en,sv}/base.html, bump BUILD_VERSION in app.py, then
#   restart EXACTLY the landing app in pm2 (the app caches i18n at startup;
#   a bare `pm2 restart all` restarts every app on that host). Commit on the
#   host repo. Host access per the private VM inventory; if the SSHFS mount
#   is stale, unmount/remount or go straight over SSH.
# - Never auto-apply from tooling: cross-repo version refs and live deploys
#   are human-confirmed changes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# Read contract version
if [ ! -f "$REPO_DIR/ecosystem.yaml" ]; then
    echo "ERROR: ecosystem.yaml not found in $REPO_DIR"
    exit 1
fi

CONTRACT_VERSION=$(python3 -c "import yaml; print(yaml.safe_load(open('$REPO_DIR/ecosystem.yaml'))['core_skills_version'])")
echo "=== Ecosystem Alignment Check ==="
echo "Contract version: $CONTRACT_VERSION"
echo ""

ALIGNED=0
DRIFTED=0

# Check core-skills README
README_VERSION=$(grep -o 'Version:.*' "$REPO_DIR/README.md" | head -1 | sed 's/.*\*\* //' | tr -d ' ')
if [ "$README_VERSION" = "$CONTRACT_VERSION" ]; then
    echo "[OK] core-skills README: $README_VERSION"
    ALIGNED=$((ALIGNED + 1))
else
    echo "[DRIFT] core-skills README: $README_VERSION (expected $CONTRACT_VERSION)"
    DRIFTED=$((DRIFTED + 1))
fi

# Check Marvin CLAUDE.md (formerly core-skills-visualisation, renamed 2026-04-29)
# Default tries the new path first, falls back to the old one until the directory rename is complete.
if [ -z "${VIS_DIR:-}" ]; then
    if [ -d "$HOME/repos/marvin" ]; then
        VIS_DIR="$HOME/repos/marvin"
    else
        VIS_DIR="$HOME/repos/core-skills-visualisation"
    fi
fi
if [ -d "$VIS_DIR" ]; then
    VIS_REF=$(grep -o 'v[0-9]\+\.[0-9]\+\.[0-9]\+' "$VIS_DIR/CLAUDE.md" 2>/dev/null | head -1 | tr -d 'v')
    if [ "$VIS_REF" = "$CONTRACT_VERSION" ]; then
        echo "[OK] Marvin CLAUDE.md: v$VIS_REF"
        ALIGNED=$((ALIGNED + 1))
    else
        echo "[DRIFT] Marvin CLAUDE.md: v${VIS_REF:-missing} (expected v$CONTRACT_VERSION)"
        DRIFTED=$((DRIFTED + 1))
    fi
else
    echo "[SKIP] visualiser not found at $VIS_DIR"
fi

# Check landing page (via mount or SSH)
LANDING_MOUNT="${LANDING_MOUNT:-$HOME/workspace/remotes/tomas/core-skills-landingpage}"
if [ -f "$LANDING_MOUNT/app.py" ]; then
    LANDING_BUILD=$(grep 'BUILD_VERSION' "$LANDING_MOUNT/app.py" | head -1 | grep -o "'[^']*'" | tr -d "'")
    # Landing page tracks its own build version, but should reference core_skills_version in i18n
    LANDING_REF=$(python3 -c "
import json
try:
    d = json.load(open('$LANDING_MOUNT/static/i18n/en.json'))
    wn = d.get('whats_new', {}).get('title', '')
    import re
    m = re.search(r'v([0-9.]+)', wn)
    print(m.group(1) if m else 'unknown')
except: print('unreadable')
" 2>/dev/null)
    if [ "$LANDING_REF" = "$CONTRACT_VERSION" ]; then
        echo "[OK] landing page i18n: v$LANDING_REF (build $LANDING_BUILD)"
        ALIGNED=$((ALIGNED + 1))
    else
        echo "[DRIFT] landing page i18n: v${LANDING_REF:-missing} (expected v$CONTRACT_VERSION, build $LANDING_BUILD)"
        DRIFTED=$((DRIFTED + 1))
    fi
else
    echo "[SKIP] landing page mount not available at $LANDING_MOUNT"
fi

# Check skill count
SKILL_COUNT=$(python3 -c "
import yaml
d = yaml.safe_load(open('$REPO_DIR/ecosystem.yaml'))
print(len(d['skills']['user_invocable']) + len(d['skills']['non_invocable']))
")
README_SKILLS=$(sed -n '/## Skills included/,/## Architecture/p' "$REPO_DIR/README.md" | grep -c '| `' 2>/dev/null || echo 0)
echo ""
echo "Skill count in ecosystem.yaml: $SKILL_COUNT"
echo "Skill rows in README table: $README_SKILLS"

echo ""
echo "=== Result: $ALIGNED aligned, $DRIFTED drifted ==="
if [ "$DRIFTED" -gt 0 ]; then
    echo "Action needed: update drifted components."
    exit 1
fi
