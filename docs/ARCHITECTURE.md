# Canton 402 — Architecture

## 1. What it is

Canton 402 is an agent-native pay-and-call protocol on Canton. An AI agent, acting
for a principal (a company or individual), discovers a priced service and buys it
in a single atomic Daml transaction that is (a) gated by an on-ledger spending
policy, (b) private to the counterparties and a named auditor, and (c) recorded
in a tamper-evident receipt chain.

It is "Canton 402" because it is the settlement-layer sibling of HTTP 402 / x402:
same intent (machine pays for a resource), but settled in a Canton asset with
Canton's privacy and atomic-settlement guarantees instead of a public-chain
stablecoin transfer.

## 2. Parties

| Party | Role |
|---|---|
| Principal (e.g. *Acme*) | Issues the agent's spending mandate. Owns the policy. |
| Agent | Acts for the principal. Holds the settlement asset, discovers offers, calls `PayAndCall`. Can only act within the mandate. |
| Provider / Vendor | Publishes `ServiceOffer`s, receives payment, delivers entitlements. |
| Issuer (e.g. *SettlementBank*) | Issues the settlement `Asset` (Canton Coin / tokenized deposit stand-in). |
| Auditor | Granted need-to-know visibility of receipts. A regulator or the principal's controller. |

## 3. Contracts and the atomic flow

The unit of work is the `PayAndCall` choice on `ServiceOffer`. In one Daml
transaction, with the authority of the agent (choice controller) and the provider
(offer signatory), it performs four sub-actions that commit together or roll back
together:

1. **Policy gate** — `exercise mandateCid Authorize`. Checks the vendor allow-list,
   per-transaction cap, and running daily cap; recreates the mandate with the new
   daily total. Any breach aborts the entire transaction.
2. **Settlement** — `exercise assetCid Split`. Moves `price` to the provider and
   returns change to the agent. The split is controlled by the asset's owner, so
   it succeeds only when the agent actually holds the funds, and the asset's
   issuer is checked against the offer's expected settlement issuer.
3. **Delivery** — `create ServiceEntitlement`. The agent's proof it may now consume
   the service.
4. **Receipt** — `create PaymentReceipt`, with `thisHash = sha256(seq | service |
   price | prevHash)`. Hash-chained to the previous receipt.

Because all four are sub-transactions of one commit, the protocol has no partial
fills: there is never payment without delivery, delivery without policy approval,
or a receipt without a real settlement.

## 4. Privacy model

Canton's ledger shows each contract only to its **stakeholders** (signatories and
observers). Canton 402 uses this deliberately:

| Contract | Signatories | Observers | Who is blind to it |
|---|---|---|---|
| `Asset` | issuer | owner | every party except the holder and the issuer |
| `Mandate` | principal | agent | vendors never see the principal's full policy |
| `ServiceOffer` | provider | `discoverableBy` agents | parties not invited to discover |
| `ServiceEntitlement` | provider, agent | — | everyone else |
| `PaymentReceipt` | provider, agent | auditor | other vendors, rival agents, the public |

Concretely (asserted in `Test.Demo`): a rival party sees **zero** of Acme's
holdings, entitlements, or receipts; each vendor sees only its own receipts, not
the other vendor's; the auditor sees exactly the settled receipts. A vendor never
learns the principal's caps or which other vendors are on the allow-list.

A regulator can be added as a receipt observer for disclosure-on-demand without
making any payment public — the institutional middle ground a transparent chain
cannot offer.

## 5. Threat model

| Threat | Mitigation |
|---|---|
| Compromised / prompt-injected agent tries to overspend | `Mandate.Authorize` enforces per-tx and daily caps on-ledger; the agent's own code is not trusted. |
| Agent pays an attacker-controlled vendor | Vendor allow-list enforced in `Authorize`; a non-listed provider's `PayAndCall` is rejected. |
| Pay-without-delivery / delivery-without-pay | Single atomic transaction; partial execution is impossible. |
| Spending another principal's funds | `Split` is controlled by the asset owner; the mandate binds `m.agent == agent`. |
| Tampering with the audit trail | Receipts are hash-chained; altering any receipt breaks every later hash. Signatories cannot unilaterally rewrite history (archival is observable to stakeholders). |
| Front-running / surveillance of treasury flows | Sub-transaction privacy: payments are not on a public mempool or explorer. |
| Settling in the wrong / fake asset | The offer pins the expected `issuer`; the settled asset's issuer is checked. |

## 6. Deployment

**Local (acceptance + demo).** `daml test` runs the full suite headless.
`daml start` boots a sandbox ledger, the JSON API, and Navigator for interactive
exploration. This is the same Daml runtime Canton uses; the contracts are
network-portable without change.

**Gateway.** The Canton 402 gateway (`gateway/`) exposes the protocol over HTTP
and MCP so any agent — including ones with no Canton SDK — can discover and pay
for services. It returns an HTTP 402 with payment requirements (x402-compatible
header shape), accepts the agent's authorization, and submits the `PayAndCall`
to the ledger via the Daml JSON API.

**Canton network.** Moving from sandbox to a Canton domain (e.g. a devnet
participant) is a configuration change: the same DAR deploys to a Canton
participant node, with parties hosted on participants and synchronized through a
domain. No contract changes are required.

## 7. Relationship to CAEL and Sumplus products

- **Maria** (policy-driven agent execution) → the `Mandate` contract and its
  `Authorize` gate.
- **Arsenal** (skills / paid-service marketplace, x402 today) → the `ServiceOffer`
  + `PayAndCall` model; Canton 402 is Arsenal's Canton settlement extension.
- **Verifiable agent** (commit-reveal + hash-chained receipts, live on EVM) →
  the on-ledger `PaymentReceipt` chain.
- **CAEL grant** → this project is a running slice of CAEL milestones M2–M3
  (on-chain Daml contracts + Canton 402 payment protocol), proving the proposed
  contract suite end-to-end.
