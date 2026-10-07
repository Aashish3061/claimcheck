#!/usr/bin/env bash
# Fails if anything that looks like a key is in the working tree or git history.
set -u
PAT='AIza[0-9A-Za-z_-]{20,}|sb_secret_[0-9A-Za-z_-]{10,}|eyJ[0-9A-Za-z_-]{20,}\.[0-9A-Za-z_-]{20,}|service_role"?\s*[:=]\s*"?eyJ'
hits=$(git grep -nIE "$PAT" -- . ":!scripts/secret_scan.sh" 2>/dev/null | grep -v "your-"; git log -p --all | grep -nE "$PAT" | grep -v secret_scan.sh | grep -v "your-")
if [ -n "$hits" ]; then echo "POSSIBLE SECRETS:"; echo "$hits" | head -20; exit 1; fi
echo "secret scan: clean"
