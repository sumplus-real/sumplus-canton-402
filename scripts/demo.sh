#!/usr/bin/env bash
# Canton 402 — one-command demo.
# Type-checks the Daml model and runs the end-to-end acceptance script
# (happy path + policy guardrails + privacy assertions).
set -euo pipefail

export PATH="$HOME/.daml/bin:$PATH"

cd "$(dirname "$0")/.."

echo "==> daml version"
daml version | head -3

echo
echo "==> daml test (Test.Demo: pay-and-call, guardrails, privacy)"
daml test --color no

echo
echo "All green. To explore interactively:  daml start"
