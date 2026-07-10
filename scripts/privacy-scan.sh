#!/bin/bash
# privacy-scan.sh (CR-029) — the repo's privacy watcher.
#
# Checks three layers:
#   1. Built-in secret patterns (public)
#   2. Private denylist of real identifiers (git config guard.denylist — never in repo)
#   3. EXAMPLE ALLOWLIST enforcement: any name-like token (contact slugs, dated
#      send-slugs, Name-Name filename pairs, display_name values) must match
#      scripts/githooks/allowed-examples.txt. Real names a denylist has never
#      met can't be enumerated — but allowed INVENTED names can. Unknown
#      name-like token => finding, even if it is not (yet) on any denylist.
#
# Modes:
#   --stdin   scan lines from stdin (used by the pre-push hook on added lines)
#   --tree    scan all tracked text files in the working tree (scheduled/manual;
#             wire into /ops sweep via workflows.sweep.privacy_scan.command)
#
# Exit 0 = clean, 1 = findings (verdict lines: [OK]/[FINDING]).

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
ALLOWLIST="$REPO/scripts/githooks/allowed-examples.txt"
MODE="${1:---tree}"

BUILTIN='sk-ant-[A-Za-z0-9_-]{8,}|sk-or-v1-[A-Za-z0-9]{8,}|sk-proj-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|BEGIN (RSA |EC |OPENSSH |PGP )?PRIVATE KEY|\b10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\b|\b192\.168\.[0-9]{1,3}\.[0-9]{1,3}\b|sshpass[[:space:]]+-p'
NAMELIKE='\b26[0-9]{4}-[a-zåäö][a-zåäö-]*_[a-zåäö-]+|_contacts/[a-zåäö][a-zåäö-]+|-[A-ZÅÄÖ][a-zåäö]+-[A-ZÅÄÖ][a-zåäö]+|display_name:[[:space:]]"[^"]+"'

if [ "$MODE" = "--stdin" ]; then
    INPUT="$(cat)"
else
    INPUT="$(git -C "$REPO" ls-files -z -- '*.md' '*.yaml' '*.yml' '*.sh' ':!:docs/audits' ':!:docs/change-requests' \
        | xargs -0 cat 2>/dev/null)"
fi
[ -z "$INPUT" ] && { echo "[OK] privacy-scan: nothing to scan"; exit 0; }

FAIL=0

# 1. built-in secrets
HITS=$(printf '%s\n' "$INPUT" | grep -nE "$BUILTIN" | head -5 || true)
if [ -n "$HITS" ]; then
    echo "[FINDING] built-in secret pattern:"; echo "$HITS"; FAIL=1
fi

# 2. private denylist (optional here — hook enforces fail-closed; scan warns)
DENY="$(git -C "$REPO" config guard.denylist || true)"
if [ -n "$DENY" ] && [ -r "$DENY" ]; then
    while IFS= read -r pat; do
        case "$pat" in ''|'#'*) continue;; esac
        HITS=$(printf '%s\n' "$INPUT" | grep -nE -e "$pat" | head -3 || true)
        if [ -n "$HITS" ]; then
            echo "[FINDING] private denylist ($pat):"; echo "$HITS"; FAIL=1
        fi
    done < "$DENY"
else
    echo "[SKIP] private denylist not configured — identifier layer UNVERIFIED"
fi

# 3. example-allowlist enforcement on name-like tokens
if [ ! -r "$ALLOWLIST" ]; then
    echo "[FINDING] allowed-examples.txt missing — allowlist layer cannot run"; FAIL=1
else
    TOKENS=$(printf '%s\n' "$INPUT" | grep -oE "$NAMELIKE" | sort -u || true)
    while IFS= read -r tok; do
        [ -z "$tok" ] && continue
        OK=0
        while IFS= read -r pat; do
            case "$pat" in ''|'#'*) continue;; esac
            if printf '%s' "$tok" | grep -qxE -e "$pat"; then OK=1; break; fi
        done < "$ALLOWLIST"
        if [ "$OK" -eq 0 ]; then
            echo "[FINDING] name-like token NOT on the invented-examples allowlist: $tok"
            echo "          -> if invented: add to scripts/githooks/allowed-examples.txt (conscious act)"
            echo "          -> if real: rewrite generically + add to the private denylist"
            FAIL=1
        fi
    done <<< "$TOKENS"
fi

if [ "$FAIL" -eq 0 ]; then echo "[OK] privacy-scan clean ($MODE)"; fi
exit $FAIL
