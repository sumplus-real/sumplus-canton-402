#!/usr/bin/env bash
# Seed a running `daml start` ledger with parties, mandate, offers, and the
# agent's wallet. Writes the real party ids to gateway/parties.json.
set -euo pipefail
export PATH="$HOME/.daml/bin:$PATH"
cd "$(dirname "$0")/.."

DAR=.daml/dist/canton402-0.1.0.dar
[ -f "$DAR" ] || daml build

daml script \
  --dar "$DAR" \
  --script-name Test.Setup:setup \
  --ledger-host localhost --ledger-port 6865 \
  --output-file gateway/parties.json

echo "seeded. party ids:"
cat gateway/parties.json
