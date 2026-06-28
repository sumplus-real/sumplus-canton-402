#!/usr/bin/env bash
# One command to bring up the Canton 402 web demo for the submission video.
#
#   scripts/web_demo.sh
#
# It builds, starts a Canton sandbox + JSON API (if not already running), seeds a
# fresh ledger (parties, mandate, three offers, the agent's wallet), starts the
# gateway that serves the UI, and opens the page. Everything on the page is a
# real transaction against the running ledger. Ctrl-C tears the demo down.
set -euo pipefail
cd "$(dirname "$0")/.."

export JAVA_HOME="${JAVA_HOME:-/usr/local/opt/openjdk@17}"
export PATH="$JAVA_HOME/bin:$HOME/.daml/bin:$PATH"

JSON_API=http://localhost:7575
GW_PORT="${CANTON402_GATEWAY_PORT:-8402}"
GW=http://localhost:$GW_PORT
DAML_PID=""
GW_PID=""

cleanup() {
  echo; echo "tearing down demo…"
  [ -n "$GW_PID" ] && kill "$GW_PID" 2>/dev/null || true
  pkill -f canton402_gateway.py 2>/dev/null || true
  [ -n "$DAML_PID" ] && { echo "stopping sandbox…"; kill "$DAML_PID" 2>/dev/null || true; }
}
trap cleanup EXIT INT TERM

echo "==> build"
daml build >/dev/null
echo "    ok"

# 1) sandbox + JSON API (reuse if already up)
if curl -s -o /dev/null "$JSON_API/readyz"; then
  echo "==> sandbox already running, reusing it"
else
  echo "==> starting Canton sandbox + JSON API (~60s)…"
  daml start >/tmp/canton402_daml_start.log 2>&1 &
  DAML_PID=$!
  until curl -s -o /dev/null "$JSON_API/readyz"; do sleep 3; done
  echo "    ledger up"
fi

# 2) fresh seed (parties, mandate, 3 offers, wallet) -> gateway/parties.json
echo "==> seeding a fresh ledger"
daml script \
  --dar .daml/dist/canton402-0.1.0.dar \
  --script-name Test.Setup:setup \
  --ledger-host localhost --ledger-port 6865 \
  --output-file gateway/parties.json >/dev/null 2>&1
echo "    seeded"

# 3) gateway that serves the UI, bound to the freshly seeded agent party
PKG=$(daml damlc inspect-dar .daml/dist/canton402-0.1.0.dar --json \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["main_package_id"])')
AGENT=$(python3 -c 'import json;print(json.load(open("gateway/parties.json"))["agent"])')
echo "==> starting gateway on $GW (pkg ${PKG:0:12}…)"
CANTON402_PKG="$PKG" CANTON402_AGENT="$AGENT" CANTON402_GATEWAY_PORT="$GW_PORT" \
  python3 gateway/canton402_gateway.py >/tmp/canton402_gateway.log 2>&1 &
GW_PID=$!
until curl -s -o /dev/null "$GW/state"; do sleep 1; done
echo "    gateway up"

echo
echo "############################################################"
echo "#  Canton 402 web demo is live:  $GW"
echo "#  Opening it now. Click the services to drive the ledger."
echo "#  Ctrl-C here when you're done recording."
echo "############################################################"
command -v open >/dev/null && open "$GW" || echo "open $GW in your browser"

# keep sandbox + gateway alive until Ctrl-C
wait
