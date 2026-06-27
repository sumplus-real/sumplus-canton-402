"""Canton 402 MCP server (stdio, zero dependencies).

Exposes the Canton 402 gateway to any MCP client (Claude, etc.) as tools, so an
LLM agent can discover and pay for Canton services in its own loop. It is a thin
adapter over the running HTTP gateway -- the ledger still enforces policy and
privacy.

Transport: newline-delimited JSON-RPC 2.0 over stdin/stdout (MCP stdio).

Add to an MCP client config, e.g.:
  {"command": "python3", "args": ["gateway/mcp_server.py"]}
(the HTTP gateway must be running; set CANTON402_GATEWAY if not on :8402)
"""

import json
import os
import sys
import urllib.request
import urllib.error

GATEWAY = os.environ.get("CANTON402_GATEWAY", "http://localhost:8402")

TOOLS = [
    {
        "name": "discover_services",
        "description": "List the Canton 402 services the agent is allowed to see, with prices.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "pay_for_service",
        "description": (
            "Buy and call a Canton 402 service by name. Settles payment and "
            "delivery atomically on the Canton ledger, within the agent's "
            "mandate, and returns the on-ledger receipt. Rejected on-ledger if "
            "the spend breaks the mandate (cap or allow-list)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "service name"}},
            "required": ["name"],
        },
    },
]


def _http(method, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(GATEWAY + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def call_tool(name, args):
    if name == "discover_services":
        _, body = _http("GET", "/services")
        return body
    if name == "pay_for_service":
        svc = args["name"]
        code, body = _http("POST", "/invoke", {"name": svc})
        if code == 402 and "accepts" in body:
            # present payment authorization and retry (x402 handshake)
            code, body = _http("POST", "/invoke", {"name": svc}, {"X-Payment": "mandate-authorized"})
        return body
    raise ValueError(f"unknown tool {name}")


def handle(msg):
    method = msg.get("method")
    mid = msg.get("id")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "canton402", "version": "0.1.0"},
            },
        }
    if method == "notifications/initialized":
        return None  # notification, no reply
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params", {})
        try:
            result = call_tool(params["name"], params.get("arguments", {}))
            text = json.dumps(result, indent=2)
            return {
                "jsonrpc": "2.0",
                "id": mid,
                "result": {"content": [{"type": "text", "text": text}]},
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": mid,
                "result": {
                    "content": [{"type": "text", "text": f"error: {e}"}],
                    "isError": True,
                },
            }
    if mid is not None:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found"}}
    return None


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        reply = handle(msg)
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
