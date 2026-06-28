#!/usr/bin/env bash
# Boot the full Canton 402 stack in one container:
#   1. Canton sandbox (ledger API :6865) + JSON API (:7575) via `daml start`
#   2. seed parties / mandate / offers (Test.Setup -> gateway/parties.json)
#   3. the x402 gateway, bound to $PORT (Railway) or 8402
set -euo pipefail
export PATH="/root/.daml/bin:$PATH"
cd /app

DAR=.daml/dist/canton402-0.1.0.dar
LEDGER_PORT=6865
JSON_PORT=7575
GW_PORT="${PORT:-${CANTON402_GATEWAY_PORT:-8402}}"

echo "[boot] starting Canton sandbox + JSON API (this takes ~60s)..."
daml start \
  --start-navigator no \
  --open-browser no \
  --sandbox-port "$LEDGER_PORT" \
  --json-api-port "$JSON_PORT" \
  >/tmp/daml.log 2>&1 &
DAML_PID=$!

cleanup() { kill "$DAML_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "[boot] waiting for JSON API on :$JSON_PORT ..."
for i in $(seq 1 180); do
  if curl -fsS "http://localhost:$JSON_PORT/livez" >/dev/null 2>&1 \
     || curl -fsS "http://localhost:$JSON_PORT/readyz" >/dev/null 2>&1; then
    echo "[boot] JSON API up after ${i}s"
    break
  fi
  if ! kill -0 "$DAML_PID" 2>/dev/null; then
    echo "[boot] daml start died; log tail:"; tail -40 /tmp/daml.log; exit 1
  fi
  sleep 1
done

echo "[boot] seeding ledger (parties, mandate, offers)..."
daml script \
  --dar "$DAR" \
  --script-name Test.Setup:setup \
  --ledger-host localhost --ledger-port "$LEDGER_PORT" \
  --output-file gateway/parties.json
echo "[boot] parties:"; cat gateway/parties.json; echo

PKG=$(daml damlc inspect-dar "$DAR" --json \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["main_package_id"])')
AGENT=$(python3 -c 'import json;print(json.load(open("gateway/parties.json"))["agent"])')
echo "[boot] pkg=$PKG agent=$AGENT"

export CANTON402_PKG="$PKG"
export CANTON402_AGENT="$AGENT"
export CANTON402_JSON_API="http://localhost:$JSON_PORT"
export CANTON402_GATEWAY_PORT="$GW_PORT"

echo "[boot] starting gateway on :$GW_PORT"
cd gateway
exec python3 canton402_gateway.py
