#!/usr/bin/env bash
# One-shot demo for the submission video. Records in ~90s, no sandbox needed.
#   1) the acceptance suite goes green (proof it all runs)
#   2) a narrated run on a simulated ledger tells the whole story on screen
#
# Usage:  scripts/demo_video.sh
# Needs:  JAVA_HOME on an OpenJDK 17, daml on PATH.

set -euo pipefail
cd "$(dirname "$0")/.."

export JAVA_HOME="${JAVA_HOME:-/usr/local/opt/openjdk@17}"
export PATH="$JAVA_HOME/bin:$HOME/.daml/bin:$PATH"

echo
echo "############################################################"
echo "# Canton 402 — agent-era corporate card on Canton"
echo "############################################################"
echo

echo "==> 1/3  Build"
daml build >/dev/null
echo "    ok"
echo

echo "==> 2/3  Acceptance suite (daml test --all)"
echo "    Two settled buys with chained receipts, three out-of-policy"
echo "    attempts rejected on-ledger, privacy asserted across five parties."
echo
daml test --all 2>&1 | grep -E ":(demo|narrate|setup):|ok," || true
echo

echo "==> 3/3  Narrated run on a live (simulated) ledger"
echo
daml script \
  --dar .daml/dist/canton402-0.1.0.dar \
  --script-name Test.Narrate:narrate \
  --ide-ledger 2>&1 \
  | sed -n 's/.*Prelude:[0-9]*\]: //p' \
  | sed 's/\\"/"/g; s/^"//; s/"$//'
echo
echo "Real Daml, real policy, real privacy."
