#!/bin/bash
# check-ecosystem-alignment.sh — Verify all ecosystem components are aligned
# Run after bumping core-skills version to detect drift.
#
# Wired into `/ops check` (vault) check 8 (CR-023) via workflows.sweep.alignment_check
# in ops-config — the sweep parses the [OK]/[DRIFT]/[SKIP] lines below.
# A [SKIP] (e.g. unreachable mount) means UNVERIFIED, not clean.
#
# Update runbook when [DRIFT] is reported (verified 2026-07-08):
# - Marvin: update the core-skills version reference + any schema notes in
#   its CLAUDE.md, commit.
# - Landing page (2.0, CR-089): the site reads ecosystem.yaml at BUILD time, so a
#   release needs a rebuild and deploy on the landing host (its scripts/deploy.sh),
#   after pulling core-skills there. This script reads what the live site says it
#   was built from: <LANDING_URL>/version.json. The Flask files it used to read
#   (app.py, static/i18n/en.json) no longer exist on the live site, and reading a
#   mount of them reported [OK] against a build nobody was served.
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

# Check contract_version against its own comment block (CR-045).
# This exists because the field sat at 2 for five days and four releases while
# CR-034..CR-038 each documented a bump above it — nothing read the value back,
# so nothing caught it (CR-044). Every bump is documented as a comment line
# "# contract_version N (CR-xxx, date): ...", which makes the comments a
# checkable declaration rather than prose.
DECLARED_MAX=$(grep -oE '^# contract_version [0-9]+' "$REPO_DIR/ecosystem.yaml" \
    | grep -oE '[0-9]+$' | sort -n | tail -1)
ACTUAL_CONTRACT=$(grep -oE '^contract_version: *[0-9]+' "$REPO_DIR/ecosystem.yaml" \
    | grep -oE '[0-9]+$')
if [ -z "$DECLARED_MAX" ]; then
    echo "[DRIFT] contract_version: no '# contract_version N' comment lines to check against"
    DRIFTED=$((DRIFTED + 1))
elif [ -z "$ACTUAL_CONTRACT" ]; then
    echo "[DRIFT] contract_version: field missing or unparseable in ecosystem.yaml"
    DRIFTED=$((DRIFTED + 1))
elif [ "$ACTUAL_CONTRACT" = "$DECLARED_MAX" ]; then
    echo "[OK] contract_version: $ACTUAL_CONTRACT (highest documented bump: $DECLARED_MAX)"
    ALIGNED=$((ALIGNED + 1))
else
    echo "[DRIFT] contract_version: field says $ACTUAL_CONTRACT, comments document $DECLARED_MAX"
    echo "        A bump was written up but never applied to the value, or vice versa."
    DRIFTED=$((DRIFTED + 1))
fi

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

# Check landing page: what the live site says it was built from (CR-089)
LANDING_URL="${LANDING_URL:-https://core-skills.doable.services}"
CONTRACT_NUM=$(python3 -c "import yaml; print(yaml.safe_load(open('$REPO_DIR/ecosystem.yaml'))['contract_version'])")
LANDING_JSON=$(curl -fsS -m 10 "$LANDING_URL/version.json" 2>/dev/null || true)
if [ -n "$LANDING_JSON" ]; then
    read -r L_SKILLS L_CONTRACT L_BUILD < <(python3 -c "
import json,sys
d=json.loads(sys.argv[1]); print(d.get('core_skills_version','?'), d.get('contract_version','?'), d.get('build','?'))
" "$LANDING_JSON")
    if [ "$L_SKILLS" = "$CONTRACT_VERSION" ] && [ "$L_CONTRACT" = "$CONTRACT_NUM" ]; then
        echo "[OK] landing page: built from v$L_SKILLS, contract $L_CONTRACT (build $L_BUILD)"
        ALIGNED=$((ALIGNED + 1))
    else
        echo "[DRIFT] landing page: built from v$L_SKILLS / contract $L_CONTRACT (expected v$CONTRACT_VERSION / contract $CONTRACT_NUM, build $L_BUILD) -- rebuild and deploy it"
        DRIFTED=$((DRIFTED + 1))
    fi
else
    echo "[SKIP] landing page not reachable at $LANDING_URL/version.json"
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
if [ "$README_SKILLS" -eq "$SKILL_COUNT" ]; then
    echo "[OK] README skills table: $README_SKILLS rows"
    ALIGNED=$((ALIGNED+1))
else
    echo "[DRIFT] README skills table: $README_SKILLS rows, contract declares $SKILL_COUNT"
    DRIFTED=$((DRIFTED+1))
fi

# CR-089: each SKILL.md's subcommands against the contract, and the avoid: phrases.
if python3 "$(dirname "$0")/check-terms.py" >/dev/null 2>&1; then
    echo "[OK] subcommands and terms (check-terms.py)"
    ALIGNED=$((ALIGNED+1))
else
    echo "[DRIFT] subcommands and terms:"
    python3 "$(dirname "$0")/check-terms.py" 2>&1 | grep -E '^\[DRIFT\]|^        ' | sed 's/^/        /' || true
    DRIFTED=$((DRIFTED+1))
fi

# The components graph and vault_conventions can disagree without any version
# number changing, which is how two undeclared paths survived until the graph
# was first written. Checked here so it runs with everything else.
echo ""
if python3 "$(dirname "$0")/check-components.py" >/dev/null 2>&1; then
    echo "[OK] components graph consistent with vault_conventions"
    ALIGNED=$((ALIGNED+1))
else
    echo "[DRIFT] components graph:"
    python3 "$(dirname "$0")/check-components.py" 2>&1 | grep '^\[FAIL\]' | sed 's/^/        /'
    DRIFTED=$((DRIFTED+1))
fi

echo ""
echo "=== Result: $ALIGNED aligned, $DRIFTED drifted ==="
if [ "$DRIFTED" -gt 0 ]; then
    echo "Action needed: update drifted components."
    exit 1
fi
