# Demo video script (3-5 min)

Goal: show a real AI agent buying services on Canton on its own — privately,
within policy, with proof. No slideware; everything on screen is the live ledger.

---

## Simplest: one command (~90s, recommended)

Record a single terminal running:

```
scripts/demo_video.sh
```

It builds, runs the acceptance suite green, then prints a narrated run on a
simulated ledger: the mandate, two atomic payments with hash-chained receipts,
an overspend blocked on-ledger, and the privacy check across five parties. No
sandbox to start. Read the lines aloud as they appear, or add the narration
below as voiceover. This screen alone proves the whole product.

For a richer three-screen version (acceptance suite, then the live HTTP-402
agent against `daml start`), follow the parts below.

---

## Part 1 — The product idea (20s, on the README or one slide)

> "AI agents are starting to spend money — on data, compute, other agents'
> services. Two things break: you can't trust an agent with an open wallet, and
> business payments shouldn't be public. Canton 402 fixes both. A company hands
> its agent a spending mandate as a contract, and the agent buys what it needs —
> privately, atomically, and only within the rules."

## Part 2 — It actually runs: acceptance suite (60-90s, terminal)

```
daml test --all
```

> "This is the whole product as a test. Two successful purchases with
> hash-chained receipts. Then three attempts that the ledger rejects: over the
> per-transaction cap, paying a vendor that isn't on the allow-list, and going
> over the daily cap. The agent's code never gets to overspend — the mandate
> stops it on the ledger."

Point at the privacy assertions in the output:

> "And privacy is checked here too: a rival party sees zero of the company's
> receipts; the auditor sees exactly the settled ones; each vendor sees only its
> own. That's Canton's sub-transaction privacy, not a setting we bolted on."

## Part 3 — The agent acting on its own (90-120s, terminals)

Terminal A:
```
daml start
```
Terminal B:
```
scripts/seed.sh          # parties, mandate, two offers, the agent's wallet
scripts/run_gateway.sh   # the Canton 402 HTTP gateway
```
Terminal C:
```
python3 gateway/agent.py
```

> "Now the agent runs against a live ledger through a plain HTTP gateway — it
> needs no Canton SDK. It discovers the services it's allowed to see. For each
> one it gets back HTTP 402, Payment Required — the same handshake as web
> payments — presents its authorization, and the gateway settles it on the
> ledger in one atomic transaction. Back comes the receipt hash."

Optionally open Navigator (the browser tab `daml start` opened) and show the
`PaymentReceipt` contracts existing only for Agent, the vendors, and the Auditor.

## Part 4 — Close (15s)

> "Real Daml, real policy, real privacy. This is a working slice of the Canton
> 402 payment protocol from our CAEL grant — the agent-commerce rail Canton
> doesn't have yet."

---

### Notes for the recorder
- Run `daml test --all` once before recording so the SDK is warm (first run is slow).
- If you only have time for one screen, record Part 2 — it is self-contained and proves everything.
- Keep total under 3:00 if possible; the cap is 5:00.
