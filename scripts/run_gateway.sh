#!/usr/bin/env bash
# Start the Canton 402 gateway against a running `daml start` ledger.
#
#   Terminal 1:  daml start            # sandbox + JSON API on :7575
#   Terminal 2:  scripts/seed.sh       # create parties, mandate, offers, wallet
#   Terminal 3:  scripts/run_gateway.sh
#   Terminal 4:  python3 gateway/agent.py
set -euo pipefail
export PATH="$HOME/.daml/bin:$PATH"
cd "$(dirname "$0")/.."

DAR=.daml/dist/canton402-0.1.0.dar
[ -f "$DAR" ] || daml build

# The main package id of our DAR (the one carrying Canton402.* templates).
PKG=$(daml damlc inspect-dar "$DAR" --json | python3 -c '
import sys, json
d = json.load(sys.stdin)
main = d["main_package_id"]
print(main)
')

echo "canton402 package id: $PKG"
export CANTON402_PKG="$PKG"

# Real agent party id from the seed step (falls back to "Agent").
if [ -f gateway/parties.json ]; then
  CANTON402_AGENT=$(python3 -c 'import json;print(json.load(open("gateway/parties.json"))["agent"])')
fi
export CANTON402_AGENT="${CANTON402_AGENT:-Agent}"
echo "agent party: $CANTON402_AGENT"
exec python3 gateway/canton402_gateway.py
