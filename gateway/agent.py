"""An autonomous agent that buys services through the Canton 402 gateway.

It needs no Canton SDK: it speaks plain HTTP. It discovers the services it is
allowed to see, then for each one it follows the x402 handshake -- get HTTP 402,
present payment, receive the on-ledger receipt. The mandate (enforced on the
ledger) silently bounds everything it does.

Run after the gateway is up:
  python3 gateway/agent.py
"""

import json
import os
import urllib.request
import urllib.error

GATEWAY = os.environ.get("CANTON402_GATEWAY", "http://localhost:8402")


def _get(path):
    with urllib.request.urlopen(GATEWAY + path, timeout=30) as r:
        return r.status, json.loads(r.read())


def _post(path, body, headers=None):
    data = json.dumps(body).encode()
    req = urllib.request.Request(GATEWAY + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def buy(name):
    print(f"\n-> agent wants '{name}'")
    # First call: no payment. Expect HTTP 402 with requirements.
    code, body = _post("/invoke", {"name": name})
    if code == 402 and "accepts" in body:
        req = body["accepts"][0]
        print(f"   402 Payment Required: {req['maxAmountRequired']} to {req['payTo']}")
        # Present payment authorization and retry (the X-Payment header is the
        # agent's authorization to spend within its mandate).
        code, body = _post("/invoke", {"name": name}, {"X-Payment": "mandate-authorized"})
    if code == 200 and body.get("settled"):
        print(f"   settled. receipt {body['receiptHash'][:16]}... amount {body['amount']}")
    else:
        print(f"   not settled ({code}): {body.get('error')}")
    return code, body


def main():
    print("Canton 402 autonomous agent")
    code, body = _get("/services")
    services = body["services"]
    print(f"discovered {len(services)} service(s):")
    for s in services:
        print(f"  - {s['name']} @ {s['price']}  ({s['description']})")

    # Buy the two in-policy services; the gateway/ledger enforces the rest.
    for s in services:
        buy(s["name"])


if __name__ == "__main__":
    main()
