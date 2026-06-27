"""Canton 402 gateway.

An x402-compatible HTTP front door for Canton 402 services. Any agent -- even
one with no Canton SDK -- can:

  GET  /services          discover the offers it is allowed to see
  POST /invoke {name}     buy and call a service

`/invoke` follows the x402 handshake: with no `X-Payment` header it answers
HTTP 402 with payment requirements; with the header it submits the atomic
`PayAndCall` to the Daml ledger and returns the receipt. Settlement, policy, and
privacy are all enforced on-ledger -- this process only relays.

Run:
  CANTON402_PKG=<pkgid> python3 gateway/canton402_gateway.py
(get <pkgid> from scripts/run_gateway.sh, which prints it).
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import ledger

PKG = os.environ.get("CANTON402_PKG", "")
AGENT = os.environ.get("CANTON402_AGENT", "Agent")
PORT = int(os.environ.get("CANTON402_GATEWAY_PORT", "8402"))

OFFER_T = lambda: ledger.tid(PKG, "Canton402.Commerce", "ServiceOffer")
RECEIPT_T = lambda: ledger.tid(PKG, "Canton402.Commerce", "PaymentReceipt")
ASSET_T = lambda: ledger.tid(PKG, "Canton402.Asset", "Asset")
MANDATE_T = lambda: ledger.tid(PKG, "Canton402.Mandate", "Mandate")


def offers():
    rows = ledger.query(AGENT, [OFFER_T()])
    return [r for r in rows]


def find_offer(name):
    for r in offers():
        if r["payload"]["name"] == name:
            return r
    return None


def best_wallet():
    rows = ledger.query(AGENT, [ASSET_T()])
    rows = [r for r in rows if r["payload"]["owner"] == AGENT]
    rows.sort(key=lambda r: float(r["payload"]["amount"]), reverse=True)
    return rows[0] if rows else None


def current_mandate():
    rows = ledger.query(AGENT, [MANDATE_T()])
    rows = [r for r in rows if r["payload"]["agent"] == AGENT]
    return rows[0] if rows else None


def receipt_chain_tip():
    """Return (next_seq, prev_hash) from the agent's existing receipts."""
    rows = ledger.query(AGENT, [RECEIPT_T()])
    if not rows:
        return 1, ""
    rows.sort(key=lambda r: int(r["payload"]["seq"]))
    last = rows[-1]["payload"]
    return int(last["seq"]) + 1, last["thisHash"]


def payment_requirements(offer):
    p = offer["payload"]
    return {
        "x402Version": 1,
        "accepts": [
            {
                "scheme": "exact",
                "network": "canton",
                "asset": "settlement-asset",
                "maxAmountRequired": p["price"],
                "payTo": p["provider"],
                "resource": "/invoke",
                "description": f"Canton 402 service: {p['name']}",
                "mimeType": "application/json",
            }
        ],
    }


def pay_and_call(offer):
    wallet = best_wallet()
    mandate = current_mandate()
    if wallet is None:
        raise RuntimeError("agent has no settlement asset")
    if mandate is None:
        raise RuntimeError("agent has no mandate")
    seq, prev = receipt_chain_tip()
    res = ledger.exercise(
        AGENT,
        OFFER_T(),
        offer["contractId"],
        "PayAndCall",
        {
            "agent": AGENT,
            "mandateCid": mandate["contractId"],
            "assetCid": wallet["contractId"],
            "seq": seq,
            "prevHash": prev,
        },
    )
    return res["result"]["exerciseResult"]


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body):
        payload = json.dumps(body, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *a):  # quieter
        pass

    def do_GET(self):
        if self.path.rstrip("/") == "/services":
            out = [
                {
                    "name": r["payload"]["name"],
                    "description": r["payload"]["description"],
                    "price": r["payload"]["price"],
                    "provider": r["payload"]["provider"],
                }
                for r in offers()
            ]
            self._send(200, {"services": out})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path.rstrip("/") != "/invoke":
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        name = body.get("name")
        offer = find_offer(name)
        if offer is None:
            self._send(404, {"error": f"unknown service '{name}'"})
            return
        if "X-Payment" not in self.headers:
            # x402 handshake: tell the agent what it must pay.
            self._send(402, payment_requirements(offer))
            return
        try:
            result = pay_and_call(offer)
            self._send(
                200,
                {
                    "settled": True,
                    "service": name,
                    "amount": offer["payload"]["price"],
                    "receiptHash": result["receiptHash"],
                    "receipt": result["receipt"],
                    "entitlement": result["entitlement"],
                },
            )
        except Exception as e:  # surface ledger rejections (e.g. policy breach)
            self._send(402, {"settled": False, "error": str(e)})


def main():
    if not PKG:
        raise SystemExit("set CANTON402_PKG to the canton402 package id")
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Canton 402 gateway on :{PORT} (agent={AGENT}, pkg={PKG[:12]}...)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
