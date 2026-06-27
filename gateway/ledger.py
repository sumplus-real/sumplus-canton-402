"""Thin Daml JSON API client for the Canton 402 gateway.

Pure standard library (works on the system python3). Talks to a running
`daml start` JSON API (default http://localhost:7575) and mints per-party dev
JWTs so the gateway can act as the agent, vendors, etc.

The JSON API scopes every read and write to the party in the bearer token, so
the privacy model is enforced by the ledger, not by this client.
"""

import base64
import hashlib
import hmac
import json
import os
import re
import urllib.request
import urllib.error

JSON_API = os.environ.get("CANTON402_JSON_API", "http://localhost:7575")
# Dev shared secret. `daml start` / sandbox in dev accepts HS256 tokens signed
# with this secret when started with `--json-api-option --auth-... ` or, in the
# default unsafe-dev mode, any well-formed token. Override via env in real use.
JWT_SECRET = os.environ.get("CANTON402_JWT_SECRET", "secret")
LEDGER_ID = os.environ.get("CANTON402_LEDGER_ID", "sandbox")


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def mint_token(party: str, app_id: str = "canton402-gateway") -> str:
    """Mint an HS256 dev JWT granting actAs/readAs for a single party."""
    header = {"alg": "HS256", "typ": "JWT"}
    claim = {
        "https://daml.com/ledger-api": {
            "ledgerId": LEDGER_ID,
            "applicationId": app_id,
            "actAs": [party],
            "readAs": [party],
        }
    }
    segments = [
        _b64url(json.dumps(header, separators=(",", ":")).encode()),
        _b64url(json.dumps(claim, separators=(",", ":")).encode()),
    ]
    signing_input = ".".join(segments).encode("ascii")
    sig = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    segments.append(_b64url(sig))
    return ".".join(segments)


def _clean_error(raw: str) -> str:
    """Pull the human-readable assertion out of a JSON API error body.

    On a policy breach the ledger raises a Daml AssertionFailed; surface just
    its message (e.g. "spend would bring today's total to 260.0, over the daily
    cap 250.0") instead of the full JSON error envelope.
    """
    m = re.search(r'message = \\?"(.*?)\\?"', raw)
    if m:
        return m.group(1)
    try:
        return json.loads(raw)["errors"][0]
    except Exception:
        return raw


def _post(path: str, party: str, body: dict) -> dict:
    url = JSON_API + path
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + mint_token(party))
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(_clean_error(e.read().decode())) from e


def package_ids() -> list:
    """Return the list of package ids known to the ledger."""
    url = JSON_API + "/v1/packages"
    req = urllib.request.Request(url, method="GET")
    # any party token works for /v1/packages
    req.add_header("Authorization", "Bearer " + mint_token("SettlementBank"))
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read()).get("result", [])


def resolve_main_package() -> str:
    """Resolve the canton402 main package id (the one carrying our templates).

    Override with CANTON402_PKG to skip the lookup.
    """
    forced = os.environ.get("CANTON402_PKG")
    if forced:
        return forced
    # The main DAR's package id is the largest non-stdlib package; in practice
    # callers pass CANTON402_PKG (printed by scripts/run_gateway.sh). As a
    # fallback we return the first package, but callers should set the env var.
    pkgs = package_ids()
    return pkgs[0] if pkgs else ""


def tid(pkg: str, module: str, entity: str) -> str:
    return f"{pkg}:{module}:{entity}"


def create(party: str, template_id: str, payload: dict) -> dict:
    return _post("/v1/create", party, {"templateId": template_id, "payload": payload})


def exercise(party: str, template_id: str, contract_id: str, choice: str, argument: dict) -> dict:
    return _post(
        "/v1/exercise",
        party,
        {
            "templateId": template_id,
            "contractId": contract_id,
            "choice": choice,
            "argument": argument,
        },
    )


def query(party: str, template_ids: list) -> list:
    res = _post("/v1/query", party, {"templateIds": template_ids})
    return res.get("result", [])
