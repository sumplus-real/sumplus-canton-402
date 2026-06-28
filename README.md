# Canton 402: Private, Policy-Bound Pay-and-Call for AI Agents

**Track:** Payments, Neobanking & Agent Commerce (Canton Foundation)

**▶ Live demo:** https://canton402-demo-production.up.railway.app . A real Canton
ledger, gateway, and dashboard in one container. Every click is a transaction on
the running ledger.

Canton 402 lets a business hand its AI agent a spending **mandate** and then let
the agent **buy services on its own**. The agent stays private, settles each
purchase atomically, and can only spend within the rules the business set. Every
purchase settles payment and delivery in a single Daml transaction, stays
visible only to the two counterparties and a named auditor, and leaves a
tamper-evident receipt.

It is an agent-era corporate card: programmable limits, an allow-list of
vendors, an auditable trail, and privacy by default. We build on Canton because
a payment there can settle for real and stay off the public record.

---

## The problem

AI agents are starting to pay for things: data feeds, compute, settlement,
other agents' services. Two things break when they do.

1. **Trust.** "Let the agent spend money" is terrifying without hard limits. A
   prompt-injected or buggy agent should not be able to drain an account or pay
   a stranger. Guardrails written in application code are a promise; guardrails
   written as a contract are enforced.
2. **Privacy.** Business payments are not meant to be public. On a transparent
   chain, every vendor relationship, price, and volume is exposed. Institutions
   will not run real treasury flows there.

Canton fixes the second by design (sub-transaction privacy: only parties to a
contract see it). Canton 402 adds the first, and wires the two together into a
product an individual or a business could actually use.

---

## How it works

```
  Acme (principal)                 Agent (Acme's AI)                Vendor
        │                                 │                            │
        │  issues Mandate                 │                            │
        │  (per-tx cap, daily cap,        │      discovers ServiceOffer│
        │   vendor allow-list, auditor)   │◄───────────────────────────┤
        ├────────────────────────────────►│                            │
        │                                 │                            │
        │                                 │   exercise PayAndCall  ─────► ONE atomic Daml tx:
        │                                 │                            │   1. check Mandate (policy)
        │                                 │                            │   2. settle payment + change
        │                                 │                            │   3. deliver ServiceEntitlement
        │                                 │                            │   4. write hash-chained Receipt
        │                                 │◄─── entitlement + receipt ──┤
        │   auditor sees receipts         │                            │
        │   (need-to-know)                │                            │
```

The whole purchase is **one transaction**. If the policy check fails, the
payment never happens. If the payment can't settle, the service isn't delivered.
There are no partial fills and no pay-without-delivery.

### The four contracts (the Canton 402 suite)

| Contract | Role | Ties to |
|---|---|---|
| `Mandate` | The agent's spending policy as a contract: per-tx cap, daily cap, running total, vendor allow-list, auditor. The `Authorize` choice enforces it on every spend. | **Maria** policy layer, native to Daml |
| `ServiceOffer` | A vendor's priced service. Its `PayAndCall` choice is the atomic pay-and-call primitive. | **Arsenal** skill / paid-service model |
| `PaymentReceipt` | Immutable, **hash-chained** receipt (each embeds the previous hash). Visible only to buyer, seller, auditor. | Sumplus **verifiable-agent** audit pattern |
| `Asset` | Issuer-signed settlement holding (stands in for Canton Coin / a tokenized deposit). | Canton token-standard pattern |

---

## How this complements the CAEL grant

Sumplus has a Canton Foundation Development Fund proposal, **CAEL (Canton Agent
Execution Layer)**. CAEL ships three layers across four milestones; the Canton
402 payment protocol and its Daml contract suite are scoped to **M2–M3 (Q3–Q4
2026)**.

**This hackathon project is a working vertical slice of exactly that layer.** It
takes the contract suite the grant *proposed* (`PaymentObligation` /
`PaymentReceipt` / `PaidService` / `AgentPermissionFramework`) and makes it
*run* end-to-end, today, on the Daml ledger: policy enforcement, atomic
settlement, privacy, and the hash-chained audit trail. It's proof that the
grant's hardest milestone actually builds.

It also reuses Sumplus's existing products by design rather than reinventing
them: the **Maria** policy model becomes the `Mandate` contract, the **Arsenal**
paid-skill model becomes `ServiceOffer`, and the **verifiable-agent** receipt
chain (commit-reveal + hash-chained receipts, already live on the EVM trading
agent) becomes the on-ledger `PaymentReceipt`.

---

## Run it

Prerequisites: [Daml SDK](https://docs.daml.com/getting-started/installation.html)
2.10.x (`curl -sSL https://get.daml.com/ | sh`).

```bash
# Type-check and run the full acceptance suite (policy + privacy assertions)
daml test

# Or explore interactively (ledger + Navigator UI)
daml start
```

`daml test` runs `Test.Demo`, which proves the whole product in one script:

- two successful atomic pay-and-calls with chained receipts;
- three out-of-policy attempts that are **rejected on-ledger** (over per-tx cap,
  unlisted vendor, over daily cap);
- privacy assertions: a rival party sees **zero** of Acme's receipts, holdings,
  or entitlements; the auditor sees exactly the settled receipts; each vendor
  sees only its own.

---

## Repository layout

```
daml/
  Canton402/Asset.daml      settlement asset (issuer-signed holding)
  Canton402/Mandate.daml    Maria policy layer, on-ledger
  Canton402/Commerce.daml   ServiceOffer + atomic PayAndCall + hash-chained receipt
  Test/Demo.daml            end-to-end acceptance script (daml test)
  Test/Narrate.daml         narrated run for the demo video
  Test/Setup.daml           seeds a live ledger (returns party ids)
gateway/
  ledger.py                 Daml JSON API client + dev JWT
  canton402_gateway.py      x402-compatible HTTP 402 gateway
  agent.py                  autonomous agent (discover -> 402 -> pay -> receipt)
  mcp_server.py             MCP stdio server (any LLM agent can call the tools)
scripts/                    demo.sh, seed.sh, run_gateway.sh
docs/ARCHITECTURE.md        design, threat model, privacy model
docs/DEMO_SCRIPT.md         3-5 min demo video script
```

---

Apache-2.0. Built by Sumplus for the Build on Canton hackathon. Contact:
j@sumplus.xyz
