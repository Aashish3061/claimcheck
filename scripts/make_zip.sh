#!/usr/bin/env bash
# Builds the submission zip (code to rerun/verify the product) after a secret scan.
set -e
cd "$(dirname "$0")/.."
bash scripts/secret_scan.sh
rm -f claimcheck_submission.zip
git archive --format=zip -o claimcheck_submission.zip HEAD
echo "built claimcheck_submission.zip ($(du -h claimcheck_submission.zip | cut -f1)) - keys go in .env / Vercel env (see README)"
